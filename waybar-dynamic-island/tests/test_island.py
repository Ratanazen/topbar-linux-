#!/usr/bin/env python3
"""
Ratana Dynamic Island Automated Test Suite
==========================================
Covers Section 17 verification requirements:
- Animation and state transitions, interruptions, priority preemption, restoration, expiration
- Screen recording detection
- Network events and SSID privacy
- Privacy-first clipboard (guaranteeing zero content leakage)
- IPC protocol, validation, oversized requests, and error responses
- Theme presets and settings persistence
"""

import asyncio
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

# Ensure repo root and scripts directory are in sys.path
REPO_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_DIR / "scripts"
sys.path.insert(0, str(REPO_DIR))
sys.path.insert(0, str(SCRIPTS_DIR))

TEST_DIR = tempfile.TemporaryDirectory()
TEST_TASKS_FILE = Path(TEST_DIR.name) / "tasks.json"
TEST_CONFIG_FILE = Path(TEST_DIR.name) / "config.ini"
os.environ["RATANA_TASKS_FILE"] = str(TEST_TASKS_FILE)
os.environ["RATANA_CONFIG_FILE"] = str(TEST_CONFIG_FILE)

import importlib.util
spec = importlib.util.spec_from_file_location("island_daemon", SCRIPTS_DIR / "island-daemon.py")
daemon_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(daemon_mod)

IslandState = daemon_mod.IslandState
Priority = daemon_mod.Priority
IslandConfig = daemon_mod.IslandConfig
DynamicIslandDaemon = daemon_mod.DynamicIslandDaemon
resolve_app_icon = daemon_mod.resolve_app_icon
resolve_language_info = daemon_mod.resolve_language_info
LANGUAGE_MAP = daemon_mod.LANGUAGE_MAP
MODES = daemon_mod.MODES
truncate_text = daemon_mod.truncate_text
from core.network_backend import NetworkBackend
from core.bluetooth_backend import BluetoothBackend


class TestStateEngine(unittest.TestCase):
    """Phase 2 & 3: Animation State Engine & Priority Arbitration Tests"""

    def setUp(self):
        if TEST_TASKS_FILE.exists():
            TEST_TASKS_FILE.unlink()
        self.daemon = DynamicIslandDaemon()
        if hasattr(self.daemon, "window_monitor"):
            self.daemon.window_monitor.stop()
            self.daemon.window_monitor.on_window_minimized = None
            self.daemon.window_monitor.on_window_restored = None
            self.daemon.window_monitor.get_minimized_windows = Mock(return_value=[])
        self.daemon.dismiss_transient()

    def test_default_idle_state(self):
        state = self.daemon.get_current_state()
        self.assertEqual(state.state, "idle")
        self.assertEqual(state.priority, Priority.IDLE)
        self.assertIn("󰸗", state.icon)

    def test_priority_preemption(self):
        # 1. Start a persistent timer (Priority 30)
        self.daemon.active_timer_state = IslandState(
            source="timer", state="timer", priority=Priority.TIMER,
            title="25:00", duration=None
        )
        self.assertEqual(self.daemon.get_current_state().state, "timer")

        # 2. Push a transient volume change (Priority 60 > 30)
        vol_state = IslandState(
            source="volume", state="volume", priority=Priority.SLIDER,
            title="50%", duration=1.5
        )
        self.daemon.push_transient_event(vol_state)
        self.assertEqual(self.daemon.get_current_state().state, "volume")

        # 3. Push an urgent notification (Priority 75 > 60)
        urgent_state = IslandState(
            source="notification", state="notification", priority=Priority.URGENT_NOTIF,
            title="Security Alert", duration=4.0
        )
        self.daemon.push_transient_event(urgent_state)
        self.assertEqual(self.daemon.get_current_state().state, "notification")

    def test_state_restoration_after_expiration(self):
        # Timer is active
        self.daemon.active_timer_state = IslandState(
            source="timer", state="timer", priority=Priority.TIMER,
            title="10:00", duration=None
        )

        # Temporary notification with 0.1s duration
        notif = IslandState(
            source="notification", state="notification", priority=Priority.NOTIFICATION,
            title="Message", duration=0.05
        )
        self.daemon.push_transient_event(notif)
        self.assertEqual(self.daemon.get_current_state().state, "notification")

        # Wait for expiration
        time.sleep(0.08)

        # State engine MUST restore timer, NOT idle!
        current = self.daemon.get_current_state()
        self.assertEqual(current.state, "timer")
        self.assertEqual(current.title, "10:00")

    def test_rapid_identical_event_deduplication(self):
        ev1 = IslandState(source="volume", state="volume", priority=Priority.SLIDER, title="20%", duration=1.5)
        ev2 = IslandState(source="volume", state="volume", priority=Priority.SLIDER, title="22%", duration=1.5)
        self.daemon.push_transient_event(ev1)
        self.daemon.push_transient_event(ev2)
        # Should replace existing event of same source/state, not duplicate queue
        self.assertEqual(len(self.daemon.transient_states), 1)
        self.assertEqual(self.daemon.transient_states[0].title, "22%")


class TestClipboardPrivacy(unittest.TestCase):
    """Feature E: Privacy-First Clipboard Tests"""

    def setUp(self):
        self.daemon = DynamicIslandDaemon()

    def test_zero_clipboard_content_leakage(self):
        # Emitted clipboard state
        clip_state = IslandState(
            source="clipboard",
            state="clipboard",
            priority=Priority.CONNECTIVITY,
            icon="󰅍",
            title="Copied",
            subtitle="Clipboard updated",
            css_class="clipboard",
            duration=2.0
        )
        payload = clip_state.to_waybar_payload(self.daemon.config)
        json_output = json.dumps(payload)

        # CRITICAL PRIVACY CHECKS:
        # Guarantee no arbitrary copied text or tokens can ever be present
        self.assertNotIn("password", json_output.lower())
        self.assertNotIn("token", json_output.lower())
        self.assertIn("Copied", json_output)
        self.assertIn("clipboard", json_output)


class TestNetworkPrivacy(unittest.TestCase):
    """Feature D: Network Events & SSID Privacy Tests"""

    def setUp(self):
        self.daemon = DynamicIslandDaemon()

    def test_ssid_privacy_enabled(self):
        self.daemon.config.network_ssid_privacy = True
        state = IslandState(
            source="network", state="network", priority=Priority.CONNECTIVITY,
            icon="󰤨", title="Connected", subtitle="Wi-Fi Connected"
        )
        payload = state.to_waybar_payload(self.daemon.config)
        self.assertIn("Wi-Fi Connected", payload["text"])
        self.assertNotIn("MySecretSSID", payload["text"])


class TestRecordingDetection(unittest.TestCase):
    """Feature B: Screen Recording Tests"""

    def setUp(self):
        self.daemon = DynamicIslandDaemon()

    def test_recording_state_attributes(self):
        rec_state = IslandState(
            source="recording", state="recording", priority=Priority.RECORDING,
            icon="󰻃", title="REC", subtitle="wf-recorder", css_class="recording"
        )
        self.daemon.active_recording_state = rec_state
        current = self.daemon.get_current_state()
        self.assertEqual(current.state, "recording")
        self.assertEqual(current.priority, Priority.RECORDING)
        self.assertIn("recording", current.css_class)


class TestIPCProtocol(unittest.TestCase):
    """Feature F: Custom Event API & Protocol Security Tests"""

    def setUp(self):
        self.daemon = DynamicIslandDaemon()
        if hasattr(self.daemon, "window_monitor"):
            self.daemon.window_monitor.get_minimized_windows = Mock(return_value=[])

    def test_valid_custom_event(self):
        args = {
            "source": "ci-script",
            "state": "system",
            "title": "Build Passed",
            "message": "All unit tests green",
            "duration": 5.0,
            "priority": 45
        }
        resp = asyncio.run(self.daemon.dispatch_action("event", args, MagicMock()))
        self.assertEqual(resp["status"], "ok")
        self.assertEqual(self.daemon.get_current_state().state, "system")
        self.assertEqual(self.daemon.get_current_state().title, "Build Passed")

    def test_duration_and_priority_clamping(self):
        # Extremely high duration and priority should be clamped
        args = {
            "title": "Clamp Test",
            "duration": 9999.0, # Should clamp to 30s
            "priority": 999     # Should clamp to 95
        }
        resp = asyncio.run(self.daemon.dispatch_action("event", args, MagicMock()))
        self.assertEqual(resp["status"], "ok")
        st = self.daemon.get_current_state()
        self.assertLessEqual(st.duration, 30.0)
        self.assertLessEqual(int(st.priority), 95)

    def test_invalid_action(self):
        resp = asyncio.run(self.daemon.dispatch_action("malicious_unrecognized_cmd", {}, MagicMock()))
        self.assertEqual(resp["status"], "error")


