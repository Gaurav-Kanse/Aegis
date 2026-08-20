import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib
from typing import List, Dict, Any, Optional

from aegis.gui.widgets.process_row import ProcessRow
from aegis.gui.client import GUIIPCClient

SORT_OPTIONS = [
    ("Score (High to Low)", "score_desc"),
    ("CPU Usage (High to Low)", "cpu_desc"),
    ("Memory (High to Low)", "rss_desc"),
    ("Runtime (Longest First)", "runtime_desc"),
    ("Process Name (A-Z)", "name_asc"),
    ("PID (Ascending)", "pid_asc"),
]

class ProcessesPage(Gtk.Box):
    def __init__(self, ipc_client: Optional[GUIIPCClient] = None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.ipc_client = ipc_client
        self.raw_processes: List[Dict[str, Any]] = []

        # Scrolled Window
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

        # Header Title Row
        hdr_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        title_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)

        lbl_title = Gtk.Label(label="Processes")
        lbl_title.add_css_class("title-1")
        lbl_title.add_css_class("bold")
        lbl_title.set_halign(Gtk.Align.START)
        title_vbox.append(lbl_title)

        self.lbl_count = Gtk.Label(label="Live process candidate scoring & real-time controls")
        self.lbl_count.add_css_class("aegis-subtext")
        self.lbl_count.set_halign(Gtk.Align.START)
        title_vbox.append(self.lbl_count)

        hdr_box.append(title_vbox)

        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        hdr_box.append(spacer)

        btn_refresh = Gtk.Button()
        btn_refresh.set_icon_name("view-refresh-symbolic")
        btn_refresh.set_tooltip_text("Refresh Process List")
        btn_refresh.connect("clicked", lambda b: self.refresh_processes())
        hdr_box.append(btn_refresh)

        main_vbox.append(hdr_box)

        # Top Filter Bar (Search + Sort)
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
        self.search_entry.set_placeholder_text("Search processes by name or PID...")
        self.search_entry.set_hexpand(True)
        self.search_entry.connect("search-changed", self._on_search_or_sort_changed)
        ctrl_bar.append(self.search_entry)

        # Sort Label
        sort_lbl = Gtk.Label(label="Sort:")
        sort_lbl.add_css_class("aegis-subtext")
        ctrl_bar.append(sort_lbl)

        # Sort DropDown
        sort_titles = [t[0] for t in SORT_OPTIONS]
        self.sort_dropdown = Gtk.DropDown.new_from_strings(sort_titles)
        self.sort_dropdown.set_selected(0)
        self.sort_dropdown.connect("notify::selected", self._on_search_or_sort_changed)
        ctrl_bar.append(self.sort_dropdown)

        main_vbox.append(ctrl_card)

        # List Box Container
        list_card = Gtk.Frame()
        list_card.add_css_class("aegis-card")

        self.list_box = Gtk.ListBox()
        self.list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        self.list_box.add_css_class("boxed-list")
        list_card.set_child(self.list_box)

        main_vbox.append(list_card)

    def set_ipc_client(self, client: GUIIPCClient):
        self.ipc_client = client

    def update_processes(self, proc_list: List[Dict[str, Any]]):
        self.raw_processes = proc_list
        self.lbl_count.set_text(f"{len(proc_list)} active processes being monitored by Aegis")
        self._render_filtered_list()

    def refresh_processes(self):
        if self.ipc_client:
            self.ipc_client.fetch_processes_async(self._on_processes_fetched)

    def _on_processes_fetched(self, res, err):
        if res is not None and isinstance(res, list):
            self.update_processes(res)

    def _on_search_or_sort_changed(self, *args):
        self._render_filtered_list()

    def _render_filtered_list(self):
        # 1. Local Search Filter
        query = self.search_entry.get_text().strip().lower()
        filtered = []
        for p in self.raw_processes:
            pid_str = str(p.get("pid", ""))
            name_str = p.get("name", "").lower()
            if not query or query in name_str or query in pid_str:
                filtered.append(p)

        # 2. Sorting
        sel_idx = self.sort_dropdown.get_selected()
        sort_key = SORT_OPTIONS[sel_idx][1] if 0 <= sel_idx < len(SORT_OPTIONS) else "score_desc"

        if sort_key == "score_desc":
            filtered.sort(key=lambda x: x.get("score", 0.0), reverse=True)
        elif sort_key == "cpu_desc":
            filtered.sort(key=lambda x: x.get("cpu", 0.0), reverse=True)
        elif sort_key == "rss_desc":
            filtered.sort(key=lambda x: x.get("rss", 0), reverse=True)
        elif sort_key == "runtime_desc":
            filtered.sort(key=lambda x: x.get("runtime", 0), reverse=True)
        elif sort_key == "name_asc":
            filtered.sort(key=lambda x: x.get("name", "").lower())
        elif sort_key == "pid_asc":
            filtered.sort(key=lambda x: x.get("pid", 0))

        # 3. Clear ListBox
        while True:
            child = self.list_box.get_first_child()
            if not child:
                break
            self.list_box.remove(child)

        # 4. Render Rows (top 150)
        for p in filtered[:150]:
            row = ProcessRow(p, self._handle_process_action)
            self.list_box.append(row)

    def _handle_process_action(self, action_type: str, proc_data: Dict[str, Any]):
        if not self.ipc_client:
            return

        name = proc_data.get("name", "")
        pid = proc_data.get("pid", 0)

        if action_type == "protect":
            self.ipc_client.protect_process_async(name, self._on_action_completed)
        elif action_type == "unprotect":
            self.ipc_client.unprotect_process_async(name, self._on_action_completed)
        elif action_type == "mark_expendable":
            self.ipc_client.mark_expendable_async(name, self._on_action_completed)
        elif action_type == "unmark_expendable":
            self.ipc_client.unmark_expendable_async(name, self._on_action_completed)
        elif action_type == "oom_protect":
            self.ipc_client.oom_protect_process_async(pid, self._on_action_completed)
        elif action_type == "terminate":
            self._show_terminate_confirmation(pid, name)

    def _show_terminate_confirmation(self, pid: int, name: str):
        dialog = Adw.MessageDialog.new(
            self.get_native(),
            "Terminate Process?",
            f"Are you sure you want to terminate:\n\n    {name} (PID {pid})\n\nThis sends SIGTERM via Aegis IPC."
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("terminate", "Terminate")
        dialog.set_response_appearance("terminate", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")

        dialog.connect("response", lambda d, resp: self._on_terminate_confirmed(resp, pid))
        dialog.present()

    def _on_terminate_confirmed(self, response_id: str, pid: int):
        if response_id == "terminate" and self.ipc_client:
            self.ipc_client.terminate_process_async(pid, self._on_action_completed)

    def _on_action_completed(self, res, err):
        if err is not None:
            self._show_error_dialog("Action Failed", str(err))
        else:
            self.refresh_processes()

    def _show_error_dialog(self, title: str, message: str):
        dialog = Adw.MessageDialog.new(self.get_native(), title, message)
        dialog.add_response("ok", "OK")
        dialog.set_default_response("ok")
        dialog.present()
