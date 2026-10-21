"""Disk caching utilities for lyrics and album artwork."""

import hashlib
import re
from pathlib import Path
from typing import Optional
from ratana_island.config import AppConfig


class CacheManager:
    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or AppConfig.get_cache_dir()
        self.lyrics_dir = self.base_dir / "lyrics"
        self.artwork_dir = self.base_dir / "artwork"
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        self.lyrics_dir.mkdir(parents=True, exist_ok=True)
        self.artwork_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def sanitize_filename(name: str) -> str:
        # Replace non-alphanumeric characters with underscores
        clean = re.sub(r"[^\w\-.]", "_", name.strip())
        # Collapse multiple underscores
        clean = re.sub(r"_+", "_", clean)
        return clean[:120] if clean else "unknown"

    def get_lyrics_path(self, artist: str, title: str) -> Path:
        s_artist = self.sanitize_filename(artist)
        s_title = self.sanitize_filename(title)
        return self.lyrics_dir / f"{s_artist}_{s_title}.lrc"

    def get_cached_lyrics(self, artist: str, title: str) -> Optional[str]:
        path = self.get_lyrics_path(artist, title)
        if path.is_file():
            try:
                return path.read_text(encoding="utf-8")
            except Exception:
                return None
        return None

    def save_cached_lyrics(self, artist: str, title: str, content: str) -> Path:
        path = self.get_lyrics_path(artist, title)
        path.write_text(content, encoding="utf-8")
        return path

    def get_artwork_path(self, url_or_uri: str) -> Path:
        # Hash URL to produce deterministic safe filename
        url_hash = hashlib.sha256(url_or_uri.encode("utf-8")).hexdigest()[:16]
        # Preserve extension if present
        ext = ".png"
        if url_or_uri.lower().endswith(".jpg") or url_or_uri.lower().endswith(".jpeg"):
            ext = ".jpg"
        elif url_or_uri.lower().endswith(".webp"):
            ext = ".webp"
        return self.artwork_dir / f"art_{url_hash}{ext}"

    def get_cached_artwork(self, url_or_uri: str) -> Optional[Path]:
        path = self.get_artwork_path(url_or_uri)
        if path.is_file() and path.stat().st_size > 0:
            return path
        return None
