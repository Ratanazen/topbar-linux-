"""
Ratana Dynamic Island — Network Backend
=======================================
Monitors network connection and disconnection events with strict privacy-preserving SSID handling.
"""

import asyncio
import logging
import re
import time
from typing import Any, Callable

from core.priority_manager import Priority
from core.state_manager import IslandState

log = logging.getLogger("ratana-island")


class NetworkBackend:
    def __init__(self, config: Any, caps: Any, on_transient_event: Callable[[IslandState], None]):
        self.config = config
        self.caps = caps
        self.on_transient_event = on_transient_event
        self.last_network_time: float = 0

    async def run_monitor(self):
        if not self.config.enable_network or not self.caps.has_nmcli:
            return

        cmd = ["nmcli", "monitor"]

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

                    # Debounce rapid network changes (0.5s)
                    now = time.time()
                    if now - self.last_network_time < 0.5:
                        continue
                    self.last_network_time = now

                    # Parse connection events
                    if "connected" in decoded.lower():
                        is_disconnect = "disconnected" in decoded.lower()
                        if is_disconnect:
                            icon = "󰤮"
                            title = "Disconnected"
                            sub = "Network Offline"
                            css = "network disconnected"
                        else:
                            icon = "󰤨"
                            title = "Connected"
                            css = "network"
                            # Handle SSID privacy
                            if self.config.network_ssid_privacy:
                                sub = "Wi-Fi Connected"
                            else:
                                match = re.search(r"connected to (\S+)", decoded)
                                sub = match.group(1) if match else "Online"

                        ev = IslandState(
                            source="network",
                            state="network",
                            priority=Priority.CONNECTIVITY,
                            icon=icon,
                            title=title,
                            subtitle=sub,
                            css_class=css,
                            duration=self.config.network_timeout_s
                        )
                        self.on_transient_event(ev)

                await proc.wait()
            except Exception as e:
                log.warning(f"Network monitor restart: {e}")
            await asyncio.sleep(2.0)

    @staticmethod
    def _signal_to_icon(signal: int) -> str:
        if signal >= 75:
            return "󰤨"
        if signal >= 50:
            return "󰤥"
        if signal >= 25:
            return "󰤢"
        if signal > 0:
            return "󰤟"
        return "󰤯"

    async def get_wifi_status(self) -> dict:
        """Query current Wi-Fi status: enabled, active connection, signal, and interface."""
        if not self.caps.has_nmcli:
            return {"available": False, "enabled": False, "connected": False, "ssid": "", "signal": 0, "device": "", "icon": "󰤮"}

        enabled = True
        try:
            p_radio = await asyncio.create_subprocess_exec(
                "nmcli", "radio", "wifi",
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL
            )
            out_radio, _ = await p_radio.communicate()
            enabled = "enabled" in out_radio.decode().lower()
        except Exception:
            pass

        if not enabled:
            return {
                "available": True,
                "enabled": False,
                "connected": False,
                "ssid": "",
                "signal": 0,
                "device": "",
                "icon": "󰤮",
                "state": "disabled",
            }

        connected = False
        active_ssid = ""
        active_signal = 0
        device_name = ""

        try:
            # Query active devices
            p_dev = await asyncio.create_subprocess_exec(
                "nmcli", "-t", "-f", "DEVICE,TYPE,STATE,CONNECTION", "dev",
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL
            )
            out_dev, _ = await p_dev.communicate()
            for line in out_dev.decode("utf-8", errors="replace").splitlines():
                parts = line.split(":")
                if len(parts) >= 4 and parts[1] == "wifi" and "connected" in parts[2]:
                    connected = True
                    device_name = parts[0]
                    active_ssid = parts[3]
                    break
        except Exception:
            pass

        if connected:
            try:
                # Query signal for active connection with fast cache (no blocking air rescan)
                p_sig = await asyncio.create_subprocess_exec(
                    "nmcli", "-t", "-f", "IN-USE,SSID,SIGNAL", "dev", "wifi", "list", "--rescan", "no",
                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL
                )
                out_sig, _ = await p_sig.communicate()
                for line in out_sig.decode("utf-8", errors="replace").splitlines():
                    if line.startswith("*"):
                        parts = line.split(":")
                        if len(parts) >= 3:
                            try:
                                active_signal = int(parts[2])
                            except ValueError:
                                pass
                        break
            except Exception:
                pass

        icon = self._signal_to_icon(active_signal) if connected else "󰤮"
        return {
            "available": True,
            "enabled": enabled,
            "connected": connected,
            "ssid": active_ssid,
            "signal": active_signal,
            "device": device_name,
            "icon": icon,
            "state": "connected" if connected else "disconnected",
        }

    async def scan_networks(self, rescan: bool = True) -> list:
        """Scan for nearby Wi-Fi access points and return formatted list."""
        if not self.caps.has_nmcli:
            return []

        cmd = ["nmcli", "-t", "-f", "IN-USE,SSID,BSSID,SIGNAL,SECURITY,BARS", "dev", "wifi", "list"]
        if rescan:
            cmd.extend(["--rescan", "auto"])

        networks_map = {}
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL
            )
            out, _ = await proc.communicate()
            lines = out.decode("utf-8", errors="replace").splitlines()

            for line in lines:
                parts = re.split(r"(?<!\\):", line)
                if len(parts) < 6:
                    continue

                in_use = parts[0].strip() == "*"
                ssid = parts[1].strip()
                # Reconstruct escaped BSSID if colons were in it
                # nmcli -t escapes colons in fields like BSSID as \:
                raw_bssid = parts[2].replace(r"\:", ":").strip()
                try:
                    signal = int(parts[3].strip())
                except ValueError:
                    signal = 0
                security = parts[4].strip()
                bars = parts[5].strip() if len(parts) > 5 else ""

                if not ssid:
                    ssid = "<Hidden Network>"

                icon = self._signal_to_icon(signal)
                is_secure = bool(security)

                # Keep highest signal per SSID
                if ssid not in networks_map or signal > networks_map[ssid]["signal"] or in_use:
                    networks_map[ssid] = {
                        "ssid": ssid,
                        "bssid": raw_bssid,
                        "signal": signal,
                        "security": security,
                        "is_secure": is_secure,
                        "in_use": in_use,
                        "bars": bars,
                        "icon": icon,
                    }

        except Exception as e:
            log.warning(f"Error scanning Wi-Fi networks: {e}")

        # Sort: connected first, then highest signal
        result = list(networks_map.values())
        result.sort(key=lambda n: (not n["in_use"], -n["signal"]))
        return result

    async def connect(self, ssid: str, password: str = "", bssid: str = "") -> dict:
        """Connect to target Wi-Fi SSID with optional password/bssid."""
        if not self.caps.has_nmcli:
            return {"status": "error", "message": "nmcli is not installed"}

        if not ssid:
            return {"status": "error", "message": "SSID cannot be empty"}

        # Emit connecting transient state
        ev = IslandState(
            source="network",
            state="network",
            priority=Priority.CONNECTIVITY,
            icon="󰤩",
            title="Connecting…",
            subtitle=ssid if not self.config.network_ssid_privacy else "Wi-Fi Network",
            css_class="network connecting",
            duration=4.0
        )
        self.on_transient_event(ev)

        cmd = ["nmcli", "dev", "wifi", "connect", ssid]
        if password:
            cmd.extend(["password", password])
        if bssid:
            cmd.extend(["bssid", bssid])

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            out, err = await proc.communicate()
            if proc.returncode == 0:
                success_ev = IslandState(
                    source="network",
                    state="network",
                    priority=Priority.CONNECTIVITY,
                    icon="󰤨",
                    title="Connected",
                    subtitle=ssid if not self.config.network_ssid_privacy else "Wi-Fi Connected",
                    css_class="network connected",
                    duration=3.0
                )
                self.on_transient_event(success_ev)
                return {"status": "ok", "message": f"Connected to '{ssid}'", "ssid": ssid}
            else:
                err_msg = err.decode("utf-8", errors="replace").strip() or out.decode("utf-8", errors="replace").strip()
                fail_ev = IslandState(
                    source="network",
                    state="network",
                    priority=Priority.CONNECTIVITY,
                    icon="󰤮",
                    title="Connection Failed",
                    subtitle=err_msg[:30] if err_msg else "Could not connect",
                    css_class="network error",
                    duration=3.0
                )
                self.on_transient_event(fail_ev)
                return {"status": "error", "message": err_msg, "ssid": ssid}
        except Exception as e:
            return {"status": "error", "message": str(e), "ssid": ssid}

    async def disconnect(self, device: str = "") -> dict:
        """Disconnect active Wi-Fi connection."""
        if not self.caps.has_nmcli:
            return {"status": "error", "message": "nmcli is not installed"}

        target_dev = device
        if not target_dev:
            status = await self.get_wifi_status()
            target_dev = status.get("device", "")

        cmd = ["nmcli", "dev", "disconnect", target_dev] if target_dev else ["nmcli", "networking", "off"]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            out, err = await proc.communicate()
            if proc.returncode == 0:
                ev = IslandState(
                    source="network",
                    state="network",
                    priority=Priority.CONNECTIVITY,
                    icon="󰤮",
                    title="Disconnected",
                    subtitle="Wi-Fi Disconnected",
                    css_class="network disconnected",
                    duration=2.5
                )
                self.on_transient_event(ev)
                return {"status": "ok", "message": "Wi-Fi disconnected"}
            return {"status": "error", "message": err.decode().strip()}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def toggle_radio(self, enable: Any = None) -> dict:
        """Toggle Wi-Fi radio on or off."""
        if not self.caps.has_nmcli:
            return {"status": "error", "message": "nmcli is not installed"}

        current_status = await self.get_wifi_status()
        target = not current_status.get("enabled", True) if enable is None else bool(enable)
        arg = "on" if target else "off"

        try:
            proc = await asyncio.create_subprocess_exec(
                "nmcli", "radio", "wifi", arg,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await proc.communicate()
            ev = IslandState(
                source="network",
                state="network",
                priority=Priority.CONNECTIVITY,
                icon="󰤨" if target else "󰤮",
                title="Wi-Fi " + ("On" if target else "Off"),
                subtitle="Radio " + ("Enabled" if target else "Disabled"),
                css_class="network",
                duration=2.0
            )
            self.on_transient_event(ev)
            return {"status": "ok", "enabled": target}
        except Exception as e:
            return {"status": "error", "message": str(e)}
