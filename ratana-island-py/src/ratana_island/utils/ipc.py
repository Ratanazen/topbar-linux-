"""UNIX domain socket IPC for Ratana Island."""

import os
import socket
from pathlib import Path
from typing import Callable, Optional


def get_socket_path() -> Path:
    runtime_dir = os.environ.get("XDG_RUNTIME_DIR")
    if runtime_dir and os.path.isdir(runtime_dir):
        return Path(runtime_dir) / "ratana-island.sock"
    return Path(f"/tmp/ratana-island-{os.getuid()}.sock")


def send_ipc_command(command: str, timeout: float = 2.0) -> Optional[str]:
    """Sends a command to the running instance. Returns response string or None if not running."""
    sock_path = get_socket_path()
    if not sock_path.exists():
        return None

    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect(str(sock_path))
        sock.sendall((command.strip() + "\n").encode("utf-8"))
        response = sock.recv(1024).decode("utf-8").strip()
        sock.close()
        return response
    except (socket.error, socket.timeout):
        return None


class IPCServer:
    def __init__(self, command_handler: Callable[[str], str]):
        self.sock_path = get_socket_path()
        self.command_handler = command_handler
        self.server_sock: Optional[socket.socket] = None
        self._io_watch_id: Optional[int] = None

    def start(self) -> bool:
        if self.sock_path.exists():
            # Check if an existing server is alive
            ping = send_ipc_command("ping", timeout=0.5)
            if ping is not None:
                # Already running!
                return False
            # Stale socket, remove it
            try:
                self.sock_path.unlink()
            except OSError:
                pass

        try:
            self.server_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.server_sock.bind(str(self.sock_path))
            self.server_sock.listen(5)
            self.server_sock.setblocking(False)

            # Integrate with GLib MainLoop
            import gi
            from gi.repository import GLib

            channel = GLib.IOChannel.unix_new(self.server_sock.fileno())
            self._io_watch_id = GLib.io_add_watch(
                channel,
                GLib.PRIORITY_DEFAULT,
                GLib.IOCondition.IN | GLib.IOCondition.HUP,
                self._on_client_connect,
            )
            return True
        except Exception:
            return False

    def _on_client_connect(self, channel, condition) -> bool:
        if not self.server_sock:
            return False

        try:
            conn, _ = self.server_sock.accept()
            conn.settimeout(1.0)
            data = conn.recv(1024).decode("utf-8").strip()
            if data:
                resp = self.command_handler(data)
                conn.sendall((str(resp) + "\n").encode("utf-8"))
            conn.close()
        except Exception:
            pass

        return True

    def stop(self) -> None:
        if self._io_watch_id:
            import gi
            from gi.repository import GLib
            GLib.source_remove(self._io_watch_id)
            self._io_watch_id = None

        if self.server_sock:
            try:
                self.server_sock.close()
            except Exception:
                pass
            self.server_sock = None

        if self.sock_path.exists():
            try:
                self.sock_path.unlink()
            except OSError:
                pass
