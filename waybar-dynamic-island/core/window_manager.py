#!/usr/bin/env python3
"""
Ratana Dynamic Island — Window Management & Minimize/Restore Engine
===================================================================
Manages Sway/SwayFX windows natively via IPC:
- Discovers active workspace windows and scratchpad (minimized) windows.
- Native Sway scratchpad minimize: `swaymsg [con_id=...] move scratchpad`
- Native Sway scratchpad restore: `swaymsg [con_id=...] scratchpad show; focus`
- Avoids manipulating raw surface geometries without compositor support.
"""

import json
import logging
import shutil
import subprocess
from typing import Any, Dict, List, Optional

log = logging.getLogger("ratana-island.window")

APP_ICON_MAP = {
    "kitty": "󰄛",
    "foot": "󰄛",
    "alacritty": "󰄛",
    "thunar": "󰉋",
    "dolphin": "󰉋",
    "nautilus": "󰉋",
    "brave-browser": "",
    "google-chrome": "",
    "firefox": "󰈹",
    "chromium": "",
    "code": "󰨞",
    "vscodium": "󰨞",
    "subl": "󰨞",
    "telegram": "󰖣",
    "org.telegram.desktop": "󰖣",
    "telegram-desktop": "󰖣",
    "discord": "󰙯",
    "vesktop": "󰙯",
    "webcord": "󰙯",
    "spotify": "󰓇",
    "vlc": "󰕧",
    "mpv": "󰕧",
    "gwenview": "󰋩",
    "blueman-manager": "󰂯",
}


def resolve_app_icon(app_id: str) -> str:
    """Map application ID or WM_CLASS to a Nerd Font glyph."""
    if not app_id:
        return "󰖲"
    clean_id = app_id.lower().strip()
    for key, icon in APP_ICON_MAP.items():
        if key in clean_id:
            return icon
    return "󰖲"


class WindowManager:
    """Sway / Wayland Native Window Controller."""

    resolve_app_icon = staticmethod(resolve_app_icon)

    @staticmethod
    def get_windows() -> Dict[str, Any]:
        """
        Query Sway tree via IPC and return categorized lists of active and minimized windows.
        """
        if not shutil.which("swaymsg"):
            return {
                "status": "error",
                "message": "swaymsg not available",
                "active_windows": [],
                "minimized_windows": []
            }

        try:
            out = subprocess.check_output(["swaymsg", "-t", "get_tree"], stderr=subprocess.DEVNULL)
            tree = json.loads(out)
        except Exception as e:
            log.warning(f"Failed to query Sway window tree: {e}")
            return {
                "status": "error",
                "message": f"Tree query failed: {e}",
                "active_windows": [],
                "minimized_windows": []
            }

        active: List[Dict[str, Any]] = []
        minimized: List[Dict[str, Any]] = []

        def traverse(node: Dict[str, Any], in_scratch: bool = False):
            is_scratch = in_scratch or (node.get("name") == "__i3_scratch")
            node_type = node.get("type", "")

            # A valid application window con
            if (node_type in ("con", "floating_con")) and node.get("name") and (node.get("app_id") or node.get("window_properties")):
                raw_app = node.get("app_id") or node.get("window_properties", {}).get("class") or ""
                con_id = node.get("id")
                title = node.get("name", "")
                focused = node.get("focused", False)

                node_rect = node.get("rect", {"x": 0, "y": 0, "width": 0, "height": 0})
                rect = {
                    "x": node_rect.get("x", 0),
                    "y": node_rect.get("y", 0),
                    "width": node_rect.get("width", 0),
                    "height": node_rect.get("height", 0),
                }

                win_info = {
                    "id": con_id,
                    "name": title,
                    "app_id": raw_app,
                    "icon": resolve_app_icon(raw_app),
                    "focused": focused,
                    "minimized": is_scratch,
                    "rect": rect
                }

                if is_scratch:
                    minimized.append(win_info)
                else:
                    active.append(win_info)

            # Traverse child nodes and floating nodes
            for child in node.get("nodes", []) + node.get("floating_nodes", []):
                traverse(child, is_scratch)

        traverse(tree)

        return {
            "status": "ok",
            "active_windows": active,
            "minimized_windows": minimized,
            "total_active": len(active),
            "total_minimized": len(minimized)
        }

    @staticmethod
    def minimize_window(con_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Move a window to the Sway scratchpad (native minimize).
        If con_id is None, targets the currently focused window.
        """
        if not shutil.which("swaymsg"):
            return {"status": "error", "message": "swaymsg not available"}

        if con_id is None:
            # Discover currently focused window
            wins = WindowManager.get_windows()
            focused = [w for w in wins.get("active_windows", []) if w.get("focused")]
            if not focused:
                return {"status": "error", "message": "No active window currently focused"}
            con_id = focused[0]["id"]

        try:
            cmd = f"[con_id={con_id}] move scratchpad"
            res = subprocess.run(["swaymsg", cmd], capture_output=True, text=True)
            if res.returncode == 0:
                log.info(f"Minimized window {con_id} to Sway scratchpad")
                return {
                    "status": "ok",
                    "con_id": con_id,
                    "minimized": True,
                    "message": f"Window {con_id} minimized to scratchpad"
                }
            return {
                "status": "error",
                "message": f"Sway error: {res.stderr.strip() or 'Failed to minimize'}"
            }
        except Exception as e:
            return {"status": "error", "message": f"Minimize failed: {e}"}

    @staticmethod
    def restore_window(con_id: int) -> Dict[str, Any]:
        """
        Restore a window from the Sway scratchpad and focus it.
        """
        if not shutil.which("swaymsg"):
            return {"status": "error", "message": "swaymsg not available"}

        try:
            # 1. Show window from scratchpad
            cmd_show = f"[con_id={con_id}] scratchpad show"
            subprocess.run(["swaymsg", cmd_show], capture_output=True, text=True)

            # 2. Focus window
            cmd_focus = f"[con_id={con_id}] focus"
            res = subprocess.run(["swaymsg", cmd_focus], capture_output=True, text=True)

            if res.returncode == 0:
                log.info(f"Restored window {con_id} from Sway scratchpad")
                return {
                    "status": "ok",
                    "con_id": con_id,
                    "restored": True,
                    "message": f"Window {con_id} restored and focused"
                }
            return {
                "status": "error",
                "message": f"Sway error: {res.stderr.strip() or 'Failed to restore'}"
            }
        except Exception as e:
            return {"status": "error", "message": f"Restore failed: {e}"}
