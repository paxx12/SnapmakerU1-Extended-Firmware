#!/usr/bin/env python3
"""RFID Spools Management API.

Lightweight HTTP server that:
- Receives OpenRFID webhook events and stores tag data per channel
- Serves channel state via REST API
- Proxies to Moonraker for filament_detect state
"""

import argparse
import json
import logging
import logging.handlers
import os
import threading
import time
import urllib.parse
import urllib.request
import urllib.error
from http.server import HTTPServer, ThreadingHTTPServer, BaseHTTPRequestHandler

LOG_FILE = "/oem/printer_data/logs/rfid-spools.log"
CONFIG_FILE = "/oem/printer_data/config/extended/rfid-spools.json"
MOONRAKER_URL = "http://localhost"
MAX_CHANNELS = 4
MAX_BODY_SIZE = 64 * 1024  # 64KB max request body


class EventBus:
    """Broadcast tag events to SSE listeners."""

    def __init__(self):
        self._lock = threading.Lock()
        self._listeners = []

    def subscribe(self):
        q = []
        with self._lock:
            self._listeners.append(q)
        return q

    def unsubscribe(self, q):
        with self._lock:
            try:
                self._listeners.remove(q)
            except ValueError:
                pass

    def publish(self, event_type, data):
        msg = 'event: {}\ndata: {}\n\n'.format(event_type, json.dumps(data))
        with self._lock:
            for q in self._listeners:
                q.append(msg)


event_bus = EventBus()


class ChannelStore:
    """Thread-safe storage for per-channel tag data from OpenRFID webhooks."""

    def __init__(self):
        self._lock = threading.Lock()
        self._channels = {i: None for i in range(MAX_CHANNELS)}

    def update(self, channel, data):
        if not isinstance(channel, int) or channel < 0 or channel >= MAX_CHANNELS:
            return False
        with self._lock:
            self._channels[channel] = data
        return True

    def get_all(self):
        with self._lock:
            return dict(self._channels)

    def get(self, channel):
        with self._lock:
            return self._channels.get(channel)


store = ChannelStore()

SYNC_STATE_FILE = "/oem/printer_data/config/extended/rfid-spools-sync-state.json"


class SyncStateStore:
    """Persists per-channel Spoolman sync state (filament_id, spool_id, uid, timestamp)."""

    def __init__(self):
        self._lock = threading.Lock()
        self._state = {}
        self._load()

    def _load(self):
        try:
            with open(SYNC_STATE_FILE, 'r') as f:
                self._state = json.load(f)
        except (OSError, ValueError):
            self._state = {}

    def _save(self):
        try:
            os.makedirs(os.path.dirname(SYNC_STATE_FILE), exist_ok=True)
            with open(SYNC_STATE_FILE, 'w') as f:
                json.dump(self._state, f)
        except OSError:
            logging.exception("Failed to save sync state")

    def set(self, channel, filament_id, spool_id, uid):
        import time
        with self._lock:
            self._state[str(channel)] = {
                'filament_id': filament_id,
                'spool_id': spool_id,
                'uid': uid,
                'synced_at': int(time.time()),
            }
            self._save()

    def get(self, channel):
        with self._lock:
            return self._state.get(str(channel))

    def clear_if_uid_changed(self, channel, current_uid):
        with self._lock:
            entry = self._state.get(str(channel))
            if entry and entry.get('uid') != current_uid:
                del self._state[str(channel)]
                self._save()

    def clear(self, channel):
        with self._lock:
            if str(channel) in self._state:
                del self._state[str(channel)]
                self._save()

    def get_all(self):
        with self._lock:
            return dict(self._state)


sync_state = SyncStateStore()

# Density defaults (g/cm³) by material type. Used when user doesn't override.
# Key lookup is done by uppercasing the first word-token of the material string.
MATERIAL_DENSITY = {
    'PLA': 1.24, 'PLA+': 1.24,
    'ABS': 1.05, 'ASA': 1.07,
    'PETG': 1.27, 'PET': 1.27,
    'TPU': 1.21, 'TPE': 1.21, 'FLEX': 1.21,
    'PA': 1.12, 'NYLON': 1.12,
    'PC': 1.20, 'HIPS': 1.05,
    'PVA': 1.23, 'PP': 0.91,
}
_DEFAULT_DENSITY = 1.24  # PLA-like safe fallback

