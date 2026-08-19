import os
import glob
import subprocess
from typing import List, Set

def set_oom_score_adj(pid: int, score: int) -> bool:
    path = f"/proc/{pid}/oom_score_adj"
    try:
        if os.path.exists(path):
            with open(path, "w") as f:
                f.write(str(score))
            return True
    except Exception:
        pass
    return False

def mark_expendable_processes(expendable_names: List[str]) -> int:
    exp_set = set(expendable_names)
    marked = 0
    for stat_path in glob.glob("/proc/[0-9]*/stat"):
        try:
            pid = int(os.path.basename(os.path.dirname(stat_path)))
            with open(f"/proc/{pid}/comm", "r") as f:
                name = f.read().strip()
            if name in exp_set:
                if set_oom_score_adj(pid, 1000):
                    marked += 1
        except Exception:
            continue
    return marked

def run_oom_protect_helper():
    """Runs `pkexec rambo-py oom-protect` in background."""
    try:
        subprocess.Popen(
            ["pkexec", "rambo-py", "oom-protect"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    except Exception:
        pass
