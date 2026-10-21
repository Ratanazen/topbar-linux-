#!/usr/bin/env python3
"""
Waybar Live Lyrics Module
A fully asynchronous, high-performance lyrics engine for Waybar.
Features: LRCLIB sync, local LRC support, notifications, and click-to-view.
"""

import os
import sys
import json
import re
import urllib.request
import urllib.parse
import logging
import traceback
import asyncio
import subprocess

# Configuration
CACHE_DIR = os.path.expanduser("~/.cache/waybar_lyrics")
LOG_FILE = os.path.join(CACHE_DIR, "lyrics.log")
CURRENT_LYRICS_FILE = os.path.join(CACHE_DIR, "current.txt")
os.makedirs(CACHE_DIR, exist_ok=True)

# Configure Logging
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

class PlayerState:
    def __init__(self):
        self.artist = ""
        self.title = ""
        self.album = ""
        self.duration = 0
        self.status = "Stopped"
        self.position = 0.0
        self.file_path = ""

class LyricsManager:
    def __init__(self):
        self.lrc_data = []
        self.full_lyrics_text = "No lyrics found."
        self.current_song_key = ""
        self.is_fetching = False
        
    def set_lyrics(self, key, lrc_data, plain_text):
        self.current_song_key = key
        self.lrc_data = lrc_data
        self.full_lyrics_text = plain_text
        self.is_fetching = False
        # Save for terminal viewer
        try:
            with open(CURRENT_LYRICS_FILE, 'w') as f:
                f.write(f"--- {key} ---\n\n{plain_text}")
        except Exception:
            pass

def clean_title(artist, title):
    try:
        title = re.sub(r'\(.*?(Official|Video|Audio|Lyric|Live|Music).*?\)', '', title, flags=re.IGNORECASE).strip()
        title = re.sub(r'\[.*?(Official|Video|Audio|Lyric|Live|Music).*?\]', '', title, flags=re.IGNORECASE).strip()
        if not artist or artist.lower() in ['youtube', 'unknown', '']:
            if '-' in title:
                parts = title.split('-', 1)
                artist, title = parts[0].strip(), parts[1].strip()
        else:
            if title.lower().startswith(artist.lower() + " -"):
                title = title[len(artist) + 2:].strip()
        return artist, title
    except Exception:
        return artist, title

def format_time(seconds):
    seconds = max(0, seconds)
    m = int(seconds) // 60
    s = int(seconds) % 60
    return f"{m:02d}:{s:02d}"

async def notify(title, message):
    try:
        await asyncio.create_subprocess_exec('notify-send', '-a', 'Live Lyrics', '-t', '3000', title, message)
    except Exception:
        pass

async def get_player_state():
    state = PlayerState()
    try:
        proc = await asyncio.create_subprocess_exec(
            'playerctl', '--player=brave,chromium,chrome,firefox,mpv,vlc,%any', 'status',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=2.0)
        status = stdout.decode().strip()
        state.status = status
        
        if status in ['Playing', 'Paused']:
            proc_meta = await asyncio.create_subprocess_exec(
                'playerctl', '--player=brave,chromium,chrome,firefox,mpv,vlc,%any', 'metadata', '--format', '{{artist}}\t{{title}}\t{{album}}\t{{mpris:length}}\t{{url}}',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL
            )
            stdout_meta, _ = await asyncio.wait_for(proc_meta.communicate(), timeout=2.0)
            meta = stdout_meta.decode().strip().split('\t')
            
            if len(meta) >= 2:
                state.artist, state.title = meta[0], meta[1]
            if len(meta) >= 3:
                state.album = meta[2]
            if len(meta) >= 4 and meta[3]:
                try: state.duration = int(meta[3]) // 1000000
                except ValueError: pass
            if len(meta) >= 5 and meta[4].startswith('file://'):
                state.file_path = urllib.parse.unquote(meta[4][7:])
                
            proc_pos = await asyncio.create_subprocess_exec(
                'playerctl', '--player=brave,chromium,chrome,firefox,mpv,vlc,%any', 'position',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL
            )
            stdout_pos, _ = await asyncio.wait_for(proc_pos.communicate(), timeout=2.0)
            state.position = float(stdout_pos.decode().strip())
    except Exception:
        pass
    return state

def parse_lrc(lrc_text):
    lines = []
    try:
        for line in lrc_text.split('\n'):
            line = line.strip()
            if line.startswith('[') and ']' in line:
                time_str, text = line[1:].split(']', 1)
                if ':' in time_str:
                    try:
                        mins, secs = time_str.split(':', 1)
                        lines.append((int(mins) * 60 + float(secs), text.strip()))
                    except ValueError:
                        pass
    except Exception:
        pass
    return sorted(lines, key=lambda x: x[0])

