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


# Complete set of valid visual and transition states
VALID_STATES: Set[str] = {
    # Core Visual States
    "idle",
    "hover",
    "media",
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
    "settings",
    "expanded",
    "error",
    # Smart Share & Window States
    "drag_enter",
    "drag_active",
    "drop_received",
    "share_picker",
    "share_launching",
    "share_cancelled",
    "share_error",
    "minimizing",
    "minimized",
    "restoring",
    # Legacy & Auxiliary States
    "task",
    "clipboard",
    "language",
    "system",
    "expanding",
    "collapsing",
}


def is_valid_state(state: str) -> bool:
    """Check if a state name is a known valid state."""
    return str(state).strip().lower() in VALID_STATES
