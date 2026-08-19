import os
import glob
import time
from typing import Dict, List, Optional, Tuple

HZ = 100

class ProcessSample:
    def __init__(self, pid: int, name: str, tty: int, start: int, utime: int, stime: int, rss: int = 0):
        self.pid = pid
        self.name = name
        self.tty = tty
        self.start = start
        self.utime = utime
        self.stime = stime
        self.rss = rss  # in bytes

def uptime_sec() -> float:
    try:
        with open("/proc/uptime", "r") as f:
            parts = f.read().split()
            return float(parts[0]) if parts else 0.0
    except Exception:
        return 0.0

def total_ram_kb() -> int:
    try:
        with open("/proc/meminfo", "r") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    parts = line.split()
                    return int(parts[1])
    except Exception:
        pass
    return 16 * 1024 * 1024  # default fallback 16GB in KB

def read_rss_bytes(pid: int) -> int:
    try:
        with open(f"/proc/{pid}/status", "r") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    parts = line.split()
                    return int(parts[1]) * 1024  # convert KB to bytes
    except Exception:
        pass
    return 0

def parse_stat(pid: int) -> Optional[ProcessSample]:
    try:
        with open(f"/proc/{pid}/stat", "r") as f:
            content = f.read()
        open_idx = content.find("(")
        close_idx = content.rfind(")")
        if open_idx < 0 or close_idx < 0 or close_idx + 1 >= len(content):
            return None
        
        name = content[open_idx + 1:close_idx]
        rest = content[close_idx + 1:].split()
        if len(rest) < 20:
            return None
        
        tty = int(rest[4])
        utime = int(rest[11])
        stime = int(rest[12])
        start = int(rest[19])
        
        return ProcessSample(pid=pid, name=name, tty=tty, start=start, utime=utime, stime=stime)
    except Exception:
        return None

def read_all_proc_samples() -> Dict[int, ProcessSample]:
    samples = {}
    for stat_path in glob.glob("/proc/[0-9]*/stat"):
        try:
            pid = int(os.path.basename(os.path.dirname(stat_path)))
            sample = parse_stat(pid)
            if sample:
                sample.rss = read_rss_bytes(pid)
                samples[pid] = sample
        except Exception:
            continue
    return samples
