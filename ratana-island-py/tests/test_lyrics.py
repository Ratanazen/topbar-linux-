"""Unit tests for LRC parsing and lyrics synchronization."""

from ratana_island.services.lyrics import LyricsEngine

SAMPLE_LRC = """
[ti:Shape of You]
[ar:Ed Sheeran]
[00:09.65] The club isn't the best place to find a lover
[00:12.10] So the bar is where I go
[00:14.81] Me and my friends at the table doing shots
[00:17.04] Drinking fast, and then we talk slow
[00:19.70] You come over and start up a conversation with just me
"""

UNSORTED_LRC = """
[00:10.00] Second line
[00:05.00] First line
[00:15.00] Third line
"""

PLAIN_LYRICS = """
First line of plain lyrics
Second line of plain lyrics
Third line of plain lyrics
"""


def test_parse_lrc_lines():
    engine = LyricsEngine()
    engine.load_lrc(SAMPLE_LRC)

    assert engine.is_synced is True
    assert len(engine.lines) == 5
    assert engine.lines[0].timestamp == 9.65
    assert "club isn't the best place" in engine.lines[0].text
    assert engine.lines[1].timestamp == 12.10
    assert engine.lines[4].timestamp == 19.70


def test_unsorted_lrc_sorting():
    engine = LyricsEngine()
    engine.load_lrc(UNSORTED_LRC)

    assert engine.is_synced is True
    assert len(engine.lines) == 3
    assert engine.lines[0].timestamp == 5.0
    assert engine.lines[0].text == "First line"
    assert engine.lines[1].timestamp == 10.0
    assert engine.lines[1].text == "Second line"
    assert engine.lines[2].timestamp == 15.0
    assert engine.lines[2].text == "Third line"


def test_timeline_synchronization():
    engine = LyricsEngine()
    engine.load_lrc(SAMPLE_LRC)

    # 1. Before first lyric (< 9.65s)
    state = engine.get_state_at(5.0)
    assert state.is_synced is True
    assert state.current_line == ""
    assert "club isn't the best place" in state.next_line
    assert state.current_index == -1

    # 2. At first lyric (9.65s)
    state = engine.get_state_at(9.65)
    assert state.is_synced is True
    assert "club isn't the best place" in state.current_line
    assert state.prev_line == ""
    assert "bar is where I go" in state.next_line
    assert state.current_index == 0

    # 3. Midway between line 1 and 2 (11.0s)
    state = engine.get_state_at(11.0)
    assert "club isn't the best place" in state.current_line
    assert "bar is where I go" in state.next_line

    # 4. At line 2 (12.10s)
    state = engine.get_state_at(12.5)
    assert "bar is where I go" in state.current_line
    assert "club isn't the best place" in state.prev_line
    assert "doing shots" in state.next_line
    assert state.current_index == 1

    # 5. After last lyric (> 19.70s)
    state = engine.get_state_at(30.0)
    assert "start up a conversation" in state.current_line
    assert state.next_line == ""
    assert state.current_index == 4


def test_plain_text_fallback():
    engine = LyricsEngine()
    engine.load_lrc(PLAIN_LYRICS)

    assert engine.is_synced is False
    state = engine.get_state_at(10.0)
    assert state.is_synced is False
    assert state.current_line == "First line of plain lyrics"


def test_empty_or_none_lrc():
    engine = LyricsEngine()
    engine.load_lrc(None)
    assert engine.is_synced is False
    assert len(engine.lines) == 0

    state = engine.get_state_at(10.0)
    assert state.is_synced is False
    assert state.current_line == ""
