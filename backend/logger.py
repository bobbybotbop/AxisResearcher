from backend import db as _db


def log_event(event: str, status: str, **fields) -> None:
    """Append an entry to the logs table in axis.db (auto-trimmed to the
    newest MAX_LOG_ENTRIES rows)."""
    _db.ensure_db()
    _db.log(event, status, **fields)
