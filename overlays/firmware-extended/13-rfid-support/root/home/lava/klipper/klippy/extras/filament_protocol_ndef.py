import copy
import io
import json
import logging
from . import filament_protocol

NDEF_OK = 0
NDEF_ERR = -1
NDEF_PARAMETER_ERR = -2
NDEF_NOT_FOUND_ERR = -3

def xxd_dump(data, max_lines=16):
    if isinstance(data, list):
        data = bytes(data)
    if not isinstance(data, (bytes, bytearray)):
        return ""

    lines = []
    for i in range(0, min(len(data), max_lines * 16), 16):
        hex_part = ' '.join(f'{b:02x}' for b in data[i:i+16])
        ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in data[i:i+16])
        lines.append(f'{i:08x}: {hex_part:<48}  {ascii_part}')

    if len(data) > max_lines * 16:
        lines.append(f'... ({len(data)} bytes total)')

    return '\n'.join(lines)

def extract_ntag_uid(data_buf):
    """Extract 7-byte UID from NTAG card data.

    NTAG215 memory structure:
    - Page 0 (bytes 0-3): UID0, UID1, UID2, BCC0
    - Page 1 (bytes 4-7): UID3, UID4, UID5, UID6, BCC1

    Returns list of 7 UID bytes, or empty list if data is invalid.
    """
    if not data_buf or len(data_buf) < 8:
        return []

    try:
        # Convert to list if needed
        data = list(data_buf) if not isinstance(data_buf, list) else data_buf

        # Extract 7-byte UID from pages 0-1
        uid = [
            data[0],  # UID0
            data[1],  # UID1
            data[2],  # UID2
            data[4],  # UID3
            data[5],  # UID4
            data[6],  # UID5
            data[7],  # UID6
        ]

        return uid
    except (IndexError, TypeError):
        return []

def ndef_parse(data_buf):
    if None == data_buf or isinstance(data_buf, (list, bytes, bytearray)) == False:
        return NDEF_PARAMETER_ERR, []

    try:
        data = bytes(data_buf) if isinstance(data_buf, list) else data_buf

        logging.info("NDEF RFID data:")
        logging.info("\n" + xxd_dump(data))

        data_io = io.BytesIO(data)

        start_offset = 0
        if len(data) > 12 and data[0] != 0xE1:
            for i in range(min(16, len(data) - 4)):
                if data[i] == 0xE1 and (data[i+1] == 0x10 or data[i+1] == 0x11 or data[i+1] == 0x40):
                    start_offset = i
                    break

        if start_offset > 0:
            data_io.seek(start_offset)

        cc = data_io.read(4)
        if len(cc) < 4 or cc[0] != 0xE1:
            return NDEF_PARAMETER_ERR, []

        records = []

        while True:
            base_tlv = data_io.read(2)
            if len(base_tlv) < 2:
                break

            tag = base_tlv[0]
            if tag == 0xFE:
                break

            tlv_len = base_tlv[1]
            if tlv_len == 0xFF:
                ext_len = data_io.read(2)
                if len(ext_len) < 2:
                    break
                tlv_len = (ext_len[0] << 8) | ext_len[1]

            if tag == 0x03:
                ndef_data = data_io.read(tlv_len)
                ndef_offset = 0

                while ndef_offset < len(ndef_data) - 2:
                    header = ndef_data[ndef_offset]
                    ndef_offset += 1

                    tnf = header & 0x07
                    sr_flag = (header >> 4) & 0x01
                    il_flag = (header >> 3) & 0x01

                    type_len = ndef_data[ndef_offset]
                    ndef_offset += 1

                    if sr_flag:
                        payload_len = ndef_data[ndef_offset]
                        ndef_offset += 1
                    else:
                        if ndef_offset + 4 > len(ndef_data):
                            break
                        payload_len = (ndef_data[ndef_offset] << 24) | (ndef_data[ndef_offset + 1] << 16) | (ndef_data[ndef_offset + 2] << 8) | ndef_data[ndef_offset + 3]
                        ndef_offset += 4

                    id_len = 0
                    if il_flag:
                        id_len = ndef_data[ndef_offset]
                        ndef_offset += 1

                    if ndef_offset + type_len + id_len + payload_len > len(ndef_data):
                        break

                    mime_type = ndef_data[ndef_offset:ndef_offset + type_len].decode('ascii', errors='ignore')
                    ndef_offset += type_len

                    if id_len > 0:
                        ndef_offset += id_len

                    payload = bytes(ndef_data[ndef_offset:ndef_offset + payload_len])
                    ndef_offset += payload_len

                    if tnf == 0x02:
                        records.append({'mime_type': mime_type, 'payload': payload})
                        logging.info(f"NDEF record found: mime_type='{mime_type}', payload_len={len(payload)}")
            else:
                data_io.seek(tlv_len, 1)

        if not records:
            return NDEF_NOT_FOUND_ERR, []

        return NDEF_OK, records

    except Exception as e:
        logging.exception("NDEF parsing failed: %s", str(e))
        return NDEF_ERR, []

