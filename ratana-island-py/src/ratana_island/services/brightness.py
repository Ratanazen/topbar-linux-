"""Brightness management via brightnessctl."""

import logging
import shutil
import subprocess

logger = logging.getLogger("ratana_island.brightness")


class BrightnessService:
    def __init__(self):
        self._brightnessctl = shutil.which("brightnessctl")

    def get_brightness(self) -> int:
        if not self._brightnessctl:
            return 100
        try:
            res_cur = subprocess.run([self._brightnessctl, "get"], capture_output=True, text=True, timeout=1.0)
            res_max = subprocess.run([self._brightnessctl, "max"], capture_output=True, text=True, timeout=1.0)
            if res_cur.returncode == 0 and res_max.returncode == 0:
                cur = int(res_cur.stdout.strip())
                mx = int(res_max.stdout.strip())
                if mx > 0:
                    return int((cur / mx) * 100)
        except Exception as e:
            logger.debug(f"brightnessctl query failed: {e}")
        return 100

    def set_brightness(self, percent: int) -> None:
        if not self._brightnessctl:
            return
        target = max(5, min(100, int(percent)))
        try:
            subprocess.run([self._brightnessctl, "set", f"{target}%"], timeout=1.0)
        except Exception as e:
            logger.debug(f"brightnessctl set failed: {e}")

    def change_brightness(self, delta: int) -> None:
        if not self._brightnessctl:
            return
        sign = "+" if delta > 0 else "-"
        val = abs(delta)
        try:
            subprocess.run([self._brightnessctl, "set", f"{val}%{sign}"], timeout=1.0)
        except Exception as e:
            logger.debug(f"brightnessctl step failed: {e}")
