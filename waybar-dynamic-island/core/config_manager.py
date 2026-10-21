"""
Ratana Dynamic Island — Configuration & Capabilities Manager
============================================================
Handles configuration parsing, atomic file persistence, themes, and compositor capabilities.
"""

import configparser
import logging
import os
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Optional

log = logging.getLogger("ratana-island")

# Runtime Paths & Defaults
RUNTIME_DIR = Path(os.environ.get("XDG_RUNTIME_DIR", f"/tmp/runtime-{os.getuid()}"))
SOCKET_PATH = RUNTIME_DIR / "ratana-island.sock"
LOCK_PATH = RUNTIME_DIR / "ratana-island.lock"
CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "ratana-island"
CONFIG_FILE = Path(os.environ.get("RATANA_CONFIG_FILE", CONFIG_DIR / "config.ini"))

PROTOCOL_VERSION = "1.3.0"
MODES = ["waybar-lite", "waybar-enhanced", "quickshell", "hybrid"]
THEME_PRESETS = [
    "macos-black",
    "macos-glass",
    "hyperos-dark",
    "originos-dark",
    "catppuccin-mocha",
    "minimal-dark",
]

THEME_ALIASES: Dict[str, str] = {
    "glass": "macos-glass",
    "minimal": "minimal-dark",
    "hyperos": "hyperos-dark",
    "originos": "originos-dark",
    "mocha": "catppuccin-mocha",
    "catppuccin": "catppuccin-mocha",
}


def normalize_theme(theme_name: str, fallback: Optional[str] = None) -> Optional[str]:
    """Normalize theme string and resolve backwards-compatible aliases."""
    normalized = str(theme_name).strip().lower()
    if normalized in THEME_ALIASES:
        return THEME_ALIASES[normalized]
    if normalized in THEME_PRESETS:
        return normalized
    return fallback


