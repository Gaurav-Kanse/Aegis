from aegis.state import load_history

def run_history(args):
    source_filter = args.source if hasattr(args, "source") else None
    limit = args.n if hasattr(args, "n") and args.n else 50
    
    events = load_history(source_filter, limit)
    if not events:
        print("No history events recorded.")
        return

    print(f"=== Aegis Event History ({len(events)} events) ===")
    for e in events:
        ts = e.get("timestamp", "")
        src = e.get("source", "").upper()
        sev = e.get("severity", "").upper()
        msg = e.get("message", "")
        print(f"[{ts}] [{sev:<8}] [{src:<10}] {msg}")
