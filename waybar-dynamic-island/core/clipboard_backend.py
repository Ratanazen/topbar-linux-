"""
Ratana Dynamic Island — Privacy-First Clipboard Backend
=======================================================
Monitors clipboard updates without reading, logging, or transmitting content.
Zero clipboard content leakage guarantee.
"""

import asyncio
import logging
import time
from typing import Any, Callable

from core.priority_manager import Priority
from core.state_manager import IslandState

log = logging.getLogger("ratana-island")


class ClipboardBackend:
    def __init__(self, config: Any, caps: Any, on_transient_event: Callable[[IslandState], None]):
        self.config = config
        self.caps = caps
        self.on_transient_event = on_transient_event
        self.last_clipboard_time: float = 0

    async def run_monitor(self):
        """Monitors clipboard changes without reading, storing, or logging contents."""
        if not self.config.enable_clipboard or not self.caps.has_wl_paste:
            return

        # Note: wl-paste -w executes a dummy echo. Contents are NEVER read!
        cmd = ["wl-paste", "--watch", "echo", "change"]

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
                    now = time.time()
                    if now - self.last_clipboard_time < 0.5:  # Debounce
                        continue
                    self.last_clipboard_time = now

                    # Emit strictly generic privacy-safe indicator
                    ev = IslandState(
                        source="clipboard",
                        state="clipboard",
                        priority=Priority.CONNECTIVITY,
                        icon="󰅍",
                        title="Copied",
                        subtitle="Clipboard updated",
                        css_class="clipboard",
                        duration=self.config.clipboard_timeout_s
                    )
                    self.on_transient_event(ev)

                await proc.wait()
            except Exception as e:
                log.warning(f"Clipboard watcher restart: {e}")
            await asyncio.sleep(2.0)
