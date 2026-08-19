import os
import subprocess
from datetime import datetime

LOG_DIR = os.path.expanduser("~/.local/share/aegis")
LOG_FILE = os.path.join(LOG_DIR, "aegis.log")

def send_notification(title: str, message: str, urgency: str = "normal"):
    os.makedirs(LOG_DIR, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] [{urgency.upper()}] {title}: {message}\n"
    try:
        with open(LOG_FILE, "a") as f:
            f.write(log_line)
    except Exception:
        pass

    try:
        subprocess.run(
            ["notify-send", "-u", urgency, "-a", "Aegis", title, message],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=2
        )
    except Exception:
        pass
