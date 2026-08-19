import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw
from typing import Callable, Dict, Any

class ProcessRow(Adw.ActionRow):
    def __init__(
        self,
        proc_data: Dict[str, Any],
        on_action: Callable[[str, Dict[str, Any]], None]
    ):
        super().__init__()
        self.proc_data = proc_data
        self.on_action = on_action

        pid = proc_data.get("pid", 0)
        name = proc_data.get("name", "unknown")
        cpu = proc_data.get("cpu", 0.0)
        rss = proc_data.get("rss", 0)
        runtime = proc_data.get("runtime", 0)
        score = proc_data.get("score", 0.0)
        protected = proc_data.get("protected", False)
        expendable = proc_data.get("expendable", False)

        # Format Memory
        if rss > 1024 * 1024 * 1024:
            mem_str = f"{rss / (1024**3):.1f} GB"
        else:
            mem_str = f"{rss // (1024*1024)} MB"

        # Format Runtime
        hours = runtime // 3600
        mins = (runtime % 3600) // 60
        secs = runtime % 60
        if hours > 0:
            rt_str = f"{hours}h {mins}m"
        elif mins > 0:
            rt_str = f"{mins}m {secs}s"
        else:
            rt_str = f"{secs}s"

        # Priority status check
        if protected:
            status = "PROTECTED"
        elif expendable:
            status = "EXPENDABLE"
        else:
            status = "NORMAL"

        self.set_title(name)
        self.set_subtitle(f"PID: {pid}  •  CPU: {cpu:.1f}%  •  RAM: {mem_str}  •  Runtime: {rt_str}  •  Score: {score:.2f}")

        # Status Tag Badge
        tag_label = Gtk.Label(label=status)
        tag_label.add_css_class("caption")
        tag_label.add_css_class("bold")
        tag_label.set_valign(Gtk.Align.CENTER)
        tag_label.set_margin_end(8)

        if status == "PROTECTED":
            tag_label.add_css_class("success")
        elif status == "EXPENDABLE":
            tag_label.add_css_class("warning")
        else:
            tag_label.add_css_class("dim-label")

        self.add_suffix(tag_label)

        # Action Buttons Box
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        btn_box.set_valign(Gtk.Align.CENTER)

        if status == "PROTECTED":
            btn_unprot = Gtk.Button(label="Unprotect")
            btn_unprot.add_css_class("flat")
            btn_unprot.connect("clicked", lambda b: self.on_action("unprotect", self.proc_data))
            btn_box.append(btn_unprot)

            btn_oom = Gtk.Button(label="OOM Protect")
            btn_oom.add_css_class("flat")
            btn_oom.connect("clicked", lambda b: self.on_action("oom_protect", self.proc_data))
            btn_box.append(btn_oom)

        elif status == "EXPENDABLE":
            btn_prot = Gtk.Button(label="Protect")
            btn_prot.add_css_class("flat")
            btn_prot.connect("clicked", lambda b: self.on_action("protect", self.proc_data))
            btn_box.append(btn_prot)

            btn_unexp = Gtk.Button(label="Remove Expendable")
            btn_unexp.add_css_class("flat")
            btn_unexp.connect("clicked", lambda b: self.on_action("unmark_expendable", self.proc_data))
            btn_box.append(btn_unexp)

        else:  # NORMAL
            btn_prot = Gtk.Button(label="Protect")
            btn_prot.add_css_class("flat")
            btn_prot.connect("clicked", lambda b: self.on_action("protect", self.proc_data))
            btn_box.append(btn_prot)

            btn_exp = Gtk.Button(label="Expendable")
            btn_exp.add_css_class("flat")
            btn_exp.connect("clicked", lambda b: self.on_action("mark_expendable", self.proc_data))
            btn_box.append(btn_exp)

        # Terminate Button (always available)
        btn_term = Gtk.Button(label="Terminate")
        btn_term.add_css_class("destructive-action")
        btn_term.connect("clicked", lambda b: self.on_action("terminate", self.proc_data))
        btn_box.append(btn_term)

        self.add_suffix(btn_box)
