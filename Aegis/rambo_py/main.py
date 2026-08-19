import sys
import argparse
from rambo_py.daemon import Daemon
from rambo_py.cli.top import run_top
from rambo_py.cli.stats import run_stats
from rambo_py.cli.threshold import run_threshold
from rambo_py.cli.protect import run_protect
from rambo_py.cli.history import run_history
from rambo_py.cli.oomprotect import run_oom_protect
from rambo_py.state import clear_history

def main():
    parser = argparse.ArgumentParser(
        prog="rambo-py",
        description="RamboPy: Event-driven, kernel-backed system monitor and resource daemon for Linux"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # daemon
    p_daemon = subparsers.add_parser("daemon", help="Start the rambo-py event-driven daemon")

    # top
    p_top = subparsers.add_parser("top", help="One-shot view of system stats and top RAM consumers")

    # stats
    p_stats = subparsers.add_parser("stats", help="Live interactive system dashboard (TUI)")

    # threshold
    p_thresh = subparsers.add_parser("threshold", help="Manage memory and resource thresholds")
    thresh_sub = p_thresh.add_subparsers(dest="subcommand", help="Threshold subcommand")
    p_thresh_status = thresh_sub.add_parser("status", help="Show current thresholds")
    p_thresh_set = thresh_sub.add_parser("set", help="Set custom thresholds")
    p_thresh_set.add_argument("--soft-pct", type=float, help="Soft memory limit percentage")
    p_thresh_set.add_argument("--hard-pct", type=float, help="Hard memory limit percentage")
    p_thresh_set.add_argument("--max-pct", type=float, help="Max memory limit percentage")
    p_thresh_set.add_argument("--temp-kill", type=float, help="Thermal kill threshold in °C")
    p_thresh_set.add_argument("--cpu-alert", type=float, help="CPU alert threshold %%")
    p_thresh_set.add_argument("--net-alert", type=float, help="Network alert threshold Mbps")
    p_thresh_set.add_argument("--disk-alert", type=float, help="Disk space alert threshold %%")

    # protect / whitelist
    p_prot = subparsers.add_parser("protect", help="Manage protected process whitelist")
    prot_sub = p_prot.add_subparsers(dest="subcommand", help="Protect subcommand")
    p_prot_list = prot_sub.add_parser("list", help="List protected processes")
    p_prot_add = prot_sub.add_parser("add", help="Add process to protect whitelist")
    p_prot_add.add_argument("--name", type=str, required=True, help="Process name to protect")
    p_prot_rem = prot_sub.add_parser("remove", help="Remove process from protect whitelist")
    p_prot_rem.add_argument("--name", type=str, required=True, help="Process name to unprotect")

    # oom-protect
    p_oom = subparsers.add_parser("oom-protect", help="Privileged helper setting oom_score_adj=-1000")

    # history
    p_hist = subparsers.add_parser("history", help="Show past events and kills")
    p_hist.add_argument("--source", type=str, help="Filter events by source")
    p_hist.add_argument("-n", type=int, default=50, help="Number of history items to show")

    # clean
    p_clean = subparsers.add_parser("clean", help="Delete state history and log file")

    args = parser.parse_args()

    if args.command == "daemon":
        d = Daemon()
        d.run()
    elif args.command == "top":
        run_top(args)
    elif args.command == "stats":
        run_stats(args)
    elif args.command == "threshold":
        run_threshold(args)
    elif args.command == "protect":
        run_protect(args)
    elif args.command == "oom-protect":
        run_oom_protect(args)
    elif args.command == "history":
        run_history(args)
    elif args.command == "clean":
        clear_history()
        print("[rambo-py] State history logs cleared.")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
