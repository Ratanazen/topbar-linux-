"""
Ratana Dynamic Island — Timer & Pomodoro Manager
================================================
Handles countdown timers, stopwatch, and Pomodoro focus sessions.
"""

import re
import time
from typing import Optional, Tuple

from core.priority_manager import Priority
from core.state_manager import IslandState, build_progress_bar


def parse_duration(s: str) -> int:
    """Parse duration string such as '25m', '10s', '1h', or raw seconds into integer seconds."""
    match = re.match(r"^(\d+)([smhd]?)$", str(s).strip().lower())
    if not match:
        return 0
    val, unit = match.groups()
    val = int(val)
    if unit in ("s", ""):
        return val
    elif unit == "m":
        return val * 60
    elif unit == "h":
        return val * 3600
    elif unit == "d":
        return val * 86400
    return 0


class TimerManager:
    def __init__(self):
        self.timer_end_timestamp: Optional[float] = None
        self.timer_total_duration: float = 0.0
        self.timer_label: str = ""
        self.timer_paused: bool = False
        self.timer_remaining_on_pause: float = 0.0
        self.is_pomodoro: bool = False
        self.stopwatch_start_timestamp: Optional[float] = None
        self.active_state: Optional[IslandState] = None

    def start_timer(self, seconds: int, label: str = "Timer") -> Tuple[bool, str]:
        if seconds <= 0:
            return False, "Invalid duration (e.g. 25m, 10s, 1h)"

        self.timer_total_duration = float(seconds)
        self.timer_end_timestamp = time.time() + seconds
        self.timer_label = label
        self.timer_paused = False
        self.is_pomodoro = False
        self.stopwatch_start_timestamp = None

        mins = seconds // 60
        secs = seconds % 60
        self.active_state = IslandState(
            source="timer",
            state="timer",
            priority=Priority.TIMER,
            icon="󰔛",
            title=f"{mins:02d}:{secs:02d}",
            subtitle=f"({label})" if label else "",
            css_class="timer",
            tooltip=f"Active Timer: {mins:02d}:{secs:02d} remaining"
        )
        return True, f"Started {label} ({mins:02d}:{secs:02d})"

    def start_pomodoro(self, minutes: int = 25) -> Tuple[bool, str]:
        seconds = minutes * 60
        self.timer_total_duration = float(seconds)
        self.timer_end_timestamp = time.time() + seconds
        self.timer_label = "Focus"
        self.timer_paused = False
        self.is_pomodoro = True
        self.stopwatch_start_timestamp = None

        self.active_state = IslandState(
            source="timer",
            state="pomodoro",
            priority=Priority.TIMER,
            icon="󰔛",
            title=f"{minutes:02d}:00",
            subtitle="(Focus)",
            css_class="timer pomodoro",
            tooltip=f"Pomodoro Focus: {minutes:02d}:00 remaining"
        )
        return True, f"Started {minutes}m Pomodoro Focus"

    def start_stopwatch(self) -> Tuple[bool, str]:
        self.stopwatch_start_timestamp = time.time()
        self.timer_end_timestamp = None
        self.timer_paused = False
        self.is_pomodoro = False
        self.active_state = IslandState(
            source="timer",
            state="timer",
            priority=Priority.TIMER,
            icon="󱎫",
            title="00:00",
            css_class="timer stopwatch",
            tooltip="Stopwatch active"
        )
        return True, "Started Stopwatch"

    def pause(self) -> Tuple[bool, str]:
        if self.timer_end_timestamp and not self.timer_paused:
            self.timer_remaining_on_pause = max(0.0, self.timer_end_timestamp - time.time())
            self.timer_paused = True
            mins = int(self.timer_remaining_on_pause) // 60
            secs = int(self.timer_remaining_on_pause) % 60
            if self.active_state:
                self.active_state.subtitle = f"(Paused {mins:02d}:{secs:02d})"
            return True, "Paused timer"
        return False, "No active running timer"

    def resume(self) -> Tuple[bool, str]:
        if self.timer_paused:
            self.timer_end_timestamp = time.time() + self.timer_remaining_on_pause
            self.timer_paused = False
            return True, "Resumed timer"
        return False, "Timer is not paused"

    def stop(self) -> Tuple[bool, str]:
        self.timer_end_timestamp = None
        self.timer_paused = False
        self.stopwatch_start_timestamp = None
        self.is_pomodoro = False
        self.active_state = None
        return True, "Stopped active timer/stopwatch"

    def tick(self) -> Optional[IslandState]:
        """Called every second or update tick to refresh timer or stopwatch state."""
        # 1. Countdown / Pomodoro
        if self.timer_end_timestamp is not None:
            if self.timer_paused:
                rem = self.timer_remaining_on_pause
            else:
                rem = max(0.0, self.timer_end_timestamp - time.time())

            if rem <= 0.0 and not self.timer_paused:
                # Timer complete
                self.timer_end_timestamp = None
                label = self.timer_label or "Timer"
                self.active_state = None
                # Create completion alert
                return IslandState(
                    source="timer",
                    state="timer",
                    priority=Priority.URGENT_NOTIF,
                    icon="󰄬",
                    title="Time Up!",
                    subtitle=f"{label} finished",
                    css_class="timer complete",
                    tooltip=f"{label} finished!",
                    duration=5.0
                )

            mins = int(rem) // 60
            secs = int(rem) % 60
            state_name = "pomodoro" if self.is_pomodoro else "timer"
            css = "timer pomodoro" if self.is_pomodoro else "timer"

            progress_bar = ""
            progress_pct = 0.0
            if self.timer_total_duration > 0:
                elapsed = self.timer_total_duration - rem
                progress_pct = min(100.0, max(0.0, (elapsed / self.timer_total_duration) * 100.0))
                progress_bar = build_progress_bar(progress_pct, total_blocks=5)

            sub = "(Paused)" if self.timer_paused else (f"({self.timer_label})" if self.timer_label else "")

            self.active_state = IslandState(
                source="timer",
                state=state_name,
                priority=Priority.TIMER,
                icon="󰔛",
                title=f"{mins:02d}:{secs:02d}",
                subtitle=sub,
                progress_bar=progress_bar,
                progress_pct=progress_pct,
                css_class=css,
                tooltip=f"Timer: {mins:02d}:{secs:02d} remaining"
            )
            return self.active_state

        # 2. Stopwatch
        if self.stopwatch_start_timestamp is not None:
            elapsed = max(0.0, time.time() - self.stopwatch_start_timestamp)
            mins = int(elapsed) // 60
            secs = int(elapsed) % 60
            self.active_state = IslandState(
                source="timer",
                state="timer",
                priority=Priority.TIMER,
                icon="󱎫",
                title=f"{mins:02d}:{secs:02d}",
                subtitle="(Stopwatch)",
                css_class="timer stopwatch",
                tooltip=f"Stopwatch: {mins:02d}:{secs:02d} elapsed"
            )
            return self.active_state

        return None
