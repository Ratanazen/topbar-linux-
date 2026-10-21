"""
Ratana Dynamic Island — Sway Window Management Backend (i3ipc & sysfs)
======================================================================
Manages window minimization to scratchpad, restoration, focus, geometry tracking,
and running app indicator tracking for Sway and SwayFX compositors with zero socket leaks.
"""

from enum import Enum
import json
import logging
import os
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


class WindowState(str, Enum):
    NORMAL = "normal"
    MINIMIZE_REQUESTED = "minimize_requested"
    MINIMIZE_ANIMATING = "minimize_animating"
    MINIMIZED = "minimized"
    RESTORE_REQUESTED = "restore_requested"
    RESTORE_ANIMATING = "restore_animating"
    RESTORED = "restored"
    CLOSED = "closed"


THUMBNAIL_DIR = "/tmp/ratana-thumbnails"
MAX_CACHED_THUMBNAILS = 10


def ensure_thumbnail_dir() -> str:
    try:
        os.makedirs(THUMBNAIL_DIR, mode=0o700, exist_ok=True)
        return THUMBNAIL_DIR
    except Exception as e:
        log.debug(f"Failed to create thumbnail directory: {e}")
        return ""


def prune_thumbnail_cache():
    try:
        if not os.path.isdir(THUMBNAIL_DIR):
            return
        files = [
            os.path.join(THUMBNAIL_DIR, f)
            for f in os.listdir(THUMBNAIL_DIR)
            if f.endswith(".jpg") or f.endswith(".png")
        ]
        if len(files) > MAX_CACHED_THUMBNAILS:
            files.sort(key=lambda x: os.path.getmtime(x))
            for f in files[:-MAX_CACHED_THUMBNAILS]:
                try:
                    os.unlink(f)
                except OSError:
                    pass
    except Exception as e:
        log.debug(f"Error pruning thumbnail cache: {e}")


def cleanup_window_thumbnail(con_id: int):
    try:
        for ext in (".jpg", ".png"):
            p = os.path.join(THUMBNAIL_DIR, f"{con_id}{ext}")
            if os.path.exists(p):
                os.unlink(p)
    except Exception:
        pass