def parse_color_hex(value):
    try:
        hex_str = str(value)
        if hex_str.startswith('#'):
            hex_str = hex_str[1:]
        return int(hex_str, 16)
    except (ValueError, TypeError):
        return 0xFFFFFF

def _get_default_density(material_type):
    """Get default density for common filament types in g/cm³."""
    density_map = {
        'PLA': 1.24,
        'PETG': 1.27,
        'ABS': 1.04,
        'TPU': 1.21,
        'PVA': 1.19,
    }
    return density_map.get(material_type.upper(), 1.24)  # Default to PLA

def openspool_parse_payload(payload):
    if None == payload or not isinstance(payload, (bytes, bytearray)):
        logging.error("OpenSpool payload parsing failed: Invalid payload parameter")
        return filament_protocol.FILAMENT_PROTO_PARAMETER_ERR, None

    try:
        payload_str = payload.decode('utf-8')
        logging.info(f"OpenSpool JSON payload: {payload_str}")

        data = json.loads(payload_str)

        if not isinstance(data, dict):
            logging.error(f"OpenSpool payload parsing failed: JSON data is not a dict, got {type(data)}")
            return filament_protocol.FILAMENT_PROTO_ERR, None

        if data.get('protocol') != 'openspool':
            logging.error(f"OpenSpool payload parsing failed: Invalid protocol '{data.get('protocol')}', expected 'openspool'")
            return filament_protocol.FILAMENT_PROTO_ERR, None

        info = copy.copy(filament_protocol.FILAMENT_INFO_STRUCT)
        info['VERSION'] = 1
        info['VENDOR'] = data.get('brand', 'Generic')
        info['MANUFACTURER'] = data.get('brand', 'Generic')

        info['MAIN_TYPE'] = data.get('type', 'PLA').upper()
        info['SUB_TYPE'] = data.get('subtype', 'Basic')
        info['TRAY'] = 0

        info['COLOR_NUMS'] = 1
        info['RGB_1'] = parse_color_hex(data.get('color_hex', 'FFFFFF'))

        additional_color_hexes = list(data.get('additional_color_hexes') or [])
        for hex_color in additional_color_hexes[:5]:
            idx = info['COLOR_NUMS'] + 1
            info['COLOR_NUMS'] = idx
            info[f'RGB_{idx}'] = parse_color_hex(hex_color)

        for i in range(info['COLOR_NUMS'] + 1, 6):
            info[f'RGB_{i}'] = 0

        try:
            alpha_val = data.get('alpha')
            if alpha_val is not None:
                if isinstance(alpha_val, int):
                    # Integer value (0-255)
                    info['ALPHA'] = max(0x00, min(0xFF, alpha_val))
                elif isinstance(alpha_val, str):
                    # String - parse as hex (2-char hex string like "22", "FF")
                    info['ALPHA'] = max(0x00, min(0xFF, int(alpha_val, 16)))
                else:
                    info['ALPHA'] = 0xFF
            else:
                info['ALPHA'] = 0xFF
        except (ValueError, TypeError):
            info['ALPHA'] = 0xFF

        info['ARGB_COLOR'] = info['ALPHA'] << 24 | info['RGB_1']

        try:
            info['DIAMETER'] = int(float(data.get('diameter', 1.75)) * 100)
        except (ValueError, TypeError):
            info['DIAMETER'] = 175
        try:
            info['WEIGHT'] = int(data.get('weight', 0))
        except (ValueError, TypeError):
            info['WEIGHT'] = 0
        info['LENGTH'] = 0
        info['DRYING_TEMP'] = 0
        info['DRYING_TIME'] = 0

        # Density from tag data or default based on material type
        info['DENSITY'] = float(data.get('density', _get_default_density(info['MAIN_TYPE'])))

        try:
            min_temp = int(data.get('min_temp', 0))
            max_temp = int(data.get('max_temp', 0))
            info['HOTEND_MIN_TEMP'] = min_temp
            info['HOTEND_MAX_TEMP'] = max_temp
        except (ValueError, TypeError):
            info['HOTEND_MIN_TEMP'] = 0
            info['HOTEND_MAX_TEMP'] = 0

        try:
            bed_min_temp = int(data.get('bed_min_temp', 0))
            bed_max_temp = int(data.get('bed_max_temp', 0))
            # Store both min and max separately for encoding
            if bed_min_temp > 0:
                info['BED_MIN_TEMP'] = bed_min_temp
            if bed_max_temp > 0:
                info['BED_MAX_TEMP'] = bed_max_temp
            # Also set BED_TEMP for backward compatibility
            info['BED_TEMP'] = bed_min_temp if bed_min_temp > 0 else bed_max_temp
        except (ValueError, TypeError):
            info['BED_TEMP'] = 0

        info['BED_TYPE'] = 0
        info['FIRST_LAYER_TEMP'] = info['HOTEND_MIN_TEMP']
        info['OTHER_LAYER_TEMP'] = info['HOTEND_MIN_TEMP']

        info['SKU'] = 0
        info['MF_DATE'] = '19700101'
        info['RSA_KEY_VERSION'] = 0
        info['OFFICIAL'] = True

        return filament_protocol.FILAMENT_PROTO_OK, info

    except json.JSONDecodeError as e:
        logging.exception("OpenSpool payload parsing failed: Invalid JSON: %s", str(e))
        return filament_protocol.FILAMENT_PROTO_ERR, None
    except Exception as e:
        logging.exception("OpenSpool payload parsing failed: %s", str(e))
        return filament_protocol.FILAMENT_PROTO_ERR, None

