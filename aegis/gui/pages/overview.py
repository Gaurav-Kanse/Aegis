import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw
from typing import Dict, Any

from aegis.gui.widgets.shield_badge import ShieldBadge
from aegis.gui.widgets.metric_card import MetricCard

class OverviewPage(Gtk.ScrolledWindow):
    def __init__(self):
        super().__init__()
        self.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        clamp = Adw.Clamp()
        clamp.set_maximum_size(900)
        self.set_child(clamp)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        main_box.set_margin_start(16)
        main_box.set_margin_end(16)
        main_box.set_margin_top(16)
        main_box.set_margin_bottom(24)
        clamp.set_child(main_box)

        # Section A: Shield Badge
        self.shield_badge = ShieldBadge()
        main_box.append(self.shield_badge)

        # Section B: Metric Cards Grid
        grid_title = Gtk.Label(label="SYSTEM METRICS")
        grid_title.add_css_class("heading")
        grid_title.add_css_class("dim-label")
        grid_title.set_halign(Gtk.Align.START)
        main_box.append(grid_title)

        grid = Gtk.Grid()
        grid.set_column_spacing(12)
        grid.set_row_spacing(12)
        grid.set_column_homogeneous(True)
        main_box.append(grid)

        self.card_cpu = MetricCard("CPU", "cpu-symbolic")
        self.card_mem = MetricCard("Memory", "drive-multidisk-symbolic")
        self.card_temp = MetricCard("Temperature", "temperature-symbolic")
        self.card_disk = MetricCard("Disk", "drive-harddisk-symbolic")
        self.card_net = MetricCard("Network", "network-transmit-receive-symbolic")
        self.card_psi = MetricCard("Pressure (PSI)", "speedometer-symbolic")
        self.card_bat = MetricCard("Battery", "battery-good-symbolic")

        grid.attach(self.card_mem, 0, 0, 1, 1)
        grid.attach(self.card_cpu, 1, 0, 1, 1)
        grid.attach(self.card_temp, 0, 1, 1, 1)
        grid.attach(self.card_psi, 1, 1, 1, 1)
        grid.attach(self.card_disk, 0, 2, 1, 1)
        grid.attach(self.card_net, 1, 2, 1, 1)
        grid.attach(self.card_bat, 0, 3, 2, 1)

        # Section C: System Status List
        status_group = Adw.PreferencesGroup()
        status_group.set_title("Subsystem Status")
        main_box.append(status_group)

        self.row_mem = Adw.ActionRow(title="Memory (cgroup v2)")
        self.lbl_mem_status = Gtk.Label(label="● Normal")
        self.lbl_mem_status.add_css_class("success")
        self.row_mem.add_suffix(self.lbl_mem_status)
        status_group.add(self.row_mem)

        self.row_cpu = Adw.ActionRow(title="CPU Utilization")
        self.lbl_cpu_status = Gtk.Label(label="● Normal")
        self.lbl_cpu_status.add_css_class("success")
        self.row_cpu.add_suffix(self.lbl_cpu_status)
        status_group.add(self.row_cpu)

        self.row_temp = Adw.ActionRow(title="Thermal Sensors")
        self.lbl_temp_status = Gtk.Label(label="● Normal")
        self.lbl_temp_status.add_css_class("success")
        self.row_temp.add_suffix(self.lbl_temp_status)
        status_group.add(self.row_temp)

        self.row_disk = Adw.ActionRow(title="Storage & Disk I/O")
        self.lbl_disk_status = Gtk.Label(label="● Normal")
        self.lbl_disk_status.add_css_class("success")
        self.row_disk.add_suffix(self.lbl_disk_status)
        status_group.add(self.row_disk)

        self.row_net = Adw.ActionRow(title="Network Interfaces")
        self.lbl_net_status = Gtk.Label(label="● Normal")
        self.lbl_net_status.add_css_class("success")
        self.row_net.add_suffix(self.lbl_net_status)
        status_group.add(self.row_net)

        self.row_psi = Adw.ActionRow(title="Pressure Stall Information")
        self.lbl_psi_status = Gtk.Label(label="● Normal")
        self.lbl_psi_status.add_css_class("success")
        self.row_psi.add_suffix(self.lbl_psi_status)
        status_group.add(self.row_psi)

    def update_data(self, status: Dict[str, Any]):
        if not status:
            return

        health = status.get("health", 100)
        state = status.get("state", "PROTECTED")
        self.shield_badge.set_status(health, state)

        # Memory Card
        mem = status.get("memory", {})
        used = mem.get("used", 0.0)
        total = mem.get("total", 0.0)
        pct = mem.get("percent", 0.0)
        self.card_mem.set_metric(f"{used:.1f} / {total:.1f} GB ({pct:.1f}%)", pct / 100.0)

        # CPU Card
        cpu_pct = status.get("cpu", 0.0)
        self.card_cpu.set_metric(f"{cpu_pct:.1f}%", cpu_pct / 100.0)

        # Temperature Card
        temp_c = status.get("temperature", 0.0)
        self.card_temp.set_metric(f"{temp_c:.1f}°C", temp_c / 100.0)

        # Pressure PSI Card
        psi = status.get("psi", {})
        some_psi = psi.get("some_avg10", 0.0)
        full_psi = psi.get("full_avg10", 0.0)
        self.card_psi.set_metric(f"some {some_psi:.1f}% | full {full_psi:.1f}%", max(some_psi, full_psi) / 100.0)

        # Disk Card
        disk = status.get("disk", {})
        root_pct = disk.get("/", 0.0)
        self.card_disk.set_metric(f"{root_pct:.1f}% used", root_pct / 100.0)

        # Network Card
        net = status.get("network", {})
        tot_net = sum(v for k, v in net.items() if isinstance(v, (int, float)))
        self.card_net.set_metric(f"{tot_net:.2f} Mbps", min(1.0, tot_net / 1000.0))

        # Battery Card
        bat = status.get("battery", {})
        if bat:
            b_cap = bat.get("capacity", 100.0)
            b_dis = "Discharging" if bat.get("discharging") else "Charging/Full"
            self.card_bat.set_metric(f"{b_cap:.0f}% ({b_dis})", b_cap / 100.0)
        else:
            self.card_bat.set_metric("N/A (Desktop/AC)", 1.0)

        # Update Subsystem Status Dots
        self._update_status_dot(self.lbl_mem_status, pct >= 96, pct >= 90)
        self._update_status_dot(self.lbl_cpu_status, False, cpu_pct >= 90)
        self._update_status_dot(self.lbl_temp_status, temp_c >= 90, temp_c >= 85)
        self._update_status_dot(self.lbl_disk_status, False, root_pct >= 90)
        self._update_status_dot(self.lbl_psi_status, full_psi >= 30, some_psi >= 40)

    def _update_status_dot(self, label: Gtk.Label, is_critical: bool, is_warning: bool):
        for cls in ["success", "warning", "error"]:
            label.remove_css_class(cls)
        if is_critical:
            label.set_label("● Critical")
            label.add_css_class("error")
        elif is_warning:
            label.set_label("● Warning")
            label.add_css_class("warning")
        else:
            label.set_label("● Normal")
            label.add_css_class("success")
