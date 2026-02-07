import logging
import os
import subprocess

PLUGIN_DIR_NTAG = '/oem/printer_data/config/extended/rfid/ntag'
PLUGIN_DIR_MIFARE = '/oem/printer_data/config/extended/rfid/mifare'
PLUGIN_TIMEOUT = 1.0

def run_plugin(plugin_path, args):
    try:
        result = subprocess.run(
            [plugin_path] + args,
            capture_output=True,
            timeout=PLUGIN_TIMEOUT,
            text=True
        )
        if result.returncode == 0:
            return True, result.stdout
        return False, None
    except subprocess.TimeoutExpired:
        logging.warning(f"Plugin '{plugin_path}' timed out after {PLUGIN_TIMEOUT}s")
        return False, None
    except Exception as e:
        logging.warning(f"Plugin '{plugin_path}' failed: {e}")
        return False, None

def run_plugins_in_dir(plugin_dir, args):
    if not os.path.isdir(plugin_dir):
        logging.debug(f"Plugin directory '{plugin_dir}' does not exist")
        return None

    try:
        entries = os.listdir(plugin_dir)
    except OSError as e:
        logging.warning(f"Failed to list plugin directory: {e}")
        return None

    for entry in sorted(entries):
        plugin_path = os.path.join(plugin_dir, entry)
        if not os.path.isfile(plugin_path):
            continue
        if not os.access(plugin_path, os.X_OK):
            continue

        logging.info(f"Trying plugin '{entry}'")
        success, output = run_plugin(plugin_path, args)
        if success and output:
            logging.info(f"Plugin '{entry}' parsed successfully: {output.strip()}")
            return output.encode('utf-8')

    logging.debug("No plugin could parse the records")
    return None

def run_all_plugins_in_dir(plugin_dir, args):
    results = []

    if not os.path.isdir(plugin_dir):
        logging.debug(f"Plugin directory '{plugin_dir}' does not exist")
        return results

    try:
        entries = os.listdir(plugin_dir)
    except OSError as e:
        logging.warning(f"Failed to list plugin directory: {e}")
        return results

    for entry in sorted(entries):
        plugin_path = os.path.join(plugin_dir, entry)
        if not os.path.isfile(plugin_path):
            continue
        if not os.access(plugin_path, os.X_OK):
            continue

        logging.info(f"Trying plugin '{entry}'")
        success, output = run_plugin(plugin_path, args)
        if success and output:
            logging.info(f"Plugin '{entry}' returned auth keys")
            results.append(output.encode('utf-8'))

    return results

def plugin_ndef_parse(records):
    args = []

    for record in records:
        mime_type = record.get('mime_type', '')
        payload = record.get('payload', b'')
        args.append(mime_type)
        args.append(payload.hex())

    return run_plugins_in_dir(PLUGIN_DIR_NTAG, args)

def plugin_m1_parse(data_buf):
    if data_buf is None or not isinstance(data_buf, list):
        return None

    hex_payload = bytes(data_buf).hex()
    args = ['parse', hex_payload]

    return run_plugins_in_dir(PLUGIN_DIR_MIFARE, args)

def plugin_m1_auth_all(card_uid):
    import json

    if card_uid is None or not isinstance(card_uid, (list, bytes, bytearray)):
        return []

    if isinstance(card_uid, list):
        card_uid = bytes(card_uid)
    hex_uid = card_uid.hex()
    args = ['auth', hex_uid]

    results = []
    for output in run_all_plugins_in_dir(PLUGIN_DIR_MIFARE, args):
        try:
            auth_data = json.loads(output.decode('utf-8'))
            if 'key_a' not in auth_data:
                continue
            key_a = [[int(k[i:i+2], 16) for i in range(0, 12, 2)] for k in auth_data['key_a']]
            key_b = None
            if 'key_b' in auth_data:
                key_b = [[int(k[i:i+2], 16) for i in range(0, 12, 2)] for k in auth_data['key_b']]
            results.append((key_a, key_b))
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logging.warning(f"Plugin auth parse error: {e}")

    return results
