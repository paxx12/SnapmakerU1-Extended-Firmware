"""Spoolman REST client and the ``vendor → filament → spool`` upsert flow."""

import json
import logging
import urllib.error
import urllib.parse
import urllib.request

from .constants import DEFAULT_DENSITY, MATERIAL_DENSITY
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

    return {
        'filament_id': filament_id,
        'spool_id': spool_id,
        'created_filament': created_filament,
        'created_spool': created_spool,
        'status': 'ok',
    }
