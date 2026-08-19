import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Pango

class ShieldBadge(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)

        self.set_halign(Gtk.Align.CENTER)
        self.set_margin_top(18)
        self.set_margin_bottom(18)

        # Shield Icon Container
        self.icon_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.icon_box.set_halign(Gtk.Align.CENTER)

        self.icon_image = Gtk.Image.new_from_icon_name("security-high-symbolic")
        self.icon_image.set_pixel_size(72)
        self.icon_box.append(self.icon_image)

        self.append(self.icon_box)

        # App Title
        title_label = Gtk.Label(label="🛡 AEGIS")
        title_label.add_css_class("title-1")
        title_label.add_css_class("bold")
        self.append(title_label)

        # Status State Badge Label
        self.state_label = Gtk.Label(label="PROTECTED")
        self.state_label.add_css_class("title-3")
        self.state_label.add_css_class("success")
        self.append(self.state_label)

        # System Health Score Label
        self.health_label = Gtk.Label(label="SYSTEM HEALTH: N/A")
        self.health_label.add_css_class("body")
        self.health_label.add_css_class("dim-label")
        self.append(self.health_label)

    def set_status(self, health: int, state: str):
        self.health_label.set_label(f"SYSTEM HEALTH: {health}/100")
        self.state_label.set_label(state.upper())

        # Clear existing color classes
        for cls in ["success", "warning", "error", "accent"]:
            self.state_label.remove_css_class(cls)

        if state.upper() in ("PROTECTED", "NORMAL"):
            self.state_label.add_css_class("success")
            self.icon_image.set_from_icon_name("security-high-symbolic")
        elif state.upper() == "WARNING":
            self.state_label.add_css_class("warning")
            self.icon_image.set_from_icon_name("security-medium-symbolic")
        elif state.upper() in ("HIGH PRESSURE", "CRITICAL"):
            self.state_label.add_css_class("error")
            self.icon_image.set_from_icon_name("security-low-symbolic")
        elif state.upper() == "EMERGENCY":
            self.state_label.add_css_class("error")
            self.icon_image.set_from_icon_name("security-low-symbolic")
        else:
            self.state_label.add_css_class("accent")
            self.icon_image.set_from_icon_name("security-high-symbolic")
