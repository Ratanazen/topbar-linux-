"""
Ratana Dynamic Island — State Manager
=====================================
Encapsulates state modeling, text formatting, progress bar generation,
language resolution, and app icon mapping.
"""

import html
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.priority_manager import Priority

BLOCKS_FILLED = "▰"
BLOCKS_EMPTY = "▱"


def build_progress_bar(percent: float, total_blocks: int = 5) -> str:
    """Build a compact unicode block progress bar."""
    percent = max(0.0, min(100.0, percent))
    filled = int(round((percent / 100.0) * total_blocks))
    filled = max(0, min(total_blocks, filled))
    return (BLOCKS_FILLED * filled) + (BLOCKS_EMPTY * (total_blocks - filled))


def truncate_text(text: str, max_chars: int = 24, force_full: bool = False) -> str:
    """Safely sanitize whitespace and truncate text with an ellipsis unless full mode is requested."""
    clean = " ".join(str(text).strip().split())
    if force_full:
        return clean
    if len(clean) > max_chars:
        return clean[:max_chars - 1] + "…"
    return clean


LANGUAGE_MAP: Dict[str, Dict[str, str]] = {
    "English (US)": {
        "short": "US",
        "full": "English (US)",
        "origin": "English",
        "flag": "󰌌",
    },
    "Khmer (Cambodia)": {
        "short": "KH",
        "full": "Khmer (Cambodia)",
        "origin": "ភាសាខ្មែរ",
        "flag": "󰌌",
    },
    "Khmer": {
        "short": "KH",
        "full": "Khmer (Cambodia)",
        "origin": "ភាសាខ្មែរ",
        "flag": "󰌌",
    },
    "English": {
        "short": "EN",
        "full": "English",
        "origin": "English",
        "flag": "󰌌",
    },
    "French": {
        "short": "FR",
        "full": "French",
        "origin": "Français",
        "flag": "󰌌",
    },
    "German": {
        "short": "DE",
        "full": "German",
        "origin": "Deutsch",
        "flag": "󰌌",
    },
    "Spanish": {
        "short": "ES",
        "full": "Spanish",
        "origin": "Español",
        "flag": "󰌌",
    },
    "Japanese": {
        "short": "JP",
        "full": "Japanese",
        "origin": "日本語",
        "flag": "󰌌",
    },
    "Chinese": {
        "short": "CN",
        "full": "Chinese",
        "origin": "中文",
        "flag": "󰌌",
    },
    "Russian": {
        "short": "RU",
        "full": "Russian",
        "origin": "Русский",
        "flag": "󰌌",
    },
    "Thai": {
        "short": "TH",
        "full": "Thai",
        "origin": "ไทย",
        "flag": "󰌌",
    },
    "Vietnamese": {
        "short": "VN",
        "full": "Vietnamese",
        "origin": "Tiếng Việt",
        "flag": "󰌌",
    },
}


def resolve_language_info(raw_name: str) -> Dict[str, str]:
    """Resolve raw layout name to full, origin, and short representation."""
    if not raw_name:
        return {"short": "US", "full": "English (US)", "origin": "English", "flag": "󰌌"}

    # Exact match
    if raw_name in LANGUAGE_MAP:
        return LANGUAGE_MAP[raw_name]

    # Substring / Case-insensitive match
    lower = raw_name.lower()
    for k, v in LANGUAGE_MAP.items():
        if k.lower() in lower or lower in k.lower():
            return v

    return {
        "short": raw_name[:2].upper(),
        "full": raw_name,
        "origin": raw_name,
        "flag": "󰌌"
    }


