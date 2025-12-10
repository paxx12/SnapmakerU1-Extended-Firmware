import os
import sys
import argparse
import logging

from . import filament_protocol
from . import filament_protocol_ndef

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    parser = argparse.ArgumentParser(description='Parse NDEF data from file')
    parser.add_argument('file', help='File containing NDEF data')
    args = parser.parse_args()

    try:
        with open(args.file, 'rb') as f:
            data = f.read()

        error_code, info = filament_protocol_ndef.ndef_proto_data_parse(data)

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
