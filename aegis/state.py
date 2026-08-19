import os
import time
import json
from datetime import datetime
from typing import List, Dict, Any

STATE_DIR = os.path.expanduser("~/.local/state/aegis")
STATE_FILE = os.path.join(STATE_DIR, "state.json")
MAX_EVENTS = 500

def record_event(source: str, severity: str, message: str, values: Dict[str, float] = None):
    os.makedirs(STATE_DIR, exist_ok=True)
    events = load_history(limit=MAX_EVENTS)
    
    now = datetime.now()
    now_ts = now.timestamp()
    evt_id = f"evt-{int(now_ts * 1000)}-{len(events) + 1}"
    
    event = {
        "id": evt_id,
        "timestamp": now.isoformat(),
        "timestamp_epoch": now_ts,
        "source": source,
        "severity": severity.upper(),
        "message": message,
        "values": values or {}
    }
    events.append(event)
    if len(events) > MAX_EVENTS:
        events = events[-MAX_EVENTS:]
    
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(events, f, indent=2)
    except Exception:
        pass

def load_history(source_filter: str = None, limit: int = 100) -> List[Dict[str, Any]]:
    if not os.path.exists(STATE_FILE):
        return []
    try:
        with open(STATE_FILE, "r") as f:
            data = json.load(f)
        
        # Ensure event IDs and epoch timestamps exist
        for idx, e in enumerate(data):
            if "id" not in e:
                ts_str = e.get("timestamp", "")
                e["id"] = f"evt-legacy-{idx}-{hash(ts_str) & 0xffff}"
            if "timestamp_epoch" not in e:
                try:
                    e["timestamp_epoch"] = datetime.fromisoformat(e["timestamp"]).timestamp()
                except Exception:
                    e["timestamp_epoch"] = 0.0

        if source_filter:
            data = [e for e in data if e.get("source") == source_filter]
        return data[-limit:]
    except Exception:
        return []

def clear_history():
    if os.path.exists(STATE_FILE):
        try:
            os.remove(STATE_FILE)
        except Exception:
            pass
