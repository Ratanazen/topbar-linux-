#!/usr/bin/env python3
"""
Ratana Dynamic Island — Smart Share & Window Management Automated Test Suite
============================================================================
Covers:
- Safe Drag & Drop URL and path sanitization (canonical paths, percent-encoding, Unicode, Khmer)
- Dangerous URL rejection (http, https, javascript, ftp)
- Application discovery (Telegram, Discord, Bluetooth OBEX, desktop mimetypes)
- Safe launch execution (Strict argv vector, shell=False guarantee)
- Sway tree parsing (active windows vs __i3_scratch scratchpad minimized windows)
- Sway window minimize and restore commands
- App icon mapping
"""

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure core and repo root are in python path
REPO_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_DIR / "scripts"
CORE_DIR = REPO_DIR / "core"

import sys
sys.path.insert(0, str(REPO_DIR))
sys.path.insert(0, str(SCRIPTS_DIR))
sys.path.insert(0, str(CORE_DIR))

from core.share_manager import ShareManager, format_size, get_file_icon
from core.window_manager import WindowManager, resolve_app_icon


class TestShareManagerSanitization(unittest.TestCase):
    """Test URL decoding, path canonicalization, Unicode handling, and security filtering."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_path = Path(self.temp_dir.name)

        # Create test files
        self.plain_file = self.base_path / "report.pdf"
        self.plain_file.write_text("dummy report content")

        self.space_file = self.base_path / "My Document 2026.txt"
        self.space_file.write_text("document with spaces")

        # Unicode / Khmer file name
        self.khmer_file = self.base_path / "ឯកសារ_ស្រាវជ្រាវ.png"
        self.khmer_file.write_bytes(b"\x89PNG\r\n\x1a\n")

        # Subdirectory
        self.sub_dir = self.base_path / "Folder_Project"
        self.sub_dir.mkdir()
        self.inside_file = self.sub_dir / "nested.json"
        self.inside_file.write_text('{"ok": true}')

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_canonical_file_paths(self):
        files = ShareManager.sanitize_urls([str(self.plain_file)])
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0]["path"], str(self.plain_file.resolve()))
        self.assertEqual(files[0]["name"], "report.pdf")
        self.assertFalse(files[0]["is_dir"])
        self.assertEqual(files[0]["mime"], "application/pdf")
        self.assertEqual(files[0]["icon"], "󰈙")

    def test_file_uri_with_spaces_and_percent_encoding(self):
        uri = self.space_file.as_uri()  # file:///.../My%20Document%202026.txt
        files = ShareManager.sanitize_urls([uri])
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0]["path"], str(self.space_file.resolve()))
        self.assertEqual(files[0]["name"], "My Document 2026.txt")
        self.assertIn("text/", files[0]["mime"])

    def test_unicode_and_khmer_script_paths(self):
        uri = self.khmer_file.as_uri()
        files = ShareManager.sanitize_urls([uri])
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0]["path"], str(self.khmer_file.resolve()))
        self.assertEqual(files[0]["name"], "ឯកសារ_ស្រាវជ្រាវ.png")
        self.assertEqual(files[0]["icon"], "󰋩")

    def test_directory_detection(self):
        files = ShareManager.sanitize_urls([str(self.sub_dir)])
        self.assertEqual(len(files), 1)
        self.assertTrue(files[0]["is_dir"])
        self.assertEqual(files[0]["icon"], "󰉋")
        self.assertEqual(files[0]["size_human"], "Folder")

    def test_reject_dangerous_schemes(self):
        dangerous_urls = [
            "http://example.com/malicious.sh",
            "https://evil.org/payload.exe",
            "javascript:alert('pwned')",
            "ftp://files.net/dump.tar",
            "data:text/html,<b>pwn</b>"
        ]
        files = ShareManager.sanitize_urls(dangerous_urls)
        # Dangerous schemes are strictly filtered out
        self.assertEqual(len(files), 0)

    def test_reject_non_existent_paths(self):
        missing = "/tmp/ratana_definitely_nonexistent_file_xyz_9999.txt"
        files = ShareManager.sanitize_urls([missing])
        self.assertEqual(len(files), 0)

    def test_human_size_formatting(self):
        self.assertEqual(ShareManager.format_size(500), "500 B")
        self.assertEqual(ShareManager.format_size(1024), "1.0 KB")
        self.assertEqual(ShareManager.format_size(int(1024 * 1024 * 2.5)), "2.5 MB")
        self.assertEqual(ShareManager.format_size(1024 * 1024 * 1024 * 4), "4.0 GB")


class TestShareManagerAppDiscovery(unittest.TestCase):
    """Test Telegram, Discord, Bluetooth OBEX, and desktop app discovery."""

    def setUp(self):
        ShareManager.clear_cache()

    @patch("shutil.which")
    def test_telegram_discovery_installed(self, mock_which):
        mock_which.side_effect = lambda binary: "/usr/bin/Telegram" if binary == "Telegram" else None
        res = ShareManager.get_telegram_status()
        self.assertTrue(res["installed"])
        self.assertIn("Telegram", res["name"])
        self.assertEqual(res["command"], ["/usr/bin/Telegram"])

    @patch("shutil.which")
    def test_discord_discovery_missing(self, mock_which):
        mock_which.return_value = None
        res = ShareManager.get_discord_status()
        self.assertFalse(res["installed"])
        self.assertEqual(res["badge"].lower(), "not installed")

    @patch("shutil.which")
    @patch("subprocess.check_output")
    def test_bluetooth_discovery_powered_on(self, mock_sub, mock_which):
        mock_which.return_value = "/usr/bin/blueman-sendto"
        mock_sub.return_value = b"Powered: yes\n"

        res = ShareManager.get_bluetooth_status()
        self.assertTrue(res["installed"])
        self.assertTrue(res["powered"])

    @patch("shutil.which")
    @patch("subprocess.check_output")
    def test_bluetooth_discovery_powered_off(self, mock_sub, mock_which):
        mock_which.return_value = "/usr/bin/blueman-sendto"
        mock_sub.return_value = b"Powered: no\n"

        res = ShareManager.get_bluetooth_status()
        self.assertTrue(res["installed"])
        self.assertFalse(res["powered"])


class TestShareManagerSafeLaunch(unittest.TestCase):
    """Verify security constraints: zero shell=True, strict argument vector arrays, no empty runs."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_file = Path(self.temp_dir.name) / "payload.txt"
        self.test_file.write_text("secure data")

    def tearDown(self):
        self.temp_dir.cleanup()

    @patch("subprocess.Popen")
    @patch("core.share_manager.ShareManager.get_telegram_status")
    def test_safe_telegram_launch_vector(self, mock_tg_status, mock_popen):
        mock_tg_status.return_value = {
            "installed": True,
            "command": ["/usr/bin/Telegram"]
        }

        res = ShareManager.launch_share("telegram", [str(self.test_file)])
        self.assertEqual(res["status"], "ok")

        # Popen must have been called with argv list, NOT a string, and shell=False
        mock_popen.assert_called_once()
        args, kwargs = mock_popen.call_args
        cmd = args[0]
        self.assertIsInstance(cmd, list)
        self.assertEqual(cmd[0], "/usr/bin/Telegram")
        self.assertIn(str(self.test_file.resolve()), cmd)
        self.assertFalse(kwargs.get("shell", False))

    def test_refuse_empty_file_list(self):
        res = ShareManager.launch_share("telegram", [])
        self.assertEqual(res["status"], "error")
        self.assertIn("invalid or missing", res["message"])

    @patch("core.share_manager.ShareManager.get_discord_status")
    def test_refuse_unavailable_app(self, mock_dc_status):
        mock_dc_status.return_value = {"installed": False, "reason": "Discord is not installed"}
        res = ShareManager.launch_share("discord", [str(self.test_file)])
        self.assertEqual(res["status"], "error")
        self.assertIn("Discord is not installed", res["message"])


