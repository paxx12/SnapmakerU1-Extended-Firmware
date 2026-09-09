#!/usr/bin/env python3

import pathlib
import re
import unittest


MODULE_ROOT = pathlib.Path(__file__).parents[1]
ROOT = MODULE_ROOT / "root"
ACE_PY = ROOT / "home/lava/klipper/klippy/extras/ace.py"
FEED_PY = ROOT / "home/lava/klipper/klippy/extras/filament_feed_ace.py"
BG_SWAP_PY = ROOT / "home/lava/klipper/klippy/extras/ace_bg_swap.py"
HOOK_SH = ROOT / "etc/hooks/klipper.d/05-anycubic-ace.sh"
CFG = ROOT / "usr/local/share/firmware-config/tweaks/klipper/ace.cfg"
LAYOUT_PY = ROOT / "usr/local/share/firmware-config/tweaks/klipper/ace/ace_macro_layout.py"


class AceSplitTests(unittest.TestCase):
    def test_runtime_tree_has_no_old_module_paths(self):
        old_module = "multi" + "ace"
        paths = [path.relative_to(MODULE_ROOT).as_posix()
                 for path in MODULE_ROOT.rglob("*")]
        self.assertFalse(any(old_module in path.lower() for path in paths))

        ace_source = ACE_PY.read_text(encoding="utf-8")
        self.assertNotIn("ma" + "ce_log", ace_source)
        old_class = "Multi" + "Ace"
        old_constant = "MULTI" + "ACE_"
        self.assertNotRegex(
            ace_source,
            r"\b(?:%s|%s)\b" % (re.escape(old_class), re.escape(old_constant)),
        )

    def test_topology_checks_use_only_all_heads_and_hybrid(self):
        feed_source = FEED_PY.read_text(encoding="utf-8")
        bg_source = BG_SWAP_PY.read_text(encoding="utf-8")

        self.assertNotRegex(
            feed_source,
            r"_ace_mode[^\n]*(?:'head'|\"head\"|'multi'|\"multi\")",
        )
        self.assertNotRegex(
            bg_source,
            r"_ace_mode[^\n]*(?:'head'|\"head\"|'multi'|\"multi\")",
        )
        self.assertIn("getattr(ace, '_ace_mode', 'all_heads') != 'hybrid'",
                      bg_source)
        self.assertIn("getattr(self.ace, '_ace_mode', 'all_heads') == 'hybrid'",
                      feed_source)

    def test_startup_activation_is_not_gated_by_saved_topology(self):
        hook_source = HOOK_SH.read_text(encoding="utf-8")
        self.assertIn('if [ -f "$ACE_CFG" ]', hook_source)
        self.assertNotIn("ACE_STATE", hook_source)
        self.assertNotIn("ACE_MODE", hook_source)

    def test_visible_macro_definitions_match_the_ace_layout(self):
        cfg_names = set(re.findall(
            r"^\[gcode_macro ([A-Z0-9_]+)\]$", CFG.read_text(encoding="utf-8"),
            re.MULTILINE,
        ))
        internal = {"SET_ACE_MODE", "INNER_RESUME"}
        layout_source = LAYOUT_PY.read_text(encoding="utf-8")
        layout_names = set(re.findall(
            r'"(ACE_[A-Z0-9_]+)"', layout_source,
        ))
        self.assertEqual(cfg_names - internal, layout_names)


if __name__ == "__main__":
    unittest.main()