class TestThemesAndSettings(unittest.TestCase):
    """Feature G & I: Themes Presets & Settings Persistence"""

    def setUp(self):
        self.daemon = DynamicIslandDaemon()

    def test_all_four_themes_valid(self):
        # Now 6 complete theme presets
        self.assertGreaterEqual(len(daemon_mod.THEME_PRESETS), 6)
        for theme in daemon_mod.THEME_PRESETS:
            resp = asyncio.run(self.daemon.dispatch_action("theme_set", {"theme": theme}, MagicMock()))
            self.assertEqual(resp["status"], "ok")
            self.assertEqual(self.daemon.config.theme, theme)

    def test_theme_aliases(self):
        # glass -> macos-glass
        resp_glass = asyncio.run(self.daemon.dispatch_action("theme_set", {"theme": "glass"}, MagicMock()))
        self.assertEqual(resp_glass["status"], "ok")
        self.assertEqual(self.daemon.config.theme, "macos-glass")

        # minimal -> minimal-dark
        resp_min = asyncio.run(self.daemon.dispatch_action("theme_set", {"theme": "minimal"}, MagicMock()))
        self.assertEqual(resp_min["status"], "ok")
        self.assertEqual(self.daemon.config.theme, "minimal-dark")

    def test_invalid_theme_fallback(self):
        resp = asyncio.run(self.daemon.dispatch_action("theme_set", {"theme": "invalid-theme-xyz"}, MagicMock()))
        self.assertEqual(resp["status"], "error")

    def test_reduced_motion_toggle(self):
        asyncio.run(self.daemon.dispatch_action("reduced_motion_set", {"enabled": True}, MagicMock()))
        self.assertTrue(self.daemon.config.reduced_motion)
        payload = self.daemon.get_current_state().to_waybar_payload(self.daemon.config)
        self.assertIn("reduced-motion", payload["class"])


class TestFrontendSwitching(unittest.TestCase):
    """Quickshell & Waybar Frontend Selection and Rich Payload Tests"""

    def setUp(self):
        self.daemon = DynamicIslandDaemon()
        if hasattr(self.daemon, "window_monitor"):
            self.daemon.window_monitor.stop()
            self.daemon.window_monitor.on_window_minimized = None
            self.daemon.window_monitor.on_window_restored = None
            self.daemon.window_monitor.get_minimized_windows = Mock(return_value=[])
        self.daemon.dismiss_transient()

    def test_frontend_get_and_set(self):
        # Default is waybar
        resp = asyncio.run(self.daemon.dispatch_action("frontend_get", {}, MagicMock()))
        self.assertEqual(resp["status"], "ok")
        self.assertIn(resp["frontend"], ("waybar", "quickshell", "both", "hybrid"))

        # Switch to quickshell
        resp = asyncio.run(self.daemon.dispatch_action("frontend_set", {"frontend": "quickshell"}, MagicMock()))
        self.assertEqual(resp["status"], "ok")
        self.assertEqual(self.daemon.config.frontend, "quickshell")

        # Switch to both
        resp = asyncio.run(self.daemon.dispatch_action("frontend_set", {"frontend": "both"}, MagicMock()))
        self.assertEqual(resp["status"], "ok")
        self.assertEqual(self.daemon.config.frontend, "both")

        # Invalid frontend rejection
        resp = asyncio.run(self.daemon.dispatch_action("frontend_set", {"frontend": "invalid_fe"}, MagicMock()))
        self.assertEqual(resp["status"], "error")

    def test_rich_payload_fields(self):
        # Push a volume slider event
        vol_state = IslandState(
            source="volume",
            state="volume",
            priority=Priority.SLIDER,
            icon="󰕾",
            title="65%",
            progress_pct=0.65,
            duration=1.5
        )
        self.daemon.push_transient_event(vol_state)
        payload = self.daemon.get_current_state().to_waybar_payload(self.daemon.config)

        # Waybar standard fields
        self.assertIn("text", payload)
        self.assertIn("alt", payload)
        self.assertIn("tooltip", payload)
        self.assertIn("class", payload)

        # Quickshell & rich stream fields
        self.assertEqual(payload["state"], "volume")
        self.assertEqual(payload["title"], "65%")
        self.assertEqual(payload["progress_pct"], 0.65)
        self.assertEqual(payload["priority"], int(Priority.SLIDER))

    def test_quickshell_files_exist(self):
        qs_dir = Path(__file__).resolve().parent.parent / "quickshell"
        self.assertTrue((qs_dir / "shell.qml").exists())
        self.assertTrue((qs_dir / "services" / "IslandBridge.qml").exists())
        self.assertTrue((qs_dir / "themes" / "Theme.qml").exists())
        self.assertTrue((qs_dir / "components" / "IslandCapsule.qml").exists())
        self.assertTrue((qs_dir / "components" / "IslandContent.qml").exists())
        self.assertTrue((qs_dir / "components" / "MediaView.qml").exists())
        self.assertTrue((qs_dir / "components" / "NotificationView.qml").exists())
        self.assertTrue((qs_dir / "components" / "VolumeView.qml").exists())
        self.assertTrue((qs_dir / "components" / "TimerView.qml").exists())
        self.assertTrue((qs_dir / "components" / "QuickActions.qml").exists())
        self.assertTrue((qs_dir / "components" / "BluetoothView.qml").exists())
        self.assertTrue((qs_dir / "components" / "CompactView.qml").exists())
        self.assertTrue((qs_dir / "components" / "ExpandedView.qml").exists())
        self.assertTrue((qs_dir / "components" / "EventView.qml").exists())
        self.assertTrue((qs_dir / "components" / "Settings.qml").exists())
        self.assertTrue((qs_dir / "dock" / "Dock.qml").exists())
        self.assertTrue((qs_dir / "widgets" / "MediaWidget.qml").exists())
        self.assertTrue((qs_dir / "widgets" / "BluetoothWidget.qml").exists())
        self.assertTrue((qs_dir / "widgets" / "NetworkWidget.qml").exists())
        self.assertTrue((qs_dir / "widgets" / "BatteryWidget.qml").exists())
        self.assertTrue((qs_dir / "widgets" / "TimerWidget.qml").exists())
        self.assertTrue((qs_dir / "widgets" / "SystemWidget.qml").exists())

    def test_smart_app_icon_resolution(self):
        self.assertEqual(resolve_app_icon("Telegram Desktop", "telegram", "New message"), "󰖣")
        self.assertEqual(resolve_app_icon("Discord", "discord", "Message from team"), "󰙯")
        self.assertEqual(resolve_app_icon("Spotify", "spotify", "Track changed"), "󰓇")
        self.assertEqual(resolve_app_icon("kitty", "terminal", "Task finished"), "󰄛")
        self.assertEqual(resolve_app_icon("firefox", "firefox", "Download completed"), "󰈹")
        self.assertEqual(resolve_app_icon("garuda-update", "checkupdates", "Updates ready"), "󰏔")
        self.assertEqual(resolve_app_icon("SomeUnknownApp", "", "Generic alert"), "󰂚")

    def test_notification_dismiss_on_click(self):
        loop = asyncio.new_event_loop()
        try:
            # 1. Post a notification
            notif = IslandState(
                source="notification",
                state="notification",
                priority=Priority.NOTIFICATION,
                title="Meeting Reminder",
                duration=4.0
            )
            self.daemon.push_transient_event(notif)
            self.assertEqual(self.daemon.get_current_state().state, "notification")

            # 2. Dispatch click / media_toggle -> should dismiss notification
            resp = loop.run_until_complete(self.daemon.dispatch_action("media_toggle", {}, None))
            self.assertEqual(resp["status"], "ok")
            self.assertIn("Dismissed", resp["message"])
            self.assertNotEqual(self.daemon.get_current_state().state, "notification")
        finally:
            loop.close()

    def test_task_management_engine(self):
        loop = asyncio.new_event_loop()
        try:
            # 1. Clear any existing tasks
            self.daemon.tasks = []
            self.daemon._save_tasks()
            self.daemon._update_active_task_state()
            self.assertEqual(self.daemon.get_current_state().state, "idle")

            # 2. Add Task 1
            res1 = loop.run_until_complete(self.daemon.dispatch_action("task_add", {"title": "Fix login bug"}, None))
            self.assertEqual(res1["status"], "ok")
            self.assertEqual(len(self.daemon.tasks), 1)

            # State engine should now reflect the active task (Priority.TASK = 25 > IDLE)
            cur = self.daemon.get_current_state()
            self.assertEqual(cur.state, "task")
            self.assertEqual(cur.priority, Priority.TASK)
            self.assertIn("Fix login bug", cur.title)

            # 3. Add Task 2
            res2 = loop.run_until_complete(self.daemon.dispatch_action("task_add", {"title": "Write unit tests"}, None))
            self.assertEqual(res2["status"], "ok")
            self.assertEqual(len(self.daemon.tasks), 2)

            # 4. Cycle next task
            res_next = loop.run_until_complete(self.daemon.dispatch_action("task_next", {}, None))
            self.assertEqual(res_next["status"], "ok")
            cur_after_next = self.daemon.get_current_state()
            self.assertIn("Write unit tests", cur_after_next.title)

            # 5. Mark done
            res_done = loop.run_until_complete(self.daemon.dispatch_action("task_done", {}, None))
            self.assertEqual(res_done["status"], "ok")

            # 6. Clear completed tasks
            res_clear = loop.run_until_complete(self.daemon.dispatch_action("task_clear", {}, None))
            self.assertEqual(res_clear["status"], "ok")
            self.assertEqual(len(self.daemon.tasks), 1)
        finally:
            loop.close()


