"""Spoolman REST client and the ``vendor → filament → spool`` upsert flow."""

import json
import logging
import urllib.error
import urllib.parse
import urllib.request

from .constants import (
    DEFAULT_DENSITY,
    MATERIAL_DENSITY,
    SPOOL_BULK_CACHE_TTL_S,
    SPOOL_BULK_HARD_CAP,
    SPOOL_BULK_PAGE_SIZE,
)
from .formatting import (
    argb_list_to_multi_hex,
    argb_to_color_hex,
    format_datetime_for_spoolman,
)


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
        # Try to extract the most useful part from a Pydantic error response
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


def spoolman_api_request_with_headers(base_url, method, path, body=None):
    """Like ``spoolman_api_request`` but also returns response headers as a
    case-insensitive dict. Used when the caller needs to read pagination
    headers (Spoolman exposes total counts via ``X-Total-Count``)."""
    url = base_url.rstrip('/') + path
    data = json.dumps(body).encode('utf-8') if body is not None else None
    headers_in = {}
    if data:
        headers_in['Content-Type'] = 'application/json'
    req = urllib.request.Request(url, data=data, method=method, headers=headers_in)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            payload = json.loads(resp.read())
            # urllib's response headers are an email.Message; lower-case keys
            # so callers can do ``hdrs.get('x-total-count')`` portably.
            response_headers = {k.lower(): v for k, v in resp.headers.items()}
            return payload, response_headers
    except urllib.error.HTTPError as e:
        logging.error("Spoolman API error %s %s -> HTTP %d", method, url, e.code)
        raise


def _safe_count(base_url, path):
    """Return the total record count for a Spoolman list endpoint, or ``None``
    if the call fails for any reason. Reads ``X-Total-Count`` from the
    response headers. Falls back to ``len(payload)`` if the header is missing."""
    try:
        payload, hdrs = spoolman_api_request_with_headers(
            base_url, 'GET', path + ('&' if '?' in path else '?') + 'limit=1'
        )
    except Exception:
        return None
    raw = hdrs.get('x-total-count')
    if raw is not None:
        try:
            return int(raw)
        except (TypeError, ValueError):
            pass
    if isinstance(payload, list):
        return len(payload)
    return None


def fetch_inventory_counts(base_url):
    """Return ``{'spools': N, 'filaments': N, 'vendors': N}`` for the Spoolman
    instance at ``base_url``. Each missing/failed count is ``None`` rather
    than raising — this is a status display, not a critical path."""
    return {
        'spools':    _safe_count(base_url, '/api/v1/spool'),
        'filaments': _safe_count(base_url, '/api/v1/filament'),
        'vendors':   _safe_count(base_url, '/api/v1/vendor'),
    }


# ── Spool browsing (used by the "write existing spool to blank tag" UI) ─────
# Strategy: fetch *all* spools in one request and let the UI search/sort
# client-side. This avoids Spoolman's per-field substring filters (which
# can't be combined into a real multi-field "q" search without breaking
# pagination) and gives instant in-memory filtering as the user types.

import threading
import time

_BULK_CACHE = {}            # {(base_url, include_archived): (timestamp, payload)}
_BULK_CACHE_LOCK = threading.Lock()


def invalidate_spool_cache():
    """Clear the bulk-spool cache. Called by ``sync_to_spoolman`` (and any
    other code path that mutates Spoolman from the printer) so the next
    picker open reflects the change immediately."""
    with _BULK_CACHE_LOCK:
        _BULK_CACHE.clear()


def _thin_spool(spool):
    """Project a Spoolman spool record down to the fields the picker UI needs.
    Tolerant of missing nested ``filament``/``vendor`` objects."""
    filament = spool.get('filament') or {}
    vendor = filament.get('vendor') or {}
    return {
        'id':           spool.get('id'),
        'filament_id':  filament.get('id'),
        'external_id':  filament.get('external_id'),
        'vendor':       vendor.get('name'),
        'material':     filament.get('material'),
        'name':         filament.get('name'),
        'color_hex':    filament.get('color_hex'),
        'weight_g':     filament.get('weight'),
        'remaining_g':  spool.get('remaining_weight'),
        'last_used':    spool.get('last_used'),
        'archived':     bool(spool.get('archived')),
    }


