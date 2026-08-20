import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib
from typing import List, Dict, Any, Optional, Set

from aegis.gui.client import GUIIPCClient

class ProtectionPage(Gtk.Box):
    def __init__(self, ipc_client: Optional[GUIIPCClient] = None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.ipc_client = ipc_client

        self.protected_list: List[str] = []
        self.expendable_list: List[str] = []
        self.active_processes: List[Dict[str, Any]] = []

        # Top Control Bar (Header + Refresh)
        top_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        top_bar.set_margin_start(16)
        top_bar.set_margin_end(16)
        top_bar.set_margin_top(12)
        top_bar.set_margin_bottom(12)
        self.append(top_bar)

        title_lbl = Gtk.Label(label="Protection & Rules Manager")
        title_lbl.add_css_class("title-2")
        title_lbl.add_css_class("bold")
        top_bar.append(title_lbl)

        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        top_bar.append(spacer)

        btn_refresh = Gtk.Button()
        btn_refresh.set_icon_name("view-refresh-symbolic")
        btn_refresh.set_tooltip_text("Refresh Protection Rules")
        btn_refresh.connect("clicked", lambda b: self.refresh_data())
        top_bar.append(btn_refresh)

        # Scrolled View Area
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        self.append(scrolled)

        clamp = Adw.Clamp()
        clamp.set_maximum_size(950)
        scrolled.set_child(clamp)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        main_box.set_margin_start(16)
        main_box.set_margin_end(16)
        main_box.set_margin_bottom(24)
        clamp.set_child(main_box)

        # Section 1: Protected Processes
        self.sec_prot_box = self._build_section(
            main_box,
            title="Protected Processes",
            description="Processes Aegis will never target for automatic recovery or termination.",
            add_button_label="+ Add Protected Process",
            on_add_clicked=self._on_add_protected_clicked,
            on_search_changed=self._on_search_prot_changed
        )
        self.search_prot_entry = self.sec_prot_box.search_entry
        self.list_prot_box = self.sec_prot_box.list_box

        # Section 2: Expendable Processes
        self.sec_exp_box = self._build_section(
            main_box,
            title="Expendable Processes",
            description="Priority candidates targeted first when memory/resource limits are exceeded.",
            add_button_label="+ Add Expendable Process",
            on_add_clicked=self._on_add_expendable_clicked,
            on_search_changed=self._on_search_exp_changed
        )
        self.search_exp_entry = self.sec_exp_box.search_entry
        self.list_exp_box = self.sec_exp_box.list_box

    def _build_section(self, parent_box, title, description, add_button_label, on_add_clicked, on_search_changed):
        grp_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)

        hdr_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        lbl_title = Gtk.Label(label=title)
        lbl_title.add_css_class("title-3")
        hdr_box.append(lbl_title)

        sp = Gtk.Box()
        sp.set_hexpand(True)
        hdr_box.append(sp)

        btn_add = Gtk.Button(label=add_button_label)
        btn_add.add_css_class("suggested-action")
        btn_add.connect("clicked", on_add_clicked)
        hdr_box.append(btn_add)

        grp_box.append(hdr_box)

        lbl_desc = Gtk.Label(label=description)
        lbl_desc.add_css_class("dim-label")
        lbl_desc.set_halign(Gtk.Align.START)
        grp_box.append(lbl_desc)

        search = Gtk.SearchEntry()
        search.set_placeholder_text(f"Filter {title.lower()}...")
        search.connect("search-changed", on_search_changed)
        grp_box.append(search)

        list_box = Gtk.ListBox()
        list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        list_box.add_css_class("boxed-list")
        grp_box.append(list_box)

        grp_box.search_entry = search
        grp_box.list_box = list_box

        parent_box.append(grp_box)
        return grp_box

    def set_ipc_client(self, client: GUIIPCClient):
        self.ipc_client = client

    def update_protection(self, prot_list: List[str], exp_list: List[str]):
        self.protected_list = prot_list
        self.expendable_list = exp_list
        self._render_lists()

    def update_active_processes(self, procs: List[Dict[str, Any]]):
        self.active_processes = procs
        self._render_lists()

    def refresh_data(self):
        if self.ipc_client:
            self.ipc_client.fetch_protection_async(self._on_protection_fetched)
            self.ipc_client.fetch_processes_async(self._on_processes_fetched)

    def _on_protection_fetched(self, res, err):
        if res is not None and isinstance(res, dict):
            self.update_protection(res.get("protected", []), res.get("expendable", []))

    def _on_processes_fetched(self, res, err):
        if res is not None and isinstance(res, list):
            self.update_active_processes(res)

    def _on_search_prot_changed(self, *args):
        self._render_lists()

    def _on_search_exp_changed(self, *args):
        self._render_lists()

    def _render_lists(self):
        # 1. Protected List Rendering
        q_prot = self.search_prot_entry.get_text().strip().lower()
        self._clear_listbox(self.list_prot_box)

        active_map: Dict[str, List[int]] = {}
        for p in self.active_processes:
            pname = p.get("name", "")
            pid = p.get("pid", 0)
            if pname:
                active_map.setdefault(pname, []).append(pid)

        for p_name in self.protected_list:
            if q_prot and q_prot not in p_name.lower():
                continue
            row = self._create_protected_row(p_name, active_map.get(p_name, []))
            self.list_prot_box.append(row)

        # 2. Expendable List Rendering
        q_exp = self.search_exp_entry.get_text().strip().lower()
        self._clear_listbox(self.list_exp_box)

        for e_name in self.expendable_list:
            if q_exp and q_exp not in e_name.lower():
                continue
            row = self._create_expendable_row(e_name, active_map.get(e_name, []))
            self.list_exp_box.append(row)

    def _clear_listbox(self, list_box: Gtk.ListBox):
        while True:
            child = list_box.get_first_child()
            if not child:
                break
            list_box.remove(child)

    def _create_protected_row(self, name: str, pids: List[int]) -> Adw.ActionRow:
        row = Adw.ActionRow()
        row.set_title(name)

        if pids:
            pid_str = ", ".join(str(p) for p in pids[:3])
            row.set_subtitle(f"● Running (PID: {pid_str})")
        else:
            row.set_subtitle("○ Not running")

        # OOM Protect Button
        btn_oom = Gtk.Button(label="OOM Protect")
        btn_oom.add_css_class("flat")
        btn_oom.connect("clicked", lambda b: self._on_oom_protect_clicked(name, pids))
        row.add_suffix(btn_oom)

        # Remove Protection Button
        btn_rem = Gtk.Button(label="Remove")
        btn_rem.add_css_class("destructive-action")
        btn_rem.connect("clicked", lambda b: self._confirm_remove_protection(name))
        row.add_suffix(btn_rem)

        return row

    def _create_expendable_row(self, name: str, pids: List[int]) -> Adw.ActionRow:
        row = Adw.ActionRow()
        row.set_title(name)

        if pids:
            pid_str = ", ".join(str(p) for p in pids[:3])
            row.set_subtitle(f"● Running (PID: {pid_str})")
        else:
            row.set_subtitle("○ Not running")

        # Remove Expendable Button
        btn_rem = Gtk.Button(label="Remove")
        btn_rem.add_css_class("destructive-action")
        btn_rem.connect("clicked", lambda b: self._confirm_remove_expendable(name))
        row.add_suffix(btn_rem)

        return row

    # --- Add Dialogs ---
    def _on_add_protected_clicked(self, button):
        self._show_add_process_dialog(
            title="Add Protected Process",
            heading="Protect Process",
            body="Enter or select a process name to protect from automated recovery.",
            action_label="Protect",
            on_submit=self._submit_add_protected
        )

    def _on_add_expendable_clicked(self, button):
        self._show_add_process_dialog(
            title="Add Expendable Process",
            heading="Mark Process Expendable",
            body="Enter or select a process name to prioritize during resource pressure.",
            action_label="Mark Expendable",
            on_submit=self._submit_add_expendable
        )

    def _show_add_process_dialog(self, title, heading, body, action_label, on_submit):
        dialog = Adw.MessageDialog.new(self.get_native(), heading, body)

        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        content_box.set_margin_top(8)

        # Process Picker Dropdown
        running_names = sorted(list(set(p.get("name", "") for p in self.active_processes if p.get("name"))))
        dropdown_items = ["(Type manual process name below...)"] + running_names
        dropdown = Gtk.DropDown.new_from_strings(dropdown_items)
        dropdown.set_selected(0)
        content_box.append(dropdown)

        # Manual Text Entry
        entry = Gtk.Entry()
        entry.set_placeholder_text("Process name (e.g. firefox, steam)")
        content_box.append(entry)

        dropdown.connect("notify::selected", lambda d, ps: entry.set_text(dropdown_items[d.get_selected()]) if d.get_selected() > 0 else None)

        dialog.set_extra_child(content_box)
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("submit", action_label)
        dialog.set_response_appearance("submit", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("submit")

        dialog.connect("response", lambda d, resp: on_submit(resp, entry.get_text().strip()))
        dialog.present()

    def _submit_add_protected(self, response_id: str, name: str):
        if response_id == "submit" and name and self.ipc_client:
            self.ipc_client.protect_process_async(name, self._on_action_completed)

    def _submit_add_expendable(self, response_id: str, name: str, force: bool = False):
        if response_id == "submit" and name and self.ipc_client:
            self.ipc_client.mark_expendable_async(name, lambda res, err: self._on_add_expendable_completed(res, err, name), force=force)

    def _on_add_expendable_completed(self, res, err, name: str):
        if err is not None:
            err_msg = str(err)
            if "PROTECTION_CONFLICT" in err_msg:
                # Prompt user for resolution
                self._show_conflict_resolution_dialog(name)
            else:
                self._show_error("Operation Failed", err_msg)
        else:
            self.refresh_data()

    def _show_conflict_resolution_dialog(self, name: str):
        dialog = Adw.MessageDialog.new(
            self.get_native(),
            "Protection Conflict",
            f"Process '{name}' is currently protected.\nRemove protection before marking it expendable?"
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("resolve", "Remove Protection & Mark Expendable")
        dialog.set_response_appearance("resolve", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")

        def _handle_resp(d, resp_id):
            if resp_id == "resolve" and self.ipc_client:
                self.ipc_client.mark_expendable_async(name, self._on_action_completed, force=True)

        dialog.connect("response", _handle_resp)
        dialog.present()

    # --- Remove Confirmations ---
    def _confirm_remove_protection(self, name: str):
        dialog = Adw.MessageDialog.new(
            self.get_native(),
            "Remove Protection?",
            f"'{name}' will no longer be protected from Aegis recovery actions."
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("remove", "Remove")
        dialog.set_response_appearance("remove", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")

        def _handle_resp(d, resp):
            if resp == "remove" and self.ipc_client:
                self.ipc_client.unprotect_process_async(name, self._on_action_completed)

        dialog.connect("response", _handle_resp)
        dialog.present()

    def _confirm_remove_expendable(self, name: str):
        dialog = Adw.MessageDialog.new(
            self.get_native(),
            "Remove Expendable Status?",
            f"'{name}' will no longer be prioritized for expendable recovery."
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("remove", "Remove")
        dialog.set_response_appearance("remove", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")

        def _handle_resp(d, resp):
            if resp == "remove" and self.ipc_client:
                self.ipc_client.unmark_expendable_async(name, self._on_action_completed)

        dialog.connect("response", _handle_resp)
        dialog.present()

    def _on_oom_protect_clicked(self, name: str, pids: List[int]):
        pid = pids[0] if pids else None
        if self.ipc_client:
            self.ipc_client.oom_protect_process_async(pid or 0, self._on_action_completed)

    def _on_action_completed(self, res, err):
        if err is not None:
            self._show_error("Action Failed", str(err))
        else:
            self.refresh_data()

    def _show_error(self, title: str, message: str):
        dialog = Adw.MessageDialog.new(self.get_native(), title, message)
        dialog.add_response("ok", "OK")
        dialog.set_default_response("ok")
        dialog.present()
