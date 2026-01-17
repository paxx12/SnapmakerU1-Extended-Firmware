#!/usr/bin/env python3

import argparse
import glob
import json
import os
import subprocess
import time
import fcntl
import yaml
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse

SYSTEM_UPGRADE_SCRIPT = "/home/lava/bin/systemUpgrade.sh"
FIRMWARE_UPLOAD_DIR = "/userdata"

def deep_merge(base, override):
    """Deep merge override into base, modifying base in place."""
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            deep_merge(base[key], value)
        else:
            base[key] = value
    return base

def load_functions_from_dir(functions_dir):
    """Load and deep merge all YAML files from a directory in sorted order."""
    config = {'links': {}, 'settings': {}, 'actions': {}}

    if not os.path.isdir(functions_dir):
        log(f"Functions directory not found: {functions_dir}")
        return config

    yaml_files = sorted(glob.glob(os.path.join(functions_dir, '*.yaml')))
    yaml_files += sorted(glob.glob(os.path.join(functions_dir, '*.yml')))
    yaml_files = sorted(set(yaml_files))

    for yaml_file in yaml_files:
        try:
            with open(yaml_file, 'r') as f:
                data = yaml.safe_load(f)
                if data:
                    deep_merge(config, data)
            log(f"Loaded functions from: {os.path.basename(yaml_file)}")
        except Exception as e:
            log(f"Error loading {yaml_file}: {e}")

    return config

def log(msg):
    ts = time.strftime('%H:%M:%S')
    print(f"[{ts}] {msg}", flush=True)

def get_current_slot():
    try:
        with open("/proc/cmdline", "r") as f:
            cmdline = f.read()
        for param in cmdline.split():
            if "android_slotsufix=" in param or "androidboot.slot_suffix=" in param:
                slot = param.split("=")[1]
                return "A" if slot == "_a" else "B"
    except Exception:
        pass
    return "unknown"

def get_hostname():
    try:
        with open("/etc/hostname", "r") as f:
            return f.read().strip()
    except Exception:
        return None

def get_ip_address(interface):
    try:
        result = subprocess.run(
            ["ip", "-4", "addr", "show", interface],
            capture_output=True,
            text=True,
            timeout=2
        )
        for line in result.stdout.split('\n'):
            if 'inet ' in line:
                return line.strip().split()[1].split('/')[0]
    except Exception:
        pass
    return None

def get_mac_address(interface):
    try:
        with open(f"/sys/class/net/{interface}/address", "r") as f:
            return f.read().strip()
    except Exception:
        return None

def get_wifi_info():
    try:
        result = subprocess.run(
            ["iwconfig", "wlan0"],
            capture_output=True,
            text=True,
            timeout=2
        )
        ssid = None
        signal = None
        for line in result.stdout.split('\n'):
            if 'ESSID:' in line:
                ssid = line.split('ESSID:')[1].strip().strip('"')
            if 'Signal level=' in line:
                signal = line.split('Signal level=')[1].split()[0]
        return ssid, signal
    except Exception:
        pass
    return None, None

def read_file_safe(path):
    try:
        with open(path, "r") as f:
            return f.read().strip()
    except Exception:
        return None

