#!/usr/bin/env python3

import configparser
import logging
import logging.handlers
import os
import runpy
import sys

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

    with open(target, "w") as f:
        config.write(f)

    sys.argv = [sys.argv[0], target]
    sys.path.insert(0, "/usr/local/share/openrfid")
    os.chdir("/usr/local/share/openrfid")
    runpy.run_path("main.py", run_name="__main__")


if __name__ == "__main__":
    main()
