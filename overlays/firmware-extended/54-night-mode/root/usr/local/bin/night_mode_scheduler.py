#!/usr/bin/env python3
import configparser
import datetime as dt
import json
import logging
import logging.handlers
import time
import urllib.error
import urllib.request
from typing import Dict, Optional

MOONRAKER_URL = "http://127.0.0.1:7125"
extended_cfg = "/home/lava/printer_data/config/extended/extended.cfg"
HEADERS = {"Content-Type": "application/json"}
PROFILE_FLOORS = {
    "speed_pct": 70.0,
    "accel": 5000.0,
    "fan_percent_min": 50.0,
    "fan_percent_max": 100.0,
    "current_min": 0.1,
    "current_max": 2.5,
}
DEFAULT_PROFILE = {
    "speed_pct": 75.0,
    "accel": 6500.0,
    "jerk": 5.0,
    "fan_percent": 65.0,
    "stepper_current_enabled": False,
    "stepper_current_x": 1.0,
    "stepper_current_y": 1.0,
    "tmc_autotune_enabled": True,
}
DEFAULT_SCHEDULE = {
    "enabled": False,
    "start": "22:00",
    "end": "07:00",
}
LOG = logging.getLogger("night_mode_scheduler")


def setup_logging() -> None:
    LOG.setLevel(logging.INFO)
    handler: logging.Handler
    try:
        handler = logging.handlers.SysLogHandler(address="/dev/log")
    except OSError:
        handler = logging.StreamHandler()
    formatter = logging.Formatter("night-mode: %(message)s")
    handler.setFormatter(formatter)
    LOG.addHandler(handler)


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def get_float(section: configparser.SectionProxy, key: str, default: float) -> float:
    try:
        return float(section.get(key, default))
    except Exception:
        LOG.warning("Invalid value for %s, using default %.2f", key, default)
        return default


def parse_time(timestr: str, fallback: str) -> dt.time:
    try:
        hh, mm = timestr.split(":")
        return dt.time(int(hh), int(mm))
    except Exception:
        LOG.warning("Invalid time '%s', falling back to '%s'", timestr, fallback)
        hh, mm = fallback.split(":")
        return dt.time(int(hh), int(mm))


def load_config() -> Dict:
    cfg = configparser.ConfigParser()
    cfg.read(extended_cfg)
    section = cfg["night_mode"] if cfg.has_section("night_mode") else {}
    raw_enabled = section.get("schedule_enabled", str(DEFAULT_SCHEDULE["enabled"])) if hasattr(section, "get") else str(DEFAULT_SCHEDULE["enabled"])
    schedule = {
        "enabled": str(raw_enabled).strip().lower() == "true",
        "start": section.get("schedule_start", DEFAULT_SCHEDULE["start"]) if hasattr(section, "get") else DEFAULT_SCHEDULE["start"],
        "end": section.get("schedule_end", DEFAULT_SCHEDULE["end"]) if hasattr(section, "get") else DEFAULT_SCHEDULE["end"],
    }
    profile = {
        "speed_pct": get_float(section, "profile_speed_pct", DEFAULT_PROFILE["speed_pct"]) if hasattr(section, "get") else DEFAULT_PROFILE["speed_pct"],
        "accel": get_float(section, "profile_accel", DEFAULT_PROFILE["accel"]) if hasattr(section, "get") else DEFAULT_PROFILE["accel"],
        "jerk": DEFAULT_PROFILE["jerk"],
        "fan_percent": get_float(section, "profile_fan_percent", DEFAULT_PROFILE["fan_percent"]) if hasattr(section, "get") else DEFAULT_PROFILE["fan_percent"],
        "stepper_current_enabled": False,
        "stepper_current_x": DEFAULT_PROFILE["stepper_current_x"],
        "stepper_current_y": DEFAULT_PROFILE["stepper_current_y"],
        "tmc_autotune_enabled": DEFAULT_PROFILE["tmc_autotune_enabled"],
    }
    if hasattr(section, "get"):
        for key in ("profile_jerk", "profile_jerk_x", "profile_jerk_y"):
            try:
                if section.get(key) is not None:
                    profile["jerk"] = float(section.get(key))
                    break
            except ValueError:
                LOG.warning("Invalid jerk value for %s, keeping default %.2f", key, profile["jerk"])
        raw_curr_en = section.get("profile_stepper_current_enabled", str(DEFAULT_PROFILE["stepper_current_enabled"]))
        profile["stepper_current_enabled"] = str(raw_curr_en).strip().lower() == "true"
        try:
            profile["stepper_current_x"] = float(section.get("profile_stepper_current_x", DEFAULT_PROFILE["stepper_current_x"]))
            profile["stepper_current_y"] = float(section.get("profile_stepper_current_y", DEFAULT_PROFILE["stepper_current_y"]))
        except ValueError:
            LOG.warning("Invalid stepper current values, using defaults")
            profile["stepper_current_x"] = DEFAULT_PROFILE["stepper_current_x"]
            profile["stepper_current_y"] = DEFAULT_PROFILE["stepper_current_y"]
        raw_tmc = section.get("profile_tmc_autotune_enabled", str(DEFAULT_PROFILE["tmc_autotune_enabled"]))
        profile["tmc_autotune_enabled"] = str(raw_tmc).strip().lower() == "true"
    # Clamp for safety
    profile["speed_pct"] = max(PROFILE_FLOORS["speed_pct"], profile["speed_pct"])
    profile["accel"] = max(PROFILE_FLOORS["accel"], profile["accel"])
    profile["fan_percent"] = clamp(profile["fan_percent"], PROFILE_FLOORS["fan_percent_min"], PROFILE_FLOORS["fan_percent_max"])
    profile["stepper_current_x"] = clamp(profile["stepper_current_x"], PROFILE_FLOORS["current_min"], PROFILE_FLOORS["current_max"])
    profile["stepper_current_y"] = clamp(profile["stepper_current_y"], PROFILE_FLOORS["current_min"], PROFILE_FLOORS["current_max"])
    return {"schedule": schedule, "profile": profile}


