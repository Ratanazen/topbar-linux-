"""
Ratana Dynamic Island — Audio Backend
=====================================
Monitors volume and mute status via pactl or wpctl, handles volume controls,
and emits transient feedback states.
"""

import asyncio
import logging
import re
import time
from typing import Any, Callable

from core.priority_manager import Priority
from core.state_manager import IslandState, build_progress_bar

log = logging.getLogger("ratana-island")


class AudioBackend:
    def __init__(self, config: Any, caps: Any, on_transient_event: Callable[[IslandState], None]):
        self.config = config
        self.caps = caps
        self.on_transient_event = on_transient_event
        self.last_volume_time: float = 0

    async def run_monitor(self):
        if not self.config.enable_volume:
            return

        if self.caps.has_pactl:
            await self._run_pactl_subscribe()
        elif self.caps.has_wpctl:
            await self._run_wpctl_poll_fallback()

    async def _run_pactl_subscribe(self):
        cmd = ["pactl", "subscribe"]
        while True:
            try:
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.DEVNULL
                )

                while True:
                    line = await proc.stdout.readline()
                    if not line:
                        break
                    decoded = line.decode("utf-8", errors="replace")
                    if "sink" in decoded or "server" in decoded:
                        now = time.time()
                        if now - self.last_volume_time > 0.04:  # 40ms debounce
                            self.last_volume_time = now
                            await self._fetch_and_post_volume_pactl()

                await proc.wait()
            except Exception as e:
                log.warning(f"pactl subscribe restart: {e}")
            await asyncio.sleep(2.0)

    async def _fetch_and_post_volume_pactl(self):
        try:
            p_vol = await asyncio.create_subprocess_exec(
                "pactl", "get-sink-volume", "@DEFAULT_SINK@",
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL
            )
            vol_out, _ = await p_vol.communicate()

            p_mute = await asyncio.create_subprocess_exec(
                "pactl", "get-sink-mute", "@DEFAULT_SINK@",
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL
            )
            mute_out, _ = await p_mute.communicate()

            vol_text = vol_out.decode("utf-8", errors="replace")
            mute_text = mute_out.decode("utf-8", errors="replace")

            match = re.search(r"(\d+)%", vol_text)
            percent = int(match.group(1)) if match else 50
            is_muted = "yes" in mute_text.lower()
            self._post_volume_state(percent, is_muted)
        except Exception:
            pass

    async def _run_wpctl_poll_fallback(self):
        last_vol = -1
        last_mute = False

        while True:
            try:
                proc = await asyncio.create_subprocess_exec(
                    "wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@",
                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL
                )
                stdout, _ = await proc.communicate()
                line = stdout.decode("utf-8", errors="replace").strip()
                match = re.search(r"Volume:\s+([0-9.]+)", line)
                if match:
                    percent = int(round(float(match.group(1)) * 100))
                    is_muted = "[MUTED]" in line
                    if percent != last_vol or is_muted != last_mute:
                        if last_vol != -1:
                            self._post_volume_state(percent, is_muted)
                        last_vol = percent
                        last_mute = is_muted
            except Exception:
                pass
            await asyncio.sleep(0.35)

    def _post_volume_state(self, percent: int, is_muted: bool):
        if is_muted or percent == 0:
            icon = "󰝟"
            css = "volume muted"
        elif percent < 30:
            icon = "󰕿"
            css = "volume"
        elif percent < 70:
            icon = "󰖀"
            css = "volume"
        else:
            icon = "󰕾"
            css = "volume"

        bar = build_progress_bar(percent, total_blocks=5)
        state = IslandState(
            source="volume",
            state="volume",
            priority=Priority.SLIDER,
            icon=icon,
            title="Muted" if is_muted else f"{percent}%",
            progress_bar="" if is_muted else bar,
            progress_pct=0.0 if is_muted else round(percent / 100.0, 3),
            css_class=css,
            tooltip=f"Audio: {'Muted' if is_muted else f'{percent}%'}",
            duration=self.config.volume_timeout_s
        )
        self.on_transient_event(state)

    async def volume_up(self, step: str = "2%"):
        if self.caps.has_pactl:
            await asyncio.create_subprocess_exec("pactl", "set-sink-volume", "@DEFAULT_SINK@", f"+{step}")
        elif self.caps.has_wpctl:
            await asyncio.create_subprocess_exec("wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", f"{step}+")

    async def volume_down(self, step: str = "2%"):
        if self.caps.has_pactl:
            await asyncio.create_subprocess_exec("pactl", "set-sink-volume", "@DEFAULT_SINK@", f"-{step}")
        elif self.caps.has_wpctl:
            await asyncio.create_subprocess_exec("wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", f"{step}-")

    async def volume_mute(self):
        if self.caps.has_pactl:
            await asyncio.create_subprocess_exec("pactl", "set-sink-mute", "@DEFAULT_SINK@", "toggle")
        elif self.caps.has_wpctl:
            await asyncio.create_subprocess_exec("wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "toggle")
