#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-PackageHomePage: https://github.com/paxx12-snapmaker-u1/SnapmakerU1-Extended-Firmware
# SPDX-FileCopyrightText: Copyright (c) 2026 @paxx12

"""Install the ACE macro layout in Fluidd and Mainsail.

The two frontends intentionally have separate storage formats.  This helper
keeps the ACE layout in one place, merges it into the existing frontend data,
and writes it through Moonraker's public database API.
"""

import argparse
import copy
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid


MOONRAKER_URL = "http://127.0.0.1:7125"
ACE_LAYOUT_NAMESPACE = "https://github.com/paxx12-snapmaker-u1/SnapmakerU1-Extended-Firmware/ace/macro-group/"
MAINSAIL_LAYOUTS = (
    "mobileLayout",
    "tabletLayout1",
    "tabletLayout2",
    "desktopLayout1",
    "desktopLayout2",
    "widescreenLayout1",
    "widescreenLayout2",
    "widescreenLayout3",
)


def _group(key, name, color, macros, show_in_printing=False, show_in_pause=False):
    return {
        "key": key,
        "name": name,
        "fluidd_id": "ace-" + key,
        "mainsail_id": str(uuid.uuid5(uuid.NAMESPACE_URL, ACE_LAYOUT_NAMESPACE + key)),
        "color": color,
        "show_in_standby": True,
        "show_in_printing": show_in_printing,
        "show_in_pause": show_in_pause,
        "macros": tuple(macros),
    }


# This is the single ACE layout definition.  The names are the actual Klipper
# macro names from ace.cfg; only the frontend grouping is managed here.
GROUPS = (
    _group(
        "status",
        "ACE | Status",
        "primary",
        ("ACE_STATUS", "ACE_LIST_DEVICES"),
        show_in_printing=True,
        show_in_pause=True,
    ),
    _group(
        "loading",
        "ACE | Loading",
        "success",
        (
            "ACE_AUTOLOAD_1",
            "ACE_AUTOLOAD_2",
            "ACE_AUTOLOAD_3",
            "ACE_AUTOLOAD_4",
            "ACE_LOAD_T0",
            "ACE_LOAD_T1",
            "ACE_LOAD_T2",
            "ACE_LOAD_T3",
        ),
        show_in_pause=True,
    ),
    _group(
        "unloading",
        "ACE | Unloading",
        "warning",
        (
            "ACE_UNLOAD_ALL",
            "ACE_UNLOAD_T0",
            "ACE_UNLOAD_T1",
            "ACE_UNLOAD_T2",
            "ACE_UNLOAD_T3",
        ),
        show_in_pause=True,
    ),
    _group(
        "tool-switching",
        "ACE | Tool Switching",
        "secondary",
        (
            "ACE_SELECT_1",
            "ACE_SELECT_2",
            "ACE_SELECT_3",
            "ACE_SELECT_4",
        ),
        show_in_pause=True,
    ),
    _group(
        "drying",
        "ACE | Drying",
        "primary",
        (
            "ACE_DRY_START_1",
            "ACE_DRY_START_2",
            "ACE_DRY_START_3",
            "ACE_DRY_START_4",
            "ACE_DRY_STOP_1",
            "ACE_DRY_STOP_2",
            "ACE_DRY_STOP_3",
            "ACE_DRY_STOP_4",
        ),
    ),
)

ACE_MACRO_NAMES = tuple(macro for group in GROUPS for macro in group["macros"])
ACE_MACRO_KEYS = {name.lower() for name in ACE_MACRO_NAMES}

# These names belonged to an earlier ACE macro panel.  They are removed when
# the layout is applied so an existing frontend database does not show
# duplicate controls beside the canonical ACE names.  This is deliberately
# limited to ACE-owned names; unrelated user macros and groups are preserved.
STALE_ACE_MACRO_NAMES = (
    "ACEA__SWITCH_0",
    "ACEA__SWITCH_1",
    "ACEA__SWITCH_2",
    "ACEA__SWITCH_3",
    "ACEB__LOAD_0",
    "ACEB__LOAD_1",
    "ACEB__LOAD_2",
    "ACEB__LOAD_3",
    "ACEC__UNLOAD_ALL",
    "ACEC__UNLOAD_T0",
    "ACEC__UNLOAD_T1",
    "ACEC__UNLOAD_T2",
    "ACEC__UNLOAD_T3",
    "ACEC__LOAD_T0",
    "ACEC__LOAD_T1",
    "ACEC__LOAD_T2",
    "ACEC__LOAD_T3",
    "ACED__DRY_START_0",
    "ACED__DRY_START_1",
    "ACED__DRY_START_2",
    "ACED__DRY_START_3",
    "ACED__DRY_STOP",
    "ACEF__MODE_NORMAL",
    "ACEF__MODE_MULTI",
    "ACEG__STATUS",
    "ACEG__LIST",
    "ACEH__UPDATE_CHECK",
    "ACEH__UPDATE_APPLY",
)
STALE_ACE_MACRO_KEYS = {name.lower() for name in STALE_ACE_MACRO_NAMES}

