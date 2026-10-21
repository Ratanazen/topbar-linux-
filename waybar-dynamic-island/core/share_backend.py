"""
Ratana Dynamic Island — Smart Share Backend
===========================================
Safe file URL validation, dynamic application discovery (Telegram, Discord, Bluetooth OBEX),
and argument-isolated subprocess execution. Zero shell=True.
"""

import configparser
import logging
import mimetypes
import os
import shutil
import subprocess
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional

log = logging.getLogger("ratana-island")


def format_file_size(bytes_size: int) -> str:
    """Format byte size into human-readable representation."""
    if bytes_size < 1024:
        return f"{bytes_size} B"
    elif bytes_size < 1024 * 1024:
        return f"{bytes_size / 1024:.1f} KB"
    elif bytes_size < 1024 * 1024 * 1024:
        return f"{bytes_size / (1024 * 1024):.1f} MB"
    else:
        return f"{bytes_size / (1024 * 1024 * 1024):.2f} GB"


def resolve_file_icon(mime: str, is_dir: bool = False) -> str:
    """Return an appropriate Nerd Font glyph based on MIME category."""
    if is_dir:
        return "󰉋"
    if not mime:
        return "󰈔"
    if mime.startswith("image/"):
        return "󰈟"
    if mime.startswith("video/"):
        return "󰈫"
    if mime.startswith("audio/"):
        return "󰈢"
    if "pdf" in mime:
        return "󰈦"
    if "zip" in mime or "tar" in mime or "compressed" in mime or "archive" in mime or "7z" in mime:
        return "󰛫"
    if mime.startswith("text/") or "document" in mime or "json" in mime or "xml" in mime:
        return "󰈙"
    return "󰈔"


