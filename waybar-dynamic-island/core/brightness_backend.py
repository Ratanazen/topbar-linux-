"""
Ratana Dynamic Island — Brightness Backend (Optimized)
======================================================
Monitors screen backlight levels via direct kernel sysfs (/sys/class/backlight)
with zero-subprocess reads, falling back to brightnessctl when sysfs is unavailable.
"""

import asyncio
import glob
import logging
import os
from typing import Any, Callable, Optional

from core.priority_manager import Priority
from core.state_manager import IslandState, build_progress_bar

log = logging.getLogger("ratana-island")


class BrightnessBackend:
    def __init__(self, config: Any, caps: Any, on_transient_event: Callable[[IslandState], None]):
        self.config = config
        self.caps = caps
        self.on_transient_event = on_transient_event

        # Locate direct sysfs backlight path for zero-subprocess polling
        self.sysfs_curr: Optional[str] = None
        self.sysfs_max: Optional[str] = None
        self.max_brightness: int = 100

        backlights = glob.glob("/sys/class/backlight/*")
        if backlights:
            bl = backlights[0]
            curr_p = os.path.join(bl, "brightness")
            max_p = os.path.join(bl, "max_brightness")
            if os.path.exists(curr_p) and os.path.exists(max_p):
                try:
                    with open(max_p, "r") as f:
                        max_val = int(f.read().strip())
                        if max_val > 0:
                            self.sysfs_curr = curr_p
                            self.sysfs_max = max_p
                            self.max_brightness = max_val
                            log.info(f"Brightness: Using zero-subprocess sysfs at {bl} (max={max_val})")
                except Exception as e:
                    log.warning(f"Failed to read sysfs max_brightness: {e}")

    def read_percent_sync(self) -> Optional[int]:
        """Read brightness percentage directly from kernel sysfs in <0.2ms without subprocesses."""
        if self.sysfs_curr:
            try:
                with open(self.sysfs_curr, "r") as f:
                    curr = int(f.read().strip())
                return int(round((curr / self.max_brightness) * 100.0))
            except Exception:
                pass
        return None

    async def read_percent_async(self) -> Optional[int]:
        pct = self.read_percent_sync()
        if pct is not None:
            return pct

        # Fallback to brightnessctl subprocess if sysfs is not accessible
        if self.caps.has_brightnessctl:
            try:
                proc = await asyncio.create_subprocess_exec(
                    "brightnessctl", "-m",
                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL
                )
                stdout, _ = await proc.communicate()
                line = stdout.decode("utf-8", errors="replace").strip()
                if line:
                    parts = line.split(",")
                    if len(parts) >= 4:
                        return int(parts[3].replace("%", "").strip())
            except Exception:
                pass
        return None

    async def run_monitor(self):
        if not self.config.enable_brightness or (not self.sysfs_curr and not self.caps.has_brightnessctl):
            return

        last_percent = -1
        # Adaptive interval based on profile
        is_low_res = getattr(self.config, "performance_profile", "balanced") == "low-resource"
        poll_interval = 1.5 if is_low_res else 0.8

        while True:
            try:
                percent = await self.read_percent_async()
                if percent is not None:
                    if last_percent != -1 and percent != last_percent:
                        if percent < 35:
                            icon = "󰃞"
                        elif percent < 70:
                            icon = "󰃟"
                        else:
                            icon = "󰃠"

                        bar = build_progress_bar(percent, total_blocks=5)
                        state = IslandState(
                            source="brightness",
                            state="brightness",
                            priority=Priority.SLIDER,
                            icon=icon,
                            title=f"{percent}%",
                            progress_bar=bar,
                            progress_pct=round(percent / 100.0, 3),
                            css_class="brightness",
                            tooltip=f"Brightness: {percent}%",
                            duration=self.config.brightness_timeout_s
                        )
                        self.on_transient_event(state)
                    last_percent = percent
            except Exception:
                pass
            await asyncio.sleep(poll_interval)

    async def brightness_up(self, step: str = "5%"):
        if self.caps.has_brightnessctl:
            proc = await asyncio.create_subprocess_exec("brightnessctl", "set", f"+{step}")
            await proc.wait()
            # Fast update
            await self._trigger_fast_feedback()

    async def brightness_down(self, step: str = "5%"):
        if self.caps.has_brightnessctl:
            proc = await asyncio.create_subprocess_exec("brightnessctl", "set", f"{step}-")
            await proc.wait()
            # Fast update
            await self._trigger_fast_feedback()

    async def _trigger_fast_feedback(self):
        pct = await self.read_percent_async()
        if pct is not None:
            icon = "󰃞" if pct < 35 else ("󰃟" if pct < 70 else "󰃠")
            bar = build_progress_bar(pct, total_blocks=5)
            state = IslandState(
                source="brightness",
                state="brightness",
                priority=Priority.SLIDER,
                icon=icon,
                title=f"{pct}%",
                progress_bar=bar,
                progress_pct=round(pct / 100.0, 3),
                css_class="brightness",
                tooltip=f"Brightness: {pct}%",
                duration=self.config.brightness_timeout_s
            )
            self.on_transient_event(state)
