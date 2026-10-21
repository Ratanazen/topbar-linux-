"""Ratana Island Application and Service Orchestrator (GTK4)."""

import logging
import os
from pathlib import Path
from typing import Optional
from gi.repository import Gdk, Gio, GLib, Gtk
from ratana_island.config import AppConfig
from ratana_island.platform.capabilities import PlatformCapabilities, detect_capabilities
from ratana_island.platform.sway import SwayService
from ratana_island.providers.lrclib import LRCLibProvider
from ratana_island.services.audio import AudioService
from ratana_island.services.brightness import BrightnessService
from ratana_island.services.lyrics import LyricsEngine
from ratana_island.services.media import MediaService, TrackMetadata
from ratana_island.ui.island import IslandWindow
from ratana_island.utils.cache import CacheManager
from ratana_island.utils.ipc import IPCServer

logger = logging.getLogger("ratana_island.app")


class RatanaIslandApp(Gtk.Application):
    def __init__(self, config: Optional[AppConfig] = None):
        super().__init__(
            application_id="net.ratana.island",
            flags=Gio.ApplicationFlags.NON_UNIQUE,
        )
        self.config = config or AppConfig.load()
        self.caps: PlatformCapabilities = detect_capabilities()
        self.cache = CacheManager()

        # Core services
        self.audio_service = AudioService()
        self.brightness_service = BrightnessService()
        self.lrclib_provider = LRCLibProvider(self.cache)
        self.lyrics_engine = LyricsEngine()

        self.media_service = MediaService(
            cache_manager=self.cache,
            on_track_change=self._on_track_changed,
            on_position_tick=self._on_position_tick,
        )

        self.sway_service = SwayService(on_window_change=self._on_sway_window_changed)

        self.ipc_server: Optional[IPCServer] = None
        self.window: Optional[IslandWindow] = None
        self._current_track_key: str = ""

    def do_activate(self) -> None:
        if self.window:
            self.window.present()
            return

        # 1. Load Stylesheet
        self._load_css()

        # 2. Create Window
        self.window = IslandWindow(
            app=self,
            config=self.config,
            capabilities=self.caps,
            media_service=self.media_service,
            lyrics_engine=self.lyrics_engine,
            audio_service=self.audio_service,
            brightness_service=self.brightness_service,
        )
        self.window.present()

        # 3. Start IPC Server
        self.ipc_server = IPCServer(self._handle_ipc_command)
        if not self.ipc_server.start():
            logger.warning("Could not bind UNIX domain socket for IPC")

        # 4. Start Services
        self.media_service.start()
        self.sway_service.start_listener()

        # Initial Sway window check
        init_title, init_app = self.sway_service.get_focused_window()
        self.window.update_active_window(init_title, init_app)

        logger.info("Ratana Island application started successfully")

    def _load_css(self) -> None:
        css_file = Path(__file__).parent / "ui" / "styles.css"
        if not css_file.exists():
            return

        provider = Gtk.CssProvider()
        try:
            provider.load_from_path(str(css_file))
            display = Gdk.Display.get_default()
            if display:
                Gtk.StyleContext.add_provider_for_display(
                    display,
                    provider,
                    Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
                )
        except Exception as e:
            logger.warning(f"Failed to load CSS styles: {e}")

    def _handle_ipc_command(self, cmd: str) -> str:
        command = cmd.lower().strip()
        logger.debug(f"Received IPC command: {command}")

        if not self.window:
            return "error: window not initialized"

        if command in ("toggle", "--toggle"):
            self.window.toggle_expanded()
            return f"ok: expanded={self.window.is_expanded}"
        elif command in ("expand", "--expand"):
            self.window.set_expanded(True)
            return "ok: expanded"
        elif command in ("collapse", "--collapse"):
            self.window.set_expanded(False)
            return "ok: collapsed"
        elif command in ("quit", "--quit"):
            GLib.idle_add(self.quit)
            return "ok: quitting"
        elif command in ("status", "--status"):
            state = "expanded" if self.window.is_expanded else "compact"
            return f"status: {state}, media={self.media_service.current_track.title}"
        elif cmd.startswith("notify:") or cmd.startswith("--notify:"):
            parts = cmd.split(":", 2)
            title = parts[1] if len(parts) > 1 else "Notification"
            body = parts[2] if len(parts) > 2 else ""
            GLib.idle_add(self.window.show_notification, title, body, None)
            return f"ok: notification displayed ({title})"
        elif command == "ping":
            return "pong"
        else:
            return f"unknown command: {cmd}"

    def _on_track_changed(self, track: TrackMetadata) -> None:
        if not self.window:
            return

        self.window.update_media(track)

        track_key = f"{track.artist}_{track.title}"
        if track.has_media and track_key != self._current_track_key:
            self._current_track_key = track_key
            if self.config.media.enable_lyrics:
                # Fetch lyrics asynchronously
                self.lrclib_provider.fetch_lyrics_async(
                    title=track.title,
                    artist=track.artist,
                    album=track.album,
                    duration=track.duration_sec,
                    on_complete=self._on_lyrics_loaded,
                )
        elif not track.has_media:
            self._current_track_key = ""
            self.lyrics_engine.load_lrc(None)
            self.window.update_lyrics_position(0.0, 0.0)

    def _on_lyrics_loaded(self, lrc_content: Optional[str]) -> None:
        self.lyrics_engine.load_lrc(lrc_content)
        if self.window and self.media_service.current_track:
            pos = self.media_service.current_track.position_sec
            dur = self.media_service.current_track.duration_sec
            self.window.update_lyrics_position(pos, dur)

    def _on_position_tick(self, pos_sec: float, dur_sec: float) -> None:
        if self.window:
            self.window.update_lyrics_position(pos_sec, dur_sec)

    def _on_sway_window_changed(self, title: str, app_id: str) -> None:
        if self.window:
            self.window.update_active_window(title, app_id)

    def do_shutdown(self) -> None:
        logger.info("Shutting down Ratana Island...")
        if self.ipc_server:
            self.ipc_server.stop()
        if self.window:
            self.window.stop()
        self.media_service.stop()
        self.sway_service.stop()
        Gtk.Application.do_shutdown(self)