def resolve_app_icon(app_name: str, app_icon: str = "", summary: str = "") -> str:
    """Intelligently map application identifiers or categories to rich Nerd Font glyphs."""
    target = f"{app_name} {app_icon} {summary}".lower()

    if any(k in target for k in ["telegram", "tg"]):
        return "󰖣"
    if any(k in target for k in ["discord", "vesktop", "webcord"]):
        return "󰙯"
    if any(k in target for k in ["spotify", "ncspot", "music", "rhythmbox", "cider"]):
        return "󰓇"
    if any(k in target for k in ["firefox"]):
        return "󰈹"
    if any(k in target for k in ["chrome", "chromium", "brave", "zen", "browser", "vivaldi", "edge"]):
        return ""
    if any(k in target for k in ["code", "vscodium", "vscode", "neovim", "nvim", "jetbrains"]):
        return "󰨞"
    if any(k in target for k in ["kitty", "alacritty", "foot", "terminal", "wezterm", "ghostty", "konsole"]):
        return "󰄛"
    if any(k in target for k in ["mail", "email", "thunderbird", "evolution", "kmail"]):
        return "󰇮"
    if any(k in target for k in ["update", "pacman", "garuda", "pamac", "checkupdates", "yay", "paru"]):
        return "󰏔"
    if any(k in target for k in ["obs", "recorder", "recording", "screenrec", "wf-recorder"]):
        return "󰑋"
    if any(k in target for k in ["bluetooth", "bluez", "blueman"]):
        return "󰂯"
    if any(k in target for k in ["volume", "audio", "sound", "headphone", "wireplumber", "pulseaudio"]):
        return "󰕾"
    if any(k in target for k in ["network", "wifi", "ethernet", "wlan", "networkmanager", "nm-applet"]):
        return "󰤨"
    if any(k in target for k in ["battery", "power", "charging", "upower"]):
        return "󰂄"
    if any(k in target for k in ["calendar", "event", "reminder", "alarm"]):
        return "󰃭"
    if any(k in target for k in ["github", "gitlab", "git"]):
        return "󰊤"
    if any(k in target for k in ["steam", "game", "gaming", "heroic", "lutris"]):
        return "󰓓"
    if any(k in target for k in ["download", "torrent", "transmission", "qbittorrent"]):
        return "󰇚"
    return "󰂚"


