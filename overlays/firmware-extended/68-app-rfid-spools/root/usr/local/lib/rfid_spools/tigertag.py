"""TigerTag registry loading, 96-byte payload encoder, and OpenRFID write.

The encoder follows the byte layout in the upstream OpenRFID parser
(``openrfid/tag/tigertag/constants.py``). It is *not* identical to the
official TigerTag spec.
"""

import base64
import json
import logging
import os
import threading
import time
import urllib.error
import urllib.request

from .constants import (
    OPENRFID_TIGERTAG_DB_DIR,
    OPENRFID_WRITE_URL,
    TIGERTAG_EPOCH_OFFSET,
    TIGERTAG_TAG_ID,
    TIGERTAG_USER_DATA_LEN,
)


# ── Database / registry ──────────────────────────────────────────────────────
# Loaded lazily by :func:`load_tigertag_registry`. Each entry is a dict
# ``{label_lower: id}`` plus the original list under the descriptive key for
# the UI.
_registry_cache = None
_registry_lock = threading.Lock()


def _load_db_file(name):
    """Load one TigerTag database JSON file as a list of records, or ``[]``."""
    path = os.path.join(OPENRFID_TIGERTAG_DB_DIR, name)
    try:
        with open(path, "r") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError) as e:
        logging.warning("TigerTag DB %s load failed: %s", name, e)
        return []


def _build_label_index(records, label_key="label"):
    """Build ``{label_lower: id}`` over a list of ``{id, label, ...}`` records.

    Falls back to the ``name`` key when ``label`` is missing — TigerTag's
    ``id_brand.json`` uses ``name`` instead of ``label``.
    """
    out = {}
    for r in records:
        if not isinstance(r, dict):
            continue
        rid = r.get("id")
        lab = r.get(label_key)
        if not isinstance(lab, str):
            lab = r.get("name")
        if rid is None or not isinstance(lab, str):
            continue
        out[lab.strip().lower()] = int(rid)
    return out


def _normalize_records(records):
    """Ensure every record has a ``label`` field for UI display."""
    out = []
    for r in records:
        if not isinstance(r, dict):
            continue
        if "label" not in r and isinstance(r.get("name"), str):
            r = dict(r)
            r["label"] = r["name"]
        out.append(r)
    return out


def load_tigertag_registry():
    """Lazy-load TigerTag database files into a registry of records + indexes."""
    global _registry_cache
    with _registry_lock:
        if _registry_cache is not None:
            return _registry_cache

        materials = _normalize_records(_load_db_file("id_material.json"))
        brands = _normalize_records(_load_db_file("id_brand.json"))
        aspects = _normalize_records(_load_db_file("id_aspect.json"))
        diameters = _normalize_records(_load_db_file("id_diameter.json"))
        units = _normalize_records(_load_db_file("id_measure_unit.json"))
        types = _normalize_records(_load_db_file("id_type.json"))

        _registry_cache = {
            "materials": materials,
            "brands": brands,
            "aspects": aspects,
            "diameters": diameters,
            "units": units,
            "types": types,
            # internal lookup tables (label.lower() → id)
            "_idx_material": _build_label_index(materials),
            "_idx_brand": _build_label_index(brands),
            "_idx_aspect": _build_label_index(aspects),
            "_idx_diameter": _build_label_index(diameters),
            "_idx_unit": _build_label_index(units),
            "_idx_type": _build_label_index(types),
        }
        return _registry_cache


def _resolve_id(registry, kind, value, default=0):
    """Resolve a label / numeric id / ``None`` into the registry id."""
    if value is None or value == "":
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        s = value.strip()
        if s.isdigit():
            return int(s)
        idx = registry.get("_idx_" + kind, {})
        return idx.get(s.lower(), default)
    return default


def _utf8_message_bytes(text, max_bytes=28):
    """Encode ``text`` to UTF-8, truncated to ``max_bytes`` without splitting
    a codepoint, right-padded with zeros."""
    if not text:
        return b'\x00' * max_bytes
    enc = str(text).encode("utf-8")
    if len(enc) > max_bytes:
        end = max_bytes
        while end > 0 and (enc[end] & 0xC0) == 0x80:
            end -= 1
        enc = enc[:end]
    return enc + b'\x00' * (max_bytes - len(enc))


