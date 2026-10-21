"""Configuration manager for Ratana Island."""

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict


@dataclass
class IslandDimensions:
    compact_width: int = 280
    compact_height: int = 38
    expanded_width: int = 460
    expanded_height: int = 230
    notification_width: int = 360
    notification_height: int = 44
    margin_top: int = 5
    corner_radius_compact: int = 19
    corner_radius_expanded: int = 26


@dataclass
class MediaConfig:
    enabled: bool = True
    enable_lyrics: bool = True
    lyrics_provider: str = "lrclib"
    sync_tolerance_ms: int = 250
    show_visualizer: bool = True
    max_title_length: int = 32
    auto_media_expand: bool = False


@dataclass
class SystemConfig:
    enable_audio: bool = True
    enable_brightness: bool = True
    volume_step: int = 5
    brightness_step: int = 5
    enable_notifications: bool = True
    notification_timeout_sec: int = 5


@dataclass
class AppearanceConfig:
    theme: str = "mac_obsidian"
    animations: bool = True
    animation_duration_ms: int = 280
    reduced_motion: bool = False
    cpu_friendly: bool = False
    notification_expansion: bool = True
    double_click_action: str = "play_pause"  # "play_pause", "toggle", "none"
    monitor: str = "focused"  # "focused", "all", or output name like "eDP-1"


@dataclass
class AppConfig:
    dimensions: IslandDimensions = field(default_factory=IslandDimensions)
    media: MediaConfig = field(default_factory=MediaConfig)
    system: SystemConfig = field(default_factory=SystemConfig)
    appearance: AppearanceConfig = field(default_factory=AppearanceConfig)

    @classmethod
    def get_config_dir(cls) -> Path:
        xdg_config = os.environ.get("XDG_CONFIG_HOME")
        if xdg_config:
            base = Path(xdg_config)
        else:
            base = Path.home() / ".config"
        return base / "ratana-island"

    @classmethod
    def get_cache_dir(cls) -> Path:
        xdg_cache = os.environ.get("XDG_CACHE_HOME")
        if xdg_cache:
            base = Path(xdg_cache)
        else:
            base = Path.home() / ".cache"
        return base / "ratana-island"

    @classmethod
    def load(cls, path: Path | None = None) -> "AppConfig":
        if path is None:
            path = cls.get_config_dir() / "config.json"

        cfg = cls()
        if not path.exists():
            cfg.save(path)
            return cfg

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            cfg._update_from_dict(data)
        except Exception:
            # Fall back safely to defaults on corruption/parse error
            return cls()

        return cfg

    def _update_from_dict(self, data: Dict[str, Any]) -> None:
        if not isinstance(data, dict):
            return

        if "dimensions" in data and isinstance(data["dimensions"], dict):
            d = data["dimensions"]
            self.dimensions.compact_width = max(160, min(800, int(d.get("compact_width", self.dimensions.compact_width))))
            self.dimensions.compact_height = max(24, min(100, int(d.get("compact_height", self.dimensions.compact_height))))
            self.dimensions.expanded_width = max(320, min(1200, int(d.get("expanded_width", self.dimensions.expanded_width))))
            self.dimensions.expanded_height = max(160, min(600, int(d.get("expanded_height", self.dimensions.expanded_height))))
            self.dimensions.notification_width = max(200, min(800, int(d.get("notification_width", self.dimensions.notification_width))))
            self.dimensions.notification_height = max(30, min(120, int(d.get("notification_height", self.dimensions.notification_height))))
            self.dimensions.margin_top = max(0, min(100, int(d.get("margin_top", self.dimensions.margin_top))))
            self.dimensions.corner_radius_compact = max(8, min(50, int(d.get("corner_radius_compact", self.dimensions.corner_radius_compact))))
            self.dimensions.corner_radius_expanded = max(12, min(50, int(d.get("corner_radius_expanded", self.dimensions.corner_radius_expanded))))

        if "media" in data and isinstance(data["media"], dict):
            m = data["media"]
            self.media.enabled = bool(m.get("enabled", self.media.enabled))
            self.media.enable_lyrics = bool(m.get("enable_lyrics", self.media.enable_lyrics))
            self.media.lyrics_provider = str(m.get("lyrics_provider", self.media.lyrics_provider))
            self.media.sync_tolerance_ms = max(50, min(2000, int(m.get("sync_tolerance_ms", self.media.sync_tolerance_ms))))
            self.media.show_visualizer = bool(m.get("show_visualizer", self.media.show_visualizer))
            self.media.max_title_length = max(10, min(100, int(m.get("max_title_length", self.media.max_title_length))))
            self.media.auto_media_expand = bool(m.get("auto_media_expand", self.media.auto_media_expand))

        if "system" in data and isinstance(data["system"], dict):
            s = data["system"]
            self.system.enable_audio = bool(s.get("enable_audio", self.system.enable_audio))
            self.system.enable_brightness = bool(s.get("enable_brightness", self.system.enable_brightness))
            self.system.volume_step = max(1, min(25, int(s.get("volume_step", self.system.volume_step))))
            self.system.brightness_step = max(1, min(25, int(s.get("brightness_step", self.system.brightness_step))))
            self.system.enable_notifications = bool(s.get("enable_notifications", self.system.enable_notifications))
            self.system.notification_timeout_sec = max(1, min(30, int(s.get("notification_timeout_sec", self.system.notification_timeout_sec))))

        if "appearance" in data and isinstance(data["appearance"], dict):
            a = data["appearance"]
            self.appearance.theme = str(a.get("theme", self.appearance.theme))
            self.appearance.animations = bool(a.get("animations", self.appearance.animations))
            self.appearance.animation_duration_ms = max(50, min(1000, int(a.get("animation_duration_ms", self.appearance.animation_duration_ms))))
            self.appearance.reduced_motion = bool(a.get("reduced_motion", self.appearance.reduced_motion))
            self.appearance.cpu_friendly = bool(a.get("cpu_friendly", self.appearance.cpu_friendly))
            self.appearance.notification_expansion = bool(a.get("notification_expansion", self.appearance.notification_expansion))
            self.appearance.double_click_action = str(a.get("double_click_action", self.appearance.double_click_action))
            self.appearance.monitor = str(a.get("monitor", self.appearance.monitor))

    def save(self, path: Path | None = None) -> None:
        if path is None:
            path = self.get_config_dir() / "config.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=4)