# Default config — pre-populates the UI with sensible field mappings per tag type.
# Saved config overlays these; if tag_mappings is absent from disk, defaults are used.
DEFAULT_CONFIG = {
    "slot_names": {},
    "slot_notes": {},
    "spoolman_url": "",
    "spoolman_extra_fields": {
        "max_extruder_temp": False,
        "max_bed_temp": False,
        "drying_temp": False,
        "drying_time": False,
        "td": False,
        "mfg_date": False,
        "modifiers": False,
    },
    "tag_mappings": [
        {"to": "manufacturer",       "from": "manufacturer"},
        {"to": "type",               "from": "type"},
        {"to": "modifiers",          "from": "modifiers"},
        {"to": "color",              "from": "colors"},
        {"to": "hotend_min_temp",    "from": "hotend_min_temp_c"},
        {"to": "hotend_max_temp",    "from": "hotend_max_temp_c"},
        {"to": "bed_temp_min",       "from": "bed_temp_min_c"},
        {"to": "bed_temp_max",       "from": "bed_temp_c"},
        {"to": "diameter_mm",        "from": "diameter_mm"},
        {"to": "weight_grams",       "from": "weight_grams"},
        {"to": "drying_temp",        "from": "drying_temp_c"},
        {"to": "drying_time",        "from": "drying_time_hours"},
        {"to": "manufacturing_date", "from": "manufacturing_date"},
        {"to": "td",                 "from": "td"},
        {"to": "message",            "from": "message"},
    ],
}


def load_config():
    """Load persistent config from disk, merged with defaults."""
    saved = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                saved = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logging.warning("Failed to load config: %s", e)

    config = dict(DEFAULT_CONFIG)
    config.update(saved)
    # tag_mappings is a flat list; migrate old per-processor dict format if needed
    if "tag_mappings" not in saved:
        config["tag_mappings"] = list(DEFAULT_CONFIG["tag_mappings"])
    elif isinstance(saved.get("tag_mappings"), dict):
        # Migrate: use the 'generic' block if present, otherwise reset to defaults
        config["tag_mappings"] = saved["tag_mappings"].get("generic", list(DEFAULT_CONFIG["tag_mappings"]))
    # Fix: bed_temp_max was mistakenly mapped from bed_temp_max_c; correct to bed_temp_c
    for m in config.get("tag_mappings", []):
        if isinstance(m, dict) and m.get("to") == "bed_temp_max" and m.get("from") == "bed_temp_max_c":
            m["from"] = "bed_temp_c"
    return config


def save_config(config):
    """Save config to disk."""
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    tmp = CONFIG_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(config, f, indent=2)
    os.replace(tmp, CONFIG_FILE)


def query_moonraker_filament_detect():
    """Query Moonraker for current filament_detect state."""
    url = f"{MOONRAKER_URL}/printer/objects/query?filament_detect"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read())
    except (urllib.error.URLError, OSError, json.JSONDecodeError) as e:
        logging.warning("Moonraker query failed: %s", e)
        return None


def moonraker_gcode(script):
    """Send a G-code script to Klipper via Moonraker."""
    url = f"{MOONRAKER_URL}/printer/gcode/script"
    body = json.dumps({"script": script}).encode("utf-8")
    req = urllib.request.Request(
        url, data=body, method="POST",
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def probe_spoolman(url):
    """Return True if a Spoolman instance responds at the given base URL."""
    try:
        req = urllib.request.Request(
            url.rstrip('/') + '/api/v1/info', method='GET'
        )
        with urllib.request.urlopen(req, timeout=2) as resp:
            return 200 <= resp.status < 300
    except Exception:
        return False


def query_moonraker_spoolman_url():
    """Try to read the configured Spoolman URL from Moonraker's config API."""
    try:
        req = urllib.request.Request(
            f"{MOONRAKER_URL}/server/config", method='GET'
        )
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read())
        spoolman = data.get('result', {}).get('config', {}).get('spoolman', {})
        return spoolman.get('server', '') or ''
    except Exception:
        return ''


def argb_to_color_hex(val):
    """Convert an ARGB integer (or first element of a list) to RRGGBB hex without '#'."""
    if isinstance(val, (list, tuple)) and len(val) > 0:
        val = val[0]
    if isinstance(val, int):
        r = (val >> 16) & 0xFF
        g = (val >> 8) & 0xFF
        b = val & 0xFF
        return '{:02X}{:02X}{:02X}'.format(r, g, b)
    if isinstance(val, str):
        v = val.lstrip('#')
        if len(v) in (6, 8):
            return v[-6:].upper()
    return None


def argb_list_to_multi_hex(colors):
    """Convert a list of ARGB ints to a comma-separated RRGGBB string for Spoolman multi_color_hexes."""
    if not isinstance(colors, (list, tuple)) or len(colors) < 2:
        return None
    hexes = []
    for val in colors:
        if isinstance(val, int):
            r = (val >> 16) & 0xFF
            g = (val >> 8) & 0xFF
            b = val & 0xFF
            hexes.append('{:02X}{:02X}{:02X}'.format(r, g, b))
    return ','.join(hexes) if len(hexes) >= 2 else None