def list_all_spools(base_url, include_archived=False, force_refresh=False):
    """Return every spool from Spoolman as a single thin list. Pages through
    Spoolman internally in fixed-size chunks; results are cached for
    ``SPOOL_BULK_CACHE_TTL_S`` seconds keyed by ``(base_url, include_archived)``.

    Returns ``{'items': [...], 'count': N, 'truncated': bool, 'fetched_at': ts}``.
    """
    cache_key = (base_url.rstrip('/'), bool(include_archived))
    now = time.time()

    if not force_refresh:
        with _BULK_CACHE_LOCK:
            cached = _BULK_CACHE.get(cache_key)
        if cached and (now - cached[0]) < SPOOL_BULK_CACHE_TTL_S:
            return cached[1]

    items = []
    truncated = False
    offset = 0
    sort = 'filament.vendor.name:asc'

    while True:
        params = {
            'limit':  str(SPOOL_BULK_PAGE_SIZE),
            'offset': str(offset),
            'sort':   sort,
        }
        if include_archived:
            params['allow_archived'] = 'true'
        qs = urllib.parse.urlencode(params)
        page = spoolman_api_request(base_url, 'GET', '/api/v1/spool?' + qs)
        if not isinstance(page, list) or not page:
            break

        # Apply the hard cap before extending so the response stays bounded.
        room = SPOOL_BULK_HARD_CAP - len(items)
        if room <= 0:
            truncated = True
            break
        if len(page) > room:
            items.extend(_thin_spool(s) for s in page[:room])
            truncated = True
            break
        items.extend(_thin_spool(s) for s in page)

        if len(page) < SPOOL_BULK_PAGE_SIZE:
            break  # last page
        offset += SPOOL_BULK_PAGE_SIZE

    payload = {
        'items':      items,
        'count':      len(items),
        'truncated':  truncated,
        'fetched_at': now,
    }
    with _BULK_CACHE_LOCK:
        _BULK_CACHE[cache_key] = (now, payload)
    return payload


def get_spool(base_url, spool_id):
    """Fetch a single spool by ID. Returns the same thin shape as
    ``list_all_spools`` items, or ``None`` if the spool doesn't exist.
    Always bypasses the bulk cache. Re-raises non-404 HTTP errors."""
    try:
        sid = int(spool_id)
    except (TypeError, ValueError):
        return None
    if sid <= 0:
        return None
    try:
        spool = spoolman_api_request(
            base_url, 'GET', '/api/v1/spool/{}'.format(sid)
        )
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise
    return _thin_spool(spool) if spool else None


def _color_hex_to_rgb_int(hex_str):
    """Convert a Spoolman ``color_hex`` (``"RRGGBB"`` or ``"#RRGGBB"``) into
    the 0xRRGGBB int the frontend's ``rgb1`` field expects. Returns ``None``
    on invalid input."""
    if not isinstance(hex_str, str):
        return None
    s = hex_str.strip().lstrip('#')
    if len(s) != 6:
        return None
    try:
        return int(s, 16)
    except ValueError:
        return None


def _coerce_extra_value(raw):
    """Spoolman serializes ``extra`` field values as JSON strings (so
    ``"60"``, ``"\"some text\""``, etc.). Decode them best-effort; return the
    raw value if not JSON-decodable."""
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except (ValueError, TypeError):
            return raw
    return raw


