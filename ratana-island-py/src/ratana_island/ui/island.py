"""Main Island Window with GTK4, LayerShell, and iPhone-style animations."""

import logging
from typing import Optional
from gi.repository import Gdk, GLib, Gtk
from ratana_island.config import AppConfig
from ratana_island.platform.capabilities import PlatformCapabilities
from ratana_island.services.audio import AudioService
from ratana_island.services.brightness import BrightnessService
from ratana_island.services.lyrics import LyricsEngine
from ratana_island.services.media import MediaService, TrackMetadata
from ratana_island.ui.animations import AnimationController, IslandState, ease_in_out_cubic, ease_out_cubic
from ratana_island.ui.compact_view import CompactView
from ratana_island.ui.expanded_view import ExpandedView
from ratana_island.ui.notification_view import NotificationView

logger = logging.getLogger("ratana_island.window")

# Attempt Gtk4LayerShell import
try:
    import gi
    gi.require_version("Gtk4LayerShell", "1.0")
    from gi.repository import Gtk4LayerShell
    HAS_LAYER_SHELL = True
except Exception:
    HAS_LAYER_SHELL = False


class IslandWindow(Gtk.ApplicationWindow):
    def __init__(
        self,
        app: Gtk.Application,
        config: AppConfig,
        capabilities: PlatformCapabilities,
        media_service: MediaService,
        lyrics_engine: LyricsEngine,
        audio_service: AudioService,
        brightness_service: BrightnessService,
    ):
        super().__init__(application=app)
        self.config = config
        self.caps = capabilities
        self.media_service = media_service
        self.lyrics_engine = lyrics_engine
        self.audio_service = audio_service
        self.brightness_service = brightness_service

        self._visualizer_timer_id: Optional[int] = None
        self._notif_timeout_id: Optional[int] = None
        self._prev_state_before_notif: IslandState = IslandState.COMPACT

        # Window properties
        self.set_title("Ratana Island")
        self.add_css_class("background")

        # Configure Layer Shell
        self._setup_layer_shell()

        # Root layout with top alignment and center anchoring
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        root.set_name("island-root")
        root.set_halign(Gtk.Align.CENTER)
        root.set_valign(Gtk.Align.START)
        self.set_child(root)

        # Capsule Container
        self.capsule = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.capsule.set_name("island-capsule")
        self.capsule.set_size_request(
            self.config.dimensions.compact_width,
            self.config.dimensions.compact_height,
        )
        root.append(self.capsule)

        # Content Stack: Compact vs Expanded vs Notification
        self.stack = Gtk.Stack()
        self.stack.set_hhomogeneous(False)
        self.stack.set_vhomogeneous(False)
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_transition_duration(self.config.appearance.animation_duration_ms)

        # 1. Compact View
        self.compact_view = CompactView(self.config)
        self.stack.add_named(self.compact_view, "compact")

        # 2. Expanded View
        self.expanded_view = ExpandedView(
            config=self.config,
            on_play_pause=self._on_play_pause,
            on_next=self._on_next,
            on_prev=self._on_prev,
            on_seek=self._on_seek,
            on_volume_change=self._on_volume_change,
            on_brightness_change=self._on_brightness_change,
        )
        self.stack.add_named(self.expanded_view, "expanded")

        # 3. Notification View
        self.notification_view = NotificationView()
        self.stack.add_named(self.notification_view, "notification")

        self.stack.set_visible_child_name("compact")
        self.capsule.append(self.stack)

        # Animation Controller
        self.animator = AnimationController(
            on_frame=self._on_anim_frame,
            on_complete=self._on_anim_complete,
            duration_ms=self.config.appearance.animation_duration_ms,
            reduced_motion=self.config.appearance.reduced_motion,
        )
        self.animator.current_width = float(self.config.dimensions.compact_width)
        self.animator.current_height = float(self.config.dimensions.compact_height)

        # Gestures and Event Controllers
        self._setup_interactions()

        # Start visualizer heartbeat
        self._start_visualizer()

    @property
    def is_expanded(self) -> bool:
        return self.animator.state in (IslandState.EXPANDED, IslandState.EXPANDING)

    def _setup_layer_shell(self) -> None:
        if HAS_LAYER_SHELL and self.caps.is_wayland:
            try:
                Gtk4LayerShell.init_for_window(self)
                Gtk4LayerShell.set_layer(self, Gtk4LayerShell.Layer.OVERLAY)
                Gtk4LayerShell.set_namespace(self, "ratana-island")
                Gtk4LayerShell.set_anchor(self, Gtk4LayerShell.Edge.TOP, True)
                Gtk4LayerShell.set_margin(
                    self, Gtk4LayerShell.Edge.TOP, self.config.dimensions.margin_top
                )
                Gtk4LayerShell.set_exclusive_zone(self, 0)
                logger.info("GTK4 LayerShell initialized successfully (OVERLAY, exclusive=0)")
            except Exception as e:
                logger.warning(f"Failed to configure LayerShell: {e}")
        else:
            logger.info("Running in standard window mode (LayerShell not active)")

    def _setup_interactions(self) -> None:
        # Click gesture with single and double click support
        click = Gtk.GestureClick.new()
        click.connect("pressed", self._on_capsule_clicked)
        self.capsule.add_controller(click)

        # Scroll gesture to adjust volume
        scroll = Gtk.EventControllerScroll.new(
            Gtk.EventControllerScrollFlags.VERTICAL | Gtk.EventControllerScrollFlags.DISCRETE
        )
        scroll.connect("scroll", self._on_scroll_volume)
        self.capsule.add_controller(scroll)

        # Escape key to collapse
        key_ctrl = Gtk.EventControllerKey.new()
        key_ctrl.connect("key-pressed", self._on_key_pressed)
        self.add_controller(key_ctrl)

    def _on_capsule_clicked(self, gesture, n_press, x, y) -> None:
        # Double click handling
        if n_press == 2:
            action = self.config.appearance.double_click_action
            if action == "play_pause":
                self.media_service.play_pause()
                return
            elif action == "toggle":
                self.toggle_expanded()
                return

        # If clicked in notification view, collapse immediately
        if self.animator.state == IslandState.NOTIFICATION:
            self._dismiss_notification()
            return

        # Don't toggle collapse if clicked inside expanded controls / sliders
        if self.is_expanded and y > 60:
            return

        self.toggle_expanded()

    def _on_scroll_volume(self, controller, dx, dy) -> bool:
        delta = -self.config.system.volume_step if dy > 0 else self.config.system.volume_step
        self.audio_service.change_volume(delta)
        vol, _ = self.audio_service.get_volume_and_mute()
        self.expanded_view.vol_scale.set_value(vol)
        return True

    def _on_key_pressed(self, controller, keyval, keycode, state) -> bool:
        if keyval == Gdk.KEY_Escape:
            if self.animator.state == IslandState.NOTIFICATION:
                self._dismiss_notification()
                return True
            elif self.is_expanded:
                self.set_expanded(False)
                return True
        return False

    def toggle_expanded(self) -> None:
        self.set_expanded(not self.is_expanded)

    def set_expanded(self, expanded: bool) -> None:
        target_state = IslandState.EXPANDED if expanded else IslandState.COMPACT
        target_w = self.config.dimensions.expanded_width if expanded else self.config.dimensions.compact_width
        target_h = self.config.dimensions.expanded_height if expanded else self.config.dimensions.compact_height

        # Update styling classes
        if expanded:
            self.capsule.add_css_class("expanded")
            self.stack.set_visible_child_name("expanded")
            vol, _ = self.audio_service.get_volume_and_mute()
            bright = self.brightness_service.get_brightness()
            self.expanded_view.set_system_levels(vol, bright)
        else:
            self.capsule.remove_css_class("expanded")
            self.stack.set_visible_child_name("compact")

        # Smooth interruptible animation
        self.animator.animate_to(
            target_width=target_w,
            target_height=target_h,
            target_state=target_state,
        )

    def show_notification(self, title: str, body: str = "", icon_name: Optional[str] = None) -> None:
        if not self.config.appearance.notification_expansion:
            return

        # Cancel any previous notification timeout
        if self._notif_timeout_id is not None:
            GLib.source_remove(self._notif_timeout_id)
            self._notif_timeout_id = None

        if self.animator.state != IslandState.NOTIFICATION:
            self._prev_state_before_notif = IslandState.EXPANDED if self.is_expanded else IslandState.COMPACT

        self.notification_view.set_notification(title, body, icon_name)
        self.stack.set_visible_child_name("notification")
        self.capsule.remove_css_class("expanded")

        # Animate smoothly to notification capsule size
        self.animator.animate_to(
            target_width=self.config.dimensions.notification_width,
            target_height=self.config.dimensions.notification_height,
            target_state=IslandState.NOTIFICATION,
            duration_ms=240,
        )

        # Set auto-collapse timer
        timeout_sec = self.config.system.notification_timeout_sec
        self._notif_timeout_id = GLib.timeout_add_seconds(timeout_sec, self._on_notification_timeout)

    def _on_notification_timeout(self) -> bool:
        self._notif_timeout_id = None
        self._dismiss_notification()
        return False

    def _dismiss_notification(self) -> None:
        if self._notif_timeout_id is not None:
            GLib.source_remove(self._notif_timeout_id)
            self._notif_timeout_id = None

        restore_expanded = (self._prev_state_before_notif == IslandState.EXPANDED)
        self.set_expanded(restore_expanded)

    def _on_anim_frame(self, width: int, height: int, progress: float) -> None:
        self.capsule.set_size_request(width, height)

    def _on_anim_complete(self, final_state: IslandState) -> None:
        if final_state == IslandState.COMPACT:
            self.stack.set_visible_child_name("compact")
        elif final_state == IslandState.EXPANDED:
            self.stack.set_visible_child_name("expanded")
        elif final_state == IslandState.NOTIFICATION:
            self.stack.set_visible_child_name("notification")

    def update_media(self, track: TrackMetadata) -> None:
        self.compact_view.update_media(track)
        self.expanded_view.update_media(track)

        # Automatic media expansion if enabled
        if track.is_playing and self.config.media.auto_media_expand and not self.is_expanded:
            self.set_expanded(True)

    def update_lyrics_position(self, pos_sec: float, duration_sec: float) -> None:
        state = self.lyrics_engine.get_state_at(pos_sec)
        self.expanded_view.update_lyrics(state)
        # Update progress label and scale smoothly
        if not self.expanded_view._seeking:
            self.expanded_view.progress_scale.set_value(pos_sec)
            self.expanded_view.elapsed_label.set_text(
                f"{int(pos_sec)//60:02d}:{int(pos_sec)%60:02d}"
            )

    def update_active_window(self, title: str, app_id: str) -> None:
        if not self.media_service.current_track.has_media:
            self.compact_view.update_window(title, app_id)

    def _start_visualizer(self) -> None:
        if not self.config.media.show_visualizer or self.config.appearance.cpu_friendly:
            return

        def tick():
            # Only tick if media is actually playing and visible
            is_playing = self.media_service.current_track.is_playing
            if is_playing and not self.is_expanded:
                self.compact_view.animate_visualizer(True)
            elif not is_playing:
                self.compact_view.animate_visualizer(False)
            return True

        self._visualizer_timer_id = GLib.timeout_add(140, tick)

    # Actions from expanded view
    def _on_play_pause(self) -> None:
        self.media_service.play_pause()

    def _on_next(self) -> None:
        self.media_service.next()

    def _on_prev(self) -> None:
        self.media_service.previous()

    def _on_seek(self, target_pos: float) -> None:
        self.media_service.seek(target_pos)

    def _on_volume_change(self, val: int) -> None:
        self.audio_service.set_volume(val)

    def _on_brightness_change(self, val: int) -> None:
        self.brightness_service.set_brightness(val)

    def stop(self) -> None:
        if self._notif_timeout_id is not None:
            GLib.source_remove(self._notif_timeout_id)
            self._notif_timeout_id = None
        if self._visualizer_timer_id is not None:
            GLib.source_remove(self._visualizer_timer_id)
            self._visualizer_timer_id = None
        self.animator.stop()
