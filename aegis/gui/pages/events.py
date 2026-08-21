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

        lbl_title = Gtk.Label(label="AEGIS // EVENT_AUDIT_LOG")
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

        btn_clear = Gtk.Button(label="[ CLEAR LOG ]")
        btn_clear.add_css_class("action-btn-normal")
        btn_clear.connect("clicked", self._on_clear_clicked)
        hdr_box.append(btn_clear)

        btn_refresh = Gtk.Button(label="[ REFRESH ]")
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
        self.list_box.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.list_box.add_css_class("boxed-list")
        self.list_box.connect("row-activated", self._on_row_activated)
        list_card.set_child(self.list_box)

        main_vbox.append(list_card)

    def set_ipc_client(self, client: GUIIPCClient):
        self.ipc_client = client

    def refresh_events(self):
        if self.ipc_client:
            self.ipc_client.fetch_events_async(limit=100, callback=self._on_events_fetched)

    def append_events(self, raw_events: List[Dict[str, Any]]):
        added_new = False
        for e in raw_events:
            evt_id = e.get("id") or f"evt-{e.get('timestamp')}-{hash(e.get('message'))}"
            e["id"] = evt_id
            if evt_id not in self.seen_ids:
                self.seen_ids.add(evt_id)
                self.events.append(e)
                added_new = True

        if added_new:
            self.events.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            self._render_filtered_events()

    def _on_events_fetched(self, res, err):
        if res is not None and isinstance(res, list):
            self.append_events(res)

    def _on_filter_changed(self, *args):
        self._render_filtered_events()

    def _on_clear_clicked(self, button):
        self.events.clear()
        self.seen_ids.clear()
        self._render_filtered_events()

    def _render_filtered_events(self):
        while True:
            child = self.list_box.get_first_child()
            if not child:
                break
            self.list_box.remove(child)

        query = self.search_entry.get_text().strip().lower()
        sev_idx = self.severity_dropdown.get_selected()

        for ev in self.events:
            msg = str(ev.get("message", ""))
            source = str(ev.get("source", ""))
            severity = str(ev.get("severity", "INFO")).upper()

            if query and query not in msg.lower() and query not in source.lower():
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
        row.set_subtitle(f"[{time_part}]  ::  SOURCE: {source}  ::  SEVERITY: {severity}")

        badge_text = f"[● {severity}]"
        badge = Gtk.Label(label=badge_text)
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
