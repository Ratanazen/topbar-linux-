"""Compact pill view for Ratana Island (GTK4)."""

import os
from typing import Optional
import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, GdkPixbuf, Gtk, Pango
from ratana_island.config import AppConfig
from ratana_island.services.media import TrackMetadata


class CompactView(Gtk.Box):
    def __init__(self, config: AppConfig):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.config = config
        self.add_css_class("compact-box")

        # Fixed height for pill alignment
        self.set_valign(Gtk.Align.CENTER)
        self.set_halign(Gtk.Align.CENTER)

        # 1. Left Icon / Mini Artwork
        self.icon_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.icon_box.set_valign(Gtk.Align.CENTER)

        self.art_picture = Gtk.Picture()
        self.art_picture.set_size_request(24, 24)
        self.art_picture.set_can_shrink(True)
        self.art_picture.add_css_class("album-art-compact")
        self.art_picture.set_visible(False)

        self.fallback_icon = Gtk.Image.new_from_icon_name("audio-x-generic-symbolic")
        self.fallback_icon.set_icon_size(Gtk.IconSize.NORMAL)
        self.fallback_icon.set_pixel_size(18)
        self.fallback_icon.add_css_class("hud-icon")

        self.icon_box.append(self.art_picture)
        self.icon_box.append(self.fallback_icon)
        self.append(self.icon_box)

        # 2. Center Text Label
        self.title_label = Gtk.Label(label="Desktop")
        self.title_label.add_css_class("pill-title")
        self.title_label.set_ellipsize(Pango.EllipsizeMode.END)
        self.title_label.set_max_width_chars(self.config.media.max_title_length)
        self.title_label.set_valign(Gtk.Align.CENTER)
        self.append(self.title_label)

        # Optional Artist Label (subtle)
        self.artist_label = Gtk.Label(label="")
        self.artist_label.add_css_class("pill-artist")
        self.artist_label.set_ellipsize(Pango.EllipsizeMode.END)
        self.artist_label.set_max_width_chars(20)
        self.artist_label.set_valign(Gtk.Align.CENTER)
        self.artist_label.set_visible(False)
        self.append(self.artist_label)

        # 3. Right Status Indicator (Mini Visualizer Bars or Play Status)
        self.status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        self.status_box.set_valign(Gtk.Align.CENTER)

        # Three mini visualizer bars
        self.bar1 = Gtk.Box()
        self.bar1.add_css_class("visualizer-bar")
        self.bar1.set_size_request(3, 8)

        self.bar2 = Gtk.Box()
        self.bar2.add_css_class("visualizer-bar")
        self.bar2.set_size_request(3, 14)

        self.bar3 = Gtk.Box()
        self.bar3.add_css_class("visualizer-bar")
        self.bar3.set_size_request(3, 10)

        self.status_box.append(self.bar1)
        self.status_box.append(self.bar2)
        self.status_box.append(self.bar3)
        self.append(self.status_box)

        self._anim_step = 0

    def update_media(self, track: TrackMetadata) -> None:
        if track.has_media:
            # Show track info
            self.title_label.set_text(track.title)
            if track.artist:
                self.artist_label.set_text(f"• {track.artist}")
                self.artist_label.set_visible(True)
            else:
                self.artist_label.set_visible(False)

            # Update Artwork
            if track.local_art_path and os.path.isfile(track.local_art_path):
                try:
                    self.art_picture.set_filename(track.local_art_path)
                    self.art_picture.set_visible(True)
                    self.fallback_icon.set_visible(False)
                except Exception:
                    self.art_picture.set_visible(False)
                    self.fallback_icon.set_visible(True)
            else:
                self.art_picture.set_visible(False)
                self.fallback_icon.set_visible(True)

            self.status_box.set_visible(True)
        else:
            self.artist_label.set_visible(False)
            self.art_picture.set_visible(False)
            self.fallback_icon.set_visible(True)
            self.status_box.set_visible(False)

    def update_window(self, title: str, app_id: str) -> None:
        self.title_label.set_text(title or "Desktop")
        self.artist_label.set_visible(False)
        self.art_picture.set_visible(False)
        self.fallback_icon.set_visible(True)
        self.status_box.set_visible(False)

    def animate_visualizer(self, is_playing: bool) -> None:
        if not is_playing or not self.config.media.show_visualizer:
            self.bar1.set_size_request(3, 4)
            self.bar2.set_size_request(3, 4)
            self.bar3.set_size_request(3, 4)
            return

        self._anim_step = (self._anim_step + 1) % 6
        heights = [
            (6, 14, 10),
            (10, 8, 16),
            (14, 16, 8),
            (16, 12, 14),
            (12, 6, 12),
            (8, 10, 6),
        ]
        h1, h2, h3 = heights[self._anim_step]
        self.bar1.set_size_request(3, h1)
        self.bar2.set_size_request(3, h2)
        self.bar3.set_size_request(3, h3)
