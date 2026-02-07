#!/usr/bin/env python3
"""
OpenTag3D NDEF plugin for RFID filament tags.

Reference implementation for parsing OpenTag3D binary format.
https://opentag3d.info/spec

Usage: opentag3d.py <mime-type> <hex-payload> [mime-type2] [hex-payload2] ...

Outputs OpenSpool JSON on success (exit 0), exits non-zero on failure.
"""

import json
import struct
import sys

OPENTAG3D_MIME = 'application/opentag3d'
OPENTAG3D_CORE_SIZE = 0x70

def read_utf8(data, offset, length):
    if offset + length > len(data):
        return ''
    return data[offset:offset + length].rstrip(b'\x00').decode('utf-8', errors='replace').strip()

def read_u8(data, offset):
    if offset >= len(data):
        return 0
    return data[offset]

def read_u16_be(data, offset):
    if offset + 2 > len(data):
        return 0
    return struct.unpack('>H', data[offset:offset + 2])[0]

def parse_opentag3d(data):
    """
    Parse OpenTag3D binary format per https://opentag3d.info/spec

    Core fields (0x00-0x6F):
      0x00  2  Tag Version (÷0.001)
      0x02  5  Base Material (UTF-8)
      0x07  5  Material Modifiers (UTF-8)
      0x1B 16  Manufacturer (UTF-8)
      0x2B 32  Color Name (UTF-8)
      0x4B  4  Color 1 RGBA
      0x50  4  Color 2 RGBA
      0x54  4  Color 3 RGBA
      0x58  4  Color 4 RGBA
      0x5C  2  Target Diameter (mm ÷ 0.001)
      0x5E  2  Target Weight (grams)
      0x60  1  Print Temperature (°C ÷ 5)
      0x61  1  Bed Temperature (°C ÷ 5)

    Extended fields (0x70+):
      0xB4  1  Min Print Temp (°C ÷ 5)
      0xB5  1  Max Print Temp (°C ÷ 5)
      0xB6  1  Min Bed Temp (°C ÷ 5)
      0xB7  1  Max Bed Temp (°C ÷ 5)
    """
    if len(data) < OPENTAG3D_CORE_SIZE:
        return None

    version = read_u16_be(data, 0x00)
    if version == 0:
        return None

    base_material = read_utf8(data, 0x02, 5)
    if not base_material:
        return None

    material_modifiers = read_utf8(data, 0x07, 5)
    manufacturer = read_utf8(data, 0x1B, 16)

    colors = []
    for offset in (0x4B, 0x50, 0x54, 0x58):
        r = read_u8(data, offset)
        g = read_u8(data, offset + 1)
        b = read_u8(data, offset + 2)
        a = read_u8(data, offset + 3)
        if r > 0 or g > 0 or b > 0:
            colors.append((r, g, b, a))

    diameter_raw = read_u16_be(data, 0x5C)
    weight = read_u16_be(data, 0x5E)
    print_temp_raw = read_u8(data, 0x60)
    bed_temp_raw = read_u8(data, 0x61)

    if not colors:
        colors = [(255, 255, 255, 255)]

    r, g, b, a = colors[0]
    result = {
        'protocol': 'openspool',
        'version': '1.0',
        'type': base_material.upper(),
        'brand': manufacturer if manufacturer else 'Generic',
        'color_hex': f'{r:02X}{g:02X}{b:02X}',
    }

    if material_modifiers:
        result['subtype'] = material_modifiers

    if a < 255:
        result['alpha'] = a

    if len(colors) > 1:
        result['additional_color_hexes'] = [
            f'{c[0]:02X}{c[1]:02X}{c[2]:02X}' for c in colors[1:]
        ]

    if diameter_raw > 0:
        result['diameter'] = diameter_raw / 1000.0

    if weight > 0:
        result['weight'] = weight

    if print_temp_raw > 0:
        print_temp = print_temp_raw * 5
        result['min_temp'] = print_temp
        result['max_temp'] = print_temp

    if bed_temp_raw > 0:
        bed_temp = bed_temp_raw * 5
        result['bed_min_temp'] = bed_temp
        result['bed_max_temp'] = bed_temp

    if len(data) > 0xB7:
        min_print = read_u8(data, 0xB4)
        max_print = read_u8(data, 0xB5)
        min_bed = read_u8(data, 0xB6)
        max_bed = read_u8(data, 0xB7)

        if min_print > 0:
            result['min_temp'] = min_print * 5
        if max_print > 0:
            result['max_temp'] = max_print * 5
        if min_bed > 0:
            result['bed_min_temp'] = min_bed * 5
        if max_bed > 0:
            result['bed_max_temp'] = max_bed * 5

    return result

def main():
    if len(sys.argv) < 3:
        sys.exit(1)

    args = sys.argv[1:]
    for i in range(0, len(args) - 1, 2):
        mime_type = args[i]
        hex_payload = args[i + 1]

        if mime_type != OPENTAG3D_MIME:
            continue

        try:
            payload = bytes.fromhex(hex_payload)
        except ValueError:
            continue

        result = parse_opentag3d(payload)
        if result:
            print(json.dumps(result))
            sys.exit(0)

    sys.exit(1)

if __name__ == '__main__':
    main()
