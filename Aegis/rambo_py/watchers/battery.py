import os
import glob
import time
from typing import Dict
from rambo_py.watchers.base import Watcher, Event, Severity
from rambo_py.config import Config

class BatteryWatcher(Watcher):
    def __init__(self, config: Config, sysfs_path: str = "/sys/class/power_supply"):
        self.config = config
        self.sysfs_path = sysfs_path
        self.battery_dirs = glob.glob(os.path.join(self.sysfs_path, "BAT*"))

    def enabled(self) -> bool:
        return len(self.battery_dirs) > 0

    def name(self) -> str:
        return "battery"

    def read_battery(self) -> Dict[str, float]:
        res = {"capacity": 100.0, "discharging": 0.0}
        for bdir in self.battery_dirs:
            cap_file = os.path.join(bdir, "capacity")
            status_file = os.path.join(bdir, "status")
            try:
                if os.path.exists(cap_file):
                    with open(cap_file, "r") as f:
                        res["capacity"] = float(f.read().strip())
                if os.path.exists(status_file):
                    with open(status_file, "r") as f:
                        status = f.read().strip()
                        res["discharging"] = 1.0 if status == "Discharging" else 0.0
            except Exception:
                pass
        return res

    def snapshot(self) -> Dict[str, float]:
        return self.read_battery()

    def run(self, emit_func):
        if not self.enabled():
            return
        while True:
            try:
                bat = self.read_battery()
                if bat["discharging"] and bat["capacity"] <= self.config.battery.low_pct:
                    emit_func(Event(
                        severity=Severity.WARNING,
                        source="battery",
                        message=f"Battery low ({bat['capacity']:.0f}%): action={self.config.battery.action}",
                        values=bat
                    ))
                time.sleep(15)
            except Exception:
                time.sleep(15)
