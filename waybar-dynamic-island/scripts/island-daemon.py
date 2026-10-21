#!/usr/bin/env python3
"""
Ratana Dynamic Island Daemon
============================
Production-ready Linux Dynamic Island daemon for Waybar (Sway/SwayFX & Hyprland)
and Quickshell Pro (Qt Quick / QML Layer Shell Overlay).

Architectural Highlights:
- Modular Architecture: Shared Core in `core/` package
- Asynchronous Event-Driven Architecture (asyncio)
- Strict Waybar Output Protocol: Single-line JSON per update, flushed immediately
- Priority Queue & Restoration: Transient events auto-expire and restore the highest-priority active state
- Real Bluetooth Engine: BlueZ D-Bus integration and bluetoothctl fallback
- Secure IPC: Unix domain socket ($XDG_RUNTIME_DIR/ratana-island.sock, 0o600) with validated JSON schemas
- Single Instance: Secured via fcntl.flock on $XDG_RUNTIME_DIR/ratana-island.lock
- Modular Adapters: MPRIS, PipeWire/pactl, Backlight, D-Bus Notifications, UPower, Recording, Network, Clipboard
- Zero shell=True: Explicit argument vectors prevent injection attacks
- Privacy-First: Network SSID masking, zero clipboard content inspection/logging
- Configuration: ~/.config/ratana-island/config.ini

Author: Principal Linux Desktop Engineer
License: MIT
"""

import asyncio
import datetime
import fcntl
import html
import json
import logging
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Ensure `core` package is discoverable (local repo takes precedence over installed config)
for search_dir in [
    Path(__file__).resolve().parent,
    Path.home() / ".config" / "ratana-island",
    Path(__file__).resolve().parent.parent,
]:
    if (search_dir / "core").is_dir():
        if str(search_dir) in sys.path:
            sys.path.remove(str(search_dir))
        sys.path.insert(0, str(search_dir))

# Import shared core modules
from core.audio_backend import AudioBackend
from core.battery_backend import BatteryBackend
from core.bluetooth_backend import BluetoothBackend
from core.brightness_backend import BrightnessBackend
from core.clipboard_backend import ClipboardBackend
from core.config_manager import (
    CONFIG_DIR,
    CONFIG_FILE,
    LOCK_PATH,
    MODES,
    PROTOCOL_VERSION,
    RUNTIME_DIR,
    SOCKET_PATH,
    THEME_PRESETS,
    BackendCapabilities,
    IslandConfig,
    normalize_theme,
)
from core.event_manager import EventManager
from core.ipc_server import IpcServer
from core.media_backend import MediaBackend
from core.network_backend import NetworkBackend
from core.notification_backend import NotificationBackend
from core.priority_manager import VALID_STATES, Priority, is_valid_state
from core.recording_backend import RecordingBackend
from core.state_manager import (
    BLOCKS_EMPTY,
    BLOCKS_FILLED,
    LANGUAGE_MAP,
    IslandState,
    build_progress_bar,
    resolve_app_icon,
    resolve_language_info,
    truncate_text,
)
from core.share_backend import ShareManager
from core.system_metrics import SystemMetricsMonitor
from core.timer_manager import TimerManager, parse_duration
from core.window_backend import SwayWindowMonitor

# ==============================================================================
# Logging & Diagnostics (Stderr only — Keeps stdout pristine for Waybar)
# ==============================================================================
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [ratana-island] %(message)s",
    stream=sys.stderr
)
log = logging.getLogger("ratana-island")


