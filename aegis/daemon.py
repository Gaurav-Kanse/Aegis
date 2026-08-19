import os
import sys
import time
import signal
import queue
import threading
from typing import List
from aegis.config import load_config
from aegis.state import record_event
from aegis.notify import send_notification
from aegis.utils.proc import total_ram_kb
from aegis.score import collect_candidates, rank_candidates
from aegis.oom import mark_expendable_processes, run_oom_protect_helper, set_oom_score_adj
from aegis.watchers.base import Event, Severity
from aegis.watchers.memory import MemoryWatcher
from aegis.watchers.temp import TempWatcher
from aegis.watchers.pressure import PressureWatcher
from aegis.watchers.cpu import CPUWatcher
from aegis.watchers.disk import DiskWatcher
from aegis.watchers.net import NetWatcher
from aegis.watchers.battery import BatteryWatcher

from aegis.ipc import IPCServer

class Daemon:
    def __init__(self):
        self.cfg = load_config()
        self.event_queue = queue.Queue(maxsize=256)
        self.stop_event = threading.Event()
        self.total_ram_bytes = total_ram_kb() * 1024
        self.last_kill_time = 0.0
        self.ipc_server = IPCServer(self)

    def run(self):
        print(f"[aegis] Daemon starting — soft {self.cfg.memory.soft_pct:.0f}% | hard {self.cfg.memory.hard_pct:.0f}% | max {self.cfg.memory.max_pct:.0f}%")
        
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

        # Start IPC Server
        self.ipc_server.start()

        if self.cfg.kill.oom_prefer:
            n = mark_expendable_processes(self.cfg.expendable)
            if n > 0:
                print(f"[aegis] Marked {n} expendable processes as OOM-preferred")

        if self.cfg.kill.oom_protect:
            run_oom_protect_helper()

        watchers = [
            MemoryWatcher(self.cfg),
            TempWatcher(self.cfg),
            PressureWatcher(self.cfg),
            CPUWatcher(self.cfg),
            DiskWatcher(self.cfg),
            NetWatcher(self.cfg),
        ]
        bat = BatteryWatcher(self.cfg)
        if bat.enabled():
            watchers.append(bat)

        for w in watchers:
            t = threading.Thread(target=w.run, args=(self._emit_event,), daemon=True)
            t.start()

        handler_t = threading.Thread(target=self._process_events, daemon=True)
        handler_t.start()

        print("[aegis] Daemon running. Press Ctrl+C to stop.")
        while not self.stop_event.is_set():
            time.sleep(1)

        # Stop IPC server & restore cgroup limits
        self.ipc_server.stop()

        for w in watchers:
            if hasattr(w, "cgroup_mgr"):
                w.cgroup_mgr.restore_limits()
        print("[aegis] Daemon stopped cleanly.")

    def _handle_signal(self, signum, frame):
        self.stop_event.set()

    def _emit_event(self, event: Event):
        try:
            self.event_queue.put_nowait(event)
        except queue.Full:
            pass

    def _process_events(self):
        while not self.stop_event.is_set():
            try:
                ev: Event = self.event_queue.get(timeout=1.0)
                record_event(ev.source, ev.severity.value, ev.message, ev.values)
                
                if ev.severity in (Severity.CRITICAL, Severity.EMERGENCY) and ev.source in ("memory", "temperature", "pressure"):
                    self._act_kill(ev)
                else:
                    send_notification(f"Aegis Alert ({ev.source.upper()})", ev.message, urgency="normal" if ev.severity == Severity.WARNING else "low")
            except queue.Empty:
                continue

    def _act_kill(self, ev: Event):
        now = time.time()
        cooldown_sec = 30.0
        if now - self.last_kill_time < cooldown_sec:
            send_notification("Aegis Action", f"Kill throttled (cooldown active): {ev.message}", urgency="high")
            return

        cands = collect_candidates(set(self.cfg.protect))
        if not cands:
            send_notification("Aegis Action", "No kill candidate found", urgency="high")
            return

        ranked = rank_candidates(cands, self.cfg.kill.weights, self.total_ram_bytes, set(self.cfg.expendable))
        victim = ranked[0]

        set_oom_score_adj(victim.pid, 1000)

        try:
            os.kill(victim.pid, signal.SIGTERM)
            msg = f"Sent SIGTERM to {victim.name} (PID {victim.pid}, RSS {victim.rss // 1024 // 1024}MB, score {victim.score:.2f}) - {ev.message}"
            print(f"[aegis] KILL: {msg}")
            send_notification("Aegis Action", msg, urgency="critical")
            record_event("kill", "critical", msg, {"pid": victim.pid, "rss": victim.rss, "score": victim.score})
            self.last_kill_time = now
        except Exception as e:
            print(f"[aegis] Failed to kill {victim.name} (PID {victim.pid}): {e}")
