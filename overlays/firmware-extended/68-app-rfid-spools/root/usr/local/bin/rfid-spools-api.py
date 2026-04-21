#!/usr/bin/env python3
"""RFID Spools Management API.

Lightweight HTTP server that:
- Receives OpenRFID webhook events and stores tag data per channel
- Serves channel state via REST API
- Proxies to Moonraker for filament_detect state
"""

import argparse
import json
import logging
import logging.handlers
import os
import threading
import urllib.request
import urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler

LOG_FILE = "/oem/printer_data/logs/rfid-spools.log"
CONFIG_FILE = "/oem/printer_data/config/extended/rfid-spools.json"
MOONRAKER_URL = "http://localhost"
MAX_CHANNELS = 4
MAX_BODY_SIZE = 64 * 1024  # 64KB max request body


class ChannelStore:
    """Thread-safe storage for per-channel tag data from OpenRFID webhooks."""

    def __init__(self):
        self._lock = threading.Lock()
        self._channels = {i: None for i in range(MAX_CHANNELS)}

    def update(self, channel, data):
        if not isinstance(channel, int) or channel < 0 or channel >= MAX_CHANNELS:
            return False
        with self._lock:
            self._channels[channel] = data
        return True

    def get_all(self):
        with self._lock:
            return dict(self._channels)

    def get(self, channel):
        with self._lock:
            return self._channels.get(channel)


store = ChannelStore()


def load_config():
    """Load persistent config from disk."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logging.warning("Failed to load config: %s", e)
    return {}


def save_config(config):
    """Save config to disk."""
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    tmp = CONFIG_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(config, f, indent=2)
    os.replace(tmp, CONFIG_FILE)


def query_moonraker_filament_detect():
    """Query Moonraker for current filament_detect state."""
    url = f"{MOONRAKER_URL}/printer/objects/query?filament_detect"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read())
    except (urllib.error.URLError, OSError, json.JSONDecodeError) as e:
        logging.warning("Moonraker query failed: %s", e)
        return None


def moonraker_gcode(script):
    """Send a G-code script to Klipper via Moonraker."""
    url = f"{MOONRAKER_URL}/printer/gcode/script"
    body = json.dumps({"script": script}).encode("utf-8")
    req = urllib.request.Request(
        url, data=body, method="POST",
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


class RequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the RFID Spools API."""

    def log_message(self, fmt, *args):
        logging.info(fmt, *args)

    def _send_json(self, status, data):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length > MAX_BODY_SIZE:
            return None
        return self.rfile.read(length)

    def do_GET(self):
        if self.path == "/api/health":
            self._send_json(200, {"status": "ok"})

        elif self.path == "/api/channels":
            # Merge Moonraker filament_detect with stored OpenRFID data
            moonraker = query_moonraker_filament_detect()
            filament_detect = {}
            if moonraker and "result" in moonraker:
                status = moonraker["result"].get("status", {})
                filament_detect = status.get("filament_detect", {})

            # filament_detect.info is an array of per-channel dicts
            fd_info = filament_detect.get("info", [])

            channels = []
            stored = store.get_all()
            for ch in range(MAX_CHANNELS):
                mk = fd_info[ch] if ch < len(fd_info) else {}
                channel_data = {
                    "channel": ch,
                    "moonraker": mk if isinstance(mk, dict) else {},
                    "tag": stored[ch],
                }
                channels.append(channel_data)

            self._send_json(200, {"channels": channels})

        elif self.path == "/api/config":
            self._send_json(200, load_config())

        else:
            self._send_json(404, {"error": "not found"})

    def do_POST(self):
        if self.path == "/api/tag-event":
            body = self._read_body()
            if body is None:
                self._send_json(413, {"error": "body too large"})
                return
            try:
                data = json.loads(body)
            except (json.JSONDecodeError, ValueError):
                self._send_json(400, {"error": "invalid json"})
                return

            channel = data.get("channel")
            if channel is None:
                # Try to extract from reader.slot
                reader = data.get("reader", {})
                channel = reader.get("slot")

            if channel is None:
                self._send_json(400, {"error": "missing channel"})
                return

            try:
                channel = int(channel)
            except (TypeError, ValueError):
                self._send_json(400, {"error": "invalid channel"})
                return

            event = data.get("event", "tag_read")
            if event in ("tag_not_present", "tag_parse_error"):
                store.update(channel, {"event": event, "tag": None})
            else:
                store.update(channel, data)

            self._send_json(200, {"status": "ok"})

        elif self.path == "/api/config":
            body = self._read_body()
            if body is None:
                self._send_json(413, {"error": "body too large"})
                return
            try:
                data = json.loads(body)
            except (json.JSONDecodeError, ValueError):
                self._send_json(400, {"error": "invalid json"})
                return
            config = load_config()
            config.update(data)
            save_config(config)
            self._send_json(200, config)

        elif self.path == "/api/scan":
            # Trigger a fresh RFID scan on all channels by issuing
            # FILAMENT_DT_UPDATE G-code, which sets state=1 per channel
            # and causes OpenRFID to re-read the tags.
            body = self._read_body()  # optional {"channels": [0,1,2,3]}
            channels = list(range(MAX_CHANNELS))
            if body:
                try:
                    req_data = json.loads(body)
                    if "channels" in req_data and isinstance(req_data["channels"], list):
                        channels = [int(c) for c in req_data["channels"]
                                    if 0 <= int(c) < MAX_CHANNELS]
                except (json.JSONDecodeError, ValueError, TypeError):
                    pass

            errors = []
            for ch in channels:
                try:
                    moonraker_gcode(f"FILAMENT_DT_UPDATE CHANNEL={ch}")
                    logging.info("Triggered RFID scan for channel %d", ch)
                except (urllib.error.URLError, OSError) as e:
                    logging.warning("Scan trigger failed for channel %d: %s", ch, e)
                    errors.append(ch)

            if errors:
                self._send_json(500, {"status": "partial", "failed_channels": errors})
            else:
                self._send_json(200, {"status": "ok", "channels": channels})

        else:
            self._send_json(404, {"error": "not found"})

    def do_PUT(self):
        if self.path == "/api/config":
            return self.do_POST()
        self._send_json(404, {"error": "not found"})


def setup_logging():
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    handlers = [
        logging.StreamHandler(),
        logging.handlers.TimedRotatingFileHandler(
            LOG_FILE, when="midnight", interval=1, backupCount=7
        ),
    ]
    fmt = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    for h in handlers:
        h.setFormatter(fmt)
    logging.root.handlers = handlers
    logging.root.setLevel(logging.INFO)


def main():
    parser = argparse.ArgumentParser(description="RFID Spools Management API")
    parser.add_argument("--bind", default="127.0.0.1", help="Bind address")
    parser.add_argument("--port", type=int, default=8093, help="Listen port")
    args = parser.parse_args()

    setup_logging()
    logging.info("Starting RFID Spools API on %s:%d", args.bind, args.port)

    server = HTTPServer((args.bind, args.port), RequestHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        logging.info("RFID Spools API stopped")


if __name__ == "__main__":
    main()