# ==============================================================================
# Dynamic Island Core Daemon
# ==============================================================================
class DynamicIslandDaemon:
    def __init__(self, config: Optional[IslandConfig] = None, tasks_file: Optional[Path] = None):
        self.config = config or IslandConfig()
        self.caps = BackendCapabilities()
        log.info(f"System audit: {self.caps.summary()}")

        # Core State & Event Managers
        self.events = EventManager()
        self.transient_states: List[IslandState] = self.events.transient_states

        self.active_media_state: Optional[IslandState] = None
        self.active_timer_state: Optional[IslandState] = None
        self.active_recording_state: Optional[IslandState] = None
        self.active_power_state: Optional[IslandState] = None
        self.current_json_line: str = ""

        # Timer & Stopwatch internals
        self.timer_mgr = TimerManager()
        self.timer_end_timestamp: Optional[float] = None
        self.timer_label: str = ""
        self.timer_paused: bool = False
        self.timer_remaining_on_pause: float = 0.0
        self.stopwatch_start_timestamp: Optional[float] = None

        # Debouncing timestamps
        self.last_volume_time: float = 0
        self.last_brightness_time: float = 0
        self.last_clipboard_time: float = 0
        self.last_network_time: float = 0

        # Feature K: Task & To-Do Tracker
        env_tasks = os.environ.get("RATANA_TASKS_FILE")
        if tasks_file is not None:
            self.tasks_file = tasks_file
        elif env_tasks:
            self.tasks_file = Path(env_tasks)
        else:
            self.tasks_file = CONFIG_DIR / "tasks.json"
        self.tasks: List[Dict[str, Any]] = self._load_tasks()
        self.active_task_state: Optional[IslandState] = None
        self._update_active_task_state()

        # Language / Keyboard Layout Tracking
        self.current_layout_name: str = self._detect_current_layout()
        self.last_layout_time: float = 0

        # Initialize Subsystem Backends
        self.media_backend = MediaBackend(self.config, self.caps, self._on_media_state_changed)
        self.bluetooth_backend = BluetoothBackend(self.config, self.push_transient_event)
        self.audio_backend = AudioBackend(self.config, self.caps, self.push_transient_event)
        self.brightness_backend = BrightnessBackend(self.config, self.caps, self.push_transient_event)
        self.battery_backend = BatteryBackend(
            self.config, self.caps, self.push_transient_event, self._on_power_state_changed
        )
        self.recording_backend = RecordingBackend(self.config, self._on_recording_state_changed)
        self.network_backend = NetworkBackend(self.config, self.caps, self.push_transient_event)
        self.clipboard_backend = ClipboardBackend(self.config, self.caps, self.push_transient_event)
        self.notification_backend = NotificationBackend(self.config, self.caps, self.push_transient_event)
        self.system_metrics_monitor = SystemMetricsMonitor(self._on_metrics_updated)
        self.current_cpu: float = 0.0
        self.current_mem: float = 0.0

        # Smart Share & Sway Window Management
        self.share_manager = ShareManager(self.bluetooth_backend)
        self.active_dropped_files: List[Dict[str, Any]] = []
        self.active_share_targets: List[Dict[str, Any]] = []
        self.window_monitor = SwayWindowMonitor(
            on_window_change=self._on_window_state_changed,
            on_window_minimized=self._on_window_minimized,
            on_window_restored=self._on_window_restored
        )
        self.window_monitor.start()

        # IPC Server & Client Writers
        self.ipc_server = IpcServer(SOCKET_PATH, self.dispatch_action, initial_state_provider=self.get_current_stream_line)
        self.client_writers: List[asyncio.StreamWriter] = self.ipc_server.client_writers

    def get_current_stream_line(self) -> str:
        state = self.get_current_state()
        return json.dumps(state.to_waybar_payload(self.config), ensure_ascii=False)

    def _on_metrics_updated(self, cpu: float, mem: float):
        self.current_cpu = cpu
        self.current_mem = mem

    def _on_media_state_changed(self, state: Optional[IslandState]):
        self.active_media_state = state
        self.render_and_broadcast()

    def _on_power_state_changed(self, state: Optional[IslandState]):
        self.active_power_state = state
        self.render_and_broadcast()

    def _on_recording_state_changed(self, state: Optional[IslandState]):
        self.active_recording_state = state
        self.render_and_broadcast()

    def _on_window_state_changed(self):
        self.render_and_broadcast()

    def _on_window_minimized(self, win_info: Dict[str, Any]):
        title = truncate_text(win_info.get("name") or win_info.get("title") or win_info.get("app_id") or "Window", 18)
        icon = win_info.get("icon", "󰖰")
        rect = win_info.get("rect", {})
        con_id = win_info.get("id", 0)

        feedback = IslandState(
            event_id="window-min",
            source="window",
            state="minimized",
            priority=Priority.WINDOW_MINIMIZE,
            icon=icon,
            title=title,
            subtitle="Minimized to Island",
            duration=2.0
        )
        self.push_transient_event(feedback)

        # Broadcast animation event to Quickshell
        anim_payload = {
            "type": "minimize",
            "id": con_id,
            "app_id": win_info.get("app_id", ""),
            "title": title,
            "icon": icon,
            "rect": rect,
            "style": getattr(self.config, "minimize_style", "macos-scale"),
            "target": getattr(self.config, "minimize_target", "island"),
            "duration": getattr(self.config, "minimize_duration_ms", 380),
        }
        self.ipc_server.broadcast_stream(json.dumps({"window_anim": anim_payload}, ensure_ascii=False))

    def _on_window_restored(self, win_info: Dict[str, Any]):
        title = truncate_text(win_info.get("name") or win_info.get("title") or win_info.get("app_id") or "Window", 18)
        icon = win_info.get("icon", "󰖯")
        rect = win_info.get("rect", {})
        con_id = win_info.get("id", 0)

        feedback = IslandState(
            event_id="window-res",
            source="window",
            state="restoring",
            priority=Priority.WINDOW_MINIMIZE,
            icon=icon,
            title=title,
            subtitle="Restored from Island",
            duration=1.8
        )
        self.push_transient_event(feedback)

        # Broadcast restore animation event to Quickshell
        anim_payload = {
            "type": "restore",
            "id": con_id,
            "app_id": win_info.get("app_id", ""),
            "title": title,
            "icon": icon,
            "rect": rect,
            "style": getattr(self.config, "minimize_style", "macos-scale"),
            "target": getattr(self.config, "minimize_target", "island"),
            "duration": getattr(self.config, "minimize_duration_ms", 380),
        }
        self.ipc_server.broadcast_stream(json.dumps({"window_anim": anim_payload}, ensure_ascii=False))

    def _detect_current_layout(self) -> str:
        """Query compositor for active keyboard layout at startup."""
        if self.caps.is_sway:
            try:
                out = subprocess.check_output(["swaymsg", "-t", "get_inputs"], stderr=subprocess.DEVNULL)
                inputs = json.loads(out)
                for inp in inputs:
                    if inp.get("type") == "keyboard" and "xkb_active_layout_name" in inp:
                        return inp["xkb_active_layout_name"]
            except Exception:
                pass
        elif self.caps.is_hyprland:
            try:
                out = subprocess.check_output(["hyprctl", "devices", "-j"], stderr=subprocess.DEVNULL)
                data = json.loads(out)
                for kb in data.get("keyboards", []):
                    if kb.get("main", False) and "active_keymap" in kb:
                        return kb["active_keymap"]
            except Exception:
                pass
        return "English (US)"

    def _load_tasks(self) -> List[Dict[str, Any]]:
        """Load tasks from JSON storage."""
        if not self.tasks_file.exists():
            return []
        try:
            with open(self.tasks_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception as e:
            log.warning(f"Error loading tasks from {self.tasks_file}: {e}")
            return []

    def _save_tasks(self):
        """Save tasks to JSON storage atomically."""
        try:
            self.tasks_file.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.tasks_file.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.tasks, f, indent=2, ensure_ascii=False)
            tmp.replace(self.tasks_file)
        except Exception as e:
            log.error(f"Error saving tasks to {self.tasks_file}: {e}")

    def _get_active_task(self) -> Optional[Dict[str, Any]]:
        pending = [t for t in self.tasks if not t.get("done", False)]
        return pending[0] if pending else None

    def _update_active_task_state(self):
        active = self._get_active_task()
        if active:
            pending_count = len([t for t in self.tasks if not t.get("done", False)])
            title = truncate_text(active.get("title", "Task"), 20)
            sub = f"({pending_count} pending)" if pending_count > 1 else ""
            self.active_task_state = IslandState(
                source="task",
                state="task",
                priority=Priority.TASK,
                icon="󰄱",
                title=title,
                subtitle=sub,
                css_class="task",
                tooltip=f"Active Focus Task: {active.get('title')}\nClick to mark done"
            )
        else:
            self.active_task_state = None

    # --------------------------------------------------------------------------
    # Output Protocol: Single JSON Object per line + Immediate Flush
    # --------------------------------------------------------------------------
    def get_current_state(self) -> IslandState:
        """Resolve highest priority active state with automatic expiration."""
        # 1. Prune expired temporary events
        self.transient_states = self.events.prune_expired()

        persistent = [
            self.active_recording_state,
            self.active_power_state,
            self.active_timer_state,
            self.active_task_state,
            self.active_media_state,
        ]

        # Base Fallback: Idle Clock & Date + Language
        now_dt = datetime.datetime.now()
        time_str = now_dt.strftime("%H:%M")
        date_str = now_dt.strftime("%a %d %b")

        lan_info = resolve_language_info(self.current_layout_name)
        idle_title = f"{time_str}  {date_str}"

        if self.config.idle_show_language and self.config.enable_language:
            if self.config.language_format == "origin":
                lan_str = lan_info["origin"]
            elif self.config.language_format == "full":
                lan_str = lan_info["full"]
            elif self.config.language_format == "short":
                lan_str = lan_info["short"]
            else:  # 'both'
                lan_str = f"{lan_info['origin']} ({lan_info['short']})"
            idle_title = f"{idle_title}  •  {lan_info['flag']} {lan_str}"

        if self.config.show_full:
            full_date = now_dt.strftime("%A, %d %B %Y")
            full_lan = f"{lan_info['origin']} ({lan_info['full']})"
            idle_title = f"{now_dt.strftime('%H:%M:%S')}  {full_date}  •  {lan_info['flag']} {full_lan}"

        tooltip = (
            f"{now_dt.strftime('%A, %B %d, %Y')}\n"
            f"Input Language: {lan_info['full']} [{lan_info['origin']}]\n"
            f"Mode: {self.config.mode} | Theme: {self.config.theme}\n"
            f"Click: Play/Pause | Right-Click: Quick Menu"
        )

        default_idle = IslandState(
            event_id="idle-clock",
            source="clock",
            state="idle",
            priority=Priority.IDLE,
            icon="󰸗",
            title=idle_title,
            css_class="idle",
            tooltip=tooltip
        )

        winner = self.events.arbitrate(persistent, default_idle)
        winner.system_cpu = getattr(self, "current_cpu", 0.0)
        winner.system_mem = getattr(self, "current_mem", 0.0)
        winner.dropped_files = getattr(self, "active_dropped_files", [])
        winner.share_targets = getattr(self, "active_share_targets", [])
        winner.running_windows = self.window_monitor.get_windows()
        return winner

    def render_and_broadcast(self):
        """Formats single-line JSON, flushes to stdout, and broadcasts to IPC stream listeners."""
        state = self.get_current_state()
        stream_payload = state.to_waybar_payload(self.config)
        stream_line = json.dumps(stream_payload, ensure_ascii=False)

        # For Waybar stdout: if frontend/mode is 'quickshell' or 'hybrid', hide the Waybar pill
        if self.config.frontend in ("quickshell", "hybrid") or self.config.mode in ("quickshell", "hybrid"):
            waybar_payload = {"text": "", "alt": "hidden", "tooltip": "", "class": "island hidden"}
            waybar_line = json.dumps(waybar_payload, ensure_ascii=False)
        else:
            waybar_line = stream_line

        if waybar_line != self.current_json_line:
            self.current_json_line = waybar_line
            try:
                sys.stdout.write(waybar_line + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                log.warning("BrokenPipeError on stdout. Waybar may have reloaded.")
            except Exception as e:
                log.error(f"Error writing to stdout: {e}")

        # Send rich payload to IPC stream readers (e.g. Quickshell)
        self.ipc_server.broadcast_stream(stream_line)

    def push_transient_event(self, state: IslandState):
        """Pushes an auto-expiring event and restores higher/persistent states when expired."""
        self.events.push_transient(state)
        self.transient_states = self.events.transient_states
        self.render_and_broadcast()

    def dismiss_transient(self, state_name: Optional[str] = None):
        """Dismiss transient event immediately and restore prior state."""
        self.events.dismiss(state_name)
        self.transient_states = self.events.transient_states
        self.render_and_broadcast()

    # --------------------------------------------------------------------------
    # Subsystem: Input Language & Keyboard Layout Monitor
    # --------------------------------------------------------------------------
    async def run_language_monitor(self):
        """Monitors keyboard layout switches in real-time across Sway and Hyprland."""
        if not self.config.enable_language:
            return

        if self.caps.is_sway:
            cmd = ["swaymsg", "-t", "subscribe", "-m", '["input"]']
            while True:
                try:
                    proc = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.DEVNULL
                    )
                    while True:
                        line = await proc.stdout.readline()
                        if not line:
                            break
                        decoded = line.decode("utf-8", errors="replace").strip()
                        if not decoded:
                            continue
                        try:
                            data = json.loads(decoded)
                            input_obj = data.get("input", {})
                            if input_obj.get("type") == "keyboard" and "xkb_active_layout_name" in input_obj:
                                layout = input_obj["xkb_active_layout_name"]
                                if layout != self.current_layout_name:
                                    self._on_layout_changed(layout)
                        except Exception:
                            pass
                    await proc.wait()
                except Exception as e:
                    log.warning(f"Sway input subscribe restart: {e}")
                await asyncio.sleep(2.0)

        elif self.caps.is_hyprland:
            xdg_rt = os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")
            his = os.environ.get("HYPRLAND_INSTANCE_SIGNATURE", "")
            sock_path = Path(xdg_rt) / "hypr" / his / ".socket2.sock"

            if sock_path.exists():
                while True:
                    try:
                        reader, writer = await asyncio.open_unix_connection(str(sock_path))
                        while True:
                            line = await reader.readline()
                            if not line:
                                break
                            decoded = line.decode("utf-8", errors="replace").strip()
                            if decoded.startswith("activelayout>>"):
                                parts = decoded[len("activelayout>>"):].split(",")
                                if len(parts) >= 2:
                                    layout = parts[1].strip()
                                    if layout != self.current_layout_name:
                                        self._on_layout_changed(layout)
                    except Exception as e:
                        log.warning(f"Hyprland socket2 restart: {e}")
                    await asyncio.sleep(2.0)

    def _on_layout_changed(self, layout_name: str):
        self.current_layout_name = layout_name
        info = resolve_language_info(layout_name)

        if self.config.language_format == "origin":
            title = info["origin"]
            subtitle = ""
        elif self.config.language_format == "full":
            title = info["full"]
            subtitle = ""
        elif self.config.language_format == "short":
            title = info["short"]
            subtitle = info["full"]
        else:  # 'both'
            title = info["origin"]
            subtitle = f"({info['short']} • {info['full']})"

        ev = IslandState(
            source="language",
            state="language",
            priority=Priority.LANGUAGE,
            icon=info["flag"],
            title=title,
            subtitle=subtitle,
            css_class="language",
            tooltip=f"Layout: {info['full']} [{info['origin']}]\nShort: {info['short']}",
            duration=self.config.language_timeout_s
        )
        self.push_transient_event(ev)

    # --------------------------------------------------------------------------
    # Subsystem: Timer & Stopwatch Clock Loop
    # --------------------------------------------------------------------------
    async def run_timer_clock(self):
        """1 Hz clock loop for countdown timer, stopwatch, and auto-render."""
        while True:
            # Sync TimerManager state if manipulated directly or via IPC
            tick_state = self.timer_mgr.tick()
            if tick_state:
                if tick_state.duration is not None:
                    # Completion alert
                    self.active_timer_state = None
                    self.push_transient_event(tick_state)
                else:
                    self.active_timer_state = tick_state
            elif self.timer_end_timestamp is not None:
                # Direct attribute compatibility
                rem = max(0.0, self.timer_end_timestamp - time.time())
                if rem <= 0.0:
                    self.timer_end_timestamp = None
                    self.active_timer_state = None
                    self.push_transient_event(IslandState(
                        source="timer",
                        state="timer",
                        priority=Priority.URGENT_NOTIF,
                        icon="󰄬",
                        title="Time Up!",
                        subtitle=self.timer_label or "Timer",
                        css_class="timer complete",
                        duration=5.0
                    ))
                else:
                    mins = int(rem) // 60
                    secs = int(rem) % 60
                    self.active_timer_state = IslandState(
                        source="timer",
                        state="timer",
                        priority=Priority.TIMER,
                        icon="󰔛",
                        title=f"{mins:02d}:{secs:02d}",
                        subtitle=f"({self.timer_label})" if self.timer_label else "",
                        css_class="timer",
                        tooltip=f"Timer: {mins:02d}:{secs:02d} remaining"
                    )

            if tick_state or self.timer_end_timestamp is not None:
                self.render_and_broadcast()
                await asyncio.sleep(1.0)
            else:
                self.render_and_broadcast()
                idle_interval = getattr(self.config, "idle_clock_interval_s", 15.0)
                await asyncio.sleep(idle_interval)

    # --------------------------------------------------------------------------
    # Subsystem: Delegation Methods
    # --------------------------------------------------------------------------
    async def run_media_monitor(self):
        await self.media_backend.run_monitor()

    async def run_bluetooth_monitor(self):
        await self.bluetooth_backend.run_monitor()

    async def run_volume_monitor(self):
        await self.audio_backend.run_monitor()

    async def run_brightness_monitor(self):
        await self.brightness_backend.run_monitor()

    async def run_notification_monitor(self):
        await self.notification_backend.run_monitor()

    async def run_battery_monitor(self):
        await self.battery_backend.run_monitor()

    async def run_recording_monitor(self):
        await self.recording_backend.run_monitor()

    async def run_network_monitor(self):
        await self.network_backend.run_monitor()

    async def run_clipboard_monitor(self):
        await self.clipboard_backend.run_monitor()

    # --------------------------------------------------------------------------
    # Unified Action Dispatcher (IPC & CLI)
    # --------------------------------------------------------------------------
    async def dispatch_action(self, action: str, args: Dict[str, Any], writer: Optional[asyncio.StreamWriter]) -> Optional[Dict[str, Any]]:
        """Dispatch validated actions strictly without shell=True."""
        params = args.get("params", [])

        # 1. Frontend Management
        if action in ("frontend_get", "frontend"):
            return {"version": 1, "status": "ok", "frontend": self.config.frontend}

        elif action == "frontend_set":
            fe = params[0] if params else args.get("frontend", "")
            fe = str(fe).lower().strip()
            if fe in ("waybar", "quickshell", "both", "hybrid"):
                self.config.frontend = fe
                self.config.save()
                self.render_and_broadcast()
                return {"version": 1, "status": "ok", "message": f"Set frontend to {fe}", "frontend": fe}
            return {
                "protocol_version": PROTOCOL_VERSION,
                "version": 1,
                "status": "error",
                "message": "Invalid frontend. Choose from 'waybar', 'quickshell', 'both', 'hybrid'"
            }

        # 2. Mode Management
        elif action in ("mode_get", "mode"):
            if not params:
                return {
                    "protocol_version": PROTOCOL_VERSION,
                    "version": 1,
                    "status": "ok",
                    "mode": self.config.mode,
                    "frontend": self.config.frontend,
                    "modes_available": MODES
                }
            target_mode = params[0].lower().strip()
            if target_mode in MODES:
                self.config.mode = target_mode
                if target_mode == "waybar-lite":
                    self.config.frontend = "waybar"
                    self.config.theme = "minimal"
                elif target_mode == "waybar-enhanced":
                    self.config.frontend = "waybar"
                elif target_mode == "quickshell":
                    self.config.frontend = "quickshell"
                elif target_mode == "hybrid":
                    self.config.frontend = "hybrid"
                self.config.save()
                self.render_and_broadcast()
                return {
                    "protocol_version": PROTOCOL_VERSION,
                    "version": 1,
                    "status": "ok",
                    "message": f"Switched mode to: {target_mode}",
                    "mode": target_mode,
                    "frontend": self.config.frontend
                }
            return {
                "protocol_version": PROTOCOL_VERSION,
                "version": 1,
                "status": "error",
                "message": f"Invalid mode '{target_mode}'. Choose from: {', '.join(MODES)}"
            }

        elif action == "mode_set":
            target_mode = params[0] if params else args.get("mode", "")
            target_mode = str(target_mode).lower().strip()
            if target_mode in MODES:
                self.config.mode = target_mode
                if target_mode == "waybar-lite":
                    self.config.frontend = "waybar"
                    self.config.theme = "minimal"
                elif target_mode == "waybar-enhanced":
                    self.config.frontend = "waybar"
                elif target_mode == "quickshell":
                    self.config.frontend = "quickshell"
                elif target_mode == "hybrid":
                    self.config.frontend = "hybrid"
                self.config.save()
                self.render_and_broadcast()
                return {
                    "protocol_version": PROTOCOL_VERSION,
                    "version": 1,
                    "status": "ok",
                    "message": f"Switched mode to: {target_mode}",
                    "mode": target_mode,
                    "frontend": self.config.frontend
                }
            return {
                "protocol_version": PROTOCOL_VERSION,
                "version": 1,
                "status": "error",
                "message": f"Invalid mode '{target_mode}'. Choose from: {', '.join(MODES)}"
            }

        # 3. Bluetooth Actions
        elif action.startswith("bluetooth"):
            sub = params[0].lower() if params else action.replace("bluetooth_", "")
            if sub in ("status", "bluetooth"):
                status_res = await self.bluetooth_backend.fetch_status()
                return {"protocol_version": PROTOCOL_VERSION, "version": 1, "status": "ok", "data": status_res}
            elif sub == "scan":
                dur = int(params[1]) if len(params) > 1 else 10
                return await self.bluetooth_backend.scan(dur)
            elif sub == "connect":
                target = params[1] if len(params) > 1 else args.get("device", "")
                return await self.bluetooth_backend.connect(target)
            elif sub == "disconnect":
                target = params[1] if len(params) > 1 else args.get("device", "")
                return await self.bluetooth_backend.disconnect(target)
            elif sub in ("devices", "list"):
                status_res = await self.bluetooth_backend.fetch_status()
                return {
                    "protocol_version": PROTOCOL_VERSION,
                    "version": 1,
                    "status": "ok",
                    "paired": status_res.get("paired_devices", []),
                    "connected": status_res.get("connected_devices", [])
                }

        # 4. Show-Full Presentation Mode
        elif action in ("full_toggle", "toggle_full"):
            self.config.show_full = not self.config.show_full
            self.config.save()
            self.render_and_broadcast()
            state_str = "enabled" if self.config.show_full else "disabled"
            return {
                "protocol_version": PROTOCOL_VERSION,
                "version": 1,
                "status": "ok",
                "message": f"Show-full mode {state_str}",
                "show_full": self.config.show_full
            }

        elif action in ("full_set", "set_full", "full"):
            sub = params[0].lower() if params else str(args.get("enabled", "")).lower()
            if sub in ("toggle", "t"):
                self.config.show_full = not self.config.show_full
            else:
                self.config.show_full = sub in ("on", "true", "1", "enable")
            self.config.save()
            self.render_and_broadcast()
            state_str = "enabled" if self.config.show_full else "disabled"
            return {
                "protocol_version": PROTOCOL_VERSION,
                "version": 1,
                "status": "ok",
                "message": f"Show-full mode {state_str}",
                "show_full": self.config.show_full
            }

        # 5. Language Actions
        elif action in ("layout_get", "lan_get", "layout"):
            if params and params[0].lower() in ("next", "switch"):
                action = "layout_next"
            elif params and params[0].lower() in ("show", "pop"):
                action = "layout_show"
            elif params and params[0].lower() in ("mode", "format"):
                args["format"] = params[1] if len(params) > 1 else "both"
                action = "layout_set"
            else:
                info = resolve_language_info(self.current_layout_name)
                return {
                    "protocol_version": PROTOCOL_VERSION,
                    "version": 1,
                    "status": "ok",
                    "layout": self.current_layout_name,
                    "info": info,
                    "format": self.config.language_format
                }

        if action in ("layout_next", "lan_next"):
            if self.caps.is_sway:
                try:
                    proc = await asyncio.create_subprocess_exec("swaymsg", "input", "*", "xkb_switch_layout", "next")
                    await proc.wait()
                    await asyncio.sleep(0.08)
                    self.current_layout_name = self._detect_current_layout()
                except Exception as e:
                    log.warning(f"Error switching layout via swaymsg: {e}")
            elif self.caps.is_hyprland:
                try:
                    proc = await asyncio.create_subprocess_exec("hyprctl", "switchxkblayout", "all", "next")
                    await proc.wait()
                    await asyncio.sleep(0.08)
                    self.current_layout_name = self._detect_current_layout()
                except Exception as e:
                    log.warning(f"Error switching layout via hyprctl: {e}")
            self._on_layout_changed(self.current_layout_name)
            info = resolve_language_info(self.current_layout_name)
            return {
                "protocol_version": PROTOCOL_VERSION,
                "version": 1,
                "status": "ok",
                "message": f"Switched layout: {info['origin']} ({info['full']})",
                "layout": self.current_layout_name,
                "info": info
            }

        elif action in ("layout_show", "lan_show"):
            self._on_layout_changed(self.current_layout_name)
            info = resolve_language_info(self.current_layout_name)
            return {
                "protocol_version": PROTOCOL_VERSION,
                "version": 1,
                "status": "ok",
                "message": f"Active layout: {info['origin']} ({info['full']})",
                "layout": self.current_layout_name,
                "info": info
            }

        elif action in ("layout_set", "lan_set"):
            fmt = params[0].lower() if params else args.get("format", "both")
            if fmt in ("both", "origin", "full", "short"):
                self.config.language_format = fmt
                self.config.save()
                self._on_layout_changed(self.current_layout_name)
                return {
                    "protocol_version": PROTOCOL_VERSION,
                    "version": 1,
                    "status": "ok",
                    "message": f"Set language format to {fmt}",
                    "format": fmt
                }
            return {
                "protocol_version": PROTOCOL_VERSION,
                "version": 1,
                "status": "error",
                "message": "Invalid format. Choose: both, origin, full, short"
            }

        # 6. Doctor / Diagnostics Audit
        elif action == "doctor":
            bt_status = await self.bluetooth_backend.fetch_status()
            return {
                "protocol_version": PROTOCOL_VERSION,
                "version": 1,
                "status": "ok",
                "doctor": {
                    "daemon_online": True,
                    "socket": str(SOCKET_PATH),
                    "config_path": str(CONFIG_FILE),
                    "mode": self.config.mode,
                    "frontend": self.config.frontend,
                    "theme": self.config.theme,
                    "show_full": self.config.show_full,
                    "compositor": self.caps.get_detected_compositor(),
                    "current_layout": self.current_layout_name,
                    "layout_info": resolve_language_info(self.current_layout_name),
                    "bluetooth": bt_status,
                    "dependencies": {
                        "playerctl": self.caps.has_playerctl,
                        "pactl": self.caps.has_pactl,
                        "wpctl": self.caps.has_wpctl,
                        "brightnessctl": self.caps.has_brightnessctl,
                        "upower": self.caps.has_upower,
                        "nmcli": self.caps.has_nmcli,
                        "wl-paste": self.caps.has_wl_paste,
                        "swaymsg": self.caps.is_sway,
                        "bluetoothctl": shutil.which("bluetoothctl") is not None,
                        "quickshell": shutil.which("quickshell") is not None
                    }
                }
            }

        # 7. Diagnostic Status Command
        elif action == "status":
            state = self.get_current_state()
            bt_status = await self.bluetooth_backend.fetch_status()
            return {
                "protocol_version": PROTOCOL_VERSION,
                "version": 1,
                "status": "ok",
                "data": {
                    "daemon_active": True,
                    "protocol_version": PROTOCOL_VERSION,
                    "socket_path": str(SOCKET_PATH),
                    "active_state": state.state,
                    "active_title": state.title,
                    "active_priority": int(state.priority),
                    "mode": self.config.mode,
                    "frontend": self.config.frontend,
                    "theme": self.config.theme,
                    "presentation_mode": self.config.presentation_mode,
                    "reduced_motion": self.config.reduced_motion,
                    "show_full": self.config.show_full,
                    "current_layout": self.current_layout_name,
                    "layout_info": resolve_language_info(self.current_layout_name),
                    "compositor": self.caps.get_detected_compositor(),
                    "bluetooth": bt_status,
                    "enabled_integrations": {
                        "media": self.config.enable_media and self.caps.has_playerctl,
                        "bluetooth": True,
                        "volume": self.config.enable_volume and (self.caps.has_pactl or self.caps.has_wpctl),
                        "brightness": self.config.enable_brightness and self.caps.has_brightnessctl,
                        "notifications": self.config.enable_notifications and self.caps.has_dbus_monitor,
                        "battery": self.config.enable_battery and self.caps.has_upower,
                        "recording": self.config.enable_recording,
                        "network": self.config.enable_network and self.caps.has_nmcli,
                        "clipboard": self.config.enable_clipboard and self.caps.has_wl_paste,
                        "timer": self.config.enable_timer,
                        "language": self.config.enable_language,
                    }
                }
            }

        # 8. Custom Event Injection
        elif action == "event":
            title = truncate_text(str(args.get("title", "Custom Event")), 32)
            message = truncate_text(str(args.get("message", "")), 48)
            source = str(args.get("source", "script"))[:16]
            st_name = str(args.get("state", "system"))
            if not is_valid_state(st_name):
                st_name = "system"

            dur = float(args.get("duration", args.get("duration_ms", 3000)))
            if dur > 100:
                dur = dur / 1000.0
            dur = max(0.5, min(30.0, dur))

            pri = int(args.get("priority", Priority.CONNECTIVITY))
            pri = max(10, min(95, pri))

            custom_ev = IslandState(
                source=source,
                state=st_name,
                priority=pri,
                icon=args.get("icon", "󰋼"),
                title=title,
                subtitle=message,
                css_class=st_name,
                tooltip=f"Source: {source}\n{title}\n{message}",
                duration=dur
            )
            self.push_transient_event(custom_ev)
            return {"version": 1, "status": "ok", "message": f"Posted event: {title}"}

        # 9. Media Controls
        elif action in ("media_toggle", "media_play_pause", "click"):
            cur_s = self.get_current_state()
            if cur_s.state == "notification":
                self.dismiss_transient("notification")
                return {"version": 1, "status": "ok", "message": "Dismissed active notification"}

            if cur_s.state == "task":
                return await self.dispatch_action("task_done", {}, None)

            await self.media_backend.toggle()
            return {"version": 1, "status": "ok", "message": "Toggled media playback"}

        elif action == "media_next":
            await self.media_backend.next()
            return {"version": 1, "status": "ok", "message": "Skipped track"}

        elif action == "media_prev":
            await self.media_backend.prev()
            return {"version": 1, "status": "ok", "message": "Previous track"}

        # 10. Volume Controls
        elif action == "volume_up":
            await self.audio_backend.volume_up()
            return {"version": 1, "status": "ok", "message": "Volume +2%"}

        elif action == "volume_down":
            await self.audio_backend.volume_down()
            return {"version": 1, "status": "ok", "message": "Volume -2%"}

        elif action in ("volume_mute", "mute"):
            await self.audio_backend.volume_mute()
            return {"version": 1, "status": "ok", "message": "Toggled volume mute"}

        # 11. Brightness Controls
        elif action == "brightness_up":
            await self.brightness_backend.brightness_up()
            return {"version": 1, "status": "ok", "message": "Brightness +5%"}

        elif action == "brightness_down":
            await self.brightness_backend.brightness_down()
            return {"version": 1, "status": "ok", "message": "Brightness -5%"}

        # 12. Timer Controls
        elif action in ("timer", "timer_start"):
            dur_str = params[0] if params else args.get("duration", "")
            label = " ".join(params[1:]) if len(params) > 1 else args.get("label", "Timer")
            seconds = parse_duration(dur_str)
            ok, msg = self.timer_mgr.start_timer(seconds, label)
            if ok:
                self.active_timer_state = self.timer_mgr.active_state
                self.timer_end_timestamp = self.timer_mgr.timer_end_timestamp
                self.timer_label = self.timer_mgr.timer_label
                self.timer_paused = False
                self.render_and_broadcast()
                return {"version": 1, "status": "ok", "message": msg}
            return {"version": 1, "status": "error", "message": msg}

        elif action in ("timer_pause", "pomodoro_pause"):
            ok, msg = self.timer_mgr.pause()
            if ok:
                self.timer_paused = True
                self.render_and_broadcast()
                return {"version": 1, "status": "ok", "message": msg}
            return {"version": 1, "status": "error", "message": msg}

        elif action in ("timer_resume", "pomodoro_resume"):
            ok, msg = self.timer_mgr.resume()
            if ok:
                self.timer_paused = False
                self.render_and_broadcast()
                return {"version": 1, "status": "ok", "message": msg}
            return {"version": 1, "status": "error", "message": msg}

        elif action in ("pomodoro", "pomodoro_start"):
            mins = int(params[0]) if params and params[0].isdigit() else 25
            ok, msg = self.timer_mgr.start_pomodoro(mins)
            self.active_timer_state = self.timer_mgr.active_state
            self.timer_end_timestamp = self.timer_mgr.timer_end_timestamp
            self.timer_label = "Focus"
            self.timer_paused = False
            self.render_and_broadcast()
            return {"version": 1, "status": "ok", "message": msg}

        elif action == "stopwatch":
            ok, msg = self.timer_mgr.start_stopwatch()
            self.active_timer_state = self.timer_mgr.active_state
            self.stopwatch_start_timestamp = self.timer_mgr.stopwatch_start_timestamp
            self.render_and_broadcast()
            return {"version": 1, "status": "ok", "message": msg}

        elif action in ("stop", "timer_stop", "pomodoro_stop"):
            self.timer_mgr.stop()
            self.timer_end_timestamp = None
            self.timer_paused = False
            self.stopwatch_start_timestamp = None
            self.active_timer_state = None
            self.render_and_broadcast()
            return {"version": 1, "status": "ok", "message": "Stopped active timer/stopwatch"}

        # 13. Task & To-Do Management
        elif action in ("task_add", "task"):
            title = " ".join(params) if params else args.get("title", args.get("text", ""))
            if not title:
                return {"version": 1, "status": "error", "message": "Task title is required"}
            new_task = {
                "id": str(uuid.uuid4())[:8],
                "title": title.strip(),
                "done": False,
                "created_at": time.time()
            }
            self.tasks.append(new_task)
            self._save_tasks()
            self._update_active_task_state()
            self.render_and_broadcast()
            return {"version": 1, "status": "ok", "message": f"Added task: {title}", "task": new_task}

        elif action == "task_done":
            active = self._get_active_task()
            if not active:
                return {"version": 1, "status": "error", "message": "No active task to complete"}
            active["done"] = True
            active["completed_at"] = time.time()
            self._save_tasks()
            done_ev = IslandState(
                source="task",
                state="task",
                priority=Priority.CONNECTIVITY,
                icon="󰄬",
                title="Done!",
                subtitle=truncate_text(active.get("title", ""), 18),
                css_class="task done",
                tooltip=f"Completed: {active.get('title')}",
                duration=3.0
            )
            self.push_transient_event(done_ev)
            self._update_active_task_state()
            self.render_and_broadcast()
            return {"version": 1, "status": "ok", "message": f"Completed task: {active.get('title')}"}

        elif action == "task_next":
            active = self._get_active_task()
            if active and len([t for t in self.tasks if not t.get("done", False)]) > 1:
                self.tasks.remove(active)
                self.tasks.append(active)
                self._save_tasks()
                self._update_active_task_state()
                self.render_and_broadcast()
                new_act = self._get_active_task()
                return {"version": 1, "status": "ok", "message": f"Next task: {new_act.get('title')}"}
            return {"version": 1, "status": "ok", "message": "No other pending tasks"}

        elif action == "task_list":
            return {"version": 1, "status": "ok", "tasks": self.tasks}

        elif action == "task_clear":
            self.tasks = [t for t in self.tasks if not t.get("done", False)]
            self._save_tasks()
            self._update_active_task_state()
            self.render_and_broadcast()
            return {"version": 1, "status": "ok", "message": "Cleared completed tasks"}

        # 14. Dismiss & DND
        elif action == "dismiss":
            self.dismiss_transient()
            return {"version": 1, "status": "ok", "message": "Dismissed transient banner"}

        elif action == "dnd_toggle":
            if self.caps.has_makoctl:
                await asyncio.create_subprocess_exec("makoctl", "mode", "-t", "dnd")
                return {"version": 1, "status": "ok", "message": "Toggled Mako DND"}
            elif self.caps.has_swaync_client:
                await asyncio.create_subprocess_exec("swaync-client", "-t", "-d")
                return {"version": 1, "status": "ok", "message": "Toggled SwayNC DND"}
            return {"version": 1, "status": "error", "message": "Neither makoctl nor swaync-client available"}

        # 15. Theme & Settings Controls
        elif action == "theme_list":
            return {"version": 1, "status": "ok", "themes": THEME_PRESETS, "active": self.config.theme}

        elif action == "theme_get":
            return {"version": 1, "status": "ok", "active": self.config.theme}

        elif action == "theme_set":
            raw_theme = params[0] if params else args.get("theme", "")
            theme_name = normalize_theme(raw_theme)
            if theme_name and theme_name in THEME_PRESETS:
                self.config.theme = theme_name
                self.config.save()
                self.render_and_broadcast()
                return {"version": 1, "status": "ok", "message": f"Set theme to {theme_name}", "theme": theme_name}
            return {
                "version": 1,
                "status": "error",
                "message": f"Invalid theme: {raw_theme}. Choose from {THEME_PRESETS}"
            }

        elif action in ("dock", "dock_toggle"):
            sub = params[0].lower() if params else args.get("state", "toggle")
            if sub in ("on", "show", "enable", "true"):
                self.config.dock_enabled = True
            elif sub in ("off", "hide", "disable", "false"):
                self.config.dock_enabled = False
            elif sub in ("status", "get"):
                pass
            else:
                self.config.dock_enabled = not self.config.dock_enabled
            self.config.save()
            self.render_and_broadcast()
            return {
                "version": 1,
                "status": "ok",
                "message": f"Dock enabled: {self.config.dock_enabled}",
                "dock_enabled": self.config.dock_enabled,
                "dock_position": self.config.dock_position
            }

        elif action in ("system", "system_metrics"):
            cpu, mem = self.system_metrics_monitor.read_metrics_sync()
            return {
                "version": 1,
                "status": "ok",
                "cpu_percent": cpu,
                "memory_percent": mem,
                "compositor": self.caps.get_detected_compositor(),
            }

        elif action in ("reduced_motion_set", "motion"):
            enabled = args.get("enabled", True)
            if params:
                enabled = params[0].lower() in ("on", "true", "1", "reduced")
            self.config.reduced_motion = bool(enabled)
            self.config.save()
            self.render_and_broadcast()
            return {"version": 1, "status": "ok", "message": f"Set reduced_motion to {self.config.reduced_motion}"}

        elif action == "settings":
            return {
                "version": 1,
                "status": "ok",
                "settings": {
                    "mode": self.config.mode,
                    "frontend": self.config.frontend,
                    "theme": self.config.theme,
                    "reduced_motion": self.config.reduced_motion,
                    "show_full": self.config.show_full,
                    "presentation_mode": self.config.presentation_mode,
                    "dock_enabled": getattr(self.config, "dock_enabled", False),
                    "dock_position": getattr(self.config, "dock_position", "bottom"),
                    "dock_magnification": getattr(self.config, "dock_magnification", True),
                    "network_ssid_privacy": self.config.network_ssid_privacy,
                    "clipboard_privacy": self.config.clipboard_privacy,
                    "enable_share": getattr(self.config, "enable_share", True),
                    "enable_window_manager": getattr(self.config, "enable_window_manager", True),
                }
            }

        # 16. Smart Share & Drag-and-Drop
        elif action == "share_inspect":
            raw_urls = args.get("urls", params)
            if isinstance(raw_urls, str):
                raw_urls = [raw_urls]
            files = self.share_manager.parse_and_validate_urls(raw_urls)
            if not files:
                return {"version": 1, "status": "error", "message": "No valid local files found."}

            targets = self.share_manager.discover_targets(files)
            self.active_dropped_files = files
            self.active_share_targets = targets

            file_names = ", ".join(f["name"] for f in files[:2])
            if len(files) > 2:
                file_names += f" +{len(files) - 2} more"

            share_state = IslandState(
                event_id="smart-share",
                source="share",
                state="share_picker",
                priority=Priority.SHARE,
                icon="󰒍",
                title=f"Share {len(files)} File(s)",
                subtitle=file_names,
                css_class="share_picker",
                duration=getattr(self.config, "share_timeout_s", 60.0),
                dropped_files=files,
                share_targets=targets,
                tooltip=f"Smart Share: {len(files)} file(s) selected"
            )
            self.push_transient_event(share_state)
            self.render_and_broadcast()
            return {
                "version": 1,
                "status": "ok",
                "files": files,
                "targets": targets,
            }

        elif action == "share_execute":
            target_id = str(args.get("target_id", params[0] if params else ""))
            raw_files = args.get("files", [f["path"] for f in self.active_dropped_files])
            res = self.share_manager.execute_share(target_id, raw_files)

            if res.get("status") == "ok":
                launch_state = IslandState(
                    event_id="share-launching",
                    source="share",
                    state="share_launching",
                    priority=Priority.SHARE,
                    icon="󰁯",
                    title="Launching Share...",
                    subtitle=res.get("message", ""),
                    duration=2.5
                )
                self.push_transient_event(launch_state)
                self.active_dropped_files = []
                self.active_share_targets = []
            else:
                err_state = IslandState(
                    event_id="share-error",
                    source="share",
                    state="share_error",
                    priority=Priority.SHARE,
                    icon="󰅚",
                    title="Share Failed",
                    subtitle=res.get("message", "Could not launch target"),
                    duration=3.0
                )
                self.push_transient_event(err_state)

            self.render_and_broadcast()
            return res

        elif action == "share_cancel":
            self.active_dropped_files = []
            self.active_share_targets = []
            self.dismiss_transient("smart-share")
            self.dismiss_transient("share_picker")
            self.render_and_broadcast()
            return {"version": 1, "status": "ok", "message": "Smart Share cancelled"}

        # 17. Sway Window Management
        elif action == "window_minimize":
            con_id = int(args.get("con_id", params[0] if params else 0))
            res = self.window_monitor.minimize_window(con_id)
            if res.get("status") == "ok":
                feedback = IslandState(
                    event_id="window-min",
                    source="window",
                    state="minimized",
                    priority=Priority.WINDOW_MINIMIZE,
                    icon="󰖰",
                    title="Window Minimized",
                    subtitle="Moved to scratchpad",
                    duration=1.8
                )
                self.push_transient_event(feedback)
                self.render_and_broadcast()
            return res

        elif action == "window_restore":
            con_id = int(args.get("con_id", params[0] if params else 0))
            res = self.window_monitor.restore_window(con_id)
            if res.get("status") == "ok":
                feedback = IslandState(
                    event_id="window-res",
                    source="window",
                    state="restoring",
                    priority=Priority.WINDOW_MINIMIZE,
                    icon="󰖯",
                    title="Window Restored",
                    subtitle="Restored from scratchpad",
                    duration=1.8
                )
                self.push_transient_event(feedback)
                self.render_and_broadcast()
            return res

        elif action == "window_toggle":
            con_id = int(args.get("con_id", params[0] if params else 0))
            res = self.window_monitor.toggle_window(con_id)
            self.render_and_broadcast()
            return res

        elif action == "window_toggle_app":
            keyword = str(args.get("app_keyword", params[0] if params else ""))
            fallback = str(args.get("fallback_binary", params[1] if len(params) > 1 else keyword))
            res = self.window_monitor.toggle_app_by_name(keyword, fallback)
            self.render_and_broadcast()
            return res

        elif action in ("windows_list", "windows"):
            return {"version": 1, "status": "ok", "windows": self.window_monitor.get_windows()}

        elif action == "profile":
            sub = args.get("subcommand") or (params[0] if params else "get")
            if sub == "set":
                target = args.get("name") or (params[1] if len(params) > 1 else "balanced")
                self.config.apply_profile(target)
                self.config.save()
                self.render_and_broadcast()
                return {
                    "version": 1,
                    "status": "ok",
                    "profile": target,
                    "message": f"Profile switched to '{target}'"
                }
            return {
                "version": 1,
                "status": "ok",
                "profile": self.config.performance_profile,
                "idle_clock_interval_s": self.config.idle_clock_interval_s,
                "metrics_interval_s": self.config.metrics_interval_s,
                "reduced_motion": self.config.reduced_motion,
                "minimize_duration_ms": self.config.minimize_duration_ms,
            }

        return {"version": 1, "status": "error", "message": f"Unknown action: {action}"}

    def parse_duration(self, s: str) -> int:
        return parse_duration(s)

    async def run_system_metrics_monitor(self):
        if not getattr(self.config, "enable_system_metrics", True):
            return
        await self.system_metrics_monitor.run_monitor(interval_s=2.5)

    # --------------------------------------------------------------------------
    # Main Daemon Lifecycle
    # --------------------------------------------------------------------------
    async def start(self):
        await self.ipc_server.start()
        self.render_and_broadcast()

        await asyncio.gather(
            self.run_timer_clock(),
            self.run_media_monitor(),
            self.run_bluetooth_monitor(),
            self.run_volume_monitor(),
            self.run_brightness_monitor(),
            self.run_notification_monitor(),
            self.run_battery_monitor(),
            self.run_recording_monitor(),
            self.run_network_monitor(),
            self.run_clipboard_monitor(),
            self.run_language_monitor(),
            self.run_system_metrics_monitor()
        )


