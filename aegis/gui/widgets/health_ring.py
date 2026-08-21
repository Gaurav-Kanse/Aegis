import math
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Pango', '1.0')
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
        radius = min(width, height) / 2.0 - 14.0
        total_dots = 40
        dot_size = 5.0

        # Draw Dot-Matrix Circular Ring
        active_dots = int((self.score / 100.0) * total_dots)

        for i in range(total_dots):
            # Start angle at top (-pi/2)
            angle = -math.pi / 2.0 + (2 * math.pi * (i / total_dots))
            dx = cx + radius * math.cos(angle)
            dy = cy + radius * math.sin(angle)

            if i <= active_dots:
                if self.state_text in ("CRITICAL", "EMERGENCY"):
                    cr.set_source_rgba(1.0, 0.23, 0.19, 1.0)  # Pixel Red
                elif self.state_text == "WARNING":
                    cr.set_source_rgba(0.98, 0.75, 0.14, 1.0)  # Pixel Amber
                else:
                    cr.set_source_rgba(1.0, 1.0, 1.0, 1.0)    # Pixel White
            else:
                cr.set_source_rgba(0.12, 0.12, 0.16, 1.0)     # Dim matrix dot

            # Render square pixel dot
            cr.rectangle(dx - dot_size / 2.0, dy - dot_size / 2.0, dot_size, dot_size)
            cr.fill()

        # Render Score Number (Monospace Pixel Text)
        cr.set_source_rgba(1.0, 1.0, 1.0, 1.0)
        
        layout = PangoCairo.create_layout(cr)
        layout.set_text(str(self.score), -1)
        font_desc = Pango.FontDescription("Monospace Bold 26")
        layout.set_font_description(font_desc)
        w, h = layout.get_pixel_size()
        cr.move_to(cx - w / 2.0, cy - h / 2.0 - 6)
        PangoCairo.show_layout(cr, layout)

        # Render State Text
        formatted_state = self.state_text
        sub_layout = PangoCairo.create_layout(cr)
        sub_layout.set_text(formatted_state, -1)
        sub_font = Pango.FontDescription("Monospace Bold 8")
        sub_layout.set_font_description(sub_font)
        sw, sh = sub_layout.get_pixel_size()
        
        if self.state_text in ("CRITICAL", "EMERGENCY"):
            cr.set_source_rgba(1.0, 0.23, 0.19, 1.0)
        elif self.state_text == "WARNING":
            cr.set_source_rgba(0.98, 0.75, 0.14, 1.0)
        else:
            cr.set_source_rgba(0.29, 0.87, 0.5, 1.0)

        cr.move_to(cx - sw / 2.0, cy + h / 2.0 - 2)
        PangoCairo.show_layout(cr, sub_layout)