def spool_to_tigertag_spec(spool, filament=None, vendor=None):
    """Project a full Spoolman spool record onto the editor's ``f``-shape
    payload. Pure function — no HTTP, no registry lookup (the frontend's
    ``_selectFromRegistry`` already handles ``(custom)`` semantics).

    ``spool`` is the Spoolman spool dict; ``filament`` and ``vendor`` may be
    passed explicitly or read from the nested ``spool['filament']`` /
    ``spool['filament']['vendor']`` structures.

    Field cascade rules:
    - **Color**: spool-level overrides win, then filament. (Spoolman's
      stock schema only has filament-level colors, but installs may add a
      spool-level ``extra.color_hex``; we honor that per the user's
      "spool wins" preference.)
    - **Temperatures**: Spoolman exposes single-valued
      ``settings_extruder_temp`` / ``settings_bed_temp``; we map them to
      both min and max so the editor pre-fills consistently.
    - **Drying / TD / modifiers**: read from filament ``extra``, which
      Spoolman serializes as JSON strings.
    - **Message**: defaults to ``"{vendor} {material}"`` truncated to
      28 bytes (the TigerTag message length).
    """
    spool = spool or {}
    if filament is None:
        filament = spool.get('filament') or {}
    if vendor is None:
        vendor = filament.get('vendor') or {}

    spool_extra = {k: _coerce_extra_value(v) for k, v in (spool.get('extra') or {}).items()}
    fil_extra = {k: _coerce_extra_value(v) for k, v in (filament.get('extra') or {}).items()}

    # Color: spool wins. Spoolman vanilla has no spool color, so this is
    # a courtesy hook for installs that store a spool-level ``color_hex``
    # in extras.
    color_hex = spool_extra.get('color_hex') or filament.get('color_hex')
    rgb_int = _color_hex_to_rgb_int(color_hex) if color_hex else None

    # Temps — Spoolman keeps single values; mirror to min/max.
    extruder = filament.get('settings_extruder_temp')
    bed = filament.get('settings_bed_temp')

    # Drying — typical Spoolman extra field names.
    drying_temp = fil_extra.get('drying_temp')
    drying_time = fil_extra.get('drying_time')
    td = fil_extra.get('td')

    modifiers_raw = fil_extra.get('modifiers')
    if isinstance(modifiers_raw, str):
        modifiers = [m.strip() for m in modifiers_raw.split(',') if m.strip()]
    elif isinstance(modifiers_raw, list):
        modifiers = [str(m) for m in modifiers_raw if m]
    else:
        modifiers = []

    vendor_name = vendor.get('name') or ''
    material = filament.get('material') or ''
    fil_name = filament.get('name') or ''
    # Message defaults to the filament's display name (most informative
    # for the user — e.g. "BronzeFill"), falling back to "{vendor} {material}"
    # only when the filament has no name. The on-tag message field is
    # 28 bytes UTF-8; truncate by bytes and decode with errors='ignore'
    # so we drop any trailing partial code point cleanly.
    msg_raw = fil_name.strip() or '{} {}'.format(vendor_name, material).strip()
    message = msg_raw.encode('utf-8')[:28].decode('utf-8', errors='ignore')

    return {
        'manufacturer':       vendor_name or None,
        'type':               material or None,
        'modifiers':          modifiers,
        'rgb1':               rgb_int,
        'colors':             None,
        'hotend_min_temp_c':  extruder,
        'hotend_max_temp_c':  extruder,
        'bed_temp_min_c':     bed,
        'bed_temp_max_c':     bed,
        'bed_temp_c':         bed,
        'diameter_mm':        filament.get('diameter'),
        'weight_grams':       filament.get('weight') or spool.get('initial_weight'),
        'drying_temp_c':      drying_temp,
        'drying_time_hours':  drying_time,
        'td':                 td,
        'manufacturing_date': fil_extra.get('mfg_date'),
        'message':            message or None,
        'unit':               'g',
        'product_type':       'Filament',
        # Source bookkeeping so the UI can show "Pre-filled from Spoolman #N"
        'source':             'spoolman',
        'source_spool_id':    spool.get('id'),
        'source_filament_id': filament.get('id'),
    }


