"""LRC parser and synchronization engine."""

import bisect
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass
class LyricLine:
    timestamp: float  # seconds
    text: str


@dataclass
class SyncLyricsState:
    is_synced: bool = False
    current_line: str = ""
    prev_line: str = ""
    next_line: str = ""
    current_index: int = -1
    total_lines: int = 0


class LyricsEngine:
    def __init__(self):
        self.lines: List[LyricLine] = []
        self.plain_text: Optional[str] = None
        self.is_synced: bool = False
        self._timestamps: List[float] = []

    def load_lrc(self, content: Optional[str]) -> None:
        self.lines.clear()
        self._timestamps.clear()
        self.plain_text = None
        self.is_synced = False

        if not content or not content.strip():
            return

        # Regex for [mm:ss.xx] or [mm:ss.xxx] or [mm:ss]
        time_tag_pattern = re.compile(r"\[(\d{1,3}):(\d{2})(?:\.(\d{1,3}))?\]")

        parsed_lines: List[LyricLine] = []
        has_time_tag = False

        for raw_line in content.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            # Find all timestamp tags in the line
            tags = time_tag_pattern.findall(line)
            if tags:
                has_time_tag = True
                # Text is everything after the last tag
                text = time_tag_pattern.sub("", line).strip()
                for mm, ss, ms in tags:
                    minutes = int(mm)
                    seconds = int(ss)
                    fraction = float(f"0.{ms}") if ms else 0.0
                    total_sec = minutes * 60 + seconds + fraction
                    parsed_lines.append(LyricLine(timestamp=total_sec, text=text))

        if has_time_tag and parsed_lines:
            # Sort by timestamp
            parsed_lines.sort(key=lambda x: x.timestamp)
            self.lines = parsed_lines
            self._timestamps = [x.timestamp for x in parsed_lines]
            self.is_synced = True
        else:
            # Plain text lyrics fallback
            self.plain_text = content.strip()
            self.is_synced = False

    def get_state_at(self, position_sec: float) -> SyncLyricsState:
        if not self.is_synced or not self.lines:
            # Return plain text if available
            fallback = self.plain_text or ""
            first_line = fallback.splitlines()[0] if fallback else ""
            return SyncLyricsState(
                is_synced=False,
                current_line=first_line,
                prev_line="",
                next_line="",
                current_index=-1,
                total_lines=len(self.lines),
            )

        # Binary search for greatest timestamp <= position_sec
        # bisect_right returns index where position_sec would be inserted
        idx = bisect.bisect_right(self._timestamps, position_sec) - 1

        if idx < 0:
            # Before the first line
            next_txt = self.lines[0].text if self.lines else ""
            return SyncLyricsState(
                is_synced=True,
                current_line="",
                prev_line="",
                next_line=next_txt,
                current_index=-1,
                total_lines=len(self.lines),
            )

        curr = self.lines[idx]
        prev_txt = self.lines[idx - 1].text if idx > 0 else ""
        next_txt = self.lines[idx + 1].text if idx + 1 < len(self.lines) else ""

        return SyncLyricsState(
            is_synced=True,
            current_line=curr.text,
            prev_line=prev_txt,
            next_line=next_txt,
            current_index=idx,
            total_lines=len(self.lines),
        )
