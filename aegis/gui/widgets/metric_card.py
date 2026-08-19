import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw

class MetricCard(Gtk.Frame):
    def __init__(self, title: str, icon_name: str):
        super().__init__()
        self.add_css_class("card")
        self.set_hexpand(True)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        self.set_child(box)

        # Header Row: Icon + Metric Name
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        
        self.icon = Gtk.Image.new_from_icon_name(icon_name)
        self.icon.set_pixel_size(20)
        header_box.append(self.icon)

        title_label = Gtk.Label(label=title.upper())
        title_label.add_css_class("heading")
        title_label.add_css_class("dim-label")
        title_label.set_halign(Gtk.Align.START)
        header_box.append(title_label)

        box.append(header_box)

        # Value Label
        self.value_label = Gtk.Label(label="N/A")
        self.value_label.add_css_class("title-2")
        self.value_label.set_halign(Gtk.Align.START)
        box.append(self.value_label)

        # Level Bar / Progress Bar
        self.level_bar = Gtk.LevelBar()
        self.level_bar.set_min_value(0.0)
        self.level_bar.set_max_value(1.0)
        self.level_bar.set_value(0.0)
        box.append(self.level_bar)

    def set_metric(self, value_text: str, fraction: float = 0.0):
        self.value_label.set_label(value_text)
        frac = max(0.0, min(1.0, fraction))
        self.level_bar.set_value(frac)
