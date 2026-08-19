import os
import time
from dataclasses import dataclass
from typing import List, Dict, Set
from aegis.utils.proc import read_all_proc_samples, uptime_sec, total_ram_kb, ProcessSample
from aegis.config import KillWeights

INTERNAL_BLACKLIST = {
    "systemd", "kwin_wayland", "plasmashell", "Xorg", "sddm", "gdm", "lightdm",
    "pipewire", "wireplumber", "pulseaudio", "dbus-daemon", "aegis", "rambo",
    "init", "kthreadd"
}

@dataclass
class Candidate:
    pid: int
    name: str
    rss: int          # in bytes
    cpu: float        # percentage [0..100]
    elapsed_sec: int
    interactive: bool
    score: float = 0.0

def collect_candidates(exclude: Set[str]) -> List[Candidate]:
    first = read_all_proc_samples()
    time.sleep(0.5)
    second = read_all_proc_samples()
    
    uptime = uptime_sec()
    now_hz = int(uptime * 100)
    
    combined_exclude = INTERNAL_BLACKLIST.union(exclude)
    candidates = []
    
    for pid, s in second.items():
        if pid not in first:
            continue
        if s.name in combined_exclude:
            continue
        
        f = first[pid]
        dt = (s.utime + s.stime) - (f.utime + f.stime)
        if dt < 0:
            dt = 0
        cpu = (dt / 50.0) * 100.0
        if cpu > 100.0:
            cpu = 100.0
        
        elapsed = 0
        if now_hz > s.start:
            elapsed = (now_hz - s.start) // 100
        
        candidates.append(Candidate(
            pid=pid,
            name=s.name,
            rss=s.rss,
            cpu=cpu,
            elapsed_sec=elapsed,
            interactive=(s.tty != 0)
        ))
    return candidates

def compute_score(c: Candidate, weights: KillWeights, total_ram_bytes: int, expendable: bool) -> float:
    rss_norm = min(1.0, max(0.0, c.rss / total_ram_bytes)) if total_ram_bytes > 0 else 0.0
    cpu_norm = min(1.0, max(0.0, c.cpu / 100.0))
    rt_norm = min(1.0, max(0.0, 1.0 - (c.elapsed_sec / (3600 * 4))))
    
    score = (weights.rss * rss_norm) + (weights.cpu * cpu_norm) + (weights.runtime * rt_norm)
    if c.interactive:
        score += 0.3
    if expendable:
        score += 0.2
    return score

def rank_candidates(candidates: List[Candidate], weights: KillWeights, total_ram_bytes: int, expendable_set: Set[str]) -> List[Candidate]:
    for c in candidates:
        is_exp = (c.name in expendable_set)
        c.score = compute_score(c, weights, total_ram_bytes, is_exp)
    
    candidates.sort(key=lambda x: x.score, reverse=True)
    return candidates
