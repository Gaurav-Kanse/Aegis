import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw

class ProcessRow(Adw.ActionRow):
    def __init__(self, pid: int, name: str, cpu: float, memory_str: str, score: float, status: str):
        super().__init__()
        self.set_title(name)
        self.set_subtitle(f"PID: {pid} • CPU: {cpu:.1f}% • RAM: {memory_str} • Score: {score:.2f}")

        # Status Tag Badge
        self.tag_label = Gtk.Label(label=status.upper())
        self.tag_label.add_css_class("caption")
        self.tag_label.set_valign(Gtk.Align.CENTER)
        
        if status.upper() == "PROTECTED":
            self.tag_label.add_css_class("success")
        elif status.upper() == "EXPENDABLE":
            self.tag_label.add_css_class("warning")

        self.add_suffix(self.tag_label)
