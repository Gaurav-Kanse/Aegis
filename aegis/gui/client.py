import threading
import time
from typing import Callable, Optional, Dict, Any
from gi.repository import GLib

from aegis.ipc import IPCClient, IPCError

class GUIIPCClient:
    def __init__(self, poll_interval: float = 1.0):
        self.client = IPCClient(timeout=3.0)
        self.poll_interval = poll_interval
        self.running = False
        self.poll_thread: Optional[threading.Thread] = None

        self.on_status_updated: Optional[Callable[[Dict[str, Any]], None]] = None
        self.on_offline_state: Optional[Callable[[], None]] = None
        self.is_connected = False

    def start_polling(self, on_status_updated: Callable[[Dict[str, Any]], None], on_offline_state: Callable[[], None]):
        self.on_status_updated = on_status_updated
        self.on_offline_state = on_offline_state
        self.running = True

        if not self.poll_thread or not self.poll_thread.is_alive():
            self.poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
            self.poll_thread.start()

    def stop_polling(self):
        self.running = False

    def _poll_loop(self):
        while self.running:
            try:
                status = self.client.get_status()
                self.is_connected = True
                if self.on_status_updated:
                    GLib.idle_add(self.on_status_updated, status)
            except IPCError:
                self.is_connected = False
                if self.on_offline_state:
                    GLib.idle_add(self.on_offline_state)
            except Exception as e:
                self.is_connected = False
                if self.on_offline_state:
                    GLib.idle_add(self.on_offline_state)

            time.sleep(self.poll_interval)

    def fetch_status_async(self, callback: Callable[[Optional[Dict[str, Any]], Optional[Exception]], None]):
        def worker():
            try:
                res = self.client.get_status()
                GLib.idle_add(callback, res, None)
            except Exception as ex:
                GLib.idle_add(callback, None, ex)

        threading.Thread(target=worker, daemon=True).start()

    def fetch_processes_async(self, callback: Callable[[Optional[Any], Optional[Exception]], None]):
        def worker():
            try:
                res = self.client.get_processes()
                GLib.idle_add(callback, res, None)
            except Exception as ex:
                GLib.idle_add(callback, None, ex)

        threading.Thread(target=worker, daemon=True).start()

    def protect_process_async(self, name: str, callback: Callable[[Optional[Any], Optional[Exception]], None]):
        def worker():
            try:
                res = self.client.protect_process(name)
                GLib.idle_add(callback, res, None)
            except Exception as ex:
                GLib.idle_add(callback, None, ex)

        threading.Thread(target=worker, daemon=True).start()

    def unprotect_process_async(self, name: str, callback: Callable[[Optional[Any], Optional[Exception]], None]):
        def worker():
            try:
                res = self.client.unprotect_process(name)
                GLib.idle_add(callback, res, None)
            except Exception as ex:
                GLib.idle_add(callback, None, ex)

        threading.Thread(target=worker, daemon=True).start()

    def mark_expendable_async(self, name: str, callback: Callable[[Optional[Any], Optional[Exception]], None], force: bool = False):
        def worker():
            try:
                res = self.client.mark_expendable(name, force=force)
                GLib.idle_add(callback, res, None)
            except Exception as ex:
                GLib.idle_add(callback, None, ex)

        threading.Thread(target=worker, daemon=True).start()

    def unmark_expendable_async(self, name: str, callback: Callable[[Optional[Any], Optional[Exception]], None]):
        def worker():
            try:
                res = self.client.unmark_expendable(name)
                GLib.idle_add(callback, res, None)
            except Exception as ex:
                GLib.idle_add(callback, None, ex)

        threading.Thread(target=worker, daemon=True).start()

    def oom_protect_process_async(self, pid: int, callback: Callable[[Optional[Any], Optional[Exception]], None]):
        def worker():
            try:
                res = self.client.oom_protect_process(pid=pid)
                GLib.idle_add(callback, res, None)
            except Exception as ex:
                GLib.idle_add(callback, None, ex)

        threading.Thread(target=worker, daemon=True).start()

    def terminate_process_async(self, pid: int, callback: Callable[[Optional[Any], Optional[Exception]], None]):
        def worker():
            try:
                res = self.client.terminate_process(pid)
                GLib.idle_add(callback, res, None)
            except Exception as ex:
                GLib.idle_add(callback, None, ex)

        threading.Thread(target=worker, daemon=True).start()

    def fetch_events_async(self, limit: int = 100, callback: Callable[[Optional[Any], Optional[Exception]], None] = None):
        def worker():
            try:
                res = self.client.get_events(limit=limit)
                if callback:
                    GLib.idle_add(callback, res, None)
            except Exception as ex:
                if callback:
                    GLib.idle_add(callback, None, ex)

        threading.Thread(target=worker, daemon=True).start()

    def fetch_metrics_history_async(self, limit: int = 300, callback: Callable[[Optional[Any], Optional[Exception]], None] = None):
        def worker():
            try:
                res = self.client.get_metrics_history(limit=limit)
                if callback:
                    GLib.idle_add(callback, res, None)
            except Exception as ex:
                if callback:
                    GLib.idle_add(callback, None, ex)

        threading.Thread(target=worker, daemon=True).start()

    def fetch_protection_async(self, callback: Callable[[Optional[Any], Optional[Exception]], None]):
        def worker():
            try:
                res = self.client.get_protection()
                GLib.idle_add(callback, res, None)
            except Exception as ex:
                GLib.idle_add(callback, None, ex)

        threading.Thread(target=worker, daemon=True).start()
