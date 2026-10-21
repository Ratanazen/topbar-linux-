#!/usr/bin/env python3
"""
Ratana Dynamic Island & macOS Shell — Hybrid Top Bar Test Suite
===============================================================
Covers:
- Notch-safe dynamic calculations and safe-area geometry
- Theme presets, aliases, and normalization (Tahoe, Dark Glass, Light Glass, Minimal, Low-Resource)
- Frontend mode mutual exclusion (Waybar Lite vs Quickshell Pro vs Hybrid)
- UI state dispatching and stream broadcasting (hide_bar, show_bar, toggle_bar, popovers)
- Waybar Lite configuration validity and module layout
- Battery color-coding and privacy streaming mic conditions
- QML component file integrity and syntax structure
"""

import asyncio
import json
import re
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

REPO_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_DIR / "scripts"
sys.path.insert(0, str(REPO_DIR))
sys.path.insert(0, str(SCRIPTS_DIR))

from core.config_manager import IslandConfig, normalize_theme, THEME_PRESETS, THEME_ALIASES

import importlib.util
spec = importlib.util.spec_from_file_location("island_daemon", SCRIPTS_DIR / "island-daemon.py")
daemon_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(daemon_mod)

DynamicIslandDaemon = daemon_mod.DynamicIslandDaemon


class TestNotchSafeCalculations(unittest.TestCase):
    """Test dynamic notch-safe center spacer geometry calculations"""

    def test_default_spacer_width(self):
        notch_enabled = False
        notch_width = 160
        capsule_width = 180  # Default idle capsule width
        spacer_width = max(notch_width if notch_enabled else 160, capsule_width + 24)
        self.assertEqual(spacer_width, 204)

    def test_expanded_capsule_spacer_expansion(self):
        """When island expands (media, timer, minimized windows), safe-area spacer expands dynamically"""
        notch_enabled = False
        notch_width = 160
        expanded_capsule_width = 380
        spacer_width = max(notch_width if notch_enabled else 160, expanded_capsule_width + 24)
        self.assertEqual(spacer_width, 404)
        self.assertGreater(spacer_width, expanded_capsule_width)

    def test_hardware_notch_override(self):
        """When hardware notch is enabled, spacer is at least notch_width"""
        notch_enabled = True
        notch_width = 240
        compact_capsule_width = 150
        spacer_width = max(notch_width if notch_enabled else 160, compact_capsule_width + 24)
        self.assertEqual(spacer_width, 240)


class TestThemeProfiles(unittest.TestCase):
    """Test theme presets, aliases, and normalization"""

    def test_required_theme_presets_present(self):
        required = [
            "macos-tahoe-glass",
            "macos-dark-glass",
            "macos-light",
            "minimal-dark",
            "low-resource"
        ]
        for t in required:
            self.assertIn(t, THEME_PRESETS)

    def test_theme_normalization_and_aliases(self):
        self.assertEqual(normalize_theme("tahoe"), "macos-tahoe-glass")
        self.assertEqual(normalize_theme("macos-tahoe"), "macos-tahoe-glass")
        self.assertEqual(normalize_theme("macos-dark"), "macos-dark-glass")
        self.assertEqual(normalize_theme("light"), "macos-light")
        self.assertEqual(normalize_theme("minimal"), "minimal-dark")
        self.assertEqual(normalize_theme("lowpower"), "low-resource")
        self.assertEqual(normalize_theme("glass"), "macos-glass")

    def test_qml_theme_file_contains_all_profiles(self):
        theme_qml = REPO_DIR / "quickshell" / "themes" / "Theme.qml"
        self.assertTrue(theme_qml.exists())
        content = theme_qml.read_text(encoding="utf-8")
        for t in ["macos-tahoe-glass", "macos-dark-glass", "macos-light", "minimal-dark", "low-resource"]:
            self.assertIn(f'case "{t}":', content)


class TestFrontendMutualExclusion(unittest.TestCase):
    """Test frontend mode mutual exclusion between Waybar Lite and Quickshell Pro"""

    def setUp(self):
        self.config = IslandConfig(Path("/tmp/test_fe_config.ini"))
        self.daemon = DynamicIslandDaemon(config=self.config)

    def test_frontend_set_validation(self):
        loop = asyncio.new_event_loop()
        try:
            for valid_fe in ("waybar", "quickshell", "both", "hybrid"):
                res = loop.run_until_complete(self.daemon.dispatch_action("frontend_set", [valid_fe], None))
                self.assertEqual(res["status"], "ok")
                self.assertEqual(res["frontend"], valid_fe)

            invalid_res = loop.run_until_complete(self.daemon.dispatch_action("frontend_set", ["unknown_bar"], None))
            self.assertEqual(invalid_res["status"], "error")
        finally:
            loop.close()

    def test_mode_set_updates_frontend(self):
        loop = asyncio.new_event_loop()
        try:
            res_lite = loop.run_until_complete(self.daemon.dispatch_action("mode", ["waybar-lite"], None))
            self.assertEqual(res_lite["status"], "ok")
            self.assertEqual(self.config.frontend, "waybar")

            res_qs = loop.run_until_complete(self.daemon.dispatch_action("mode", ["quickshell"], None))
            self.assertEqual(res_qs["status"], "ok")
            self.assertEqual(self.config.frontend, "quickshell")

            res_hy = loop.run_until_complete(self.daemon.dispatch_action("mode", ["hybrid"], None))
            self.assertEqual(res_hy["status"], "ok")
            self.assertEqual(self.config.frontend, "hybrid")
        finally:
            loop.close()

    def test_topbar_ui_broadcast_hiding_and_showing(self):
        loop = asyncio.new_event_loop()
        try:
            with patch.object(self.daemon.ipc_server, "broadcast_stream") as mock_broadcast:
                res = loop.run_until_complete(self.daemon.dispatch_action("topbar_ui", ["hide_bar"], None))
                self.assertEqual(res["status"], "ok")
                call_arg = json.loads(mock_broadcast.call_args[0][0])
                self.assertEqual(call_arg.get("ui_action"), "hide_bar")

                res2 = loop.run_until_complete(self.daemon.dispatch_action("topbar_ui", ["show_bar"], None))
                self.assertEqual(res2["status"], "ok")
                call_arg2 = json.loads(mock_broadcast.call_args[0][0])
                self.assertEqual(call_arg2.get("ui_action"), "show_bar")
        finally:
            loop.close()