@dataclass
class IslandState:
    event_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    source: str = "core"
    state: str = "idle"
    priority: int = Priority.IDLE
    created_at: float = field(default_factory=time.monotonic)
    duration: Optional[float] = None  # None = persistent, float = seconds

    title: str = ""
    subtitle: str = ""
    progress_bar: str = ""
    progress_pct: float = 0.0
    icon: str = "󰸗"
    css_class: str = ""
    tooltip: str = ""
    privacy_level: str = "public"
    dismissal_policy: str = "auto"

    # Rich payload fields for artwork, media detail, device, and system monitoring
    art_url: str = ""
    duration_str: str = ""
    position_str: str = ""
    player_name: str = ""
    device_mac: str = ""
    device_battery: Optional[int] = None
    system_cpu: float = 0.0
    system_mem: float = 0.0

    # Smart Share and Window Management payload fields
    dropped_files: List[Dict[str, Any]] = field(default_factory=list)
    share_targets: List[Dict[str, Any]] = field(default_factory=list)
    running_windows: List[Dict[str, Any]] = field(default_factory=list)

    # State Machine & Animation tracking
    previous_state: Optional[str] = None
    anim_key: str = ""

    @property
    def is_expired(self) -> bool:
        if self.duration is None:
            return False
        return (time.monotonic() - self.created_at) >= self.duration

    def to_waybar_payload(self, config: Any) -> Dict[str, Any]:
        """Convert state to a valid JSON dictionary conforming to Waybar protocol and rich stream consumers."""
        icon_esc = html.escape(self.icon)
        title_esc = html.escape(self.title)
        subtitle_esc = html.escape(self.subtitle) if self.subtitle else ""
        bar_esc = html.escape(self.progress_bar) if self.progress_bar else ""

        if self.css_class.startswith("idle"):
            formatted_text = f"{icon_esc}  {title_esc}"
        elif self.progress_bar and subtitle_esc:
            formatted_text = f"{icon_esc}  <b>{title_esc}</b>  <span>{bar_esc}</span>  <span alpha='70%'>{subtitle_esc}</span>"
        elif self.progress_bar:
            formatted_text = f"{icon_esc}  <b>{title_esc}</b>  <span>{bar_esc}</span>"
        elif subtitle_esc:
            formatted_text = f"{icon_esc}  <b>{title_esc}</b>  <span alpha='70%'>{subtitle_esc}</span>"
        else:
            formatted_text = f"{icon_esc}  <b>{title_esc}</b>"

        # Compose classes including theme, mode, and presentation mode
        classes = ["island", self.state]
        if self.css_class:
            classes.append(self.css_class)
        if getattr(config, "show_full", False):
            classes.append("full")
        if getattr(config, "presentation_mode", ""):
            classes.append(config.presentation_mode)
        if getattr(config, "theme", ""):
            classes.append(f"theme-{config.theme}")
        if getattr(config, "reduced_motion", False):
            classes.append("reduced-motion")
        if getattr(config, "mode", ""):
            classes.append(f"mode-{config.mode}")

        return {
            "text": formatted_text,
            "alt": self.state,
            "tooltip": self.tooltip or f"Ratana Island: {self.title}",
            "class": " ".join(dict.fromkeys(classes)).strip(),
            # Rich structured fields for Quickshell & advanced IPC
            "state": self.state,
            "title": self.title,
            "subtitle": self.subtitle,
            "icon": self.icon,
            "progress_bar": self.progress_bar,
            "progress_pct": getattr(self, "progress_pct", 0.0),
            "priority": int(self.priority),
            "source": self.source,
            "duration": self.duration,
            "theme": getattr(config, "theme", "macos-black"),
            "presentation_mode": getattr(config, "presentation_mode", "stable-width"),
            "reduced_motion": getattr(config, "reduced_motion", False),
            "frontend": getattr(config, "frontend", "waybar"),
            "show_full": getattr(config, "show_full", False),
            "capsule_position": getattr(config, "position", "top-center"),
            "blur_enabled": getattr(config, "blur_enabled", True),
            "minimize_style": getattr(config, "minimize_style", "scale"),
            "minimize_target": getattr(config, "minimize_target", "island"),
            "minimized_apps_visibility": getattr(config, "minimized_apps_visibility", "auto"),
            "art_url": getattr(self, "art_url", ""),
            "duration_str": getattr(self, "duration_str", ""),
            "position_str": getattr(self, "position_str", ""),
            "player_name": getattr(self, "player_name", ""),
            "device_mac": getattr(self, "device_mac", ""),
            "device_battery": getattr(self, "device_battery", None),
            "system_cpu": getattr(self, "system_cpu", 0.0),
            "system_mem": getattr(self, "system_mem", 0.0),
            "dropped_files": getattr(self, "dropped_files", []),
            "share_targets": getattr(self, "share_targets", []),
            "running_windows": getattr(self, "running_windows", []),
            "previous_state": getattr(self, "previous_state", None),
            "anim_key": getattr(self, "anim_key", ""),
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert state to raw dictionary for JSON serialization."""
        return {
            "event_id": self.event_id,
            "source": self.source,
            "state": self.state,
            "priority": int(self.priority),
            "created_at": self.created_at,
            "duration": self.duration,
            "title": self.title,
            "subtitle": self.subtitle,
            "progress_bar": self.progress_bar,
            "progress_pct": self.progress_pct,
            "icon": self.icon,
            "css_class": self.css_class,
            "tooltip": self.tooltip,
            "is_expired": self.is_expired,
            "art_url": self.art_url,
            "duration_str": self.duration_str,
            "position_str": self.position_str,
            "player_name": self.player_name,
            "device_mac": self.device_mac,
            "device_battery": self.device_battery,
            "system_cpu": self.system_cpu,
            "system_mem": self.system_mem,
            "dropped_files": self.dropped_files,
            "share_targets": self.share_targets,
            "running_windows": self.running_windows,
            "previous_state": self.previous_state,
            "animation_token": self.animation_token,
        }
