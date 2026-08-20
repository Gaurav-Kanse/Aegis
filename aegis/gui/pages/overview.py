import time
import math
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib
from typing import Dict, Any, List, Optional

from aegis.gui.widgets.metric_card import MetricCard
from aegis.gui.widgets.health_ring import HealthRingGauge

class OverviewPage(Gtk.ScrolledWindow):
    def __init__(self, ipc_client: Optional[Any] = None, page_switcher: Optional[Any] = None):
        super().__init__()
        self.ipc_client = ipc_client
        self.page_switcher = page_switcher
        self.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self.history_samples: List[Dict[str, Any]] = []

        clamp = Adw.Clamp()
        clamp.set_maximum_size(1050)
        self.set_child(clamp)

        main_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        main_vbox.set_margin_start(20)
        main_vbox.set_margin_end(20)
        main_vbox.set_margin_top(20)
        main_vbox.set_margin_bottom(28)
        clamp.set_child(main_vbox)

        # Header Title Bar
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        title_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        
        lbl_title = Gtk.Label(label="System Overview")
        lbl_title.add_css_class("title-1")
        lbl_title.add_css_class("bold")
        lbl_title.set_halign(Gtk.Align.START)
        title_vbox.append(lbl_title)

        lbl_subtitle = Gtk.Label(label="Aegis is actively monitoring system resources & protecting core processes.")
        lbl_subtitle.add_css_class("aegis-subtext")
        lbl_subtitle.set_halign(Gtk.Align.START)
        title_vbox.append(lbl_subtitle)

        header_box.append(title_vbox)

        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        header_box.append(spacer)

        self.lbl_last_update = Gtk.Label(label="Updated: just now")
        self.lbl_last_update.add_css_class("aegis-subtext")
        self.lbl_last_update.set_valign(Gtk.Align.CENTER)
        header_box.append(self.lbl_last_update)

        main_vbox.append(header_box)

        # ---------------- Section 1: Summary Metric Cards Row ----------------
        grid_metrics = Gtk.Grid()
        grid_metrics.set_column_spacing(12)
        grid_metrics.set_row_spacing(12)
        grid_metrics.set_column_homogeneous(True)
        main_vbox.append(grid_metrics)

        self.card_mem = MetricCard("Memory", "drive-multidisk-symbolic")
        self.card_cpu = MetricCard("CPU", "cpu-symbolic")
        self.card_temp = MetricCard("Temperature", "temperature-symbolic")
        self.card_disk = MetricCard("Disk", "drive-harddisk-symbolic")
        self.card_net = MetricCard("Network", "network-transmit-receive-symbolic")

        grid_metrics.attach(self.card_mem, 0, 0, 1, 1)
        grid_metrics.attach(self.card_cpu, 1, 0, 1, 1)
        grid_metrics.attach(self.card_temp, 2, 0, 1, 1)
        grid_metrics.attach(self.card_disk, 3, 0, 1, 1)
        grid_metrics.attach(self.card_net, 4, 0, 1, 1)

        # ---------------- Section 2: Middle Cards Row ----------------
        middle_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        main_vbox.append(middle_box)

        # Card A: System Health Ring Gauge Card
        health_card = Gtk.Frame()
        health_card.add_css_class("aegis-card")
        health_card.set_size_request(300, -1)
        
        health_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        health_vbox.set_margin_start(16)
        health_vbox.set_margin_end(16)
        health_vbox.set_margin_top(14)
        health_vbox.set_margin_bottom(14)
        health_card.set_child(health_vbox)

        lbl_h_header = Gtk.Label(label="SYSTEM HEALTH")
        lbl_h_header.add_css_class("aegis-card-header")
        lbl_h_header.set_halign(Gtk.Align.START)
        health_vbox.append(lbl_h_header)

        self.health_ring = HealthRingGauge(size=140)
        self.health_ring.set_halign(Gtk.Align.CENTER)
        health_vbox.append(self.health_ring)

        # Status Rows
        self.lbl_mem_sub = self._add_subsystem_row(health_vbox, "Memory Pressure")
        self.lbl_cpu_sub = self._add_subsystem_row(health_vbox, "CPU Pressure")
        self.lbl_temp_sub = self._add_subsystem_row(health_vbox, "Thermal State")
        self.lbl_disk_sub = self._add_subsystem_row(health_vbox, "Disk Pressure")
        self.lbl_net_sub = self._add_subsystem_row(health_vbox, "Network Activity")

        middle_box.append(health_card)

        # Card B: Top Processes Card
        procs_card = Gtk.Frame()
        procs_card.add_css_class("aegis-card")
        procs_card.set_hexpand(True)

        procs_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        procs_vbox.set_margin_start(16)
        procs_vbox.set_margin_end(16)
        procs_vbox.set_margin_top(14)
        procs_vbox.set_margin_bottom(14)
        procs_card.set_child(procs_vbox)

        procs_head_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        lbl_p_header = Gtk.Label(label="TOP PROCESSES")
        lbl_p_header.add_css_class("aegis-card-header")
        lbl_p_header.set_halign(Gtk.Align.START)
        procs_head_box.append(lbl_p_header)

        p_spacer = Gtk.Box()
        p_spacer.set_hexpand(True)
        procs_head_box.append(p_spacer)

        btn_view_procs = Gtk.Button(label="View All")
        btn_view_procs.add_css_class("flat")
        btn_view_procs.connect("clicked", lambda b: self._switch_page("processes"))
        procs_head_box.append(btn_view_procs)

        procs_vbox.append(procs_head_box)

        # Column headers
        p_hdr_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        p_hdr_box.add_css_class("aegis-subtext")
        
        lbl_p_name = Gtk.Label(label="Process")
        lbl_p_name.set_hexpand(True)
        lbl_p_name.set_halign(Gtk.Align.START)
        p_hdr_box.append(lbl_p_name)

        lbl_p_cpu = Gtk.Label(label="CPU")
        lbl_p_cpu.set_size_request(60, -1)
        p_hdr_box.append(lbl_p_cpu)

        lbl_p_mem = Gtk.Label(label="Memory")
        lbl_p_mem.set_size_request(80, -1)
        p_hdr_box.append(lbl_p_mem)

        lbl_p_score = Gtk.Label(label="Score")
        lbl_p_score.set_size_request(50, -1)
        p_hdr_box.append(lbl_p_score)

        procs_vbox.append(p_hdr_box)

        self.top_procs_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        procs_vbox.append(self.top_procs_list)

        middle_box.append(procs_card)

        # Card C: Recent Events Card
        events_card = Gtk.Frame()
        events_card.add_css_class("aegis-card")
        events_card.set_hexpand(True)

        events_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        events_vbox.set_margin_start(16)
        events_vbox.set_margin_end(16)
        events_vbox.set_margin_top(14)
        events_vbox.set_margin_bottom(14)
        events_card.set_child(events_vbox)

        events_head_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        lbl_e_header = Gtk.Label(label="RECENT EVENTS")
        lbl_e_header.add_css_class("aegis-card-header")
        lbl_e_header.set_halign(Gtk.Align.START)
        events_head_box.append(lbl_e_header)

        e_spacer = Gtk.Box()
        e_spacer.set_hexpand(True)
        events_head_box.append(e_spacer)

        btn_view_events = Gtk.Button(label="View All")
        btn_view_events.add_css_class("flat")
        btn_view_events.connect("clicked", lambda b: self._switch_page("events"))
        events_head_box.append(btn_view_events)

        events_vbox.append(events_head_box)

        self.recent_events_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        events_vbox.append(self.recent_events_list)

        middle_box.append(events_card)

        # ---------------- Section 3: Resource History Live Chart Card ----------------
        chart_card = Gtk.Frame()
        chart_card.add_css_class("aegis-card")

        chart_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        chart_vbox.set_margin_start(16)
        chart_vbox.set_margin_end(16)
        chart_vbox.set_margin_top(14)
        chart_vbox.set_margin_bottom(14)
        chart_card.set_child(chart_vbox)

        chart_hdr = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        lbl_c_title = Gtk.Label(label="RESOURCE HISTORY")
        lbl_c_title.add_css_class("aegis-card-header")
        chart_hdr.append(lbl_c_title)

        c_spacer = Gtk.Box()
        c_spacer.set_hexpand(True)
        chart_hdr.append(c_spacer)

        self.lbl_chart_stats = Gtk.Label(label="RAM: -- | CPU: --")
        self.lbl_chart_stats.add_css_class("aegis-subtext")
        chart_hdr.append(self.lbl_chart_stats)

        chart_vbox.append(chart_hdr)

        self.chart_canvas = Gtk.DrawingArea()
        self.chart_canvas.set_size_request(-1, 140)
        self.chart_canvas.set_draw_func(self._on_draw_chart)
        chart_vbox.append(self.chart_canvas)

        main_vbox.append(chart_card)

    def _add_subsystem_row(self, vbox: Gtk.Box, name: str) -> Gtk.Label:
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        lbl_name = Gtk.Label(label=name)
        lbl_name.add_css_class("aegis-subtext")
        lbl_name.set_halign(Gtk.Align.START)
        lbl_name.set_hexpand(True)
        row.append(lbl_name)

        lbl_val = Gtk.Label(label="Normal")
        lbl_val.add_css_class("status-badge")
        lbl_val.add_css_class("normal")
        row.append(lbl_val)

        vbox.append(row)
        return lbl_val

    def _switch_page(self, page_name: str):
        if self.page_switcher:
            self.page_switcher(page_name)

    def update_data(self, status: Dict[str, Any]):
        if not status:
            return

        self.lbl_last_update.set_text(f"Updated: {time.strftime('%H:%M:%S')}")

        health = status.get("health", 100)
        state = status.get("state", "PROTECTED")
        self.health_ring.set_status(health, state)

        # Memory Card
        mem = status.get("memory", {})
        used = mem.get("used", 0.0)
        total = mem.get("total", 0.0)
        pct = mem.get("percent", 0.0)
        self.card_mem.set_metric(f"{pct:.0f}%", pct / 100.0, f"{used:.1f} / {total:.1f} GB")

        # CPU Card
        cpu_pct = status.get("cpu", 0.0)
        self.card_cpu.set_metric(f"{cpu_pct:.0f}%", cpu_pct / 100.0, "Utilization")

        # Temperature Card
        temp_c = status.get("temperature", 0.0)
        self.card_temp.set_metric(f"{temp_c:.0f}°C", temp_c / 100.0, "Normal" if temp_c < 85 else "High")

        # Disk Card
        disk = status.get("disk", {})
        root_pct = disk.get("/", 0.0)
        self.card_disk.set_metric(f"{root_pct:.0f}%", root_pct / 100.0, "Storage used")

        # Network Card
        net = status.get("network", {})
        tot_net = sum(v for k, v in net.items() if isinstance(v, (int, float)))
        self.card_net.set_metric(f"{tot_net:.1f}", min(1.0, tot_net / 1000.0), "Mbps activity")

        # PSI Card / Subsystems
        psi = status.get("psi", {})
        some_psi = psi.get("some_avg10", 0.0)
        full_psi = psi.get("full_avg10", 0.0)

        # Update Subsystem Status Labels
        self._update_status_badge(self.lbl_mem_sub, pct >= 96, pct >= 90)
        self._update_status_badge(self.lbl_cpu_sub, False, cpu_pct >= 90)
        self._update_status_badge(self.lbl_temp_sub, temp_c >= 90, temp_c >= 85)
        self._update_status_badge(self.lbl_disk_sub, False, root_pct >= 90)
        self._update_status_badge(self.lbl_net_sub, False, tot_net >= 900)

        # Update Chart Sample History
        sample = {
            "timestamp": time.time(),
            "cpu": cpu_pct,
            "memory": pct
        }
        self.history_samples.append(sample)
        if len(self.history_samples) > 300:
            self.history_samples = self.history_samples[-300:]
        
        self.lbl_chart_stats.set_text(f"RAM: {pct:.1f}%  |  CPU: {cpu_pct:.1f}%")
        self.chart_canvas.queue_draw()

        # Fetch Top Processes & Events via IPC Client if available
        if self.ipc_client:
            self.ipc_client.fetch_processes_async(self._on_top_procs_response)
            self.ipc_client.fetch_events_async(5, self._on_recent_events_response)

    def _update_status_badge(self, label: Gtk.Label, is_critical: bool, is_warning: bool):
        for cls in ["normal", "warning", "critical"]:
            label.remove_css_class(cls)
        if is_critical:
            label.set_label("Critical")
            label.add_css_class("critical")
        elif is_warning:
            label.set_label("Warning")
            label.add_css_class("warning")
        else:
            label.set_label("Normal")
            label.add_css_class("normal")

    def _on_top_procs_response(self, procs, err):
        if not procs or not isinstance(procs, list):
            return

        # Clear existing rows
        while child := self.top_procs_list.get_first_child():
            self.top_procs_list.remove(child)

        top5 = procs[:5]
        for p in top5:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            
            name = p.get("name", "unknown")
            lbl_n = Gtk.Label(label=name[:16])
            lbl_n.set_hexpand(True)
            lbl_n.set_halign(Gtk.Align.START)
            row.append(lbl_n)

            cpu = p.get("cpu", 0.0)
            lbl_c = Gtk.Label(label=f"{cpu:.1f}%")
            lbl_c.set_size_request(60, -1)
            lbl_c.add_css_class("aegis-subtext")
            row.append(lbl_c)

            rss = p.get("rss", 0)
            rss_mb = rss // (1024 * 1024)
            lbl_m = Gtk.Label(label=f"{rss_mb} MB")
            lbl_m.set_size_request(80, -1)
            lbl_m.add_css_class("aegis-subtext")
            row.append(lbl_m)

            score = p.get("score", 0.0)
            lbl_s = Gtk.Label(label=f"{score:.2f}")
            lbl_s.set_size_request(50, -1)
            lbl_s.add_css_class("bold")
            row.append(lbl_s)

            self.top_procs_list.append(row)

    def _on_recent_events_response(self, events, err):
        if not events or not isinstance(events, list):
            return

        while child := self.recent_events_list.get_first_child():
            self.recent_events_list.remove(child)

        for ev in events[:5]:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            
            ts = ev.get("timestamp", "")
            time_str = ts.split("T")[-1][:8] if "T" in ts else ts[:8]
            lbl_t = Gtk.Label(label=time_str)
            lbl_t.add_css_class("aegis-subtext")
            row.append(lbl_t)

            source = ev.get("source", "system").upper()
            lbl_src = Gtk.Label(label=source)
            lbl_src.add_css_class("status-badge")
            lbl_src.add_css_class("normal")
            row.append(lbl_src)

            msg = ev.get("message", "")
            lbl_msg = Gtk.Label(label=msg[:32])
            lbl_msg.set_hexpand(True)
            lbl_msg.set_halign(Gtk.Align.START)
            row.append(lbl_msg)

            self.recent_events_list.append(row)

    def _on_draw_chart(self, area, cr, width, height):
        # Draw background grid
        cr.set_source_rgba(1.0, 1.0, 1.0, 0.03)
        for y in range(0, height, 30):
            cr.move_to(0, y)
            cr.line_to(width, y)
            cr.stroke()

        if not self.history_samples or len(self.history_samples) < 2:
            return

        # Render Memory & CPU trend lines
        pts_mem = []
        pts_cpu = []
        n = len(self.history_samples)
        dx = width / max(1, n - 1)

        for i, s in enumerate(self.history_samples):
            x = i * dx
            y_mem = height - (s.get("memory", 0.0) / 100.0 * height)
            y_cpu = height - (s.get("cpu", 0.0) / 100.0 * height)
            pts_mem.append((x, y_mem))
            pts_cpu.append((x, y_cpu))

        # Memory Line (White)
        cr.set_source_rgba(0.95, 0.95, 0.96, 0.9)
        cr.set_line_width(2.0)
        cr.move_to(pts_mem[0][0], pts_mem[0][1])
        for x, y in pts_mem[1:]:
            cr.line_to(x, y)
        cr.stroke()

        # CPU Line (Muted Gray)
        cr.set_source_rgba(0.6, 0.6, 0.65, 0.6)
        cr.set_line_width(1.5)
        cr.move_to(pts_cpu[0][0], pts_cpu[0][1])
        for x, y in pts_cpu[1:]:
            cr.line_to(x, y)
        cr.stroke()