def _hex_to_rgba(value, default=(0, 0, 0, 0xFF)):
    """Parse ``#RRGGBB`` / ``RRGGBB`` / ``RRGGBBAA`` to ``(R, G, B, A)``."""
    if isinstance(value, (list, tuple)) and len(value) >= 3:
        r, g, b = int(value[0]) & 0xFF, int(value[1]) & 0xFF, int(value[2]) & 0xFF
        a = int(value[3]) & 0xFF if len(value) >= 4 else 0xFF
        return (r, g, b, a)
    if not isinstance(value, str):
        return default
    s = value.strip().lstrip('#')
    if len(s) == 6:
        try:
            return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16), 0xFF)
        except ValueError:
            return default
    if len(s) == 8:
        try:
            return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16), int(s[6:8], 16))
        except ValueError:
            return default
    return default


def _resolve_mfg_timestamp(mfg_raw):
    """Convert a manufacturing-date spec into a TigerTag timestamp (seconds
    since 2000-01-01). Falls back to ``now`` on parse failure."""
    if isinstance(mfg_raw, (int, float)):
        return int(mfg_raw)
    if isinstance(mfg_raw, str) and mfg_raw.strip():
        s = mfg_raw.strip()
        for fmt in ('%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
            try:
                return int(time.mktime(time.strptime(s[:len(fmt) + 4], fmt))) - TIGERTAG_EPOCH_OFFSET
            except (ValueError, OverflowError):
                continue
    return int(time.time()) - TIGERTAG_EPOCH_OFFSET


def encode_tigertag(spec):
    """Encode a TigerTag spec dict into a 96-byte user-data block.

    Layout follows the upstream OpenRFID parser. All multi-byte fields are
    big-endian.

    Spec fields (all optional unless noted)::

      material:           str label or numeric id   (default 0)
      brand:              str label or numeric id   (default 0)
      aspect_1:           str label or numeric id   (default 0)
      aspect_2:           str label or numeric id   (default 0)
      type:               str label or numeric id   (default 0)
      diameter:           str label or numeric id   (e.g. "1.75mm")
      product_id:         int 0..0xFFFFFFFF         (default 0)
      color:              "#RRGGBB" or [r,g,b,a]    (default opaque black)
      weight_g:           int 0..16777215           (3-byte BE)
      unit:               str label or numeric id   (default 0)
      temp_min_c:         int 0..65535
      temp_max_c:         int 0..65535
      dry_temp_c:         int 0..255
      dry_time_h:         int 0..255
      bed_temp_min_c:     int 0..255
      bed_temp_max_c:     int 0..255
      td_mm:              float 0..6553.5           (encoded as round(mm * 10))
      td:                 int 0..65535              (legacy raw, ignored if td_mm)
      manufacturing_date: ISO date/datetime str or epoch number
      message:            str up to 28 UTF-8 bytes  (written at OFF_METADATA)
    """
    registry = load_tigertag_registry()
    if not isinstance(spec, dict):
        spec = {}

    buf = bytearray(TIGERTAG_USER_DATA_LEN)

    # Header / IDs
    buf[0:4] = TIGERTAG_TAG_ID.to_bytes(4, 'big')                # OFF_TAG_ID
    pid = int(spec.get('product_id', 0)) & 0xFFFFFFFF
    buf[4:8] = pid.to_bytes(4, 'big')                            # OFF_PRODUCT_ID
    mid = _resolve_id(registry, 'material', spec.get('material'))
    buf[8:10] = (mid & 0xFFFF).to_bytes(2, 'big')                # OFF_MATERIAL_ID
    buf[10] = _resolve_id(registry, 'aspect', spec.get('aspect_1')) & 0xFF
    buf[11] = _resolve_id(registry, 'aspect', spec.get('aspect_2')) & 0xFF
    buf[12] = _resolve_id(registry, 'type', spec.get('type')) & 0xFF
    buf[13] = _resolve_id(registry, 'diameter', spec.get('diameter')) & 0xFF
    bid = _resolve_id(registry, 'brand', spec.get('brand'))
    buf[14:16] = (bid & 0xFFFF).to_bytes(2, 'big')               # OFF_BRAND_ID

    # Color (RGBA)
    r, g, b, a = _hex_to_rgba(spec.get('color'))
    buf[16] = r
    buf[17] = g
    buf[18] = b
    buf[19] = a

    # Weight (3-byte BE) + unit
    weight = max(0, min(int(spec.get('weight_g', 0) or 0), 0xFFFFFF))
    buf[20] = (weight >> 16) & 0xFF
    buf[21] = (weight >> 8) & 0xFF
    buf[22] = weight & 0xFF
    buf[23] = _resolve_id(registry, 'unit', spec.get('unit')) & 0xFF

    # Temps
    tmin = max(0, min(int(spec.get('temp_min_c', 0) or 0), 0xFFFF))
    tmax = max(0, min(int(spec.get('temp_max_c', 0) or 0), 0xFFFF))
    buf[24:26] = tmin.to_bytes(2, 'big')
    buf[26:28] = tmax.to_bytes(2, 'big')
    buf[28] = max(0, min(int(spec.get('dry_temp_c', 0) or 0), 0xFF))
    buf[29] = max(0, min(int(spec.get('dry_time_h', 0) or 0), 0xFF))
    buf[30] = max(0, min(int(spec.get('bed_temp_min_c', 0) or 0), 0xFF))
    buf[31] = max(0, min(int(spec.get('bed_temp_max_c', 0) or 0), 0xFF))

    # Manufacturing timestamp (seconds since 2000-01-01)
    ts = max(0, min(_resolve_mfg_timestamp(spec.get('manufacturing_date')), 0xFFFFFFFF))
    buf[32:36] = ts.to_bytes(4, 'big')

    # bytes 36..43 reserved — leave zero

    # TD (transmission distance) at OFF_TD = 44, value is mm * 10
    if 'td_mm' in spec and spec.get('td_mm') is not None:
        try:
            td = int(round(float(spec.get('td_mm') or 0) * 10))
        except (TypeError, ValueError):
            td = 0
    else:
        td = int(spec.get('td', 0) or 0)
    td = max(0, min(td, 0xFFFF))
    buf[44:46] = td.to_bytes(2, 'big')

    # bytes 46..47 reserved — leave zero
    # OFF_METADATA = 48: 28-byte UTF-8 message + 4 reserved bytes
    buf[48:48 + 28] = _utf8_message_bytes(spec.get('message'), max_bytes=28)
    # OFF_SIGNATURE = 80 (16 bytes) — write zeros; OpenRFID parser accepts.

    return bytes(buf)


def write_ntag215_payload(channel, payload, timeout=20.0):
    """Submit a write to the OpenRFID daemon and return a normalized status dict.

    The OpenRFID write extension takes the payload base64-encoded and writes
    it to the NTAG215 starting at page 4 (the user-data area).

    Returns one of::

      {"state": "success", "details": <openrfid result>}
      {"state": "error",   "message": <reason>, "details": <openrfid result>}
    """
    if not isinstance(payload, (bytes, bytearray)):
        raise TypeError("payload must be bytes")
    if len(payload) % 4 != 0:
        raise ValueError("payload length must be a multiple of 4")

    body = json.dumps({
        "slot":       int(channel),
        "data_b64":   base64.b64encode(bytes(payload)).decode("ascii"),
        "start_page": 4,
        "timeout":    max(1.0, timeout - 2.0),
    }).encode("utf-8")

    req = urllib.request.Request(
        OPENRFID_WRITE_URL, data=body, method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        try:
            data = json.loads(e.read())
        except Exception:
            return {"state": "error", "message": "http {}: {}".format(e.code, e.reason)}
    except urllib.error.URLError as e:
        return {"state": "error", "message": "openrfid not reachable: {}".format(e.reason)}
    except Exception as e:
        return {"state": "error", "message": "openrfid request failed: {}".format(e)}

    if data.get("ok"):
        return {"state": "success", "details": data}
    return {
        "state": "error",
        "message": data.get("error", "unknown error"),
        "details": data,
    }
