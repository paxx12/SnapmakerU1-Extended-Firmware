#!/usr/bin/env python3
# OVERRIDE: this file is installed by the rfid-spools overlay (68-app-rfid-spools)
# on top of the base launcher from 64-app-openrfid. It is identical to the base
# launcher except that it installs the NTAG write extension before running
# main.py, so the rfid-spools backend can submit writes without stopping the
# OpenRFID daemon.

import configparser
import logging
import logging.handlers
import os
import runpy
import sys


LOG_FILE = "/oem/printer_data/logs/openrfid.log"
MAX_ROTATIONS = 7


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <target.cfg> [source.cfg ...]")
        sys.exit(1)

    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

    syslogHandler = logging.handlers.SysLogHandler(address="/dev/log")
    stderrHandler = logging.StreamHandler(sys.stderr)
    fileHandler = logging.handlers.TimedRotatingFileHandler(
        LOG_FILE,
        when="midnight",
        interval=1,
        backupCount=MAX_ROTATIONS,
    )

    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    for handler in (syslogHandler, stderrHandler, fileHandler):
        handler.setFormatter(formatter)

    logging.root.handlers = [syslogHandler, stderrHandler, fileHandler]
    logging.root.setLevel(logging.DEBUG)

    target = sys.argv[1]
    sources = sys.argv[2:]

    config = configparser.RawConfigParser()
    config.optionxform = str
    config.read(sources)

    with open(target, "w") as f:
        config.write(f)

    sys.argv = [sys.argv[0], target]
    sys.path.insert(0, "/usr/local/share/openrfid")
    os.chdir("/usr/local/share/openrfid")

    # Install the NTAG write extension before main.py imports the reader
    # classes, so the Fm175xx monkey-patch is in place when instances are
    # constructed. Failures are logged but never block the daemon.
    try:
        from extensions.ntag_write import install as _install_ntag_write
        _install_ntag_write()
    except Exception:
        logging.getLogger("openrfid.launcher").exception(
            "Failed to install NTAG write extension; daemon will continue without it"
        )

    runpy.run_path("main.py", run_name="__main__")


if __name__ == "__main__":
    main()
