"""Notification capsule view for Ratana Island (GTK4)."""

from typing import Optional
import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Pango


class NotificationView(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.add_css_class("notification-box")
        self.set_valign(Gtk.Align.CENTER)
        self.set_halign(Gtk.Align.CENTER)

        # 1. Left Icon
        self.icon = Gtk.Image.new_from_icon_name("dialog-information-symbolic")
        self.icon.set_pixel_size(22)
        self.icon.add_css_class("notification-icon")
        self.append(self.icon)

        # 2. Text Container
        text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        text_box.set_valign(Gtk.Align.CENTER)
        text_box.set_hexpand(True)

        self.title_label = Gtk.Label(label="Notification")
        self.title_label.add_css_class("notification-title")
        self.title_label.set_xalign(0.0)
        self.title_label.set_ellipsize(Pango.EllipsizeMode.END)
        text_box.append(self.title_label)

        self.body_label = Gtk.Label(label="")
        self.body_label.add_css_class("notification-body")
        self.body_label.set_xalign(0.0)
        self.body_label.set_ellipsize(Pango.EllipsizeMode.END)
        text_box.append(self.body_label)

        self.append(text_box)

        # 3. Right Status Dot
        self.dot = Gtk.Label(label="•")
        self.dot.add_css_class("notification-dot")
        self.append(self.dot)

    def set_notification(self, title: str, body: str = "", icon_name: Optional[str] = None) -> None:
        self.title_label.set_text(title or "Notification")
        self.body_label.set_text(body or "")
        self.body_label.set_visible(bool(body))
        if icon_name:
            self.icon.set_from_icon_name(icon_name)
        else:
            self.icon.set_from_icon_name("dialog-information-symbolic")
