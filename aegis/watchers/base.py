from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional

class Severity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"

@dataclass
class Event:
    severity: Severity
    source: str
    message: str
    values: Dict[str, float] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

class Watcher:
    def name(self) -> str:
        raise NotImplementedError

    def run(self, emit_func):
        raise NotImplementedError

    def snapshot(self) -> Dict[str, float]:
        return {}
