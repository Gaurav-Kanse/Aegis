import os
import sys
import time
import subprocess
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib, Gdk
from typing import Optional, Dict, Any

from aegis.gui.client import GUIIPCClient
from aegis.gui.pages.overview import OverviewPage
from aegis.gui.pages.processes import ProcessesPage
from aegis.gui.pages.analytics import AnalyticsPage
from aegis.gui.pages.events import EventsPage
from aegis.gui.pages.protection import ProtectionPage
from aegis.gui.pages.settings import SettingsPage

PAGES = [
    ("overview", "Overview", "security-high-symbolic"),
    ("processes", "Processes", "system-run-symbolic"),
    ("analytics", "Analytics", "utilities-system-monitor-symbolic"),
    ("events", "Events", "dialog-warning-symbolic"),
    ("protection", "Protection", "emblem-readonly-symbolic"),
    ("settings", "Settings", "emblem-system-symbolic"),
]

class AegisWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application, ipc_client: GUIIPCClient):
        super().__init__(application=app)
        self.ipc_client = ipc_client
        self.start_time = time.time()

        self.set_title("Aegis System Monitor")
        self.set_default_size(1080, 720)
        self.set_hide_on_close(False)
        self.add_css_class("main-window")

        # Main Outer Box (Horizontal for Sidebar + Content)
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.set_content(self.main_box)

        # ---------------- 1. Right Content Area First ----------------
        content_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        content_vbox.set_hexpand(True)
        content_vbox.set_vexpand(True)
        self.main_box.append(content_vbox)

        # Header Bar
        self.header_bar = Adw.HeaderBar()
        content_vbox.append(self.header_bar)

        # Main Stack for App vs Offline Page
        self.overlay_stack = Gtk.Stack()
        self.overlay_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.overlay_stack.set_vexpand(True)
        content_vbox.append(self.overlay_stack)

        # View Stack for Pages
        self.view_stack = Adw.ViewStack()
        self.view_stack.set_vexpand(True)
        self.overlay_stack.add_named(self.view_stack, "online")

        # Instantiate Pages
        self.page_overview = OverviewPage(self.ipc_client, self.switch_page)
        self.view_stack.add_named(self.page_overview, "overview")

        self.page_processes = ProcessesPage(self.ipc_client)
        self.view_stack.add_named(self.page_processes, "processes")

        self.page_analytics = AnalyticsPage(self.ipc_client)
        self.view_stack.add_named(self.page_analytics, "analytics")

        self.page_events = EventsPage(self.ipc_client)
        self.view_stack.add_named(self.page_events, "events")

        self.page_protection = ProtectionPage(self.ipc_client)
        self.view_stack.add_named(self.page_protection, "protection")

        self.page_settings = SettingsPage(self.ipc_client)
        self.view_stack.add_named(self.page_settings, "settings")

        # Build Offline View
        self._build_offline_view()

        # ---------------- 2. Left Sidebar Navigation ----------------
        self._build_sidebar()

    def _build_sidebar(self):
        self.sidebar_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        self.sidebar_box.add_css_class("sidebar")
        self.sidebar_box.set_size_request(230, -1)
        self.sidebar_box.set_margin_start(12)
        self.sidebar_box.set_margin_end(12)
        self.sidebar_box.set_margin_top(16)
        self.sidebar_box.set_margin_bottom(16)
        self.main_box.prepend(self.sidebar_box)

        # Branding Header Box
        brand_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        brand_box.set_margin_start(8)

        icon_img = Gtk.Image.new_from_icon_name("security-high-symbolic")
        icon_img.set_pixel_size(24)
        brand_box.append(icon_img)

        title_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        lbl_brand = Gtk.Label(label="AEGIS")
        lbl_brand.add_css_class("sidebar-title")
        lbl_brand.set_halign(Gtk.Align.START)
        title_vbox.append(lbl_brand)

        lbl_sub = Gtk.Label(label="SYSTEM GUARDIAN")
        lbl_sub.add_css_class("sidebar-subtitle")
        lbl_sub.set_halign(Gtk.Align.START)
        title_vbox.append(lbl_sub)

        brand_box.append(title_vbox)
        self.sidebar_box.append(brand_box)

        # Nav Buttons List Box
        self.nav_btns: Dict[str, Gtk.Button] = {}
        nav_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        nav_vbox.set_margin_top(8)

        for name, label, icon in PAGES:
            btn = Gtk.Button()
            btn.add_css_class("sidebar-button")
            
            btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            img = Gtk.Image.new_from_icon_name(icon)
            img.set_pixel_size(16)
            btn_box.append(img)

            lbl = Gtk.Label(label=label)
            lbl.set_halign(Gtk.Align.START)
            btn_box.append(lbl)

            btn.set_child(btn_box)
            btn.connect("clicked", lambda b, n=name: self.switch_page(n))
            
            nav_vbox.append(btn)
            self.nav_btns[name] = btn

        self.sidebar_box.append(nav_vbox)

        # Spacer
        spacer = Gtk.Box()
        spacer.set_vexpand(True)
        self.sidebar_box.append(spacer)

        # Bottom Daemon Status Card
        daemon_card = Gtk.Frame()
        daemon_card.add_css_class("aegis-card")

        d_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        d_box.set_margin_start(12)
        d_box.set_margin_end(12)
        d_box.set_margin_top(12)
        d_box.set_margin_bottom(12)
        daemon_card.set_child(d_box)

        self.lbl_daemon_status = Gtk.Label(label="● Running")
        self.lbl_daemon_status.add_css_class("status-badge")
        self.lbl_daemon_status.add_css_class("normal")
        self.lbl_daemon_status.set_halign(Gtk.Align.START)
        d_box.append(self.lbl_daemon_status)

        self.lbl_uptime = Gtk.Label(label="Uptime: 0m")
        self.lbl_uptime.add_css_class("aegis-subtext")
        self.lbl_uptime.set_halign(Gtk.Align.START)
        d_box.append(self.lbl_uptime)

        self.btn_daemon_toggle = Gtk.Button(label="Stop Daemon")
        self.btn_daemon_toggle.add_css_class("action-btn-normal")
        self.btn_daemon_toggle.set_margin_top(4)
        self.btn_daemon_toggle.connect("clicked", self._on_daemon_toggle_clicked)
        d_box.append(self.btn_daemon_toggle)

        self.sidebar_box.append(daemon_card)

        # Highlight default page
        self.switch_page("overview")

    def switch_page(self, page_name: str):
        self.view_stack.set_visible_child_name(page_name)
        for name, btn in self.nav_btns.items():
            if name == page_name:
                btn.add_css_class("active")
            else:
                btn.remove_css_class("active")

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

        # Update daemon uptime widget
        elapsed = int(time.time() - self.start_time)
        m = elapsed // 60
        h = m // 60
        if h > 0:
            up_str = f"Uptime: {h}h {m % 60}m"
        else:
            up_str = f"Uptime: {m}m"
        self.lbl_uptime.set_text(up_str)
        self.lbl_daemon_status.set_text("● Running")
        self.lbl_daemon_status.add_css_class("normal")
        self.lbl_daemon_status.remove_css_class("critical")
        self.btn_daemon_toggle.set_label("Stop Daemon")

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
        self.lbl_daemon_status.set_text("○ Offline")
        self.lbl_daemon_status.add_css_class("critical")
        self.lbl_daemon_status.remove_css_class("normal")
        self.btn_daemon_toggle.set_label("Start Daemon")

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

    def _on_daemon_toggle_clicked(self, button):
        if self.btn_daemon_toggle.get_label() == "Start Daemon":
            self._on_start_daemon_clicked(button)
        else:
            self.show_offline()


class AegisApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="org.aegis.desktop", flags=0)
        self.ipc_client = GUIIPCClient(poll_interval=1.0)
        self.window: Optional[AegisWindow] = None

    def do_activate(self):
        # Force Dark Theme for Nothing-inspired aesthetic
        Adw.StyleManager.get_default().set_color_scheme(Adw.ColorScheme.PREFER_DARK)

        # Load Custom CSS Provider
        css_provider = Gtk.CssProvider()
        css_path = os.path.join(os.path.dirname(__file__), "style.css")
        if os.path.exists(css_path):
            css_provider.load_from_path(css_path)
            display = Gdk.Display.get_default()
            if display:
                Gtk.StyleContext.add_provider_for_display(
                    display,
                    css_provider,
                    Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
                )

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
