"""
NTAG215 write extension for OpenRFID.

Monkey-patches the GpioEnabledRfidReader (one per slot) to add NTAG21x page
write support and exposes a tiny loopback HTTP server (127.0.0.1:8740) so the
rfid-spools backend can submit write requests without stopping the daemon.

Architecture:
- A pending write is associated with a reader slot (0..N).
- GpioEnabledRfidReader.scan() is wrapped: at the top of each scan cycle it
  checks for a pending write, performs activate -> page-write loop, signals
  completion via a threading.Event, then returns None so the runtime skips the
  read this iteration. start_session/end_session still run normally so GPIO
  pins are toggled and the carrier wave is properly enabled/disabled.
- The HTTP server enqueues writes and waits on the Event for the result.

This keeps SPI access serialized inside the existing reader loop -- no
service stop/start, no second SPI client.
"""

from __future__ import annotations

import base64
import json
import logging
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Optional


_LOGGER = logging.getLogger("openrfid.ntag_write")
_INSTALL_LOCK = threading.Lock()
_INSTALLED = False

# slot (int) -> GpioEnabledRfidReader instance
_INSTANCES: dict = {}
_INSTANCES_LOCK = threading.Lock()

# The Runtime instance, captured via a monkey-patched __init__ below. We need it
# so we can call start_reading_tag(slot) when a write is enqueued -- otherwise
# OpenRFID with `auto_read_mode = false` would never iterate the target reader
# and the pending write would sit untouched until it timed out.
_RUNTIME_REF: dict = {"runtime": None}

DEFAULT_BIND_HOST = "127.0.0.1"
DEFAULT_BIND_PORT = 8740
DEFAULT_WRITE_TIMEOUT = 15.0  # seconds to wait for the scan loop to pick up a write


def install(host: str = DEFAULT_BIND_HOST, port: int = DEFAULT_BIND_PORT) -> None:
    """Install the NTAG write extension. Safe to call multiple times."""
    global _INSTALLED
    with _INSTALL_LOCK:
        if _INSTALLED:
            return
        _patch_gpio_reader()
        _patch_runtime()
        _start_http_server(host, port)
        _INSTALLED = True
        _LOGGER.info("NTAG write extension installed on %s:%d", host, port)


def _patch_runtime() -> None:
    """Monkey-patch Runtime to capture the instance for start_reading_tag()."""
    from runtime import Runtime

    original_init = Runtime.__init__

    def patched_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        _RUNTIME_REF["runtime"] = self
        _LOGGER.info(
            "Captured Runtime instance with %d readers",
            len(getattr(self, "rfid_readers", [])),
        )

    Runtime.__init__ = patched_init


# ---------------------------------------------------------------------------
# Reader monkey-patch
# ---------------------------------------------------------------------------
def _patch_gpio_reader() -> None:
    from reader.gpio_enabled_rfid_reader import GpioEnabledRfidReader
    from reader.fm175xx.rfid import Fm175xx, Fm175xxCmdMetaData
    from reader.fm175xx import constants as Constants

    original_init = GpioEnabledRfidReader.__init__
    original_scan = GpioEnabledRfidReader.scan

    def patched_init(self, config: dict):
        original_init(self, config)
        self._pending_write: Optional[dict] = None
        self._pending_write_lock = threading.Lock()
        slot = getattr(self, "slot", None)
        if slot is None:
            return
        with _INSTANCES_LOCK:
            _INSTANCES[int(slot)] = self
        _LOGGER.info(
            "Registered GpioEnabledRfidReader %r for write on slot %d",
            getattr(self, "name", "?"),
            int(slot),
        )

    def patched_scan(self):
        with self._pending_write_lock:
            pending = self._pending_write
            self._pending_write = None

        if pending is not None:
            inner = getattr(self, "rfid_reader", None)
            if not isinstance(inner, Fm175xx):
                pending["result"] = {
                    "ok": False,
                    "error": f"unsupported_reader:{type(inner).__name__}",
                }
                pending["event"].set()
                return None
            _execute_pending_write(inner, pending, Constants, Fm175xxCmdMetaData)
            # Skip normal read this iteration; runtime will re-scan next loop.
            return None

        return original_scan(self)

    GpioEnabledRfidReader.__init__ = patched_init
    GpioEnabledRfidReader.scan = patched_scan
    _LOGGER.debug("GpioEnabledRfidReader patched with NTAG write hooks")


def _execute_pending_write(reader, pending: dict, Constants, Fm175xxCmdMetaData) -> None:
    """Activate the card and write pages. Called inside scan() with carrier wave on."""
    event: threading.Event = pending["event"]
    try:
        data: bytes = pending["data"]
        start_page: int = pending["start_page"]

        activate = getattr(reader, "_Fm175xx__reader_a_activate")
        ret, UID, ATQA, BCC, SAK = activate()
        if ret != Constants.FM175XX_OK:
            pending["result"] = {"ok": False, "error": f"activate_failed:{ret}"}
            return

        total_pages = (len(data) + 3) // 4
        if total_pages == 0:
            pending["result"] = {"ok": False, "error": "empty_data"}
            return

        end_page = start_page + total_pages - 1
        max_user_page = getattr(Constants, "FM175XX_NTAG215_USER_END_PAGE", 129)
        if end_page > max_user_page:
            pending["result"] = {
                "ok": False,
                "error": f"data_too_large:end_page={end_page}>max={max_user_page}",
            }
            return

        for i in range(total_pages):
            chunk = list(data[i * 4 : i * 4 + 4])
            while len(chunk) < 4:
                chunk.append(0x00)
            page_no = start_page + i
            wret = _ntag_page_write(reader, page_no, chunk, Constants, Fm175xxCmdMetaData)
            if wret != Constants.FM175XX_OK:
                pending["result"] = {
                    "ok": False,
                    "error": f"write_failed:page={page_no}:{wret}",
                }
                return

        pending["result"] = {
            "ok": True,
            "pages_written": total_pages,
            "start_page": start_page,
            "end_page": end_page,
            "uid": bytes(UID).hex(),
        }
        _LOGGER.info(
            "NTAG write OK: uid=%s pages=%d (%d..%d)",
            bytes(UID).hex(),
            total_pages,
            start_page,
            end_page,
        )

    except Exception as exc:
        _LOGGER.exception("NTAG write crashed")
        pending["result"] = {"ok": False, "error": f"exception:{exc}"}
    finally:
        event.set()


