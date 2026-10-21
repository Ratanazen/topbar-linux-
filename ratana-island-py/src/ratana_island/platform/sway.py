"""Sway compositor IPC integration for active window and outputs."""

import json
import logging
import shutil
import subprocess
import threading
from typing import Callable, List, Optional

logger = logging.getLogger("ratana_island.sway")


class SwayService:
    def __init__(self, on_window_change: Optional[Callable[[str, str], None]] = None):
        self.on_window_change = on_window_change
        self.active_title: str = "Desktop"
        self.active_app_id: str = "sway"
        self._thread: Optional[threading.Thread] = None
        self._running: bool = False

    def get_outputs(self) -> List[dict]:
        swaymsg = shutil.which("swaymsg")
        if not swaymsg:
            return []
        try:
            res = subprocess.run([swaymsg, "-t", "get_outputs"], capture_output=True, text=True, timeout=1.0)
            if res.returncode == 0:
                return json.loads(res.stdout)
        except Exception as e:
            logger.debug(f"Failed to get Sway outputs: {e}")
        return []

    def get_focused_window(self) -> tuple[str, str]:
        swaymsg = shutil.which("swaymsg")
        if not swaymsg:
            return ("Desktop", "sway")
        try:
            res = subprocess.run([swaymsg, "-t", "get_tree"], capture_output=True, text=True, timeout=1.0)
            if res.returncode == 0:
                tree = json.loads(res.stdout)
                focused = self._find_focused_node(tree)
                if focused:
                    title = focused.get("name") or "Desktop"
                    app_id = focused.get("app_id") or focused.get("window_properties", {}).get("class") or "app"
                    return (title, app_id)
        except Exception:
            pass
        return ("Desktop", "sway")

    def _find_focused_node(self, node: dict) -> Optional[dict]:
        if node.get("focused"):
            return node
        for child in node.get("nodes", []):
            f = self._find_focused_node(child)
            if f:
                return f
        for child in node.get("floating_nodes", []):
            f = self._find_focused_node(child)
            if f:
                return f
        return None

    def start_listener(self) -> None:
        try:
            import i3ipc
            self._running = True
            self._thread = threading.Thread(target=self._i3ipc_worker, daemon=True)
            self._thread.start()
        except ImportError:
            logger.debug("i3ipc not available, active window tracking will be manual")

    def _i3ipc_worker(self) -> None:
        import i3ipc
        from gi.repository import GLib

        try:
            conn = i3ipc.Connection()

            def on_window(ipc, event):
                if not self._running:
                    return
                con = event.container
                title = con.name or "Desktop"
                app_id = con.app_id or (con.window_properties.get("class") if con.window_properties else "app") or "app"
                self.active_title = title
                self.active_app_id = app_id
                if self.on_window_change:
                    GLib.idle_add(self.on_window_change, title, app_id)

            conn.on("window::focus", on_window)
            conn.on("window::title", on_window)
            conn.main()
        except Exception as e:
            logger.debug(f"Sway IPC worker exited: {e}")

    def stop(self) -> None:
        self._running = False
