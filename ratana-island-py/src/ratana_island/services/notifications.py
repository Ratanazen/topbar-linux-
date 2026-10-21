"""Notification preview service for transient island alerts."""

import logging
from dataclasses import dataclass
from typing import Callable, Optional

logger = logging.getLogger("ratana_island.notifications")


@dataclass
class NotificationItem:
    app_name: str = ""
    summary: str = ""
    body: str = ""
    icon: Optional[str] = None
    timeout_ms: int = 5000


class NotificationService:
    def __init__(self, on_notification: Optional[Callable[[NotificationItem], None]] = None):
        self.on_notification = on_notification
        self.active_notification: Optional[NotificationItem] = None

    def post_alert(self, app_name: str, summary: str, body: str = "", timeout_ms: int = 5000) -> None:
        item = NotificationItem(
            app_name=app_name,
            summary=summary,
            body=body,
            timeout_ms=timeout_ms,
        )
        self.active_notification = item
        if self.on_notification:
            self.on_notification(item)

    def clear(self) -> None:
        self.active_notification = None
