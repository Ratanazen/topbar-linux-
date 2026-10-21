"""Unit tests for platform capability detection."""

import os
from unittest.mock import patch
from ratana_island.platform.capabilities import detect_capabilities


def test_detect_capabilities_wayland():
    with patch.dict(os.environ, {"WAYLAND_DISPLAY": "wayland-1", "SWAYSOCK": ""}, clear=True):
        caps = detect_capabilities()
        assert caps.is_wayland is True


def test_detect_capabilities_swayfx():
    with patch.dict(os.environ, {"WAYLAND_DISPLAY": "wayland-1", "SWAYSOCK": "/tmp/sway.sock"}):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "sway version 1.10 (SwayFX)"
            caps = detect_capabilities()
            assert caps.is_sway is True
            assert caps.is_swayfx is True
            assert caps.supports_blur is True
            assert caps.supports_shadows is True
