import copy
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib

from aegis.config import get_default_config, validate_config_dict, Config


class SettingsPage(Adw.Bin):
    def __init__(self, ipc_client=None):
        super().__init__()
        self.ipc_client = ipc_client

        self.server_config = {}
        self.edited_config = {}
        self.is_dirty = False
        self.is_valid = True
        self.is_offline = False
        self._updating_widgets = False

        # Main vertical container
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_child(self.main_box)

        # Top Control Bar (Save, Revert, Reset, Status Banner)
        self._build_top_control_bar()

        # Scrolled Window containing Adw.PreferencesPage
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)
        self.main_box.append(scrolled)

        self.prefs_page = Adw.PreferencesPage()
        scrolled.set_child(self.prefs_page)

        # Build preference groups
        self._build_memory_group()
        self._build_cpu_temp_group()
        self._build_disk_net_group()
        self._build_kill_group()
        self._build_battery_group()

        # Initial validation state
        self._revalidate()

    def _build_top_control_bar(self):
        # Action Bar container
        action_bar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.main_box.append(action_bar)

        # Adw.Banner for validation errors / status messages
        self.banner = Adw.Banner()
        action_bar.append(self.banner)

        # Toolbar Box for buttons
        toolbar_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        toolbar_box.set_margin_start(16)
        toolbar_box.set_margin_end(16)
        toolbar_box.set_margin_top(8)
        toolbar_box.set_margin_bottom(8)
        action_bar.append(toolbar_box)

        # Status Label
        self.lbl_status = Gtk.Label(label=":: CONFIGURATION SAVED ::") 
        self.lbl_status.add_css_class("aegis-subtext")
        self.lbl_status.set_hexpand(True)
        self.lbl_status.set_halign(Gtk.Align.START)
        toolbar_box.append(self.lbl_status)

        # Reset Defaults Button
        self.btn_reset = Gtk.Button(label="[ RESET DEFAULTS ]")
        self.btn_reset.add_css_class("action-btn-normal")
        self.btn_reset.connect("clicked", self._on_reset_clicked)
        toolbar_box.append(self.btn_reset)

        # Revert Button
        self.btn_revert = Gtk.Button(label="[ REVERT ]")
        self.btn_revert.add_css_class("action-btn-normal")
        self.btn_revert.connect("clicked", self._on_revert_clicked)
        toolbar_box.append(self.btn_revert)

        # Save Changes Button
        self.btn_save = Gtk.Button(label="[ SAVE CHANGES ]")
        self.btn_save.add_css_class("suggested-action")
        self.btn_save.connect("clicked", self._on_save_clicked)
        toolbar_box.append(self.btn_save)

    def _build_memory_group(self):
        group = Adw.PreferencesGroup()
        group.set_title(":: MEMORY THRESHOLDS ::")
        group.set_description("RAM usage percentages triggering automated warnings, kills, and OOM escalation.")
        self.prefs_page.add(group)

        # Soft Memory Limit
        self.row_mem_soft = Adw.ActionRow()
        self.row_mem_soft.set_title("Soft Memory Threshold (%)")
        self.row_mem_soft.set_subtitle("Early warning threshold for system memory pressure")
        self.spin_mem_soft = Gtk.SpinButton.new_with_range(0.0, 100.0, 1.0)
        self.spin_mem_soft.set_valign(Gtk.Align.CENTER)
        self.spin_mem_soft.connect("value-changed", self._on_widget_changed)
        self.row_mem_soft.add_suffix(self.spin_mem_soft)
        group.add(self.row_mem_soft)

        # Hard Memory Limit
        self.row_mem_hard = Adw.ActionRow()
        self.row_mem_hard.set_title("Hard Memory Threshold (%)")
        self.row_mem_hard.set_subtitle("Critical threshold that triggers automated victim termination")
        self.spin_mem_hard = Gtk.SpinButton.new_with_range(0.0, 100.0, 1.0)
        self.spin_mem_hard.set_valign(Gtk.Align.CENTER)
        self.spin_mem_hard.connect("value-changed", self._on_widget_changed)
        self.row_mem_hard.add_suffix(self.spin_mem_hard)
        group.add(self.row_mem_hard)

        # Max Memory Limit
        self.row_mem_max = Adw.ActionRow()
        self.row_mem_max.set_title("Maximum Memory Limit (%)")
        self.row_mem_max.set_subtitle("Emergency kernel OOM killer escalation threshold")
        self.spin_mem_max = Gtk.SpinButton.new_with_range(0.0, 100.0, 1.0)
        self.spin_mem_max.set_valign(Gtk.Align.CENTER)
        self.spin_mem_max.connect("value-changed", self._on_widget_changed)
        self.row_mem_max.add_suffix(self.spin_mem_max)
        group.add(self.row_mem_max)

    def _build_cpu_temp_group(self):
        group = Adw.PreferencesGroup()
        group.set_title(":: CPU &amp; THERMAL LIMITS ::")
        group.set_description("Resource alert limits and hardware temperature monitoring thresholds.")
        self.prefs_page.add(group)

        # CPU Alert Threshold
        self.row_cpu_alert = Adw.ActionRow()
        self.row_cpu_alert.set_title("CPU Alert Threshold (%)")
        self.row_cpu_alert.set_subtitle("CPU utilization warning threshold")
        self.spin_cpu_alert = Gtk.SpinButton.new_with_range(0.0, 100.0, 1.0)
        self.spin_cpu_alert.set_valign(Gtk.Align.CENTER)
        self.spin_cpu_alert.connect("value-changed", self._on_widget_changed)
        self.row_cpu_alert.add_suffix(self.spin_cpu_alert)
        group.add(self.row_cpu_alert)

        # Warning Temperature
        self.row_temp_warning = Adw.ActionRow()
        self.row_temp_warning.set_title("Warning Temperature (°C)")
        self.row_temp_warning.set_subtitle("Thermal warning alert threshold")
        self.spin_temp_warning = Gtk.SpinButton.new_with_range(0.0, 150.0, 1.0)
        self.spin_temp_warning.set_valign(Gtk.Align.CENTER)
        self.spin_temp_warning.connect("value-changed", self._on_widget_changed)
        self.row_temp_warning.add_suffix(self.spin_temp_warning)
        group.add(self.row_temp_warning)

        # Critical Temperature
        self.row_temp_critical = Adw.ActionRow()
        self.row_temp_critical.set_title("Critical Temperature (°C)")
        self.row_temp_critical.set_subtitle("Critical thermal emergency threshold")
        self.spin_temp_critical = Gtk.SpinButton.new_with_range(0.0, 150.0, 1.0)
        self.spin_temp_critical.set_valign(Gtk.Align.CENTER)
        self.spin_temp_critical.connect("value-changed", self._on_widget_changed)
        self.row_temp_critical.add_suffix(self.spin_temp_critical)
        group.add(self.row_temp_critical)

        # Thermal Action
        self.row_temp_action = Adw.ActionRow()
        self.row_temp_action.set_title("Thermal Action")
        self.row_temp_action.set_subtitle("Action taken when critical thermal limit is reached (e.g. kill, notify)")
        self.entry_temp_action = Gtk.Entry()
        self.entry_temp_action.set_valign(Gtk.Align.CENTER)
        self.entry_temp_action.connect("changed", self._on_widget_changed)
        self.row_temp_action.add_suffix(self.entry_temp_action)
        group.add(self.row_temp_action)

    def _build_disk_net_group(self):
        group = Adw.PreferencesGroup()
        group.set_title(":: DISK &amp; NETWORK ALERTS ::")
        group.set_description("Storage usage and network throughput threshold settings.")
        self.prefs_page.add(group)

        # Disk Space Alert
        self.row_disk_space = Adw.ActionRow()
        self.row_disk_space.set_title("Disk Space Alert (%)")
        self.row_disk_space.set_subtitle("Alert when root partition storage usage exceeds threshold")
        self.spin_disk_space = Gtk.SpinButton.new_with_range(0.0, 100.0, 1.0)
        self.spin_disk_space.set_valign(Gtk.Align.CENTER)
        self.spin_disk_space.connect("value-changed", self._on_widget_changed)
        self.row_disk_space.add_suffix(self.spin_disk_space)
        group.add(self.row_disk_space)

        # Disk I/O Alert
        self.row_disk_io = Adw.ActionRow()
        self.row_disk_io.set_title("Disk I/O Alerts")
        self.row_disk_io.set_subtitle("Monitor and alert on high disk I/O latency")
        self.switch_disk_io = Gtk.Switch()
        self.switch_disk_io.set_valign(Gtk.Align.CENTER)
        self.switch_disk_io.connect("notify::active", self._on_widget_changed)
        self.row_disk_io.add_suffix(self.switch_disk_io)
        group.add(self.row_disk_io)

        # Network Alert
        self.row_net_alert = Adw.ActionRow()
        self.row_net_alert.set_title("Network Alert Threshold (Mbps)")
        self.row_net_alert.set_subtitle("Alert when network bandwidth exceeds limit")
        self.spin_net_alert = Gtk.SpinButton.new_with_range(0.0, 10000.0, 10.0)
        self.spin_net_alert.set_valign(Gtk.Align.CENTER)
        self.spin_net_alert.connect("value-changed", self._on_widget_changed)
        self.row_net_alert.add_suffix(self.spin_net_alert)
        group.add(self.row_net_alert)

    def _build_kill_group(self):
        group = Adw.PreferencesGroup()
        group.set_title(":: KILL POLICY &amp; CANDIDATE SCORING ::")
        group.set_description("Automated recovery policies and victim candidate calculation weights.")
        self.prefs_page.add(group)

        # Kill Policy
        self.row_kill_policy = Adw.ActionRow()
        self.row_kill_policy.set_title("Kill Policy")
        self.row_kill_policy.set_subtitle("Algorithm used for candidate ranking (default: score)")
        self.entry_kill_policy = Gtk.Entry()
        self.entry_kill_policy.set_valign(Gtk.Align.CENTER)
        self.entry_kill_policy.connect("changed", self._on_widget_changed)
        self.row_kill_policy.add_suffix(self.entry_kill_policy)
        group.add(self.row_kill_policy)

        # Cooldown
        self.row_kill_cooldown = Adw.ActionRow()
        self.row_kill_cooldown.set_title("Kill Cooldown Period")
        self.row_kill_cooldown.set_subtitle("Minimum time window between automated process kills (e.g. 30s)")
        self.entry_kill_cooldown = Gtk.Entry()
        self.entry_kill_cooldown.set_valign(Gtk.Align.CENTER)
        self.entry_kill_cooldown.connect("changed", self._on_widget_changed)
        self.row_kill_cooldown.add_suffix(self.entry_kill_cooldown)
        group.add(self.row_kill_cooldown)

        # Max per min
        self.row_max_per_min = Adw.ActionRow()
        self.row_max_per_min.set_title("Maximum Kills Per Minute")
        self.row_max_per_min.set_subtitle("Limits how many processes Aegis can terminate during automated recovery")
        self.spin_max_per_min = Gtk.SpinButton.new_with_range(0.0, 60.0, 1.0)
        self.spin_max_per_min.set_valign(Gtk.Align.CENTER)
        self.spin_max_per_min.connect("value-changed", self._on_widget_changed)
        self.row_max_per_min.add_suffix(self.spin_max_per_min)
        group.add(self.row_max_per_min)

        # OOM Prefer
        self.row_oom_prefer = Adw.ActionRow()
        self.row_oom_prefer.set_title("OOM Prefer Expendables")
        self.row_oom_prefer.set_subtitle("Automatically mark expendable processes with higher OOM score adj (+1000)")
        self.switch_oom_prefer = Gtk.Switch()
        self.switch_oom_prefer.set_valign(Gtk.Align.CENTER)
        self.switch_oom_prefer.connect("notify::active", self._on_widget_changed)
        self.row_oom_prefer.add_suffix(self.switch_oom_prefer)
        group.add(self.row_oom_prefer)

        # OOM Protect
        self.row_oom_protect = Adw.ActionRow()
        self.row_oom_protect.set_title("OOM Protect Critical Apps")
        self.row_oom_protect.set_subtitle("Protect registered critical processes from kernel OOM killer (-1000)")
        self.switch_oom_protect = Gtk.Switch()
        self.switch_oom_protect.set_valign(Gtk.Align.CENTER)
        self.switch_oom_protect.connect("notify::active", self._on_widget_changed)
        self.row_oom_protect.add_suffix(self.switch_oom_protect)
        group.add(self.row_oom_protect)

        # Candidate Weights
        self.row_w_rss = Adw.ActionRow()
        self.row_w_rss.set_title("Scoring Weight: Memory (RSS)")
        self.row_w_rss.set_subtitle("Weight factor for process resident RAM consumption")
        self.spin_w_rss = Gtk.SpinButton.new_with_range(0.0, 1.0, 0.05)
        self.spin_w_rss.set_digits(2)
        self.spin_w_rss.set_valign(Gtk.Align.CENTER)
        self.spin_w_rss.connect("value-changed", self._on_widget_changed)
        self.row_w_rss.add_suffix(self.spin_w_rss)
        group.add(self.row_w_rss)

        self.row_w_cpu = Adw.ActionRow()
        self.row_w_cpu.set_title("Scoring Weight: CPU Usage")
        self.row_w_cpu.set_subtitle("Weight factor for process CPU utilization")
        self.spin_w_cpu = Gtk.SpinButton.new_with_range(0.0, 1.0, 0.05)
        self.spin_w_cpu.set_digits(2)
        self.spin_w_cpu.set_valign(Gtk.Align.CENTER)
        self.spin_w_cpu.connect("value-changed", self._on_widget_changed)
        self.row_w_cpu.add_suffix(self.spin_w_cpu)
        group.add(self.row_w_cpu)

        self.row_w_rt = Adw.ActionRow()
        self.row_w_rt.set_title("Scoring Weight: Runtime")
        self.row_w_rt.set_subtitle("Weight factor for process elapsed runtime")
        self.spin_w_rt = Gtk.SpinButton.new_with_range(0.0, 1.0, 0.05)
        self.spin_w_rt.set_digits(2)
        self.spin_w_rt.set_valign(Gtk.Align.CENTER)
        self.spin_w_rt.connect("value-changed", self._on_widget_changed)
        self.row_w_rt.add_suffix(self.spin_w_rt)
        group.add(self.row_w_rt)

        self.row_w_total = Adw.ActionRow()
        self.row_w_total.set_title("Total Scoring Weight")
        self.row_w_total.set_subtitle("Sum of scoring weights (must total 100%)")
        self.lbl_w_total = Gtk.Label(label="100%")
        self.lbl_w_total.set_valign(Gtk.Align.CENTER)
        self.lbl_w_total.add_css_class("bold")
        self.row_w_total.add_suffix(self.lbl_w_total)
        group.add(self.row_w_total)

    def _build_battery_group(self):
        group = Adw.PreferencesGroup()
        group.set_title("Battery Settings")
        group.set_description("Low power threshold and system suspend rules")
        self.prefs_page.add(group)

        # Low battery level
        self.row_bat_low = Adw.ActionRow()
        self.row_bat_low.set_title("Low Battery Threshold (%)")
        self.row_bat_low.set_subtitle("Battery percentage for low power warning or action")
        self.spin_bat_low = Gtk.SpinButton.new_with_range(0.0, 100.0, 1.0)
        self.spin_bat_low.set_valign(Gtk.Align.CENTER)
        self.spin_bat_low.connect("value-changed", self._on_widget_changed)
        self.row_bat_low.add_suffix(self.spin_bat_low)
        group.add(self.row_bat_low)

        # Battery action
        self.row_bat_action = Adw.ActionRow()
        self.row_bat_action.set_title("Low Battery Action")
        self.row_bat_action.set_subtitle("Action taken when low battery threshold is reached (e.g. suspend, notify)")
        self.entry_bat_action = Gtk.Entry()
        self.entry_bat_action.set_valign(Gtk.Align.CENTER)
        self.entry_bat_action.connect("changed", self._on_widget_changed)
        self.row_bat_action.add_suffix(self.entry_bat_action)
        group.add(self.row_bat_action)

    # ------------------ Logic & State Synchronization ------------------

    def update_config(self, config_dict: dict):
        """Called when configuration is fetched from the daemon."""
        if not config_dict or not isinstance(config_dict, dict):
            return

        self.server_config = copy.deepcopy(config_dict)
        # Only populate widgets from server if user has no unsaved local changes
        if not self.is_dirty:
            self.edited_config = copy.deepcopy(config_dict)
            self._populate_widgets_from_config(self.edited_config)
            self._revalidate()

    def _populate_widgets_from_config(self, cfg: dict):
        self._updating_widgets = True
        try:
            mem = cfg.get("memory", {})
            self.spin_mem_soft.set_value(mem.get("soft_pct", 90.0))
            self.spin_mem_hard.set_value(mem.get("hard_pct", 96.0))
            self.spin_mem_max.set_value(mem.get("max_pct", 99.0))

            cpu = cfg.get("cpu", {})
            self.spin_cpu_alert.set_value(cpu.get("alert_pct", 90.0))

            temp = cfg.get("temperature", {})
            self.spin_temp_warning.set_value(temp.get("warning", 85.0))
            self.spin_temp_critical.set_value(temp.get("critical", 90.0))
            self.entry_temp_action.set_text(temp.get("action", "kill"))

            disk = cfg.get("disk", {})
            self.spin_disk_space.set_value(disk.get("space_alert_pct", 90.0))
            self.switch_disk_io.set_active(disk.get("io_alert", True))

            net = cfg.get("network", {})
            self.spin_net_alert.set_value(net.get("alert_mbps", 900.0))

            kill = cfg.get("kill", {})
            self.entry_kill_policy.set_text(kill.get("policy", "score"))
            self.entry_kill_cooldown.set_text(kill.get("cooldown", "30s"))
            self.spin_max_per_min.set_value(kill.get("max_per_min", 3))
            self.switch_oom_prefer.set_active(kill.get("oom_prefer", True))
            self.switch_oom_protect.set_active(kill.get("oom_protect", True))

            w = kill.get("weights", {})
            self.spin_w_rss.set_value(w.get("rss", 0.6))
            self.spin_w_cpu.set_value(w.get("cpu", 0.3))
            self.spin_w_rt.set_value(w.get("runtime", 0.1))

            bat = cfg.get("battery", {})
            self.spin_bat_low.set_value(bat.get("low_pct", 20.0))
            self.entry_bat_action.set_text(bat.get("action", "suspend"))
        finally:
            self._updating_widgets = False

    def _collect_config_from_widgets(self) -> dict:
        return {
            "memory": {
                "soft_pct": round(self.spin_mem_soft.get_value(), 1),
                "hard_pct": round(self.spin_mem_hard.get_value(), 1),
                "max_pct": round(self.spin_mem_max.get_value(), 1)
            },
            "temperature": {
                "warning": round(self.spin_temp_warning.get_value(), 1),
                "critical": round(self.spin_temp_critical.get_value(), 1),
                "action": self.entry_temp_action.get_text().strip()
            },
            "cpu": {
                "alert_pct": round(self.spin_cpu_alert.get_value(), 1),
                "action": "notify"
            },
            "disk": {
                "space_alert_pct": round(self.spin_disk_space.get_value(), 1),
                "io_alert": self.switch_disk_io.get_active()
            },
            "network": {
                "alert_mbps": round(self.spin_net_alert.get_value(), 1)
            },
            "kill": {
                "policy": self.entry_kill_policy.get_text().strip(),
                "cooldown": self.entry_kill_cooldown.get_text().strip(),
                "max_per_min": int(self.spin_max_per_min.get_value()),
                "oom_prefer": self.switch_oom_prefer.get_active(),
                "oom_protect": self.switch_oom_protect.get_active(),
                "weights": {
                    "rss": round(self.spin_w_rss.get_value(), 2),
                    "cpu": round(self.spin_w_cpu.get_value(), 2),
                    "runtime": round(self.spin_w_rt.get_value(), 2)
                }
            },
            "battery": {
                "low_pct": round(self.spin_bat_low.get_value(), 1),
                "action": self.entry_bat_action.get_text().strip()
            }
        }

    def _on_widget_changed(self, *args):
        if self._updating_widgets:
            return

        self.edited_config = self._collect_config_from_widgets()
        self._revalidate()

    def _revalidate(self):
        # Update weight sum total display
        w_rss = self.spin_w_rss.get_value()
        w_cpu = self.spin_w_cpu.get_value()
        w_rt = self.spin_w_rt.get_value()
        w_total = round(w_rss + w_cpu + w_rt, 2)
        total_pct = int(round(w_total * 100))
        self.lbl_w_total.set_text(f"{total_pct}% ({w_total:.2f})")

        # Perform validation using config module
        self.is_valid = True
        val_error = None
        try:
            validate_config_dict(self.edited_config)
        except ValueError as ve:
            self.is_valid = False
            val_error = str(ve)

        # Check dirty state vs server config
        self.is_dirty = (self.edited_config != self.server_config)

        # Update UI feedback controls
        if self.is_offline:
            self.banner.set_title("[ DAEMON OFFLINE ] — Settings controls are disabled")
            self.banner.set_revealed(True)
            self.lbl_status.set_text(":: DAEMON OFFLINE ::")
            self.btn_save.set_sensitive(False)
            self.btn_revert.set_sensitive(False)
            self.btn_reset.set_sensitive(False)
        elif not self.is_valid:
            self.banner.set_title(f"[ INVALID CONFIG ] {val_error}")
            self.banner.set_revealed(True)
            self.lbl_status.set_text(":: VALIDATION ERROR ::")
            self.btn_save.set_sensitive(False)
            self.btn_revert.set_sensitive(self.is_dirty)
            self.btn_reset.set_sensitive(True)
        elif self.is_dirty:
            self.banner.set_revealed(False)
            self.lbl_status.set_text(":: UNSAVED CHANGES ::")
            self.btn_save.set_sensitive(True)
            self.btn_revert.set_sensitive(True)
            self.btn_reset.set_sensitive(True)
        else:
            self.banner.set_revealed(False)
            self.lbl_status.set_text(":: CONFIGURATION SAVED ::")
            self.btn_save.set_sensitive(False)
            self.btn_revert.set_sensitive(False)
            self.btn_reset.set_sensitive(True)

    # ------------------ Action Handlers ------------------

    def _on_save_clicked(self, button):
        if not self.is_dirty or not self.is_valid or self.is_offline or not self.ipc_client:
            return

        self.btn_save.set_sensitive(False)
        self.btn_revert.set_sensitive(False)
        self.lbl_status.set_text(":: SAVING... ::")

        self.ipc_client.update_config_async(self.edited_config, self._on_save_response)

    def _on_save_response(self, res, err):
        if err:
            error_msg = str(err)
            self.banner.set_title(f"[ SAVE FAILED ] {error_msg}")
            self.banner.set_revealed(True)
            self.lbl_status.set_text(":: SAVE FAILED ::")
            self._revalidate()
        elif res and res.get("updated"):
            self.server_config = copy.deepcopy(self.edited_config)
            self.banner.set_revealed(False)
            self.lbl_status.set_text(":: CONFIG APPLIED OK ::")
            self._revalidate()

    def _on_revert_clicked(self, button):
        if not self.server_config:
            return
        self.edited_config = copy.deepcopy(self.server_config)
        self._populate_widgets_from_config(self.edited_config)
        self._revalidate()

    def _on_reset_clicked(self, button):
        # Create confirmation dialog
        dialog = Adw.MessageDialog(
            heading="Reset Aegis Settings?",
            body="This will restore default configuration values. Process protection lists will be preserved."
        )
        if self.get_root():
            dialog.set_transient_for(self.get_root())

        dialog.add_response("cancel", "Cancel")
        dialog.add_response("reset", "Reset Defaults")
        dialog.set_response_appearance("reset", Adw.ResponseAppearance.DESTRUCTIVE)

        def _on_dialog_response(d, response_id):
            if response_id == "reset":
                self._do_reset_defaults()

        dialog.connect("response", _on_dialog_response)
        dialog.present()

    def _do_reset_defaults(self):
        def_cfg = get_default_config()
        # Convert default config object to dictionary
        def_dict = {
            "memory": {
                "soft_pct": def_cfg.memory.soft_pct,
                "hard_pct": def_cfg.memory.hard_pct,
                "max_pct": def_cfg.memory.max_pct
            },
            "temperature": {
                "warning": def_cfg.temperature.warning,
                "critical": def_cfg.temperature.critical,
                "action": def_cfg.temperature.action
            },
            "cpu": {
                "alert_pct": def_cfg.cpu.alert_pct,
                "action": def_cfg.cpu.action
            },
            "disk": {
                "space_alert_pct": def_cfg.disk.space_alert_pct,
                "io_alert": def_cfg.disk.io_alert
            },
            "network": {
                "alert_mbps": def_cfg.network.alert_mbps
            },
            "kill": {
                "policy": def_cfg.kill.policy,
                "cooldown": def_cfg.kill.cooldown,
                "max_per_min": def_cfg.kill.max_per_min,
                "oom_prefer": def_cfg.kill.oom_prefer,
                "oom_protect": def_cfg.kill.oom_protect,
                "weights": {
                    "rss": def_cfg.kill.weights.rss,
                    "cpu": def_cfg.kill.weights.cpu,
                    "runtime": def_cfg.kill.weights.runtime
                }
            },
            "battery": {
                "low_pct": def_cfg.battery.low_pct,
                "action": def_cfg.battery.action
            }
        }
        # Preserve protect and expendable from server config if present
        if "protect" in self.server_config:
            def_dict["protect"] = list(self.server_config["protect"])
        if "expendable" in self.server_config:
            def_dict["expendable"] = list(self.server_config["expendable"])

        self.edited_config = def_dict
        self._populate_widgets_from_config(self.edited_config)
        self._revalidate()

    def set_offline(self, is_offline: bool):
        """Called by parent window on daemon disconnect/reconnect."""
        self.is_offline = is_offline
        self._revalidate()
