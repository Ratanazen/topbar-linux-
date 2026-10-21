"""
Ratana Dynamic Island — Priority Manager
========================================
Defines the strict hierarchical priority matrix and valid visual states
conforming to Phase Five of the Master Build Prompt.
"""

from enum import IntEnum
from typing import Set


class Priority(IntEnum):
    """
    Priority ranking for dynamic island events.
    Higher integer value preempts lower integer value.
    """
    IDLE = 10
    MEDIA = 20
    TASK = 25                               # Focus task / Todo
    TIMER = 30                              # Countdown timer / Pomodoro / Stopwatch
    BLUETOOTH_CONNECTED = 45                # Bluetooth connected confirmation
    NETWORK = 50                            # Network transition (online/offline)
    CONNECTIVITY = 50                       # General connectivity / clipboard
    LANGUAGE = 55                           # Input Language / Keyboard Layout
    WINDOW_MINIMIZE = 58                    # macOS-style window minimize/restore feedback
    SLIDER = 60                             # Volume, Brightness
    NOTIFICATION = 68                       # Standard Notification
    BLUETOOTH_CONNECTING = 72               # Bluetooth connecting / connection failure
    SHARE = 75                              # Drag-and-drop Smart Share
    URGENT_NOTIF = 80                       # Urgent Notification
    CRITICAL_POWER = 85                     # Critical low battery (< 15%)
    RECORDING = 90                          # Active Screen Recording / Critical system event
    ERROR = 90                              # Fatal errors / alerts


# Complete set of valid visual and transition states conforming to Section 11
VALID_STATES: Set[str] = {
    # Core States
    "idle",
    "compact",
    "expanded",
    "hover",
    "media",
    "mediaCompact",
    "mediaExpanded",
    "media_expanded",
    "bluetooth",
    "audio",
    "volume",
    "brightness",
    "network",
    "battery",
    "battery_warning",
    "low-battery",
    "charging",
    "recording",
    "notification",
    "timer",
    "pomodoro",
    "quick_actions",
    "quick-actions",
    "quick_settings",
    "settings",
    "error",
    # Smart Share States
    "drag_enter",
    "drag_active",
    "drop_received",
    "share_picker",
    "share_confirm",
    "share_launching",
    "share_cancelled",
    "share_error",
    # Window Management & Minimize/Restore States
    "minimize_detected",
    "minimize_animating",
    "minimized_apps",
    "restore_detected",
    "restore_animating",
    "minimizing",
    "minimized",
    "restoring",
    # Auxiliary & Legacy States
    "task",
    "clipboard",
    "language",
    "system",
    "expanding",
    "collapsing",
}

# Graph of permissible state transitions
VALID_TRANSITIONS = {
    "idle": {"compact", "expanded", "hover", "media", "mediaCompact", "media_expanded", "volume", "brightness", "bluetooth", "network", "battery", "battery_warning", "recording", "notification", "timer", "pomodoro", "drag_enter", "drag_active", "minimize_detected", "minimize_animating", "minimized_apps", "restore_detected", "restore_animating", "quick_settings", "quick_actions", "settings", "task", "language", "clipboard", "system", "error"},
    "compact": {"idle", "expanded", "hover", "media", "volume", "brightness", "drag_enter", "drag_active", "minimize_detected", "minimize_animating", "minimized_apps", "restore_detected", "restore_animating", "quick_settings", "quick_actions", "notification", "error"},
    "expanded": {"idle", "compact", "media_expanded", "minimized_apps", "quick_settings", "quick_actions", "settings", "notification", "error"},
    "minimize_detected": {"minimize_animating", "minimized_apps", "idle", "compact", "error"},
    "minimize_animating": {"minimized_apps", "idle", "compact", "error"},
    "minimized_apps": {"restore_detected", "restore_animating", "idle", "compact", "expanded", "error"},
    "restore_detected": {"restore_animating", "idle", "compact", "error"},
    "restore_animating": {"idle", "compact", "expanded", "error"},
    "drag_enter": {"drag_active", "idle", "compact"},
    "drag_active": {"share_picker", "idle", "compact", "drag_enter"},
    "share_picker": {"share_confirm", "share_launching", "share_error", "share_cancelled", "idle", "compact"},
    "share_confirm": {"share_launching", "share_picker", "share_cancelled", "idle", "compact"},
    "share_launching": {"idle", "compact", "share_error"},
    "share_error": {"idle", "compact", "share_picker"},
    "media_expanded": {"media", "mediaCompact", "idle", "compact", "expanded"},
    "quick_settings": {"idle", "compact", "settings", "expanded"},
    "quick_actions": {"idle", "compact", "settings", "expanded"},
    "notification": {"idle", "compact", "expanded", "notification", "error"},
}


def is_valid_state(state: str) -> bool:
    """Check if a state name is a known valid state."""
    return str(state).strip().lower() in {s.lower() for s in VALID_STATES}


def is_valid_transition(from_state: str, to_state: str) -> bool:
    """Check whether a transition between two states is allowed."""
    src = str(from_state).strip().lower()
    dst = str(to_state).strip().lower()

    if not is_valid_state(dst):
        return False
    if src == dst:
        return True
    # Emergency / high-priority overrides (recording, low-battery, urgent notif, error) always permitted
    if dst in ("recording", "error", "battery_warning", "notification", "idle"):
        return True

    allowed = VALID_TRANSITIONS.get(src, None)
    if allowed is not None:
        return dst in {s.lower() for s in allowed}
    # If not explicitly mapped, permit transitions from transient states back to idle/compact
    return True
