"""Compositor and environment capability detector."""

import os
import shutil
import subprocess
from dataclasses import dataclass
from typing import Optional


@dataclass
class PlatformCapabilities:
    is_wayland: bool = False
    is_sway: bool = False
    is_swayfx: bool = False
    has_layer_shell: bool = False
    supports_blur: bool = False
    supports_shadows: bool = False
    supports_rounded_corners: bool = True
    compositor_name: str = "Unknown"
    compositor_version: str = "Unknown"


def detect_capabilities() -> PlatformCapabilities:
    caps = PlatformCapabilities()

    # 1. Wayland check
    wayland_display = os.environ.get("WAYLAND_DISPLAY")
    session_type = os.environ.get("XDG_SESSION_TYPE", "").lower()
    caps.is_wayland = bool(wayland_display) or (session_type == "wayland")

    # 2. Sway / SwayFX check
    swaysock = os.environ.get("SWAYSOCK")
    swaymsg_bin = shutil.which("swaymsg")
    if swaysock and swaymsg_bin:
        caps.is_sway = True
        try:
            res = subprocess.run(
                [swaymsg_bin, "-t", "get_version"],
                capture_output=True,
                text=True,
                timeout=1.5,
            )
            if res.returncode == 0:
                out = res.stdout.lower()
                caps.compositor_version = res.stdout.strip()
                if "swayfx" in out:
                    caps.is_swayfx = True
                    caps.compositor_name = "SwayFX"
                    caps.supports_blur = True
                    caps.supports_shadows = True
                else:
                    caps.compositor_name = "Sway"
        except Exception:
            caps.compositor_name = "Sway"
    elif caps.is_wayland:
        desktop = os.environ.get("XDG_CURRENT_DESKTOP", "Wayland")
        caps.compositor_name = desktop

    # 3. Layer shell support check
    try:
        import gi
        gi.require_version("Gtk", "4.0")
        gi.require_version("Gtk4LayerShell", "1.0")
        from gi.repository import Gtk4LayerShell
        caps.has_layer_shell = Gtk4LayerShell.is_supported() if hasattr(Gtk4LayerShell, "is_supported") else True
    except Exception:
        caps.has_layer_shell = False

    return caps
