import time
from typing import Dict, Tuple
from rambo_py.watchers.base import Watcher, Event, Severity
from rambo_py.config import Config

class NetWatcher(Watcher):
    def __init__(self, config: Config):
        self.config = config

    def name(self) -> str:
        return "network"

    def read_net_dev(self) -> Dict[str, Tuple[int, int]]:
        """Returns dict of interface -> (rx_bytes, tx_bytes)."""
        res = {}
        try:
            with open("/proc/net/dev", "r") as f:
                lines = f.readlines()
            for line in lines[2:]:
                parts = line.split(":")
                if len(parts) == 2:
                    iface = parts[0].strip()
                    fields = parts[1].split()
                    if len(fields) >= 9:
                        rx = int(fields[0])
                        tx = int(fields[8])
                        res[iface] = (rx, tx)
        except Exception:
            pass
        return res

    def snapshot(self) -> Dict[str, float]:
        n1 = self.read_net_dev()
        time.sleep(0.5)
        n2 = self.read_net_dev()
        res = {}
        for iface, (r2, t2) in n2.items():
            if iface in n1 and not iface.startswith("lo"):
                r1, t1 = n1[iface]
                rx_mbps = (r2 - r1) * 8 / (0.5 * 1000 * 1000)
                tx_mbps = (t2 - t1) * 8 / (0.5 * 1000 * 1000)
                res[f"{iface}_rx_mbps"] = rx_mbps
                res[f"{iface}_tx_mbps"] = tx_mbps
        return res

    def run(self, emit_func):
        n1 = self.read_net_dev()
        t1 = time.time()
        while True:
            try:
                time.sleep(2)
                t2 = time.time()
                dt = t2 - t1
                n2 = self.read_net_dev()

                for iface, (r2, tx2) in n2.items():
                    if iface in n1 and not iface.startswith("lo") and dt > 0:
                        r1, tx1 = n1[iface]
                        rx_mbps = (r2 - r1) * 8 / (dt * 1000 * 1000)
                        tx_mbps = (tx2 - tx1) * 8 / (dt * 1000 * 1000)
                        tot_mbps = rx_mbps + tx_mbps
                        if tot_mbps >= self.config.network.alert_mbps:
                            emit_func(Event(
                                severity=Severity.WARNING,
                                source="network",
                                message=f"Network alert on {iface}: {tot_mbps:.1f} Mbps >= {self.config.network.alert_mbps:.1f} Mbps",
                                values={"iface": iface, "tot_mbps": tot_mbps}
                            ))
                n1, t1 = n2, t2
            except Exception:
                time.sleep(2)
