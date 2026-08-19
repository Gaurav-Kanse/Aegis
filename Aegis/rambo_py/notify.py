import os
import subprocess
from datetime import datetime

LOG_DIR = os.path.expanduser("~/.local/share/rambo-py")
LOG_FILE = os.path.join(LOG_DIR, "rambo.log")

def send_notification(title: str, message: str, urgency: str = "normal"):
    os.makedirs(LOG_DIR, exist_ok=True)
    
    # Log to file
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] [{urgency.upper()}] {title}: {message}\n"
    try:
        with open(LOG_FILE, "a") as f:
            f.write(log_line)
    except Exception:
        pass

    # Try notify-send desktop notification
    try:
        subprocess.run(
            ["notify-send", "-u", urgency, "-a", "RamboPy", title, message],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=2
        )
    except Exception:
        pass
