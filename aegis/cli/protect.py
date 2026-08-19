import sys
from aegis.config import load_config, save_config

def run_protect(args):
    cfg = load_config()
    
    if args.subcommand == "list":
        if not cfg.protect:
            print("Protect list is empty")
        else:
            print("Protected processes:")
            for p in cfg.protect:
                print(f"  - {p}")

    elif args.subcommand == "add":
        if not args.name:
            print("Error: --name required")
            return
        if args.name not in cfg.protect:
            cfg.protect.append(args.name)
            save_config(cfg)
            print(f"[aegis] Added '{args.name}' to protect list")
        else:
            print(f"[aegis] '{args.name}' is already in protect list")

    elif args.subcommand == "remove":
        if not args.name:
            print("Error: --name required")
            return
        if args.name in cfg.protect:
            cfg.protect.remove(args.name)
            save_config(cfg)
            print(f"[aegis] Removed '{args.name}' from protect list")
        else:
            print(f"[aegis] '{args.name}' not found in protect list")
