import json
import os
import threading
from datetime import datetime, timezone

from backend.constants.paths import LOG_FILE_NAME, MAX_LOG_ENTRIES

_lock = threading.Lock()
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_LOG_FILE = os.path.join(_PROJECT_ROOT, LOG_FILE_NAME)
_MAX_ENTRIES = MAX_LOG_ENTRIES


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
