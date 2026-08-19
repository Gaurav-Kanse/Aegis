import os
import json
from datetime import datetime
from typing import List, Dict, Any

STATE_DIR = os.path.expanduser("~/.local/state/aegis")
STATE_FILE = os.path.join(STATE_DIR, "state.json")
MAX_EVENTS = 500

def record_event(source: str, severity: str, message: str, values: Dict[str, float] = None):
    os.makedirs(STATE_DIR, exist_ok=True)
    events = load_history()
    
    event = {
        "timestamp": datetime.now().isoformat(),
        "source": source,
        "severity": severity,
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

def load_history(source_filter: str = None, limit: int = 50) -> List[Dict[str, Any]]:
    if not os.path.exists(STATE_FILE):
        return []
    try:
        with open(STATE_FILE, "r") as f:
            data = json.load(f)
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
