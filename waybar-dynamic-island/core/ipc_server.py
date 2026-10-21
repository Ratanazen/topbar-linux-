"""
Ratana Dynamic Island — IPC Server
==================================
Secure Unix domain socket server running at $XDG_RUNTIME_DIR/ratana-island.sock (0o600).
Validates messages, enforces size bounds, and broadcasts state snapshots.
"""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any, Callable, Coroutine, Dict, List, Optional

from core.config_manager import PROTOCOL_VERSION

log = logging.getLogger("ratana-island")

MAX_MESSAGE_SIZE = 65536  # 64 KB maximum request limit


class IpcServer:
    def __init__(
        self,
        socket_path: Path,
        dispatch_handler: Callable[[str, Dict[str, Any], asyncio.StreamWriter], Coroutine[Any, Any, Optional[Dict[str, Any]]]],
        initial_state_provider: Optional[Callable[[], str]] = None
    ):
        self.socket_path = socket_path
        self.dispatch_handler = dispatch_handler
        self.initial_state_provider = initial_state_provider
        self.server: Optional[asyncio.Server] = None
        self.client_writers: List[asyncio.StreamWriter] = []

    async def start(self):
        """Bind and start listening on the Unix domain socket with strict 0o600 permissions."""
        if self.socket_path.exists():
            try:
                self.socket_path.unlink()
            except OSError as e:
                log.warning(f"Could not remove stale socket at {self.socket_path}: {e}")

        self.server = await asyncio.start_unix_server(
            self.handle_client,
            path=str(self.socket_path)
        )
        try:
            os.chmod(self.socket_path, 0o600)
        except OSError as e:
            log.warning(f"Could not set 0o600 permissions on socket: {e}")
        log.info(f"IPC Server listening at {self.socket_path} (mode 0600)")

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handles an individual client connection with length limits and input validation."""
        try:
            raw_data = await asyncio.wait_for(reader.readline(), timeout=5.0)
            if not raw_data:
                writer.close()
                return

            if len(raw_data) > MAX_MESSAGE_SIZE:
                err_resp = {
                    "protocol_version": PROTOCOL_VERSION,
                    "version": 1,
                    "status": "error",
                    "message": "Payload exceeds maximum allowed size (64KB)"
                }
                writer.write((json.dumps(err_resp) + "\n").encode("utf-8"))
                await writer.drain()
                writer.close()
                return

            line = raw_data.decode("utf-8", errors="replace").strip()

            # Handle streaming mode (continuous state subscriber)
            if line.startswith("stream"):
                if writer not in self.client_writers:
                    self.client_writers.append(writer)
                if self.initial_state_provider:
                    try:
                        init_line = self.initial_state_provider()
                        if init_line:
                            writer.write((init_line + "\n").encode("utf-8"))
                            await writer.drain()
                    except Exception as e:
                        log.debug(f"Error sending initial state: {e}")
                return

            # Parse JSON command
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                err_resp = {
                    "protocol_version": PROTOCOL_VERSION,
                    "version": 1,
                    "status": "error",
                    "message": "Malformed JSON payload"
                }
                writer.write((json.dumps(err_resp) + "\n").encode("utf-8"))
                await writer.drain()
                writer.close()
                return

            if not isinstance(payload, dict):
                err_resp = {
                    "protocol_version": PROTOCOL_VERSION,
                    "version": 1,
                    "status": "error",
                    "message": "Payload must be a JSON object"
                }
                writer.write((json.dumps(err_resp) + "\n").encode("utf-8"))
                await writer.drain()
                writer.close()
                return

            # Extract command and arguments
            command = payload.get("command") or payload.get("action")
            if not command or not isinstance(command, str):
                err_resp = {
                    "protocol_version": PROTOCOL_VERSION,
                    "version": 1,
                    "status": "error",
                    "message": "Missing or invalid 'command' string field"
                }
                writer.write((json.dumps(err_resp) + "\n").encode("utf-8"))
                await writer.drain()
                writer.close()
                return

            args = payload.get("args", {})
            if not isinstance(args, dict):
                args = {}

            # Execute dispatch handler
            response = await self.dispatch_handler(command, args, writer)
            if response is not None:
                if "protocol_version" not in response:
                    response["protocol_version"] = PROTOCOL_VERSION
                if "version" not in response:
                    response["version"] = 1
                writer.write((json.dumps(response, ensure_ascii=False) + "\n").encode("utf-8"))
                await writer.drain()

            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass
        except asyncio.TimeoutError:
            writer.close()
        except Exception as e:
            log.error(f"IPC Client Exception: {e}")
            try:
                writer.close()
            except Exception:
                pass

    def broadcast_stream(self, stream_line: str):
        """Sends a JSON line to all connected streaming clients (e.g. Quickshell)."""
        dead_writers = []
        data = (stream_line + "\n").encode("utf-8")
        for writer in self.client_writers:
            try:
                writer.write(data)
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(writer.drain())
                except RuntimeError:
                    pass
            except Exception:
                dead_writers.append(writer)

        for w in dead_writers:
            if w in self.client_writers:
                self.client_writers.remove(w)

    async def close(self):
        """Closes server and clears client streams."""
        for writer in self.client_writers:
            try:
                writer.close()
            except Exception:
                pass
        self.client_writers.clear()

        if self.server:
            self.server.close()
            await self.server.wait_closed()
        if self.socket_path.exists():
            try:
                self.socket_path.unlink()
            except OSError:
                pass
