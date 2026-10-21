"""
Ratana Dynamic Island Core Package
==================================
Shared business logic, state machines, priority arbitration, backends, and IPC.
"""

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

__all__ = [
    "Priority",
    "VALID_STATES",
    "is_valid_state",
    "IslandState",
    "build_progress_bar",
    "truncate_text",
    "LANGUAGE_MAP",
    "resolve_language_info",
    "resolve_app_icon",
    "BLOCKS_FILLED",
    "BLOCKS_EMPTY",
    "IslandConfig",
    "BackendCapabilities",
    "RUNTIME_DIR",
    "SOCKET_PATH",
    "LOCK_PATH",
    "CONFIG_DIR",
    "CONFIG_FILE",
    "PROTOCOL_VERSION",
    "MODES",
    "THEME_PRESETS",
    "normalize_theme",
    "EventManager",
    "TimerManager",
    "parse_duration",
    "MediaBackend",
    "BluetoothBackend",
    "AudioBackend",
    "BrightnessBackend",
    "BatteryBackend",
    "RecordingBackend",
    "NetworkBackend",
    "ClipboardBackend",
    "NotificationBackend",
    "SystemMetricsMonitor",
    "ShareManager",
    "SwayWindowMonitor",
    "IpcServer",
]