class TestWindowManager(unittest.TestCase):
    """Test Sway tree parsing, active window collection, scratchpad minimization, and restore."""

    MOCK_SWAY_TREE = {
        "id": 1,
        "name": "root",
        "nodes": [
            {
                "id": 2,
                "name": "output-1",
                "nodes": [
                    {
                        "id": 10,
                        "name": "1",
                        "type": "workspace",
                        "nodes": [
                            {
                                "id": 101,
                                "name": "kitty - /home/reny",
                                "type": "con",
                                "app_id": "kitty",
                                "focused": True,
                                "nodes": []
                            },
                            {
                                "id": 102,
                                "name": "Mozilla Firefox",
                                "type": "con",
                                "app_id": "firefox",
                                "focused": False,
                                "nodes": []
                            }
                        ]
                    },
                    {
                        "id": 99,
                        "name": "__i3_scratch",
                        "type": "workspace",
                        "floating_nodes": [
                            {
                                "id": 201,
                                "name": "Thunar File Manager",
                                "type": "con",
                                "app_id": "thunar",
                                "focused": False,
                                "nodes": []
                            }
                        ]
                    }
                ]
            }
        ]
    }

    @patch("shutil.which")
    @patch("subprocess.check_output")
    def test_parse_sway_tree_active_and_minimized(self, mock_sub, mock_which):
        mock_which.return_value = "/usr/bin/swaymsg"
        mock_sub.return_value = json.dumps(self.MOCK_SWAY_TREE).encode("utf-8")

        info = WindowManager.get_windows()
        self.assertEqual(info["status"], "ok")
        active = info["active_windows"]
        minimized = info["minimized_windows"]

        # Active windows
        self.assertEqual(len(active), 2)
        self.assertEqual(active[0]["id"], 101)
        self.assertEqual(active[0]["app_id"], "kitty")
        self.assertEqual(active[0]["icon"], "󰄛")
        self.assertTrue(active[0]["focused"])
        self.assertFalse(active[0]["minimized"])

        self.assertEqual(active[1]["id"], 102)
        self.assertEqual(active[1]["app_id"], "firefox")
        self.assertEqual(active[1]["icon"], "󰈹")

        # Minimized (scratchpad) windows
        self.assertEqual(len(minimized), 1)
        self.assertEqual(minimized[0]["id"], 201)
        self.assertEqual(minimized[0]["app_id"], "thunar")
        self.assertEqual(minimized[0]["icon"], "󰉋")
        self.assertTrue(minimized[0]["minimized"])

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_minimize_window_command(self, mock_run, mock_which):
        mock_which.return_value = "/usr/bin/swaymsg"
        mock_run.return_value = MagicMock(returncode=0)

        res = WindowManager.minimize_window(101)
        self.assertEqual(res["status"], "ok")
        self.assertTrue(res["minimized"])

        # Check command sent to swaymsg
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        self.assertEqual(cmd, ["swaymsg", "[con_id=101] move scratchpad"])

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_restore_window_command(self, mock_run, mock_which):
        mock_which.return_value = "/usr/bin/swaymsg"
        mock_run.return_value = MagicMock(returncode=0)

        res = WindowManager.restore_window(201)
        self.assertEqual(res["status"], "ok")
        self.assertTrue(res["restored"])

        # Check commands sent to swaymsg
        self.assertEqual(mock_run.call_count, 2)
        cmd_show = mock_run.call_args_list[0][0][0]
        cmd_focus = mock_run.call_args_list[1][0][0]
        self.assertEqual(cmd_show, ["swaymsg", "[con_id=201] scratchpad show"])
        self.assertEqual(cmd_focus, ["swaymsg", "[con_id=201] focus"])

    def test_app_icon_mapping(self):
        self.assertEqual(WindowManager.resolve_app_icon("kitty"), "󰄛")
        self.assertEqual(WindowManager.resolve_app_icon("brave-browser"), "")
        self.assertEqual(WindowManager.resolve_app_icon("thunar"), "󰉋")
        self.assertEqual(WindowManager.resolve_app_icon("code"), "󰨞")
        self.assertEqual(WindowManager.resolve_app_icon("org.telegram.desktop"), "󰖣")
        self.assertEqual(WindowManager.resolve_app_icon("discord"), "󰙯")
        self.assertEqual(WindowManager.resolve_app_icon("unknown_binary"), "󰖲")


if __name__ == "__main__":
    unittest.main()