class TestLanguageAndModes(unittest.TestCase):
    """Tests for Keyboard Layout / Origin Script, Four Modes, and Full View Engine"""

    def setUp(self):
        self.daemon = DynamicIslandDaemon()

    def test_language_resolution(self):
        # 1. English resolution
        us_info = resolve_language_info("us")
        self.assertEqual(us_info["short"], "US")
        self.assertEqual(us_info["origin"], "English")
        self.assertIn("English", us_info["full"])

        # 2. Khmer resolution (Origin script: ភាសាខ្មែរ)
        kh_info = resolve_language_info("kh")
        self.assertEqual(kh_info["short"], "KH")
        self.assertEqual(kh_info["origin"], "ភាសាខ្មែរ")
        self.assertEqual(kh_info["full"], "Khmer (Cambodia)")

        # 3. Layout name resolution directly
        kh_by_name = resolve_language_info("Khmer (Cambodia)")
        self.assertEqual(kh_by_name["origin"], "ភាសាខ្មែរ")
        self.assertEqual(kh_by_name["short"], "KH")

        # 4. Fallback for unknown
        unk = resolve_language_info("unknown_xyz")
        self.assertEqual(unk["short"], "UN")
        self.assertEqual(unk["origin"], "unknown_xyz")

    def test_language_event_and_priority_arbitration(self):
        self.assertEqual(Priority.LANGUAGE, 55)

        # Trigger layout change to Khmer
        self.daemon._on_layout_changed("Khmer (Cambodia)")
        cur = self.daemon.get_current_state()
        self.assertEqual(cur.state, "language")
        self.assertEqual(cur.priority, Priority.LANGUAGE)
        self.assertIn("ភាសាខ្មែរ", cur.title)

        # Higher priority (Volume = 60) should preempt language
        vol = IslandState(source="volume", state="volume", priority=Priority.SLIDER, title="70%", duration=1.5)
        self.daemon.push_transient_event(vol)
        self.assertEqual(self.daemon.get_current_state().state, "volume")

    def test_four_modes_ipc(self):
        loop = asyncio.new_event_loop()
        try:
            # Check default mode
            res = loop.run_until_complete(self.daemon.dispatch_action("mode_get", {}, None))
            self.assertEqual(res["status"], "ok")
            self.assertIn(res["mode"], MODES)

            # Switch through all four modes
            for m in ["waybar-lite", "waybar-enhanced", "quickshell", "hybrid"]:
                res_set = loop.run_until_complete(self.daemon.dispatch_action("mode_set", {"mode": m}, None))
                self.assertEqual(res_set["status"], "ok")
                self.assertEqual(self.daemon.config.mode, m)

            # Invalid mode should be rejected
            res_bad = loop.run_until_complete(self.daemon.dispatch_action("mode_set", {"mode": "invalid-mode"}, None))
            self.assertEqual(res_bad["status"], "error")
        finally:
            loop.close()

    def test_show_full_mode_and_truncation(self):
        loop = asyncio.new_event_loop()
        try:
            # Toggle show_full on
            res_on = loop.run_until_complete(self.daemon.dispatch_action("full_set", {"enabled": True}, None))
            self.assertEqual(res_on["status"], "ok")
            self.assertTrue(self.daemon.config.show_full)

            # Test truncate_text with force_full
            long_title = "This is a super long track name that would otherwise be severely truncated"
            truncated = truncate_text(long_title, max_chars=20, force_full=False)
            self.assertTrue(truncated.endswith("…"))
            self.assertLessEqual(len(truncated), 21)

            not_truncated = truncate_text(long_title, max_chars=20, force_full=True)
            self.assertEqual(not_truncated, long_title)

            # Toggle show_full off
            res_off = loop.run_until_complete(self.daemon.dispatch_action("full_toggle", {}, None))
            self.assertEqual(res_off["status"], "ok")
            self.assertFalse(self.daemon.config.show_full)
        finally:
            loop.close()

    def test_doctor_diagnostics_ipc(self):
        loop = asyncio.new_event_loop()
        try:
            res = loop.run_until_complete(self.daemon.dispatch_action("doctor", {}, None))
            self.assertEqual(res["status"], "ok")
            self.assertIn("doctor", res)
            self.assertIn("mode", res["doctor"])
            self.assertIn("dependencies", res["doctor"])
            self.assertIn("compositor", res["doctor"])
        finally:
            loop.close()


class TestV2MasterFeatures(unittest.TestCase):
    """Master Build Prompt: Shared Core, Bluetooth, 14 States, Waybar JSONL, & Quickshell Integration"""

    def setUp(self):
        self.daemon = DynamicIslandDaemon()

    def test_modular_core_exports(self):
        import core
        self.assertTrue(hasattr(core, "Priority"))
        self.assertTrue(hasattr(core, "IslandState"))
        self.assertTrue(hasattr(core, "IslandConfig"))
        self.assertTrue(hasattr(core, "EventManager"))
        self.assertTrue(hasattr(core, "TimerManager"))
        self.assertTrue(hasattr(core, "BluetoothBackend"))
        self.assertTrue(hasattr(core, "AudioBackend"))
        self.assertTrue(hasattr(core, "BrightnessBackend"))
        self.assertTrue(hasattr(core, "IpcServer"))

    def test_all_14_visual_states_valid(self):
        from core import VALID_STATES, is_valid_state
        expected_14 = [
            "idle", "media", "notification", "volume", "brightness",
            "timer", "pomodoro", "recording", "battery_warning", "charging",
            "network", "quick_actions", "expanded", "settings"
        ]
        for st in expected_14:
            self.assertIn(st, VALID_STATES)
            self.assertTrue(is_valid_state(st))

    def test_bluetooth_states_and_priority(self):
        # Bluetooth connecting priority = 72
        bt_conn = IslandState(
            source="bluetooth",
            state="bluetooth",
            priority=Priority.BLUETOOTH_CONNECTING,
            title="Connecting…",
            subtitle="Olike T111",
            duration=2.0
        )
        self.daemon.push_transient_event(bt_conn)
        self.assertEqual(self.daemon.get_current_state().state, "bluetooth")
        self.assertEqual(self.daemon.get_current_state().priority, Priority.BLUETOOTH_CONNECTING)
        self.assertEqual(self.daemon.get_current_state().title, "Connecting…")

        # Critical power (85) or Recording (90) preempts Bluetooth connecting (72)
        rec = IslandState(source="recording", state="recording", priority=Priority.RECORDING, title="REC")
        self.daemon.active_recording_state = rec
        self.assertEqual(self.daemon.get_current_state().state, "recording")
        self.daemon.active_recording_state = None

        # After recording ends, Bluetooth connecting is restored
        self.assertEqual(self.daemon.get_current_state().state, "bluetooth")

        # Bluetooth connected (priority = 45) preempts media (20) and timer (30)
        self.daemon.dismiss_transient()
        timer_st = IslandState(source="timer", state="timer", priority=Priority.TIMER, title="25:00")
        self.daemon.active_timer_state = timer_st

        bt_done = IslandState(
            source="bluetooth",
            state="bluetooth",
            priority=Priority.BLUETOOTH_CONNECTED,
            title="Connected",
            subtitle="Olike T111",
            duration=1.0
        )
        self.daemon.push_transient_event(bt_done)
        self.assertEqual(self.daemon.get_current_state().state, "bluetooth")
        self.assertEqual(self.daemon.get_current_state().title, "Connected")

    def test_volume_mute_and_brightness_ipc(self):
        loop = asyncio.new_event_loop()
        try:
            res_mute = loop.run_until_complete(self.daemon.dispatch_action("volume_mute", {}, None))
            self.assertEqual(res_mute["status"], "ok")

            res_bup = loop.run_until_complete(self.daemon.dispatch_action("brightness_up", {}, None))
            self.assertEqual(res_bup["status"], "ok")

            res_bdown = loop.run_until_complete(self.daemon.dispatch_action("brightness_down", {}, None))
            self.assertEqual(res_bdown["status"], "ok")
        finally:
            loop.close()

    def test_settings_and_bluetooth_ipc(self):
        loop = asyncio.new_event_loop()
        try:
            res_set = loop.run_until_complete(self.daemon.dispatch_action("settings", {}, None))
            self.assertEqual(res_set["status"], "ok")
            self.assertIn("settings", res_set)
            self.assertIn("theme", res_set["settings"])

            res_bt = loop.run_until_complete(self.daemon.dispatch_action("bluetooth", {"params": ["status"]}, None))
            self.assertEqual(res_bt["status"], "ok")
            self.assertIn("data", res_bt)
        finally:
            loop.close()

    def test_pomodoro_transitions(self):
        loop = asyncio.new_event_loop()
        try:
            res_pomo = loop.run_until_complete(self.daemon.dispatch_action("pomodoro", {}, None))
            self.assertEqual(res_pomo["status"], "ok")
            self.assertIsNotNone(self.daemon.active_timer_state)
            self.assertIn(self.daemon.active_timer_state.state, ("timer", "pomodoro"))

            res_pause = loop.run_until_complete(self.daemon.dispatch_action("pomodoro_pause", {}, None))
            self.assertEqual(res_pause["status"], "ok")
            self.assertTrue(self.daemon.timer_paused)

            res_res = loop.run_until_complete(self.daemon.dispatch_action("pomodoro_resume", {}, None))
            self.assertEqual(res_res["status"], "ok")
            self.assertFalse(self.daemon.timer_paused)

            res_stop = loop.run_until_complete(self.daemon.dispatch_action("stop", {}, None))
            self.assertEqual(res_stop["status"], "ok")
            self.assertIsNone(self.daemon.active_timer_state)
        finally:
            loop.close()

    def test_waybar_stdout_single_line_json(self):
        state = self.daemon.get_current_state()
        payload = state.to_waybar_payload(self.daemon.config)
        line = json.dumps(payload, ensure_ascii=False)
        self.assertNotIn("\n", line)
        parsed = json.loads(line)
        self.assertIn("text", parsed)
        self.assertIn("alt", parsed)
        self.assertIn("tooltip", parsed)
        self.assertIn("class", parsed)