def fetch_spool_with_relations(base_url, spool_id):
    """Fetch a spool plus its full filament and vendor records (Spoolman's
    list endpoint embeds these, but the by-ID endpoint may not). Returns
    ``(spool, filament, vendor)`` or ``(None, None, None)`` on 404."""
    spool = None
    try:
        sid = int(spool_id)
    except (TypeError, ValueError):
        return (None, None, None)
    try:
        spool = spoolman_api_request(
            base_url, 'GET', '/api/v1/spool/{}'.format(sid)
        )
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return (None, None, None)
        raise
    if not spool:
        return (None, None, None)

    filament = spool.get('filament') or {}
    vendor = filament.get('vendor') or {}
    # If the embedded objects look thin (no name, no material), fetch them
    # explicitly. Spoolman's spool endpoint normally embeds the full records,
    # so this is just a safety net.
    if filament.get('id') and not filament.get('material'):
        try:
            filament = spoolman_api_request(
                base_url, 'GET', '/api/v1/filament/{}'.format(filament['id'])
            ) or filament
            vendor = filament.get('vendor') or vendor
        except urllib.error.HTTPError:
            pass
    if vendor.get('id') and not vendor.get('name'):
        try:
            vendor = spoolman_api_request(
                base_url, 'GET', '/api/v1/vendor/{}'.format(vendor['id'])
            ) or vendor
        except urllib.error.HTTPError:
            pass

    return (spool, filament, vendor)


def resolve_display_fields(tag_event, _config=None):
    """Resolve display fields from a raw tag event.

    Tag fields map directly onto display fields; the only smoothing applied
    here is the bed-temp cascade for tags that carry only a single bed
    temperature (e.g. Snapmaker), so the UI never shows an empty min or max
    column when the other side is populated.

    The ``_config`` argument is unused and kept only for backward compat
    with older call sites.
    """
    filament = tag_event.get('filament') or {}

    def fget(key):
        v = filament.get(key)
        return v if v not in ('',) else None

    # UID: prefer scan.uid (TigerTag / generic RFID), fall back to CARD_UID
    uid_raw = (tag_event.get('scan') or {}).get('uid')
    if isinstance(uid_raw, list) and uid_raw:
        uid = ''.join('{:02X}'.format(b & 0xFF) for b in uid_raw)
    elif uid_raw:
        uid = str(uid_raw)
    else:
        card_uid = filament.get('CARD_UID') or filament.get('card_uid')
        if isinstance(card_uid, (list, tuple)) and card_uid:
            uid = ''.join('{:02X}'.format(b & 0xFF) for b in card_uid)
        elif card_uid:
            uid = str(card_uid)
        else:
            uid = None

    # Bed temps: upstream OpenRFID exposes the min as ``bed_temp_c`` and
    # the max as ``bed_temp_max_c``. For tags carrying only a single value,
    # mirror whichever side is set onto the other so the UI is never
    # half-empty.
    bed_min = fget('bed_temp_c')
    bed_max = fget('bed_temp_max_c')
    if bed_min in (None, '') and bed_max not in (None, ''):
        bed_min = bed_max
    elif bed_max in (None, '') and bed_min not in (None, ''):
        bed_max = bed_min

    return {
        'manufacturer':       fget('manufacturer'),
        'type':               fget('type'),
        'modifiers':          fget('modifiers'),
        'colors':             fget('colors'),
        'hotend_min_temp_c':  fget('hotend_min_temp_c'),
        'hotend_max_temp_c':  fget('hotend_max_temp_c'),
        'bed_temp_min_c':     bed_min,
        'bed_temp_max_c':     bed_max,
        'diameter_mm':        fget('diameter_mm'),
        'weight_grams':       fget('weight_grams'),
        'drying_temp_c':      fget('drying_temp_c'),
        'drying_time_hours':  fget('drying_time_hours'),
        'manufacturing_date': fget('manufacturing_date'),
        'td':                 fget('td'),
        'message':            fget('message'),
        'uid':                uid,
    }


