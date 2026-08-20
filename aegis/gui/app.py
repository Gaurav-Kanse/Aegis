import sys
import subprocess
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib, Gdk

from aegis.gui.client import GUIIPCClient
from aegis.gui.pages.overview import OverviewPage
from aegis.gui.pages.processes import ProcessesPage
from aegis.gui.pages.analytics import AnalyticsPage
from aegis.gui.pages.events import EventsPage
from aegis.gui.pages.protection import ProtectionPage
from aegis.gui.pages.settings import SettingsPage

class AegisWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application, ipc_client: GUIIPCClient):
        super().__init__(application=app)
        self.ipc_client = ipc_client

        self.set_title("Aegis System Monitor")
        self.set_default_size(950, 700)
        self.set_hide_on_close(False)

        # Main Layout Box
        self.main_layout = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_content(self.main_layout)

        # Header Bar
        self.header_bar = Adw.HeaderBar()
        self.main_layout.append(self.header_bar)

        # View Stack & Switcher Title
        self.view_stack = Adw.ViewStack()
        self.view_stack.set_vexpand(True)

        self.switcher_title = Adw.ViewSwitcherTitle()
        self.switcher_title.set_stack(self.view_stack)
        self.header_bar.set_title_widget(self.switcher_title)

        # Main Stack for App vs Offline Page
        self.overlay_stack = Gtk.Stack()
        self.overlay_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.overlay_stack.set_vexpand(True)
        self.main_layout.append(self.overlay_stack)

        # Container for pages + switcher bar
        self.online_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.online_box.append(self.view_stack)

        # View Switcher Bar at Bottom
        self.switcher_bar = Adw.ViewSwitcherBar()
        self.switcher_bar.set_stack(self.view_stack)
        self.online_box.append(self.switcher_bar)

        self.overlay_stack.add_named(self.online_box, "online")

        # Build Pages
        self.page_overview = OverviewPage()
        self.view_stack.add_titled_with_icon(
            self.page_overview, "overview", "Overview", "security-high-symbolic"
        )

        self.page_processes = ProcessesPage(self.ipc_client)
        self.view_stack.add_titled_with_icon(
            self.page_processes, "processes", "Processes", "system-run-symbolic"
        )

        self.page_analytics = AnalyticsPage(self.ipc_client)
        self.view_stack.add_titled_with_icon(
            self.page_analytics, "analytics", "Analytics", "utilities-system-monitor-symbolic"
        )

        self.page_events = EventsPage(self.ipc_client)
        self.view_stack.add_titled_with_icon(
            self.page_events, "events", "Events", "dialog-warning-symbolic"
        )

        self.page_protection = ProtectionPage(self.ipc_client)
        self.view_stack.add_titled_with_icon(
            self.page_protection, "protection", "Protection", "emblem-readonly-symbolic"
        )

        self.page_settings = SettingsPage(self.ipc_client)
        self.view_stack.add_titled_with_icon(
            self.page_settings, "settings", "Settings", "emblem-system-symbolic"
        )

        # Build Offline View
        self._build_offline_view()

    def _build_offline_view(self):
        offline_page = Adw.StatusPage()
        offline_page.set_icon_name("network-error-symbolic")
        offline_page.set_title("Aegis Offline")
        offline_page.set_description("The Aegis daemon is not currently running.")

        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        btn_box.set_halign(Gtk.Align.CENTER)
        btn_box.set_margin_top(12)

        btn_retry = Gtk.Button(label="Retry")
        btn_retry.add_css_class("suggested-action")
        btn_retry.connect("clicked", self._on_retry_clicked)
        btn_box.append(btn_retry)

        btn_start = Gtk.Button(label="Start Daemon")
        btn_start.connect("clicked", self._on_start_daemon_clicked)
        btn_box.append(btn_start)

        offline_page.set_child(btn_box)
        self.overlay_stack.add_named(offline_page, "offline")

    def show_online(self, status: dict):
        self.overlay_stack.set_visible_child_name("online")
        self.page_settings.set_offline(False)
        self.page_overview.update_data(status)
        self.page_analytics.update_sample(status)
        self.ipc_client.fetch_processes_async(self._on_processes_response)
        self.ipc_client.fetch_events_async(100, self._on_events_response)
        self.ipc_client.fetch_protection_async(self._on_protection_response)
        self.ipc_client.fetch_config_async(self._on_config_response)

    def _on_processes_response(self, procs, err):
        if procs is not None and isinstance(procs, list):
            self.page_processes.update_processes(procs)
            self.page_protection.update_active_processes(procs)

    def _on_events_response(self, events, err):
        if events is not None and isinstance(events, list):
            self.page_events.append_events(events)

    def _on_protection_response(self, prot, err):
        if prot is not None and isinstance(prot, dict):
            self.page_protection.update_protection(prot.get("protected", []), prot.get("expendable", []))

    def _on_config_response(self, cfg, err):
        if cfg is not None and isinstance(cfg, dict):
            self.page_settings.update_config(cfg)

    def _on_metrics_history_response(self, history, err):
        if history is not None and isinstance(history, list):
            self.page_analytics.set_metrics_history(history)

    def show_offline(self):
        self.overlay_stack.set_visible_child_name("offline")
        self.page_settings.set_offline(True)

    def _on_retry_clicked(self, button):
        self.ipc_client.fetch_status_async(self._on_retry_response)

    def _on_retry_response(self, res, err):
        if res is not None:
            self.show_online(res)
        else:
            self.show_offline()

    def _on_start_daemon_clicked(self, button):
        try:
            subprocess.Popen(["aegis", "daemon"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            GLib.timeout_add(1000, lambda: self._on_retry_clicked(None) or False)
        except Exception as e:
            print(f"[aegis-gui] Failed to start daemon: {e}")


class AegisApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="org.aegis.desktop", flags=0)
        self.ipc_client = GUIIPCClient(poll_interval=1.0)
        self.window: Optional[AegisWindow] = None

    def do_activate(self):
        if not self.window:
            self.window = AegisWindow(self, self.ipc_client)
            self.ipc_client.start_polling(
                on_status_updated=self.window.show_online,
                on_offline_state=self.window.show_offline
            )
            self.ipc_client.fetch_metrics_history_async(300, self.window._on_metrics_history_response)

        self.window.present()

    def do_shutdown(self):
        self.ipc_client.stop_polling()
        Adw.Application.do_shutdown(self)


def run_gui(argv=None):
    app = AegisApp()
    return app.run(argv or sys.argv)