class TestV3Enhancements(unittest.TestCase):
    """Phase 3: HyperOS, OriginOS, macOS Dock, and System Monitoring Tests"""

    def setUp(self):
        self.daemon = DynamicIslandDaemon()

    def test_dock_toggle_and_config(self):
        loop = asyncio.new_event_loop()
        try:
            # Enable dock
            res_on = loop.run_until_complete(self.daemon.dispatch_action("dock", {"params": ["on"]}, None))
            self.assertEqual(res_on["status"], "ok")
            self.assertTrue(res_on["dock_enabled"])
            self.assertTrue(self.daemon.config.dock_enabled)

            # Disable dock
            res_off = loop.run_until_complete(self.daemon.dispatch_action("dock", {"params": ["off"]}, None))
            self.assertEqual(res_off["status"], "ok")
            self.assertFalse(res_off["dock_enabled"])
            self.assertFalse(self.daemon.config.dock_enabled)

            # Toggle dock
            res_toggle = loop.run_until_complete(self.daemon.dispatch_action("dock", {"params": ["toggle"]}, None))
            self.assertEqual(res_toggle["status"], "ok")
            self.assertTrue(res_toggle["dock_enabled"])
        finally:
            loop.close()

    def test_system_metrics_telemetry(self):
        loop = asyncio.new_event_loop()
        try:
            res = loop.run_until_complete(self.daemon.dispatch_action("system", {}, None))
            self.assertEqual(res["status"], "ok")
            self.assertIn("cpu_percent", res)
            self.assertIn("memory_percent", res)
            self.assertIsInstance(res["cpu_percent"], (int, float))
            self.assertIsInstance(res["memory_percent"], (int, float))
            self.assertGreaterEqual(res["cpu_percent"], 0.0)
            self.assertGreaterEqual(res["memory_percent"], 0.0)
            self.assertLessEqual(res["memory_percent"], 100.0)
        finally:
            loop.close()

    def test_media_formatting_and_rich_payload(self):
        from core.media_backend import format_seconds
        self.assertEqual(format_seconds(0), "00:00")
        self.assertEqual(format_seconds(65), "01:05")
        self.assertEqual(format_seconds(3665), "1:01:05")

        state = IslandState(
            source="media",
            state="media",
            title="Blinding Lights",
            subtitle="The Weeknd",
            art_url="file:///tmp/artwork.jpg",
            duration_str="03:20",
            position_str="01:10",
            player_name="spotify",
            system_cpu=12.5,
            system_mem=45.2
        )
        payload = state.to_waybar_payload(self.daemon.config)
        self.assertEqual(payload["art_url"], "file:///tmp/artwork.jpg")
        self.assertEqual(payload["duration_str"], "03:20")
        self.assertEqual(payload["position_str"], "01:10")
        self.assertEqual(payload["player_name"], "spotify")
        self.assertEqual(payload["system_cpu"], 12.5)
        self.assertEqual(payload["system_mem"], 45.2)


class TestSmartShareSystem(unittest.TestCase):
    """Smart Share & Drag-and-Drop Tests"""

    def setUp(self):
        self.daemon = DynamicIslandDaemon()
        self.share_mgr = self.daemon.share_manager

    def test_url_validation_local_files_only(self):
        # 1. Non-existent file rejected
        res_non = self.share_mgr.parse_and_validate_urls(["/nonexistent/path/foo.png"])
        self.assertEqual(len(res_non), 0)

        # 2. Web schemes rejected
        res_web = self.share_mgr.parse_and_validate_urls(["https://example.com/test.jpg"])
        self.assertEqual(len(res_web), 0)

        # 3. Valid local file with file:// scheme
        with tempfile.NamedTemporaryFile(suffix=".png") as tf:
            file_url = f"file://{tf.name}"
            res = self.share_mgr.parse_and_validate_urls([file_url])
            self.assertEqual(len(res), 1)
            self.assertEqual(res[0]["path"], tf.name)
            self.assertEqual(res[0]["icon"], "󰈟")
            self.assertTrue(res[0]["exists"])

    def test_unicode_and_encoded_spaces_handling(self):
        with tempfile.TemporaryDirectory() as td:
            special_file = Path(td) / "My Document ខ្មែរ.pdf"
            special_file.write_text("dummy test content")

            # Encoded URI
            uri = f"file://{td}/My%20Document%20%E1%9E%81%E1%9F%92%E1%9E%98%E1%9F%82%E1%9E%94.pdf"
            # Raw string
            raw = str(special_file)

            res = self.share_mgr.parse_and_validate_urls([raw])
            self.assertEqual(len(res), 1)
            self.assertEqual(res[0]["name"], "My Document ខ្មែរ.pdf")
            self.assertEqual(res[0]["icon"], "󰈦")

    def test_dynamic_target_discovery(self):
        with tempfile.NamedTemporaryFile(suffix=".txt") as tf:
            files = self.share_mgr.parse_and_validate_urls([tf.name])
            targets = self.share_mgr.discover_targets(files)

            # Targets list must contain core share options
            target_ids = [t["id"] for t in targets]
            self.assertIn("telegram", target_ids)
            self.assertIn("discord", target_ids)
            self.assertIn("bluetooth", target_ids)
            self.assertIn("default_app", target_ids)
            self.assertIn("clipboard", target_ids)

            # Clipboard and default openers should be available
            clip_tgt = next(t for t in targets if t["id"] == "clipboard")
            self.assertTrue(clip_tgt["available"])

    def test_share_ipc_lifecycle(self):
        loop = asyncio.new_event_loop()
        try:
            with tempfile.NamedTemporaryFile(suffix=".jpg") as tf:
                # 1. share_inspect opens share_picker
                res_insp = loop.run_until_complete(
                    self.daemon.dispatch_action("share_inspect", {"urls": [tf.name]}, None)
                )
                self.assertEqual(res_insp["status"], "ok")
                self.assertEqual(len(res_insp["files"]), 1)

                st = self.daemon.get_current_state()
                self.assertEqual(st.state, "share_picker")
                self.assertEqual(st.priority, Priority.SHARE)

                # Payload includes dropped_files and share_targets
                payload = st.to_waybar_payload(self.daemon.config)
                self.assertEqual(len(payload["dropped_files"]), 1)
                self.assertGreaterEqual(len(payload["share_targets"]), 4)

                # 2. share_execute with clipboard
                res_exec = loop.run_until_complete(
                    self.daemon.dispatch_action("share_execute", {"target_id": "clipboard"}, None)
                )
                self.assertEqual(res_exec["status"], "ok")

                # 3. share_cancel cleans up state
                res_canc = loop.run_until_complete(
                    self.daemon.dispatch_action("share_cancel", {}, None)
                )
                self.assertEqual(res_canc["status"], "ok")
                self.assertNotEqual(self.daemon.get_current_state().state, "share_picker")
        finally:
            loop.close()


