"""Unit tests for cache manager."""

from pathlib import Path
from ratana_island.utils.cache import CacheManager


def test_sanitize_filename():
    assert CacheManager.sanitize_filename("AC/DC") == "AC_DC"
    assert CacheManager.sanitize_filename("What's up?!") == "What_s_up_"
    assert CacheManager.sanitize_filename("Normal-Name.123") == "Normal-Name.123"
    assert CacheManager.sanitize_filename("   ") == "unknown"


def test_lyrics_cache_read_write(tmp_path: Path):
    cache = CacheManager(base_dir=tmp_path)
    assert cache.get_cached_lyrics("Artist", "Song") is None

    sample_lrc = "[00:01.00] Hello World"
    saved_path = cache.save_cached_lyrics("Artist", "Song", sample_lrc)
    assert saved_path.exists()

    retrieved = cache.get_cached_lyrics("Artist", "Song")
    assert retrieved == sample_lrc


def test_artwork_path_hashing(tmp_path: Path):
    cache = CacheManager(base_dir=tmp_path)
    p1 = cache.get_artwork_path("https://example.com/cover1.jpg")
    p2 = cache.get_artwork_path("https://example.com/cover2.png")
    p3 = cache.get_artwork_path("https://example.com/cover1.jpg")

    assert p1.suffix == ".jpg"
    assert p2.suffix == ".png"
    assert p1 == p3
    assert p1 != p2
