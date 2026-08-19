import os
import glob
import time
from typing import Dict
from aegis.watchers.base import Watcher, Event, Severity
from aegis.config import Config

class TempWatcher(Watcher):
    def __init__(self, config: Config):
        self.config = config

    def name(self) -> str:
        return "temperature"

    def read_temperatures(self) -> Dict[str, float]:
        temps = {}
        for hwmon_dir in glob.glob("/sys/class/hwmon/hwmon*"):
            name = "unknown"
            name_file = os.path.join(hwmon_dir, "name")
            if os.path.exists(name_file):
                try:
                    with open(name_file, "r") as f:
                        name = f.read().strip()
                except Exception:
                    pass

            for temp_input in glob.glob(os.path.join(hwmon_dir, "temp*_input")):
                try:
                    label = name
                    label_file = temp_input.replace("_input", "_label")
                    if os.path.exists(label_file):
                        with open(label_file, "r") as f:
                            label = f"{name}_{f.read().strip()}"

                    with open(temp_input, "r") as f:
                        val = float(f.read().strip()) / 1000.0
                        if val > 0 and val < 150:
                            temps[label] = max(temps.get(label, 0.0), val)
                except Exception:
                    continue
        return temps

    def snapshot(self) -> Dict[str, float]:
        return self.read_temperatures()

    def run(self, emit_func):
        while True:
            try:
                temps = self.read_temperatures()
                max_temp = max(temps.values()) if temps else 0.0
                
                if max_temp >= self.config.temperature.critical:
                    emit_func(Event(
                        severity=Severity.CRITICAL,
                        source="temperature",
                        message=f"Critical temperature detected: {max_temp:.1f}°C >= {self.config.temperature.critical:.1f}°C",
                        values={"max_temp": max_temp}
                    ))
                elif max_temp >= self.config.temperature.warning:
                    emit_func(Event(
                        severity=Severity.WARNING,
                        source="temperature",
                        message=f"High temperature warning: {max_temp:.1f}°C >= {self.config.temperature.warning:.1f}°C",
                        values={"max_temp": max_temp}
                    ))
                
                time.sleep(2)
            except Exception:
                time.sleep(2)
