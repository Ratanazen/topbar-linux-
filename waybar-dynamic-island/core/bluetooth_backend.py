"""
Ratana Dynamic Island — Bluetooth Backend
=========================================
Implements BlueZ D-Bus integration with bluetoothctl fallback.
Supports device discovery, connection lifecycle, and priority-aware capsule states.
"""

import asyncio
import logging
import re
import shutil
from typing import Any, Callable, Dict, List, Optional

from core.priority_manager import Priority
from core.state_manager import IslandState

log = logging.getLogger("ratana-island")


class BluetoothBackend:
    def __init__(self, config: Any, on_transient_event: Callable[[IslandState], None]):
        self.config = config
        self.on_transient_event = on_transient_event
        self.has_bluez = False
        self.bus = None
        self.adapter_powered = False
        self.adapter_discovering = False
        self.connected_devices: Dict[str, Dict[str, Any]] = {}
        self.paired_devices: Dict[str, Dict[str, Any]] = {}

        self._init_dbus()

    def _init_dbus(self):
        try:
            import dbus
            self.bus = dbus.SystemBus()
            self.has_bluez = True
        except Exception as e:
            log.info(f"BlueZ D-Bus not available ({e}). Using bluetoothctl fallback.")
            self.has_bluez = False

    async def run_monitor(self):
        """Monitors Bluetooth device state changes and adapter transitions."""
        if not shutil.which("bluetoothctl") and not self.has_bluez:
            log.info("Neither BlueZ D-Bus nor bluetoothctl found. Bluetooth backend disabled.")
            return

        last_connected_macs = set()

        while True:
            try:
                status = await self.fetch_status()
                current_connected = {d["mac"]: d for d in status.get("connected_devices", [])}
                current_macs = set(current_connected.keys())

                # Detect newly connected devices
                newly_connected = current_macs - last_connected_macs
                for mac in newly_connected:
                    dev = current_connected[mac]
                    name = dev.get("name") or dev.get("alias") or mac
                    battery = dev.get("battery")
                    sub = f"{name} • {battery}%" if battery is not None else name
                    icon = "󰂱"
                    if dev.get("icon") in ("audio-headset", "audio-headphones"):
                        icon = "󰋋"

                    ev = IslandState(
                        source="bluetooth",
                        state="bluetooth",
                        priority=Priority.BLUETOOTH_CONNECTED,
                        icon=icon,
                        title="Connected",
                        subtitle=sub,
                        css_class="bluetooth connected",
                        tooltip=f"Bluetooth: Connected to {name}\nMAC: {mac}",
                        duration=4.0
                    )
                    self.on_transient_event(ev)

                # Detect disconnected devices
                newly_disconnected = last_connected_macs - current_macs
                for mac in newly_disconnected:
                    # Look up name from paired cache
                    dev_name = self.paired_devices.get(mac, {}).get("name", mac)
                    ev = IslandState(
                        source="bluetooth",
                        state="bluetooth",
                        priority=Priority.BLUETOOTH_CONNECTED,
                        icon="󰂲",
                        title="Disconnected",
                        subtitle=dev_name,
                        css_class="bluetooth disconnected",
                        tooltip=f"Bluetooth: Disconnected from {dev_name}",
                        duration=3.0
                    )
                    self.on_transient_event(ev)

                last_connected_macs = current_macs
            except Exception as e:
                log.debug(f"Bluetooth poll error: {e}")

            await asyncio.sleep(2.0)

    async def fetch_status(self) -> Dict[str, Any]:
        """Queries BlueZ D-Bus or bluetoothctl for adapter and device states."""
        if self.has_bluez and self.bus:
            try:
                import dbus
                manager = dbus.Interface(
                    self.bus.get_object("org.bluez", "/"),
                    "org.freedesktop.DBus.ObjectManager"
                )
                objects = manager.GetManagedObjects()

                self.adapter_powered = False
                self.adapter_discovering = False
                self.connected_devices.clear()
                self.paired_devices.clear()

                for path, ifaces in objects.items():
                    if "org.bluez.Adapter1" in ifaces:
                        adap = ifaces["org.bluez.Adapter1"]
                        self.adapter_powered = bool(adap.get("Powered", False))
                        self.adapter_discovering = bool(adap.get("Discovering", False))

                    if "org.bluez.Device1" in ifaces:
                        dev = ifaces["org.bluez.Device1"]
                        mac = str(dev.get("Address", ""))
                        name = str(dev.get("Name", dev.get("Alias", mac)))
                        is_connected = bool(dev.get("Connected", False))
                        is_paired = bool(dev.get("Paired", False))
                        icon = str(dev.get("Icon", "bluetooth"))

                        battery = None
                        if "org.bluez.Battery1" in ifaces:
                            battery = int(ifaces["org.bluez.Battery1"].get("Percentage", 0))

                        info = {
                            "mac": mac,
                            "name": name,
                            "icon": icon,
                            "connected": is_connected,
                            "paired": is_paired,
                            "battery": battery,
                        }

                        if is_paired:
                            self.paired_devices[mac] = info
                        if is_connected:
                            self.connected_devices[mac] = info

                state = "idle"
                if not self.adapter_powered:
                    state = "adapter_off"
                elif self.connected_devices:
                    state = "connected"
                elif self.adapter_discovering:
                    state = "scanning"

                return {
                    "backend": "bluez-dbus",
                    "available": True,
                    "adapter_powered": self.adapter_powered,
                    "discovering": self.adapter_discovering,
                    "state": state,
                    "connected_devices": list(self.connected_devices.values()),
                    "paired_devices": list(self.paired_devices.values()),
                }
            except Exception as e:
                log.debug(f"BlueZ D-Bus query failed, falling back to CLI: {e}")

        # bluetoothctl CLI fallback
        return await self._fetch_status_cli()

    async def _fetch_status_cli(self) -> Dict[str, Any]:
        if not shutil.which("bluetoothctl"):
            return {
                "backend": "none",
                "available": False,
                "state": "unavailable",
                "adapter_powered": False,
                "connected_devices": [],
                "paired_devices": [],
            }

        try:
            p_show = await asyncio.create_subprocess_exec(
                "bluetoothctl", "show",
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL
            )
            out_show, _ = await p_show.communicate()
            show_text = out_show.decode("utf-8", errors="replace")
            powered = "Powered: yes" in show_text
            discovering = "Discovering: yes" in show_text

            p_paired = await asyncio.create_subprocess_exec(
                "bluetoothctl", "devices", "Paired",
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL
            )
            out_paired, _ = await p_paired.communicate()

            p_conn = await asyncio.create_subprocess_exec(
                "bluetoothctl", "devices", "Connected",
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL
            )
            out_conn, _ = await p_conn.communicate()

            paired_list = []
            for line in out_paired.decode("utf-8", errors="replace").splitlines():
                m = re.match(r"^Device\s+([0-9A-Fa-f:]+)\s+(.+)$", line.strip())
                if m:
                    paired_list.append({"mac": m.group(1), "name": m.group(2), "paired": True})

            connected_list = []
            for line in out_conn.decode("utf-8", errors="replace").splitlines():
                m = re.match(r"^Device\s+([0-9A-Fa-f:]+)\s+(.+)$", line.strip())
                if m:
                    connected_list.append({"mac": m.group(1), "name": m.group(2), "connected": True})

            state = "connected" if connected_list else ("scanning" if discovering else ("adapter_off" if not powered else "idle"))

            return {
                "backend": "bluetoothctl",
                "available": True,
                "adapter_powered": powered,
                "discovering": discovering,
                "state": state,
                "connected_devices": connected_list,
                "paired_devices": paired_list,
            }
        except Exception as e:
            return {
                "backend": "error",
                "available": False,
                "error": str(e),
                "state": "failed",
                "connected_devices": [],
                "paired_devices": [],
            }

    async def connect(self, device_id: str) -> Dict[str, Any]:
        """Initiates connection to target MAC or device name."""
        mac = self._resolve_mac(device_id)
        if not mac:
            return {"status": "error", "message": f"Device '{device_id}' not found in paired devices"}

        dev_name = self.paired_devices.get(mac, {}).get("name", mac)

        # Emit connecting transient state
        ev = IslandState(
            source="bluetooth",
            state="bluetooth",
            priority=Priority.BLUETOOTH_CONNECTING,
            icon="󰂰",
            title="Connecting…",
            subtitle=dev_name,
            css_class="bluetooth connecting",
            tooltip=f"Connecting to {dev_name} ({mac})",
            duration=5.0
        )
        self.on_transient_event(ev)

        try:
            proc = await asyncio.create_subprocess_exec(
                "bluetoothctl", "connect", mac,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL
            )
            stdout, _ = await proc.communicate()
            out_str = stdout.decode("utf-8", errors="replace")

            if "Connection successful" in out_str or proc.returncode == 0:
                # Emit connected confirmation
                conn_ev = IslandState(
                    source="bluetooth",
                    state="bluetooth",
                    priority=Priority.BLUETOOTH_CONNECTED,
                    icon="󰂱",
                    title="Connected",
                    subtitle=dev_name,
                    css_class="bluetooth connected",
                    duration=4.0
                )
                self.on_transient_event(conn_ev)
                return {"status": "ok", "message": f"Connected to {dev_name} ({mac})"}
            else:
                fail_ev = IslandState(
                    source="bluetooth",
                    state="bluetooth",
                    priority=Priority.BLUETOOTH_CONNECTING,
                    icon="󰂲",
                    title="Connection Failed",
                    subtitle=dev_name,
                    css_class="bluetooth error",
                    duration=4.0
                )
                self.on_transient_event(fail_ev)
                return {"status": "error", "message": f"Failed to connect to {dev_name}: {out_str.strip()}"}
        except Exception as e:
            return {"status": "error", "message": f"Error executing connect: {e}"}

    async def disconnect(self, device_id: Optional[str] = None) -> Dict[str, Any]:
        """Disconnects a specific device or all active connections."""
        target_mac = self._resolve_mac(device_id) if device_id else None
        if not target_mac:
            # Pick first connected device if none specified
            status = await self.fetch_status()
            conn = status.get("connected_devices", [])
            if conn:
                target_mac = conn[0]["mac"]

        if not target_mac:
            return {"status": "error", "message": "No active device to disconnect"}

        try:
            proc = await asyncio.create_subprocess_exec(
                "bluetoothctl", "disconnect", target_mac,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL
            )
            stdout, _ = await proc.communicate()
            return {"status": "ok", "message": f"Disconnected {target_mac}"}
        except Exception as e:
            return {"status": "error", "message": f"Error disconnecting: {e}"}

    async def scan(self, duration: int = 10) -> Dict[str, Any]:
        """Initiates a temporary discovery scan."""
        try:
            # Start scan in background
            await asyncio.create_subprocess_exec("bluetoothctl", "--timeout", str(duration), "scan", "on")
        except Exception as e:
            return {"status": "error", "message": f"Scan failed: {e}"}

    async def toggle_power(self, enable: Optional[bool] = None) -> Dict[str, Any]:
        """Toggles or sets Bluetooth adapter power state."""
        try:
            status = await self.fetch_status()
            current_powered = status.get("adapter_powered", False)
            target = not current_powered if enable is None else bool(enable)
            arg = "power on" if target else "power off"

            proc = await asyncio.create_subprocess_exec(
                "bluetoothctl", *arg.split(),
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL
            )
            await proc.communicate()

            ev = IslandState(
                source="bluetooth",
                state="bluetooth",
                priority=Priority.BLUETOOTH_CONNECTED,
                icon="󰂯" if target else "󰂲",
                title="Bluetooth " + ("On" if target else "Off"),
                subtitle="Adapter " + ("Powered On" if target else "Powered Off"),
                css_class="bluetooth",
                duration=2.0
            )
            self.on_transient_event(ev)
            return {"status": "ok", "powered": target}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _resolve_mac(self, device_id: str) -> Optional[str]:
        device_id = device_id.strip()
        # Direct MAC pattern
        if re.match(r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$", device_id):
            return device_id.replace("-", ":").upper()

        # Search by name in paired devices
        lower = device_id.lower()
        for mac, dev in self.paired_devices.items():
            if lower in dev.get("name", "").lower():
                return mac
        return None