class IslandConfig:
    def __init__(self, config_path: Optional[Path] = None):
        self.config_file = config_path or CONFIG_FILE
        self.mode: str = "waybar-enhanced"  # 'waybar-lite', 'waybar-enhanced', 'quickshell', 'hybrid'
        self.theme: str = "macos-black"
        self.presentation_mode: str = "stable-width"
        self.compact_width: int = 160
        self.expanded_width: int = 280
        self.position: str = "top-center"  # 'top-center', 'top-left', 'top-right'
        self.blur_enabled: bool = True
        self.monitor: str = ""
        self.reduced_motion: bool = False
        self.show_full: bool = False

        # Integrations
        self.enable_media: bool = True
        self.enable_volume: bool = True
        self.enable_brightness: bool = True
        self.enable_notifications: bool = True
        self.enable_battery: bool = True
        self.enable_recording: bool = True
        self.enable_network: bool = True
        self.enable_clipboard: bool = True
        self.enable_timer: bool = True
        self.enable_language: bool = True
        self.enable_system_metrics: bool = True
        self.enable_share: bool = True
        self.enable_window_manager: bool = True
        self.idle_show_language: bool = True
        self.language_format: str = "both"  # 'both', 'origin', 'full', 'short'
        self.frontend: str = "waybar"  # 'waybar', 'quickshell', 'both', 'hybrid'

        # Dock configuration
        self.dock_enabled: bool = False
        self.dock_position: str = "bottom"
        self.dock_icon_size: int = 48
        self.dock_magnification: bool = True
        self.dock_autohide: bool = False

        # Performance Profiles ('low-resource', 'balanced', 'visual-quality')
        self.performance_profile: str = "balanced"
        self.adaptive_refresh: bool = True
        self.idle_clock_interval_s: float = 15.0
        self.metrics_interval_s: float = 3.0
        self.max_cached_images: int = 24

        # Window Minimize / Restore Animation Configuration
        self.minimize_animation_enabled: bool = True
        self.minimize_style: str = "macos-genie-inspired"  # 'macos-genie-inspired', 'spring-scale', 'scale-fade', 'reduced-motion', 'none', 'low-resource'
        self.minimize_target: str = "island"  # 'island' or 'dock'
        self.minimize_duration_ms: int = 380
        self.minimize_highlight: bool = True
        self.minimized_apps_visibility: str = "auto"  # 'auto', 'compact', 'expanded', 'hidden'
        self.minimize_exclusions: List[str] = []

        # Privacy & Timeouts
        self.network_ssid_privacy: bool = True
        self.clipboard_privacy: bool = True
        self.preferred_menu: str = "auto"
        self.volume_timeout_s: float = 1.5
        self.brightness_timeout_s: float = 1.5
        self.notification_timeout_s: float = 4.0
        self.urgent_notification_timeout_s: float = 6.0
        self.network_timeout_s: float = 3.0
        self.clipboard_timeout_s: float = 2.0
        self.charging_timeout_s: float = 3.0
        self.language_timeout_s: float = 2.0
        self.share_timeout_s: float = 60.0
        self.battery_low_threshold: int = 15

        # Recording
        self.recorders: List[str] = ["wf-recorder", "wl-screenrec", "gpu-screen-recorder", "obs"]
        self.obs_websocket_enabled: bool = False
        self.obs_websocket_url: str = "ws://127.0.0.1:4455"
        self.obs_websocket_password: str = ""

        self.load()

    @staticmethod
    def normalize_minimize_style(style_name: str) -> str:
        """Map human or legacy style strings to canonical style tokens."""
        s = str(style_name).strip().lower()
        if s in ("lamp", "macos-lamp", "lamp-effect", "magic-lamp", "aladdin"):
            return "macos-lamp"
        if s in ("genie", "genie-inspired", "macos-genie", "macos-genie-inspired"):
            return "macos-genie-inspired"
        if s in ("spring-scale", "spring_scale"):
            return "spring-scale"
        if s in ("originos-spring", "spring", "bounce", "elastic"):
            return "originos-spring"
        if s in ("originos-morph", "morph"):
            return "originos-morph"
        if s in ("hyperos-mini", "hyperos", "mini", "snappy"):
            return "hyperos-mini"
        if s in ("scale-fade", "scale_fade", "macos-fade", "fade"):
            return "scale-fade"
        if s in ("low-resource", "low_resource", "lightweight", "fast"):
            return "low-resource"
        if s in ("reduced-motion", "reduced_motion", "subtle"):
            return "reduced-motion"
        if s in ("none", "disabled", "off"):
            return "none"
        if s in ("scale", "macos-scale", "minimize-to-island", "minimize-to-dock"):
            return "scale"
        return "macos-genie-inspired"

    def apply_profile(self, profile_name: str):
        """Configure parameters dynamically based on selected performance profile."""
        p = profile_name.lower().strip()
        if p == "low-resource":
            self.performance_profile = "low-resource"
            self.idle_clock_interval_s = 30.0
            self.metrics_interval_s = 6.0
            self.reduced_motion = True
            self.blur_enabled = False
            self.minimize_duration_ms = 180
            self.minimize_style = "low-resource"
            self.max_cached_images = 8
        elif p == "visual-quality":
            self.performance_profile = "visual-quality"
            self.idle_clock_interval_s = 5.0
            self.metrics_interval_s = 2.0
            self.reduced_motion = False
            self.blur_enabled = True
            self.minimize_duration_ms = 420
            self.minimize_style = "macos-genie-inspired"
            self.max_cached_images = 64
        else:  # balanced
            self.performance_profile = "balanced"
            self.idle_clock_interval_s = 15.0
            self.metrics_interval_s = 3.0
            self.reduced_motion = False
            self.blur_enabled = True
            self.minimize_duration_ms = 380
            self.minimize_style = "scale"
            self.max_cached_images = 24

    def load(self):
        """Load configuration from INI file if present."""
        if not self.config_file.exists():
            log.info(f"No config.ini found at {self.config_file}. Using sensible defaults.")
            return

        parser = configparser.ConfigParser()
        try:
            parser.read(str(self.config_file))
            if "General" in parser:
                gen = parser["General"]
                self.mode = gen.get("mode", self.mode)
                self.theme = normalize_theme(gen.get("theme", self.theme), fallback="macos-black")
                self.presentation_mode = gen.get("presentation_mode", self.presentation_mode)
                self.compact_width = gen.getint("compact_width", self.compact_width)
                self.expanded_width = gen.getint("expanded_width", self.expanded_width)
                self.position = gen.get("position", self.position)
                self.blur_enabled = gen.getboolean("blur_enabled", self.blur_enabled)
                self.monitor = gen.get("monitor", self.monitor)
                self.reduced_motion = gen.getboolean("reduced_motion", self.reduced_motion)
                self.show_full = gen.getboolean("show_full", self.show_full)
                self.frontend = gen.get("frontend", self.frontend)

            if "Dock" in parser:
                dk = parser["Dock"]
                self.dock_enabled = dk.getboolean("dock_enabled", self.dock_enabled)
                self.dock_position = dk.get("dock_position", self.dock_position)
                self.dock_icon_size = dk.getint("dock_icon_size", self.dock_icon_size)
                self.dock_magnification = dk.getboolean("dock_magnification", self.dock_magnification)
                self.dock_autohide = dk.getboolean("dock_autohide", self.dock_autohide)

            if "Integrations" in parser:
                integ = parser["Integrations"]
                self.enable_media = integ.getboolean("enable_media", self.enable_media)
                self.enable_volume = integ.getboolean("enable_volume", self.enable_volume)
                self.enable_brightness = integ.getboolean("enable_brightness", self.enable_brightness)
                self.enable_notifications = integ.getboolean("enable_notifications", self.enable_notifications)
                self.enable_battery = integ.getboolean("enable_battery", self.enable_battery)
                self.enable_recording = integ.getboolean("enable_recording", self.enable_recording)
                self.enable_network = integ.getboolean("enable_network", self.enable_network)
                self.enable_clipboard = integ.getboolean("enable_clipboard", self.enable_clipboard)
                self.enable_timer = integ.getboolean("enable_timer", self.enable_timer)
                self.enable_language = integ.getboolean("enable_language", self.enable_language)
                self.enable_system_metrics = integ.getboolean("enable_system_metrics", self.enable_system_metrics)
                self.enable_share = integ.getboolean("enable_share", self.enable_share)
                self.enable_window_manager = integ.getboolean("enable_window_manager", self.enable_window_manager)
                self.idle_show_language = integ.getboolean("idle_show_language", self.idle_show_language)
                self.language_format = integ.get("language_format", self.language_format)

                self.network_ssid_privacy = integ.getboolean("network_ssid_privacy", self.network_ssid_privacy)
                self.clipboard_privacy = integ.getboolean("clipboard_privacy", self.clipboard_privacy)
                self.preferred_menu = integ.get("preferred_menu", self.preferred_menu)

                self.volume_timeout_s = integ.getfloat("volume_timeout_s", self.volume_timeout_s)
                self.brightness_timeout_s = integ.getfloat("brightness_timeout_s", self.brightness_timeout_s)
                self.notification_timeout_s = integ.getfloat("notification_timeout_s", self.notification_timeout_s)
                self.urgent_notification_timeout_s = integ.getfloat("urgent_notification_timeout_s", self.urgent_notification_timeout_s)
                self.network_timeout_s = integ.getfloat("network_timeout_s", self.network_timeout_s)
                self.clipboard_timeout_s = integ.getfloat("clipboard_timeout_s", self.clipboard_timeout_s)
                self.charging_timeout_s = integ.getfloat("charging_timeout_s", self.charging_timeout_s)
                self.language_timeout_s = integ.getfloat("language_timeout_s", self.language_timeout_s)
                self.share_timeout_s = integ.getfloat("share_timeout_s", self.share_timeout_s)
                self.battery_low_threshold = integ.getint("battery_low_threshold", self.battery_low_threshold)

            if "Recording" in parser:
                rec = parser["Recording"]
                rec_str = rec.get("recorders", "")
                if rec_str:
                    self.recorders = [r.strip() for r in rec_str.split(",") if r.strip()]
                self.obs_websocket_enabled = rec.getboolean("obs_websocket_enabled", self.obs_websocket_enabled)
                self.obs_websocket_url = rec.get("obs_websocket_url", self.obs_websocket_url)
            if "Performance" in parser:
                perf = parser["Performance"]
                p_name = perf.get("profile", self.performance_profile)
                self.apply_profile(p_name)
                self.adaptive_refresh = perf.getboolean("adaptive_refresh", self.adaptive_refresh)
                self.idle_clock_interval_s = perf.getfloat("idle_clock_interval_s", self.idle_clock_interval_s)
                self.metrics_interval_s = perf.getfloat("metrics_interval_s", self.metrics_interval_s)
                self.max_cached_images = perf.getint("max_cached_images", self.max_cached_images)

            if "WindowManagement" in parser:
                wm = parser["WindowManagement"]
                self.minimize_animation_enabled = wm.getboolean("minimize_animation_enabled", self.minimize_animation_enabled)
                self.minimize_style = self.normalize_minimize_style(wm.get("minimize_style", self.minimize_style))
                self.minimize_target = wm.get("minimize_target", self.minimize_target)
                self.minimize_duration_ms = wm.getint("minimize_duration_ms", self.minimize_duration_ms)
                self.minimize_highlight = wm.getboolean("minimize_highlight", self.minimize_highlight)
                self.minimized_apps_visibility = wm.get("minimized_apps_visibility", self.minimized_apps_visibility)

            log.info(f"Loaded configuration from {self.config_file} (mode={self.mode}, theme={self.theme}, full={self.show_full})")
        except Exception as e:
            log.warning(f"Error parsing {self.config_file}: {e}. Retaining safe defaults.")

    def save(self):
        """Persist current configuration to INI file atomically."""
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        parser = configparser.ConfigParser()
        parser["General"] = {
            "mode": self.mode,
            "frontend": self.frontend,
            "theme": self.theme,
            "presentation_mode": self.presentation_mode,
            "compact_width": str(self.compact_width),
            "expanded_width": str(self.expanded_width),
            "position": self.position,
            "blur_enabled": str(self.blur_enabled).lower(),
            "monitor": self.monitor,
            "reduced_motion": str(self.reduced_motion).lower(),
            "show_full": str(self.show_full).lower(),
        }
        parser["Dock"] = {
            "dock_enabled": str(self.dock_enabled).lower(),
            "dock_position": self.dock_position,
            "dock_icon_size": str(self.dock_icon_size),
            "dock_magnification": str(self.dock_magnification).lower(),
            "dock_autohide": str(self.dock_autohide).lower(),
        }
        parser["Integrations"] = {
            "enable_media": str(self.enable_media).lower(),
            "enable_volume": str(self.enable_volume).lower(),
            "enable_brightness": str(self.enable_brightness).lower(),
            "enable_notifications": str(self.enable_notifications).lower(),
            "enable_battery": str(self.enable_battery).lower(),
            "enable_recording": str(self.enable_recording).lower(),
            "enable_network": str(self.enable_network).lower(),
            "enable_clipboard": str(self.enable_clipboard).lower(),
            "enable_timer": str(self.enable_timer).lower(),
            "enable_language": str(self.enable_language).lower(),
            "enable_system_metrics": str(self.enable_system_metrics).lower(),
            "idle_show_language": str(self.idle_show_language).lower(),
            "language_format": self.language_format,
            "network_ssid_privacy": str(self.network_ssid_privacy).lower(),
            "clipboard_privacy": str(self.clipboard_privacy).lower(),
            "preferred_menu": self.preferred_menu,
            "volume_timeout_s": str(self.volume_timeout_s),
            "brightness_timeout_s": str(self.brightness_timeout_s),
            "notification_timeout_s": str(self.notification_timeout_s),
            "urgent_notification_timeout_s": str(self.urgent_notification_timeout_s),
            "network_timeout_s": str(self.network_timeout_s),
            "clipboard_timeout_s": str(self.clipboard_timeout_s),
            "charging_timeout_s": str(self.charging_timeout_s),
            "language_timeout_s": str(self.language_timeout_s),
            "battery_low_threshold": str(self.battery_low_threshold),
        }
        parser["Recording"] = {
            "recorders": ",".join(self.recorders),
            "obs_websocket_enabled": str(self.obs_websocket_enabled).lower(),
            "obs_websocket_url": self.obs_websocket_url,
            "obs_websocket_password": self.obs_websocket_password,
        }
        parser["Performance"] = {
            "profile": self.performance_profile,
            "adaptive_refresh": str(self.adaptive_refresh).lower(),
            "idle_clock_interval_s": str(self.idle_clock_interval_s),
            "metrics_interval_s": str(self.metrics_interval_s),
            "max_cached_images": str(self.max_cached_images),
        }
        parser["WindowManagement"] = {
            "minimize_animation_enabled": str(self.minimize_animation_enabled).lower(),
            "minimize_style": self.minimize_style,
            "minimize_target": self.minimize_target,
            "minimize_duration_ms": str(self.minimize_duration_ms),
            "minimize_highlight": str(self.minimize_highlight).lower(),
            "minimized_apps_visibility": self.minimized_apps_visibility,
        }
        temp_file = self.config_file.with_suffix(".tmp")
        try:
            with open(temp_file, "w") as f:
                parser.write(f)
            temp_file.replace(self.config_file)
            log.info(f"Persisted configuration atomically to {self.config_file}")
        except Exception as e:
            log.error(f"Failed to save {self.config_file}: {e}")

    def restore_defaults(self):
        """Restore all configuration settings to factory defaults and save."""
        self.mode = "waybar-enhanced"
        self.theme = "macos-black"
        self.presentation_mode = "stable-width"
        self.compact_width = 160
        self.expanded_width = 280
        self.position = "top-center"
        self.blur_enabled = True
        self.monitor = ""
        self.reduced_motion = False
        self.show_full = False
        self.enable_media = True
        self.enable_volume = True
        self.enable_brightness = True
        self.enable_notifications = True
        self.enable_battery = True
        self.enable_recording = True
        self.enable_network = True
        self.enable_clipboard = True
        self.enable_timer = True
        self.enable_language = True
        self.enable_system_metrics = True
        self.enable_share = True
        self.enable_window_manager = True
        self.idle_show_language = True
        self.language_format = "both"
        self.frontend = "waybar"
        self.dock_enabled = False
        self.dock_position = "bottom"
        self.dock_icon_size = 48
        self.dock_magnification = True
        self.dock_autohide = False
        self.performance_profile = "balanced"
        self.adaptive_refresh = True
        self.idle_clock_interval_s = 15.0
        self.metrics_interval_s = 3.0
        self.max_cached_images = 24
        self.minimize_animation_enabled = True
        self.minimize_style = "macos-genie-inspired"
        self.minimize_target = "island"
        self.minimize_duration_ms = 380
        self.minimize_highlight = True
        self.minimized_apps_visibility = "auto"
        self.minimize_exclusions = []
        self.network_ssid_privacy = True
        self.clipboard_privacy = True
        self.preferred_menu = "auto"
        self.volume_timeout_s = 1.5
        self.brightness_timeout_s = 1.5
        self.notification_timeout_s = 4.0
        self.urgent_notification_timeout_s = 6.0
        self.network_timeout_s = 3.0
        self.clipboard_timeout_s = 2.0
        self.charging_timeout_s = 3.0
        self.language_timeout_s = 2.0
        self.share_timeout_s = 60.0
        self.battery_low_threshold = 15
        self.save()

    def export_dict(self) -> Dict[str, Any]:
        """Export all current configurable settings as a dictionary."""
        return {
            "mode": self.mode,
            "frontend": self.frontend,
            "theme": self.theme,
            "presentation_mode": self.presentation_mode,
            "position": self.position,
            "blur_enabled": self.blur_enabled,
            "reduced_motion": self.reduced_motion,
            "show_full": self.show_full,
            "performance_profile": self.performance_profile,
            "dock_enabled": self.dock_enabled,
            "dock_position": self.dock_position,
            "dock_icon_size": self.dock_icon_size,
            "dock_magnification": self.dock_magnification,
            "dock_autohide": self.dock_autohide,
            "minimize_animation_enabled": self.minimize_animation_enabled,
            "minimize_style": self.minimize_style,
            "minimize_target": self.minimize_target,
            "minimize_duration_ms": self.minimize_duration_ms,
            "minimize_highlight": self.minimize_highlight,
            "minimized_apps_visibility": self.minimized_apps_visibility,
            "network_ssid_privacy": self.network_ssid_privacy,
            "clipboard_privacy": self.clipboard_privacy,
            "enable_share": self.enable_share,
            "enable_window_manager": self.enable_window_manager,
            "enable_media": self.enable_media,
            "enable_volume": self.enable_volume,
            "enable_brightness": self.enable_brightness,
            "enable_notifications": self.enable_notifications,
            "enable_battery": self.enable_battery,
            "enable_network": self.enable_network,
        }

    def import_dict(self, data: Dict[str, Any]) -> bool:
        """Validate and import settings from a dictionary."""
        if not isinstance(data, dict):
            return False
        for k, v in data.items():
            self.set_setting(k, v)
        self.save()
        return True

    def set_setting(self, key: str, val: Any) -> bool:
        """Set a single configuration setting with validation and type coercion."""
        key = str(key).strip().lower()
        bool_keys = {
            "blur_enabled", "reduced_motion", "show_full", "dock_enabled",
            "dock_magnification", "dock_autohide", "minimize_animation_enabled",
            "minimize_highlight", "network_ssid_privacy", "clipboard_privacy",
            "enable_share", "enable_window_manager", "enable_media", "enable_volume",
            "enable_brightness", "enable_notifications", "enable_battery", "enable_network"
        }
        int_keys = {"dock_icon_size", "minimize_duration_ms", "compact_width", "expanded_width"}

        if key in bool_keys:
            if isinstance(val, str):
                b = val.lower() in ("true", "1", "yes", "on")
            else:
                b = bool(val)
            setattr(self, key, b)
            return True
        elif key in int_keys:
            try:
                setattr(self, key, int(val))
                return True
            except (ValueError, TypeError):
                return False
        elif key == "theme":
            norm = normalize_theme(str(val))
            if norm:
                self.theme = norm
                return True
            return False
        elif key == "mode":
            m = str(val).lower()
            if m in MODES:
                self.mode = m
                return True
            return False
        elif key == "frontend":
            f = str(val).lower()
            if f in ("waybar", "quickshell", "both", "hybrid"):
                self.frontend = f
                return True
            return False
        elif key == "minimize_style":
            self.minimize_style = self.normalize_minimize_style(str(val))
            return True
        elif key == "performance_profile":
            self.apply_profile(str(val))
            return True
        elif hasattr(self, key):
            setattr(self, key, val)
            return True
        return False