# ==============================================================================
# Single-Instance Enforcement
# ==============================================================================
def stream_from_existing_daemon():
    """Proxy stdout stream from the already-running daemon socket to Waybar."""
    if not SOCKET_PATH.exists():
        sys.exit(0)
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.connect(str(SOCKET_PATH))
            sock.sendall(b"stream\n")
            buffer = ""
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                buffer += chunk.decode("utf-8", errors="replace")
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    if line.strip():
                        # Filter for Waybar stdout: if frontend/mode is 'quickshell' or 'hybrid', hide the Waybar pill
                        try:
                            payload = json.loads(line)
                            fe = payload.get("frontend", "")
                            md = payload.get("mode", "")
                            if fe in ("quickshell", "hybrid") or md in ("quickshell", "hybrid"):
                                line = json.dumps({"text": "", "alt": "hidden", "tooltip": "", "class": "island hidden"}, ensure_ascii=False)
                        except Exception:
                            pass
                        sys.stdout.write(line + "\n")
                        sys.stdout.flush()
    except Exception:
        sys.exit(0)


def acquire_single_instance_lock():
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    lock_file = open(LOCK_PATH, "w")
    try:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        lock_file.write(f"{os.getpid()}\n")
        lock_file.flush()
        return lock_file
    except (BlockingIOError, IOError):
        log.info(f"Existing daemon instance detected at {LOCK_PATH}. Streaming stdout...")
        stream_from_existing_daemon()
        sys.exit(0)


def main():
    lock_file = acquire_single_instance_lock()
    daemon = DynamicIslandDaemon()

    def handle_signal():
        log.info("Received termination signal. Exiting cleanly.")
        if SOCKET_PATH.exists():
            try:
                SOCKET_PATH.unlink()
            except Exception:
                pass
        try:
            lock_file.close()
            LOCK_PATH.unlink(missing_ok=True)
        except Exception:
            pass
        sys.exit(0)

    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: handle_signal())

    try:
        asyncio.run(daemon.start())
    except KeyboardInterrupt:
        handle_signal()


if __name__ == "__main__":
    main()