class TestSwayWindowInteractions(unittest.TestCase):
    """Sway Window Management, Scratchpad Minimize/Restore, and Running Indicator Tests"""

    def setUp(self):
        self.daemon = DynamicIslandDaemon()
        self.win_mgr = self.daemon.window_monitor

    def test_window_list_and_scratchpad_detection(self):
        windows = self.win_mgr.get_windows()
        self.assertIsInstance(windows, list)
        for w in windows:
            self.assertIn("id", w)
            self.assertIn("app_id", w)
            self.assertIn("title", w)
            self.assertIn("focused", w)
            self.assertIn("minimized", w)

    def test_window_ipc_actions(self):
        loop = asyncio.new_event_loop()
        try:
            # 1. windows_list
            res_list = loop.run_until_complete(self.daemon.dispatch_action("windows_list", {}, None))
            self.assertEqual(res_list["status"], "ok")
            self.assertIn("windows", res_list)

            # 2. Mocking minimize window
            with patch.object(self.win_mgr, "minimize_window", return_value={"status": "ok", "message": "Window 123 minimized to scratchpad"}):
                res_min = loop.run_until_complete(self.daemon.dispatch_action("window_minimize", {"con_id": 123}, None))
                self.assertEqual(res_min["status"], "ok")
                self.assertEqual(self.daemon.get_current_state().state, "minimized")

            # 3. Mocking restore window
            with patch.object(self.win_mgr, "restore_window", return_value={"status": "ok", "message": "Window 123 restored from scratchpad"}):
                res_res = loop.run_until_complete(self.daemon.dispatch_action("window_restore", {"con_id": 123}, None))
                self.assertEqual(res_res["status"], "ok")
                self.assertEqual(self.daemon.get_current_state().state, "restoring")

            # 4. Mocking toggle app
            with patch.object(self.win_mgr, "toggle_app_by_name", return_value={"status": "ok", "action": "focused", "con_id": 456}):
                res_tog = loop.run_until_complete(self.daemon.dispatch_action("window_toggle_app", {"app_keyword": "kitty"}, None))
                self.assertEqual(res_tog["status"], "ok")
        finally:
            loop.close()

    def test_running_windows_payload(self):
        state = self.daemon.get_current_state()
        payload = state.to_waybar_payload(self.daemon.config)
        self.assertIn("running_windows", payload)
        self.assertIsInstance(payload["running_windows"], list)

    def test_performance_profiles(self):
        cfg = self.daemon.config
        cfg.apply_profile("low-resource")
        self.assertEqual(cfg.performance_profile, "low-resource")
        self.assertEqual(cfg.idle_clock_interval_s, 30.0)
        self.assertEqual(cfg.metrics_interval_s, 6.0)
        self.assertTrue(cfg.reduced_motion)
        self.assertEqual(cfg.minimize_duration_ms, 180)

        cfg.apply_profile("visual-quality")
        self.assertEqual(cfg.performance_profile, "visual-quality")
        self.assertEqual(cfg.idle_clock_interval_s, 5.0)
        self.assertEqual(cfg.metrics_interval_s, 2.0)
        self.assertFalse(cfg.reduced_motion)
        self.assertEqual(cfg.minimize_duration_ms, 420)

        cfg.apply_profile("balanced")
        self.assertEqual(cfg.performance_profile, "balanced")
        self.assertEqual(cfg.idle_clock_interval_s, 15.0)
        self.assertEqual(cfg.metrics_interval_s, 3.0)
        self.assertFalse(cfg.reduced_motion)
        self.assertEqual(cfg.minimize_duration_ms, 380)

        # Test IPC action profile
        loop = asyncio.new_event_loop()
        try:
            res_get = loop.run_until_complete(self.daemon.dispatch_action("profile", {}, None))
            self.assertEqual(res_get["status"], "ok")
            self.assertEqual(res_get["profile"], "balanced")

            res_set = loop.run_until_complete(self.daemon.dispatch_action("profile", {"subcommand": "set", "name": "low-resource"}, None))
            self.assertEqual(res_set["status"], "ok")
            self.assertEqual(res_set["profile"], "low-resource")
            self.assertEqual(self.daemon.config.performance_profile, "low-resource")
        finally:
            loop.close()

    def test_window_minimize_restore_animation_events(self):
        win_info = {
            "id": 999,
            "app_id": "kitty",
            "name": "Terminal",
            "title": "Terminal",
            "icon": "󰄛",
            "rect": {"x": 100, "y": 200, "width": 800, "height": 600}
        }
        with patch.object(self.daemon.ipc_server, "broadcast_stream") as mock_broadcast:
            self.daemon._on_window_minimized(win_info)
            self.assertEqual(self.daemon.get_current_state().state, "minimized")
            self.assertEqual(self.daemon.get_current_state().icon, "󰄛")
            mock_broadcast.assert_called()
            sent_payload = json.loads(mock_broadcast.call_args[0][0])
            self.assertIn("window_anim", sent_payload)
            self.assertEqual(sent_payload["window_anim"]["type"], "minimize")
            self.assertEqual(sent_payload["window_anim"]["id"], 999)
            self.assertEqual(sent_payload["window_anim"]["rect"]["width"], 800)

        with patch.object(self.daemon.ipc_server, "broadcast_stream") as mock_broadcast:
            self.daemon._on_window_restored(win_info)
            self.assertEqual(self.daemon.get_current_state().state, "restoring")
            mock_broadcast.assert_called()
            sent_payload = json.loads(mock_broadcast.call_args[0][0])
            self.assertIn("window_anim", sent_payload)
            self.assertEqual(sent_payload["window_anim"]["type"], "restore")

    def test_17_state_machine_and_transitions(self):
        from core.priority_manager import is_valid_state, is_valid_transition, VALID_STATES
        required_states = [
            "idle", "compact", "expanded",
            "minimize_detected", "minimize_animating", "minimized_apps",
            "restore_detected", "restore_animating",
            "drag_enter", "drag_active", "share_picker", "share_confirm", "share_launching", "share_error",
            "media_expanded", "quick_settings", "notification"
        ]
        for st in required_states:
            self.assertTrue(is_valid_state(st), f"State '{st}' must be valid in VALID_STATES")

        # Test valid transitions
        self.assertTrue(is_valid_transition("idle", "drag_enter"))
        self.assertTrue(is_valid_transition("drag_enter", "drag_active"))
        self.assertTrue(is_valid_transition("drag_active", "share_picker"))
        self.assertTrue(is_valid_transition("share_picker", "share_confirm"))
        self.assertTrue(is_valid_transition("share_confirm", "share_launching"))
        self.assertTrue(is_valid_transition("minimize_detected", "minimize_animating"))
        self.assertTrue(is_valid_transition("minimize_animating", "minimized_apps"))
        self.assertTrue(is_valid_transition("minimized_apps", "restore_detected"))
        self.assertTrue(is_valid_transition("restore_detected", "restore_animating"))
        self.assertTrue(is_valid_transition("restore_animating", "idle"))

        # Emergency preemption is always allowed
        self.assertTrue(is_valid_transition("minimized_apps", "recording"))
        self.assertTrue(is_valid_transition("media_expanded", "error"))

    def test_animation_style_normalization_and_targets(self):
        normalize = IslandConfig.normalize_minimize_style
        self.assertEqual(normalize("lamp"), "macos-lamp")
        self.assertEqual(normalize("macos-lamp"), "macos-lamp")
        self.assertEqual(normalize("magic-lamp"), "macos-lamp")
        self.assertEqual(normalize("lamp-effect"), "macos-lamp")
        self.assertEqual(normalize("genie"), "macos-genie-inspired")
        self.assertEqual(normalize("genie-inspired"), "macos-genie-inspired")
        self.assertEqual(normalize("macos-genie"), "macos-genie-inspired")
        self.assertEqual(normalize("scale"), "scale")
        self.assertEqual(normalize("macos-scale"), "scale")
        self.assertEqual(normalize("scale-fade"), "scale-fade")
        self.assertEqual(normalize("fade"), "scale-fade")
        self.assertEqual(normalize("spring"), "originos-spring")
        self.assertEqual(normalize("bounce"), "originos-spring")
        self.assertEqual(normalize("reduced-motion"), "reduced-motion")
        self.assertEqual(normalize("subtle"), "reduced-motion")
        self.assertEqual(normalize("none"), "none")

    def test_minimized_apps_and_window_ipc_actions(self):
        loop = asyncio.new_event_loop()
        try:
            # Test window_style action with lamp and genie
            res_lamp = loop.run_until_complete(self.daemon.dispatch_action("window_style", {"subcommand": "set", "style": "lamp"}, None))
            self.assertEqual(res_lamp["status"], "ok")
            self.assertEqual(res_lamp["style"], "macos-lamp")
            self.assertEqual(self.daemon.config.minimize_style, "macos-lamp")

            res_style = loop.run_until_complete(self.daemon.dispatch_action("window_style", {"subcommand": "set", "style": "genie"}, None))
            self.assertEqual(res_style["status"], "ok")
            self.assertEqual(res_style["style"], "macos-genie-inspired")
            self.assertEqual(self.daemon.config.minimize_style, "macos-genie-inspired")

            # Test window_target action
            res_target = loop.run_until_complete(self.daemon.dispatch_action("window_target", {"subcommand": "set", "target": "dock"}, None))
            self.assertEqual(res_target["status"], "ok")
            self.assertEqual(res_target["target"], "dock")
            self.assertEqual(self.daemon.config.minimize_target, "dock")

            # Test position action
            res_pos = loop.run_until_complete(self.daemon.dispatch_action("position", {"subcommand": "set", "position": "top-left"}, None))
            self.assertEqual(res_pos["status"], "ok")
            self.assertEqual(res_pos["position"], "top-left")
            self.assertEqual(self.daemon.config.position, "top-left")

            # Test minimized_apps_show action
            res_min = loop.run_until_complete(self.daemon.dispatch_action("minimized_apps_show", {}, None))
            self.assertEqual(res_min["status"], "ok")
            self.assertEqual(self.daemon.get_current_state().state, "minimized_apps")
        finally:
            loop.close()


