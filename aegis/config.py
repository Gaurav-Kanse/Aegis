import os
import sys
from dataclasses import dataclass, field
from typing import List, Dict, Any

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None

CONFIG_DIR = os.path.expanduser("~/.config/aegis")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.toml")

DEFAULT_CONFIG_CONTENT = """# Aegis Configuration
protect = ["nvim", "gnome-shell", "code", "python3"]
expendable = ["steam"]

[memory]
soft_pct = 90
hard_pct = 96
max_pct = 99

[memory_pressure]
some_pct = 60
full_pct = 20
window = "10s"
action = "escalate"

[temperature]
warning = 85
critical = 90
action = "kill"
sensors = []

[network]
alert_mbps = 900
action = "notify"

[cpu]
alert_pct = 90
action = "notify"

[disk]
space_alert_pct = 90
io_alert = true
action = "notify"

[kill]
policy = "score"
cooldown = "30s"
max_per_min = 3
oom_prefer = true
oom_protect = true

[kill.weights]
rss = 0.6
cpu = 0.3
runtime = 0.1

[battery]
low_pct = 20
action = "suspend"
"""

@dataclass
class MemoryConfig:
    soft_pct: float = 90.0
    hard_pct: float = 96.0
    max_pct: float = 99.0

@dataclass
class TempConfig:
    warning: float = 85.0
    critical: float = 90.0
    action: str = "kill"
    sensors: List[str] = field(default_factory=list)

@dataclass
class NetConfig:
    alert_mbps: float = 900.0
    action: str = "notify"

@dataclass
class CPUConfig:
    alert_pct: float = 90.0
    action: str = "notify"

@dataclass
class DiskConfig:
    space_alert_pct: float = 90.0
    io_alert: bool = True
    action: str = "notify"

@dataclass
class KillWeights:
    rss: float = 0.6
    cpu: float = 0.3
    runtime: float = 0.1

@dataclass
class KillConfig:
    policy: str = "score"
    cooldown: str = "30s"
    max_per_min: int = 3
    oom_prefer: bool = True
    oom_protect: bool = True
    weights: KillWeights = field(default_factory=KillWeights)

@dataclass
class BatteryConfig:
    low_pct: float = 20.0
    action: str = "suspend"

@dataclass
class Config:
    protect: List[str] = field(default_factory=lambda: ["nvim", "gnome-shell", "code", "python3"])
    expendable: List[str] = field(default_factory=lambda: ["steam"])
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    temperature: TempConfig = field(default_factory=TempConfig)
    network: NetConfig = field(default_factory=NetConfig)
    cpu: CPUConfig = field(default_factory=CPUConfig)
    disk: DiskConfig = field(default_factory=DiskConfig)
    kill: KillConfig = field(default_factory=KillConfig)
    battery: BatteryConfig = field(default_factory=BatteryConfig)

