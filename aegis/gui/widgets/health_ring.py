import math
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('PangoCairo', '1.0')
from gi.repository import Gtk, Gdk, Pango, PangoCairo

class HealthRingGauge(Gtk.DrawingArea):
    def __init__(self, size: int = 160):
        super().__init__()
        self.set_content_width(size)
        self.set_content_height(size)
        self.score = 100
        self.state_text = "PROTECTED"
        self.set_draw_func(self._on_draw)

    def set_status(self, score: int, state_text: str):
        self.score = max(0, min(100, score))
        self.state_text = state_text.upper()
        self.queue_draw()

    def _on_draw(self, area, cr, width, height):
        cx = width / 2.0
        cy = height / 2.0
        radius = min(width, height) / 2.0 - 12.0
        line_width = 8.0

        # Background Ring Arc
        cr.set_line_width(line_width)
        cr.set_source_rgba(1.0, 1.0, 1.0, 0.08)
        cr.arc(cx, cy, radius, 0, 2 * math.pi)
        cr.stroke()

        # Score Arc Progress
        start_angle = -math.pi / 2.0
        end_angle = start_angle + (2 * math.pi * (self.score / 100.0))

        # Color based on state
        if self.state_text in ("CRITICAL", "EMERGENCY"):
            cr.set_source_rgba(0.97, 0.44, 0.44, 1.0)  # Subtle red
        elif self.state_text == "WARNING":
            cr.set_source_rgba(0.98, 0.75, 0.14, 1.0)  # Subtle amber
        else:
            cr.set_source_rgba(0.95, 0.95, 0.96, 0.95)  # Monochrome white

        cr.set_line_width(line_width)
        cr.arc(cx, cy, radius, start_angle, end_angle)
        cr.stroke()

        # Render Score Number (e.g. 87)
        cr.set_source_rgba(1.0, 1.0, 1.0, 1.0)
        
        layout = PangoCairo.create_layout(cr)
        layout.set_text(str(self.score), -1)
        font_desc = Pango.FontDescription("Sans Bold 26")
        layout.set_font_description(font_desc)
        w, h = layout.get_pixel_size()
        cr.move_to(cx - w / 2.0, cy - h / 2.0 - 6)
        PangoCairo.show_layout(cr, layout)

        # Render State Text (e.g. PROTECTED)
        sub_layout = PangoCairo.create_layout(cr)
        sub_layout.set_text(self.state_text, -1)
        sub_font = Pango.FontDescription("Sans Bold 9")
        sub_layout.set_font_description(sub_font)
        sw, sh = sub_layout.get_pixel_size()
        
        if self.state_text in ("CRITICAL", "EMERGENCY"):
            cr.set_source_rgba(0.97, 0.44, 0.44, 1.0)
        elif self.state_text == "WARNING":
            cr.set_source_rgba(0.98, 0.75, 0.14, 1.0)
        else:
            cr.set_source_rgba(0.29, 0.87, 0.5, 1.0)  # Green protected

        cr.move_to(cx - sw / 2.0, cy + h / 2.0 - 2)
        PangoCairo.show_layout(cr, sub_layout)
