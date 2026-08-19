import os
import glob
from rambo_py.config import load_config
from rambo_py.score import INTERNAL_BLACKLIST
from rambo_py.oom import set_oom_score_adj

def run_oom_protect(args=None):
    if os.geteuid() != 0:
        print("[rambo-py] oom-protect: warning: requires root privileges to set oom_score_adj=-1000")
    
    cfg = load_config()
    protected_names = INTERNAL_BLACKLIST.union(set(cfg.protect)).union({"rambo-py", "python3"})
    
    protected_count = 0
    for stat_path in glob.glob("/proc/[0-9]*/stat"):
        try:
            pid = int(os.path.basename(os.path.dirname(stat_path)))
            comm_file = f"/proc/{pid}/comm"
            if os.path.exists(comm_file):
                with open(comm_file, "r") as f:
                    name = f.read().strip()
                if name in protected_names:
                    if set_oom_score_adj(pid, -1000):
                        protected_count += 1
        except Exception:
            continue
    
    print(f"[rambo-py] oom-protect: protected {protected_count} processes with oom_score_adj=-1000")
