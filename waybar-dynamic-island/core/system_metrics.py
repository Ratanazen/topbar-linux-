"""
Ratana Dynamic Island — System Metrics Monitor
==============================================
Reads CPU and Memory utilization from /proc/stat and /proc/meminfo without spawning external processes.
Supplies live metrics for HyperOS quick settings and OriginOS widgets.
"""

import asyncio
import logging
from typing import Callable, Optional, Tuple

import shutil

log = logging.getLogger("ratana-island")


class SystemMetricsMonitor:
    def __init__(self, on_metrics_updated: Optional[Callable[..., None]] = None):
        self.on_metrics_updated = on_metrics_updated
        self.last_total: int = 0
        self.last_idle: int = 0
        self.cpu_pct: float = 0.0
        self.mem_pct: float = 0.0
        self.disk_used_gb: float = 0.0
        self.disk_total_gb: float = 0.0
        self.disk_pct: float = 0.0
        self.cpu_model: str = self._read_cpu_model()

    def _read_cpu_model(self) -> str:
        try:
            with open("/proc/cpuinfo", "r") as f:
                for line in f:
                    if "model name" in line:
                        name = line.split(":", 1)[1].strip()
                        # Shorten if long, e.g., "AMD Ryzen 5 7520U with Radeon Graphics" -> "Ryzen 5 7520U"
                        name = name.replace("AMD ", "").replace("Intel(R) Core(TM) ", "").replace(" with Radeon Graphics", "").replace(" CPU", "").strip()
                        return name
        except Exception:
            pass
        return "CPU"

    def read_metrics_sync(self) -> Tuple[float, float]:
        """Read instant CPU and RAM utilization percentages."""
        # Read CPU
        try:
            with open("/proc/stat", "r") as f:
                first_line = f.readline()
                parts = [int(p) for p in first_line.split()[1:8]]
                idle = parts[3] + parts[4]  # idle + iowait
                total = sum(parts)

                if self.last_total > 0:
                    diff_total = total - self.last_total
                    diff_idle = idle - self.last_idle
                    if diff_total > 0:
                        self.cpu_pct = round(max(0.0, min(100.0, (1.0 - diff_idle / diff_total) * 100.0)), 1)
                self.last_total = total
                self.last_idle = idle
        except Exception:
            pass

        # Read RAM
        try:
            total_kb = 0
            avail_kb = 0
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        total_kb = int(line.split()[1])
                    elif line.startswith("MemAvailable:"):
                        avail_kb = int(line.split()[1])
                    if total_kb > 0 and avail_kb > 0:
                        break
            if total_kb > 0:
                self.mem_pct = round(max(0.0, min(100.0, (1.0 - avail_kb / total_kb) * 100.0)), 1)
        except Exception:
            pass

        # Read Disk Usage
        try:
            total_b, used_b, free_b = shutil.disk_usage("/")
            self.disk_used_gb = round(used_b / (1024**3), 1)
            self.disk_total_gb = round(total_b / (1024**3), 1)
            if total_b > 0:
                self.disk_pct = round((used_b / total_b) * 100.0, 1)
        except Exception:
            pass

        return self.cpu_pct, self.mem_pct

    async def run_monitor(self, interval_s: float = 3.0):
        """Periodic background reader loop."""
        # Prime the CPU stats
        self.read_metrics_sync()
        await asyncio.sleep(0.5)

        while True:
            try:
                cpu, mem = self.read_metrics_sync()
                if self.on_metrics_updated:
                    self.on_metrics_updated(cpu, mem)
            except Exception as e:
                log.debug(f"Metrics monitor error: {e}")
            await asyncio.sleep(interval_s)
