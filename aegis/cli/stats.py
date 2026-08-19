import os
import sys
import time
import curses
from aegis.config import load_config
from aegis.utils.proc import total_ram_kb, read_all_proc_samples
from aegis.watchers.memory import MemoryWatcher
from aegis.watchers.cpu import CPUWatcher
from aegis.watchers.temp import TempWatcher

def run_stats(args=None):
    try:
        curses.wrapper(_draw_stats)
    except KeyboardInterrupt:
        pass

def _draw_stats(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.timeout(1000)

    cfg = load_config()
    total_kb = total_ram_kb()
    total_gb = total_kb / 1024 / 1024

    mw = MemoryWatcher(cfg)
    cw = CPUWatcher(cfg)
    tw = TempWatcher(cfg)

    while True:
        stdscr.clear()
        h, w = stdscr.getmaxyx()

        mem_snap = mw.snapshot()
        used_gb = mem_snap["used_bytes"] / 1024 / 1024 / 1024
        mem_pct = mem_snap["used_pct"]
        cpu_snap = cw.snapshot()
        cpu_pct = cpu_snap.get("busy_pct", 0.0)

        stdscr.addstr(0, 0, "=== Aegis Live System Dashboard (Ctrl+C or 'q' to Exit) ===")
        stdscr.addstr(2, 0, f"RAM: [{used_gb:.1f} GB / {total_gb:.1f} GB] {mem_pct:.1f}%")
        
        bar_len = min(40, w - 25)
        filled = int(bar_len * (mem_pct / 100.0))
        bar = "#" * filled + "-" * (bar_len - filled)
        stdscr.addstr(3, 0, f"     [{bar}]")

        stdscr.addstr(5, 0, f"CPU Usage: {cpu_pct:.1f}%")
        
        temps = tw.snapshot()
        t_str = ", ".join(f"{k}: {v:.1f}°C" for k, v in list(temps.items())[:4])
        stdscr.addstr(7, 0, f"Temperatures: {t_str if t_str else 'N/A'}")

        stdscr.addstr(9, 0, "Top Memory Consumers:")
        stdscr.addstr(10, 0, f"{'PID':<8} {'NAME':<20} {'RSS':<10}")
        stdscr.addstr(11, 0, "-" * 40)

        samples = read_all_proc_samples()
        proc_list = sorted(samples.values(), key=lambda s: s.rss, reverse=True)[:max(5, h - 14)]
        row = 12
        for p in proc_list:
            if row < h - 1:
                rss_mb = p.rss // 1024 // 1024
                stdscr.addstr(row, 0, f"{p.pid:<8} {p.name[:20]:<20} {rss_mb} MB")
                row += 1

        stdscr.refresh()
        ch = stdscr.getch()
        if ch == ord('q') or ch == 27:
            break
