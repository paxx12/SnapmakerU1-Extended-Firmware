"""Helpers for talking to the local Moonraker REST API."""

import json
import logging
import urllib.error
import urllib.request

from .constants import MOONRAKER_URL


def query_filament_detect():
    """Query Moonraker for the current ``filament_detect`` object."""
    url = "{}/printer/objects/query?filament_detect".format(MOONRAKER_URL)
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read())
    except (urllib.error.URLError, OSError, json.JSONDecodeError) as e:
        logging.warning("Moonraker query failed: %s", e)
        return None


def gcode(script):
    """Send a G-code script to Klipper via Moonraker."""
    url = "{}/printer/gcode/script".format(MOONRAKER_URL)
    body = json.dumps({"script": script}).encode("utf-8")
    req = urllib.request.Request(
        url, data=body, method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def query_spoolman_url():
    """Read the configured Spoolman URL from Moonraker's config API."""
    try:
        req = urllib.request.Request(
            "{}/server/config".format(MOONRAKER_URL), method='GET'
        )
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read())
        spoolman = data.get('result', {}).get('config', {}).get('spoolman', {})
        return spoolman.get('server', '') or ''
    except Exception:
        return ''
