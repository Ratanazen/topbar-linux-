"""Animation Controller and State Machine for Ratana Island."""

import math
import time
from enum import Enum
from typing import Callable, Optional
from gi.repository import GLib


class IslandState(Enum):
    IDLE = "idle"
    COMPACT = "compact"
    EXPANDING = "expanding"
    EXPANDED = "expanded"
    COLLAPSING = "collapsing"
    NOTIFICATION = "notification"
    MEDIA_CHANGED = "media_changed"


# Easing Functions
def ease_out_cubic(t: float) -> float:
    """Fast initial burst with soft deceleration."""
    t = max(0.0, min(1.0, float(t)))
    return 1.0 - math.pow(1.0 - t, 3)


def ease_in_out_cubic(t: float) -> float:
    """Smooth organic acceleration and deceleration."""
    t = max(0.0, min(1.0, float(t)))
    if t < 0.5:
        return 4.0 * t * t * t
    return 1.0 - math.pow(-2.0 * t + 2.0, 3) / 2.0


def ease_out_quad(t: float) -> float:
    t = max(0.0, min(1.0, float(t)))
    return 1.0 - (1.0 - t) * (1.0 - t)


def linear(t: float) -> float:
    return max(0.0, min(1.0, float(t)))


class AnimationController:
    """Frame-based animation controller with interruptible retargeting."""

    def __init__(
        self,
        on_frame: Callable[[int, int, float], None],
        on_complete: Optional[Callable[[IslandState], None]] = None,
        duration_ms: int = 280,
        reduced_motion: bool = False,
    ):
        self.on_frame = on_frame
        self.on_complete = on_complete
        self.duration_ms = duration_ms
        self.reduced_motion = reduced_motion

        self.state: IslandState = IslandState.COMPACT

        # Current interpolated values
        self.current_width: float = 280.0
        self.current_height: float = 38.0

        # Animation target values
        self.start_width: float = 280.0
        self.start_height: float = 38.0
        self.target_width: float = 280.0
        self.target_height: float = 38.0

        self.start_time: float = 0.0
        self.target_state: IslandState = IslandState.COMPACT
        self._timer_id: Optional[int] = None
        self._easing_func = ease_out_cubic

    def is_animating(self) -> bool:
        return self._timer_id is not None

    def animate_to(
        self,
        target_width: int,
        target_height: int,
        target_state: IslandState,
        duration_ms: Optional[int] = None,
        easing: Optional[Callable[[float], float]] = None,
    ) -> None:
        """Interruptibly retargets animation from current position to target."""
        dur = duration_ms if duration_ms is not None else self.duration_ms
        ease = easing if easing is not None else (
            ease_in_out_cubic if target_state in (IslandState.COLLAPSING, IslandState.COMPACT) else ease_out_cubic
        )

        # 1. Capture current position as new starting point (prevents jumping!)
        self.start_width = self.current_width
        self.start_height = self.current_height
        self.target_width = float(target_width)
        self.target_height = float(target_height)
        self.target_state = target_state
        self._easing_func = ease
        self.start_time = time.monotonic()

        # Update transitional state
        if target_state in (IslandState.EXPANDED, IslandState.NOTIFICATION):
            self.state = IslandState.EXPANDING
        elif target_state in (IslandState.COMPACT, IslandState.IDLE):
            self.state = IslandState.COLLAPSING
        else:
            self.state = target_state

        # If reduced motion is requested, finish immediately
        if self.reduced_motion or dur <= 0:
            self._cancel_timer()
            self.current_width = self.target_width
            self.current_height = self.target_height
            self.state = target_state
            self.on_frame(int(self.current_width), int(self.current_height), 1.0)
            if self.on_complete:
                self.on_complete(target_state)
            return

        # Start timer (16ms = ~60fps)
        self._cancel_timer()
        self._timer_id = GLib.timeout_add(16, self._tick, dur)

    def step(self, progress: float) -> None:
        """Manual step function used for deterministic unit testing."""
        p = max(0.0, min(1.0, float(progress)))
        eased = self._easing_func(p)
        self.current_width = self.start_width + (self.target_width - self.start_width) * eased
        self.current_height = self.start_height + (self.target_height - self.start_height) * eased
        self.on_frame(int(round(self.current_width)), int(round(self.current_height)), eased)

    def _tick(self, dur_ms: int) -> bool:
        now = time.monotonic()
        elapsed_ms = (now - self.start_time) * 1000.0
        progress = elapsed_ms / float(dur_ms)

        if progress >= 1.0:
            # Animation complete
            self.current_width = self.target_width
            self.current_height = self.target_height
            self.state = self.target_state
            self._timer_id = None
            self.on_frame(int(self.current_width), int(self.current_height), 1.0)
            if self.on_complete:
                self.on_complete(self.state)
            return False

        self.step(progress)
        return True

    def _cancel_timer(self) -> None:
        if self._timer_id is not None:
            GLib.source_remove(self._timer_id)
            self._timer_id = None

    def stop(self) -> None:
        self._cancel_timer()
