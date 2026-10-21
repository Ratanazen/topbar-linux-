"""Unit tests for media tracking and metadata normalization."""

from ratana_island.services.media import TrackMetadata
from ratana_island.ui.expanded_view import format_time


def test_track_metadata_defaults():
    t = TrackMetadata()
    assert t.title == "Nothing Playing"
    assert t.is_playing is False
    assert t.has_media is False
    assert t.progress_fraction == 0.0


def test_track_metadata_active_playing():
    t = TrackMetadata(
        title="Shape of You",
        artist="Ed Sheeran",
        status="Playing",
        duration_sec=240.0,
        position_sec=60.0,
    )
    assert t.is_playing is True
    assert t.has_media is True
    assert t.progress_fraction == 0.25


def test_track_metadata_paused():
    t = TrackMetadata(
        title="Shape of You",
        artist="Ed Sheeran",
        status="Paused",
        duration_sec=240.0,
        position_sec=120.0,
    )
    assert t.is_playing is False
    assert t.has_media is True
    assert t.progress_fraction == 0.5


def test_format_time():
    assert format_time(0) == "00:00"
    assert format_time(59) == "00:59"
    assert format_time(60) == "01:00"
    assert format_time(234) == "03:54"
    assert format_time(-10) == "00:00"