def _resolve_density(density, material):
    """Pick a positive density value, falling back to the material lookup."""
    try:
        density_val = float(density) if density is not None else None
    except (TypeError, ValueError):
        density_val = None
    if not density_val or density_val <= 0:
        mat_key = str(material or '').upper().split()[0].split('-')[0] if material else ''
        density_val = MATERIAL_DENSITY.get(mat_key, DEFAULT_DENSITY)
    return density_val


def _int_pos(val):
    """Return ``int(val)`` if > 0, else ``None``. Handles strings like '210.0'."""
    try:
        v = int(float(str(val)))
        return v if v > 0 else None
    except (TypeError, ValueError):
        return None


def _float_pos(val):
    """Return ``float(val)`` if > 0, else ``None``."""
    try:
        v = float(val)
        return v if v > 0 else None
    except (TypeError, ValueError):
        return None


_EXTRA_FIELD_MAP = [
    ('max_extruder_temp', 'hotend_max_temp_c'),
    ('max_bed_temp',      'bed_temp_max_c'),
    ('drying_temp',       'drying_temp_c'),
    ('drying_time',       'drying_time_hours'),
    ('td',                'td'),
    ('mfg_date',          'manufacturing_date'),
    ('modifiers',         'modifiers'),
]
_INT_EXTRA = {'max_extruder_temp', 'max_bed_temp', 'drying_temp'}
_STR_EXTRA = {'mfg_date', 'modifiers'}  # text/datetime — must be JSON strings


def _build_extra_payload(fields, extra_fields):
    """Translate the ``spoolman_extra_fields`` config + tag fields into the
    JSON-encoded ``extra`` dict Spoolman expects."""
    if not extra_fields:
        return None
    extra = {}
    for spoolman_key, src_key in _EXTRA_FIELD_MAP:
        if not extra_fields.get(spoolman_key):
            continue
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
        if spoolman_key in _INT_EXTRA:
            try:
                extra[spoolman_key] = str(int(float(str(val))))
            except (TypeError, ValueError):
                continue
        elif spoolman_key in _STR_EXTRA:
            extra[spoolman_key] = json.dumps(str(val))
        else:
            extra[spoolman_key] = str(val)
    return extra or None


def _build_filament_payload(uid, fields, name, vendor_id, density):
    """Compose the Spoolman filament POST/PATCH body from resolved fields."""
    if not name:
        parts = [fields.get('type'), fields.get('manufacturer')]
        name = ' '.join(p for p in parts if p) or 'Unknown Filament'
    payload = {'external_id': uid, 'name': name}
    if vendor_id is not None:
        payload['vendor_id'] = vendor_id
    material = fields.get('type')
    if material:
        payload['material'] = material
    payload['density'] = _resolve_density(density, material)

    # Multi-color support: if more than one color, use multi_color_hexes
    colors_raw = fields.get('colors')
    multi_hex = argb_list_to_multi_hex(colors_raw)
    if multi_hex:
        payload['multi_color_hexes'] = multi_hex
    else:
        color_hex = argb_to_color_hex(colors_raw)
        if color_hex:
            payload['color_hex'] = color_hex

    v = _int_pos(fields.get('hotend_min_temp_c'))
    if v is not None:
        payload['settings_extruder_temp'] = v
    v = _int_pos(fields.get('bed_temp_min_c')) or _int_pos(fields.get('bed_temp_max_c'))
    if v is not None:
        payload['settings_bed_temp'] = v
    v = _float_pos(fields.get('diameter_mm'))
    if v is not None:
        payload['diameter'] = v

    weight_grams_raw = fields.get('weight_grams')
    try:
        weight_grams = float(weight_grams_raw) if weight_grams_raw is not None else None
    except (TypeError, ValueError):
        weight_grams = None
    if weight_grams and weight_grams > 0:
        payload['weight'] = weight_grams

    return payload, weight_grams