def _ntag_page_write(reader, page: int, data: list, Constants, Fm175xxCmdMetaData) -> int:
    """Issue an NTAG WRITE (0xA2) for a single 4-byte page."""
    cmd = Fm175xxCmdMetaData()
    cmd.send_crc_en = Constants.FM175XX_SET
    cmd.recv_crc_en = Constants.FM175XX_RESET
    cmd.send_buff = [0xA2, page & 0xFF, data[0], data[1], data[2], data[3]]
    cmd.recv_buff = [0]
    cmd.bytes_to_send = 6
    cmd.bits_to_send = 0
    cmd.bits_to_recv = 0
    cmd.bytes_to_recv = 1
    cmd.timeout = 10
    cmd.cmd = Constants.FM175XX_CMD_TRANSCEIVE

    command_exe = getattr(reader, "_Fm175xx__command_exe")
    result = command_exe(cmd)

    # Tag ACK: 4 bits, low nibble == 0x0A
    if result.err_code != Constants.FM175XX_OK:
        return result.err_code
    if cmd.bits_recved != 4:
        return Constants.FM175XX_CARD_COMM_ERR
    if (cmd.recv_buff[0] & 0x0F) != 0x0A:
        return Constants.FM175XX_CARD_COMM_ERR
    return Constants.FM175XX_OK


# ---------------------------------------------------------------------------
# HTTP server
# ---------------------------------------------------------------------------
def submit_write(slot, data: bytes, start_page: int = 4, timeout: float = DEFAULT_WRITE_TIMEOUT) -> dict:
    """Enqueue a write to the reader at `slot` and wait for completion."""
    try:
        slot_int = int(slot)
    except (TypeError, ValueError):
        return {"ok": False, "error": f"bad_slot:{slot!r}"}

    with _INSTANCES_LOCK:
        reader = _INSTANCES.get(slot_int)
    if reader is None:
        return {"ok": False, "error": f"unknown_slot:{slot_int}"}

    event = threading.Event()
    pending = {
        "data": data,
        "start_page": start_page,
        "event": event,
        "result": None,
    }
    with reader._pending_write_lock:
        if reader._pending_write is not None:
            return {"ok": False, "error": "write_already_pending"}
        reader._pending_write = pending

    # Wake up the runtime so it iterates this slot. With auto_read_mode = false
    # the reader is otherwise only processed on demand (e.g. when Klipper asks
    # for a read). We need at least one iteration to happen so our patched
    # scan() can drain the pending write.
    runtime = _RUNTIME_REF.get("runtime")
    if runtime is not None:
        try:
            runtime.start_reading_tag(slot_int)
        except Exception:
            _LOGGER.exception("start_reading_tag(%d) failed", slot_int)

    if not event.wait(timeout=timeout):
        with reader._pending_write_lock:
            if reader._pending_write is pending:
                reader._pending_write = None
        return {"ok": False, "error": "timeout"}

    return pending["result"] or {"ok": False, "error": "no_result"}


class _WriteHandler(BaseHTTPRequestHandler):
    server_version = "OpenRFIDWrite/1.0"

    def log_message(self, fmt, *args):  # noqa: N802
        _LOGGER.info("HTTP %s - %s", self.address_string(), fmt % args)

    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802
        if self.path == "/health":
            with _INSTANCES_LOCK:
                slots = sorted(_INSTANCES.keys())
            self._send_json(200, {"ok": True, "slots": slots})
            return
        self._send_json(404, {"ok": False, "error": "not_found"})

    def do_POST(self):  # noqa: N802
        if self.path != "/write":
            self._send_json(404, {"ok": False, "error": "not_found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length > 0 else b""
            req = json.loads(raw.decode("utf-8")) if raw else {}
        except Exception as exc:
            self._send_json(400, {"ok": False, "error": f"bad_request:{exc}"})
            return

        slot = req.get("slot", req.get("channel"))
        data_b64 = req.get("data_b64") or req.get("payload_b64")
        start_page = int(req.get("start_page", 4))
        timeout = float(req.get("timeout", DEFAULT_WRITE_TIMEOUT))

        if slot is None or data_b64 is None:
            self._send_json(400, {"ok": False, "error": "missing_slot_or_data"})
            return

        try:
            data = base64.b64decode(data_b64)
        except Exception as exc:
            self._send_json(400, {"ok": False, "error": f"bad_base64:{exc}"})
            return

        result = submit_write(slot, data, start_page=start_page, timeout=timeout)
        status = 200 if result.get("ok") else 500
        self._send_json(status, result)


def _start_http_server(host: str, port: int) -> None:
    def serve():
        last_exc = None
        for _ in range(10):
            try:
                httpd = ThreadingHTTPServer((host, port), _WriteHandler)
                _LOGGER.info("NTAG write HTTP server listening on %s:%d", host, port)
                httpd.serve_forever()
                return
            except OSError as exc:
                last_exc = exc
                time.sleep(0.5)
        _LOGGER.error("Failed to bind NTAG write HTTP server: %s", last_exc)

    t = threading.Thread(target=serve, name="ntag-write-http", daemon=True)
    t.start()