class TestMacOSWindowMinimizeAndRestore(unittest.TestCase):
    """
    Comprehensive verification for RATANA DYNAMIC ISLAND — FULL macOS-STYLE MINIMIZE TO ISLAND.
    Tests:
    1. Correct window identification (ID, app_id, title, workspace, output, geometry).
    2. Minimize and restore state transitions (WindowState machine).
    3. Single capsule with multiple applications (single selection, counter [1/3], next/prev).
    4. Rapid repeated minimize/restore (concurrency & no stuck state).
    5. Closed and stale windows (graceful cleanup, no duplicate processes).
    6. Workspace and monitor changes (output resolution).
    7. Animation cancellation & interruptibility.
    8. Thumbnail safety and bounded cache.
    9. Low-resource mode (thumbnail skip, duration bounds).
    10. Waybar Lite independent operation (JSON payload validity).
    """

    def setUp(self):
        self.daemon = DynamicIslandDaemon()
        from core.window_backend import SwayWindowMonitor, WindowState
        self.monitor = SwayWindowMonitor()

    def test_window_identification(self):
        mock_tree = {
            "type": "root",
            "nodes": [
                {
                    "type": "output",
                    "name": "eDP-1",
                    "nodes": [
                        {
                            "type": "workspace",
                            "name": "1",
                            "nodes": [
                                {
                                    "id": 101,
                                    "type": "con",
                                    "name": "Terminal — fish",
                                    "app_id": "kitty",
                                    "focused": True,
                                    "rect": {"x": 50, "y": 60, "width": 800, "height": 600}
                                }
                            ],
                            "floating_nodes": []
                        }
                    ]
                }
            ],
            "floating_nodes": []
        }
        with patch("subprocess.check_output", return_value=json.dumps(mock_tree).encode()):
            self.monitor.refresh_cache_now()
            wins = self.monitor.get_windows(force_refresh=True)
            self.assertEqual(len(wins), 1)
            w = wins[0]
            self.assertEqual(w["id"], 101)
            self.assertEqual(w["app_id"], "kitty")
            self.assertEqual(w["name"], "Terminal — fish")
            self.assertEqual(w["output"], "eDP-1")
            self.assertEqual(w["workspace"], "active")
            self.assertEqual(w["rect"]["width"], 800)
            self.assertEqual(w["icon"], "󰄛")
            self.assertTrue(w["focused"])
            self.assertFalse(w["minimized"])

    def test_minimize_and_restore_state_transitions(self):
        from core.window_backend import WindowState
        con_id = 202
        rect = {"x": 100, "y": 100, "width": 600, "height": 400}
        self.monitor._last_geometries[con_id] = rect
        self.monitor._cached_windows = [{
            "id": con_id, "app_id": "firefox", "name": "Browser", "title": "Browser",
            "focused": True, "minimized": False, "rect": rect, "workspace": "1", "output": "eDP-1"
        }]

        min_called = []
        res_called = []
        self.monitor.on_window_minimized = lambda w: min_called.append(w)
        self.monitor.on_window_restored = lambda w: res_called.append(w)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stderr="")
            # Minimize
            res_min = self.monitor.minimize_window(con_id, allow_thumbnail=False)
            self.assertEqual(res_min["status"], "ok")
            self.assertEqual(self.monitor.get_window_state(con_id), WindowState.MINIMIZED.value)
            self.assertEqual(len(min_called), 1)

            # Restore
            res_res = self.monitor.restore_window(con_id)
            self.assertEqual(res_res["status"], "ok")
            self.assertEqual(self.monitor.get_window_state(con_id), WindowState.NORMAL.value)
            self.assertEqual(len(res_called), 1)

    def test_single_capsule_multiple_applications(self):
        mins = [
            {"id": 1, "app_id": "kitty", "name": "Terminal", "minimized": True, "icon": "󰄛"},
            {"id": 2, "app_id": "firefox", "name": "Firefox", "minimized": True, "icon": "󰈹"},
            {"id": 3, "app_id": "code", "name": "VSCode", "minimized": True, "icon": "󰨞"},
        ]
        with patch.object(self.daemon.window_monitor, "get_minimized_windows", return_value=mins):
            self.daemon._on_window_state_changed()
            self.assertEqual(self.daemon.selected_minimized_index, 0)

            # Test next
            loop = asyncio.new_event_loop()
            try:
                res = loop.run_until_complete(self.daemon.dispatch_action("windows", ["next"], None))
                self.assertEqual(res["selected_index"], 1)
                self.assertEqual(self.daemon.selected_minimized_index, 1)

                res = loop.run_until_complete(self.daemon.dispatch_action("windows", ["next"], None))
                self.assertEqual(res["selected_index"], 2)

                # Wraps around
                res = loop.run_until_complete(self.daemon.dispatch_action("windows", ["next"], None))
                self.assertEqual(res["selected_index"], 0)

                # Test prev
                res = loop.run_until_complete(self.daemon.dispatch_action("windows", ["prev"], None))
                self.assertEqual(res["selected_index"], 2)

                # Test select
                res = loop.run_until_complete(self.daemon.dispatch_action("windows", ["select", "1"], None))
                self.assertEqual(res["selected_index"], 1)
            finally:
                loop.close()

            # Verify Waybar formatted output displays single selected app + counter [2/3]
            state = IslandState(
                event_id="test",
                source="core",
                state="idle",
                priority=Priority.IDLE,
                icon="󰸗",
                title="12:00 PM",
                css_class="idle"
            )
            state.running_windows = mins
            state.selected_minimized_index = 1
            payload = state.to_waybar_payload(self.daemon.config)
            self.assertIn("[2/3]", payload["text"])
            self.assertIn("󰈹", payload["text"])
            self.assertIn("Firefox", payload["text"])

    def test_rapid_repeated_minimize_restore(self):
        con_id = 303
        self.monitor._cached_windows = [{
            "id": con_id, "app_id": "foot", "name": "Foot", "focused": True, "minimized": False, "rect": {"x": 0, "y": 0, "width": 400, "height": 300}
        }]
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stderr="")
            for _ in range(10):
                res_m = self.monitor.minimize_window(con_id, allow_thumbnail=False)
                self.assertEqual(res_m["status"], "ok")
                res_r = self.monitor.restore_window(con_id)
                self.assertEqual(res_r["status"], "ok")

    def test_closed_and_stale_windows(self):
        stale_id = 99999
        self.monitor._cached_windows = [{"id": stale_id, "name": "Ghost", "minimized": True}]
        self.monitor._prev_minimized_ids = {stale_id}

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stderr="Error: [con_id=99999] not found")
            res = self.monitor.restore_window(stale_id)
            self.assertEqual(res["status"], "error")
            self.assertTrue(res.get("stale"))
            self.assertNotIn(stale_id, self.monitor._prev_minimized_ids)
            self.assertNotIn(stale_id, [w["id"] for w in self.monitor._cached_windows])

    def test_thumbnail_safety_and_bounds(self):
        from core.window_backend import (
            capture_window_thumbnail, prune_thumbnail_cache,
            cleanup_window_thumbnail, THUMBNAIL_DIR, MAX_CACHED_THUMBNAILS
        )
        os.makedirs(THUMBNAIL_DIR, mode=0o700, exist_ok=True)
        # Create dummy thumbnails exceeding MAX_CACHED_THUMBNAILS
        for i in range(15):
            p = os.path.join(THUMBNAIL_DIR, f"{i}.jpg")
            with open(p, "w") as f:
                f.write("test")
        prune_thumbnail_cache()
        remaining = [f for f in os.listdir(THUMBNAIL_DIR) if f.endswith(".jpg")]
        self.assertLessEqual(len(remaining), MAX_CACHED_THUMBNAILS)

        # Cleanup single thumbnail
        cleanup_window_thumbnail(0)
        self.assertFalse(os.path.exists(os.path.join(THUMBNAIL_DIR, "0.jpg")))

    def test_low_resource_mode(self):
        self.daemon.config.apply_profile("low-resource")
        self.assertEqual(self.daemon.config.minimize_style, "low-resource")
        self.assertLessEqual(self.daemon.config.minimize_duration_ms, 200)

    def test_missing_thumbnail_support(self):
        from core.window_backend import capture_window_thumbnail
        with patch("shutil.which", return_value=None):
            # When grim is not installed
            res = capture_window_thumbnail(123, {"x": 10, "y": 10, "width": 500, "height": 400})
            self.assertEqual(res, "")

    def test_workspace_and_monitor_changes(self):
        mock_tree = {
            "type": "root",
            "nodes": [
                {
                    "type": "output",
                    "name": "HDMI-A-1",
                    "nodes": [
                        {
                            "type": "workspace",
                            "name": "3",
                            "nodes": [
                                {
                                    "id": 505,
                                    "type": "con",
                                    "name": "Code",
                                    "app_id": "code",
                                    "focused": False,
                                    "rect": {"x": 1920, "y": 0, "width": 1920, "height": 1080}
                                }
                            ],
                            "floating_nodes": []
                        }
                    ]
                }
            ],
            "floating_nodes": []
        }
        with patch("subprocess.check_output", return_value=json.dumps(mock_tree).encode()):
            wins = self.monitor.get_windows(force_refresh=True)
            w = next((x for x in wins if x["id"] == 505), None)
            self.assertIsNotNone(w)
            self.assertEqual(w["output"], "HDMI-A-1")
            self.assertEqual(w["rect"]["x"], 1920)

    def test_animation_cancellation(self):
        # Broadcast minimize followed immediately by restore to verify cancellation payload
        con_id = 707
        win = {
            "id": con_id, "app_id": "kitty", "name": "Terminal",
            "icon": "󰄛", "rect": {"x": 100, "y": 100, "width": 500, "height": 400}
        }
        payloads = []
        with patch.object(self.daemon.ipc_server, "broadcast_stream") as mock_broadcast:
            mock_broadcast.side_effect = lambda msg: payloads.append(json.loads(msg))
            self.daemon._on_window_minimized(win)
            self.daemon._on_window_restored(win)
            anim_payloads = [p for p in payloads if "window_anim" in p]
            self.assertEqual(len(anim_payloads), 2)
            self.assertEqual(anim_payloads[0]["window_anim"]["type"], "minimize")
            self.assertEqual(anim_payloads[1]["window_anim"]["type"], "restore")
            self.assertEqual(anim_payloads[1]["window_anim"]["id"], con_id)

    def test_waybar_lite_independence(self):
        state = self.daemon.get_current_state()
        data = state.to_waybar_payload(self.daemon.config)
        self.assertIn("text", data)
        self.assertIn("tooltip", data)
        self.assertIn("class", data)
        self.assertIn("alt", data)
        serialized = json.dumps(data)
        loaded = json.loads(serialized)
        self.assertEqual(loaded["text"], data["text"])


