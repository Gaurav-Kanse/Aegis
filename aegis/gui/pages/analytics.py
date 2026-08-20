import time
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib
import cairo
from typing import List, Dict, Any, Optional

from aegis.gui.client import GUIIPCClient

PRIMARY_METRICS = [
    ("CPU", "cpu", "%", 100.0),
    ("Memory", "memory", "%", 100.0),
    ("Temp", "temperature", "°C", 100.0),
    ("Disk", "disk", "%", 100.0),
    ("Network", "network", "Mbps", 0.0),
    ("PSI CPU", "psi_cpu", "%", 100.0),
    ("PSI Memory", "psi_memory", "%", 100.0),
]

TIME_RANGES = [
    ("5m", 300),
    ("30m", 1800),
    ("1h", 3600),
]

class AnalyticsPage(Gtk.Box):
    def __init__(self, ipc_client: Optional[GUIIPCClient] = None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.ipc_client = ipc_client

        self.history_buffer: List[Dict[str, Any]] = []
        self.selected_metric_idx = 0
        self.selected_time_range_idx = 0

        # Scrolled Container
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        self.append(scrolled)

        clamp = Adw.Clamp()
        clamp.set_maximum_size(1050)
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

        lbl_title = Gtk.Label(label="Analytics & Telemetry")
        lbl_title.add_css_class("title-1")
        lbl_title.add_css_class("bold")
        lbl_title.set_halign(Gtk.Align.START)
        title_vbox.append(lbl_title)

        lbl_sub = Gtk.Label(label="Clear, real-time resource utilization history & trend analysis")
        lbl_sub.add_css_class("aegis-subtext")
        lbl_sub.set_halign(Gtk.Align.START)
        title_vbox.append(lbl_sub)

        hdr_box.append(title_vbox)

        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        hdr_box.append(spacer)

        btn_refresh = Gtk.Button()
        btn_refresh.set_icon_name("view-refresh-symbolic")
        btn_refresh.set_tooltip_text("Refresh Telemetry History")
        btn_refresh.connect("clicked", lambda b: self.refresh_history())
        hdr_box.append(btn_refresh)

        main_vbox.append(hdr_box)

        # Quick Metric Filter Tabs Bar (CPU, Memory, Temp, Disk, Network, PSI)
        filter_card = Gtk.Frame()
        filter_card.add_css_class("aegis-card")

        filter_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        filter_box.set_margin_start(12)
        filter_box.set_margin_end(12)
        filter_box.set_margin_top(10)
        filter_box.set_margin_bottom(10)
        filter_card.set_child(filter_box)

        self.metric_btns: List[Gtk.Button] = []
        for idx, (label, key, unit, scale) in enumerate(PRIMARY_METRICS):
            btn = Gtk.Button(label=label)
            btn.add_css_class("tab-btn")
            if idx == 0:
                btn.add_css_class("active")
            btn.connect("clicked", lambda b, i=idx: self._select_metric(i))
            filter_box.append(btn)
            self.metric_btns.append(btn)

        f_spacer = Gtk.Box()
        f_spacer.set_hexpand(True)
        filter_box.append(f_spacer)

        # Time Window Selector (5m, 30m, 1h)
        self.range_btns: List[Gtk.Button] = []
        for idx, (lbl, secs) in enumerate(TIME_RANGES):
            btn = Gtk.Button(label=lbl)
            btn.add_css_class("tab-btn")
            if idx == 0:
                btn.add_css_class("active")
            btn.connect("clicked", lambda b, i=idx: self._select_time_range(i))
            filter_box.append(btn)
            self.range_btns.append(btn)

        main_vbox.append(filter_card)

        # Stats Cards Row (CURRENT, AVERAGE, MINIMUM, MAXIMUM)
        stats_grid = Gtk.Grid()
        stats_grid.set_column_spacing(12)
        stats_grid.set_row_spacing(12)
        stats_grid.set_column_homogeneous(True)
        main_vbox.append(stats_grid)

        self.card_curr = self._create_stat_card("CURRENT VALUE", "--", stats_grid, 0)
        self.card_avg = self._create_stat_card("WINDOW AVERAGE", "--", stats_grid, 1)
        self.card_min = self._create_stat_card("WINDOW MINIMUM", "--", stats_grid, 2)
        self.card_max = self._create_stat_card("WINDOW MAXIMUM", "--", stats_grid, 3)

        # Main Telemetry Graph Card
        chart_card = Gtk.Frame()
        chart_card.add_css_class("aegis-card")

        chart_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        chart_vbox.set_margin_start(16)
        chart_vbox.set_margin_end(16)
        chart_vbox.set_margin_top(14)
        chart_vbox.set_margin_bottom(14)
        chart_card.set_child(chart_vbox)

        chart_hdr = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.chart_header_lbl = Gtk.Label(label="Resource Telemetry Trend")
        self.chart_header_lbl.add_css_class("aegis-card-header")
        self.chart_header_lbl.set_halign(Gtk.Align.START)
        chart_hdr.append(self.chart_header_lbl)

        c_spacer = Gtk.Box()
        c_spacer.set_hexpand(True)
        chart_hdr.append(c_spacer)

        self.lbl_legend_info = Gtk.Label(label="— Trend Line  - - Alert Threshold (90%)")
        self.lbl_legend_info.add_css_class("aegis-subtext")
        chart_hdr.append(self.lbl_legend_info)

        chart_vbox.append(chart_hdr)

        self.drawing_area = Gtk.DrawingArea()
        self.drawing_area.set_size_request(-1, 320)
        self.drawing_area.set_draw_func(self._on_draw_chart)
        chart_vbox.append(self.drawing_area)

        main_vbox.append(chart_card)

    def _create_stat_card(self, title: str, val: str, grid: Gtk.Grid, col: int) -> Gtk.Label:
        frame = Gtk.Frame()
        frame.add_css_class("aegis-card")
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_top(10)
        box.set_margin_bottom(10)

        lbl_title = Gtk.Label(label=title)
        lbl_title.add_css_class("aegis-card-header")
        lbl_title.set_halign(Gtk.Align.START)
        box.append(lbl_title)

        lbl_val = Gtk.Label(label=val)
        lbl_val.add_css_class("aegis-value-medium")
        lbl_val.set_halign(Gtk.Align.START)
        box.append(lbl_val)

        frame.set_child(box)
        grid.attach(frame, col, 0, 1, 1)
        return lbl_val

    def set_ipc_client(self, client: GUIIPCClient):
        self.ipc_client = client

    def refresh_history(self):
        if self.ipc_client:
            self.ipc_client.fetch_metrics_history_async(300, lambda h, e: self.set_metrics_history(h) if h else None)

    def update_sample(self, status: Dict[str, Any]):
        sample = {
            "timestamp": time.time(),
            "cpu": status.get("cpu", 0.0),
            "memory": status.get("memory", {}).get("percent", 0.0),
            "temperature": status.get("temperature", 0.0),
            "disk": list(status.get("disk", {}).values())[0] if status.get("disk") else 0.0,
            "network_rx": sum(v for k, v in status.get("network", {}).items() if k.endswith("_rx_mbps")),
            "network_tx": sum(v for k, v in status.get("network", {}).items() if k.endswith("_tx_mbps")),
            "psi_cpu": status.get("psi", {}).get("some_avg10", 0.0),
            "psi_memory": status.get("psi", {}).get("full_avg10", 0.0),
        }
        self.history_buffer.append(sample)
        if len(self.history_buffer) > 3600:
            self.history_buffer = self.history_buffer[-3600:]

        self._update_stats_and_redraw()

    def set_metrics_history(self, history: List[Dict[str, Any]]):
        if history:
            self.history_buffer = history
            self._update_stats_and_redraw()

    def _select_metric(self, idx: int):
        self.selected_metric_idx = idx
        for i, btn in enumerate(self.metric_btns):
            if i == idx:
                btn.add_css_class("active")
            else:
                btn.remove_css_class("active")
        self._update_stats_and_redraw()

    def _select_time_range(self, idx: int):
        self.selected_time_range_idx = idx
        for i, btn in enumerate(self.range_btns):
            if i == idx:
                btn.add_css_class("active")
            else:
                btn.remove_css_class("active")
        self._update_stats_and_redraw()

    def _get_window_samples(self) -> List[Dict[str, Any]]:
        max_secs = TIME_RANGES[self.selected_time_range_idx][1]
        now = time.time()
        cutoff = now - max_secs
        return [s for s in self.history_buffer if s.get("timestamp", 0) >= cutoff]

    def _update_stats_and_redraw(self):
        samples = self._get_window_samples()
        metric_info = PRIMARY_METRICS[self.selected_metric_idx]
        metric_key = metric_info[1]
        unit = metric_info[2]
        title = metric_info[0]

        self.chart_header_lbl.set_text(f"{title.upper()} TELEMETRY HISTORY — LAST {TIME_RANGES[self.selected_time_range_idx][0].upper()}")

        if not samples:
            self.card_curr.set_text("--")
            self.card_avg.set_text("--")
            self.card_min.set_text("--")
            self.card_max.set_text("--")
            self.drawing_area.queue_draw()
            return

        if metric_key == "network":
            vals = [s.get("network_rx", 0.0) + s.get("network_tx", 0.0) for s in samples]
        else:
            vals = [s.get(metric_key, 0.0) for s in samples]

        curr = vals[-1] if vals else 0.0
        avg = sum(vals) / len(vals) if vals else 0.0
        mn = min(vals) if vals else 0.0
        mx = max(vals) if vals else 0.0

        self.card_curr.set_text(f"{curr:.1f} {unit}")
        self.card_avg.set_text(f"{avg:.1f} {unit}")
        self.card_min.set_text(f"{mn:.1f} {unit}")
        self.card_max.set_text(f"{mx:.1f} {unit}")

        self.drawing_area.queue_draw()

    def _on_draw_chart(self, area, cr: cairo.Context, width: int, height: int):
        # Background
        cr.set_source_rgb(0.09, 0.09, 0.11)
        cr.rectangle(0, 0, width, height)
        cr.fill()

        samples = self._get_window_samples()
        if not samples:
            cr.set_source_rgba(0.6, 0.6, 0.6, 0.6)
            cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
            cr.set_font_size(13)
            cr.move_to(width / 2 - 80, height / 2)
            cr.show_text("Waiting for Aegis telemetry history...")
            return

        margin_left = 60
        margin_right = 30
        margin_top = 25
        margin_bottom = 35

        chart_w = width - margin_left - margin_right
        chart_h = height - margin_top - margin_bottom

        metric_info = PRIMARY_METRICS[self.selected_metric_idx]
        metric_key = metric_info[1]
        unit = metric_info[2]
        max_scale = metric_info[3]

        if metric_key == "network":
            vals = [s.get("network_rx", 0.0) + s.get("network_tx", 0.0) for s in samples]
        else:
            vals = [s.get(metric_key, 0.0) for s in samples]

        if max_scale <= 0.0:
            max_scale = max(1.0, max(vals) * 1.25)

        # 1. Y-Axis Grid Lines & Tick Labels (100%, 75%, 50%, 25%, 0%)
        cr.set_line_width(1)
        cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        cr.set_font_size(10)

        for i in range(5):
            ratio = (4 - i) / 4.0
            y = margin_top + chart_h * (1.0 - ratio)

            # Grid Line
            cr.set_source_rgba(1.0, 1.0, 1.0, 0.05)
            cr.move_to(margin_left, y)
            cr.line_to(width - margin_right, y)
            cr.stroke()

            # Axis Tick Label
            val_tick = max_scale * ratio
            tick_str = f"{val_tick:.0f}{unit}" if unit == "%" or max_scale >= 10 else f"{val_tick:.1f}{unit}"
            cr.set_source_rgba(0.6, 0.6, 0.65, 0.8)
            cr.move_to(10, y + 4)
            cr.show_text(tick_str)

        # 2. Threshold Warning Line (Dashed red line at 90% if scale == 100%)
        if max_scale == 100.0:
            thresh_y = margin_top + chart_h * (1.0 - 0.90)
            cr.set_source_rgba(0.97, 0.44, 0.44, 0.5)
            cr.set_line_width(1)
            cr.set_dash([4, 4], 0)
            cr.move_to(margin_left, thresh_y)
            cr.line_to(width - margin_right, thresh_y)
            cr.stroke()
            cr.set_dash([], 0)  # Reset dash

        # 3. X-Axis Time Labels (-5m, -2.5m, now)
        time_label = TIME_RANGES[self.selected_time_range_idx][0]
        cr.set_source_rgba(0.6, 0.6, 0.65, 0.8)
        cr.move_to(margin_left, height - 10)
        cr.show_text(f"-{time_label}")
        
        cr.move_to(margin_left + chart_w / 2 - 15, height - 10)
        cr.show_text(f"-{int(TIME_RANGES[self.selected_time_range_idx][1] / 120)}m")

        cr.move_to(width - margin_right - 25, height - 10)
        cr.show_text("NOW")

        # 4. Plot Trend Line & Shaded Area
        n = len(vals)
        step_x = chart_w / max(1, n - 1)
        points = []

        for i, val in enumerate(vals):
            x = margin_left + i * step_x
            norm_y = max(0.0, min(1.0, val / max_scale))
            y = margin_top + chart_h * (1.0 - norm_y)
            points.append((x, y))

        if points:
            # Gradient fill under line
            cr.move_to(margin_left, margin_top + chart_h)
            for x, y in points:
                cr.line_to(x, y)
            cr.line_to(points[-1][0], margin_top + chart_h)
            cr.close_path()

            grad = cairo.LinearGradient(0, margin_top, 0, margin_top + chart_h)
            grad.add_color_stop_rgba(0, 1.0, 1.0, 1.0, 0.18)
            grad.add_color_stop_rgba(1, 1.0, 1.0, 1.0, 0.01)
            cr.set_source(grad)
            cr.fill()

            # Crisp main plot line
            cr.set_source_rgba(0.95, 0.95, 0.96, 0.95)
            cr.set_line_width(2.0)
            cr.move_to(points[0][0], points[0][1])
            for x, y in points[1:]:
                cr.line_to(x, y)
            cr.stroke()

            # Highlight current value point with a subtle white dot
            cx, cy = points[-1]
            cr.set_source_rgba(1.0, 1.0, 1.0, 1.0)
            cr.arc(cx, cy, 4, 0, 2 * 3.14159)
            cr.fill()