def api_get(path: str) -> Optional[dict]:
    try:
        with urllib.request.urlopen(f"{MOONRAKER_URL}{path}", timeout=5) as resp:
            return json.load(resp)
    except urllib.error.URLError as exc:
        LOG.debug("GET %s failed: %s", path, exc)
        return None


def api_post(path: str, payload: dict) -> bool:
    data = json.dumps(payload).encode("utf-8")
    try:
        req = urllib.request.Request(f"{MOONRAKER_URL}{path}", data=data, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=5):
            return True
    except urllib.error.URLError as exc:
        LOG.debug("POST %s failed: %s", path, exc)
        return False


def set_profile_vars(profile: Dict) -> None:
    cmds = [
        f"SET_GCODE_VARIABLE MACRO=NIGHT_MODE_STATE VARIABLE=profile_speed_pct VALUE={profile['speed_pct']}",
        f"SET_GCODE_VARIABLE MACRO=NIGHT_MODE_STATE VARIABLE=profile_accel VALUE={profile['accel']}",
        f"SET_GCODE_VARIABLE MACRO=NIGHT_MODE_STATE VARIABLE=profile_jerk VALUE={profile['jerk']}",
        f"SET_GCODE_VARIABLE MACRO=NIGHT_MODE_STATE VARIABLE=profile_fan_percent VALUE={profile['fan_percent']}",
        f"SET_GCODE_VARIABLE MACRO=NIGHT_MODE_STATE VARIABLE=profile_stepper_current_enabled VALUE={1 if profile['stepper_current_enabled'] else 0}",
        f"SET_GCODE_VARIABLE MACRO=NIGHT_MODE_STATE VARIABLE=profile_stepper_current_x VALUE={profile['stepper_current_x']}",
        f"SET_GCODE_VARIABLE MACRO=NIGHT_MODE_STATE VARIABLE=profile_stepper_current_y VALUE={profile['stepper_current_y']}",
        f"SET_GCODE_VARIABLE MACRO=NIGHT_MODE_STATE VARIABLE=profile_tmc_autotune_enabled VALUE={1 if profile['tmc_autotune_enabled'] else 0}",
    ]
    api_post("/printer/gcode/script", {"script": "\n".join(cmds)})


def get_state() -> Optional[Dict]:
    res = api_get("/printer/objects/query?gcode_macro%20NIGHT_MODE_STATE")
    if not res or "result" not in res:
        return None
    return res["result"].get("status", {}).get("gcode_macro NIGHT_MODE_STATE", {})


def send_script(script: str) -> None:
    api_post("/printer/gcode/script", {"script": script})


def window_active(now: dt.datetime, start: dt.time, end: dt.time) -> bool:
    today = now.date()
    start_dt = dt.datetime.combine(today, start)
    end_dt = dt.datetime.combine(today, end)
    if end_dt <= start_dt:
        # Crosses midnight
        end_dt += dt.timedelta(days=1)
    if now < start_dt:
        # Maybe we are after midnight in wrap window
        start_dt -= dt.timedelta(days=1)
        end_dt -= dt.timedelta(days=1)
    return start_dt <= now < end_dt


def maybe_clear_hold(state: Dict, in_window: bool) -> None:
    if state.get("manual_hold", 0) and not in_window:
        send_script("SET_GCODE_VARIABLE MACRO=NIGHT_MODE_STATE VARIABLE=manual_hold VALUE=0")


def main() -> None:
    setup_logging()
    LOG.info("Night Mode scheduler starting")
    last_profile: Optional[Dict] = None
    while True:
        cfg = load_config()
        now = dt.datetime.now()
        start_time = parse_time(cfg["schedule"]["start"], DEFAULT_SCHEDULE["start"])
        end_time = parse_time(cfg["schedule"]["end"], DEFAULT_SCHEDULE["end"])
        in_window = cfg["schedule"]["enabled"] and window_active(now, start_time, end_time)

        state = get_state()
        if state is None:
            time.sleep(10)
            continue

        profile = cfg["profile"]
        if profile != last_profile:
            set_profile_vars(profile)
            last_profile = dict(profile)

        active = bool(state.get("active", False))
        manual_hold = bool(state.get("manual_hold", 0))

        if cfg["schedule"]["enabled"]:
            maybe_clear_hold(state, in_window)
            if in_window and (not active) and (not manual_hold):
                LOG.info("Entering Night Mode via schedule")
                send_script("NIGHT_MODE_ON")
            if (not in_window) and active:
                LOG.info("Exiting Night Mode via schedule")
                send_script("NIGHT_MODE_OFF")

        time.sleep(30)


if __name__ == "__main__":
    main()