def load_config() -> Config:
    os.makedirs(CONFIG_DIR, exist_ok=True)
    if not os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "w") as f:
            f.write(DEFAULT_CONFIG_CONTENT)
    
    cfg = Config()
    if tomllib is not None:
        try:
            with open(CONFIG_PATH, "rb") as f:
                data = tomllib.load(f)
            
            if "protect" in data:
                cfg.protect = list(data["protect"])
            if "expendable" in data:
                cfg.expendable = list(data["expendable"])
            
            mem = data.get("memory", {})
            cfg.memory.soft_pct = float(mem.get("soft_pct", cfg.memory.soft_pct))
            cfg.memory.hard_pct = float(mem.get("hard_pct", cfg.memory.hard_pct))
            cfg.memory.max_pct = float(mem.get("max_pct", cfg.memory.max_pct))

            t = data.get("temperature", {})
            cfg.temperature.warning = float(t.get("warning", cfg.temperature.warning))
            cfg.temperature.critical = float(t.get("critical", cfg.temperature.critical))
            cfg.temperature.action = str(t.get("action", cfg.temperature.action))
            cfg.temperature.sensors = list(t.get("sensors", cfg.temperature.sensors))

            n = data.get("network", {})
            cfg.network.alert_mbps = float(n.get("alert_mbps", cfg.network.alert_mbps))
            cfg.network.action = str(n.get("action", cfg.network.action))

            c = data.get("cpu", {})
            cfg.cpu.alert_pct = float(c.get("alert_pct", cfg.cpu.alert_pct))
            cfg.cpu.action = str(c.get("action", cfg.cpu.action))

            d = data.get("disk", {})
            cfg.disk.space_alert_pct = float(d.get("space_alert_pct", cfg.disk.space_alert_pct))
            cfg.disk.io_alert = bool(d.get("io_alert", cfg.disk.io_alert))
            cfg.disk.action = str(d.get("action", cfg.disk.action))

            k = data.get("kill", {})
            cfg.kill.policy = str(k.get("policy", cfg.kill.policy))
            cfg.kill.cooldown = str(k.get("cooldown", cfg.kill.cooldown))
            cfg.kill.max_per_min = int(k.get("max_per_min", cfg.kill.max_per_min))
            cfg.kill.oom_prefer = bool(k.get("oom_prefer", cfg.kill.oom_prefer))
            cfg.kill.oom_protect = bool(k.get("oom_protect", cfg.kill.oom_protect))

            w = k.get("weights", {})
            cfg.kill.weights.rss = float(w.get("rss", cfg.kill.weights.rss))
            cfg.kill.weights.cpu = float(w.get("cpu", cfg.kill.weights.cpu))
            cfg.kill.weights.runtime = float(w.get("runtime", cfg.kill.weights.runtime))

            b = data.get("battery", {})
            cfg.battery.low_pct = float(b.get("low_pct", cfg.battery.low_pct))
            cfg.battery.action = str(b.get("action", cfg.battery.action))

        except Exception as e:
            print(f"[aegis] Config parse warning: {e}. Using defaults.")

    return cfg

def get_default_config() -> Config:
    return Config()

def validate_config_dict(data: Dict[str, Any], current_cfg: Config = None) -> None:
    """Validates configuration updates. Raises ValueError with descriptive error if invalid."""
    if current_cfg is None:
        current_cfg = Config()

    # Create dummy copy for full validation
    soft_pct = current_cfg.memory.soft_pct
    hard_pct = current_cfg.memory.hard_pct
    max_pct = current_cfg.memory.max_pct

    warning_temp = current_cfg.temperature.warning
    critical_temp = current_cfg.temperature.critical

    rss_w = current_cfg.kill.weights.rss
    cpu_w = current_cfg.kill.weights.cpu
    rt_w = current_cfg.kill.weights.runtime

    if "memory" in data:
        mem = data["memory"]
        if not isinstance(mem, dict):
            raise ValueError("Memory config must be a dictionary")
        if "soft_pct" in mem:
            val = float(mem["soft_pct"])
            if not (0 <= val <= 100):
                raise ValueError("Memory soft threshold must be between 0% and 100%")
            soft_pct = val
        if "hard_pct" in mem:
            val = float(mem["hard_pct"])
            if not (0 <= val <= 100):
                raise ValueError("Memory hard threshold must be between 0% and 100%")
            hard_pct = val
        if "max_pct" in mem:
            val = float(mem["max_pct"])
            if not (0 <= val <= 100):
                raise ValueError("Memory max threshold must be between 0% and 100%")
            max_pct = val

        if soft_pct >= hard_pct:
            raise ValueError("Hard memory threshold must be greater than soft threshold")
        if hard_pct >= max_pct:
            raise ValueError("Critical/max memory threshold must be greater than hard threshold")

    if "temperature" in data:
        t = data["temperature"]
        if not isinstance(t, dict):
            raise ValueError("Temperature config must be a dictionary")
        if "warning" in t:
            val = float(t["warning"])
            if not (0 <= val <= 150):
                raise ValueError("Warning temperature must be between 0°C and 150°C")
            warning_temp = val
        if "critical" in t:
            val = float(t["critical"])
            if not (0 <= val <= 150):
                raise ValueError("Critical temperature must be between 0°C and 150°C")
            critical_temp = val

        if warning_temp >= critical_temp:
            raise ValueError("Warning temperature must be lower than critical temperature")

    if "cpu" in data:
        c = data["cpu"]
        if not isinstance(c, dict):
            raise ValueError("CPU config must be a dictionary")
        if "alert_pct" in c:
            val = float(c["alert_pct"])
            if not (0 <= val <= 100):
                raise ValueError("CPU alert threshold must be between 0% and 100%")

    if "disk" in data:
        d = data["disk"]
        if not isinstance(d, dict):
            raise ValueError("Disk config must be a dictionary")
        if "space_alert_pct" in d:
            val = float(d["space_alert_pct"])
            if not (0 <= val <= 100):
                raise ValueError("Disk space alert threshold must be between 0% and 100%")

    if "network" in data:
        n = data["network"]
        if not isinstance(n, dict):
            raise ValueError("Network config must be a dictionary")
        if "alert_mbps" in n:
            val = float(n["alert_mbps"])
            if val < 0:
                raise ValueError("Network alert threshold cannot be negative")

    if "kill" in data:
        k = data["kill"]
        if not isinstance(k, dict):
            raise ValueError("Kill config must be a dictionary")
        if "max_per_min" in k:
            val = int(k["max_per_min"])
            if val < 0:
                raise ValueError("Maximum kills per minute cannot be negative")
        if "weights" in k:
            w = k["weights"]
            if not isinstance(w, dict):
                raise ValueError("Kill weights must be a dictionary")
            if "rss" in w:
                rss_w = float(w["rss"])
                if not (0 <= rss_w <= 1.0):
                    raise ValueError("RSS scoring weight must be between 0.0 and 1.0")
            if "cpu" in w:
                cpu_w = float(w["cpu"])
                if not (0 <= cpu_w <= 1.0):
                    raise ValueError("CPU scoring weight must be between 0.0 and 1.0")
            if "runtime" in w:
                rt_w = float(w["runtime"])
                if not (0 <= rt_w <= 1.0):
                    raise ValueError("Runtime scoring weight must be between 0.0 and 1.0")

            total_weight = round(rss_w + cpu_w + rt_w, 4)
            if abs(total_weight - 1.0) > 0.01:
                raise ValueError(f"Scoring weights must total 100% (currently {int(round(total_weight * 100))}%)")

    if "battery" in data:
        b = data["battery"]
        if not isinstance(b, dict):
            raise ValueError("Battery config must be a dictionary")
        if "low_pct" in b:
            val = float(b["low_pct"])
            if not (0 <= val <= 100):
                raise ValueError("Battery low threshold must be between 0% and 100%")

