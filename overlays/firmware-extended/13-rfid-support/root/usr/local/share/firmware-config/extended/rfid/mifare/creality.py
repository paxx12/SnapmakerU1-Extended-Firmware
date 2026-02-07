#!/usr/bin/env python3
"""
Creality Mifare Classic 1K filament tag plugin.

Reference implementation for parsing Creality filament tags.

Usage:
  creality.py auth <card-uid-hex>
  creality.py parse <hex-payload>

For auth: outputs JSON with key_a/key_b arrays (16 sectors, 6 bytes each hex).
For parse: outputs OpenSpool JSON on success (exit 0), exits non-zero on failure.
"""

import json
import sys

CREALITY_KEY_A = 'FFFFFFFFFFFF'
CREALITY_KEY_B = 'FFFFFFFFFFFF'

MATERIAL_TYPES = {
    0x00: 'PLA',
    0x01: 'ABS',
    0x02: 'PETG',
    0x03: 'TPU',
    0x04: 'PA',
    0x05: 'PC',
    0x06: 'ASA',
    0x07: 'PVA',
    0x08: 'HIPS',
    0x09: 'PLA+',
    0x0A: 'PLA-CF',
    0x0B: 'PA-CF',
    0x0C: 'PETG-CF',
}

def cmd_auth(card_uid_hex):
    """Return authentication keys for Creality tags."""
    keys = {
        'key_a': [CREALITY_KEY_A] * 16,
        'key_b': [CREALITY_KEY_B] * 16,
    }
    print(json.dumps(keys))
    return 0

def cmd_parse(hex_payload):
    """Parse Creality tag data and output OpenSpool JSON."""
    try:
        data = bytes.fromhex(hex_payload)
    except ValueError:
        return 1

    if len(data) < 1024:
        return 1

    vendor_bytes = data[16:32]
    vendor = vendor_bytes.rstrip(b'\x00').decode('utf-8', errors='replace').strip()
    if not vendor or vendor.lower() not in ('creality', 'ender', 'cr'):
        if not any(v in vendor.lower() for v in ('creality', 'ender', 'cr', 'hyper')):
            return 1

    material_type = data[64]
    color_r = data[65]
    color_g = data[66]
    color_b = data[67]

    min_temp = data[68] + 150 if data[68] > 0 else 0
    max_temp = data[69] + 150 if data[69] > 0 else 0
    bed_temp = data[70]

    weight_lo = data[72]
    weight_hi = data[73]
    weight = (weight_hi << 8) | weight_lo

    result = {
        'protocol': 'openspool',
        'version': '1.0',
        'brand': vendor if vendor else 'Creality',
        'type': MATERIAL_TYPES.get(material_type, 'PLA'),
        'color_hex': f'{color_r:02X}{color_g:02X}{color_b:02X}',
    }

    if min_temp > 0:
        result['min_temp'] = min_temp
    if max_temp > 0:
        result['max_temp'] = max_temp
    if bed_temp > 0:
        result['bed_temp'] = bed_temp
    if weight > 0:
        result['weight'] = weight

    print(json.dumps(result))
    return 0

def main():
    if len(sys.argv) < 3:
        return 1

    cmd = sys.argv[1]
    arg = sys.argv[2]

    if cmd == 'auth':
        return cmd_auth(arg)
    elif cmd == 'parse':
        return cmd_parse(arg)

    return 1

if __name__ == '__main__':
    sys.exit(main())