class MaintenanceToolHandler(SimpleHTTPRequestHandler):
    html_dir = None
    functions = {'settings': {}, 'links': {}, 'actions': {}}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=self.html_dir, **kwargs)

    def log_message(self, _format, *_args):
        pass

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/version":
            self.handle_version()
        elif path == "/api/settings":
            self.handle_get_settings()
        elif path == "/api/links":
            self.handle_get_links()
        elif path == "/api/actions":
            self.handle_get_actions()
        else:
            super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/upgrade":
            self.handle_upgrade()
        elif parsed.path.startswith("/api/settings/"):
            path_parts = parsed.path[14:].split('/')
            if len(path_parts) == 2:
                option = path_parts[0]
                value = path_parts[1]
                self.handle_update_setting(option, value)
            else:
                self.send_error(404, "Invalid settings path")
        elif parsed.path.startswith("/api/action/"):
            path_parts = parsed.path[12:].split('/')
            action = path_parts[0] if path_parts else None
            is_download = len(path_parts) > 1 and path_parts[1] == 'download'

            if not action:
                self.send_error(404, "Action not specified")
            elif is_download:
                self.handle_action_download(action)
            else:
                self.handle_action(action)
        else:
            self.send_error(404, "Not Found")

    def _start_text_stream(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()

    def _write_stream_chunk(self, data):
        if isinstance(data, str):
            data = data.encode("utf-8")
        self.wfile.write(data)
        self.wfile.flush()

    def _finish_text_stream(self):
        pass

    def _stream_command(self, cmd, stop_token=None):
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        try:
            for line in iter(process.stdout.readline, ""):
                self._write_stream_chunk(line)
                if stop_token and stop_token in line:
                    return 0, True
            process.wait()
            return process.returncode, False
        finally:
            try:
                process.stdout.close()
            except Exception:
                pass

    def handle_action(self, action):
        try:
            actions = self.functions.get('actions', {})
            if action not in actions:
                self.send_error(400, f"Unknown action: {action}")
                return

            cfg = actions[action]
            log(f"Action: {action}")

            if cfg.get("background"):
                self._start_text_stream()
                self._write_stream_chunk(f"=== {action} ===\n")
                self._write_stream_chunk(f"{cfg['message']}\n")
                subprocess.Popen(cfg["cmd"], start_new_session=True)
                self._write_stream_chunk(f"\nSUCCESS: Completed successfully\n")
                self._finish_text_stream()
            else:
                self._start_text_stream()
                self._write_stream_chunk(f"=== {cfg.get('label', action)} ===\n")
                self._write_stream_chunk(f"{cfg['message']}\n")
                self._write_stream_chunk(f"\n")
                exit_code, _ = self._stream_command(cfg["cmd"])
                if exit_code == 0:
                    self._write_stream_chunk(f"\nSUCCESS: Completed successfully (exit code: 0)\n")
                else:
                    self._write_stream_chunk(f"\nERROR: Failed with exit code: {exit_code}\n")
                self._finish_text_stream()
        except Exception as e:
            log(f"Action error: {e}")
            self.send_error(500, str(e))

    def handle_action_download(self, action):
        try:
            actions = self.functions.get('actions', {})
            if action not in actions:
                self.send_error(400, f"Unknown action: {action}")
                return

            cfg = actions[action]
            download_file = cfg.get("download_file")

            if not download_file:
                self.send_error(404, f"Action {action} does not provide a download file")
                return

            if not os.path.exists(download_file):
                self.send_error(404, f"Download file not found: {download_file}")
                return

            filename = os.path.basename(download_file)
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()

            with open(download_file, "rb") as f:
                chunk_size = 64 * 1024
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
        except Exception as e:
            log(f"Action error: {e}")
            self.send_error(500, str(e))

    def send_json(self, data):
        response = json.dumps(data, indent=2).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(response))
        self.end_headers()
        self.wfile.write(response)

    def handle_version(self):
        try:
            wifi_ssid, wifi_signal = get_wifi_info()
            versions = {
                "current_slot": get_current_slot(),
                "base_version": read_file_safe("/etc/FULLVERSION"),
                "build_version": read_file_safe("/etc/BUILD_VERSION"),
                "build_profile": read_file_safe("/etc/BUILD_PROFILE"),
                "hostname": get_hostname(),
                "wlan_ip": get_ip_address("wlan0"),
                "wlan_mac": get_mac_address("wlan0"),
                "eth_ip": get_ip_address("eth0"),
                "eth_mac": get_mac_address("eth0"),
                "wifi_ssid": wifi_ssid,
                "wifi_signal": wifi_signal
            }
            self.send_json(versions)
        except Exception as e:
            log(f"Version error: {e}")
            self.send_error(500, str(e))

    def handle_get_settings(self):
        try:
            settings = self.functions.get('settings', {})
            settings_data = {}
            for key, config in settings.items():
                try:
                    result = subprocess.run(
                        config["get_cmd"],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    current_value = result.stdout.strip() if result.returncode == 0 else config["default"]
                except Exception:
                    current_value = config["default"]

                settings_data[key] = {
                    "label": config["label"],
                    "current": current_value,
                    "options": {opt_key: opt_val["label"] for opt_key, opt_val in config["options"].items()}
                }

            self.send_json(settings_data)
        except Exception as e:
            log(f"Get settings error: {e}")
            self.send_error(500, str(e))

    def handle_get_links(self):
        try:
            settings = self.functions.get('settings', {})
            links = self.functions.get('links', {})
            # First, get current settings values if needed
            settings_cache = {}
            for link_key, link_config in links.items():
                condition = link_config.get("condition")
                if condition:
                    setting_key = condition["setting"]
                    if setting_key not in settings_cache:
                        try:
                            setting_config = settings[setting_key]
                            result = subprocess.run(
                                setting_config["get_cmd"],
                                capture_output=True,
                                text=True,
                                timeout=5
                            )
                            settings_cache[setting_key] = result.stdout.strip() if result.returncode == 0 else setting_config["default"]
                        except Exception:
                            settings_cache[setting_key] = settings[setting_key]["default"]

            # Build links list based on conditions
            links_list = []
            for link_key, link_config in links.items():
                condition = link_config.get("condition")

                # If no condition, always show
                if condition is None:
                    links_list.append({
                        "url": link_config["url"],
                        "icon": link_config["icon"],
                        "label": link_config["label"]
                    })
                else:
                    # Check condition
                    setting_key = condition["setting"]
                    required_value = condition["value"]
                    current_value = settings_cache.get(setting_key)

                    if current_value == required_value:
                        links_list.append({
                            "url": link_config["url"],
                            "icon": link_config["icon"],
                            "label": link_config["label"]
                        })

            self.send_json(links_list)
        except Exception as e:
            log(f"Get links error: {e}")
            self.send_error(500, str(e))

    def handle_get_actions(self):
        try:
            actions_cfg = self.functions.get('actions', {})
            actions = []
            for action_id, cfg in actions_cfg.items():
                actions.append({
                    "id": action_id,
                    "label": cfg.get("label", action_id),
                    "confirm": cfg.get("confirm", False),
                    "background": cfg.get("background", False),
                    "download_file": cfg.get("download_file")
                })

            self.send_json(actions)
        except Exception as e:
            log(f"Get actions error: {e}")
            self.send_error(500, str(e))

    def handle_update_setting(self, setting_key, value):
        stream_started = False
        try:
            settings = self.functions.get('settings', {})
            if not setting_key or setting_key not in settings:
                self.send_error(400, "Invalid setting key")
                return

            config = settings[setting_key]

            if value not in config["options"]:
                self.send_error(400, f"Invalid value. Must be one of: {', '.join(config['options'].keys())}")
                return

            option_config = config["options"][value]

            log(f"Updating setting {setting_key} to {value}")

            self._start_text_stream()
            stream_started = True

            self._write_stream_chunk(f"=== Updating {config['label']} ===\n")
            self._write_stream_chunk(f"Setting: {option_config['label']}\n")
            self._write_stream_chunk(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            self._write_stream_chunk(f"{'=' * 40}\n\n")

            # Execute the command for this option
            self._write_stream_chunk(f"Applying changes...\n")
            rc, _ = self._stream_command(option_config["cmd"])

            self._write_stream_chunk(f"\n{'=' * 40}\n")
            if rc == 0:
                self._write_stream_chunk(f"SUCCESS: Setting updated successfully\n")
            else:
                self._write_stream_chunk(f"ERROR: Command completed with exit code {rc}\n")
            self._finish_text_stream()

        except Exception as e:
            log(f"Update setting error: {e}")
            try:
                if stream_started:
                    try:
                        self._write_stream_chunk(f"\nError: {e}\n")
                        self._finish_text_stream()
                    except Exception:
                        pass
                else:
                    self.send_error(500, str(e))
            except Exception:
                pass

    def stream_multipart_to_file(self, field_name, filename):
        content_type = self.headers.get("Content-Type", "")
        content_length = int(self.headers.get("Content-Length", 0))
        boundary = None
        for part in content_type.split(";"):
            part = part.strip()
            if part.startswith("boundary="):
                boundary = part[9:].strip('"')
                break
        if not boundary or content_length == 0:
            return None, 0
        boundary_bytes = f"--{boundary}".encode()
        os.makedirs(FIRMWARE_UPLOAD_DIR, exist_ok=True)
        target_path = os.path.join(FIRMWARE_UPLOAD_DIR, filename)
        try:
            os.unlink(target_path)
        except FileNotFoundError:
            pass
        tf = open(target_path, "wb")
        try:
            fcntl.flock(tf, fcntl.LOCK_EX)
            in_file_content = False
            file_size = 0
            buf = b""
            chunk_size = 64 * 1024
            remaining = content_length
            while remaining > 0:
                read_size = min(chunk_size, remaining)
                chunk = self.rfile.read(read_size)
                if not chunk:
                    break
                remaining -= len(chunk)
                buf += chunk
                if not in_file_content:
                    header_end = buf.find(b"\r\n\r\n")
                    if header_end != -1:
                        header_part = buf[:header_end]
                        if field_name.encode() in header_part:
                            in_file_content = True
                            buf = buf[header_end + 4:]
                        else:
                            buf = buf[header_end + 4:]
                if in_file_content:
                    end_pos = buf.find(boundary_bytes)
                    if end_pos != -1:
                        data = buf[:end_pos]
                        if data.endswith(b"\r\n"):
                            data = data[:-2]
                        tf.write(data)
                        file_size += len(data)
                        break
                    else:
                        safe_len = len(buf) - len(boundary_bytes) - 4
                        if safe_len > 0:
                            tf.write(buf[:safe_len])
                            file_size += safe_len
                            buf = buf[safe_len:]
            tf.close()
            return target_path, file_size
        except Exception:
            tf.close()
            try:
                os.unlink(target_path)
            except Exception:
                pass
            raise

    def handle_upgrade(self):
        stream_started = False
        firmware_path = None
        try:
            content_type = self.headers.get("Content-Type", "")

            # Detect if it's JSON (URL download) or multipart (file upload)
            if "application/json" in content_type:
                # URL-based download and upgrade
                content_length = int(self.headers.get("Content-Length", 0))
                if content_length == 0:
                    self.send_error(400, "Empty request body")
                    return

                body = self.rfile.read(content_length).decode('utf-8')
                try:
                    data = json.loads(body)
                    url = data.get('url', '').strip()
                except json.JSONDecodeError:
                    self.send_error(400, "Invalid JSON")
                    return

                if not url:
                    self.send_error(400, "Missing 'url' parameter")
                    return

                log(f"Downloading firmware from: {url}")

                self._start_text_stream()
                stream_started = True

                self._write_stream_chunk(f"=== Firmware Download & Upgrade Started ===\n")
                self._write_stream_chunk(f"URL: {url}\n")
                self._write_stream_chunk(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                self._write_stream_chunk(f"{'=' * 40}\n\n")

                # Check for GitHub Actions artifact URLs
                if 'github.com' in url and '/artifacts/' in url:
                    self._write_stream_chunk("ERROR: GitHub Actions artifact URLs require authentication.\n")
                    self._write_stream_chunk("Please download the artifact manually or use a direct download URL.\n")
                    self._write_stream_chunk("\nHow to get a direct download URL:\n")
                    self._write_stream_chunk("1. Download the artifact from GitHub Actions\n")
                    self._write_stream_chunk("2. Use the local file upload option\n")
                    self._finish_text_stream()
                    return

                os.makedirs(FIRMWARE_UPLOAD_DIR, exist_ok=True)
                firmware_path = os.path.join(FIRMWARE_UPLOAD_DIR, "downloaded_firmware.bin")

                try:
                    os.unlink(firmware_path)
                except FileNotFoundError:
                    pass

                self._write_stream_chunk("Downloading firmware...\n")
                curl_cmd = [
                    "/usr/local/bin/curl", "-L", "-f", "--progress-bar",
                    "-o", firmware_path,
                    url
                ]

                rc, _ = self._stream_command(curl_cmd)

                if rc != 0:
                    self._write_stream_chunk(f"\nDownload failed with exit code {rc}\n")
                    if rc == 22:
                        self._write_stream_chunk("\nHTTP error (404, 401, 403, etc.)\n")
                        self._write_stream_chunk("Common causes:\n")
                        self._write_stream_chunk("- URL requires authentication\n")
                        self._write_stream_chunk("- File not found (404)\n")
                        self._write_stream_chunk("- Access denied (401/403)\n")
                        self._write_stream_chunk("\nPlease check the URL or use local file upload.\n")
                    elif rc == 6:
                        self._write_stream_chunk("\nCould not resolve host. Check the URL.\n")
                    elif rc == 7:
                        self._write_stream_chunk("\nFailed to connect to host.\n")
                    self._finish_text_stream()
                    return

                if not os.path.exists(firmware_path):
                    self._write_stream_chunk("\nDownload failed: file not created\n")
                    self._finish_text_stream()
                    return

                file_size = os.path.getsize(firmware_path)
                log(f"Firmware downloaded: {firmware_path} ({file_size} bytes)")

                self._write_stream_chunk(f"\nDownload complete: {file_size} bytes\n")
                self._write_stream_chunk(f"{'=' * 40}\n\n")
                self._write_stream_chunk("Starting upgrade...\n\n")

            elif "multipart/form-data" in content_type:
                # File upload
                firmware_path, file_size = self.stream_multipart_to_file("firmware", "uploaded_firmware.bin")
                if not firmware_path:
                    self.send_error(400, "No firmware file in request")
                    return
                log(f"Firmware uploaded: {firmware_path} ({file_size} bytes)")
                self._start_text_stream()
                stream_started = True
                self._write_stream_chunk(f"=== Firmware Upgrade Started ===\n")
                self._write_stream_chunk(f"Firmware file: {firmware_path}\n")
                self._write_stream_chunk(f"Size: {file_size} bytes\n")
                self._write_stream_chunk(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                self._write_stream_chunk(f"{'=' * 40}\n\n")
            else:
                self.send_error(400, "Expected application/json or multipart/form-data")
                return

            # Common upgrade logic
            try:
                stop_token = "upgrade soc finish, prepare to reboot"
                rc, stopped = self._stream_command(
                    [SYSTEM_UPGRADE_SCRIPT, "upgrade", "all", firmware_path],
                    stop_token=stop_token
                )
                self._write_stream_chunk(f"\n{'=' * 40}\n")
                self._write_stream_chunk(f"Exit code: {rc}\n")
                if rc == 0 or stopped:
                    self._write_stream_chunk("SUCCESS: Upgrade completed successfully. System will reboot.\n")
                else:
                    self._write_stream_chunk(f"ERROR: Upgrade failed with exit code {rc}\n")
            except Exception as e:
                self._write_stream_chunk(f"\nError during upgrade: {e}\n")
            finally:
                try:
                    os.unlink(firmware_path)
                except Exception:
                    pass
            self._finish_text_stream()
        except Exception as e:
            log(f"Upgrade error: {e}")
            try:
                if stream_started:
                    try:
                        self._write_stream_chunk(f"\nError: {e}\n")
                        self._finish_text_stream()
                    except Exception:
                        pass
                else:
                    self.send_error(500, str(e))
            except Exception:
                pass

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    local_html_dir = os.path.join(script_dir, "html")
    installed_html_dir = "/usr/local/share/maintenance-tool/html"

    if os.path.isdir(local_html_dir):
        default_html_dir = local_html_dir
    else:
        default_html_dir = installed_html_dir

    # Determine default functions directory
    local_functions_dir = os.path.join(script_dir, "functions")
    installed_functions_dir = "/usr/local/share/maintenance-tool/functions"

    if os.path.isdir(local_functions_dir):
        default_functions_dir = local_functions_dir
    else:
        default_functions_dir = installed_functions_dir

    parser = argparse.ArgumentParser(description="Maintenance Tool")
    parser.add_argument("-p", "--port", type=int, default=8080, help="HTTP port")
    parser.add_argument("--bind", default="0.0.0.0", help="Bind address")
    parser.add_argument("--html-dir", default=default_html_dir, help="Path to HTML directory")
    parser.add_argument("--functions-dir", default=default_functions_dir, help="Path to directory containing YAML function files (loaded in sorted order)")
    args = parser.parse_args()

    if not os.path.isdir(args.functions_dir):
        log(f"ERROR: Functions directory not found: {args.functions_dir}")
        return 1

    functions = load_functions_from_dir(args.functions_dir)

    MaintenanceToolHandler.html_dir = os.fspath(args.html_dir)
    MaintenanceToolHandler.functions = functions

    server = ThreadingHTTPServer((args.bind, args.port), MaintenanceToolHandler)
    log(f"Firmware Tool Control Server running on http://{args.bind}:{args.port}")
    log(f"  HTML directory: {args.html_dir}")
    log(f"  Functions dir: {args.functions_dir}")
    log(f"")
    log(f"Available endpoints:")
    log(f"  GET  /                         - Web interface")
    log(f"  GET  /api/version              - System and network information")
    log(f"  GET  /api/settings             - Get current settings")
    log(f"  GET  /api/links                - Get available quick links")
    log(f"  GET  /api/actions              - Get available actions")
    log(f"  POST /api/upgrade                   - Upload file or download from URL and install firmware")
    log(f"  POST /api/settings/<option>/<value> - Update a setting")
    log(f"  POST /api/action/<action>           - Execute action")
    log(f"  POST /api/action/<action>/download  - Download action result file")
    log(f"")
    log(f"Available actions: {', '.join(functions.get('actions', {}).keys())}")
    log(f"Available settings: {', '.join(functions.get('settings', {}).keys())}")
    log(f"Available links: {', '.join(functions.get('links', {}).keys())}")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log("Shutting down...")

    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