class BackendCapabilities:
    """Detects available compositors and system helper utilities."""
    def __init__(self):
        self.desktop_env = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
        self.is_sway = "sway" in self.desktop_env
        self.is_hyprland = "hyprland" in self.desktop_env

        # Available binaries
        self.has_playerctl = shutil.which("playerctl") is not None
        self.has_pactl = shutil.which("pactl") is not None
        self.has_wpctl = shutil.which("wpctl") is not None
        self.has_brightnessctl = shutil.which("brightnessctl") is not None
        self.has_upower = shutil.which("upower") is not None
        self.has_nmcli = shutil.which("nmcli") is not None
        self.has_wl_paste = shutil.which("wl-paste") is not None
        self.has_dbus_monitor = shutil.which("dbus-monitor") is not None
        self.has_swaync_client = shutil.which("swaync-client") is not None
        self.has_makoctl = shutil.which("makoctl") is not None
        self.has_fuzzel = shutil.which("fuzzel") is not None
        self.has_rofi = shutil.which("rofi") is not None
        self.has_wofi = shutil.which("wofi") is not None

    def get_detected_compositor(self) -> str:
        if self.is_sway:
            return "Sway / SwayFX"
        elif self.is_hyprland:
            return "Hyprland"
        return self.desktop_env or "Wayland Compositor"

    def summary(self) -> str:
        parts = [f"Compositor={self.get_detected_compositor()}"]
        if self.has_playerctl: parts.append("MPRIS=playerctl")
        if self.has_pactl: parts.append("Audio=pactl")
        elif self.has_wpctl: parts.append("Audio=wpctl")
        if self.has_brightnessctl: parts.append("Backlight=brightnessctl")
        if self.has_upower: parts.append("Power=upower")
        if self.has_nmcli: parts.append("Network=nmcli")
        return ", ".join(parts)
