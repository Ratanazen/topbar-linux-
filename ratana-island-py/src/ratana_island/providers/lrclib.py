"""LRCLIB API client for fetching synchronized lyrics."""

import logging
import threading
from typing import Callable, Optional
import requests
from ratana_island.utils.cache import CacheManager

logger = logging.getLogger("ratana_island.lrclib")

API_BASE = "https://lrclib.net/api/get"


class LRCLibProvider:
    def __init__(self, cache_manager: Optional[CacheManager] = None):
        self.cache = cache_manager or CacheManager()
        self._ongoing_requests: set[str] = set()

    def fetch_lyrics_sync(
        self,
        title: str,
        artist: str,
        album: Optional[str] = None,
        duration: Optional[float] = None,
    ) -> Optional[str]:
        """Synchronously check local cache and fetch from LRCLIB if not found."""
        if not title or not artist:
            return None

        # 1. Check local disk cache
        cached = self.cache.get_cached_lyrics(artist, title)
        if cached is not None:
            logger.debug(f"Cache hit for lyrics: {artist} - {title}")
            return cached

        # 2. Query LRCLIB API
        params = {
            "track_name": title,
            "artist_name": artist,
        }
        if album:
            params["album_name"] = album
        if duration and duration > 0:
            params["duration"] = int(duration)

        headers = {
            "User-Agent": "RatanaIsland/0.1.0 (Linux; Wayland; SwayFX)",
        }

        try:
            resp = requests.get(API_BASE, params=params, headers=headers, timeout=4.0)
            if resp.status_code == 200:
                data = resp.json()
                synced = data.get("syncedLyrics")
                plain = data.get("plainLyrics")
                result = synced if synced else plain
                if result:
                    self.cache.save_cached_lyrics(artist, title, result)
                    logger.info(f"Successfully fetched lyrics for: {artist} - {title}")
                    return result
            elif resp.status_code == 404:
                # If exact lookup failed with album/duration, try fallback with only title and artist
                if album or duration:
                    fallback_params = {"track_name": title, "artist_name": artist}
                    fb_resp = requests.get(API_BASE, params=fallback_params, headers=headers, timeout=4.0)
                    if fb_resp.status_code == 200:
                        fb_data = fb_resp.json()
                        fb_result = fb_data.get("syncedLyrics") or fb_data.get("plainLyrics")
                        if fb_result:
                            self.cache.save_cached_lyrics(artist, title, fb_result)
                            return fb_result
                logger.debug(f"Lyrics not found on LRCLIB for: {artist} - {title}")
        except Exception as e:
            logger.debug(f"Network error fetching lyrics from LRCLIB: {e}")

        return None

    def fetch_lyrics_async(
        self,
        title: str,
        artist: str,
        album: Optional[str] = None,
        duration: Optional[float] = None,
        on_complete: Optional[Callable[[Optional[str]], None]] = None,
    ) -> None:
        """Asynchronously query LRCLIB in a worker thread and call callback with result."""
        req_key = f"{artist}_{title}"
        if req_key in self._ongoing_requests:
            return
        self._ongoing_requests.add(req_key)

        def worker():
            from gi.repository import GLib

            try:
                res = self.fetch_lyrics_sync(title, artist, album, duration)
                if on_complete:
                    GLib.idle_add(on_complete, res)
            finally:
                self._ongoing_requests.discard(req_key)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
