import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib
from datetime import datetime
from typing import List, Dict, Any, Optional, Set

from aegis.gui.client import GUIIPCClient

SEVERITY_OPTIONS = ["ALL SEVERITIES", "INFO", "WARNING", "CRITICAL / ERROR"]

class EventsPage(Gtk.Box):
    def __init__(self, ipc_client: Optional[GUIIPCClient] = None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.ipc_client = ipc_client

        self.events: List[Dict[str, Any]] = []
        self.seen_ids: Set[str] = set()

        # Scrolled Container
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        self.append(scrolled)

        clamp = Adw.Clamp()
        clamp.set_maximum_size(1000)
        scrolled.set_child(clamp)

        main_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        main_vbox.set_margin_start(20)
        main_vbox.set_margin_end(20)
        main_vbox.set_margin_top(20)
        main_vbox.set_margin_bottom(28)
        clamp.set_child(main_vbox)

        # Header Title
        hdr_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        title_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)

        lbl_title = Gtk.Label(label="Events")
        lbl_title.add_css_class("title-1")
        lbl_title.add_css_class("bold")
        lbl_title.set_halign(Gtk.Align.START)
        title_vbox.append(lbl_title)

        lbl_sub = Gtk.Label(label="Audit log of resource warnings, recovery actions, and system protection events.")
        lbl_sub.add_css_class("aegis-subtext")
        lbl_sub.set_halign(Gtk.Align.START)
        title_vbox.append(lbl_sub)

        hdr_box.append(title_vbox)

        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        hdr_box.append(spacer)

        btn_clear = Gtk.Button(label="Clear Log")
        btn_clear.add_css_class("action-btn-normal")
        btn_clear.connect("clicked", self._on_clear_clicked)
        hdr_box.append(btn_clear)

        btn_refresh = Gtk.Button(label="Refresh")
        btn_refresh.add_css_class("tab-btn")
        btn_refresh.set_tooltip_text("Refresh Events")
        btn_refresh.connect("clicked", lambda b: self.refresh_events())
        hdr_box.append(btn_refresh)

        main_vbox.append(hdr_box)

        # Controls Card (Search + Severity Filter)
        ctrl_card = Gtk.Frame()
        ctrl_card.add_css_class("aegis-card")

        ctrl_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        ctrl_bar.set_margin_start(14)
        ctrl_bar.set_margin_end(14)
        ctrl_bar.set_margin_top(10)
        ctrl_bar.set_margin_bottom(10)
        ctrl_card.set_child(ctrl_bar)

        # Search Entry
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Search event messages, sources, or details...")
        self.search_entry.set_hexpand(True)
        self.search_entry.connect("search-changed", self._on_filter_changed)
        ctrl_bar.append(self.search_entry)

        # Severity Filter DropDown
        self.severity_dropdown = Gtk.DropDown.new_from_strings(SEVERITY_OPTIONS)
        self.severity_dropdown.set_selected(0)
        self.severity_dropdown.connect("notify::selected", self._on_filter_changed)
        ctrl_bar.append(self.severity_dropdown)

        main_vbox.append(ctrl_card)

        # List Box Container
        list_card = Gtk.Frame()
        list_card.add_css_class("aegis-card")

        self.list_box = Gtk.ListBox()
        self.list_box.add_css_class("selection-mode")
        self.list_box.connect("row-activated", self._on_row_activated)
        list_card.set_child(self.list_box)

        main_vbox.append(list_card)

    def set_ipc_client(self, client: GUIIPCClient):
        self.ipc_client = client

    def append_events(self, events: List[Dict[str, Any]]):
        self.all_events.extend(events)
        # Keep last 500
        if len(self.all_events) > 500:
            self.all_events = self.all_events[-500:]
        self._apply_filter()

    def refresh_events(self):
        if self.ipc_client:
            self.ipc_client.fetch_events_async(100, self._on_events_response)

    def _on_events_response(self, events, err):
        if events is not None and isinstance(events, list):
            self.all_events = events
            self._apply_filter()

    def _on_clear_clicked(self, button):
        self.all_events.clear()
        self._apply_filter()

    def _on_filter_changed(self, *args):
        self._apply_filter()

    def _apply_filter(self):
        # Clear existing list
        while True:
            child = self.list_box.get_first_child()
            if child is None:
                break
            self.list_box.remove(child)

        search_query = self.search_entry.get_text().lower().strip()
        sev_idx = self.severity_dropdown.get_selected()

        for ev in reversed(self.all_events):
            source = str(ev.get("source", "")).lower()
            severity = str(ev.get("severity", "")).upper()
            msg = str(ev.get("message", "")).lower()

            if search_query and (search_query not in msg and search_query not in source):
                continue

            if sev_idx == 1 and severity != "INFO":
                continue
            elif sev_idx == 2 and severity != "WARNING":
                continue
            elif sev_idx == 3 and severity not in ("CRITICAL", "ERROR", "EMERGENCY"):
                continue

            row = self._create_event_row(ev)
            self.list_box.append(row)

    def _create_event_row(self, ev: Dict[str, Any]) -> Adw.ActionRow:
        ts = ev.get("timestamp", "")
        if "T" in ts:
            time_part = ts.split("T")[-1][:8]
        else:
            time_part = str(ts)[:8]

        source = str(ev.get("source", "system")).upper()
        severity = str(ev.get("severity", "INFO")).upper()
        msg = str(ev.get("message", ""))

        row = Adw.ActionRow()
        row.set_title(msg)
        row.set_subtitle(f"{time_part}  ·  Source: {source}  ·  Severity: {severity}")

        badge = Gtk.Label(label=severity)
        badge.add_css_class("status-badge")
        if severity in ("CRITICAL", "ERROR", "EMERGENCY"):
            badge.add_css_class("critical")
        elif severity == "WARNING":
            badge.add_css_class("warning")
        else:
            badge.add_css_class("normal")

        badge.set_valign(Gtk.Align.CENTER)
        row.add_suffix(badge)

        row._event_data = ev
        return row

    def _on_row_activated(self, listbox, row):
        if hasattr(row, "_event_data"):
            ev = row._event_data
            details = ev.get("details") or {}
            detail_str = "\n".join(f"  • {k}: {v}" for k, v in details.items()) if details else "None"

            body = (
                f"Source: {ev.get('source')}\n"
                f"Severity: {ev.get('severity')}\n"
                f"Timestamp: {ev.get('timestamp')}\n\n"
                f"Message:\n{ev.get('message')}\n\n"
                f"Details:\n{detail_str}"
            )

            dialog = Adw.MessageDialog.new(self.get_native(), "Event Details", body)
            dialog.add_response("ok", "Close")
            dialog.set_default_response("ok")
            dialog.present()
