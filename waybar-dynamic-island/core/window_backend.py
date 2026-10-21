"""
Ratana Dynamic Island — Sway Window Management Backend (i3ipc & sysfs)
======================================================================
Manages window minimization to scratchpad, restoration, focus, geometry tracking,
and running app indicator tracking for Sway and SwayFX compositors with zero socket leaks.
"""

import json
import logging
import shutil
import subprocess
import threading
from typing import Any, Callable, Dict, List, Optional

log = logging.getLogger("ratana-island")

try:
    import i3ipc
    HAS_I3IPC = True
except ImportError:
    HAS_I3IPC = False
    log.warning("i3ipc module not found. Window management will operate in fallback mode.")


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
    "telegram": "󰈰",
    "org.telegram.desktop": "󰈰",
    "telegram-desktop": "󰈰",
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


class SwayWindowMonitor:
    """Interfaces with Sway/SwayFX compositor to track and control application windows."""

    def __init__(
        self,
        on_window_change: Optional[Callable[[], None]] = None,
        on_window_minimized: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_window_restored: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        self.on_window_change = on_window_change
        self.on_window_minimized = on_window_minimized
        self.on_window_restored = on_window_restored
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None

        # In-memory caches to eliminate constant polling and socket leaks
        self._cached_windows: List[Dict[str, Any]] = []
        self._last_geometries: Dict[int, Dict[str, int]] = {}
        self._prev_minimized_ids: set = set()

        # Initial prime
        self.refresh_cache_now()

    def start(self):
        """Start background window event listener if i3ipc is available."""
        if not HAS_I3IPC:
            return

        self._running = True
        self._thread = threading.Thread(target=self._run_event_loop, daemon=True, name="SwayWindowListener")
        self._thread.start()

    def stop(self):
        self._running = False

    def _run_event_loop(self):
        """Listen to Sway window events in a background thread."""
        conn = None
        try:
            conn = i3ipc.Connection()

            def on_event(ipc, event):
                if not self._running:
                    return
                try:
                    tree = ipc.get_tree()
                    self._update_cache_from_tree(tree)
                    if self.on_window_change:
                        self.on_window_change()
                except Exception as e:
                    log.debug(f"Window event processing error: {e}")

            conn.on("window::focus", on_event)
            conn.on("window::close", on_event)
            conn.on("window::new", on_event)
            conn.on("window::title", on_event)
            conn.on("window::move", on_event)
            conn.on("window::floating", on_event)
            conn.on("window::mark", on_event)

            # Prime cache with current connection tree
            try:
                self._update_cache_from_tree(conn.get_tree())
            except Exception:
                pass

            conn.main()
        except Exception as e:
            log.debug(f"Sway IPC event loop terminated or unavailable: {e}")
        finally:
            if conn is not None and hasattr(conn, "socket") and conn.socket:
                try:
                    conn.socket.close()
                except Exception:
                    pass

    def _update_cache_from_tree(self, tree):
        """Parse Sway container tree and update window and geometry caches."""
        new_windows: List[Dict[str, Any]] = []
        current_minimized_ids: set = set()

        try:
            for con in tree.descendants():
                app_id = con.app_id or getattr(con, "window_class", "") or ""
                if not app_id and not con.name:
                    continue
                if con.type not in ("con", "floating_con"):
                    continue
                if con.name in ("root", "__i3", "__i3_scratch"):
                    continue

                ws = con.workspace() if hasattr(con, "workspace") else None
                ws_name = ws.name if ws else ""
                if not ws_name:
                    continue

                is_scratchpad = (
                    ws_name == "__i3_scratch"
                    or con.scratchpad_state != "none"
                    or (con.parent and getattr(con.parent, "name", "") == "__i3_scratch")
                )

                if con.nodes and not con.window and not con.app_id:
                    continue

                rect = {
                    "x": getattr(con.rect, "x", 0),
                    "y": getattr(con.rect, "y", 0),
                    "width": getattr(con.rect, "width", 0),
                    "height": getattr(con.rect, "height", 0),
                }

                con_id = con.id
                icon = resolve_app_icon(app_id)

                if not is_scratchpad:
                    self._last_geometries[con_id] = rect
                else:
                    current_minimized_ids.add(con_id)
                    # Preserve last known non-scratchpad geometry if available
                    if con_id in self._last_geometries:
                        rect = self._last_geometries[con_id]

                win_info = {
                    "id": con_id,
                    "app_id": app_id,
                    "name": con.name or "",
                    "title": con.name or "",
                    "icon": icon,
                    "focused": bool(con.focused),
                    "minimized": bool(is_scratchpad),
                    "workspace": ws_name,
                    "rect": rect,
                }
                new_windows.append(win_info)

            # Detect state transitions (minimize / restore)
            with self._lock:
                just_minimized = current_minimized_ids - self._prev_minimized_ids
                just_restored = self._prev_minimized_ids - current_minimized_ids
                self._prev_minimized_ids = current_minimized_ids
                self._cached_windows = new_windows

            # Fire notifications outside lock
            if self.on_window_minimized and just_minimized:
                for wid in just_minimized:
                    w = next((x for x in new_windows if x["id"] == wid), None)
                    if w:
                        try:
                            self.on_window_minimized(w)
                        except Exception as e:
                            log.debug(f"on_window_minimized error: {e}")

            if self.on_window_restored and just_restored:
                for wid in just_restored:
                    w = next((x for x in new_windows if x["id"] == wid), None)
                    if w:
                        try:
                            self.on_window_restored(w)
                        except Exception as e:
                            log.debug(f"on_window_restored error: {e}")

        except Exception as e:
            log.debug(f"Error parsing Sway tree: {e}")

    def refresh_cache_now(self):
        """Fallback one-time cache refresh using swaymsg or i3ipc without socket leak."""
        if not shutil.which("swaymsg"):
            return

        try:
            out = subprocess.check_output(["swaymsg", "-t", "get_tree"], stderr=subprocess.DEVNULL)
            tree = json.loads(out)
            new_windows: List[Dict[str, Any]] = []
            minimized_ids: set = set()

            def traverse(node, in_scratch=False):
                is_scratch = in_scratch or (node.get("name") == "__i3_scratch")
                node_type = node.get("type", "")

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
                    if not is_scratch:
                        self._last_geometries[con_id] = rect
                    else:
                        minimized_ids.add(con_id)
                        if con_id in self._last_geometries:
                            rect = self._last_geometries[con_id]

                    new_windows.append({
                        "id": con_id,
                        "app_id": raw_app,
                        "name": title,
                        "title": title,
                        "icon": resolve_app_icon(raw_app),
                        "focused": focused,
                        "minimized": is_scratch,
                        "workspace": "__i3_scratch" if is_scratch else "active",
                        "rect": rect,
                    })

                for child in node.get("nodes", []) + node.get("floating_nodes", []):
                    traverse(child, is_scratch)

            traverse(tree)
            with self._lock:
                self._cached_windows = new_windows
                self._prev_minimized_ids = minimized_ids
        except Exception as e:
            log.debug(f"refresh_cache_now error: {e}")

    def get_windows(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Return list of active application windows. Uses in-memory cache for ultra-low CPU (<0.01ms)."""
        with self._lock:
            if self._cached_windows and not force_refresh:
                return list(self._cached_windows)

        if force_refresh or not self._cached_windows:
            self.refresh_cache_now()

        with self._lock:
            return list(self._cached_windows)

    def get_minimized_windows(self) -> List[Dict[str, Any]]:
        """Return only windows currently in Sway scratchpad."""
        return [w for w in self.get_windows() if w.get("minimized")]

    def minimize_window(self, con_id: Optional[int] = None) -> Dict[str, Any]:
        """Minimize window to scratchpad via Sway IPC and return window metadata and last geometry."""
        if not shutil.which("swaymsg"):
            return {"status": "error", "message": "swaymsg not available"}

        windows = self.get_windows()
        target = None
        if con_id is None:
            target = next((w for w in windows if w.get("focused")), None)
            if not target:
                return {"status": "error", "message": "No active window currently focused"}
            con_id = target["id"]
        else:
            target = next((w for w in windows if w["id"] == con_id), None)

        rect = self._last_geometries.get(con_id, target.get("rect", {}) if target else {})

        try:
            cmd = f"[con_id={con_id}] move scratchpad"
            res = subprocess.run(["swaymsg", cmd], capture_output=True, text=True)
            if res.returncode == 0:
                log.info(f"Minimized window {con_id} to Sway scratchpad")
                # Immediately update cached status
                with self._lock:
                    for w in self._cached_windows:
                        if w["id"] == con_id:
                            w["minimized"] = True
                            w["focused"] = False
                            w["rect"] = rect
                    self._prev_minimized_ids.add(con_id)

                win_info = target or {
                    "id": con_id,
                    "app_id": "",
                    "name": f"Window {con_id}",
                    "title": f"Window {con_id}",
                    "icon": "󰖲",
                    "rect": rect,
                }
                win_info["minimized"] = True
                win_info["rect"] = rect

                if self.on_window_minimized:
                    try:
                        self.on_window_minimized(win_info)
                    except Exception:
                        pass

                return {
                    "status": "ok",
                    "con_id": con_id,
                    "minimized": True,
                    "window": win_info,
                    "rect": rect,
                    "message": f"Window {con_id} minimized to scratchpad"
                }
            return {"status": "error", "message": f"Sway error: {res.stderr.strip()}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def restore_window(self, con_id: int) -> Dict[str, Any]:
        """Restore window from scratchpad and focus it via Sway IPC."""
        if not shutil.which("swaymsg"):
            return {"status": "error", "message": "swaymsg not available"}

        windows = self.get_windows()
        target = next((w for w in windows if w["id"] == con_id), None)
        rect = self._last_geometries.get(con_id, target.get("rect", {}) if target else {})

        try:
            cmd = f"[con_id={con_id}] scratchpad show; [con_id={con_id}] focus"
            res = subprocess.run(["swaymsg", cmd], capture_output=True, text=True)
            if res.returncode == 0:
                log.info(f"Restored window {con_id} from Sway scratchpad")
                with self._lock:
                    for w in self._cached_windows:
                        if w["id"] == con_id:
                            w["minimized"] = False
                            w["focused"] = True
                    self._prev_minimized_ids.discard(con_id)

                win_info = target or {
                    "id": con_id,
                    "app_id": "",
                    "name": f"Window {con_id}",
                    "title": f"Window {con_id}",
                    "icon": "󰖲",
                    "rect": rect,
                }
                win_info["minimized"] = False

                if self.on_window_restored:
                    try:
                        self.on_window_restored(win_info)
                    except Exception:
                        pass

                return {
                    "status": "ok",
                    "con_id": con_id,
                    "restored": True,
                    "window": win_info,
                    "rect": rect,
                    "message": f"Window {con_id} restored and focused"
                }
            return {"status": "error", "message": f"Sway error: {res.stderr.strip()}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def focus_window(self, con_id: int) -> Dict[str, Any]:
        """Focus specified window via Sway IPC."""
        if not shutil.which("swaymsg"):
            return {"status": "error", "message": "swaymsg not available"}

        try:
            cmd = f"[con_id={con_id}] focus"
            res = subprocess.run(["swaymsg", cmd], capture_output=True, text=True)
            if res.returncode == 0:
                return {"status": "ok", "message": f"Window {con_id} focused"}
            return {"status": "error", "message": f"Sway error: {res.stderr.strip()}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def toggle_window(self, con_id: int) -> Dict[str, Any]:
        """Toggle window: if focused -> minimize; if minimized or unfocused -> focus."""
        windows = self.get_windows()
        target = next((w for w in windows if w["id"] == con_id), None)
        if not target:
            return self.focus_window(con_id)

        if target.get("focused"):
            return self.minimize_window(con_id)
        else:
            return self.restore_window(con_id)

    def toggle_app_by_name(self, app_keyword: str, fallback_binary: Optional[str] = None) -> Dict[str, Any]:
        """Toggle or restore a window matching app_keyword, or launch fallback_binary."""
        windows = self.get_windows()
        keywords = app_keyword.lower().split("|")

        match = None
        for w in windows:
            app_id = (w.get("app_id") or "").lower()
            name = (w.get("name") or "").lower()
            if any(k in app_id or k in name for k in keywords):
                match = w
                if w.get("focused"):
                    break

        if match:
            return self.toggle_window(match["id"])
        elif fallback_binary:
            bin_to_launch = fallback_binary or keywords[0]
            bin_path = shutil.which(bin_to_launch)
            if bin_path:
                subprocess.Popen([bin_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
                return {"status": "ok", "message": f"Launched {bin_to_launch}"}
            else:
                return {"status": "error", "message": f"Binary '{bin_to_launch}' not found"}

        return {"status": "error", "message": f"No running window found for '{app_keyword}'"}
