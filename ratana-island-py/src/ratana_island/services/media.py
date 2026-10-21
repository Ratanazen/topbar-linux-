"""MPRIS media service over D-Bus for tracking playback and controls."""

import logging
import os
import threading
import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional
import requests
from gi.repository import Gio, GLib
from ratana_island.utils.cache import CacheManager

logger = logging.getLogger("ratana_island.media")


@dataclass
class TrackMetadata:
    title: str = "Nothing Playing"
    artist: str = ""
    album: str = ""
    art_url: Optional[str] = None
    local_art_path: Optional[str] = None
    duration_sec: float = 0.0
    position_sec: float = 0.0
    status: str = "Stopped"  # "Playing", "Paused", "Stopped"
    player_name: str = ""
    player_bus: str = ""

    @property
    def is_playing(self) -> bool:
        return self.status.lower() == "playing"

    @property
    def has_media(self) -> bool:
        return self.status.lower() in ("playing", "paused") and bool(self.title) and self.title != "Nothing Playing"

    @property
    def progress_fraction(self) -> float:
        if self.duration_sec <= 0:
            return 0.0
        return max(0.0, min(1.0, self.position_sec / self.duration_sec))


class MediaService:
    def __init__(
        self,
        cache_manager: Optional[CacheManager] = None,
        on_track_change: Optional[Callable[[TrackMetadata], None]] = None,
        on_position_tick: Optional[Callable[[float, float], None]] = None,
    ):
        self.cache = cache_manager or CacheManager()
        self.on_track_change = on_track_change
        self.on_position_tick = on_position_tick

        self.current_track = TrackMetadata()
        self._bus: Optional[Gio.DBusConnection] = None
        self._prop_sub_id: Optional[int] = None
        self._name_sub_id: Optional[int] = None
        self._pos_timer_id: Optional[int] = None
        self._active_player_bus: Optional[str] = None
        self._tick_interval_ms: int = 250

    def start(self) -> None:
        try:
            self._bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)

            # 1. Listen for player appearance and disappearance
            self._name_sub_id = self._bus.signal_subscribe(
                "org.freedesktop.DBus",
                "org.freedesktop.DBus",
                "NameOwnerChanged",
                "/org/freedesktop/DBus",
                None,
                Gio.DBusSignalFlags.NONE,
                self._on_name_owner_changed,
            )

            # 2. Listen for MPRIS properties changed on all players
            self._prop_sub_id = self._bus.signal_subscribe(
                None,
                "org.freedesktop.DBus.Properties",
                "PropertiesChanged",
                "/org/mpris/MediaPlayer2",
                "org.mpris.MediaPlayer2.Player",
                Gio.DBusSignalFlags.NONE,
                self._on_properties_changed,
            )

            # 3. Initial scan for currently active players
            self._find_and_select_player()
        except Exception as e:
            logger.error(f"Failed to connect to D-Bus session bus: {e}")

    def _find_and_select_player(self) -> None:
        if not self._bus:
            return

        try:
            reply = self._bus.call_sync(
                "org.freedesktop.DBus",
                "/org/freedesktop/DBus",
                "org.freedesktop.DBus",
                "ListNames",
                None,
                GLib.VariantType("(as)"),
                Gio.DBusCallFlags.NONE,
                1000,
                None,
            )
            names = reply.unpack()[0]
            mpris_names = [n for n in names if n.startswith("org.mpris.MediaPlayer2.")]

            # Find first playing player, or first existing player
            selected = None
            for name in mpris_names:
                status = self._get_player_property(name, "PlaybackStatus")
                if status == "Playing":
                    selected = name
                    break
                elif selected is None and status == "Paused":
                    selected = name

            if selected:
                self._switch_to_player(selected)
            elif mpris_names:
                self._switch_to_player(mpris_names[0])
            else:
                self._reset_track()
        except Exception as e:
            logger.debug(f"Error listing D-Bus names: {e}")

    def _switch_to_player(self, bus_name: str) -> None:
        self._active_player_bus = bus_name
        self._update_player_state(bus_name)

    def _on_name_owner_changed(self, conn, sender, path, iface, signal, params) -> None:
        name, old_owner, new_owner = params.unpack()
        if not name.startswith("org.mpris.MediaPlayer2."):
            return

        if not new_owner and name == self._active_player_bus:
            # Current player exited, search for another player
            logger.info(f"Player {name} disconnected")
            self._find_and_select_player()
        elif new_owner and not old_owner:
            # New player appeared
            logger.info(f"New player appeared: {name}")
            self._find_and_select_player()

    def _on_properties_changed(self, conn, sender, path, iface, signal, params) -> None:
        iface_name, changed_props, invalidated = params.unpack()
        if iface_name != "org.mpris.MediaPlayer2.Player":
            return

        # sender is the unique name, e.g. :1.45
        self._update_player_state(sender)

    def _get_player_property(self, bus_name: str, prop_name: str):
        if not self._bus:
            return None
        try:
            val = self._bus.call_sync(
                bus_name,
                "/org/mpris/MediaPlayer2",
                "org.freedesktop.DBus.Properties",
                "Get",
                GLib.Variant("(ss)", ("org.mpris.MediaPlayer2.Player", prop_name)),
                GLib.VariantType("(v)"),
                Gio.DBusCallFlags.NONE,
                500,
                None,
            )
            return val.unpack()[0]
        except Exception:
            return None

    def _update_player_state(self, bus_name: str) -> None:
        if not self._bus:
            return

        try:
            all_props = self._bus.call_sync(
                bus_name,
                "/org/mpris/MediaPlayer2",
                "org.freedesktop.DBus.Properties",
                "GetAll",
                GLib.Variant("(s)", ("org.mpris.MediaPlayer2.Player",)),
                GLib.VariantType("(a{sv})"),
                Gio.DBusCallFlags.NONE,
                800,
                None,
            )
            props = all_props.unpack()[0]
        except Exception:
            return

        status = props.get("PlaybackStatus", "Stopped")
        metadata = props.get("Metadata", {})

        title = str(metadata.get("xesam:title", "Unknown Track"))
        artist_raw = metadata.get("xesam:artist", "")
        if isinstance(artist_raw, list):
            artist = ", ".join(str(a) for a in artist_raw if a)
        else:
            artist = str(artist_raw)

        album = str(metadata.get("xesam:album", ""))
        art_url = str(metadata.get("mpris:artUrl", ""))
        length_us = metadata.get("mpris:length", 0)
        duration_sec = float(length_us) / 1_000_000.0 if length_us else 0.0

        # Current position in microseconds
        position_us = props.get("Position", 0)
        if position_us == 0:
            # Query directly if not in GetAll
            p_val = self._get_player_property(bus_name, "Position")
            if p_val is not None:
                position_us = p_val
        pos_sec = float(position_us) / 1_000_000.0 if position_us else 0.0

        player_display = bus_name.replace("org.mpris.MediaPlayer2.", "").split(".")[0].capitalize()

        # Check artwork local resolution or download
        local_art = self._resolve_artwork(art_url)

        new_track = TrackMetadata(
            title=title,
            artist=artist,
            album=album,
            art_url=art_url,
            local_art_path=local_art,
            duration_sec=duration_sec,
            position_sec=pos_sec,
            status=status,
            player_name=player_display,
            player_bus=bus_name,
        )

        self._active_player_bus = bus_name
        self.current_track = new_track

        # Manage position ticker
        if new_track.is_playing:
            self._start_position_ticker()
        else:
            self._stop_position_ticker()

        if self.on_track_change:
            self.on_track_change(new_track)

    def _resolve_artwork(self, art_url: str) -> Optional[str]:
        if not art_url:
            return None

        # Check if it's already a local file path
        if art_url.startswith("file://"):
            parsed = urllib.parse.urlparse(art_url)
            local_path = urllib.parse.unquote(parsed.path)
            if os.path.exists(local_path):
                return local_path

        if os.path.exists(art_url):
            return art_url

        # Check if in cache
        cached = self.cache.get_cached_artwork(art_url)
        if cached:
            return str(cached)

        # Download asynchronously if http/https
        if art_url.startswith("http://") or art_url.startswith("https://"):
            dest_path = self.cache.get_artwork_path(art_url)
            self._download_art_async(art_url, dest_path)

        return None

    def _download_art_async(self, url: str, dest_path: Path) -> None:
        def worker():
            try:
                resp = requests.get(url, timeout=5.0)
                if resp.status_code == 200:
                    dest_path.write_bytes(resp.content)
                    if self.current_track and self.current_track.art_url == url:
                        self.current_track.local_art_path = str(dest_path)
                        if self.on_track_change:
                            GLib.idle_add(self.on_track_change, self.current_track)
            except Exception as e:
                logger.debug(f"Artwork download failed: {e}")

        threading.Thread(target=worker, daemon=True).start()

    def _start_position_ticker(self) -> None:
        if self._pos_timer_id is not None:
            return
        self._pos_timer_id = GLib.timeout_add(self._tick_interval_ms, self._on_pos_tick)

    def _stop_position_ticker(self) -> None:
        if self._pos_timer_id is not None:
            GLib.source_remove(self._pos_timer_id)
            self._pos_timer_id = None

    def _on_pos_tick(self) -> bool:
        if not self.current_track.is_playing:
            self._pos_timer_id = None
            return False

        # Advance position smoothly
        dt = float(self._tick_interval_ms) / 1000.0
        self.current_track.position_sec += dt
        if self.current_track.duration_sec > 0 and self.current_track.position_sec > self.current_track.duration_sec:
            self.current_track.position_sec = self.current_track.duration_sec

        if self.on_position_tick:
            self.on_position_tick(self.current_track.position_sec, self.current_track.duration_sec)

        return True

    def _reset_track(self) -> None:
        self._stop_position_ticker()
        self.current_track = TrackMetadata()
        self._active_player_bus = None
        if self.on_track_change:
            self.on_track_change(self.current_track)

    def play_pause(self) -> None:
        self._call_player_method("PlayPause")

    def next(self) -> None:
        self._call_player_method("Next")

    def previous(self) -> None:
        self._call_player_method("Previous")

    def seek(self, position_sec: float) -> None:
        if not self._bus or not self._active_player_bus:
            return
        try:
            # SetPosition takes (o, x) -> (trackId, position_in_microseconds)
            pos_us = int(position_sec * 1_000_000)
            self._bus.call_sync(
                self._active_player_bus,
                "/org/mpris/MediaPlayer2",
                "org.mpris.MediaPlayer2.Player",
                "SetPosition",
                GLib.Variant("(ox)", ("/not/used", pos_us)),
                None,
                Gio.DBusCallFlags.NONE,
                500,
                None,
            )
            self.current_track.position_sec = position_sec
        except Exception as e:
            logger.debug(f"Seek failed: {e}")

    def _call_player_method(self, method: str) -> None:
        if not self._bus or not self._active_player_bus:
            return
        try:
            self._bus.call_sync(
                self._active_player_bus,
                "/org/mpris/MediaPlayer2",
                "org.mpris.MediaPlayer2.Player",
                method,
                None,
                None,
                Gio.DBusCallFlags.NONE,
                800,
                None,
            )
        except Exception as e:
            logger.debug(f"MPRIS call {method} failed: {e}")

    def stop(self) -> None:
        self._stop_position_ticker()
        if self._bus:
            if self._prop_sub_id:
                self._bus.signal_unsubscribe(self._prop_sub_id)
                self._prop_sub_id = None
            if self._name_sub_id:
                self._bus.signal_unsubscribe(self._name_sub_id)
                self._name_sub_id = None
