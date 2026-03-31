#!/usr/bin/env python3

import configparser
import logging
import logging.handlers
import os
import re
import runpy
import sys


_FM175XX_READER = "/home/lava/klipper/klippy/extras/fm175xx_reader.py"


def _snapmaker_key():
    if not os.path.exists(_FM175XX_READER):
        logging.error("Snapmaker RFID reader not found at %s", _FM175XX_READER)
        sys.exit(1)
    with open(_FM175XX_READER, "r") as f:
        m = re.search(r'FM175XX_M1_CARD_HKDF_SALT_KEY_B\s*=\s*b"([^"]+)"', f.read())
    if not m:
        logging.error("Snapmaker RFID key not found in %s", _FM175XX_READER)
        sys.exit(1)
    return m.group(1).encode().hex()


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <target.cfg> [source.cfg ...]")
        sys.exit(1)

    syslogHandler = logging.handlers.SysLogHandler(address="/dev/log")
    stderrHandler = logging.StreamHandler(sys.stderr)
    logging.root.handlers = [syslogHandler, stderrHandler]
    logging.root.setLevel(logging.DEBUG)

    target = sys.argv[1]
    sources = sys.argv[2:]

    config = configparser.RawConfigParser()
    config.optionxform = str
    config.read(sources)

    if not config.has_section("snapmaker_tag_processor"):
        config.add_section("snapmaker_tag_processor")
    config.set("snapmaker_tag_processor", "key", _snapmaker_key())

    with open(target, "w") as f:
        config.write(f)

    sys.argv = [sys.argv[0], target]
    sys.path.insert(0, "/usr/local/share/openrfid")
    os.chdir("/usr/local/share/openrfid")
    runpy.run_path("main.py", run_name="__main__")


if __name__ == "__main__":
    main()