def format_datetime_for_spoolman(val):
    """Convert common date formats to ISO 8601 datetime string (YYYY-MM-DDTHH:MM:SS)."""
    if val is None:
        return None
    s = str(val).strip()
    if s in ('', '19700101', '0001-01-01', 'NONE', '0'):
        return None
    # YYYYMMDD
    if len(s) == 8 and s.isdigit():
        return '{}-{}-{}T00:00:00'.format(s[:4], s[4:6], s[6:8])
    # YYYY-MM-DD
    if len(s) == 10 and s[4:5] == '-' and s[7:8] == '-':
        return s + 'T00:00:00'
    # Already has time component
    if 'T' in s and len(s) >= 19:
        return s[:19]
    return None


def spoolman_api_request(base_url, method, path, body=None):
    """Make an HTTP request to the Spoolman REST API. Raises on error."""
    url = base_url.rstrip('/') + path
    data = json.dumps(body).encode('utf-8') if body is not None else None
    headers = {}
    if data:
        headers['Content-Type'] = 'application/json'
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        try:
            detail = e.read().decode('utf-8', errors='replace')
        except Exception:
            detail = ''
        # Try to extract the most useful part from Pydantic error
        try:
            err_obj = json.loads(detail)
            pyd_details = err_obj.get('detail', [])
            if isinstance(pyd_details, list) and pyd_details:
                msgs = ['{} @ {}: {}'.format(
                    d.get('type', '?'),
                    '.'.join(str(x) for x in d.get('loc', [])),
                    d.get('msg', ''),
                ) for d in pyd_details[:3]]
                detail = '; '.join(msgs)
        except Exception:
            pass
        logging.error("Spoolman API error %s %s -> HTTP %d: %s", method, url, e.code, detail)
        raise urllib.error.HTTPError(url, e.code, '{}: {}'.format(e.reason, detail), e.headers, None)


def resolve_display_fields(tag_event, config):
    """Apply tag_mappings config to resolve display fields from a raw tag event."""
    filament = tag_event.get('filament') or {}

    mappings = {}
    for rule in config.get('tag_mappings', []):
        to_key = rule.get('to')
        from_key = rule.get('from')
        if to_key and from_key:
            mappings[to_key] = from_key

    def get_mapped(display_key):
        from_key = mappings.get(display_key)
        if from_key:
            return filament.get(from_key)
        return None

    # UID: prefer scan.uid (TigerTag / generic RFID), fall back to CARD_UID (Snapmaker)
    uid_raw = (tag_event.get('scan') or {}).get('uid')
    if isinstance(uid_raw, list) and uid_raw:
        uid = ''.join('{:02X}'.format(b & 0xFF) for b in uid_raw)
    elif uid_raw:
        uid = str(uid_raw)
    else:
        # Snapmaker tags store UID as CARD_UID in the filament dict
        card_uid = filament.get('CARD_UID') or filament.get('card_uid')
        if isinstance(card_uid, (list, tuple)) and card_uid:
            uid = ''.join('{:02X}'.format(b & 0xFF) for b in card_uid)
        elif card_uid:
            uid = str(card_uid)
        else:
            uid = None

    return {
        'manufacturer':      get_mapped('manufacturer'),
        'type':              get_mapped('type'),
        'modifiers':         get_mapped('modifiers'),
        'colors':            get_mapped('color'),
        'hotend_min_temp_c': get_mapped('hotend_min_temp'),
        'hotend_max_temp_c': get_mapped('hotend_max_temp'),
        'bed_temp_min_c':    get_mapped('bed_temp_min'),
        'bed_temp_max_c':    get_mapped('bed_temp_max'),
        'diameter_mm':       get_mapped('diameter_mm'),
        'weight_grams':      get_mapped('weight_grams'),
        'drying_temp_c':     get_mapped('drying_temp'),
        'drying_time_hours': get_mapped('drying_time'),
        'manufacturing_date': get_mapped('manufacturing_date'),
        'td':                get_mapped('td'),
        'message':           get_mapped('message'),
        'uid':               uid,
    }