class ShareManager:
    """Handles file inspection, application target discovery, and safe dispatch."""

    def __init__(self, bluetooth_backend=None):
        self.bluetooth = bluetooth_backend

    def parse_and_validate_urls(self, raw_urls: List[str]) -> List[Dict[str, Any]]:
        """Validate input URLs, rejecting non-file or dangerous schemes, preserving Unicode paths."""
        valid_files = []
        if not raw_urls:
            return valid_files

        for raw in raw_urls:
            if not isinstance(raw, str) or not raw.strip():
                continue

            cleaned = raw.strip()

            # Handle URI scheme
            if "://" in cleaned:
                parsed = urllib.parse.urlparse(cleaned)
                if parsed.scheme.lower() != "file":
                    log.warning(f"SmartShare: Rejected unsupported URL scheme '{parsed.scheme}': {cleaned}")
                    continue
                # Unquote path to handle Unicode and spaces
                local_path_str = urllib.parse.unquote(parsed.path)
            else:
                # Direct filesystem path
                local_path_str = cleaned

            try:
                p = Path(local_path_str).resolve()
            except Exception as e:
                log.warning(f"SmartShare: Invalid path '{local_path_str}': {e}")
                continue

            if not p.exists():
                log.warning(f"SmartShare: File not found: {p}")
                continue

            try:
                # Verify read permission
                if not os.access(p, os.R_OK):
                    log.warning(f"SmartShare: File unreadable (permission denied): {p}")
                    continue

                is_dir = p.is_dir()
                size_bytes = 0 if is_dir else p.stat().st_size
                mime, _ = mimetypes.guess_type(str(p))
                if is_dir:
                    mime = "inode/directory"
                elif not mime:
                    mime = "application/octet-stream"

                valid_files.append({
                    "path": str(p),
                    "name": p.name or str(p),
                    "size_bytes": size_bytes,
                    "size_str": format_file_size(size_bytes) if not is_dir else "Folder",
                    "mime": mime,
                    "is_dir": is_dir,
                    "icon": resolve_file_icon(mime, is_dir=is_dir),
                    "exists": True,
                })
            except Exception as e:
                log.error(f"SmartShare: Error inspecting '{p}': {e}")

        return valid_files

    def discover_targets(self, files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Dynamically detect installed apps and file-sharing integrations suitable for the files."""
        targets = []
        if not files:
            return targets

        # 1. Telegram Desktop
        tg_bin = shutil.which("Telegram") or shutil.which("telegram-desktop")
        if tg_bin:
            targets.append({
                "id": "telegram",
                "name": "Telegram Desktop",
                "icon": "󰖣",
                "available": True,
                "badge": "Installed",
                "description": "Open Telegram to drag/paste files into chat",
                "binary": tg_bin,
            })
        else:
            targets.append({
                "id": "telegram",
                "name": "Telegram Desktop",
                "icon": "󰖣",
                "available": False,
                "badge": "Missing",
                "description": "Telegram Desktop is not installed",
                "binary": None,
            })

        # 2. Discord (Vesktop / WebCord / official Discord)
        discord_bin = shutil.which("discord") or shutil.which("vesktop") or shutil.which("webcord")
        if discord_bin:
            targets.append({
                "id": "discord",
                "name": "Discord",
                "icon": "󰙯",
                "available": True,
                "badge": "Installed",
                "description": "Open Discord to share files in chat",
                "binary": discord_bin,
            })
        else:
            targets.append({
                "id": "discord",
                "name": "Discord",
                "icon": "󰙯",
                "available": False,
                "badge": "Missing",
                "description": "Discord client not installed (install discord or vesktop)",
                "binary": None,
            })

        # 3. Bluetooth File Transfer (BlueZ OBEX / blueman-sendto)
        bt_sendto = shutil.which("blueman-sendto") or shutil.which("bluetooth-sendto")
        bt_powered = True
        if self.bluetooth:
            try:
                bt_powered = getattr(self.bluetooth, "adapter_powered", True)
            except Exception:
                bt_powered = True

        if bt_sendto and bt_powered:
            targets.append({
                "id": "bluetooth",
                "name": "Bluetooth Transfer",
                "icon": "󰂯",
                "available": True,
                "badge": "BlueZ OBEX",
                "description": "Send files to paired Bluetooth device",
                "binary": bt_sendto,
            })
        elif bt_sendto and not bt_powered:
            targets.append({
                "id": "bluetooth",
                "name": "Bluetooth Transfer",
                "icon": "󰂲",
                "available": False,
                "badge": "Powered Off",
                "description": "Bluetooth adapter is turned off",
                "binary": bt_sendto,
            })
        else:
            targets.append({
                "id": "bluetooth",
                "name": "Bluetooth Transfer",
                "icon": "󰂲",
                "available": False,
                "badge": "Missing Tool",
                "description": "Install 'blueman' for Bluetooth file transfer",
                "binary": None,
            })

        # 4. Registered Default Application for Primary MIME
        primary_mime = files[0]["mime"]
        default_app = self._resolve_mime_default_app(primary_mime)
        if default_app and default_app.get("binary"):
            targets.append({
                "id": "default_app",
                "name": default_app.get("name", "Default App"),
                "icon": "󰅩",
                "available": True,
                "badge": "Default",
                "description": f"Open with {default_app.get('name')}",
                "binary": default_app.get("binary"),
            })
        elif shutil.which("xdg-open"):
            targets.append({
                "id": "default_app",
                "name": "Default App",
                "icon": "󰅩",
                "available": True,
                "badge": "Default",
                "description": "Open with system default application",
                "binary": "xdg-open",
            })

        # 5. Copy Paths to Clipboard
        if shutil.which("wl-copy"):
            targets.append({
                "id": "clipboard",
                "name": "Copy to Clipboard",
                "icon": "󰅍",
                "available": True,
                "badge": "System",
                "description": "Copy file paths to system clipboard",
                "binary": "wl-copy",
            })

        return targets

    def _resolve_mime_default_app(self, mime: str) -> Optional[Dict[str, str]]:
        """Look up default application for MIME type via xdg-mime or desktop files."""
        if not mime or mime == "application/octet-stream":
            return None

        # Check xdg-mime query default
        try:
            res = subprocess.run(["xdg-mime", "query", "default", mime], capture_output=True, text=True, timeout=1.5)
            if res.returncode == 0 and res.stdout.strip():
                desktop_file = res.stdout.strip()
                return self._parse_desktop_file(desktop_file)
        except Exception:
            pass

        return None

    def _parse_desktop_file(self, desktop_id: str) -> Optional[Dict[str, str]]:
        """Parse desktop file to extract application name and binary executable."""
        search_dirs = [
            Path.home() / ".local/share/applications",
            Path("/usr/local/share/applications"),
            Path("/usr/share/applications"),
        ]

        found_path = None
        for d in search_dirs:
            candidate = d / desktop_id
            if candidate.exists():
                found_path = candidate
                break

        if not found_path:
            return None

        try:
            parser = configparser.ConfigParser(interpolation=None)
            parser.read(str(found_path), encoding="utf-8")
            if "Desktop Entry" in parser:
                sec = parser["Desktop Entry"]
                name = sec.get("Name", desktop_id.replace(".desktop", ""))
                exec_line = sec.get("Exec", "")
                if exec_line:
                    # Clean %f, %F, %u, %U placeholders
                    parts = exec_line.split()
                    bin_name = parts[0]
                    bin_path = shutil.which(bin_name)
                    if bin_path:
                        return {"name": name, "binary": bin_path, "desktop_id": desktop_id}
        except Exception as e:
            log.warning(f"SmartShare: Error reading desktop file {found_path}: {e}")

        return None

    def execute_share(self, target_id: str, files: List[str]) -> Dict[str, Any]:
        """Execute sharing action using argument arrays without shell=True."""
        if not files:
            return {"status": "error", "message": "No files selected to share."}

        # Validate that files actually exist
        valid_paths = [str(Path(f).resolve()) for f in files if Path(f).exists()]
        if not valid_paths:
            return {"status": "error", "message": "None of the specified files exist on disk."}

        try:
            if target_id == "clipboard":
                # Copy file paths / URIs into Wayland clipboard
                uri_list = "\n".join(f"file://{p}" for p in valid_paths)
                proc = subprocess.Popen(["wl-copy", "-t", "text/uri-list"], stdin=subprocess.PIPE)
                proc.communicate(input=uri_list.encode("utf-8"))
                return {"status": "ok", "message": f"Copied {len(valid_paths)} file URI(s) to clipboard."}

            elif target_id == "bluetooth":
                bt_send = shutil.which("blueman-sendto") or shutil.which("bluetooth-sendto")
                if not bt_send:
                    return {"status": "error", "message": "Bluetooth file transfer tool (blueman-sendto) is not installed."}
                cmd = [bt_send, *valid_paths]
                subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
                return {"status": "ok", "message": f"Launched Bluetooth transfer for {len(valid_paths)} file(s)."}

            elif target_id == "telegram":
                tg_bin = shutil.which("Telegram") or shutil.which("telegram-desktop")
                if not tg_bin:
                    return {"status": "error", "message": "Telegram Desktop is not installed."}
                # Telegram desktop does not take multiple arbitrary file paths directly on CLI reliably;
                # copy file paths to clipboard for convenient paste into chat, and launch/focus Telegram
                try:
                    uri_list = "\n".join(f"file://{p}" for p in valid_paths)
                    p_clip = subprocess.Popen(["wl-copy", "-t", "text/uri-list"], stdin=subprocess.PIPE)
                    p_clip.communicate(input=uri_list.encode("utf-8"))
                except Exception:
                    pass
                subprocess.Popen([tg_bin], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
                return {"status": "ok", "message": f"Opened Telegram Desktop. {len(valid_paths)} file(s) copied to clipboard for pasting."}

            elif target_id == "discord":
                dc_bin = shutil.which("discord") or shutil.which("vesktop") or shutil.which("webcord")
                if not dc_bin:
                    return {"status": "error", "message": "Discord client is not installed."}
                try:
                    uri_list = "\n".join(f"file://{p}" for p in valid_paths)
                    p_clip = subprocess.Popen(["wl-copy", "-t", "text/uri-list"], stdin=subprocess.PIPE)
                    p_clip.communicate(input=uri_list.encode("utf-8"))
                except Exception:
                    pass
                subprocess.Popen([dc_bin], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
                return {"status": "ok", "message": f"Opened Discord. {len(valid_paths)} file(s) copied to clipboard for pasting."}

            elif target_id == "default_app":
                # Determine default app or use xdg-open
                mime, _ = mimetypes.guess_type(valid_paths[0])
                default_app = self._resolve_mime_default_app(mime)
                if default_app and default_app.get("binary"):
                    cmd = [default_app["binary"], *valid_paths]
                elif shutil.which("xdg-open"):
                    cmd = ["xdg-open", valid_paths[0]]
                else:
                    return {"status": "error", "message": "No default application found."}

                subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
                return {"status": "ok", "message": f"Opened file(s) with {cmd[0]}."}

            else:
                # Custom binary or specific application ID
                app_bin = shutil.which(target_id)
                if not app_bin:
                    return {"status": "error", "message": f"Target application '{target_id}' not found."}
                cmd = [app_bin, *valid_paths]
                subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
                return {"status": "ok", "message": f"Opened file(s) with {target_id}."}

        except Exception as e:
            log.error(f"SmartShare: Execution error for target '{target_id}': {e}")
            return {"status": "error", "message": f"Failed to launch sharing action: {e}"}
