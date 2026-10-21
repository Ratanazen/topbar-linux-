"""
Ratana Dynamic Island — Recording Backend (Optimized)
=====================================================
Monitors active screen recording utilities (wf-recorder, obs, wl-screenrec)
and maintains persistent high-priority recording indicators with change-only emissions.
"""

import asyncio
import logging
import shutil
from typing import Any, Callable, Optional

from core.priority_manager import Priority
from core.state_manager import IslandState

log = logging.getLogger("ratana-island")


class RecordingBackend:
    def __init__(self, config: Any, on_state_changed: Callable[[Optional[IslandState]], None]):
        self.config = config
        self.on_state_changed = on_state_changed
        self.active_recording_state: Optional[IslandState] = None
        self.last_recorder: Optional[str] = None

    async def run_monitor(self):
        if not self.config.enable_recording:
            return

        is_low_res = getattr(self.config, "performance_profile", "balanced") == "low-resource"
        poll_interval = 4.0 if is_low_res else 2.0

        while True:
            try:
                active_recorder = None
                for rec in self.config.recorders:
                    if shutil.which(rec):
                        proc = await asyncio.create_subprocess_exec(
                            "pgrep", "-x", rec,
                            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL
                        )
                        ret = await proc.wait()
                        if ret == 0:
                            active_recorder = rec
                            break

                # Emit change ONLY when recorder status changes!
                if active_recorder != self.last_recorder:
                    self.last_recorder = active_recorder
                    if active_recorder:
                        self.active_recording_state = IslandState(
                            source="recording",
                            state="recording",
                            priority=Priority.RECORDING,
                            icon="󰻃",
                            title="REC",
                            subtitle=active_recorder,
                            css_class="recording",
                            tooltip=f"Screen recording confirmed via {active_recorder}!"
                        )
                    else:
                        self.active_recording_state = None
                    self.on_state_changed(self.active_recording_state)
            except Exception:
                pass
            await asyncio.sleep(poll_interval)
