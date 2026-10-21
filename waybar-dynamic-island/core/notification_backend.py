"""
Ratana Dynamic Island — Notification Backend
============================================
Listens to D-Bus org.freedesktop.Notifications method calls and generates
priority-aware transient notification states.
"""

import asyncio
import logging
import re
from typing import Any, Callable

from core.priority_manager import Priority
from core.state_manager import IslandState, resolve_app_icon, truncate_text

log = logging.getLogger("ratana-island")


class NotificationBackend:
    def __init__(self, config: Any, caps: Any, on_transient_event: Callable[[IslandState], None]):
        self.config = config
        self.caps = caps
        self.on_transient_event = on_transient_event
        self._last_notif_payload = None

    async def run_monitor(self):
        if not self.config.enable_notifications or not self.caps.has_dbus_monitor:
            return

        cmd = [
            "dbus-monitor", "--session",
            "type='method_call',interface='org.freedesktop.Notifications',member='Notify'"
        ]

        while True:
            try:
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.DEVNULL
                )

                app_name = ""
                app_icon = ""
                summary = ""
                body = ""
                urgency = 1
                in_string = False
                current_string = []
                completed_strings = []
                last_dict_key = ""

                while True:
                    line = await proc.stdout.readline()
                    if not line:
                        break
                    raw_line = line.decode("utf-8", errors="replace")
                    stripped = raw_line.strip()

                    # Detect boundary of new D-Bus method call
                    if stripped.startswith("method call"):
                        app_name = ""
                        app_icon = ""
                        summary = ""
                        body = ""
                        urgency = 1
                        in_string = False
                        current_string = []
                        completed_strings = []
                        last_dict_key = ""
                        continue

                    # Handle multiline and single-line strings
                    if in_string:
                        if stripped.endswith('"') and not stripped.endswith(r'\"'):
                            current_string.append(stripped[:-1])
                            in_string = False
                            completed_strings.append("\n".join(current_string))
                            current_string = []
                        else:
                            current_string.append(raw_line.rstrip("\r\n"))
                        continue

                    if stripped.startswith('string "'):
                        content = stripped[8:]
                        if content.endswith('"') and not content.endswith(r'\"'):
                            val = content[:-1]
                            completed_strings.append(val)
                        else:
                            in_string = True
                            current_string = [content]
                        continue

                    # Capture urgency and hint variants
                    if 'string "urgency"' in stripped:
                        last_dict_key = "urgency"
                    elif last_dict_key == "urgency" and "variant" in stripped:
                        match_urg = re.search(r"byte\s+(\d+)", stripped)
                        if match_urg:
                            try:
                                urgency = int(match_urg.group(1))
                            except ValueError:
                                pass
                        last_dict_key = ""

                    # Map collected positional strings for Notify:
                    if len(completed_strings) >= 1 and not app_name:
                        app_name = completed_strings[0]
                    if len(completed_strings) >= 2 and not app_icon:
                        app_icon = completed_strings[1]
                    if len(completed_strings) >= 3 and not summary:
                        summary = completed_strings[2]
                    if len(completed_strings) >= 4 and not body:
                        body = completed_strings[3]

                    # Trigger notification once summary/body or expire_timeout is reached
                    if (summary or body) and (len(completed_strings) >= 4 or stripped.startswith("int32")):
                        notif_key = (app_name, summary, body, urgency)
                        if self._last_notif_payload != notif_key:
                            self._last_notif_payload = notif_key

                            is_urgent = (urgency == 2) or ("urgent" in (app_name + summary).lower())
                            priority = Priority.URGENT_NOTIF if is_urgent else Priority.NOTIFICATION
                            css = "notification urgent" if is_urgent else "notification"

                            icon = "󰵚" if is_urgent else resolve_app_icon(app_name, app_icon, summary)
                            disp_summary = truncate_text(summary or app_name, 22)
                            disp_body = truncate_text(body, 20) if body else ""
                            dur = (
                                self.config.urgent_notification_timeout_s
                                if is_urgent
                                else self.config.notification_timeout_s
                            )

                            state = IslandState(
                                source="notification",
                                state="notification",
                                priority=priority,
                                icon=icon,
                                title=disp_summary,
                                subtitle=disp_body,
                                css_class=css,
                                tooltip=f"App: {app_name}\nSummary: {summary}\n{body}\nClick to dismiss",
                                duration=dur
                            )
                            self.on_transient_event(state)

                await proc.wait()
            except Exception as e:
                log.warning(f"Notification monitor restart: {e}")
            await asyncio.sleep(2.0)
