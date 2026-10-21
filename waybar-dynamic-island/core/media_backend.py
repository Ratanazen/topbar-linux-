"""
Ratana Dynamic Island — Media Backend
=====================================
Monitors MPRIS-compatible players via playerctl and BlueZ D-Bus, handles media transport,
sanitizes metadata, extracts track progress and duration, and securely caches album artwork.
"""

import asyncio
import hashlib
import logging
import os
import re
import urllib.parse
from pathlib import Path
from typing import Any, Callable, List, Optional

from core.priority_manager import Priority
from core.state_manager import IslandState, build_progress_bar, truncate_text

log = logging.getLogger("ratana-island")

CACHE_DIR = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "ratana-island" / "artwork"


def format_seconds(seconds: float) -> str:
    """Format numeric seconds into MM:SS or HH:MM:SS."""
    s = int(max(0, seconds))
    m, sec = divmod(s, 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h}:{m:02d}:{sec:02d}"
    return f"{m:02d}:{sec:02d}"


def prune_artwork_cache(max_files: int = 50):
    """Keep artwork cache bounded to prevent unbounded disk growth."""
    try:
        if not CACHE_DIR.exists():
            return
        files = sorted(CACHE_DIR.glob("*.jpg"), key=lambda p: p.stat().st_mtime)
        if len(files) > max_files:
            for f in files[:len(files) - max_files]:
                try:
                    f.unlink()
                except OSError:
                    pass
    except Exception as e:
        log.debug(f"Cache prune exception: {e}")


class MediaBackend:
    def __init__(self, config: Any, caps: Any, on_state_changed: Callable[[Optional[IslandState]], None]):
        self.config = config
        self.caps = caps
        self.on_state_changed = on_state_changed
        self.active_media_state: Optional[IslandState] = None
        self.cached_art_urls: dict = {}
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

    async def run_monitor(self):
        """Continuously monitors media players via playerctl --follow."""
        if not self.config.enable_media or not self.caps.has_playerctl:
            return

        cmd = [
            "playerctl", "--follow", "metadata",
            "--format", "{{status}}|||{{artist}}|||{{title}}|||{{position}}|||{{mpris:length}}|||{{playerName}}|||{{mpris:artUrl}}"
        ]

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

                    parts = decoded.split("|||")
                    if len(parts) >= 6:
                        status = parts[0]
                        artist = parts[1]
                        title = parts[2]
                        pos_raw = parts[3]
                        len_raw = parts[4]
                        player_name = parts[5]
                        art_raw = parts[6] if len(parts) > 6 else ""

                        # Sanitize YouTube badges and video suffixes
                        title = re.sub(r"^\(\d+\)\s*", "", title)
                        title = re.sub(r"\s*-\s*YouTube$", "", title)

                        if status.lower() == "playing":
                            icon = "󰐊"
                            try:
                                pos = float(pos_raw) / 1000000.0 if pos_raw else 0.0
                                length = float(len_raw) / 1000000.0 if len_raw else 0.0
                                percent = (pos / length * 100.0) if length > 0 else 0.0
                            except ValueError:
                                pos = 0.0
                                length = 0.0
                                percent = 0.0

                            bar = build_progress_bar(percent, total_blocks=5)
                            disp_title = truncate_text(title, 20)
                            disp_artist = truncate_text(artist, 14) if artist else ""

                            pos_str = format_seconds(pos) if length > 0 else ""
                            len_str = format_seconds(length) if length > 0 else ""

                            # Resolve and cache album artwork safely
                            local_art = await self._resolve_artwork(art_raw)

                            self.active_media_state = IslandState(
                                source="media",
                                state="media",
                                priority=Priority.MEDIA,
                                icon=icon,
                                title=disp_title,
                                subtitle=disp_artist,
                                progress_bar=bar,
                                progress_pct=round(percent / 100.0, 3),
                                css_class="media playing",
                                tooltip=f"Playing: {title}\nArtist: {artist}\nPlayer: {player_name}",
                                art_url=local_art,
                                duration_str=len_str,
                                position_str=pos_str,
                                player_name=player_name,
                            )
                        else:
                            self.active_media_state = None

                        self.on_state_changed(self.active_media_state)

                await proc.wait()
            except Exception as e:
                log.warning(f"Media monitor restart: {e}")
            await asyncio.sleep(2.0)

    async def _resolve_artwork(self, raw_url: str) -> str:
        """Validates and caches artwork URLs, returning a local file:// URI."""
        if not raw_url:
            return ""

        raw_url = raw_url.strip()

        # Local file paths
        if raw_url.startswith("file://"):
            local_path = Path(urllib.parse.unquote(raw_url[7:]))
            if local_path.exists() and local_path.is_file():
                return local_path.as_uri()
            return ""

        if raw_url.startswith("/"):
            local_path = Path(raw_url)
            if local_path.exists() and local_path.is_file():
                return local_path.as_uri()
            return ""

        # Remote HTTP/HTTPS URLs: Download safely to bounded cache
        if raw_url.startswith("http://") or raw_url.startswith("https://"):
            if raw_url in self.cached_art_urls:
                cached_path = Path(self.cached_art_urls[raw_url])
                if cached_path.exists():
                    return cached_path.as_uri()

            url_hash = hashlib.sha256(raw_url.encode("utf-8")).hexdigest()[:16]
            dest_file = CACHE_DIR / f"{url_hash}.jpg"

            if dest_file.exists():
                self.cached_art_urls[raw_url] = str(dest_file)
                return dest_file.as_uri()

            try:
                # Bounded download: max 3s, max 4MB
                proc = await asyncio.create_subprocess_exec(
                    "curl", "-s", "-f", "-m", "3", "--max-filesize", "4194304",
                    "-o", str(dest_file), raw_url,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL
                )
                ret = await proc.wait()
                if ret == 0 and dest_file.exists() and dest_file.stat().st_size > 0:
                    self.cached_art_urls[raw_url] = str(dest_file)
                    prune_artwork_cache(50)
                    return dest_file.as_uri()
            except Exception as e:
                log.debug(f"Artwork download failed: {e}")

        return ""

    async def list_players(self) -> List[str]:
        """Discover active MPRIS player instances."""
        if not self.caps.has_playerctl:
            return []
        try:
            proc = await asyncio.create_subprocess_exec(
                "playerctl", "-l",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL
            )
            out, _ = await proc.communicate()
            return [p.strip() for p in out.decode("utf-8", errors="replace").splitlines() if p.strip()]
        except Exception:
            return []

    async def toggle(self):
        if self.caps.has_playerctl:
            await asyncio.create_subprocess_exec("playerctl", "play-pause")

    async def next(self):
        if self.caps.has_playerctl:
            await asyncio.create_subprocess_exec("playerctl", "next")

    async def prev(self):
        if self.caps.has_playerctl:
            await asyncio.create_subprocess_exec("playerctl", "previous")

    async def stop(self):
        if self.caps.has_playerctl:
            await asyncio.create_subprocess_exec("playerctl", "stop")
