import time
from typing import Dict, Tuple, List
from rambo_py.watchers.base import Watcher, Event, Severity
from rambo_py.config import Config

class CPUWatcher(Watcher):
    def __init__(self, config: Config):
        self.config = config
        self.last_stat: Tuple[int, int] = (0, 0)

    def name(self) -> str:
        return "cpu"

    def read_cpu_raw(self) -> Tuple[int, int, List[Tuple[int, int]]]:
        """Returns (overall_idle, overall_total, per_core_list)."""
        overall_idle = 0
        overall_total = 0
        per_core = []
        try:
            with open("/proc/stat", "r") as f:
                for line in f:
                    if line.startswith("cpu "):
                        fields = list(map(int, line.split()[1:]))
                        idle = fields[3] + fields[4]
                        total = sum(fields)
                        overall_idle = idle
                        overall_total = total
                    elif line.startswith("cpu") and line[3].isdigit():
                        fields = list(map(int, line.split()[1:]))
                        idle = fields[3] + fields[4]
                        total = sum(fields)
                        per_core.append((idle, total))
        except Exception:
            pass
        return overall_idle, overall_total, per_core

    def snapshot(self) -> Dict[str, float]:
        i1, t1, _ = self.read_cpu_raw()
        time.sleep(0.2)
        i2, t2, _ = self.read_cpu_raw()
        dt = t2 - t1
        di = i2 - i1
        pct = (1.0 - di / dt) * 100.0 if dt > 0 else 0.0
        return {"busy_pct": pct}

    def run(self, emit_func):
        i1, t1, _ = self.read_cpu_raw()
        while True:
            try:
                time.sleep(2)
                i2, t2, _ = self.read_cpu_raw()
                dt = t2 - t1
                di = i2 - i1
                pct = (1.0 - di / dt) * 100.0 if dt > 0 else 0.0
                i1, t1 = i2, t2

                if pct >= self.config.cpu.alert_pct:
                    emit_func(Event(
                        severity=Severity.WARNING,
                        source="cpu",
                        message=f"CPU usage sustained above alert limit: {pct:.1f}% >= {self.config.cpu.alert_pct:.1f}%",
                        values={"busy_pct": pct}
                    ))
            except Exception:
                time.sleep(2)