def save_config(cfg: Config):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    protect_str = ", ".join(f'"{p}"' for p in cfg.protect)
    expendable_str = ", ".join(f'"{e}"' for e in cfg.expendable)
    sensors_str = ", ".join(f'"{s}"' for s in cfg.temperature.sensors)

    content = f"""# Aegis Configuration
protect = [{protect_str}]
expendable = [{expendable_str}]

[memory]
soft_pct = {cfg.memory.soft_pct}
hard_pct = {cfg.memory.hard_pct}
max_pct = {cfg.memory.max_pct}

[temperature]
warning = {cfg.temperature.warning}
critical = {cfg.temperature.critical}
action = "{cfg.temperature.action}"
sensors = [{sensors_str}]

[network]
alert_mbps = {cfg.network.alert_mbps}
action = "{cfg.network.action}"

[cpu]
alert_pct = {cfg.cpu.alert_pct}
action = "{cfg.cpu.action}"

[disk]
space_alert_pct = {cfg.disk.space_alert_pct}
io_alert = {str(cfg.disk.io_alert).lower()}
action = "{cfg.disk.action}"

[kill]
policy = "{cfg.kill.policy}"
cooldown = "{cfg.kill.cooldown}"
max_per_min = {cfg.kill.max_per_min}
oom_prefer = {str(cfg.kill.oom_prefer).lower()}
oom_protect = {str(cfg.kill.oom_protect).lower()}

[kill.weights]
rss = {cfg.kill.weights.rss}
cpu = {cfg.kill.weights.cpu}
runtime = {cfg.kill.weights.runtime}

[battery]
low_pct = {cfg.battery.low_pct}
action = "{cfg.battery.action}"
"""
    tmp_path = CONFIG_PATH + ".tmp"
    with open(tmp_path, "w") as f:
        f.write(content)
    os.replace(tmp_path, CONFIG_PATH)