def capture_window_thumbnail(con_id: int, rect: Dict[str, int]) -> str:
    """Capture a fast lightweight JPEG snapshot of the window using grim."""
    if not shutil.which("grim"):
        return ""
    tdir = ensure_thumbnail_dir()
    if not tdir:
        return ""

    x = rect.get("x", 0)
    y = rect.get("y", 0)
    w = rect.get("width", 0)
    h = rect.get("height", 0)
    if w < 50 or h < 50:
        return ""

    prune_thumbnail_cache()
    out_path = os.path.join(tdir, f"{con_id}.jpg")
    geo = f"{x},{y} {w}x{h}"

    try:
        cmd = ["grim", "-t", "jpeg", "-q", "75", "-g", geo, out_path]
        res = subprocess.run(cmd, capture_output=True, timeout=0.3)
        if res.returncode == 0 and os.path.exists(out_path) and os.path.getsize(out_path) > 0:
            return out_path
    except Exception as e:
        log.debug(f"Thumbnail capture skipped or failed for {con_id}: {e}")
    return ""


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
        self._window_states: Dict[int, str] = {}
        self._thumbnail_paths: Dict[int, str] = {}

        # Initial prime
        self.refresh_cache_now()

    def get_window_state(self, con_id: int) -> str:
        with self._lock:
            return self._window_states.get(con_id, WindowState.NORMAL.value)

    def _set_window_state(self, con_id: int, state: WindowState):
        with self._lock:
            self._window_states[con_id] = state.value

    def _handle_stale_window(self, con_id: int):
        """Clean up references to a window that is no longer accessible."""
        with self._lock:
            self._cached_windows = [w for w in self._cached_windows if w["id"] != con_id]
            self._prev_minimized_ids.discard(con_id)
            self._last_geometries.pop(con_id, None)
            self._thumbnail_paths.pop(con_id, None)
            self._window_states[con_id] = WindowState.CLOSED.value
        cleanup_window_thumbnail(con_id)
        if self.on_window_change:
            try:
                self.on_window_change()
            except Exception:
                pass

    def start(self):
        """Start background window event listener if i3ipc is available."""
        if not HAS_I3IPC:
            return

        self._running = True
        self._thread = threading.Thread(target=self._run_event_loop, daemon=True, name="SwayWindowListener")
        self._thread.start()

    def stop(self):
        self._running = False
        if hasattr(self, "_conn") and self._conn is not None:
            try:
                self._conn.main_quit()
            except Exception:
                pass

    def _run_event_loop(self):
        """Listen to Sway window events in a background thread."""
        conn = None
        try:
            conn = i3ipc.Connection()
            self._conn = conn
            if not self._running:
                return

            def on_event(ipc, event):
                if not self._running:
                    return
                try:
                    tree = ipc.get_tree()
                    self._update_cache_from_tree(tree, notify=True)
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
                self._update_cache_from_tree(conn.get_tree(), notify=False)
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

    def _update_cache_from_tree(self, tree, notify: bool = True):
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

                # Resolve output name
                output_name = ""
                curr = con
                while curr:
                    if getattr(curr, "type", "") == "output":
                        output_name = getattr(curr, "name", "") or ""
                        break
                    curr = getattr(curr, "parent", None)

                con_id = con.id
                icon = resolve_app_icon(app_id)

                if not is_scratchpad:
                    self._last_geometries[con_id] = rect
                    self._set_window_state(con_id, WindowState.NORMAL)
                else:
                    current_minimized_ids.add(con_id)
                    # Preserve last known non-scratchpad geometry if available
                    if con_id in self._last_geometries:
                        rect = self._last_geometries[con_id]
                    self._set_window_state(con_id, WindowState.MINIMIZED)

                win_info = {
                    "id": con_id,
                    "app_id": app_id,
                    "name": con.name or "",
                    "title": con.name or "",
                    "icon": icon,
                    "focused": bool(con.focused),
                    "minimized": bool(is_scratchpad),
                    "workspace": ws_name,
                    "output": output_name,
                    "rect": rect,
                    "thumbnail": self._thumbnail_paths.get(con_id, ""),
                    "state": self.get_window_state(con_id),
                }
                new_windows.append(win_info)

            # Cleanup closed windows
            all_current_ids = {w["id"] for w in new_windows}
            closed_ids = set(self._last_geometries.keys()) - all_current_ids
            for cid in closed_ids:
                cleanup_window_thumbnail(cid)
                self._thumbnail_paths.pop(cid, None)
                self._last_geometries.pop(cid, None)
                self._set_window_state(cid, WindowState.CLOSED)

            # Detect state transitions (minimize / restore)
            with self._lock:
                just_minimized = current_minimized_ids - self._prev_minimized_ids
                just_restored = self._prev_minimized_ids - current_minimized_ids
                self._prev_minimized_ids = current_minimized_ids
                self._cached_windows = new_windows

            # Fire notifications outside lock
            if notify and self._running and self.on_window_minimized and just_minimized:
                for wid in just_minimized:
                    w = next((x for x in new_windows if x["id"] == wid), None)
                    if w:
                        try:
                            self.on_window_minimized(w)
                        except Exception as e:
                            log.debug(f"on_window_minimized error: {e}")

            if notify and self._running and self.on_window_restored and just_restored:
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

            def traverse(node, in_scratch=False, current_output=""):
                is_scratch = in_scratch or (node.get("name") == "__i3_scratch")
                node_type = node.get("type", "")
                if node_type == "output":
                    current_output = node.get("name", "")

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
                        self._set_window_state(con_id, WindowState.NORMAL)
                    else:
                        minimized_ids.add(con_id)
                        if con_id in self._last_geometries:
                            rect = self._last_geometries[con_id]
                        self._set_window_state(con_id, WindowState.MINIMIZED)

                    new_windows.append({
                        "id": con_id,
                        "app_id": raw_app,
                        "name": title,
                        "title": title,
                        "icon": resolve_app_icon(raw_app),
                        "focused": focused,
                        "minimized": is_scratch,
                        "workspace": "__i3_scratch" if is_scratch else "active",
                        "output": current_output,
                        "rect": rect,
                        "thumbnail": self._thumbnail_paths.get(con_id, ""),
                        "state": self.get_window_state(con_id),
                    })

                for child in node.get("nodes", []) + node.get("floating_nodes", []):
                    traverse(child, is_scratch, current_output)

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

    def minimize_window(self, con_id: Optional[int] = None, allow_thumbnail: bool = True) -> Dict[str, Any]:
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

        # Transition state: MINIMIZE_REQUESTED
        self._set_window_state(con_id, WindowState.MINIMIZE_REQUESTED)

        # Capture thumbnail only before window is hidden to scratchpad
        thumb_path = ""
        if allow_thumbnail and rect and rect.get("width", 0) >= 50 and rect.get("height", 0) >= 50:
            thumb_path = capture_window_thumbnail(con_id, rect)
            if thumb_path:
                self._thumbnail_paths[con_id] = thumb_path

        # Transition state: MINIMIZE_ANIMATING
        self._set_window_state(con_id, WindowState.MINIMIZE_ANIMATING)

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
                            if thumb_path:
                                w["thumbnail"] = thumb_path
                            w["state"] = WindowState.MINIMIZED.value
                    self._prev_minimized_ids.add(con_id)

                self._set_window_state(con_id, WindowState.MINIMIZED)

                win_info = dict(target) if target else {
                    "id": con_id,
                    "app_id": "",
                    "name": f"Window {con_id}",
                    "title": f"Window {con_id}",
                    "icon": "󰖲",
                    "rect": rect,
                }
                win_info["minimized"] = True
                win_info["rect"] = rect
                win_info["thumbnail"] = thumb_path
                win_info["state"] = WindowState.MINIMIZED.value

                if self.on_window_minimized:
                    try:
                        self.on_window_minimized(win_info)
                    except Exception as e:
                        log.debug(f"on_window_minimized error: {e}")

                return {
                    "status": "ok",
                    "con_id": con_id,
                    "minimized": True,
                    "window": win_info,
                    "rect": rect,
                    "thumbnail": thumb_path,
                    "message": f"Window {con_id} minimized to scratchpad"
                }
            self._set_window_state(con_id, WindowState.NORMAL)
            return {"status": "error", "message": f"Sway error: {res.stderr.strip()}"}
        except Exception as e:
            self._set_window_state(con_id, WindowState.NORMAL)
            return {"status": "error", "message": str(e)}

    def restore_window(self, con_id: int) -> Dict[str, Any]:
        """Restore window from scratchpad and focus it via Sway IPC."""
        if not shutil.which("swaymsg"):
            return {"status": "error", "message": "swaymsg not available"}

        windows = self.get_windows()
        target = next((w for w in windows if w["id"] == con_id), None)
        rect = self._last_geometries.get(con_id, target.get("rect", {}) if target else {})
        thumb_path = self._thumbnail_paths.get(con_id, target.get("thumbnail", "") if target else "")

        # Transition state: RESTORE_REQUESTED
        self._set_window_state(con_id, WindowState.RESTORE_REQUESTED)

        win_info = dict(target) if target else {
            "id": con_id,
            "app_id": "",
            "name": f"Window {con_id}",
            "title": f"Window {con_id}",
            "icon": "󰖲",
            "rect": rect,
        }
        win_info["minimized"] = False
        win_info["rect"] = rect
        win_info["thumbnail"] = thumb_path
        win_info["state"] = WindowState.RESTORE_ANIMATING.value

        # Transition state: RESTORE_ANIMATING
        self._set_window_state(con_id, WindowState.RESTORE_ANIMATING)

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
                            w["state"] = WindowState.NORMAL.value
                    self._prev_minimized_ids.discard(con_id)

                self._set_window_state(con_id, WindowState.RESTORED)
                cleanup_window_thumbnail(con_id)
                self._thumbnail_paths.pop(con_id, None)

                if self.on_window_restored:
                    try:
                        self.on_window_restored(win_info)
                    except Exception as e:
                        log.debug(f"on_window_restored error: {e}")

                self._set_window_state(con_id, WindowState.NORMAL)

                return {
                    "status": "ok",
                    "con_id": con_id,
                    "restored": True,
                    "window": win_info,
                    "rect": rect,
                    "message": f"Window {con_id} restored and focused"
                }
            else:
                err = res.stderr.strip()
                log.warning(f"Failed to restore window {con_id}: {err}. Handling stale window.")
                self._handle_stale_window(con_id)
                return {
                    "status": "error",
                    "stale": True,
                    "con_id": con_id,
                    "message": f"Window {con_id} is stale or closed ({err})"
                }
        except Exception as e:
            self._handle_stale_window(con_id)
            return {"status": "error", "stale": True, "con_id": con_id, "message": str(e)}

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
