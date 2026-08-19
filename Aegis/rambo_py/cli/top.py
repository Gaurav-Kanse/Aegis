import sys
from rambo_py.config import load_config
from rambo_py.utils.proc import total_ram_kb, read_all_proc_samples
from rambo_py.watchers.memory import MemoryWatcher
from rambo_py.watchers.cpu import CPUWatcher
from rambo_py.watchers.net import NetWatcher
from rambo_py.watchers.temp import TempWatcher
from rambo_py.watchers.pressure import PressureWatcher
from rambo_py.watchers.disk import DiskWatcher

def run_top(args=None):
    cfg = load_config()
    total_kb = total_ram_kb()
    total_gb = total_kb / 1024 / 1024

    mw = MemoryWatcher(cfg)
    mem_snap = mw.snapshot()
    used_gb = mem_snap["used_bytes"] / 1024 / 1024 / 1024
    mem_pct = mem_snap["used_pct"]

    cw = CPUWatcher(cfg)
    cpu_snap = cw.snapshot()
    cpu_pct = cpu_snap.get("busy_pct", 0.0)

    tw = TempWatcher(cfg)
    temps = tw.snapshot()

    pw = PressureWatcher(cfg)
    psi = pw.snapshot()

    dw = DiskWatcher(cfg)
    disks = dw.snapshot()

    print("┌─ RAM ───────────────────────────┐")
    print(f"│ {used_gb:.1f} GB / {total_gb:.1f} GB used ({mem_pct:.1f}%) │")
    print("└────────────────────────────────┘\n")

    print("┌─ CPU ─────────────────────────────────────────────────────┐")
    print(f"│ Overall: {cpu_pct:.1f}%                                           │")
    print("└──────────────────────────────────────────────────────────┘\n")

    print("┌─ Disk Space ────────────────────────────────────────────┐")
    for m, pct in disks.items():
        print(f"│ {m:<20} {pct:.1f}% used                                │")
    print("└────────────────────────────────────────────────────────┘\n")

    print("┌─ Temperature ───────┐")
    for sensor, val in temps.items():
        print(f"│ {sensor:<12} {val:.1f} C │")
    print("└────────────────────┘\n")

    print("┌─ Memory Pressure (PSI) ────────┐")
    print(f"│ some {psi.get('some_avg10', 0.0):.1f}%  full {psi.get('full_avg10', 0.0):.1f}% (avg10) │")
    print("└───────────────────────────────┘\n")

    print("┌─ Top RAM Consumers ───────────────────┐")
    print(f"│ {'PID':<8} {'NAME':<20} {'RAM':<8} │")
    
    samples = read_all_proc_samples()
    proc_list = sorted(samples.values(), key=lambda s: s.rss, reverse=True)[:10]
    for p in proc_list:
        rss_mb = p.rss // 1024 // 1024
        print(f"│ {p.pid:<8} {p.name[:20]:<20} {rss_mb} MB   │")
    print("└───────────────────────────────────────┘")