def sync_to_spoolman(base_url, fields, name, extra_fields=None, override_filament_id=None, density=None):
    """Upsert vendor → filament → spool in Spoolman. Returns result dict."""
    uid = fields.get('uid')
    if not uid:
        raise ValueError("tag has no UID")
    uid = str(uid)  # already formatted as hex string by resolve_display_fields

    # 1. Upsert vendor
    vendor_id = None
    manufacturer = fields.get('manufacturer')
    if manufacturer:
        existing = spoolman_api_request(
            base_url, 'GET',
            '/api/v1/vendor?name=' + urllib.parse.quote(str(manufacturer))
        )
        if existing:
            vendor_id = existing[0]['id']
        else:
            new_vendor = spoolman_api_request(
                base_url, 'POST', '/api/v1/vendor', {'name': manufacturer}
            )
            vendor_id = new_vendor['id']

    # 2. Build filament payload
    # name is required by Spoolman — use fallback if user left it blank
    if not name:
        parts = [fields.get('type'), fields.get('manufacturer')]
        name = ' '.join(p for p in parts if p) or 'Unknown Filament'
    filament_payload = {'external_id': uid, 'name': name}
    if vendor_id is not None:
        filament_payload['vendor_id'] = vendor_id
    material = fields.get('type')
    if material:
        filament_payload['material'] = material
    # density is required by Spoolman — fall back to material lookup if not provided by user
    try:
        density_val = float(density) if density is not None else None
    except (TypeError, ValueError):
        density_val = None
    if not density_val or density_val <= 0:
        mat_key = str(material or '').upper().split()[0].split('-')[0] if material else ''
        density_val = MATERIAL_DENSITY.get(mat_key, _DEFAULT_DENSITY)
    filament_payload['density'] = density_val
    # Multi-color support: if more than one color, use multi_color_hexes
    colors_raw = fields.get('colors')
    multi_hex = argb_list_to_multi_hex(colors_raw)
    if multi_hex:
        filament_payload['multi_color_hexes'] = multi_hex
    else:
        color_hex = argb_to_color_hex(colors_raw)
        if color_hex:
            filament_payload['color_hex'] = color_hex
    def _int_pos(val):
        """Return int(val) if > 0, else None. Handles string-float inputs like '210.0'."""
        try:
            v = int(float(str(val)))
            return v if v > 0 else None
        except (TypeError, ValueError):
            return None

    def _float_pos(val):
        """Return float(val) if > 0, else None."""
        try:
            v = float(val)
            return v if v > 0 else None
        except (TypeError, ValueError):
            return None

    v = _int_pos(fields.get('hotend_min_temp_c'))
    if v is not None:
        filament_payload['settings_extruder_temp'] = v
    v = _int_pos(fields.get('bed_temp_min_c')) or _int_pos(fields.get('bed_temp_max_c'))
    if v is not None:
        filament_payload['settings_bed_temp'] = v
    v = _float_pos(fields.get('diameter_mm'))
    if v is not None:
        filament_payload['diameter'] = v
    weight_grams_raw = fields.get('weight_grams')
    try:
        weight_grams = float(weight_grams_raw) if weight_grams_raw is not None else None
    except (TypeError, ValueError):
        weight_grams = None
    if weight_grams and weight_grams > 0:
        filament_payload['weight'] = weight_grams

    if extra_fields:
        _field_map = [
            ('max_extruder_temp', 'hotend_max_temp_c'),
            ('max_bed_temp',      'bed_temp_max_c'),
            ('drying_temp',       'drying_temp_c'),
            ('drying_time',       'drying_time_hours'),
            ('td',                'td'),
            ('mfg_date',          'manufacturing_date'),
            ('modifiers',         'modifiers'),
        ]
        extra = {}
        _int_extra = {'max_extruder_temp', 'max_bed_temp', 'drying_temp'}
        _str_extra  = {'mfg_date', 'modifiers'}  # text/datetime: must be JSON-quoted strings
        for spoolman_key, src_key in _field_map:
            if extra_fields.get(spoolman_key):
                val = fields.get(src_key)
                if val is None:
                    continue
                if spoolman_key == 'mfg_date':
                    val = format_datetime_for_spoolman(val)
                elif isinstance(val, list):
                    val = ', '.join(str(v) for v in val if v)
                if not val and val != 0:
                    continue
                # Spoolman validates extra field values as JSON.
                # Integer fields need an integer-string ("260", not "260.0").
                # Text/datetime fields need a JSON-quoted string ('"Matte"').
                # Float fields ("1.5") are valid JSON numbers as-is.
                if spoolman_key in _int_extra:
                    try:
                        extra[spoolman_key] = str(int(float(str(val))))
                    except (TypeError, ValueError):
                        continue
                elif spoolman_key in _str_extra:
                    extra[spoolman_key] = json.dumps(str(val))
                else:
                    extra[spoolman_key] = str(val)
        if extra:
            filament_payload['extra'] = extra

    # 3. Upsert filament by external_id or override
    uid_encoded = urllib.parse.quote(str(uid))
    if override_filament_id is not None:
        # User chose an existing filament — link the tag UID to it and update fields
        filament_payload['external_id'] = uid
        spoolman_api_request(
            base_url, 'PATCH', '/api/v1/filament/{}'.format(override_filament_id), filament_payload
        )
        filament_id = override_filament_id
        created_filament = False
    else:
        existing_filaments = spoolman_api_request(
            base_url, 'GET', '/api/v1/filament?external_id=' + uid_encoded
        )
        if existing_filaments:
            filament_id = existing_filaments[0]['id']
            spoolman_api_request(
                base_url, 'PATCH', '/api/v1/filament/{}'.format(filament_id), filament_payload
            )
            created_filament = False
        else:
            filament_payload['external_id'] = uid
            new_filament = spoolman_api_request(
                base_url, 'POST', '/api/v1/filament', filament_payload
            )
            filament_id = new_filament['id']
            created_filament = True

    # 4. Upsert spool
    spool_payload = {'filament_id': filament_id}
    if weight_grams and weight_grams > 0:
        spool_payload['initial_weight'] = weight_grams

    existing_spools = spoolman_api_request(
        base_url, 'GET', '/api/v1/spool?filament_id={}'.format(filament_id)
    )
    created_spool = False
    if existing_spools:
        spool_id = existing_spools[0]['id']
        if weight_grams is not None:
            spoolman_api_request(
                base_url, 'PATCH', '/api/v1/spool/{}'.format(spool_id),
                {'initial_weight': float(weight_grams)}
            )
    else:
        new_spool = spoolman_api_request(
            base_url, 'POST', '/api/v1/spool', spool_payload
        )
        spool_id = new_spool['id']
        created_spool = True

    return {
        'filament_id': filament_id,
        'spool_id': spool_id,
        'created_filament': created_filament,
        'created_spool': created_spool,
        'status': 'ok',
    }


class RequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the RFID Spools API."""

    def log_message(self, fmt, *args):
        logging.info(fmt, *args)

    def _send_json(self, status, data):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length > MAX_BODY_SIZE:
            return None
        return self.rfile.read(length)

    def do_GET(self):
        if self.path == "/api/health":
            self._send_json(200, {"status": "ok"})

        elif self.path == "/api/channels":
            # Merge Moonraker filament_detect with stored OpenRFID data
            moonraker = query_moonraker_filament_detect()
            filament_detect = {}
            if moonraker and "result" in moonraker:
                status = moonraker["result"].get("status", {})
                filament_detect = status.get("filament_detect", {})

            # filament_detect.info is an array of per-channel dicts
            fd_info = filament_detect.get("info", [])

            channels = []
            stored = store.get_all()
            config = load_config()
            spoolman_url = config.get('spoolman_url', '').rstrip('/')
            for ch in range(MAX_CHANNELS):
                mk = fd_info[ch] if ch < len(fd_info) else {}
                tag = stored[ch]
                # Clear stale sync state if the tag UID changed
                if tag and spoolman_url:
                    uid_raw = (tag.get('scan') or {}).get('uid')
                    if isinstance(uid_raw, list):
                        current_uid = ''.join('{:02X}'.format(b & 0xFF) for b in uid_raw)
                    elif uid_raw:
                        current_uid = str(uid_raw)
                    else:
                        current_uid = None
                    if current_uid:
                        sync_state.clear_if_uid_changed(ch, current_uid)
                channel_data = {
                    "channel": ch,
                    "moonraker": mk if isinstance(mk, dict) else {},
                    "tag": tag,
                    "spoolman_sync": sync_state.get(ch),
                }
                channels.append(channel_data)

            self._send_json(200, {"channels": channels})

        elif self.path == "/api/config":
            self._send_json(200, load_config())

        elif self.path == "/api/spoolman-status":
            config = load_config()
            spoolman_url = config.get('spoolman_url', '').rstrip('/')
            if not spoolman_url:
                self._send_json(200, {"configured": False})
                return
            ok = probe_spoolman(spoolman_url)
            self._send_json(200, {"configured": True, "ok": ok})

        elif self.path.startswith("/api/spoolman-ping"):
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)
            target = params.get('url', [None])[0]
            if not target:
                self._send_json(400, {"error": "missing url parameter"})
                return
            # Validate scheme to prevent SSRF to local services
            if not target.startswith(('http://', 'https://')):
                self._send_json(400, {"error": "invalid url scheme"})
                return
            ok = probe_spoolman(target)
            self._send_json(200, {"reachable": ok})

        elif self.path.startswith("/api/spoolman-discover"):
            candidates = []
            seen = set()

            mk_url = query_moonraker_spoolman_url()
            if mk_url and mk_url not in seen:
                seen.add(mk_url)
                if probe_spoolman(mk_url):
                    candidates.append(mk_url)

            for probe_url in [
                "http://localhost:7912",
                "http://127.0.0.1:7912",
                "http://spoolman.local:7912",
            ]:
                if probe_url not in seen:
                    seen.add(probe_url)
                    if probe_spoolman(probe_url):
                        candidates.append(probe_url)

            self._send_json(200, {"candidates": candidates})

        elif self.path.startswith("/api/spoolman-extra-fields-status"):
            config = load_config()
            spoolman_url = config.get('spoolman_url', '').rstrip('/')
            if not spoolman_url:
                self._send_json(400, {"error": "spoolman_url not configured"})
                return
            try:
                existing = spoolman_api_request(spoolman_url, 'GET', '/api/v1/field/filament') or []
                registered = set(f['key'] for f in existing)
                known_keys = ['max_extruder_temp', 'max_bed_temp', 'drying_temp', 'drying_time', 'td', 'mfg_date', 'modifiers']
                self._send_json(200, {"fields": {k: k in registered for k in known_keys}})
            except Exception:
                logging.exception("Extra fields status error")
                self._send_json(502, {"error": "failed to query spoolman"})

        elif self.path.startswith("/api/spoolman-candidates"):
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)
            channel_str = params.get('channel', [None])[0]
            if channel_str is None:
                self._send_json(400, {"error": "missing channel parameter"})
                return
            try:
                channel = int(channel_str)
            except (ValueError, TypeError):
                self._send_json(400, {"error": "invalid channel"})
                return

            config = load_config()
            spoolman_url = config.get('spoolman_url', '').rstrip('/')
            if not spoolman_url:
                self._send_json(400, {"error": "spoolman_url not configured"})
                return

            tag_event = store.get(channel)
            if not tag_event or not tag_event.get('filament'):
                self._send_json(404, {"error": "no tag data for channel"})
                return

            fields = resolve_display_fields(tag_event, config)
            material = fields.get('type')
            manufacturer = fields.get('manufacturer')

            try:
                qparams = {}
                if material:
                    qparams['material'] = material
                if manufacturer:
                    qparams['vendor_name'] = manufacturer
                path = '/api/v1/filament'
                if qparams:
                    path += '?' + urllib.parse.urlencode(qparams)
                filaments = spoolman_api_request(spoolman_url, 'GET', path) or []
                result = []
                for fil in filaments:
                    vendor = fil.get('vendor') or {}
                    result.append({
                        'id': fil['id'],
                        'name': fil.get('name', ''),
                        'material': fil.get('material', ''),
                        'color_hex': fil.get('color_hex', ''),
                        'vendor_name': vendor.get('name', ''),
                        'external_id': fil.get('external_id', ''),
                    })
                self._send_json(200, {"candidates": result})
            except Exception:
                logging.exception("Spoolman candidates error")
                self._send_json(502, {"error": "failed to query spoolman"})

        elif self.path.startswith("/api/spoolman-filament"):
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)
            channel_str = params.get('channel', [None])[0]
            if channel_str is None:
                self._send_json(400, {"error": "missing channel parameter"})
                return
            try:
                channel = int(channel_str)
            except (ValueError, TypeError):
                self._send_json(400, {"error": "invalid channel"})
                return

            config = load_config()
            spoolman_url = config.get('spoolman_url', '').rstrip('/')
            if not spoolman_url:
                self._send_json(400, {"error": "spoolman_url not configured"})
                return

            sync = sync_state.get(channel)
            if not sync or not sync.get('filament_id'):
                self._send_json(404, {"error": "channel not synced"})
                return

            try:
                filament = spoolman_api_request(
                    spoolman_url, 'GET',
                    '/api/v1/filament/{}'.format(sync['filament_id'])
                )
                self._send_json(200, {
                    'name':        filament.get('name', ''),
                    'density':     filament.get('density', 1.24),
                    'material':    filament.get('material', ''),
                    'filament_id': sync['filament_id'],
                })
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    # Filament was deleted from Spoolman — clear stale local sync state
                    sync_state.clear(channel)
                self._send_json(e.code if e.code in (404, 400) else 502,
                                {"error": "Spoolman: " + str(e.reason)})
            except Exception:
                logging.exception("Spoolman filament fetch error")
                self._send_json(502, {"error": "failed to query spoolman"})

        elif self.path == "/api/events":
            # Server-Sent Events stream
            q = event_bus.subscribe()
            try:
                self.send_response(200)
                self.send_header('Content-Type', 'text/event-stream')
                self.send_header('Cache-Control', 'no-cache')
                self.send_header('X-Accel-Buffering', 'no')
                self.end_headers()
                # Send a keepalive comment immediately so the browser connects
                self.wfile.write(b': ok\n\n')
                self.wfile.flush()
                while True:
                    time.sleep(0.2)
                    msgs = q[:]
                    del q[:]
                    for m in msgs:
                        self.wfile.write(m.encode())
                    self.wfile.flush()
            except (OSError, BrokenPipeError, ConnectionResetError):
                pass
            finally:
                event_bus.unsubscribe(q)
            return

        else:
            self._send_json(404, {"error": "not found"})

    def do_POST(self):
        if self.path == "/api/tag-event":
            body = self._read_body()
            if body is None:
                self._send_json(413, {"error": "body too large"})
                return
            try:
                data = json.loads(body)
            except (json.JSONDecodeError, ValueError):
                self._send_json(400, {"error": "invalid json"})
                return

            channel = data.get("channel")
            if channel is None:
                # Try to extract from reader.slot
                reader = data.get("reader", {})
                channel = reader.get("slot")

            if channel is None:
                self._send_json(400, {"error": "missing channel"})
                return

            try:
                channel = int(channel)
            except (TypeError, ValueError):
                self._send_json(400, {"error": "invalid channel"})
                return

            event = data.get("event", "tag_read")
            if event in ("tag_not_present", "tag_parse_error"):
                store.update(channel, {"event": event, "tag": None})
                event_bus.publish("tag-removed", {"channel": channel})
            else:
                store.update(channel, data)
                event_bus.publish("tag-event", {"channel": channel})

            self._send_json(200, {"status": "ok"})

        elif self.path == "/api/config":
            body = self._read_body()
            if body is None:
                self._send_json(413, {"error": "body too large"})
                return
            try:
                data = json.loads(body)
            except (json.JSONDecodeError, ValueError):
                self._send_json(400, {"error": "invalid json"})
                return
            config = load_config()
            config.update(data)
            save_config(config)
            self._send_json(200, config)

        elif self.path == "/api/scan":
            # Trigger a fresh RFID scan on all channels by issuing
            # FILAMENT_DT_UPDATE G-code, which sets state=1 per channel
            # and causes OpenRFID to re-read the tags.
            body = self._read_body()  # optional {"channels": [0,1,2,3]}
            channels = list(range(MAX_CHANNELS))
            if body:
                try:
                    req_data = json.loads(body)
                    if "channels" in req_data and isinstance(req_data["channels"], list):
                        channels = [int(c) for c in req_data["channels"]
                                    if 0 <= int(c) < MAX_CHANNELS]
                except (json.JSONDecodeError, ValueError, TypeError):
                    pass

            errors = []
            for ch in channels:
                try:
                    moonraker_gcode(f"FILAMENT_DT_UPDATE CHANNEL={ch}")
                    logging.info("Triggered RFID scan for channel %d", ch)
                except (urllib.error.URLError, OSError) as e:
                    logging.warning("Scan trigger failed for channel %d: %s", ch, e)
                    errors.append(ch)

            if errors:
                self._send_json(500, {"status": "partial", "failed_channels": errors})
            else:
                self._send_json(200, {"status": "ok", "channels": channels})

        elif self.path.startswith("/api/spoolman-sync"):
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)
            channel_str = params.get('channel', [None])[0]
            if channel_str is None:
                self._send_json(400, {"error": "missing channel parameter"})
                return
            try:
                channel = int(channel_str)
            except (ValueError, TypeError):
                self._send_json(400, {"error": "invalid channel"})
                return

            body = self._read_body()
            req_data = {}
            if body:
                try:
                    req_data = json.loads(body)
                except (json.JSONDecodeError, ValueError):
                    pass
            name = req_data.get('name', '')

            try:
                override_filament_id = int(req_data.get('filament_id')) if req_data.get('filament_id') else None
            except (ValueError, TypeError):
                override_filament_id = None

            try:
                density = float(req_data['density']) if req_data.get('density') is not None else None
            except (TypeError, ValueError):
                density = None

            config = load_config()
            spoolman_url = config.get('spoolman_url', '').rstrip('/')
            if not spoolman_url:
                self._send_json(400, {"error": "spoolman_url not configured"})
                return

            tag_event = store.get(channel)
            if not tag_event or not tag_event.get('filament'):
                self._send_json(404, {"error": "no tag data for channel"})
                return

            fields = resolve_display_fields(tag_event, config)
            extra_fields = config.get('spoolman_extra_fields', {})
            try:
                result = sync_to_spoolman(spoolman_url, fields, name, extra_fields=extra_fields, override_filament_id=override_filament_id, density=density)
                sync_state.set(channel, result['filament_id'], result['spool_id'], fields.get('uid'))
                self._send_json(200, result)
            except ValueError as e:
                self._send_json(400, {"error": str(e)})
            except urllib.error.HTTPError as e:
                # Forward Spoolman's own error status/message to the client
                msg = str(e.reason)
                if e.code == 422:
                    msg = 'Spoolman rejected the data (422) — ' + msg + '. If extra fields are included, register them first in Config.'
                elif e.code == 404:
                    msg = 'Spoolman endpoint not found (404) — check Spoolman version.'
                self._send_json(e.code if e.code in (400, 422, 404) else 502, {"error": msg})
            except (urllib.error.URLError, OSError) as e:
                logging.error("Spoolman sync 502: url=%s error=%s", spoolman_url, e)
                self._send_json(502, {"error": "spoolman request failed: " + str(e)})
            except Exception:
                logging.exception("Spoolman sync error")
                self._send_json(500, {"error": "internal error"})

        elif self.path.startswith("/api/spoolman-register-extra-fields"):
            config = load_config()
            spoolman_url = config.get('spoolman_url', '').rstrip('/')
            if not spoolman_url:
                self._send_json(400, {"error": "spoolman_url not configured"})
                return
            _FIELD_DEFS = [
                ('max_extruder_temp', 'Max extruder temp',    'integer', '°C'),
                ('max_bed_temp',      'Max bed temp',          'integer', '°C'),
                ('drying_temp',       'Drying temperature',    'integer', '°C'),
                ('drying_time',       'Drying time',           'float',   'h'),
                ('td',                'Transparency density',  'float',   'mm'),
                ('mfg_date',          'Manufacturing date',    'datetime',  ''),
                ('modifiers',         'Modifiers / finish',    'text',    ''),
            ]
            registered = []
            already_existed = []
            errors = {}
            for key, name, ftype, unit in _FIELD_DEFS:
                try:
                    body = {'name': name, 'field_type': ftype}
                    if unit:
                        body['unit'] = unit
                    try:
                        spoolman_api_request(
                            spoolman_url, 'POST',
                            '/api/v1/field/filament/' + key,
                            body
                        )
                        registered.append(key)
                    except urllib.error.HTTPError as he:
                        if he.code == 409:
                            # Field already exists — update it via PATCH
                            spoolman_api_request(
                                spoolman_url, 'PATCH',
                                '/api/v1/field/filament/' + key,
                                body
                            )
                            already_existed.append(key)
                        else:
                            raise
                except Exception as e:
                    logging.exception("Register field %s error", key)
                    errors[key] = str(e)
            self._send_json(200, {"registered": registered, "already_existed": already_existed, "errors": errors})

        elif self.path.startswith("/api/spoolman-sync-all"):
            config = load_config()
            spoolman_url = config.get('spoolman_url', '').rstrip('/')
            if not spoolman_url:
                self._send_json(400, {"error": "spoolman_url not configured"})
                return
            extra_fields = config.get('spoolman_extra_fields', {})
            synced = []
            errors = []
            for ch in range(MAX_CHANNELS):
                tag_event = store.get(ch)
                if not tag_event or not tag_event.get('filament'):
                    continue
                fields = resolve_display_fields(tag_event, config)
                name = fields.get('message') or ''
                if not name:
                    parts = [fields.get('type'), fields.get('manufacturer')]
                    name = ' '.join(p for p in parts if p)
                try:
                    r = sync_to_spoolman(spoolman_url, fields, name, extra_fields=extra_fields)
                    sync_state.set(ch, r['filament_id'], r['spool_id'], fields.get('uid'))
                    r['channel'] = ch
                    synced.append(r)
                except Exception as e:
                    logging.exception("Sync-all error ch %d", ch)
                    errors.append({'channel': ch, 'error': str(e)})
            self._send_json(200, {"synced": synced, "errors": errors})

        else:
            self._send_json(404, {"error": "not found"})

    def do_PUT(self):
        if self.path == "/api/config":
            return self.do_POST()
        self._send_json(404, {"error": "not found"})


def setup_logging():
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    handlers = [
        logging.StreamHandler(),
        logging.handlers.TimedRotatingFileHandler(
            LOG_FILE, when="midnight", interval=1, backupCount=7
        ),
    ]
    fmt = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    for h in handlers:
        h.setFormatter(fmt)
    logging.root.handlers = handlers
    logging.root.setLevel(logging.INFO)


def main():
    parser = argparse.ArgumentParser(description="RFID Spools Management API")
    parser.add_argument("--bind", default="127.0.0.1", help="Bind address")
    parser.add_argument("--port", type=int, default=8093, help="Listen port")
    args = parser.parse_args()

    setup_logging()
    logging.info("Starting RFID Spools API on %s:%d", args.bind, args.port)

    server = ThreadingHTTPServer((args.bind, args.port), RequestHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        logging.info("RFID Spools API stopped")


if __name__ == "__main__":
    main()