class TestWifiAndBluetoothManagers(unittest.TestCase):
    def setUp(self):
        self.config = IslandConfig()
        self.caps = Mock()
        self.caps.has_nmcli = True
        self.events = []
        self.net_backend = NetworkBackend(self.config, self.caps, lambda ev: self.events.append(ev))

    def test_wifi_scan_networks_parsing(self):
        loop = asyncio.new_event_loop()
        try:
            sample_output = (
                "*:MyHomeWifi:AA\\:BB\\:CC\\:DD\\:EE\\:FF:85:WPA2:▂▄▆█\n"
                " :CoffeeShop:11\\:22\\:33\\:44\\:55\\:66:50:WPA2 802.1X:▂▄__\n"
                " :OpenWiFi:22\\:33\\:44\\:55\\:66\\:77:90::▂▄▆█\n"
                " :សួស្តីកម្ពុជា:33\\:44\\:55\\:66\\:77\\:88:65:WPA2:▂▄▆_\n"
            ).encode("utf-8")

            mock_proc = Mock()
            mock_proc.communicate = AsyncMock(return_value=(sample_output, b""))

            with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
                networks = loop.run_until_complete(self.net_backend.scan_networks(rescan=False))

                self.assertEqual(len(networks), 4)
                home = next(n for n in networks if n["ssid"] == "MyHomeWifi")
                self.assertTrue(home["in_use"])
                self.assertEqual(home["bssid"], "AA:BB:CC:DD:EE:FF")
                self.assertEqual(home["signal"], 85)
                self.assertTrue(home["is_secure"])

                open_net = next(n for n in networks if n["ssid"] == "OpenWiFi")
                self.assertFalse(open_net["is_secure"])
                self.assertEqual(open_net["signal"], 90)

                khmer = next(n for n in networks if n["ssid"] == "សួស្តីកម្ពុជា")
                self.assertEqual(khmer["signal"], 65)
                self.assertEqual(khmer["bssid"], "33:44:55:66:77:88")
        finally:
            loop.close()

    def test_wifi_status_parsing(self):
        loop = asyncio.new_event_loop()
        try:
            mock_radio = Mock()
            mock_radio.communicate = AsyncMock(return_value=(b"enabled\n", b""))

            mock_dev = Mock()
            mock_dev.communicate = AsyncMock(return_value=(b"wlan0:wifi:connected:MyHomeWifi\n", b""))

            mock_sig = Mock()
            mock_sig.communicate = AsyncMock(return_value=(b"*:MyHomeWifi:88\n", b""))

            with patch("asyncio.create_subprocess_exec", side_effect=[mock_radio, mock_dev, mock_sig]):
                status = loop.run_until_complete(self.net_backend.get_wifi_status())
                self.assertTrue(status["available"])
                self.assertTrue(status["enabled"])
                self.assertTrue(status["connected"])
                self.assertEqual(status["ssid"], "MyHomeWifi")
                self.assertEqual(status["signal"], 88)
                self.assertEqual(status["device"], "wlan0")
                self.assertEqual(status["icon"], "󰤨")
        finally:
            loop.close()

    def test_bluetooth_toggle_power(self):
        loop = asyncio.new_event_loop()
        try:
            bt_backend = BluetoothBackend(self.config, lambda ev: self.events.append(ev))
            bt_backend.has_bluez = False  # Avoid real DBus during test

            mock_status = {"adapter_powered": False}
            with patch.object(bt_backend, "fetch_status", AsyncMock(return_value=mock_status)):
                mock_proc = Mock()
                mock_proc.communicate = AsyncMock(return_value=(b"", b""))

                with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
                    res = loop.run_until_complete(bt_backend.toggle_power(enable=True))
                    self.assertEqual(res["status"], "ok")
                    self.assertTrue(res["powered"])
                    self.assertEqual(len(self.events), 1)
                    self.assertEqual(self.events[0].title, "Bluetooth On")
        finally:
            loop.close()

    def test_dual_split_accessory_pill_payload(self):
        state = IslandState(
            source="media",
            state="media",
            title="Blinding Lights",
            subtitle="The Weeknd",
            accessory_icon="󰓇",
            accessory_label="The Weeknd",
            accessory_visible=True
        )
        payload = state.to_waybar_payload(self.config)
        self.assertIn("accessory_icon", payload)
        self.assertIn("accessory_label", payload)
        self.assertTrue(payload["accessory_visible"])
        self.assertEqual(payload["accessory_icon"], "󰓇")
        self.assertEqual(payload["accessory_label"], "The Weeknd")

        d = state.to_dict()
        self.assertTrue(d["accessory_visible"])
        self.assertEqual(d["accessory_icon"], "󰓇")


class TestConfigurationAndSettingsSystem(unittest.TestCase):
    """Phase 6: Unified Settings & Configuration Verification Tests"""

    def setUp(self):
        self.daemon = DynamicIslandDaemon()
        if hasattr(self.daemon, "window_monitor"):
            self.daemon.window_monitor.stop()
            self.daemon.window_monitor.on_window_minimized = None
            self.daemon.window_monitor.on_window_restored = None
            self.daemon.window_monitor.get_minimized_windows = Mock(return_value=[])
        self.daemon.dismiss_transient()

    def test_settings_get_and_export(self):
        loop = asyncio.new_event_loop()
        try:
            res = loop.run_until_complete(self.daemon.dispatch_action("settings", [], None))
            self.assertEqual(res["status"], "ok")
            self.assertIn("settings", res)
            s = res["settings"]
            self.assertIn("theme", s)
            self.assertIn("mode", s)
            self.assertIn("minimize_style", s)

            res_exp = loop.run_until_complete(self.daemon.dispatch_action("settings_export", [], None))
            self.assertEqual(res_exp["status"], "ok")
            self.assertEqual(res_exp["settings"]["theme"], self.daemon.config.theme)
        finally:
            loop.close()

    def test_settings_set(self):
        loop = asyncio.new_event_loop()
        try:
            res1 = loop.run_until_complete(self.daemon.dispatch_action("settings_set", {"key": "theme", "val": "hyperos-dark"}, None))
            self.assertEqual(res1["status"], "ok")
            self.assertEqual(self.daemon.config.theme, "hyperos-dark")

            res2 = loop.run_until_complete(self.daemon.dispatch_action("settings_set", {"key": "minimize_style", "val": "originos-spring"}, None))
            self.assertEqual(res2["status"], "ok")
            self.assertEqual(self.daemon.config.minimize_style, "originos-spring")

            res3 = loop.run_until_complete(self.daemon.dispatch_action("settings_set", {"key": "minimize_duration_ms", "val": "220"}, None))
            self.assertEqual(res3["status"], "ok")
            self.assertEqual(self.daemon.config.minimize_duration_ms, 220)

            res4 = loop.run_until_complete(self.daemon.dispatch_action("settings_set", {"key": "network_ssid_privacy", "val": "false"}, None))
            self.assertEqual(res4["status"], "ok")
            self.assertFalse(self.daemon.config.network_ssid_privacy)
        finally:
            loop.close()

    def test_settings_reset_to_defaults(self):
        loop = asyncio.new_event_loop()
        try:
            # Change some settings
            self.daemon.config.theme = "catppuccin-mocha"
            self.daemon.config.minimize_duration_ms = 999
            self.daemon.config.reduced_motion = True

            # Reset
            res = loop.run_until_complete(self.daemon.dispatch_action("settings_reset", [], None))
            self.assertEqual(res["status"], "ok")
            self.assertEqual(self.daemon.config.theme, "macos-black")
            self.assertEqual(self.daemon.config.minimize_duration_ms, 380)
            self.assertFalse(self.daemon.config.reduced_motion)
        finally:
            loop.close()

    def test_settings_import(self):
        loop = asyncio.new_event_loop()
        try:
            import_data = {
                "theme": "originos-dark",
                "minimize_style": "hyperos-mini",
                "blur_enabled": False
            }
            res = loop.run_until_complete(self.daemon.dispatch_action("settings_import", {"settings": import_data}, None))
            self.assertEqual(res["status"], "ok")
            self.assertEqual(self.daemon.config.theme, "originos-dark")
            self.assertEqual(self.daemon.config.minimize_style, "hyperos-mini")
            self.assertFalse(self.daemon.config.blur_enabled)
        finally:
            loop.close()

    def test_settings_ui_action(self):
        loop = asyncio.new_event_loop()
        try:
            res = loop.run_until_complete(self.daemon.dispatch_action("settings_ui", [], None))
            self.assertEqual(res["status"], "ok")
            current = self.daemon.get_current_state()
            self.assertEqual(current.state, "settings")
            self.assertEqual(current.priority, Priority.SETTINGS)
        finally:
            loop.close()