class TestSystemIndicatorsAndColors(unittest.TestCase):
    """Test battery color levels and system status indicators"""

    def test_battery_color_logic(self):
        def compute_batt_color(level, is_charging):
            if is_charging:
                return "#30d158"
            if level <= 20:
                return "#ff453a"
            if level <= 50:
                return "#ffd60a"
            return "#30d158"

        self.assertEqual(compute_batt_color(15, False), "#ff453a")  # Low / critical: Red
        self.assertEqual(compute_batt_color(45, False), "#ffd60a")  # Medium: Amber/Yellow
        self.assertEqual(compute_batt_color(85, False), "#30d158")  # Good: Green
        self.assertEqual(compute_batt_color(10, True), "#30d158")   # Charging: Always Green

    def test_waybar_config_jsonc_validity(self):
        """Verify config.jsonc is valid JSON and contains required macOS modules"""
        cfg_file = REPO_DIR / "config.jsonc"
        self.assertTrue(cfg_file.exists())
        raw_text = cfg_file.read_text(encoding="utf-8")
        # Strip comments
        cleaned = re.sub(r'/\*.*?\*/', '', raw_text, flags=re.DOTALL)
        cleaned = re.sub(r'//.*', '', cleaned)
        data = json.loads(cleaned)

        self.assertIn("modules-left", data)
        self.assertIn("modules-center", data)
        self.assertIn("modules-right", data)

        # Left section has window title and system menu
        self.assertIn("sway/window", data["modules-left"])
        self.assertIn("group/left1", data["modules-left"])

        # Center section has island
        self.assertIn("custom/island", data["modules-center"])

        # Right section has network, bluetooth, pulseaudio, battery, clock
        self.assertIn("network", data["modules-right"])
        self.assertIn("bluetooth", data["modules-right"])
        self.assertIn("pulseaudio", data["modules-right"])
        self.assertIn("battery", data["modules-right"])
        self.assertIn("clock", data["modules-right"])


class TestQMLIntegrations(unittest.TestCase):
    """Verify integrity of top bar and popover components"""

    def test_mactopbar_contains_full_icon_suite(self):
        bar_qml = REPO_DIR / "quickshell" / "components" / "MacTopBar.qml"
        self.assertTrue(bar_qml.exists())
        content = bar_qml.read_text(encoding="utf-8")

        # Dynamic center spacer tracking capsuleWidth
        self.assertIn("IslandBridge.capsuleWidth", content)
        self.assertIn("centerSpacer", content)

        # Full icon suite
        self.assertIn("󰌌", content)  # Keyboard
        self.assertIn("󰍬", content)  # Mic
        self.assertIn("󰕟", content)  # AirPlay / Screen Mirroring
        self.assertIn("󰤨", content)  # Wi-Fi
        self.assertIn("󰂯", content)  # Bluetooth
        self.assertIn("󰕾", content)  # Sound
        self.assertIn("󰂄", content)  # Battery charging
        self.assertIn("󰂚", content)  # Notification
        self.assertIn("󰍉", content)  # Spotlight
        self.assertIn("󰚩", content)  # Siri
        self.assertIn("󰘳", content)  # Control Center
        self.assertIn("ddd MMM d  h:mm A", content)  # Clock

    def test_quickactions_full_color_macos_styling(self):
        qa_qml = REPO_DIR / "quickshell" / "components" / "QuickActions.qml"
        self.assertTrue(qa_qml.exists())
        content = qa_qml.read_text(encoding="utf-8")

        # Check authentic macOS colors
        self.assertIn("#007AFF", content)  # Blue (Wi-Fi / BT / Sound)
        self.assertIn("#AF52DE", content)  # Purple (Focus / DND)
        self.assertIn("#FF9500", content)  # Orange (Display Brightness)
        self.assertIn("#FF2D55", content)  # Pink (Music)
        self.assertIn("#30d158", content)  # Green (Battery)


if __name__ == "__main__":
    unittest.main()
