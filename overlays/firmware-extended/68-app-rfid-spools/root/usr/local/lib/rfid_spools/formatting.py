"""Color and date formatting helpers used during Spoolman sync."""


def argb_to_color_hex(val):
    """Convert an ARGB integer (or first element of a list) to RRGGBB hex.

    Returns the 6-character upper-case hex string without a leading ``#``,
    or ``None`` if the value cannot be interpreted.
    """
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
    """Convert a list of 2+ ARGB ints into Spoolman's ``multi_color_hexes``
    comma-separated RRGGBB string. Returns ``None`` for shorter lists."""
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
    """Convert common date formats to ISO 8601 datetime ``YYYY-MM-DDTHH:MM:SS``.

    Returns ``None`` if the input is empty or recognized as a sentinel
    (``19700101``, ``0001-01-01``, ``NONE``, ``0``).
    """
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