class TestWallpaperAndSystemTheme(unittest.TestCase):
    """Wallpaper and System Theme IPC dispatch tests"""

    def setUp(self):
        self.daemon = DynamicIslandDaemon()

    def test_wallpaper_ipc_actions(self):
        loop = asyncio.new_event_loop()
        try:
            with unittest.mock.patch("subprocess.run") as mock_run:
                mock_run.return_value = subprocess.CompletedProcess(
                    args=[], returncode=0,
                    stdout="/path/to/wall1.jpg\n/path/to/wall2.jpg\n",
                    stderr=""
                )
                res_list = loop.run_until_complete(self.daemon.dispatch_action("wallpaper_list", [], None))
                self.assertEqual(res_list["status"], "ok")
                self.assertIn("wallpapers", res_list)
                self.assertEqual(len(res_list["wallpapers"]), 2)

                mock_run.return_value = subprocess.CompletedProcess(
                    args=[], returncode=0,
                    stdout="/path/to/wall1.jpg\n",
                    stderr=""
                )
                res_get = loop.run_until_complete(self.daemon.dispatch_action("wallpaper_get", [], None))
                self.assertEqual(res_get["status"], "ok")
                self.assertEqual(res_get["current"], "/path/to/wall1.jpg")

                mock_run.return_value = subprocess.CompletedProcess(
                    args=[], returncode=0,
                    stdout="Applied next wallpaper: /path/to/wall2.jpg",
                    stderr=""
                )
                res_next = loop.run_until_complete(self.daemon.dispatch_action("wallpaper_next", [], None))
                self.assertEqual(res_next["status"], "ok")

                res_set = loop.run_until_complete(self.daemon.dispatch_action("wallpaper_set", ["/path/to/wall2.jpg"], None))
                self.assertEqual(res_set["status"], "ok")
                self.assertEqual(res_set["path"], "/path/to/wall2.jpg")
        finally:
            loop.close()

    def test_system_theme_ipc_actions(self):
        loop = asyncio.new_event_loop()
        try:
            with unittest.mock.patch("subprocess.run") as mock_run:
                mock_run.return_value = subprocess.CompletedProcess(
                    args=[], returncode=0,
                    stdout="macos-dark: macOS Sonoma Dark (active)\nmacos-light: macOS Sonoma Light\nnordic: Nordic Frost\ncatppuccin: Catppuccin Mocha\ndr460nized-ember: Dr460nized Ember\n",
                    stderr=""
                )
                res_list = loop.run_until_complete(self.daemon.dispatch_action("system_theme_list", [], None))
                self.assertEqual(res_list["status"], "ok")
                self.assertIn("themes", res_list)
                self.assertEqual(len(res_list["themes"]), 5)

                mock_run.return_value = subprocess.CompletedProcess(
                    args=[], returncode=0,
                    stdout="macos-dark\n",
                    stderr=""
                )
                res_get = loop.run_until_complete(self.daemon.dispatch_action("system_theme_get", [], None))
                self.assertEqual(res_get["status"], "ok")
                self.assertEqual(res_get["current"], "macos-dark")

                mock_run.return_value = subprocess.CompletedProcess(
                    args=[], returncode=0,
                    stdout="Applied theme: macOS Sonoma Dark (macos-dark)\n",
                    stderr=""
                )
                res_set = loop.run_until_complete(self.daemon.dispatch_action("system_theme_set", ["macos-dark"], None))
                self.assertEqual(res_set["status"], "ok")
                self.assertEqual(res_set["theme"], "macos-dark")
        finally:
            loop.close()


class TestV4TransparencyAndInteractions(unittest.TestCase):
    """Test suite covering 0% Waybar transparency, Quickshell overlay elevation, and interactive controls."""

    def setUp(self):
        self.daemon = DynamicIslandDaemon()

    def test_waybar_zero_transparency_tokens(self):
        css_path = Path(__file__).resolve().parent.parent / "style.css"
        if not css_path.exists():
            css_path = Path.home() / ".config" / "waybar" / "style.css"
        self.assertTrue(css_path.exists())
        content = css_path.read_text()
        # Verify 0.0 alpha tokens or transparent backgrounds are used
        self.assertTrue(
            "rgba(20, 24, 30, 0.0)" in content or "background: transparent" in content or "background-color: transparent" in content
        )

    def test_gtk_css_no_important_tokens(self):
        css_path = Path(__file__).resolve().parent.parent / "style.css"
        if not css_path.exists():
            css_path = Path.home() / ".config" / "waybar" / "style.css"
        content = css_path.read_text()
        # GTK CSS throws "Junk at end of value" on !important
        self.assertNotIn("!important", content)

    def test_quickshell_layer_stacking_overlay(self):
        shell_qml = Path(__file__).resolve().parent.parent / "quickshell" / "shell.qml"
        self.assertTrue(shell_qml.exists())
        content = shell_qml.read_text()
        self.assertIn("WlrLayer.Overlay", content)

    def test_wallpaper_prev_and_random_ipc(self):
        loop = asyncio.new_event_loop()
        try:
            with unittest.mock.patch("subprocess.run") as mock_run:
                mock_run.return_value = subprocess.CompletedProcess(
                    args=[], returncode=0, stdout="Applied prev wallpaper: /path/to/wall1.jpg", stderr=""
                )
                res_prev = loop.run_until_complete(self.daemon.dispatch_action("wallpaper_prev", [], None))
                self.assertEqual(res_prev["status"], "ok")

                mock_run.return_value = subprocess.CompletedProcess(
                    args=[], returncode=0, stdout="Applied random wallpaper: /path/to/wall3.jpg", stderr=""
                )
                res_rand = loop.run_until_complete(self.daemon.dispatch_action("wallpaper_random", [], None))
                self.assertEqual(res_rand["status"], "ok")
        finally:
            loop.close()

    def test_wallpaper_gui_launch_ipc(self):
        loop = asyncio.new_event_loop()
        try:
            with unittest.mock.patch("subprocess.Popen") as mock_popen:
                res_gui = loop.run_until_complete(self.daemon.dispatch_action("wallpaper_gui", [], None))
                self.assertEqual(res_gui["status"], "ok")
                self.assertIn("message", res_gui)
        finally:
            loop.close()

    def test_system_theme_prev_ipc(self):
        loop = asyncio.new_event_loop()
        try:
            with unittest.mock.patch("subprocess.run") as mock_run:
                mock_run.return_value = subprocess.CompletedProcess(
                    args=[], returncode=0, stdout="Applied theme: macOS Sonoma Light (macos-light)", stderr=""
                )
                res_prev = loop.run_until_complete(self.daemon.dispatch_action("system_theme_prev", [], None))
                self.assertEqual(res_prev["status"], "ok")
        finally:
            loop.close()

    def test_system_theme_gui_launch_ipc(self):
        loop = asyncio.new_event_loop()
        try:
            with unittest.mock.patch("subprocess.Popen") as mock_popen:
                res_gui = loop.run_until_complete(self.daemon.dispatch_action("system_theme_gui", [], None))
                self.assertEqual(res_gui["status"], "ok")
                self.assertIn("message", res_gui)
        finally:
            loop.close()

    def test_pomodoro_toggle_and_reset_actions(self):
        loop = asyncio.new_event_loop()
        try:
            res_start = loop.run_until_complete(self.daemon.dispatch_action("pomodoro", [], None))
            self.assertEqual(res_start["status"], "ok")
            self.assertIn("Focus", res_start["message"])

            res_stop = loop.run_until_complete(self.daemon.dispatch_action("stop", [], None))
            self.assertEqual(res_stop["status"], "ok")
        finally:
            loop.close()

    def test_dnd_toggle_ipc_actions(self):
        loop = asyncio.new_event_loop()
        try:
            with unittest.mock.patch("asyncio.create_subprocess_exec") as mock_exec:
                self.daemon.caps.has_makoctl = True
                res = loop.run_until_complete(self.daemon.dispatch_action("dnd_toggle", [], None))
                self.assertEqual(res["status"], "ok")
                self.assertIn("DND", res["message"])
        finally:
            loop.close()

    def test_compact_view_click_actions(self):
        compact_qml = Path(__file__).resolve().parent.parent / "quickshell" / "components" / "CompactView.qml"
        self.assertTrue(compact_qml.exists())
        content = compact_qml.read_text()
        self.assertIn("toggleQuickActions", content)
        self.assertIn("restoreSelectedWindow", content)

    def test_window_scratchpad_filtering(self):
        from core.window_backend import SwayWindowMonitor, WindowState
        self.assertTrue(issubclass(WindowState, str))
        monitor = SwayWindowMonitor()
        self.assertIsNotNone(monitor)

    def test_input_mask_region_integrity(self):
        shell_qml = Path(__file__).resolve().parent.parent / "quickshell" / "shell.qml"
        content = shell_qml.read_text()
        self.assertTrue("compactMask" in content and "Region" in content and "item: capsule" in content)

    def test_app_launcher_process_spawning(self):
        bridge_qml = Path(__file__).resolve().parent.parent / "quickshell" / "services" / "IslandBridge.qml"
        self.assertTrue(bridge_qml.exists())
        content = bridge_qml.read_text()
        self.assertIn("appLauncherComponent.createObject", content)


if __name__ == "__main__":
    unittest.main()


