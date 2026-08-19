import time
from typing import Dict, Any
from aegis.watchers.base import Watcher, Event, Severity
from aegis.utils.cgroup import CGroupManager
from aegis.utils.proc import total_ram_kb
from aegis.config import Config

class MemoryWatcher(Watcher):
    def __init__(self, config: Config):
        self.config = config
        self.cgroup_mgr = CGroupManager()
        self.total_kb = total_ram_kb()
        self.total_bytes = self.total_kb * 1024
        
        soft_bytes = int(self.total_bytes * (self.config.memory.soft_pct / 100.0))
        max_bytes = int(self.total_bytes * (self.config.memory.max_pct / 100.0))
        self.cgroup_mgr.apply_limits(soft_bytes, max_bytes)

    def name(self) -> str:
        return "memory"

    def snapshot(self) -> Dict[str, float]:
        mem_info = self._read_meminfo()
        used_kb = mem_info.get("MemTotal", 0) - mem_info.get("MemAvailable", 0)
        pct = (used_kb / mem_info["MemTotal"] * 100.0) if mem_info.get("MemTotal", 0) > 0 else 0.0
        return {
            "used_bytes": float(used_kb * 1024),
            "total_bytes": float(self.total_bytes),
            "used_pct": pct
        }

    def _read_meminfo(self) -> Dict[str, int]:
        res = {}
        try:
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    parts = line.split(":")
                    if len(parts) == 2:
                        k = parts[0].strip()
                        v = int(parts[1].split()[0])
                        res[k] = v
        except Exception:
            pass
        return res

    def run(self, emit_func):
        while True:
            try:
                snap = self.snapshot()
                pct = snap["used_pct"]
                
                if pct >= self.config.memory.max_pct:
                    ev = Event(
                        severity=Severity.EMERGENCY,
                        source="memory",
                        message=f"Memory usage emergency: {pct:.1f}% >= max limit {self.config.memory.max_pct:.1f}%",
                        values={"pct": pct}
                    )
                    emit_func(ev)
                elif pct >= self.config.memory.hard_pct:
                    ev = Event(
                        severity=Severity.CRITICAL,
                        source="memory",
                        message=f"Memory usage critical: {pct:.1f}% >= hard limit {self.config.memory.hard_pct:.1f}%",
                        values={"pct": pct}
                    )
                    emit_func(ev)
                elif pct >= self.config.memory.soft_pct:
                    ev = Event(
                        severity=Severity.WARNING,
                        source="memory",
                        message=f"Memory usage warning: {pct:.1f}% >= soft limit {self.config.memory.soft_pct:.1f}%",
                        values={"pct": pct}
                    )
                    emit_func(ev)
                
                time.sleep(1)
            except Exception:
                time.sleep(1)
