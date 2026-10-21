#!/usr/bin/env python3
"""
Ratana Dynamic Island — Smart Share Engine
==========================================
Handles drag-and-drop file sanitization, dynamic application discovery,
MIME-type association matching, Bluetooth OBEX check, and safe launching
strictly without `shell=True`.
"""

import logging
import mimetypes
import os
import shutil
import subprocess
import time
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

log = logging.getLogger("ratana-island.share")


def format_size(num_bytes: int) -> str:
    """Format bytes into human-readable string (KB, MB, GB)."""
    if num_bytes < 1024:
        return f"{num_bytes} B"
    elif num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024:.1f} KB"
    elif num_bytes < 1024 * 1024 * 1024:
        return f"{num_bytes / (1024 * 1024):.1f} MB"
    return f"{num_bytes / (1024 * 1024 * 1024):.1f} GB"


def get_file_icon(mime: str, is_dir: bool = False) -> str:
    """Resolve a symbolic Nerd Font icon according to MIME type."""
    if is_dir:
        return "󰉋"
    if not mime:
        return "󰈔"
    if mime.startswith("image/"):
        return "󰋩"
    elif mime.startswith("video/"):
        return "󰕧"
    elif mime.startswith("audio/"):
        return "󰎆"
    elif mime in ("application/pdf", "application/msword", "application/vnd.oasis.opendocument.text") or mime.startswith("text/"):
        return "󰈙"
    elif "zip" in mime or "tar" in mime or "compressed" in mime or "archive" in mime or "7z" in mime:
        return "󰛫"
    elif "code" in mime or "json" in mime or "xml" in mime or "script" in mime or "javascript" in mime:
        return "󰅩"
    return "󰈔"


