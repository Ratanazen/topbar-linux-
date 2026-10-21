"""
Ratana Dynamic Island — Network Backend
=======================================
Monitors network connection and disconnection events with strict privacy-preserving SSID handling.
"""

import asyncio
import logging
import re
import time
from typing import Any, Callable

from core.priority_manager import Priority
from core.state_manager import IslandState

log = logging.getLogger("ratana-island")


class NetworkBackend:
    def __init__(self, config: Any, caps: Any, on_transient_event: Callable[[IslandState], None]):
        self.config = config
        self.caps = caps
        self.on_transient_event = on_transient_event
        self.last_network_time: float = 0

    async def run_monitor(self):
        if not self.config.enable_network or not self.caps.has_nmcli:
            return

        cmd = ["nmcli", "monitor"]

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
                    decoded = line.decode("utf-8", errors="replace").strip()
                    if not decoded:
                        continue

                    # Debounce rapid network changes (0.5s)
                    now = time.time()
                    if now - self.last_network_time < 0.5:
                        continue
                    self.last_network_time = now

                    # Parse connection events
                    if "connected" in decoded.lower():
                        is_disconnect = "disconnected" in decoded.lower()
                        if is_disconnect:
                            icon = "󰤮"
                            title = "Disconnected"
                            sub = "Network Offline"
                            css = "network disconnected"
                        else:
                            icon = "󰤨"
                            title = "Connected"
                            css = "network"
                            # Handle SSID privacy
                            if self.config.network_ssid_privacy:
                                sub = "Wi-Fi Connected"
                            else:
                                match = re.search(r"connected to (\S+)", decoded)
                                sub = match.group(1) if match else "Online"

                        ev = IslandState(
                            source="network",
                            state="network",
                            priority=Priority.CONNECTIVITY,
                            icon=icon,
                            title=title,
                            subtitle=sub,
                            css_class=css,
                            duration=self.config.network_timeout_s
                        )
                        self.on_transient_event(ev)

                await proc.wait()
            except Exception as e:
                log.warning(f"Network monitor restart: {e}")
            await asyncio.sleep(2.0)
