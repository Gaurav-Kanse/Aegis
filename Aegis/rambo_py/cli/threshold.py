import sys
from rambo_py.config import load_config, save_config
from rambo_py.utils.proc import total_ram_kb

def run_threshold(args):
    cfg = load_config()
    total_kb = total_ram_kb()
    total_gb = total_kb / 1024 / 1024

    if args.subcommand == "status":
        soft_gb = total_gb * (cfg.memory.soft_pct / 100.0)
        hard_gb = total_gb * (cfg.memory.hard_pct / 100.0)
        max_gb = total_gb * (cfg.memory.max_pct / 100.0)

        print(f"Soft threshold:   {cfg.memory.soft_pct:.0f}% ({soft_gb:.1f} GB)")
        print(f"Hard threshold:   {cfg.memory.hard_pct:.0f}% ({hard_gb:.1f} GB)")
        print(f"Kernel max:       {cfg.memory.max_pct:.0f}% ({max_gb:.1f} GB)")
        print(f"Temp kill:        {cfg.temperature.critical:.0f} C")
        print(f"Network alert:    {cfg.network.alert_mbps:.1f} MB/s")
        print(f"CPU alert:        {cfg.cpu.alert_pct:.1f}%")
        print(f"Disk space alert: {cfg.disk.space_alert_pct:.1f}%")
        print(f"Kill policy:      {cfg.kill.policy} (cooldown {cfg.kill.cooldown}, max {cfg.kill.max_per_min}/min)")
        print(f"Protect list:     {cfg.protect}")
        print(f"Expendable list:  {cfg.expendable}")

    elif args.subcommand == "set":
        if args.soft_pct is not None:
            cfg.memory.soft_pct = float(args.soft_pct)
        if args.hard_pct is not None:
            cfg.memory.hard_pct = float(args.hard_pct)
        if args.max_pct is not None:
            cfg.memory.max_pct = float(args.max_pct)
        if args.temp_kill is not None:
            cfg.temperature.critical = float(args.temp_kill)
        if args.cpu_alert is not None:
            cfg.cpu.alert_pct = float(args.cpu_alert)
        if args.net_alert is not None:
            cfg.network.alert_mbps = float(args.net_alert)
        if args.disk_alert is not None:
            cfg.disk.space_alert_pct = float(args.disk_alert)

        save_config(cfg)
        print("[rambo-py] Thresholds updated successfully.")