# These macros remain available to Klipper because the topology and recovery
# code uses them internally, but they are not user-facing controls.
INTERNAL_ACE_MACRO_NAMES = ("SET_ACE_MODE", "INNER_RESUME")
INTERNAL_ACE_MACRO_KEYS = {name.lower() for name in INTERNAL_ACE_MACRO_NAMES}
HIDDEN_ACE_MACRO_KEYS = STALE_ACE_MACRO_KEYS | INTERNAL_ACE_MACRO_KEYS


def _dict(value):
    return value if isinstance(value, dict) else {}


def _list(value):
    return value if isinstance(value, list) else []


class MoonrakerClient:
    def __init__(self, base_url=MOONRAKER_URL, timeout=8, dry_run=False):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.dry_run = dry_run

    def _url(self, namespace, key=None):
        params = {"namespace": namespace}
        if key is not None:
            params["key"] = key
        return self.base_url + "/server/database/item?" + urllib.parse.urlencode(params)

    @staticmethod
    def _decode_response(response):
        data = json.loads(response.read().decode("utf-8"))
        if isinstance(data, dict) and data.get("error"):
            raise RuntimeError("Moonraker error: " + json.dumps(data["error"], sort_keys=True))
        result = data.get("result") if isinstance(data, dict) else None
        if isinstance(result, dict) and "value" in result:
            return result["value"]
        return result

    def get(self, namespace, key=None):
        request = urllib.request.Request(self._url(namespace, key), method="GET")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return self._decode_response(response)
        except urllib.error.HTTPError as error:
            if error.code == 404:
                return None
            try:
                detail = error.read().decode("utf-8", errors="replace")
            except Exception:
                detail = str(error)
            raise RuntimeError("Moonraker GET failed: " + detail) from error
        except urllib.error.URLError as error:
            raise RuntimeError("Moonraker is unavailable: " + str(error.reason)) from error

    def post(self, namespace, key, value):
        payload = json.dumps({"namespace": namespace, "key": key, "value": value}).encode("utf-8")
        request = urllib.request.Request(
            self.base_url + "/server/database/item",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        if self.dry_run:
            print("DRY-RUN POST " + namespace + "." + key)
            return
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                self._decode_response(response)
        except urllib.error.HTTPError as error:
            try:
                detail = error.read().decode("utf-8", errors="replace")
            except Exception:
                detail = str(error)
            raise RuntimeError("Moonraker POST failed: " + detail) from error
        except urllib.error.URLError as error:
            raise RuntimeError("Moonraker is unavailable: " + str(error.reason)) from error


def _case_index(items):
    index = {}
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            continue
        index.setdefault(item["name"].lower(), item)
    return index


def merge_fluidd_macros(current):
    """Return a Fluidd macro state with ACE categories assigned."""
    state = copy.deepcopy(_dict(current))
    categories = _list(state.get("categories"))
    stored = [
        item
        for item in _list(state.get("stored"))
        if not (
            isinstance(item, dict)
            and isinstance(item.get("name"), str)
            and item["name"].lower() in STALE_ACE_MACRO_KEYS
        )
    ]
    for item in stored:
        if (
            isinstance(item, dict)
            and isinstance(item.get("name"), str)
            and item["name"].lower() in INTERNAL_ACE_MACRO_KEYS
        ):
            item["visible"] = False

    owned_ids = {group["fluidd_id"] for group in GROUPS}
    category_by_id = {
        category.get("id"): category
        for category in categories
        if isinstance(category, dict) and category.get("id") is not None
    }
    owned_categories = []
    for group in GROUPS:
        category = copy.deepcopy(category_by_id.get(group["fluidd_id"], {}))
        category["id"] = group["fluidd_id"]
        category["name"] = group["name"]
        owned_categories.append(category)

    # Keep all user-created categories and their order, then put the ACE
    # categories together so the umbrella name is easy to scan.
    state["categories"] = [
        category
        for category in categories
        if not isinstance(category, dict) or category.get("id") not in owned_ids
    ] + owned_categories

    stored_by_name = _case_index(stored)
    for group in GROUPS:
        for name in group["macros"]:
            existing = stored_by_name.get(name.lower())
            if existing is None:
                existing = {"name": name, "visible": True}
                stored.append(existing)
                stored_by_name[name.lower()] = existing
            existing["name"] = name
            # ACE controls should be usable after the feature is enabled.  A
            # prior stale Fluidd record can have visible=false even though
            # the macro exists; category assignment alone would leave it
            # missing from the dashboard.
            existing["visible"] = True
            existing["categoryId"] = group["fluidd_id"]

    state["stored"] = stored
    state.setdefault("expanded", [])
    return state


def _mainsail_macro_defaults(group, position, name):
    return {
        "pos": position,
        "name": name,
        "color": "group",
        "showInStandby": group["show_in_standby"],
        "showInPrinting": group["show_in_printing"],
        "showInPause": group["show_in_pause"],
    }


def merge_mainsail_group(current, group):
    """Return one Mainsail macro group, preserving user customizations."""
    existing = copy.deepcopy(_dict(current))
    existing.setdefault("name", group["name"])
    existing.setdefault("color", group["color"])
    existing.setdefault("showInStandby", group["show_in_standby"])
    existing.setdefault("showInPrinting", group["show_in_printing"])
    existing.setdefault("showInPause", group["show_in_pause"])

    old_macros = _list(existing.get("macros"))
    ace_by_name = {}
    extras = []
    target_names = {name.lower() for name in group["macros"]}
    for macro in old_macros:
        if not isinstance(macro, dict) or not isinstance(macro.get("name"), str):
            extras.append(macro)
        elif macro["name"].lower() in target_names:
            ace_by_name.setdefault(macro["name"].lower(), macro)
        elif macro["name"].lower() in ACE_MACRO_KEYS:
            # This is an ACE macro belonging to another ACE-owned group.
            # It will be rebuilt in its canonical group below.
            continue
        elif macro["name"].lower() in HIDDEN_ACE_MACRO_KEYS:
            # Remove stale and internal ACE controls instead of carrying them
            # forward as clickable extras.
            continue
        else:
            extras.append(macro)

    merged_macros = []
    for position, name in enumerate(group["macros"], start=1):
        macro = copy.deepcopy(ace_by_name.get(name.lower(), {}))
        defaults = _mainsail_macro_defaults(group, position, name)
        macro.update({"pos": position, "name": name})
        for key, value in defaults.items():
            macro.setdefault(key, value)
        merged_macros.append(macro)

    # Do not delete unrelated macros a user may have added to an ACE panel.
    for offset, macro in enumerate(extras, start=len(merged_macros) + 1):
        if isinstance(macro, dict):
            macro["pos"] = offset
        merged_macros.append(macro)
    existing["macros"] = merged_macros
    return existing


def _remove_from_owned_mainsail_groups(current, target_group):
    state = copy.deepcopy(_dict(current))
    macros = _dict(state.get("macros"))
    groups = _dict(macros.get("macrogroups"))
    target_names = {name.lower() for name in target_group["macros"]}

    for group in GROUPS:
        if group["key"] == target_group["key"]:
            continue
        group_state = groups.get(group["mainsail_id"])
        if not isinstance(group_state, dict):
            continue
        group_state["macros"] = [
            macro
            for macro in _list(group_state.get("macros"))
            if not (
                isinstance(macro, dict)
                and isinstance(macro.get("name"), str)
                and macro["name"].lower() in target_names
            )
        ]
    return state


def merge_mainsail_namespace(current):
    """Return Mainsail data plus the keys that should be posted."""
    original = copy.deepcopy(_dict(current))
    state = copy.deepcopy(original)
    macros_state = _dict(state.get("macros"))
    groups_state = _dict(macros_state.get("macrogroups"))
    for group_state in groups_state.values():
        if not isinstance(group_state, dict):
            continue
        group_state["macros"] = [
            macro
            for macro in _list(group_state.get("macros"))
            if not (
                isinstance(macro, dict)
                and isinstance(macro.get("name"), str)
                and macro["name"].lower() in HIDDEN_ACE_MACRO_KEYS
            )
        ]
    hidden_macros = _list(macros_state.get("hiddenMacros"))
    hidden_macros = [
        name
        for name in hidden_macros
        if not (
            isinstance(name, str)
            and name.lower() in STALE_ACE_MACRO_KEYS
        )
    ]
    hidden_macros.extend(INTERNAL_ACE_MACRO_NAMES)
    macros_state["hiddenMacros"] = list(dict.fromkeys(hidden_macros))
    # Attach newly-created containers before the loop.  Without this, an
    # entirely new Mainsail namespace would lose every group except the last
    # one while the merge loop copied the state.
    macros_state["macrogroups"] = groups_state
    state["macros"] = macros_state

    for group in GROUPS:
        # Remove an ACE macro from any other ACE-owned group before assigning
        # it to its canonical group.  User-created groups are untouched.
        state = _remove_from_owned_mainsail_groups(state, group)
        macros_state = _dict(state.get("macros"))
        groups_state = _dict(macros_state.get("macrogroups"))
        groups_state[group["mainsail_id"]] = merge_mainsail_group(
            groups_state.get(group["mainsail_id"]), group
        )

    macros_state["macrogroups"] = groups_state
    state["macros"] = macros_state

    dashboard = _dict(state.get("dashboard"))
    updated_layouts = {}
    for layout_name in MAINSAIL_LAYOUTS:
        layout = dashboard.get(layout_name)
        if not isinstance(layout, list):
            continue
        layout = copy.deepcopy(layout)
        for group in GROUPS:
            panel_name = "macrogroup_" + group["mainsail_id"]
            if not any(isinstance(entry, dict) and entry.get("name") == panel_name for entry in layout):
                layout.append({"name": panel_name, "visible": True})
        if layout != dashboard.get(layout_name):
            updated_layouts[layout_name] = layout
            dashboard[layout_name] = layout
    if dashboard:
        state["dashboard"] = dashboard

    posts = []
    original_groups = _dict(_dict(original.get("macros")).get("macrogroups"))
    for group in GROUPS:
        group_id = group["mainsail_id"]
        if groups_state.get(group_id) != original_groups.get(group_id):
            posts.append(("mainsail", "macros.macrogroups." + group_id, groups_state[group_id]))

    for layout_name, layout in updated_layouts.items():
        posts.append(("mainsail", "dashboard." + layout_name, layout))
    return state, posts


def apply_fluidd(client):
    current = client.get("fluidd", "macros")
    updated = merge_fluidd_macros(current)
    if updated != _dict(current):
        client.post("fluidd", "macros", updated)
        return True
    return False


def apply_mainsail(client):
    current = client.get("mainsail")
    _, posts = merge_mainsail_namespace(current)
    for namespace, key, value in posts:
        client.post(namespace, key, value)
    mode = _dict(_dict(current).get("macros")).get("mode", "simple")
    if mode != "expert":
        print(
            "NOTE: Mainsail ACE panels are saved; switch Mainsail to Expert Mode "
            "under Settings > Macros to display them.",
            file=sys.stderr,
        )
    return bool(posts)


def apply_layout(client):
    results = []
    errors = []
    for frontend, function in (("Fluidd", apply_fluidd), ("Mainsail", apply_mainsail)):
        try:
            changed = function(client)
            results.append(frontend + (" updated" if changed else " already up to date"))
        except Exception as error:
            errors.append(frontend + ": " + str(error))

    for result in results:
        print(result)
    for error in errors:
        print("WARNING: " + error, file=sys.stderr)
    if errors and not results:
        raise RuntimeError("No frontend layout could be updated")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Apply the ACE macro layout to Fluidd and Mainsail")
    parser.add_argument("command", choices=("apply",), help="layout operation to perform")
    parser.add_argument("--url", default=MOONRAKER_URL, help="Moonraker base URL")
    parser.add_argument("--dry-run", action="store_true", help="show database writes without sending them")
    parser.add_argument(
        "--best-effort",
        action="store_true",
        help="report frontend errors without failing the ACE enable operation",
    )
    args = parser.parse_args(argv)
    client = MoonrakerClient(args.url, dry_run=args.dry_run)
    try:
        apply_layout(client)
        return 0
    except Exception as error:
        print("ERROR: " + str(error), file=sys.stderr)
        return 0 if args.best_effort else 1


if __name__ == "__main__":
    sys.exit(main())
