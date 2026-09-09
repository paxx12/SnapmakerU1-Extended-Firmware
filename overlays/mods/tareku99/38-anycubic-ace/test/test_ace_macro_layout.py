#!/usr/bin/env python3

import importlib.util
import pathlib
import unittest


SCRIPT = pathlib.Path(__file__).parents[1] / "root/usr/local/share/firmware-config/tweaks/klipper/ace/ace_macro_layout.py"
SPEC = importlib.util.spec_from_file_location("ace_macro_layout", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class AceMacroLayoutTests(unittest.TestCase):
    def test_layout_covers_all_ace_macros_once(self):
        self.assertEqual(len(MODULE.GROUPS), 5)
        self.assertEqual(len(MODULE.ACE_MACRO_NAMES), 27)
        self.assertEqual(len(set(MODULE.ACE_MACRO_KEYS)), 27)

    def test_fluidd_merge_preserves_user_data_and_is_idempotent(self):
        current = {
            "stored": [
                {"name": "PRINT_START", "visible": False, "categoryId": "user"},
                {"name": "ACE_STATUS", "visible": False, "color": "#123456"},
                {"name": "MY_CUSTOM_MACRO", "visible": True},
                {"name": "SET_ACE_MODE", "visible": True},
            ],
            "categories": [{"id": "user", "name": "My Macros"}],
            "expanded": [3],
        }

        updated = MODULE.merge_fluidd_macros(current)
        stored = {item["name"].lower(): item for item in updated["stored"]}

        self.assertEqual(stored["print_start"]["categoryId"], "user")
        self.assertTrue(stored["ace_status"]["visible"])
        self.assertEqual(stored["ace_status"]["color"], "#123456")
        self.assertEqual(stored["ace_status"]["categoryId"], "ace-status")
        self.assertTrue(stored["my_custom_macro"]["visible"])
        self.assertFalse(stored["set_ace_mode"]["visible"])
        self.assertEqual(updated["expanded"], [3])
        self.assertEqual(
            [category["id"] for category in updated["categories"]],
            ["user"] + [group["fluidd_id"] for group in MODULE.GROUPS],
        )
        self.assertEqual(MODULE.merge_fluidd_macros(updated), updated)

    def test_mainsail_merge_preserves_mode_and_adds_panels(self):
        status_id = MODULE.GROUPS[0]["mainsail_id"]
        current = {
            "macros": {
                "mode": "simple",
                "hiddenMacros": ["PRINT_START", "MY_HIDDEN_MACRO"],
                "macrogroups": {
                    status_id: {
                        "name": "ACE | Status",
                        "color": "custom",
                        "colorCustom": "#123456",
                        "showInStandby": True,
                        "showInPrinting": False,
                        "showInPause": True,
                        "macros": [
                            {
                                "pos": 1,
                                "name": "ACE_STATUS",
                                "color": "error",
                                "showInStandby": True,
                                "showInPrinting": False,
                                "showInPause": True,
                            },
                            {"pos": 2, "name": "ACE_AUTOLOAD_1", "color": "group"},
                            {"pos": 3, "name": "MY_CUSTOM_MACRO", "color": "primary"},
                        ],
                    },
                    "user-group": {
                        "name": "User Group",
                        "macros": [
                            {"pos": 1, "name": "ACE_AUTOLOAD_1"},
                            {"pos": 2, "name": "MY_CUSTOM_MACRO"},
                        ],
                    },
                },
            },
            "dashboard": {
                "desktopLayout1": [{"name": "temperature", "visible": True}],
                "mobileLayout": [],
            },
        }

        updated, posts = MODULE.merge_mainsail_namespace(current)
        macros = updated["macros"]
        hidden = {name.lower() for name in macros["hiddenMacros"]}
        groups = macros["macrogroups"]

        self.assertEqual(
            hidden,
            {"print_start", "my_hidden_macro", "set_ace_mode", "inner_resume"},
        )
        self.assertEqual(macros["mode"], "simple")
        self.assertEqual(groups[status_id]["color"], "custom")
        self.assertEqual(groups[status_id]["colorCustom"], "#123456")
        self.assertEqual(
            [macro["name"] for macro in groups[status_id]["macros"]],
            ["ACE_STATUS", "ACE_LIST_DEVICES", "MY_CUSTOM_MACRO"],
        )
        self.assertEqual(
            [macro["name"] for macro in groups["user-group"]["macros"]],
            ["ACE_AUTOLOAD_1", "MY_CUSTOM_MACRO"],
        )

        for group in MODULE.GROUPS:
            self.assertIn(group["mainsail_id"], groups)
            self.assertIn(
                {"name": "macrogroup_" + group["mainsail_id"], "visible": True},
                updated["dashboard"]["desktopLayout1"],
            )
            self.assertIn(
                {"name": "macrogroup_" + group["mainsail_id"], "visible": True},
                updated["dashboard"]["mobileLayout"],
            )

        self.assertTrue(posts)
        _, posts_again = MODULE.merge_mainsail_namespace(updated)
        self.assertEqual(posts_again, [])

    def test_mainsail_merge_from_empty_namespace_creates_every_group(self):
        updated, posts = MODULE.merge_mainsail_namespace({})
        groups = updated["macros"]["macrogroups"]

        self.assertEqual(len(groups), len(MODULE.GROUPS))
        self.assertEqual(
            {key for _, key, _ in posts},
            {"macros.macrogroups." + group["mainsail_id"] for group in MODULE.GROUPS},
        )


if __name__ == "__main__":
    unittest.main()
