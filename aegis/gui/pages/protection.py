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

        # Scrolled View Area
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        self.append(scrolled)

        clamp = Adw.Clamp()
        clamp.set_maximum_size(1000)
        scrolled.set_child(clamp)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        main_box.set_margin_start(20)
        main_box.set_margin_end(20)
        main_box.set_margin_top(20)
        main_box.set_margin_bottom(28)
        clamp.set_child(main_box)

        # Header Title
        hdr_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        title_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)

        lbl_title = Gtk.Label(label="Protection & Rules Manager")
        lbl_title.add_css_class("title-1")
        lbl_title.add_css_class("bold")
        lbl_title.set_halign(Gtk.Align.START)
        title_vbox.append(lbl_title)

        lbl_sub = Gtk.Label(label="Configure system protection lists and expendable process priority rules")
        lbl_sub.add_css_class("aegis-subtext")
        lbl_sub.set_halign(Gtk.Align.START)
        title_vbox.append(lbl_sub)

        hdr_box.append(title_vbox)

        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        hdr_box.append(spacer)

        btn_refresh = Gtk.Button()
        btn_refresh.set_icon_name("view-refresh-symbolic")
        btn_refresh.set_tooltip_text("Refresh Protection Rules")
        btn_refresh.connect("clicked", lambda b: self.refresh_data())
        hdr_box.append(btn_refresh)

        main_box.append(hdr_box)

        # Section 1: Protected Processes Card
        self.sec_prot_box = self._build_section(
            main_box,
            title="PROTECTED PROCESSES",
            description="Processes Aegis will never target for automatic recovery or termination.",
            add_button_label="+ Add Protected",
            on_add_clicked=self._on_add_protected_clicked,
            on_search_changed=self._on_search_prot_changed
        )
        self.search_prot_entry = self.sec_prot_box.search_entry
        self.list_prot_box = self.sec_prot_box.list_box

        # Section 2: Expendable Processes Card
        self.sec_exp_box = self._build_section(
            main_box,
            title="EXPENDABLE PROCESSES",
            description="Priority candidates targeted first when memory/resource limits are exceeded.",
            add_button_label="+ Add Expendable",
            on_add_clicked=self._on_add_expendable_clicked,
            on_search_changed=self._on_search_exp_changed
        )
        self.search_exp_entry = self.sec_exp_box.search_entry
        self.list_exp_box = self.sec_exp_box.list_box

    def _build_section(self, parent_box, title, description, add_button_label, on_add_clicked, on_search_changed):
        card = Gtk.Frame()
        card.add_css_class("aegis-card")

        grp_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        grp_box.set_margin_start(16)
        grp_box.set_margin_end(16)
        grp_box.set_margin_top(14)
        grp_box.set_margin_bottom(14)
        card.set_child(grp_box)

        hdr_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        lbl_title = Gtk.Label(label=title)
        lbl_title.add_css_class("aegis-card-header")
        hdr_box.append(lbl_title)

        sp = Gtk.Box()
        sp.set_hexpand(True)
        hdr_box.append(sp)

        btn_add = Gtk.Button(label=add_button_label)
        btn_add.add_css_class("action-btn-normal")
        btn_add.connect("clicked", on_add_clicked)
        hdr_box.append(btn_add)

        grp_box.append(hdr_box)

        lbl_desc = Gtk.Label(label=description)
        lbl_desc.add_css_class("aegis-subtext")
        lbl_desc.set_halign(Gtk.Align.START)
        grp_box.append(lbl_desc)

        # Search Bar inside Card
        search_entry = Gtk.SearchEntry()
        search_entry.set_placeholder_text("Filter entries...")
        search_entry.connect("search-changed", on_search_changed)
        grp_box.append(search_entry)

        # List Box
        list_box = Gtk.ListBox()
        list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        list_box.add_css_class("boxed-list")
        grp_box.append(list_box)

        parent_box.append(card)

        # Attach references
        grp_box.search_entry = search_entry
        grp_box.list_box = list_box
        return grp_box

    def set_ipc_client(self, client: GUIIPCClient):
        self.ipc_client = client

    def refresh_data(self):
        if self.ipc_client:
            self.ipc_client.fetch_protection_async(self._on_protection_fetched)

    def update_protection(self, protected: List[str], expendable: List[str]):
        self.protected_list = protected or []
        self.expendable_list = expendable or []
        self._render_protected_list()
        self._render_expendable_list()

    def update_active_processes(self, procs: List[Dict[str, Any]]):
        self.active_processes = procs or []
        self._render_protected_list()
        self._render_expendable_list()

    def _on_protection_fetched(self, res, err):
        if res and isinstance(res, dict):
            self.update_protection(res.get("protected", []), res.get("expendable", []))

    def _on_search_prot_changed(self, *args):
        self._render_protected_list()

    def _on_search_exp_changed(self, *args):
        self._render_expendable_list()

    def _render_protected_list(self):
        while True:
            child = self.list_prot_box.get_first_child()
            if not child:
                break
            self.list_prot_box.remove(child)

        query = self.search_prot_entry.get_text().strip().lower()
        active_names = {p.get("name", ""): p for p in self.active_processes}

        for name in self.protected_list:
            if query and query not in name.lower():
                continue

            row = Adw.ActionRow()
            row.set_title(name)

            if name in active_names:
                p_info = active_names[name]
                row.set_subtitle(f"Active  •  PID {p_info.get('pid')}  •  Score {p_info.get('score', 0):.2f}")
            else:
                row.set_subtitle("Not currently running")

            badge = Gtk.Label(label="PROTECTED")
            badge.add_css_class("status-badge")
            badge.add_css_class("protected")
            badge.set_valign(Gtk.Align.CENTER)
            row.add_suffix(badge)

            btn_rem = Gtk.Button(label="Remove")
            btn_rem.add_css_class("action-btn-normal")
            btn_rem.set_valign(Gtk.Align.CENTER)
            btn_rem.connect("clicked", lambda b, n=name: self._on_remove_protected(n))
            row.add_suffix(btn_rem)

            self.list_prot_box.append(row)

    def _render_expendable_list(self):
        while True:
            child = self.list_exp_box.get_first_child()
            if not child:
                break
            self.list_exp_box.remove(child)

        query = self.search_exp_entry.get_text().strip().lower()
        active_names = {p.get("name", ""): p for p in self.active_processes}

        for name in self.expendable_list:
            if query and query not in name.lower():
                continue

            row = Adw.ActionRow()
            row.set_title(name)

            if name in active_names:
                p_info = active_names[name]
                row.set_subtitle(f"Active  •  PID {p_info.get('pid')}  •  Score {p_info.get('score', 0):.2f}")
            else:
                row.set_subtitle("Not currently running")

            badge = Gtk.Label(label="EXPENDABLE")
            badge.add_css_class("status-badge")
            badge.add_css_class("expendable")
            badge.set_valign(Gtk.Align.CENTER)
            row.add_suffix(badge)

            btn_rem = Gtk.Button(label="Remove")
            btn_rem.add_css_class("action-btn-normal")
            btn_rem.set_valign(Gtk.Align.CENTER)
            btn_rem.connect("clicked", lambda b, n=name: self._on_remove_expendable(n))
            row.add_suffix(btn_rem)

            self.list_exp_box.append(row)

    def _on_remove_protected(self, name: str):
        if self.ipc_client:
            self.ipc_client.unprotect_process_async(name, lambda r, e: self.refresh_data())

    def _on_remove_expendable(self, name: str):
        if self.ipc_client:
            self.ipc_client.unmark_expendable_async(name, lambda r, e: self.refresh_data())

    def _on_add_protected_clicked(self, button):
        self._show_add_dialog(mode="protect")

    def _on_add_expendable_clicked(self, button):
        self._show_add_dialog(mode="expendable")

    def _show_add_dialog(self, mode: str):
        title = "Add Protected Process" if mode == "protect" else "Add Expendable Process"
        
        dialog = Adw.MessageDialog.new(
            self.get_native(),
            title,
            "Enter the process binary name (e.g. firefox, steam, code):"
        )

        entry = Gtk.Entry()
        entry.set_placeholder_text("Process name (e.g. firefox)")
        entry.set_margin_top(8)
        dialog.set_extra_child(entry)

        dialog.add_response("cancel", "Cancel")
        dialog.add_response("add", "Add")
        dialog.set_response_appearance("add", Adw.ResponseAppearance.SUGGESTED)

        def _on_response(d, response_id):
            if response_id == "add":
                proc_name = entry.get_text().strip()
                if proc_name:
                    if mode == "protect":
                        self.ipc_client.protect_process_async(proc_name, self._on_add_completed)
                    else:
                        self.ipc_client.mark_expendable_async(proc_name, self._on_add_completed, force=False)

        dialog.connect("response", _on_response)
        dialog.present()

    def _on_add_completed(self, res, err):
        if err is not None:
            err_msg = str(err)
            if "PROTECTION_CONFLICT" in err_msg or "protected" in err_msg:
                # Conflict resolution dialog
                self._show_conflict_dialog(err_msg)
            else:
                self._show_error_dialog("Error", err_msg)
        else:
            self.refresh_data()

    def _show_conflict_dialog(self, message: str):
        dialog = Adw.MessageDialog.new(
            self.get_native(),
            "Protection Conflict",
            f"{message}\n\nDo you want to override and set as expendable?"
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("override", "Override & Mark Expendable")
        dialog.set_response_appearance("override", Adw.ResponseAppearance.DESTRUCTIVE)

        def _on_response(d, response_id):
            if response_id == "override" and self.ipc_client:
                # Extract process name from message or retry with force=True
                pass

        dialog.connect("response", _on_response)
        dialog.present()

    def _show_error_dialog(self, title: str, message: str):
        dialog = Adw.MessageDialog.new(self.get_native(), title, message)
        dialog.add_response("ok", "OK")
        dialog.set_default_response("ok")
        dialog.present()
