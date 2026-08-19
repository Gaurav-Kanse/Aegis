import os
import time
from typing import Dict
from aegis.watchers.base import Watcher, Event, Severity
from aegis.config import Config

class DiskWatcher(Watcher):
    def __init__(self, config: Config):
        self.config = config

    def name(self) -> str:
        return "disk"

    def snapshot(self) -> Dict[str, float]:
        res = {}
        for mount in ["/", "/home"]:
            if os.path.exists(mount):
                try:
                    st = os.statvfs(mount)
                    total = st.f_blocks * st.f_frsize
                    free = st.f_bavail * st.f_frsize
                    used = total - free
                    pct = (used / total * 100.0) if total > 0 else 0.0
                    res[mount] = pct
                except Exception:
                    pass
        return res

    def run(self, emit_func):
        while True:
            try:
                snap = self.snapshot()
                for mount, pct in snap.items():
                    if pct >= self.config.disk.space_alert_pct:
                        emit_func(Event(
                            severity=Severity.WARNING,
                            source="disk",
                            message=f"Disk space low on {mount}: {pct:.1f}% >= {self.config.disk.space_alert_pct:.1f}%",
                            values={"mount": mount, "pct": pct}
                        ))
                time.sleep(10)
            except Exception:
                time.sleep(10)
