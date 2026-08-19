import os
import sys
import json
import socket
import select
import signal
import threading
import time
from typing import Dict, Any, List, Optional

from aegis.config import load_config, save_config, Config
from aegis.state import record_event, load_history
from aegis.notify import send_notification
from aegis.utils.proc import total_ram_kb, read_all_proc_samples, uptime_sec
from aegis.score import collect_candidates, rank_candidates, compute_score, INTERNAL_BLACKLIST
from aegis.watchers.memory import MemoryWatcher
from aegis.watchers.cpu import CPUWatcher
from aegis.watchers.temp import TempWatcher
from aegis.watchers.pressure import PressureWatcher
from aegis.watchers.disk import DiskWatcher
from aegis.watchers.net import NetWatcher
from aegis.watchers.battery import BatteryWatcher

IPC_DIR = os.path.expanduser("~/.local/state/aegis")
SOCKET_PATH = os.path.join(IPC_DIR, "ipc.sock")


class IPCError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class IPCServer:
    def __init__(self, daemon_instance=None):
        self.daemon = daemon_instance
        self.socket_path = SOCKET_PATH
        self.server_sock: Optional[socket.socket] = None
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.metrics_history: List[Dict[str, Any]] = []

    def start(self):
        os.makedirs(IPC_DIR, mode=0o700, exist_ok=True)

        # Cleanup stale socket if present
        if os.path.exists(self.socket_path):
            try:
                # Test connection to check if active server is listening
                test_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                test_sock.settimeout(0.5)
                test_sock.connect(self.socket_path)
                test_sock.close()
                print(f"[aegis-ipc] Warning: Active IPC server running on {self.socket_path}")
            except (ConnectionRefusedError, FileNotFoundError, OSError):
                pass
            
            try:
                os.unlink(self.socket_path)
            except OSError:
                pass

        self.server_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.server_sock.bind(self.socket_path)
        os.chmod(self.socket_path, 0o600)
        self.server_sock.listen(10)
        self.server_sock.settimeout(1.0)

        self.running = True
        self.thread = threading.Thread(target=self._server_loop, daemon=True)
        self.thread.start()
        print(f"[aegis-ipc] Server listening on {self.socket_path}")

    def stop(self):
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
        if self.server_sock:
            try:
                self.server_sock.close()
            except OSError:
                pass
        if os.path.exists(self.socket_path):
            try:
                os.unlink(self.socket_path)
            except OSError:
                pass
        print("[aegis-ipc] Server stopped and socket cleaned up.")

    def _server_loop(self):
        while self.running:
            try:
                client_sock, _ = self.server_sock.accept()
                t = threading.Thread(target=self._handle_client, args=(client_sock,), daemon=True)
                t.start()
            except socket.timeout:
                continue
            except OSError:
                break
            except Exception as e:
                print(f"[aegis-ipc] Server accept error: {e}")
                time.sleep(0.5)

    def _handle_client(self, client_sock: socket.socket):
        client_sock.settimeout(5.0)
        rfile = client_sock.makefile("r", encoding="utf-8")
        wfile = client_sock.makefile("w", encoding="utf-8")

        try:
            for line in rfile:
                line = line.strip()
                if not line:
                    continue

                response = self._process_request(line)
                wfile.write(json.dumps(response) + "\n")
                wfile.flush()
        except (ConnectionResetError, BrokenPipeError, socket.timeout):
            pass
        except Exception as e:
            print(f"[aegis-ipc] Client handler exception: {e}")
        finally:
            try:
                rfile.close()
                wfile.close()
                client_sock.close()
            except Exception:
                pass

    def _process_request(self, raw_line: str) -> Dict[str, Any]:
        req_id = None
        try:
            req = json.loads(raw_line)
        except Exception:
            return {
                "id": None,
                "ok": False,
                "error": {"code": "PARSE_ERROR", "message": "Malformed JSON request"}
            }

        if not isinstance(req, dict):
            return {
                "id": None,
                "ok": False,
                "error": {"code": "INVALID_REQUEST", "message": "Request must be a JSON object"}
            }

        req_id = req.get("id")
        method = req.get("method")
        params = req.get("params", {})

        if not isinstance(method, str):
            return {
                "id": req_id,
                "ok": False,
                "error": {"code": "INVALID_REQUEST", "message": "Method must be a string"}
            }

        if not isinstance(params, dict):
            return {
                "id": req_id,
                "ok": False,
                "error": {"code": "INVALID_PARAMS", "message": "Params must be an object"}
            }

        handler = getattr(self, f"_rpc_{method}", None)
        if not handler:
            return {
                "id": req_id,
                "ok": False,
                "error": {"code": "METHOD_NOT_FOUND", "message": f"Unknown method: '{method}'"}
            }

        try:
            res = handler(params)
            return {"id": req_id, "ok": True, "result": res}
        except IPCError as ie:
            return {
                "id": req_id,
                "ok": False,
                "error": {"code": ie.code, "message": ie.message}
            }
        except Exception as ex:
            return {
                "id": req_id,
                "ok": False,
                "error": {"code": "INTERNAL_ERROR", "message": str(ex)}
            }

    # ------------------ RPC Handlers ------------------

    def _rpc_get_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        cfg = self.daemon.cfg if self.daemon else load_config()

        mw = MemoryWatcher(cfg)
        mem_snap = mw.snapshot()
        total_gb = mem_snap["total_bytes"] / 1024 / 1024 / 1024
        used_gb = mem_snap["used_bytes"] / 1024 / 1024 / 1024
        mem_pct = mem_snap["used_pct"]

        cw = CPUWatcher(cfg)
        cpu_snap = cw.snapshot()
        cpu_pct = cpu_snap.get("busy_pct", 0.0)

        tw = TempWatcher(cfg)
        temps = tw.snapshot()
        max_temp = max(temps.values()) if temps else 0.0

        pw = PressureWatcher(cfg)
        psi = pw.snapshot()

        dw = DiskWatcher(cfg)
        disks = dw.snapshot()

        nw = NetWatcher(cfg)
        nets = nw.snapshot()

        bw = BatteryWatcher(cfg)
        bats = bw.snapshot() if bw.enabled() else {}

        # Calculate health score (100 is best, lower is high pressure/temp)
        health = 100
        health -= int(min(40.0, mem_pct * 0.4))
        health -= int(min(30.0, cpu_pct * 0.3))
        if max_temp > 70:
            health -= int(min(20.0, (max_temp - 70) * 1.0))
        health = max(0, min(100, health))

        # Determine state
        state = "PROTECTED"
        if mem_pct >= cfg.memory.max_pct or max_temp >= cfg.temperature.critical:
            state = "EMERGENCY"
        elif mem_pct >= cfg.memory.hard_pct or psi.get("full_avg10", 0.0) >= 30.0:
            state = "CRITICAL"
        elif mem_pct >= cfg.memory.soft_pct or max_temp >= cfg.temperature.warning or cpu_pct >= cfg.cpu.alert_pct:
            state = "WARNING"

        sample = {
            "timestamp": time.time(),
            "cpu": round(cpu_pct, 1),
            "memory": round(mem_pct, 1),
            "temperature": round(max_temp, 1),
            "disk": round(disks.get("/", 0.0), 1),
            "network_rx": round(sum(v for k, v in nets.items() if k.endswith("_rx_mbps")), 2),
            "network_tx": round(sum(v for k, v in nets.items() if k.endswith("_tx_mbps")), 2),
            "psi_cpu": round(psi.get("some_avg10", 0.0), 1),
            "psi_memory": round(psi.get("full_avg10", 0.0), 1),
            "psi_io": 0.0
        }
        self.metrics_history.append(sample)
        if len(self.metrics_history) > 3600:
            self.metrics_history = self.metrics_history[-3600:]

        return {
            "health": health,
            "state": state,
            "cpu": round(cpu_pct, 1),
            "memory": {
                "used": round(used_gb, 2),
                "total": round(total_gb, 2),
                "percent": round(mem_pct, 1)
            },
            "temperature": round(max_temp, 1),
            "disk": {k: round(v, 1) for k, v in disks.items()},
            "network": {k: round(v, 2) for k, v in nets.items()},
            "battery": bats,
            "psi": {k: round(v, 1) for k, v in psi.items()}
        }

    def _rpc_get_metrics_history(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        limit = params.get("limit", 300)
        if not isinstance(limit, int) or limit <= 0:
            limit = 300
        return self.metrics_history[-limit:]

    def _rpc_get_processes(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        cfg = self.daemon.cfg if self.daemon else load_config()
        total_ram = total_ram_kb() * 1024
        expendable_set = set(cfg.expendable)
        protect_set = set(cfg.protect).union(INTERNAL_BLACKLIST)

        samples = read_all_proc_samples()
        cands = collect_candidates(set())

        proc_list = []
        for c in cands:
            is_exp = c.name in expendable_set
            is_prot = c.name in protect_set
            sc = compute_score(c, cfg.kill.weights, total_ram, is_exp)
            
            proc_list.append({
                "pid": c.pid,
                "name": c.name,
                "cpu": round(c.cpu, 1),
                "rss": c.rss,
                "runtime": c.elapsed_sec,
                "score": round(sc, 3),
                "protected": is_prot,
                "expendable": is_exp
            })

        proc_list.sort(key=lambda x: x["rss"], reverse=True)
        return proc_list

    def _rpc_get_events(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        limit = params.get("limit", 50)
        if not isinstance(limit, int) or limit <= 0:
            limit = 50
        source = params.get("source")
        if source and not isinstance(source, str):
            source = None
        return load_history(source_filter=source, limit=limit)

    def _rpc_get_config(self, params: Dict[str, Any]) -> Dict[str, Any]:
        cfg = self.daemon.cfg if self.daemon else load_config()
        return {
            "protect": cfg.protect,
            "expendable": cfg.expendable,
            "memory": {
                "soft_pct": cfg.memory.soft_pct,
                "hard_pct": cfg.memory.hard_pct,
                "max_pct": cfg.memory.max_pct
            },
            "temperature": {
                "warning": cfg.temperature.warning,
                "critical": cfg.temperature.critical,
                "action": cfg.temperature.action
            },
            "cpu": {
                "alert_pct": cfg.cpu.alert_pct,
                "action": cfg.cpu.action
            },
            "disk": {
                "space_alert_pct": cfg.disk.space_alert_pct,
                "io_alert": cfg.disk.io_alert
            },
            "network": {
                "alert_mbps": cfg.network.alert_mbps
            },
            "kill": {
                "policy": cfg.kill.policy,
                "cooldown": cfg.kill.cooldown,
                "max_per_min": cfg.kill.max_per_min,
                "oom_prefer": cfg.kill.oom_prefer,
                "oom_protect": cfg.kill.oom_protect,
                "weights": {
                    "rss": cfg.kill.weights.rss,
                    "cpu": cfg.kill.weights.cpu,
                    "runtime": cfg.kill.weights.runtime
                }
            }
        }

    def _rpc_protect_process(self, params: Dict[str, Any]) -> Dict[str, Any]:
        name = params.get("name")
        if not name or not isinstance(name, str):
            raise IPCError("INVALID_PARAMS", "Parameter 'name' (string) is required")

        cfg = self.daemon.cfg if self.daemon else load_config()
        if name not in cfg.protect:
            cfg.protect.append(name)
            save_config(cfg)
            if self.daemon:
                self.daemon.cfg = cfg
            record_event("process", "INFO", f"Protected process '{name}'", {"name": name})

        return {"protected": True, "name": name}

    def _rpc_unprotect_process(self, params: Dict[str, Any]) -> Dict[str, Any]:
        name = params.get("name")
        if not name or not isinstance(name, str):
            raise IPCError("INVALID_PARAMS", "Parameter 'name' (string) is required")

        cfg = self.daemon.cfg if self.daemon else load_config()
        if name in cfg.protect:
            cfg.protect.remove(name)
            save_config(cfg)
            if self.daemon:
                self.daemon.cfg = cfg
            record_event("process", "INFO", f"Unprotected process '{name}'", {"name": name})

        return {"unprotected": True, "name": name}

    def _rpc_mark_expendable(self, params: Dict[str, Any]) -> Dict[str, Any]:
        name = params.get("name")
        if not name or not isinstance(name, str):
            raise IPCError("INVALID_PARAMS", "Parameter 'name' (string) is required")

        cfg = self.daemon.cfg if self.daemon else load_config()
        if name not in cfg.expendable:
            cfg.expendable.append(name)
            save_config(cfg)
            if self.daemon:
                self.daemon.cfg = cfg
            record_event("process", "INFO", f"Marked process '{name}' as expendable", {"name": name})

        return {"expendable": True, "name": name}

    def _rpc_unmark_expendable(self, params: Dict[str, Any]) -> Dict[str, Any]:
        name = params.get("name")
        if not name or not isinstance(name, str):
            raise IPCError("INVALID_PARAMS", "Parameter 'name' (string) is required")

        cfg = self.daemon.cfg if self.daemon else load_config()
        if name in cfg.expendable:
            cfg.expendable.remove(name)
            save_config(cfg)
            if self.daemon:
                self.daemon.cfg = cfg
            record_event("process", "INFO", f"Removed expendable status from process '{name}'", {"name": name})

        return {"unmarked_expendable": True, "name": name}

    def _rpc_oom_protect_process(self, params: Dict[str, Any]) -> Dict[str, Any]:
        pid = params.get("pid")
        name = params.get("name")

        if not pid and not name:
            raise IPCError("INVALID_PARAMS", "Either 'pid' or 'name' is required for oom_protect_process")

        from aegis.oom import set_oom_score_adj, run_oom_protect_helper

        cfg = self.daemon.cfg if self.daemon else load_config()

        if pid and isinstance(pid, int):
            if not os.path.exists(f"/proc/{pid}"):
                raise IPCError("INVALID_PARAMS", f"Process PID {pid} does not exist")
            
            proc_name = "unknown"
            try:
                with open(f"/proc/{pid}/comm", "r") as f:
                    proc_name = f.read().strip()
                if proc_name not in cfg.protect:
                    cfg.protect.append(proc_name)
                    save_config(cfg)
                    if self.daemon:
                        self.daemon.cfg = cfg
            except Exception:
                pass

            if not set_oom_score_adj(pid, -1000):
                run_oom_protect_helper()
            record_event("oom", "INFO", f"OOM protection (-1000) applied to process '{proc_name}' (PID {pid})", {"pid": pid, "name": proc_name})
            return {"oom_protected": True, "pid": pid}

        if name and isinstance(name, str):
            if name not in cfg.protect:
                cfg.protect.append(name)
                save_config(cfg)
                if self.daemon:
                    self.daemon.cfg = cfg
            run_oom_protect_helper()
            record_event("oom", "INFO", f"OOM protection (-1000) applied to process '{name}'", {"name": name})
            return {"oom_protected": True, "name": name}

    def _rpc_terminate_process(self, params: Dict[str, Any]) -> Dict[str, Any]:
        pid = params.get("pid")
        if not isinstance(pid, int) or pid <= 1:
            raise IPCError("INVALID_PARAMS", "Valid positive integer 'pid' is required")

        # Check process exists
        if not os.path.exists(f"/proc/{pid}"):
            raise IPCError("INVALID_PARAMS", f"Process PID {pid} does not exist")

        # Read process comm name
        proc_name = "unknown"
        try:
            with open(f"/proc/{pid}/comm", "r") as f:
                proc_name = f.read().strip()
        except Exception:
            pass

        cfg = self.daemon.cfg if self.daemon else load_config()
        protected_set = set(cfg.protect).union(INTERNAL_BLACKLIST)
        if proc_name in protected_set:
            raise IPCError("INVALID_PARAMS", f"Process '{proc_name}' (PID {pid}) is protected and cannot be terminated")

        try:
            os.kill(pid, signal.SIGTERM)
            msg = f"User terminated {proc_name} (PID {pid}) via IPC"
            print(f"[aegis-ipc] {msg}")
            send_notification("Aegis Action", msg, urgency="normal")
            record_event("kill", "info", msg, {"pid": pid, "proc_name": proc_name})
            return {"terminated": True, "pid": pid, "name": proc_name}
        except Exception as e:
            raise IPCError("INTERNAL_ERROR", f"Failed to terminate process {pid}: {e}")

    def _rpc_update_config(self, params: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(params, dict):
            raise IPCError("INVALID_PARAMS", "Config object required")

        cfg = self.daemon.cfg if self.daemon else load_config()

        if "protect" in params and isinstance(params["protect"], list):
            cfg.protect = [str(x) for x in params["protect"]]
        if "expendable" in params and isinstance(params["expendable"], list):
            cfg.expendable = [str(x) for x in params["expendable"]]

        if "memory" in params and isinstance(params["memory"], dict):
            mem = params["memory"]
            if "soft_pct" in mem:
                cfg.memory.soft_pct = float(mem["soft_pct"])
            if "hard_pct" in mem:
                cfg.memory.hard_pct = float(mem["hard_pct"])
            if "max_pct" in mem:
                cfg.memory.max_pct = float(mem["max_pct"])

        if "temperature" in params and isinstance(params["temperature"], dict):
            t = params["temperature"]
            if "warning" in t:
                cfg.temperature.warning = float(t["warning"])
            if "critical" in t:
                cfg.temperature.critical = float(t["critical"])
            if "action" in t:
                cfg.temperature.action = str(t["action"])

        if "cpu" in params and isinstance(params["cpu"], dict):
            c = params["cpu"]
            if "alert_pct" in c:
                cfg.cpu.alert_pct = float(c["alert_pct"])

        if "disk" in params and isinstance(params["disk"], dict):
            d = params["disk"]
            if "space_alert_pct" in d:
                cfg.disk.space_alert_pct = float(d["space_alert_pct"])

        if "network" in params and isinstance(params["network"], dict):
            n = params["network"]
            if "alert_mbps" in n:
                cfg.network.alert_mbps = float(n["alert_mbps"])

        if "kill" in params and isinstance(params["kill"], dict):
            k = params["kill"]
            if "policy" in k:
                cfg.kill.policy = str(k["policy"])
            if "cooldown" in k:
                cfg.kill.cooldown = str(k["cooldown"])
            if "max_per_min" in k:
                cfg.kill.max_per_min = int(k["max_per_min"])
            if "weights" in k and isinstance(k["weights"], dict):
                w = k["weights"]
                if "rss" in w:
                    cfg.kill.weights.rss = float(w["rss"])
                if "cpu" in w:
                    cfg.kill.weights.cpu = float(w["cpu"])
                if "runtime" in w:
                    cfg.kill.weights.runtime = float(w["runtime"])

        save_config(cfg)
        if self.daemon:
            self.daemon.cfg = cfg

        return {"updated": True}


class IPCClient:
    def __init__(self, socket_path: str = SOCKET_PATH, timeout: float = 5.0):
        self.socket_path = socket_path
        self.timeout = timeout
        self._req_id = 0

    def _call(self, method: str, params: Dict[str, Any] = None) -> Any:
        if not os.path.exists(self.socket_path):
            raise IPCError("NO_SERVER", f"IPC socket not found at {self.socket_path}. Is Aegis daemon running?")

        self._req_id += 1
        req = {
            "id": self._req_id,
            "method": method,
            "params": params or {}
        }

        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            sock.connect(self.socket_path)

            sock.sendall((json.dumps(req) + "\n").encode("utf-8"))

            rfile = sock.makefile("r", encoding="utf-8")
            line = rfile.readline()
            sock.close()

            if not line:
                raise IPCError("DISCONNECTED", "Daemon closed connection without response")

            resp = json.loads(line)
            if not resp.get("ok"):
                err = resp.get("error", {})
                raise IPCError(err.get("code", "UNKNOWN"), err.get("message", "IPC Error"))

            return resp.get("result")
        except socket.timeout:
            raise IPCError("TIMEOUT", f"IPC call '{method}' timed out after {self.timeout}s")
        except (ConnectionRefusedError, FileNotFoundError):
            raise IPCError("NO_SERVER", "Aegis daemon IPC server is not reachable")
        except json.JSONDecodeError:
            raise IPCError("PARSE_ERROR", "Invalid JSON response from daemon")

    def get_status(self) -> Dict[str, Any]:
        return self._call("get_status")

    def get_processes(self) -> List[Dict[str, Any]]:
        return self._call("get_processes")

    def get_events(self, limit: int = 50, source: str = None) -> List[Dict[str, Any]]:
        p = {"limit": limit}
        if source:
            p["source"] = source
        return self._call("get_events", p)

    def get_config(self) -> Dict[str, Any]:
        return self._call("get_config")

    def protect_process(self, name: str) -> Dict[str, Any]:
        return self._call("protect_process", {"name": name})

    def unprotect_process(self, name: str) -> Dict[str, Any]:
        return self._call("unprotect_process", {"name": name})

    def mark_expendable(self, name: str) -> Dict[str, Any]:
        return self._call("mark_expendable", {"name": name})

    def unmark_expendable(self, name: str) -> Dict[str, Any]:
        return self._call("unmark_expendable", {"name": name})

    def oom_protect_process(self, pid: int = None, name: str = None) -> Dict[str, Any]:
        p = {}
        if pid is not None:
            p["pid"] = pid
        if name is not None:
            p["name"] = name
        return self._call("oom_protect_process", p)

    def terminate_process(self, pid: int) -> Dict[str, Any]:
        return self._call("terminate_process", {"pid": pid})

    def update_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        return self._call("update_config", config)

    def get_metrics_history(self, limit: int = 300) -> List[Dict[str, Any]]:
        return self._call("get_metrics_history", {"limit": limit})
