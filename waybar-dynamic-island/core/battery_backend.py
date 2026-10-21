"""
Ratana Dynamic Island — Battery & Power Backend (Optimized)
===========================================================
Monitors battery capacity, charging status, and critical low-battery events
via direct kernel sysfs (/sys/class/power_supply) with zero-subprocess reads,
falling back to UPower only when sysfs is unavailable.
"""

import asyncio
import glob
import logging
import os
import re
from typing import Any, Callable, Optional, Tuple

from core.priority_manager import Priority
from core.state_manager import IslandState

log = logging.getLogger("ratana-island")


class BatteryBackend:
    def __init__(
        self,
        config: Any,
        caps: Any,
        on_transient_event: Callable[[IslandState], None],
        on_power_state_changed: Callable[[Optional[IslandState]], None]
    ):
        self.config = config
        self.caps = caps
        self.on_transient_event = on_transient_event
        self.on_power_state_changed = on_power_state_changed
        self.active_power_state: Optional[IslandState] = None

        # Check for direct sysfs battery device
        self.sysfs_cap: Optional[str] = None
        self.sysfs_stat: Optional[str] = None
        bats = glob.glob("/sys/class/power_supply/BAT*")
        if bats:
            b = bats[0]
            cap_p = os.path.join(b, "capacity")
            stat_p = os.path.join(b, "status")
            if os.path.exists(cap_p) and os.path.exists(stat_p):
                self.sysfs_cap = cap_p
                self.sysfs_stat = stat_p
                log.info(f"Battery: Using zero-subprocess sysfs at {b}")

    def read_battery_sync(self) -> Optional[Tuple[str, int]]:
        """Read state and percentage directly from kernel sysfs in <0.1ms."""
        if self.sysfs_cap and self.sysfs_stat:
            try:
                with open(self.sysfs_stat, "r") as f:
                    st = f.read().strip().lower()
                with open(self.sysfs_cap, "r") as f:
                    pct = int(f.read().strip())
                return st, pct
            except Exception:
                pass
        return None

    async def read_battery_async(self) -> Optional[Tuple[str, int]]:
        res = self.read_battery_sync()
        if res is not None:
            return res

        if self.caps.has_upower:
            try:
                proc = await asyncio.create_subprocess_exec(
                    "upower", "-i", "/org/freedesktop/UPower/devices/DisplayDevice",
                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL
                )
                stdout, _ = await proc.communicate()
                text = stdout.decode("utf-8", errors="replace")

                state_match = re.search(r"state:\s+([a-zA-Z-]+)", text)
                pct_match = re.search(r"percentage:\s+(\d+)%", text)
                if state_match and pct_match:
                    return state_match.group(1).lower(), int(pct_match.group(1))
            except Exception:
                pass
        return None

    async def run_monitor(self):
        if not self.config.enable_battery or (not self.sysfs_cap and not self.caps.has_upower):
            return

        last_state = ""
        prev_warning_state = False

        # Sleep interval adapts to performance profile
        is_low_res = getattr(self.config, "performance_profile", "balanced") == "low-resource"
        poll_interval = 8.0 if is_low_res else 4.0

        while True:
            try:
                data = await self.read_battery_async()
                if data:
                    current_state, pct = data
                    pct_norm = round(pct / 100.0, 3)

                    # 1. Transient on connect (charging)
                    if current_state == "charging" and last_state != "charging" and last_state != "":
                        ev = IslandState(
                            source="battery",
                            state="charging",
                            priority=Priority.CONNECTIVITY,
                            icon="󰂄",
                            title=f"Charging {pct}%",
                            progress_pct=pct_norm,
                            css_class="charging",
                            tooltip=f"Power: Connected\nBattery: {pct}%",
                            duration=self.config.charging_timeout_s
                        )
                        self.on_transient_event(ev)

                    # 2. Transient on disconnect (discharging)
                    if current_state in ("discharging", "not charging") and last_state == "charging":
                        ev = IslandState(
                            source="battery",
                            state="battery",
                            priority=Priority.CONNECTIVITY,
                            icon="󰁹",
                            title=f"On Battery {pct}%",
                            progress_pct=pct_norm,
                            css_class="battery",
                            tooltip=f"Power: Disconnected\nBattery: {pct}%",
                            duration=self.config.charging_timeout_s
                        )
                        self.on_transient_event(ev)

                    # 3. Persistent Low-Battery Warning
                    is_critical = (current_state in ("discharging", "not charging")) and (pct <= self.config.battery_low_threshold)
                    if is_critical and not prev_warning_state:
                        self.active_power_state = IslandState(
                            source="battery",
                            state="battery_warning",
                            priority=Priority.CRITICAL_POWER,
                            icon="󰂃",
                            title=f"Battery {pct}%",
                            subtitle="Plug in now",
                            progress_pct=pct_norm,
                            css_class="low-battery battery_warning",
                            tooltip=f"Battery critically low: {pct}%"
                        )
                        self.on_power_state_changed(self.active_power_state)
                        prev_warning_state = True
                    elif not is_critical and prev_warning_state:
                        self.active_power_state = None
                        self.on_power_state_changed(None)
                        prev_warning_state = False

                    last_state = current_state
            except Exception:
                pass
            await asyncio.sleep(poll_interval)