def openspool_encode_payload(info):
    """Encode filament info dict to OpenSpool JSON payload."""
    try:
        logging.info(f"openspool_encode_payload called with info keys: {list(info.keys())}")

        # Build JSON dict with OpenSpool fields
        data = {
            'protocol': 'openspool',
            'version': '1.0',
            'type': info.get('MAIN_TYPE', 'PLA'),
            'brand': info.get('VENDOR', 'Generic'),
        }

        # Add subtype if available
        if info.get('SUB_TYPE') and info['SUB_TYPE'] != 'Reserved':
            data['subtype'] = info['SUB_TYPE']

        # Add color
        rgb = info.get('RGB_1', 0xFFFFFF)
        color_hex = f"#{rgb:06X}"
        data['color_hex'] = color_hex

        # Add alpha transparency if not fully opaque
        alpha = info.get('ALPHA', 0xFF)
        if alpha < 0xFF:
            data['alpha'] = f"{alpha:02X}"

        # Add additional colors (multicolor spools)
        additional_colors = []
        for i in range(2, 6):
            rgb_key = f'RGB_{i}'
            color_val = info.get(rgb_key, 0)
            if color_val != 0:
                additional_colors.append(f"{color_val:06X}")
        if additional_colors:
            data['additional_color_hexes'] = additional_colors

        # Add temperatures
        if info.get('HOTEND_MIN_TEMP', 0) > 0:
            data['min_temp'] = str(info['HOTEND_MIN_TEMP'])
        if info.get('HOTEND_MAX_TEMP', 0) > 0:
            data['max_temp'] = str(info['HOTEND_MAX_TEMP'])

        # Bed temperature - use BED_MIN_TEMP/BED_MAX_TEMP if available, otherwise fall back to BED_TEMP
        bed_min = info.get('BED_MIN_TEMP')
        bed_max = info.get('BED_MAX_TEMP')
        if bed_min is not None and bed_min > 0:
            data['bed_min_temp'] = str(bed_min)
        elif info.get('BED_TEMP', 0) > 0:
            data['bed_min_temp'] = str(info['BED_TEMP'])

        if bed_max is not None and bed_max > 0:
            data['bed_max_temp'] = str(bed_max)
        elif info.get('BED_TEMP', 0) > 0 and bed_min is None:
            data['bed_max_temp'] = str(info['BED_TEMP'])

        # Add diameter and density
        diameter_mm = info.get('DIAMETER', 175) / 100.0  # Convert from 1/100mm to mm
        data['diameter'] = diameter_mm

        if info.get('DENSITY', 0.0) > 0:
            data['density'] = info['DENSITY']

        # Add weight if provided
        weight = info.get('WEIGHT', 0)
        if weight > 0:
            data['weight'] = weight

        # Encode to JSON bytes
        json_str = json.dumps(data, separators=(',', ':'))  # Compact JSON
        logging.info(f"openspool_encode_payload success: {len(json_str)} bytes")
        return filament_protocol.FILAMENT_PROTO_OK, json_str.encode('utf-8')

    except Exception as e:
        logging.exception("OpenSpool payload encoding failed: %s", str(e))
        return filament_protocol.FILAMENT_PROTO_ERR, None

