"""Expanded Card view for Ratana Island (GTK4)."""

import os
from typing import Callable, Optional
import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Pango
from ratana_island.config import AppConfig
from ratana_island.services.lyrics import SyncLyricsState
from ratana_island.services.media import TrackMetadata


def format_time(seconds: float) -> str:
    s = max(0, int(seconds))
    m = s // 60
    sec = s % 60
    return f"{m:02d}:{sec:02d}"


class ExpandedView(Gtk.Box):
    def __init__(
        self,
        config: AppConfig,
        on_play_pause: Callable[[], None],
        on_next: Callable[[], None],
        on_prev: Callable[[], None],
        on_seek: Callable[[float], None],
        on_volume_change: Callable[[int], None],
        on_brightness_change: Callable[[int], None],
    ):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.config = config
        self.on_play_pause = on_play_pause
        self.on_next = on_next
        self.on_prev = on_prev
        self.on_seek = on_seek
        self.on_volume_change = on_volume_change
        self.on_brightness_change = on_brightness_change

        self.add_css_class("expanded-box")
        self._seeking = False

        # --- Top Section: Artwork & Track Metadata ---
        self.top_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)

        # Artwork
        self.art_picture = Gtk.Picture()
        self.art_picture.set_size_request(56, 56)
        self.art_picture.set_can_shrink(True)
        self.art_picture.add_css_class("album-art-expanded")

        self.fallback_art = Gtk.Image.new_from_icon_name("audio-x-generic-symbolic")
        self.fallback_art.set_pixel_size(48)
        self.fallback_art.add_css_class("hud-icon")

        self.art_stack = Gtk.Stack()
        self.art_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.art_stack.set_transition_duration(200)
        self.art_stack.add_named(self.art_picture, "picture")
        self.art_stack.add_named(self.fallback_art, "fallback")
        self.art_stack.set_visible_child_name("fallback")
        self.top_box.append(self.art_stack)

        self._last_lyrics_index = -999
        self._last_lyrics_synced = None

        # Metadata text container
        meta_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        meta_box.set_valign(Gtk.Align.CENTER)
        meta_box.set_hexpand(True)

        self.title_label = Gtk.Label(label="No Track Playing")
        self.title_label.add_css_class("expanded-title")
        self.title_label.set_xalign(0.0)
        self.title_label.set_ellipsize(Pango.EllipsizeMode.END)
        meta_box.append(self.title_label)

        self.artist_label = Gtk.Label(label="Unknown Artist")
        self.artist_label.add_css_class("expanded-artist")
        self.artist_label.set_xalign(0.0)
        self.artist_label.set_ellipsize(Pango.EllipsizeMode.END)
        meta_box.append(self.artist_label)

        self.top_box.append(meta_box)

        # Player Badge (e.g. Spotify)
        self.player_badge = Gtk.Label(label="MPRIS")
        self.player_badge.add_css_class("expanded-player-badge")
        self.player_badge.set_valign(Gtk.Align.START)
        self.top_box.append(self.player_badge)

        self.append(self.top_box)

        # --- Middle Section: Synchronized Lyrics Pane ---
        self.lyrics_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        self.lyrics_box.add_css_class("lyrics-box")

        self.lyric_prev_label = Gtk.Label(label="")
        self.lyric_prev_label.add_css_class("lyric-prev")
        self.lyric_prev_label.set_xalign(0.5)
        self.lyric_prev_label.set_ellipsize(Pango.EllipsizeMode.END)
        self.lyrics_box.append(self.lyric_prev_label)

        self.lyric_active_label = Gtk.Label(label="Ratana Island")
        self.lyric_active_label.add_css_class("lyric-active")
        self.lyric_active_label.set_xalign(0.5)
        self.lyric_active_label.set_ellipsize(Pango.EllipsizeMode.END)
        self.lyrics_box.append(self.lyric_active_label)

        self.lyric_next_label = Gtk.Label(label="")
        self.lyric_next_label.add_css_class("lyric-next")
        self.lyric_next_label.set_xalign(0.5)
        self.lyric_next_label.set_ellipsize(Pango.EllipsizeMode.END)
        self.lyrics_box.append(self.lyric_next_label)

        self.append(self.lyrics_box)

        # --- Bottom Section: Progress Bar & Controls ---
        progress_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.elapsed_label = Gtk.Label(label="00:00")
        self.elapsed_label.add_css_class("time-label")
        progress_box.append(self.elapsed_label)

        self.progress_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0.0, 100.0, 1.0)
        self.progress_scale.set_draw_value(False)
        self.progress_scale.set_hexpand(True)
        self.progress_scale.connect("change-value", self._on_scale_change)
        progress_box.append(self.progress_scale)

        self.total_label = Gtk.Label(label="00:00")
        self.total_label.add_css_class("time-label")
        progress_box.append(self.total_label)
        self.append(progress_box)

        # Playback Control Buttons
        ctrl_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        ctrl_box.set_halign(Gtk.Align.CENTER)

        self.prev_btn = Gtk.Button.new_from_icon_name("media-skip-backward-symbolic")
        self.prev_btn.add_css_class("control-btn")
        self.prev_btn.connect("clicked", lambda b: self.on_prev())
        ctrl_box.append(self.prev_btn)

        self.play_btn = Gtk.Button.new_from_icon_name("media-playback-start-symbolic")
        self.play_btn.add_css_class("control-btn")
        self.play_btn.add_css_class("play-btn")
        self.play_btn.connect("clicked", lambda b: self.on_play_pause())
        ctrl_box.append(self.play_btn)

        self.next_btn = Gtk.Button.new_from_icon_name("media-skip-forward-symbolic")
        self.next_btn.add_css_class("control-btn")
        self.next_btn.connect("clicked", lambda b: self.on_next())
        ctrl_box.append(self.next_btn)

        self.append(ctrl_box)

        # --- System HUD: Volume & Brightness ---
        hud_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        hud_box.set_hexpand(True)

        # Volume
        vol_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        vol_box.set_hexpand(True)
        vol_icon = Gtk.Image.new_from_icon_name("audio-volume-high-symbolic")
        vol_icon.add_css_class("hud-icon")
        vol_box.append(vol_icon)

        self.vol_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0.0, 100.0, 5.0)
        self.vol_scale.set_draw_value(False)
        self.vol_scale.set_hexpand(True)
        self.vol_scale.connect("value-changed", self._on_vol_changed)
        vol_box.append(self.vol_scale)
        hud_box.append(vol_box)

        # Brightness
        bright_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        bright_box.set_hexpand(True)
        bright_icon = Gtk.Image.new_from_icon_name("display-brightness-symbolic")
        bright_icon.add_css_class("hud-icon")
        bright_box.append(bright_icon)

        self.bright_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0.0, 100.0, 5.0)
        self.bright_scale.set_draw_value(False)
        self.bright_scale.set_hexpand(True)
        self.bright_scale.connect("value-changed", self._on_bright_changed)
        bright_box.append(self.bright_scale)
        hud_box.append(bright_box)

        self.append(hud_box)

    def update_media(self, track: TrackMetadata) -> None:
        self.title_label.set_text(track.title)
        self.artist_label.set_text(track.artist or "Unknown Artist")
        self.player_badge.set_text(track.player_name or "MPRIS")

        # Play/Pause Icon
        icon_name = "media-playback-pause-symbolic" if track.is_playing else "media-playback-start-symbolic"
        self.play_btn.set_icon_name(icon_name)

        # Artwork
        if track.local_art_path and os.path.isfile(track.local_art_path):
            try:
                self.art_picture.set_filename(track.local_art_path)
                self.art_stack.set_visible_child_name("picture")
            except Exception:
                self.art_stack.set_visible_child_name("fallback")
        else:
            self.art_stack.set_visible_child_name("fallback")

        # Progress
        if not self._seeking:
            self.progress_scale.set_range(0.0, max(1.0, track.duration_sec))
            self.progress_scale.set_value(track.position_sec)
            self.elapsed_label.set_text(format_time(track.position_sec))
            self.total_label.set_text(format_time(track.duration_sec))

    def update_lyrics(self, state: SyncLyricsState) -> None:
        if self._last_lyrics_index == state.current_index and self._last_lyrics_synced == state.is_synced:
            return
        self._last_lyrics_index = state.current_index
        self._last_lyrics_synced = state.is_synced

        if state.is_synced:
            self.lyric_prev_label.set_text(state.prev_line)
            self.lyric_active_label.set_text(state.current_line or "...")
            self.lyric_next_label.set_text(state.next_line)
        else:
            self.lyric_prev_label.set_text("")
            self.lyric_active_label.set_text(state.current_line or "No lyrics available")
            self.lyric_next_label.set_text("")

    def set_system_levels(self, volume: int, brightness: int) -> None:
        self.vol_scale.set_value(volume)
        self.bright_scale.set_value(brightness)

    def _on_scale_change(self, scale, scroll_type, value) -> bool:
        self.on_seek(value)
        return False

    def _on_vol_changed(self, scale) -> None:
        self.on_volume_change(int(scale.get_value()))

    def _on_bright_changed(self, scale) -> None:
        self.on_brightness_change(int(scale.get_value()))
