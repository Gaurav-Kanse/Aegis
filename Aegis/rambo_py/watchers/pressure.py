import os
import time
from typing import Dict
from rambo_py.watchers.base import Watcher, Event, Severity
from rambo_py.config import Config

class PressureWatcher(Watcher):
    def __init__(self, config: Config):
        self.config = config

    def name(self) -> str:
        return "pressure"

    def read_psi(self) -> Dict[str, float]:
        res = {"some_avg10": 0.0, "full_avg10": 0.0}
        psi_file = "/proc/pressure/memory"
        if not os.path.exists(psi_file):
            return res
        try:
            with open(psi_file, "r") as f:
                for line in f:
                    parts = line.split()
                    if len(parts) >= 2:
                        kind = parts[0]
                        for kv in parts[1:]:
                            if kv.startswith("avg10="):
                                val = float(kv.split("=")[1])
                                if kind == "some":
                                    res["some_avg10"] = val
                                elif kind == "full":
                                    res["full_avg10"] = val
        except Exception:
            pass
        return res

    def snapshot(self) -> Dict[str, float]:
        return self.read_psi()

    def run(self, emit_func):
        while True:
            try:
                psi = self.read_psi()
                if psi["full_avg10"] >= self.config.memory.hard_pct / 2.0:
                    emit_func(Event(
                        severity=Severity.CRITICAL,
                        source="pressure",
                        message=f"Critical memory pressure: full avg10 = {psi['full_avg10']:.1f}%",
                        values=psi
                    ))
                elif psi["some_avg10"] >= 40.0:
                    emit_func(Event(
                        severity=Severity.WARNING,
                        source="pressure",
                        message=f"High memory pressure warning: some avg10 = {psi['some_avg10']:.1f}%",
                        values=psi
                    ))
                time.sleep(2)
            except Exception:
                time.sleep(2)