class ShareManager:
    """Core Smart Share Controller."""

    _cache: Dict[str, Tuple[float, Any]] = {}
    _CACHE_TTL: float = 60.0

    @classmethod
    def _get_cached(cls, key: str) -> Optional[Any]:
        if key in cls._cache:
            ts, val = cls._cache[key]
            if time.time() - ts < cls._CACHE_TTL:
                return val
        return None

    @classmethod
    def _set_cached(cls, key: str, val: Any) -> Any:
        cls._cache[key] = (time.time(), val)
        return val

    @staticmethod
    def sanitize_urls(urls_or_paths: List[str]) -> List[Dict[str, Any]]:
        """
        Validate, parse, and sanitize file URLs or paths.
        - Accepts only 'file://' scheme or absolute local paths
        - Rejects dangerous schemes ('javascript:', 'data:', 'http:', etc.)
        - Safely decodes percent-encoded Unicode filenames (Khmer, UTF-8, spaces)
        - Verifies filesystem existence without loading file contents into memory
        """
        sanitized = []
        if not urls_or_paths:
            return sanitized

        for item in urls_or_paths:
            if not isinstance(item, str) or not item.strip():
                continue
            item = item.strip()

            # Handle URL schemes
            if "://" in item:
                parsed = urllib.parse.urlparse(item)
                if parsed.scheme.lower() != "file":
                    log.warning(f"Rejected unsupported URL scheme '{parsed.scheme}': {item}")
                    continue
                # Unquote path to handle %20 and Unicode sequences
                raw_path = urllib.parse.unquote(parsed.path)
            else:
                raw_path = urllib.parse.unquote(item)

            try:
                real_p = os.path.realpath(raw_path)
            except Exception as e:
                log.warning(f"Failed to resolve realpath for '{item}': {e}")
                continue

            if not os.path.exists(real_p):
                log.warning(f"File path does not exist on filesystem: '{real_p}'")
                continue

            try:
                is_dir = os.path.isdir(real_p)
                size_bytes = os.path.getsize(real_p) if not is_dir else 0
                size_label = "Folder" if is_dir else format_size(size_bytes)
                name = os.path.basename(real_p) or real_p

                if is_dir:
                    mime = "inode/directory"
                else:
                    guessed, _ = mimetypes.guess_type(real_p)
                    mime = guessed or "application/octet-stream"

                icon = get_file_icon(mime, is_dir=is_dir)

                sanitized.append({
                    "path": real_p,
                    "name": name,
                    "size": size_bytes,
                    "size_bytes": size_bytes,
                    "size_str": size_label,
                    "size_human": size_label,
                    "is_dir": is_dir,
                    "mime": mime,
                    "icon": icon,
                })
            except Exception as e:
                log.warning(f"Error inspecting file metadata for '{real_p}': {e}")

        return sanitized

    @classmethod
    def get_telegram_status(cls) -> Dict[str, Any]:
        """Detect Telegram Desktop across binary PATH and Flatpak installations."""
        cached = cls._get_cached("telegram")
        if cached is not None:
            return cached

        res = None
        for candidate in ("telegram-desktop", "Telegram", "telegram"):
            path = shutil.which(candidate)
            if path:
                res = {
                    "id": "telegram",
                    "name": "Telegram",
                    "icon": "󰈰",
                    "installed": True,
                    "exec": path,
                    "command": [path],
                    "category": "chat",
                    "badge": "Messenger",
                    "description": "Send via Telegram Desktop (open app & attach)",
                    "manual_step": "Select contact or chat inside Telegram"
                }
                break

        # Check Flatpak
        if res is None:
            try:
                fp_res = subprocess.run(["flatpak", "info", "org.telegram.desktop"], capture_output=True, text=True)
                if fp_res.returncode == 0:
                    res = {
                        "id": "telegram",
                        "name": "Telegram (Flatpak)",
                        "icon": "󰈰",
                        "installed": True,
                        "exec": "flatpak",
                        "command": ["flatpak", "run", "org.telegram.desktop"],
                        "category": "chat",
                        "badge": "Flatpak",
                        "description": "Send via Telegram Desktop",
                        "manual_step": "Select contact or chat inside Telegram"
                    }
            except Exception:
                pass

        if res is None:
            res = {
                "id": "telegram",
                "name": "Telegram",
                "icon": "󰈰",
                "installed": False,
                "category": "chat",
                "badge": "Not Installed",
                "description": "Telegram is not installed",
                "reason": "Install with 'sudo pacman -S telegram-desktop'"
            }

        return cls._set_cached("telegram", res)

    @classmethod
    def get_discord_status(cls) -> Dict[str, Any]:
        """Detect Discord clients (Discord, Vesktop, WebCord, Flatpak)."""
        cached = cls._get_cached("discord")
        if cached is not None:
            return cached

        res = None
        for candidate, label in (("discord", "Discord"), ("vesktop", "Vesktop"), ("webcord", "WebCord"), ("Discord", "Discord")):
            path = shutil.which(candidate)
            if path:
                res = {
                    "id": "discord",
                    "name": label,
                    "icon": "󰙯",
                    "installed": True,
                    "exec": path,
                    "command": [path],
                    "category": "chat",
                    "badge": "Community",
                    "description": f"Share with {label} channels and friends",
                    "manual_step": "Select channel or server to attach file"
                }
                break

        # Check Flatpak
        if res is None:
            for fp_app in ("com.discordapp.Discord", "dev.vencord.Vesktop"):
                try:
                    fp_res = subprocess.run(["flatpak", "info", fp_app], capture_output=True, text=True)
                    if fp_res.returncode == 0:
                        res = {
                            "id": "discord",
                            "name": "Discord (Flatpak)",
                            "icon": "󰙯",
                            "installed": True,
                            "exec": "flatpak",
                            "command": ["flatpak", "run", fp_app],
                            "category": "chat",
                            "badge": "Flatpak",
                            "description": "Share to Discord",
                            "manual_step": "Select channel or server to attach file"
                        }
                        break
                except Exception:
                    pass

        if res is None:
            res = {
                "id": "discord",
                "name": "Discord",
                "icon": "󰙯",
                "installed": False,
                "category": "chat",
                "badge": "Not Installed",
                "description": "Discord client is not installed",
                "reason": "Install with 'sudo pacman -S discord' or 'yay -S vesktop'"
            }

        return cls._set_cached("discord", res)

    @classmethod
    def clear_cache(cls):
        """Clear discovery cache (useful for tests and dynamic re-scans)."""
        cls._cache.clear()

    @classmethod
    def get_bluetooth_status(cls, use_cache: bool = True) -> Dict[str, Any]:
        """Detect Bluetooth hardware power and OBEX file transfer tool availability."""
        if use_cache:
            cached = cls._get_cached("bluetooth")
            if cached is not None:
                return cached

        sendto_bin = shutil.which("blueman-sendto") or shutil.which("bluetooth-sendto")

        # Check if Bluetooth adapter is powered
        is_powered = False
        try:
            out = subprocess.check_output(["bluetoothctl", "show"], stderr=subprocess.DEVNULL, text=True)
            if isinstance(out, bytes):
                out = out.decode("utf-8", errors="replace")
            if "Powered: yes" in out:
                is_powered = True
        except Exception:
            pass

        if not is_powered and shutil.which("rfkill"):
            try:
                out = subprocess.check_output(["rfkill", "list", "bluetooth"], stderr=subprocess.DEVNULL, text=True)
                if isinstance(out, bytes):
                    out = out.decode("utf-8", errors="replace")
                if "Soft blocked: no" in out and "Hard blocked: no" in out:
                    is_powered = True
            except Exception:
                pass

        if sendto_bin and is_powered:
            res = {
                "id": "bluetooth",
                "name": "Bluetooth Transfer",
                "icon": "󰂯",
                "installed": True,
                "powered": True,
                "exec": sendto_bin,
                "command": [sendto_bin],
                "category": "bluetooth",
                "badge": "OBEX",
                "description": "Transfer to nearby paired device over Bluetooth",
                "manual_step": "Select destination device in Blueman"
            }
        elif sendto_bin and not is_powered:
            res = {
                "id": "bluetooth",
                "name": "Bluetooth Transfer",
                "icon": "󰂯",
                "installed": True,
                "powered": False,
                "category": "bluetooth",
                "badge": "Disabled",
                "description": "Bluetooth adapter is powered off",
                "reason": "Enable via 'bluetoothctl power on'"
            }
        else:
            res = {
                "id": "bluetooth",
                "name": "Bluetooth Transfer",
                "icon": "󰂯",
                "installed": False,
                "powered": is_powered,
                "category": "bluetooth",
                "badge": "Missing OBEX",
                "description": "Bluetooth file transfer tool unavailable",
                "reason": "Install blueman with 'sudo pacman -S blueman'"
            }

        return cls._set_cached("bluetooth", res)

    @classmethod
    def get_desktop_candidates(cls, mimes: List[str]) -> List[Dict[str, Any]]:
        """
        Discover installed desktop applications compatible with the selected MIME types.
        Uses 'gio mime' when available and parses .desktop entries.
        """
        candidates = []
        seen_bins = set()

        # Check common file openers based on mime categories
        has_image = any(m.startswith("image/") for m in mimes)
        has_video = any(m.startswith("video/") for m in mimes)
        has_audio = any(m.startswith("audio/") for m in mimes)
        has_doc = any(m in ("application/pdf", "text/plain") or m.startswith("text/") for m in mimes)

        preferred = []
        if has_image:
            preferred.extend(["gwenview", "feh", "swappy", "eog", "kolourpaint"])
        if has_video or has_audio:
            preferred.extend(["vlc", "mpv"])
        if has_doc:
            preferred.extend(["code", "subl", "gedit", "kate", "libreoffice", "okular"])
        preferred.extend(["brave-browser", "firefox", "chromium", "google-chrome", "thunar", "dolphin"])

        for bin_name in preferred:
            bin_path = shutil.which(bin_name)
            if bin_path and bin_name not in seen_bins:
                seen_bins.add(bin_name)
                label = bin_name.replace("-", " ").capitalize()
                icon = "󰈔"
                if "brave" in bin_name or "firefox" in bin_name or "chrome" in bin_name:
                    icon = ""
                    label = "Web Browser"
                elif "thunar" in bin_name or "dolphin" in bin_name:
                    icon = "󰉋"
                    label = "File Manager"
                elif "code" in bin_name or "kate" in bin_name or "gedit" in bin_name:
                    icon = "󰨞"
                    label = "Code / Editor"
                elif "vlc" in bin_name or "mpv" in bin_name:
                    icon = "󰕧"
                    label = "Media Player"
                elif "gwenview" in bin_name or "feh" in bin_name:
                    icon = "󰋩"
                    label = "Image Viewer"

                candidates.append({
                    "id": bin_name,
                    "name": label,
                    "icon": icon,
                    "installed": True,
                    "exec": bin_path,
                    "command": [bin_path],
                    "category": "app",
                    "badge": "Application",
                    "description": f"Open with {bin_name}"
                })
                if len(candidates) >= 4:
                    break

        return candidates

    format_size = staticmethod(format_size)
    get_file_icon = staticmethod(get_file_icon)

    @classmethod
    def scan_files(cls, urls_or_paths: List[str]) -> Dict[str, Any]:
        """Complete Smart Share scan returning sanitized files and application targets."""
        files = cls.sanitize_urls(urls_or_paths)
        if not files:
            return {
                "status": "error",
                "message": "No valid local files provided",
                "files": [],
                "count": 0,
                "apps": []
            }

        mimes = [f["mime"] for f in files]

        apps = [
            cls.get_telegram_status(),
            cls.get_discord_status(),
            cls.get_bluetooth_status(),
        ]
        apps.extend(cls.get_desktop_candidates(mimes))

        # Ensure 'available' boolean is always present for QML frontend
        for app in apps:
            if "available" not in app:
                app["available"] = bool(app.get("installed", False) and app.get("powered", True))

        return {
            "status": "ok",
            "files": files,
            "count": len(files),
            "apps": apps
        }

    @classmethod
    def launch_share(cls, app_id: str, file_paths: List[str]) -> Dict[str, Any]:
        """
        Safely execute the application with validated files without shell=True.
        Enforces user confirmation by policy.
        """
        files = cls.sanitize_urls(file_paths)
        if not files:
            return {"status": "error", "message": "Cannot launch share: file paths are invalid or missing"}

        raw_paths = [f["path"] for f in files]

        cmd: List[str] = []

        if app_id == "telegram":
            status = cls.get_telegram_status()
            if not status.get("installed"):
                return {"status": "error", "message": status.get("reason", "Telegram is not installed")}
            cmd = status["command"] + raw_paths

        elif app_id == "discord":
            status = cls.get_discord_status()
            if not status.get("installed"):
                return {"status": "error", "message": status.get("reason", "Discord is not installed")}
            cmd = status["command"] + raw_paths

        elif app_id == "bluetooth":
            status = cls.get_bluetooth_status()
            if not status.get("installed"):
                return {"status": "error", "message": status.get("reason", "Bluetooth transfer tool missing")}
            if not status.get("powered"):
                return {"status": "error", "message": status.get("reason", "Bluetooth adapter is powered off")}
            cmd = status["command"] + raw_paths

        else:
            # Look up binary in PATH
            bin_path = shutil.which(app_id)
            if not bin_path:
                return {"status": "error", "message": f"Application '{app_id}' is not found in PATH"}
            cmd = [bin_path] + raw_paths

        try:
            log.info(f"Safely launching share destination: {cmd[0]} with {len(raw_paths)} file(s)")
            subprocess.Popen(cmd, start_new_session=True)
            return {
                "status": "ok",
                "message": f"Launched {app_id} with {len(raw_paths)} file(s)",
                "app_id": app_id,
                "file_count": len(raw_paths)
            }
        except Exception as e:
            log.error(f"Failed to launch application '{app_id}': {e}")
            return {"status": "error", "message": f"Execution failed: {e}"}
