import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib
from datetime import datetime
from typing import List, Dict, Any, Optional, Set

from aegis.gui.client import GUIIPCClient

SEVERITY_OPTIONS = ["All Severities", "INFO", "WARNING", "CRITICAL / ERROR"]

class EventsPage(Gtk.Box):
    def __init__(self, ipc_client: Optional[GUIIPCClient] = None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.ipc_client = ipc_client

        self.events: List[Dict[str, Any]] = []
        self.seen_ids: Set[str] = set()

        # Top Control Bar (Search, Filter, Actions)
        ctrl_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        ctrl_bar.set_margin_start(16)
        ctrl_bar.set_margin_end(16)
        ctrl_bar.set_margin_top(12)
        ctrl_bar.set_margin_bottom(12)
        self.append(ctrl_bar)

        # Search Entry
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Search events (message, source, PID)...")
        self.search_entry.set_hexpand(True)
        self.search_entry.connect("search-changed", self._on_filter_changed)
        ctrl_bar.append(self.search_entry)

        # Severity Filter DropDown
        self.severity_dropdown = Gtk.DropDown.new_from_strings(SEVERITY_OPTIONS)
        self.severity_dropdown.set_selected(0)
        self.severity_dropdown.connect("notify::selected", self._on_filter_changed)
        ctrl_bar.append(self.severity_dropdown)

        # Clear View Button
        btn_clear = Gtk.Button(label="Clear View")
        btn_clear.add_css_class("flat")
        btn_clear.connect("clicked", self._on_clear_clicked)
        ctrl_bar.append(btn_clear)

        # Refresh Button
        btn_refresh = Gtk.Button()
        btn_refresh.set_icon_name("view-refresh-symbolic")
        btn_refresh.set_tooltip_text("Refresh Events")
        btn_refresh.connect("clicked", lambda b: self.refresh_events())
        ctrl_bar.append(btn_refresh)

        # Main Overlay for List + "New Events" Floating Pill
        overlay = Gtk.Overlay()
        overlay.set_vexpand(True)
        self.append(overlay)

        # Scrolled Area
        self.scrolled = Gtk.ScrolledWindow()
        self.scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        overlay.set_child(self.scrolled)

        clamp = Adw.Clamp()
        clamp.set_maximum_size(950)
        self.scrolled.set_child(clamp)

        self.list_box = Gtk.ListBox()
        self.list_box.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.list_box.add_css_class("boxed-list")
        self.list_box.set_margin_start(16)
        self.list_box.set_margin_end(16)
        self.list_box.set_margin_bottom(24)
        self.list_box.connect("row-activated", self._on_row_activated)
        clamp.set_child(self.list_box)

        # Floating "New Events" Button
        self.btn_new_events = Gtk.Button(label="⬇ New Events")
        self.btn_new_events.add_css_class("pill")
        self.btn_new_events.add_css_class("suggested-action")
        self.btn_new_events.set_halign(Gtk.Align.CENTER)
        self.btn_new_events.set_valign(Gtk.Align.END)
        self.btn_new_events.set_margin_bottom(20)
        self.btn_new_events.set_visible(False)
        self.btn_new_events.connect("clicked", self._scroll_to_bottom)
        overlay.add_overlay(self.btn_new_events)

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
            # Enforce 500 max limit in memory
            if len(self.events) > 500:
                overflow = len(self.events) - 500
                trimmed = self.events[:overflow]
                for t in trimmed:
                    self.seen_ids.discard(t.get("id"))
                self.events = self.events[overflow:]

            self._render_events()

    def _on_events_fetched(self, res, err):
        if res is not None and isinstance(res, list):
            self.append_events(res)

    def _on_clear_clicked(self, button):
        self.events.clear()
        self.seen_ids.clear()
        self._render_events()

    def _on_filter_changed(self, *args):
        self._render_events()

    def _render_events(self):
        query = self.search_entry.get_text().strip().lower()
        sel_idx = self.severity_dropdown.get_selected()
        sev_filter = SEVERITY_OPTIONS[sel_idx] if 0 <= sel_idx < len(SEVERITY_OPTIONS) else "All Severities"

        filtered = []
        for e in self.events:
            msg = e.get("message", "").lower()
            src = e.get("source", "").lower()
            sev = e.get("severity", "").upper()
            vals_str = str(e.get("values", "")).lower()

            if query and not (query in msg or query in src or query in sev or query in vals_str):
                continue

            if sev_filter == "INFO" and sev != "INFO":
                continue
            elif sev_filter == "WARNING" and sev != "WARNING":
                continue
            elif sev_filter == "CRITICAL / ERROR" and sev not in ("CRITICAL", "ERROR", "EMERGENCY"):
                continue

            filtered.append(e)

        # Clear existing list box children
        while True:
            child = self.list_box.get_first_child()
            if not child:
                break
            self.list_box.remove(child)

        # Render rows
        for e in filtered:
            row = self._create_event_row(e)
            self.list_box.append(row)

        # Auto-scroll or show floating pill
        adj = self.scrolled.get_vadjustment()
        if adj:
            val = adj.get_value()
            max_val = adj.get_upper() - adj.get_page_size()
            if max_val - val < 80 or max_val <= 0:
                GLib.idle_add(self._scroll_to_bottom, None)
            else:
                self.btn_new_events.set_visible(True)

    def _create_event_row(self, evt: Dict[str, Any]) -> Adw.ActionRow:
        row = Adw.ActionRow()
        row.evt_data = evt

        ts_str = evt.get("timestamp", "")
        try:
            dt = datetime.fromisoformat(ts_str)
            time_display = dt.strftime("%H:%M:%S")
        except Exception:
            time_display = ts_str[:8] if len(ts_str) >= 8 else ts_str

        sev = evt.get("severity", "INFO").upper()
        src = evt.get("source", "system").upper()
        msg = evt.get("message", "")

        row.set_title(msg)
        row.set_subtitle(f"Time: {time_display}  •  Source: {src}")

        # Severity Badge
        tag = Gtk.Label(label=sev)
        tag.add_css_class("caption")
        tag.add_css_class("bold")
        tag.set_valign(Gtk.Align.CENTER)

        if sev in ("CRITICAL", "EMERGENCY", "ERROR"):
            tag.add_css_class("error")
        elif sev == "WARNING":
            tag.add_css_class("warning")
        else:
            tag.add_css_class("accent")

        row.add_suffix(tag)
        return row

    def _scroll_to_bottom(self, button=None):
        adj = self.scrolled.get_vadjustment()
        if adj:
            adj.set_value(adj.get_upper() - adj.get_page_size())
        self.btn_new_events.set_visible(False)

    def _on_row_activated(self, list_box, row):
        evt = getattr(row, "evt_data", None)
        if not evt:
            return

        msg = evt.get("message", "")
        sev = evt.get("severity", "INFO")
        src = evt.get("source", "system")
        ts = evt.get("timestamp", "")
        vals = evt.get("values", {})

        detail_text = f"Time:\n{ts}\n\nSeverity:\n{sev}\n\nSource:\n{src}\n\nMessage:\n{msg}"
        if vals:
            detail_text += f"\n\nDetails / Metadata:\n{vals}"

        dialog = Adw.MessageDialog.new(
            self.get_native(),
            "Event Details",
            detail_text
        )
        dialog.add_response("close", "Close")
        dialog.set_default_response("close")
        dialog.present()
