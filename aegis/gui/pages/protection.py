import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw

class ProtectionPage(Adw.Bin):
    def __init__(self):
        super().__init__()

        status_page = Adw.StatusPage()
        status_page.set_icon_name("security-high-symbolic")
        status_page.set_title("Protection & Rules Manager")
        status_page.set_description("Interactive whitelist and expendables manager are coming in Phase 3.")
        self.set_child(status_page)
