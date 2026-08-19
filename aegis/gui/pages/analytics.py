import time
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib
import cairo
from typing import List, Dict, Any, Optional

from aegis.gui.client import GUIIPCClient

METRIC_OPTIONS = [
    ("CPU Usage (%)", "cpu", "%", 100.0),
    ("Memory Usage (%)", "memory", "%", 100.0),
    ("Temperature (°C)", "temperature", "°C", 100.0),
    ("Disk Usage (%)", "disk", "%", 100.0),
    ("Network Activity (Mbps)", "network", "Mbps", 0.0),
    ("PSI CPU Pressure (%)", "psi_cpu", "%", 100.0),
    ("PSI Memory Pressure (%)", "psi_memory", "%", 100.0),
    ("PSI I/O Pressure (%)", "psi_io", "%", 100.0),
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

        # Top Control Bar (Metric selector, Time range, Refresh)
        ctrl_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        ctrl_bar.set_margin_start(16)
        ctrl_bar.set_margin_end(16)
        ctrl_bar.set_margin_top(12)
        ctrl_bar.set_margin_bottom(12)
        self.append(ctrl_bar)

        # Metric DropDown
        metric_titles = [m[0] for m in METRIC_OPTIONS]
        self.metric_dropdown = Gtk.DropDown.new_from_strings(metric_titles)
        self.metric_dropdown.set_selected(0)
        self.metric_dropdown.connect("notify::selected", self._on_selection_changed)
        ctrl_bar.append(self.metric_dropdown)

        # Spacer
        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        ctrl_bar.append(spacer)

        # Time Range Buttons
        self.range_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.range_btns: List[Gtk.Button] = []
        for idx, (lbl, secs) in enumerate(TIME_RANGES):
            btn = Gtk.Button(label=lbl)
            if idx == 0:
                btn.add_css_class("suggested-action")
            btn.connect("clicked", lambda b, i=idx: self._select_time_range(i))
            self.range_box.append(btn)
            self.range_btns.append(btn)
        ctrl_bar.append(self.range_box)

        # Main Scrolled Container
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        self.append(scrolled)

        clamp = Adw.Clamp()
        clamp.set_maximum_size(950)
        scrolled.set_child(clamp)

        main_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        main_vbox.set_margin_start(16)
        main_vbox.set_margin_end(16)
        main_vbox.set_margin_bottom(24)
        clamp.set_child(main_vbox)

        # Stats Cards Grid (Current, Avg, Min, Max)
        stats_grid = Gtk.Grid()
        stats_grid.set_column_spacing(12)
        stats_grid.set_row_spacing(12)
        stats_grid.set_column_homogeneous(True)
        main_vbox.append(stats_grid)

        self.card_curr = self._create_stat_card("Current", "--", stats_grid, 0)
        self.card_avg = self._create_stat_card("Average", "--", stats_grid, 1)
        self.card_min = self._create_stat_card("Minimum", "--", stats_grid, 2)
        self.card_max = self._create_stat_card("Maximum", "--", stats_grid, 3)

        # Chart Frame Header
        self.chart_header_lbl = Gtk.Label(label="Resource History")
        self.chart_header_lbl.add_css_class("title-3")
        self.chart_header_lbl.set_halign(Gtk.Align.START)
        self.chart_header_lbl.set_margin_top(8)
        main_vbox.append(self.chart_header_lbl)

        # Cairo Canvas Drawing Area
        self.chart_frame = Gtk.Frame()
        self.chart_frame.set_vexpand(True)
        self.chart_frame.set_size_request(-1, 320)
        main_vbox.append(self.chart_frame)

        self.drawing_area = Gtk.DrawingArea()
        self.drawing_area.set_draw_func(self._on_draw_chart)
        self.chart_frame.set_child(self.drawing_area)

    def _create_stat_card(self, title: str, val: str, grid: Gtk.Grid, col: int) -> Gtk.Label:
        frame = Gtk.Frame()
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_top(12)
        box.set_margin_bottom(12)

        lbl_title = Gtk.Label(label=title)
        lbl_title.add_css_class("dim-label")
        lbl_title.set_halign(Gtk.Align.START)
        box.append(lbl_title)

        lbl_val = Gtk.Label(label=val)
        lbl_val.add_css_class("title-2")
        lbl_val.add_css_class("bold")
        lbl_val.set_halign(Gtk.Align.START)
        box.append(lbl_val)

        frame.set_child(box)
        grid.attach(frame, col, 0, 1, 1)
        return lbl_val

    def set_ipc_client(self, client: GUIIPCClient):
        self.ipc_client = client

    def update_sample(self, status: Dict[str, Any]):
        # Convert status payload into time-series sample
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
            "psi_io": 0.0
        }
        self.history_buffer.append(sample)
        if len(self.history_buffer) > 3600:
            self.history_buffer = self.history_buffer[-3600:]

        self._update_stats_and_redraw()

    def set_metrics_history(self, history: List[Dict[str, Any]]):
        if history:
            self.history_buffer = history
            self._update_stats_and_redraw()

    def _select_time_range(self, idx: int):
        self.selected_time_range_idx = idx
        for i, btn in enumerate(self.range_btns):
            if i == idx:
                btn.add_css_class("suggested-action")
            else:
                btn.remove_css_class("suggested-action")
        self._update_stats_and_redraw()

    def _on_selection_changed(self, *args):
        self.selected_metric_idx = self.metric_dropdown.get_selected()
        self._update_stats_and_redraw()

    def _get_window_samples(self) -> List[Dict[str, Any]]:
        max_secs = TIME_RANGES[self.selected_time_range_idx][1]
        now = time.time()
        cutoff = now - max_secs
        return [s for s in self.history_buffer if s.get("timestamp", 0) >= cutoff]

    def _update_stats_and_redraw(self):
        samples = self._get_window_samples()
        metric_key = METRIC_OPTIONS[self.selected_metric_idx][1]
        unit = METRIC_OPTIONS[self.selected_metric_idx][2]
        title = METRIC_OPTIONS[self.selected_metric_idx][0]

        self.chart_header_lbl.set_text(f"{title} - Last {TIME_RANGES[self.selected_time_range_idx][0]}")

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
        # Draw background canvas
        cr.set_source_rgb(0.12, 0.12, 0.14)
        cr.rectangle(0, 0, width, height)
        cr.fill()

        samples = self._get_window_samples()
        if not samples:
            cr.set_source_rgb(0.5, 0.5, 0.5)
            cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
            cr.set_font_size(14)
            cr.move_to(width / 2 - 70, height / 2)
            cr.show_text("Waiting for Aegis metrics...")
            return

        margin_left = 50
        margin_right = 20
        margin_top = 20
        margin_bottom = 30

        chart_w = width - margin_left - margin_right
        chart_h = height - margin_top - margin_bottom

        # Grid lines
        cr.set_line_width(1)
        cr.set_source_rgba(0.25, 0.25, 0.28, 0.8)

        for i in range(5):
            y = margin_top + (chart_h / 4) * i
            cr.move_to(margin_left, y)
            cr.line_to(width - margin_right, y)
            cr.stroke()

        metric_info = METRIC_OPTIONS[self.selected_metric_idx]
        metric_key = metric_info[1]
        unit = metric_info[2]
        max_limit = metric_info[3]

        if metric_key == "network":
            all_v = [s.get("network_rx", 0.0) + s.get("network_tx", 0.0) for s in samples]
            max_limit = max(10.0, max(all_v) * 1.2) if all_v else 10.0

        # Y-Axis Labels
        cr.set_source_rgb(0.6, 0.6, 0.6)
        cr.set_font_size(10)
        for i in range(5):
            val = max_limit * (1.0 - (i / 4.0))
            y = margin_top + (chart_h / 4) * i
            cr.move_to(8, y + 4)
            cr.show_text(f"{val:.0f}{unit}")

        # X-Axis Time Labels
        time_range_str = TIME_RANGES[self.selected_time_range_idx][0]
        cr.move_to(margin_left, height - 10)
        cr.show_text(f"-{time_range_str}")
        cr.move_to(margin_left + chart_w / 2 - 10, height - 10)
        cr.show_text("Now-half")
        cr.move_to(width - margin_right - 25, height - 10)
        cr.show_text("Now")

        # Plot Data Curve
        if len(samples) < 2:
            return

        now = time.time()
        max_secs = TIME_RANGES[self.selected_time_range_idx][1]
        min_ts = now - max_secs

        def get_coords(ts: float, val: float):
            rel_x = max(0.0, min(1.0, (ts - min_ts) / max_secs))
            x = margin_left + rel_x * chart_w
            rel_y = max(0.0, min(1.0, val / max_limit))
            y = margin_top + (1.0 - rel_y) * chart_h
            return x, y

        if metric_key == "network":
            # Plot RX (Blue) and TX (Green)
            for key, (r, g, b) in [("network_rx", (0.2, 0.6, 1.0)), ("network_tx", (0.2, 0.8, 0.4))]:
                cr.set_source_rgb(r, g, b)
                cr.set_line_width(2.0)
                first = True
                for s in samples:
                    x, y = get_coords(s.get("timestamp", 0), s.get(key, 0.0))
                    if first:
                        cr.move_to(x, y)
                        first = False
                    else:
                        cr.line_to(x, y)
                cr.stroke()
        else:
            # Plot single metric curve (Accent Color)
            cr.set_source_rgb(0.2, 0.6, 0.95)
            cr.set_line_width(2.5)

            pts = []
            for s in samples:
                val = s.get(metric_key, 0.0)
                x, y = get_coords(s.get("timestamp", 0), val)
                pts.append((x, y))

            if pts:
                cr.move_to(pts[0][0], pts[0][1])
                for x, y in pts[1:]:
                    cr.line_to(x, y)
                cr.stroke()

                # Subtle Gradient Fill
                cr.line_to(pts[-1][0], margin_top + chart_h)
                cr.line_to(pts[0][0], margin_top + chart_h)
                cr.close_path()
                cr.set_source_rgba(0.2, 0.6, 0.95, 0.15)
                cr.fill()
