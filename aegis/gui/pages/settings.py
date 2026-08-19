import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw

class SettingsPage(Adw.Bin):
    def __init__(self):
        super().__init__()

        status_page = Adw.StatusPage()
        status_page.set_icon_name("emblem-system-symbolic")
        status_page.set_title("Aegis Daemon Settings")
        status_page.set_description("GUI preference controls for memory thresholds and policy weights are coming in Phase 3.")
        self.set_child(status_page)
