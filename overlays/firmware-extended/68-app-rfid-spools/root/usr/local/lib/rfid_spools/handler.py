"""HTTP request handler — routes to the rest of the package.

Routes are kept as a flat ``if/elif`` chain inside :meth:`do_GET` and
:meth:`do_POST` to mirror the original implementation. Helpers live in
the rest of the package so the handler is purely about transport.
"""

import base64
import json
import logging
import time
import urllib.error
import urllib.parse
from http.server import BaseHTTPRequestHandler

from .config import load_config, save_config
from .constants import MAX_BODY_SIZE, MAX_CHANNELS
from .discovery import lan_sweep_for_spoolman, probe_spoolman
from . import moonraker
from .runtime import event_bus, store, sync_state
from .spoolman import (
    resolve_display_fields,
    spoolman_api_request,
    sync_to_spoolman,
)
from .tigertag import (
    encode_tigertag,
    load_tigertag_registry,
    write_ntag215_payload,
)


_ERR_INVALID_JSON = {"error": "invalid json"}
_ERR_BODY_TOO_LARGE = {"error": "body too large"}
_ERR_NOT_FOUND = {"error": "not found"}
_ERR_INVALID_CHANNEL = {"error": "invalid channel"}
_ERR_MISSING_CHANNEL_PARAM = {"error": "missing channel parameter"}
_ERR_SPOOLMAN_NOT_CONFIGURED = {"error": "spoolman_url not configured"}
_ERR_SPOOLMAN_QUERY_FAILED = {"error": "failed to query spoolman"}


def _format_uid(uid_raw):
    """Format an OpenRFID scan.uid (list[int] or str) into upper-case hex."""
    if isinstance(uid_raw, list) and uid_raw:
        return ''.join('{:02X}'.format(b & 0xFF) for b in uid_raw)
    if uid_raw:
        return str(uid_raw)
    return None


class RequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the RFID Spools API."""

    # ── Plumbing ─────────────────────────────────────────────────────────────
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

    # ── GET ──────────────────────────────────────────────────────────────────
    def do_GET(self):
        if self.path == "/api/health":
            self._send_json(200, {"status": "ok"})

        elif self.path == "/api/channels":
            self._handle_channels()

        elif self.path == "/api/config":
            self._send_json(200, load_config())

        elif self.path == "/api/spoolman-status":
            self._handle_spoolman_status()

        elif self.path.startswith("/api/spoolman-ping"):
            self._handle_spoolman_ping()

        elif self.path.startswith("/api/spoolman-discover"):
            self._handle_spoolman_discover()

        elif self.path.startswith("/api/spoolman-extra-fields-status"):
            self._handle_spoolman_extra_fields_status()

        elif self.path.startswith("/api/spoolman-candidates"):
            self._handle_spoolman_candidates()

        elif self.path.startswith("/api/spoolman-filament"):
            self._handle_spoolman_filament()

        elif self.path == "/api/tigertag/registry":
            self._handle_tigertag_registry()

        elif self.path == "/api/events":
            self._handle_events_sse()
            return

        else:
            self._send_json(404, _ERR_NOT_FOUND)

    # ── POST ─────────────────────────────────────────────────────────────────
    def do_POST(self):
        if self.path == "/api/tag-event":
            self._handle_tag_event()

        elif self.path == "/api/config":
            self._handle_config_post()

        elif self.path == "/api/scan":
            self._handle_scan()

        elif self.path == "/api/tigertag/encode-preview":
            self._handle_encode_preview()

        elif self.path == "/api/write":
            self._handle_write()

        elif self.path == "/api/clear":
            self._handle_clear()

        elif self.path.startswith("/api/spoolman-sync") and not self.path.startswith("/api/spoolman-sync-all"):
            self._handle_spoolman_sync()

        elif self.path.startswith("/api/spoolman-register-extra-fields"):
            self._handle_spoolman_register_extra_fields()

        elif self.path.startswith("/api/spoolman-sync-all"):
            self._handle_spoolman_sync_all()

        else:
            self._send_json(404, _ERR_NOT_FOUND)

    def do_PUT(self):
        if self.path == "/api/config":
            return self.do_POST()
        self._send_json(404, _ERR_NOT_FOUND)

    # ── Channel listing ──────────────────────────────────────────────────────
    def _handle_channels(self):
        """Merge Moonraker filament_detect with stored OpenRFID data."""
        mr = moonraker.query_filament_detect()
        filament_detect = {}
        if mr and "result" in mr:
            status = mr["result"].get("status", {})
            filament_detect = status.get("filament_detect", {})

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
                current_uid = _format_uid((tag.get('scan') or {}).get('uid'))
                if current_uid:
                    sync_state.clear_if_uid_changed(ch, current_uid)
            channels.append({
                "channel": ch,
                "moonraker": mk if isinstance(mk, dict) else {},
                "tag": tag,
                "spoolman_sync": sync_state.get(ch),
            })

        self._send_json(200, {"channels": channels})

    # ── Spoolman discovery / probing ─────────────────────────────────────────
    def _handle_spoolman_status(self):
        config = load_config()
        spoolman_url = config.get('spoolman_url', '').rstrip('/')
        if not spoolman_url:
            self._send_json(200, {"configured": False})
            return
        ok = probe_spoolman(spoolman_url)
        self._send_json(200, {"configured": True, "ok": ok})

    def _handle_spoolman_ping(self):
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

    def _handle_spoolman_discover(self):
        candidates = []
        seen = set()

        mk_url = moonraker.query_spoolman_url()
        if mk_url and mk_url not in seen:
            seen.add(mk_url)
            if probe_spoolman(mk_url):
                candidates.append(mk_url)

        for probe_url in ("http://localhost:7912", "http://127.0.0.1:7912"):
            if probe_url not in seen:
                seen.add(probe_url)
                if probe_spoolman(probe_url):
                    candidates.append(probe_url)

        # LAN sweep — the Snapmaker rootfs has no mDNS resolver, so
        # `spoolman.local` cannot work. Scan the local /24 on port 7912
        # and confirm any TCP-open host actually serves Spoolman's API.
        for url in lan_sweep_for_spoolman():
            if url not in seen:
                seen.add(url)
                candidates.append(url)

        self._send_json(200, {"candidates": candidates})

    def _handle_spoolman_extra_fields_status(self):
        config = load_config()
        spoolman_url = config.get('spoolman_url', '').rstrip('/')
        if not spoolman_url:
            self._send_json(400, _ERR_SPOOLMAN_NOT_CONFIGURED)
            return
        try:
            existing = spoolman_api_request(spoolman_url, 'GET', '/api/v1/field/filament') or []
            registered = {f['key'] for f in existing}
            known_keys = ['max_extruder_temp', 'max_bed_temp', 'drying_temp',
                          'drying_time', 'td', 'mfg_date', 'modifiers']
            self._send_json(200, {"fields": {k: k in registered for k in known_keys}})
        except Exception:
            logging.exception("Extra fields status error")
            self._send_json(502, _ERR_SPOOLMAN_QUERY_FAILED)

    def _handle_spoolman_candidates(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        channel_str = params.get('channel', [None])[0]
        if channel_str is None:
            self._send_json(400, _ERR_MISSING_CHANNEL_PARAM)
            return
        try:
            channel = int(channel_str)
        except (ValueError, TypeError):
            self._send_json(400, _ERR_INVALID_CHANNEL)
            return

        config = load_config()
        spoolman_url = config.get('spoolman_url', '').rstrip('/')
        if not spoolman_url:
            self._send_json(400, _ERR_SPOOLMAN_NOT_CONFIGURED)
            return

        tag_event = store.get(channel)
        if not tag_event or not tag_event.get('filament'):
            self._send_json(404, {"error": "no tag data for channel"})
            return

        fields = resolve_display_fields(tag_event)
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
            self._send_json(502, _ERR_SPOOLMAN_QUERY_FAILED)

    def _handle_spoolman_filament(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        channel_str = params.get('channel', [None])[0]
        if channel_str is None:
            self._send_json(400, _ERR_MISSING_CHANNEL_PARAM)
            return
        try:
            channel = int(channel_str)
        except (ValueError, TypeError):
            self._send_json(400, _ERR_INVALID_CHANNEL)
            return

        config = load_config()
        spoolman_url = config.get('spoolman_url', '').rstrip('/')
        if not spoolman_url:
            self._send_json(400, _ERR_SPOOLMAN_NOT_CONFIGURED)
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
            self._send_json(502, _ERR_SPOOLMAN_QUERY_FAILED)

    # ── TigerTag ─────────────────────────────────────────────────────────────
    def _handle_tigertag_registry(self):
        try:
            reg = load_tigertag_registry()
            self._send_json(200, {
                "materials":  reg.get("materials", []),
                "brands":     reg.get("brands", []),
                "aspects":    reg.get("aspects", []),
                "diameters":  reg.get("diameters", []),
                "units":      reg.get("units", []),
                "types":      reg.get("types", []),
            })
        except Exception:
            logging.exception("tigertag registry load failed")
            self._send_json(500, {"error": "failed to load tigertag registry"})

    def _handle_encode_preview(self):
        body = self._read_body()
        try:
            spec = json.loads(body) if body else {}
            if not isinstance(spec, dict):
                raise ValueError("spec must be a JSON object")
        except (json.JSONDecodeError, ValueError) as e:
            self._send_json(400, {"error": "invalid json: " + str(e)})
            return
        try:
            payload = encode_tigertag(spec)
        except Exception as e:
            logging.exception("tigertag encode failed")
            self._send_json(500, {"error": "encode failed: " + str(e)})
            return
        self._send_json(200, {
            "bytes_len": len(payload),
            "hex":       payload.hex(),
            "base64":    base64.b64encode(payload).decode("ascii"),
        })

    def _handle_write(self):
        """``{"channel": int, "spec": {...}}`` → encode + submit via OpenRFID."""
        body = self._read_body()
        try:
            req_data = json.loads(body) if body else {}
            channel = int(req_data.get("channel"))
            spec = req_data.get("spec", {})
            if not isinstance(spec, dict):
                raise ValueError("spec must be an object")
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            self._send_json(400, {"error": "invalid request: " + str(e)})
            return
        if channel < 0 or channel >= MAX_CHANNELS:
            self._send_json(400, {"error": "channel out of range"})
            return
        try:
            payload = encode_tigertag(spec)
            logging.info("Writing TigerTag to channel %d (%d bytes)", channel, len(payload))
            result = write_ntag215_payload(channel, payload)
        except Exception as e:
            logging.exception("write failed")
            self._send_json(500, {"state": "error", "message": str(e)})
            return

        status = 200 if result.get("state") == "success" else 502
        self._send_json(status, result)

    def _handle_clear(self):
        """``{"channel": int}`` → erase the user-data area (96 zero bytes)."""
        body = self._read_body()
        try:
            req_data = json.loads(body) if body else {}
            channel = int(req_data.get("channel"))
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            self._send_json(400, {"error": "invalid request: " + str(e)})
            return
        if channel < 0 or channel >= MAX_CHANNELS:
            self._send_json(400, {"error": "channel out of range"})
            return
        try:
            payload = bytes(96)
            logging.info("Clearing tag on channel %d (%d zero bytes)", channel, len(payload))
            result = write_ntag215_payload(channel, payload)
        except Exception as e:
            logging.exception("clear failed")
            self._send_json(500, {"state": "error", "message": str(e)})
            return

        status = 200 if result.get("state") == "success" else 502
        self._send_json(status, result)

    # ── Tag events / scan / config ───────────────────────────────────────────
    def _handle_tag_event(self):
        body = self._read_body()
        if body is None:
            self._send_json(413, _ERR_BODY_TOO_LARGE)
            return
        try:
            data = json.loads(body)
        except (json.JSONDecodeError, ValueError):
            self._send_json(400, _ERR_INVALID_JSON)
            return

        channel = data.get("channel")
        if channel is None:
            channel = (data.get("reader") or {}).get("slot")

        if channel is None:
            self._send_json(400, {"error": "missing channel"})
            return

        try:
            channel = int(channel)
        except (TypeError, ValueError):
            self._send_json(400, _ERR_INVALID_CHANNEL)
            return

        event = data.get("event", "tag_read")
        if event == "tag_not_present":
            store.update(channel, {"event": event, "tag": None})
            event_bus.publish("tag-removed", {"channel": channel})
        elif event == "tag_parse_error":
            # Tag is physically present (UID known) but no processor parsed it.
            # Keep the slot populated with the same shape as tag_read so the
            # UI can offer to initialize/write a blank or unrecognized tag.
            store.update(channel, {
                "event": event,
                "channel": channel,
                "reader": data.get("reader") or {},
                "scan": data.get("scan") or {},
                "filament": None,
                "unrecognized": True,
            })
            event_bus.publish("tag-event", {"channel": channel})
        else:
            store.update(channel, data)
            event_bus.publish("tag-event", {"channel": channel})

        self._send_json(200, {"status": "ok"})

    def _handle_config_post(self):
        body = self._read_body()
        if body is None:
            self._send_json(413, _ERR_BODY_TOO_LARGE)
            return
        try:
            data = json.loads(body)
        except (json.JSONDecodeError, ValueError):
            self._send_json(400, _ERR_INVALID_JSON)
            return
        config = load_config()
        config.update(data)
        save_config(config)
        self._send_json(200, config)

    def _handle_scan(self):
        """Trigger ``FILAMENT_DT_UPDATE`` per channel via Moonraker."""
        body = self._read_body()  # optional {"channels": [0,1,2,3]}
        channels = list(range(MAX_CHANNELS))
        if body:
            try:
                req_data = json.loads(body)
                if isinstance(req_data.get("channels"), list):
                    channels = [int(c) for c in req_data["channels"]
                                if 0 <= int(c) < MAX_CHANNELS]
            except (json.JSONDecodeError, ValueError, TypeError):
                pass

        errors = []
        for ch in channels:
            try:
                moonraker.gcode("FILAMENT_DT_UPDATE CHANNEL={}".format(ch))
                logging.info("Triggered RFID scan for channel %d", ch)
            except (urllib.error.URLError, OSError) as e:
                logging.warning("Scan trigger failed for channel %d: %s", ch, e)
                errors.append(ch)

        if errors:
            self._send_json(500, {"status": "partial", "failed_channels": errors})
        else:
            self._send_json(200, {"status": "ok", "channels": channels})

    # ── Spoolman sync ────────────────────────────────────────────────────────
    def _handle_spoolman_sync(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        channel_str = params.get('channel', [None])[0]
        if channel_str is None:
            self._send_json(400, _ERR_MISSING_CHANNEL_PARAM)
            return
        try:
            channel = int(channel_str)
        except (ValueError, TypeError):
            self._send_json(400, _ERR_INVALID_CHANNEL)
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
            self._send_json(400, _ERR_SPOOLMAN_NOT_CONFIGURED)
            return

        tag_event = store.get(channel)
        if not tag_event or not tag_event.get('filament'):
            self._send_json(404, {"error": "no tag data for channel"})
            return

        fields = resolve_display_fields(tag_event)
        extra_fields = config.get('spoolman_extra_fields', {})
        try:
            result = sync_to_spoolman(
                spoolman_url, fields, name,
                extra_fields=extra_fields,
                override_filament_id=override_filament_id,
                density=density,
            )
            sync_state.set(channel, result['filament_id'], result['spool_id'], fields.get('uid'))
            self._send_json(200, result)
        except ValueError as e:
            self._send_json(400, {"error": str(e)})
        except urllib.error.HTTPError as e:
            msg = str(e.reason)
            if e.code == 422:
                msg = ('Spoolman rejected the data (422) — ' + msg
                       + '. If extra fields are included, register them first in Config.')
            elif e.code == 404:
                msg = 'Spoolman endpoint not found (404) — check Spoolman version.'
            self._send_json(e.code if e.code in (400, 422, 404) else 502, {"error": msg})
        except (urllib.error.URLError, OSError) as e:
            logging.error("Spoolman sync 502: url=%s error=%s", spoolman_url, e)
            self._send_json(502, {"error": "spoolman request failed: " + str(e)})
        except Exception:
            logging.exception("Spoolman sync error")
            self._send_json(500, {"error": "internal error"})

    def _handle_spoolman_register_extra_fields(self):
        config = load_config()
        spoolman_url = config.get('spoolman_url', '').rstrip('/')
        if not spoolman_url:
            self._send_json(400, _ERR_SPOOLMAN_NOT_CONFIGURED)
            return
        field_defs = [
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
        for key, name, ftype, unit in field_defs:
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
        self._send_json(200, {
            "registered": registered,
            "already_existed": already_existed,
            "errors": errors,
        })

    def _handle_spoolman_sync_all(self):
        config = load_config()
        spoolman_url = config.get('spoolman_url', '').rstrip('/')
        if not spoolman_url:
            self._send_json(400, _ERR_SPOOLMAN_NOT_CONFIGURED)
            return
        extra_fields = config.get('spoolman_extra_fields', {})
        synced = []
        errors = []
        for ch in range(MAX_CHANNELS):
            tag_event = store.get(ch)
            if not tag_event or not tag_event.get('filament'):
                continue
            fields = resolve_display_fields(tag_event)
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

    # ── SSE event stream ─────────────────────────────────────────────────────
    def _handle_events_sse(self):
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
            last_ping = time.monotonic()
            while True:
                time.sleep(0.2)
                msgs = q[:]
                del q[:]
                for m in msgs:
                    self.wfile.write(m.encode())
                if msgs:
                    self.wfile.flush()
                    last_ping = time.monotonic()
                    continue
                # Periodic keepalive comment so nginx (and any other proxy
                # in front of us) does not close an idle SSE connection at
                # its read-timeout.
                if time.monotonic() - last_ping >= 15.0:
                    self.wfile.write(b': ping\n\n')
                    self.wfile.flush()
                    last_ping = time.monotonic()
        except OSError:
            pass
        finally:
            event_bus.unsubscribe(q)
