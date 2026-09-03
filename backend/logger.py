import json
import os
import threading
from datetime import datetime, timezone

_lock = threading.Lock()
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_LOG_FILE = os.path.join(_PROJECT_ROOT, "logs.ndjson")
_MAX_ENTRIES = 1000


def log_event(event: str, status: str, **fields) -> None:
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "status": status,
        **fields,
    }
    line = json.dumps(entry, ensure_ascii=False)
    with _lock:
        with open(_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
        _trim_log_file()


def _trim_log_file() -> None:
    try:
        with open(_LOG_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        if len(lines) > _MAX_ENTRIES:
            with open(_LOG_FILE, "w", encoding="utf-8") as f:
                f.writelines(lines[-_MAX_ENTRIES:])
    except FileNotFoundError:
        pass