async def fetch_url(url):
    loop = asyncio.get_running_loop()
    req = urllib.request.Request(url, headers={'User-Agent': 'WaybarLyrics/4.0'})
    def _fetch():
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.read().decode()
    return await loop.run_in_executor(None, _fetch)

async def fetch_lyrics_task(artist, title, album, duration, file_path, manager, key, force_refresh=False):
    try:
        cache_file = os.path.join(CACHE_DIR, key.replace("/", "_") + ".json")
        
        if not force_refresh and os.path.exists(cache_file):
            with open(cache_file, 'r') as f:
                data = json.load(f)
                synced = data.get('synced')
                manager.set_lyrics(key, parse_lrc(synced) if synced else [], data.get('plain', 'No lyrics found.'))
                return

        if file_path and os.path.exists(file_path):
            lrc_path = os.path.splitext(file_path)[0] + ".lrc"
            if os.path.exists(lrc_path):
                with open(lrc_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    with open(cache_file, 'w') as out: json.dump({'synced': content, 'plain': content}, out)
                    manager.set_lyrics(key, parse_lrc(content), content)
                    return

        # Fetch LRCLIB
        for attempt in range(3):
            try:
                url = f"https://lrclib.net/api/get?artist_name={urllib.parse.quote(artist)}&track_name={urllib.parse.quote(title)}"
                resp = await fetch_url(url)
                data = json.loads(resp)
                synced, plain = data.get('syncedLyrics'), data.get('plainLyrics')
                with open(cache_file, 'w') as f: json.dump({'synced': synced, 'plain': plain}, f)
                manager.set_lyrics(key, parse_lrc(synced) if synced else [], plain or "No lyrics found.")
                return
            except Exception as e:
                if "HTTP Error 404" in str(e): break
                await asyncio.sleep(1)
            
        # Fallback Search
        try:
            url_search = f"https://lrclib.net/api/search?q={urllib.parse.quote(artist + ' ' + title)}"
            resp = await fetch_url(url_search)
            data = json.loads(resp)
            if data and isinstance(data, list):
                best = data[0]
                synced, plain = best.get('syncedLyrics'), best.get('plainLyrics')
                with open(cache_file, 'w') as f: json.dump({'synced': synced, 'plain': plain}, f)
                manager.set_lyrics(key, parse_lrc(synced) if synced else [], plain or "No lyrics found.")
                return
        except Exception:
            pass

        with open(cache_file, 'w') as f: json.dump({'synced': None, 'plain': None}, f)
        manager.set_lyrics(key, [], "No lyrics found.")

    except Exception:
        manager.set_lyrics(key, [], "Error fetching lyrics.")

async def main():
    manager = LyricsManager()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--refresh":
        state = await get_player_state()
        if state.title:
            artist, title = clean_title(state.artist, state.title)
            song_key = f"{artist} - {title}"
            manager.is_fetching = True
            await fetch_lyrics_task(artist, title, state.album, state.duration, state.file_path, manager, song_key, force_refresh=True)
            await notify("Lyrics Refreshed", song_key)
        sys.exit(0)
    
    while True:
        try:
            state = await get_player_state()
            
            if state.status == "Stopped" or not state.title:
                print(json.dumps({"text": "", "tooltip": "No music playing", "class": "stopped"}), flush=True)
                await asyncio.sleep(2)
                continue
                
            artist, title = clean_title(state.artist, state.title)
            song_key = f"{artist} - {title}"
            
            if manager.current_song_key != song_key and not manager.is_fetching:
                manager.is_fetching = True
                manager.full_lyrics_text = "Fetching lyrics..."
                manager.lrc_data = []
                manager.current_song_key = song_key
                await notify("Now Playing", song_key)
                asyncio.create_task(fetch_lyrics_task(artist, title, state.album, state.duration, state.file_path, manager, song_key))

            text = title
            if manager.is_fetching:
                text = "Fetching lyrics..."
            elif manager.lrc_data:
                current_line = ""
                for t, lrc_text in manager.lrc_data:
                    if t <= state.position + 0.5:
                        current_line = lrc_text
                    else:
                        break
                if current_line:
                    text = current_line
            else:
                text = title
                
            full_text = f"󰎆 {text}"
            if len(full_text) > 50: full_text = full_text[:47] + "..."
                
            tooltip = f"Title: {title}\nArtist: {artist}\nAlbum: {state.album or 'Unknown'}\n\n{manager.full_lyrics_text}"
            tooltip = tooltip.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                
            out = {
                "text": full_text,
                "tooltip": tooltip,
                "class": state.status.lower()
            }
            print(json.dumps(out), flush=True)
            await asyncio.sleep(0.5)
            
        except Exception:
            await asyncio.sleep(2)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