def ndef_encode(info):
    """Encode filament info dict to complete NDEF message for NTAG.

    Called by FILAMENT_TAG_WRITE_OPENSPOOL gcode command in filament_detect.py
    to convert user parameters into NDEF format for tag writing.
    """
    try:
        logging.info("ndef_encode called")

        # Encode payload
        error, payload = openspool_encode_payload(info)
        if error != filament_protocol.FILAMENT_PROTO_OK:
            logging.error(f"ndef_encode: openspool_encode_payload failed with error {error}")
            return error, None

        mime_type = b'application/json'

        # Build NDEF record
        type_len = len(mime_type)
        payload_len = len(payload)

        # NDEF record structure
        record = bytearray()

        if payload_len <= 255:
            # Short record format: SR=1, payload length in 1 byte
            # Header byte: MB=1, ME=1, CF=0, SR=1, IL=0, TNF=0x02 (Media-type)
            header = 0xD2  # 11010010
            record.append(header)
            record.append(type_len)
            record.append(payload_len)
        else:
            # Long record format: SR=0, payload length in 4 bytes
            # Header byte: MB=1, ME=1, CF=0, SR=0, IL=0, TNF=0x02 (Media-type)
            header = 0xC2  # 11000010
            record.append(header)
            record.append(type_len)
            record.append((payload_len >> 24) & 0xFF)
            record.append((payload_len >> 16) & 0xFF)
            record.append((payload_len >> 8) & 0xFF)
            record.append(payload_len & 0xFF)

        record.extend(mime_type)
        record.extend(payload)

        # Build TLV structure
        tlv = bytearray()
        tlv.append(0x03)  # NDEF Message TLV tag
        if len(record) < 255:
            tlv.append(len(record))  # Length (1 byte)
        else:
            tlv.append(0xFF)  # Extended length format
            tlv.append((len(record) >> 8) & 0xFF)
            tlv.append(len(record) & 0xFF)
        tlv.extend(record)
        tlv.append(0xFE)  # Terminator TLV

        # Build complete NDEF message with CC (Capability Container)
        ndef_data = bytearray()
        ndef_data.append(0xE1)  # NDEF Magic Number
        ndef_data.append(0x10)  # Version 1.0
        ndef_data.append(0x6D)  # Data area size (440 bytes / 8 = 55 => 0x37, but use conservative 0x6D for 880 bytes)
        ndef_data.append(0x00)  # Read/Write access
        ndef_data.extend(tlv)

        logging.info(f"NDEF encoded: {len(ndef_data)} bytes total")
        return filament_protocol.FILAMENT_PROTO_OK, list(ndef_data)

    except Exception as e:
        logging.exception("NDEF encoding failed: %s", str(e))
        return filament_protocol.FILAMENT_PROTO_ERR, None

def ndef_proto_data_parse(data_buf):
    # Extract UID from raw NTAG data (first 9 bytes)
    card_uid = extract_ntag_uid(data_buf)

    # Create minimal info struct with UID for error cases
    def _create_minimal_info():
        info = copy.copy(filament_protocol.FILAMENT_INFO_STRUCT)
        info['CARD_UID'] = card_uid
        return info

    error, records = ndef_parse(data_buf)

    if error != NDEF_OK:
        logging.error(f"NDEF parse failed: NDEF parsing error (code: {error}), returning partial info with UID only")
        return filament_protocol.FILAMENT_PROTO_ERR, _create_minimal_info()

    if not records:
        logging.error("NDEF parse failed: No records found, returning partial info with UID only")
        return filament_protocol.FILAMENT_PROTO_ERR, _create_minimal_info()

    for record in records:
        mime_type = record['mime_type']
        payload = record['payload']

        if mime_type == 'application/json':
            logging.info(f"Detected OpenSpool format, parsing payload ({len(payload)} bytes)")
            error_code, info = openspool_parse_payload(payload)
            if error_code != filament_protocol.FILAMENT_PROTO_OK:
                logging.error(f"OpenSpool parse failed: Payload parsing error (code: {error_code})")
                continue
            else:
                # Set the extracted UID
                info['CARD_UID'] = card_uid
                logging.info(f"OpenSpool parse success: vendor={info.get('VENDOR')}, type={info.get('MAIN_TYPE')}, uid={':'.join(f'{b:02X}' for b in card_uid) if card_uid else 'none'}")
                return error_code, info

        else:
            logging.warning(f"Skipping unsupported MIME type '{mime_type}'")

    logging.error("NDEF parse failed: No supported records found, returning partial info with UID only")
    return filament_protocol.FILAMENT_PROTO_SIGN_CHECK_ERR, _create_minimal_info()

if __name__ == '__main__':
    import sys
    import argparse

    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    parser = argparse.ArgumentParser(description='Parse NDEF data from file')
    parser.add_argument('file', help='File containing NDEF data')
    args = parser.parse_args()

    try:
        with open(args.file, 'rb') as f:
            data = f.read()

        error_code, info = ndef_proto_data_parse(data)

        if error_code == filament_protocol.FILAMENT_PROTO_OK:
            print(info)
        else:
            print(f"Error: {error_code}")
            sys.exit(1)

    except FileNotFoundError:
        print(f"Error: File '{args.file}' not found")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
