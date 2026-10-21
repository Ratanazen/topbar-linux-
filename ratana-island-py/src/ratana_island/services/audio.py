"""Audio volume and mute management via pamixer / wpctl."""

import logging
import shutil
import subprocess
from typing import Tuple

logger = logging.getLogger("ratana_island.audio")


class AudioService:
    def __init__(self):
        self._pamixer = shutil.which("pamixer")
        self._wpctl = shutil.which("wpctl")

    def get_volume_and_mute(self) -> Tuple[int, bool]:
        """Returns (volume_percent, is_muted)."""
        if self._pamixer:
            try:
                res_vol = subprocess.run([self._pamixer, "--get-volume"], capture_output=True, text=True, timeout=1.0)
                res_mute = subprocess.run([self._pamixer, "--get-mute"], capture_output=True, text=True, timeout=1.0)
                vol = int(res_vol.stdout.strip()) if res_vol.returncode == 0 else 50
                is_muted = res_mute.stdout.strip().lower() == "true" if res_mute.returncode == 0 else False
                return (vol, is_muted)
            except Exception as e:
                logger.debug(f"pamixer query failed: {e}")

        if self._wpctl:
            try:
                res = subprocess.run([self._wpctl, "get-volume", "@DEFAULT_AUDIO_SINK@"], capture_output=True, text=True, timeout=1.0)
                if res.returncode == 0:
                    # Output format: "Volume: 0.65 [MUTED]"
                    parts = res.stdout.strip().split()
                    vol = int(float(parts[1]) * 100) if len(parts) > 1 else 50
                    is_muted = "[MUTED]" in res.stdout
                    return (vol, is_muted)
            except Exception as e:
                logger.debug(f"wpctl query failed: {e}")

        return (50, False)

    def set_volume(self, percent: int) -> None:
        target = max(0, min(100, int(percent)))
        if self._pamixer:
            try:
                subprocess.run([self._pamixer, "--set-volume", str(target)], timeout=1.0)
                return
            except Exception:
                pass
        if self._wpctl:
            try:
                frac = target / 100.0
                subprocess.run([self._wpctl, "set-volume", "@DEFAULT_AUDIO_SINK@", f"{frac:.2f}"], timeout=1.0)
            except Exception:
                pass

    def change_volume(self, delta: int) -> None:
        if self._pamixer:
            try:
                flag = "--increase" if delta > 0 else "--decrease"
                subprocess.run([self._pamixer, flag, str(abs(delta))], timeout=1.0)
                return
            except Exception:
                pass
        if self._wpctl:
            try:
                flag = f"{abs(delta)}%+" if delta > 0 else f"{abs(delta)}%-"
                subprocess.run([self._wpctl, "set-volume", "@DEFAULT_AUDIO_SINK@", flag], timeout=1.0)
            except Exception:
                pass

    def toggle_mute(self) -> None:
        if self._pamixer:
            try:
                subprocess.run([self._pamixer, "--toggle-mute"], timeout=1.0)
                return
            except Exception:
                pass
        if self._wpctl:
            try:
                subprocess.run([self._wpctl, "set-mute", "@DEFAULT_AUDIO_SINK@", "toggle"], timeout=1.0)
            except Exception:
                pass
