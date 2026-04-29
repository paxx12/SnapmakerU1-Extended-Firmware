"""Persistent JSON config for the RFID Spools service."""

import json
import logging
import os

from .constants import CONFIG_FILE


# Default config — applied as a base and then overlaid with the saved file.
DEFAULT_CONFIG = {
    "slot_names": {},
    "slot_notes": {},
    "spoolman_url": "",
    "spoolman_extra_fields": {
        "max_extruder_temp": False,
        "max_bed_temp": False,
        "drying_temp": False,
        "drying_time": False,
        "td": False,
        "mfg_date": False,
        "modifiers": False,
    },
}


def load_config():
    """Load persistent config from disk, merged with defaults."""
    saved = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                saved = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logging.warning("Failed to load config: %s", e)

    config = dict(DEFAULT_CONFIG)
    config.update(saved)
    # Drop legacy tag_mappings key that older builds persisted.
    config.pop("tag_mappings", None)
    return config


def save_config(config):
    """Atomically save the given config dict to disk."""
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    tmp = CONFIG_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(config, f, indent=2)
    os.replace(tmp, CONFIG_FILE)