def _upsert_vendor(base_url, manufacturer):
    """Return the Spoolman vendor id for ``manufacturer``, creating it if needed."""
    if not manufacturer:
        return None
    existing = spoolman_api_request(
        base_url, 'GET',
        '/api/v1/vendor?name=' + urllib.parse.quote(str(manufacturer))
    )
    if existing:
        return existing[0]['id']
    new_vendor = spoolman_api_request(
        base_url, 'POST', '/api/v1/vendor', {'name': manufacturer}
    )
    return new_vendor['id']


def _upsert_filament(base_url, uid, payload, override_filament_id):
    """Patch an existing or POST a new filament record. Returns
    ``(filament_id, created)``."""
    if override_filament_id is not None:
        payload['external_id'] = uid
        spoolman_api_request(
            base_url, 'PATCH', '/api/v1/filament/{}'.format(override_filament_id), payload
        )
        return override_filament_id, False
    uid_encoded = urllib.parse.quote(str(uid))
    existing = spoolman_api_request(
        base_url, 'GET', '/api/v1/filament?external_id=' + uid_encoded
    )
    if existing:
        fid = existing[0]['id']
        spoolman_api_request(
            base_url, 'PATCH', '/api/v1/filament/{}'.format(fid), payload
        )
        return fid, False
    payload['external_id'] = uid
    new_filament = spoolman_api_request(
        base_url, 'POST', '/api/v1/filament', payload
    )
    return new_filament['id'], True


def _upsert_spool(base_url, filament_id, weight_grams):
    """Patch the first existing spool for the filament or POST a new one.
    Returns ``(spool_id, created)``."""
    payload = {'filament_id': filament_id}
    if weight_grams and weight_grams > 0:
        payload['initial_weight'] = weight_grams
    existing = spoolman_api_request(
        base_url, 'GET', '/api/v1/spool?filament_id={}'.format(filament_id)
    )
    if existing:
        spool_id = existing[0]['id']
        if weight_grams is not None:
            spoolman_api_request(
                base_url, 'PATCH', '/api/v1/spool/{}'.format(spool_id),
                {'initial_weight': float(weight_grams)}
            )
        return spool_id, False
    new_spool = spoolman_api_request(
        base_url, 'POST', '/api/v1/spool', payload
    )
    return new_spool['id'], True


def sync_to_spoolman(base_url, fields, name, extra_fields=None,
                     override_filament_id=None, density=None):
    """Upsert vendor → filament → spool in Spoolman. Returns a result dict.

    Raises :class:`ValueError` if the tag has no UID, and propagates
    :class:`urllib.error.HTTPError` / :class:`OSError` from the underlying
    Spoolman calls.
    """
    uid = fields.get('uid')
    if not uid:
        raise ValueError("tag has no UID")
    uid = str(uid)  # already formatted as hex string by resolve_display_fields

    vendor_id = _upsert_vendor(base_url, fields.get('manufacturer'))
    filament_payload, weight_grams = _build_filament_payload(
        uid, fields, name, vendor_id, density
    )
    extra_payload = _build_extra_payload(fields, extra_fields)
    if extra_payload:
        filament_payload['extra'] = extra_payload

    filament_id, created_filament = _upsert_filament(
        base_url, uid, filament_payload, override_filament_id
    )
    spool_id, created_spool = _upsert_spool(base_url, filament_id, weight_grams)

    # Any write to Spoolman invalidates the bulk-spool cache so the picker
    # reflects the new state on its next open.
    invalidate_spool_cache()

    return {
        'filament_id': filament_id,
        'spool_id': spool_id,
        'created_filament': created_filament,
        'created_spool': created_spool,
        'status': 'ok',
    }
