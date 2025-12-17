#!/usr/bin/env python3

import sys
import configparser

cfg_file, section, key, default = sys.argv[1:5]

cfg = configparser.ConfigParser()
cfg.read(cfg_file)

value = (
    cfg.get(section, key, fallback=default).strip()
    if cfg.has_section(section)
    else default
)

print(value if value else default)
