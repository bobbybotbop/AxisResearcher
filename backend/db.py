"""
SQLite storage foundation (GLOSSARY: "SQLite Database").

The single persistent store for all structured application data, replacing
listingPreferences.json, Generated_Listings/*.json, logs.ndjson, and
prompts/*.txt. Uses Python's stdlib sqlite3 (no ORM). Binary files stay on
disk; the database stores their paths. Secrets remain in .env.

On first run (axis.db does not exist yet) all existing data is migrated from
the JSON files into the database. The JSON files are kept as backup.
"""

import json
import os
import sqlite3
import threading
from datetime import datetime, timezone

from backend.constants.paths import (
    CONFIG_FILE,
    DB_FILE_NAME,
    GENERATED_LISTINGS_DIR,
    LOG_FILE_NAME,
    MAX_LOG_ENTRIES,
    PROMPTS_DIR,
)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Module-level path so tests can monkeypatch it (same pattern as CONFIG_FILE).
DB_FILE = os.path.join(PROJECT_ROOT, DB_FILE_NAME)

_lock = threading.RLock()

_SCHEMA = """
CREATE TABLE IF NOT EXISTS preferences (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS listings (
    sku             TEXT PRIMARY KEY,
    title           TEXT,
    price           TEXT,
    currency        TEXT,
    category_id     TEXT,
    quantity        INTEGER,
    image_count     INTEGER,
    ebay_listing_id TEXT,
    is_manual       INTEGER,
    is_variation    INTEGER,
    ebay_status     TEXT,
    hidden          INTEGER,
    created_at      TEXT,
    raw_json        TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS logs (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    event     TEXT,
    status    TEXT,
    details   TEXT
);
CREATE TABLE IF NOT EXISTS prompts (
    name       TEXT PRIMARY KEY,
    content    TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS saved_3d_files (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    ebay_listing_url   TEXT,
    ebay_listing_title TEXT,
    source_site        TEXT,
    source_url         TEXT,
    match_label        TEXT,
    pipeline           TEXT,
    file_path          TEXT,
    images_dir         TEXT,
    created_at         TEXT
);
"""


def _connect():
    conn = sqlite3.connect(DB_FILE, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Create the database and tables if they do not exist."""
    with _lock:
        conn = _connect()
        try:
            conn.executescript(_SCHEMA)
            conn.commit()
        finally:
            conn.close()


def ensure_db():
    """App startup entry point: create tables, and on first run (axis.db did
    not exist) migrate all existing data from the JSON files into the database."""
    first_run = not os.path.exists(DB_FILE)
    init_db()
    if first_run:
        migrate_from_json()


# --- preferences ---

def get_preference(key, default=None):
    with _lock:
        conn = _connect()
        try:
            row = conn.execute("SELECT value FROM preferences WHERE key = ?", (key,)).fetchone()
        finally:
            conn.close()
    if row is None:
        return default
    return json.loads(row["value"])


def set_preference(key, value):
    encoded = json.dumps(value, ensure_ascii=False)
    with _lock:
        conn = _connect()
        try:
            conn.execute(
                "INSERT INTO preferences (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, encoded),
            )
            conn.commit()
        finally:
            conn.close()


def get_all_preferences():
    with _lock:
        conn = _connect()
        try:
            rows = conn.execute("SELECT key, value FROM preferences").fetchall()
        finally:
            conn.close()
    return {row["key"]: json.loads(row["value"]) for row in rows}


# --- listings ---

def _listing_columns(data):
    product = data.get("inventoryItem", {}).get("product", {})
    offer = data.get("offer", {})
    price = offer.get("pricingSummary", {}).get("price", {})
    image_urls = product.get("imageUrls", []) or []
    quantity = offer.get("quantity", 0)
    try:
        quantity = int(quantity)
    except (TypeError, ValueError):
        quantity = 0
    return {
        "title": product.get("title", ""),
        "price": str(price.get("value", "")),
        "currency": str(price.get("currency", "USD")),
        "category_id": str(offer.get("categoryId", "")),
        "quantity": quantity,
        "image_count": len(image_urls),
        "ebay_listing_id": str(data.get("ebayListingId") or "").strip(),
        "is_manual": 1 if data.get("isManualListing") else 0,
        "is_variation": 1 if data.get("isVariationListing") else 0,
        "ebay_status": data.get("ebay_status", "active"),
        "hidden": 1 if data.get("hidden") else 0,
        "created_at": data.get("createdDateTime", ""),
    }


def save_listing(data, filename=None):
    """Insert or replace a listing. The SKU comes from data['sku'], falling back
    to the filename stem (matching the old {sku}.json convention)."""
    sku = str(data.get("sku") or "").strip()
    if not sku and filename:
        sku = filename[:-5] if filename.endswith(".json") else filename
    if not sku:
        raise ValueError("save_listing: could not determine SKU")
    cols = _listing_columns(data)
    raw = json.dumps(data, ensure_ascii=False)
    with _lock:
        conn = _connect()
        try:
            conn.execute(
                """
                INSERT INTO listings (
                    sku, title, price, currency, category_id, quantity, image_count,
                    ebay_listing_id, is_manual, is_variation, ebay_status, hidden,
                    created_at, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(sku) DO UPDATE SET
                    title=excluded.title, price=excluded.price, currency=excluded.currency,
                    category_id=excluded.category_id, quantity=excluded.quantity,
                    image_count=excluded.image_count, ebay_listing_id=excluded.ebay_listing_id,
                    is_manual=excluded.is_manual, is_variation=excluded.is_variation,
                    ebay_status=excluded.ebay_status, hidden=excluded.hidden,
                    created_at=excluded.created_at, raw_json=excluded.raw_json
                """,
                (
                    sku, cols["title"], cols["price"], cols["currency"], cols["category_id"],
                    cols["quantity"], cols["image_count"], cols["ebay_listing_id"],
                    cols["is_manual"], cols["is_variation"], cols["ebay_status"],
                    cols["hidden"], cols["created_at"], raw,
                ),
            )
            conn.commit()
        finally:
            conn.close()
    return sku


def load_listing(sku):
    with _lock:
        conn = _connect()
        try:
            row = conn.execute("SELECT raw_json FROM listings WHERE sku = ?", (str(sku),)).fetchone()
        finally:
            conn.close()
    if row is None:
        return None
    return json.loads(row["raw_json"])


def listing_exists(sku):
    with _lock:
        conn = _connect()
        try:
            row = conn.execute("SELECT 1 FROM listings WHERE sku = ?", (str(sku),)).fetchone()
        finally:
            conn.close()
    return row is not None


def list_listings():
    """Return all listings as raw dicts (including hidden ones; callers filter)."""
    with _lock:
        conn = _connect()
        try:
            rows = conn.execute("SELECT raw_json FROM listings").fetchall()
        finally:
            conn.close()
    return [json.loads(row["raw_json"]) for row in rows]


def delete_listing(sku):
    with _lock:
        conn = _connect()
        try:
            cur = conn.execute("DELETE FROM listings WHERE sku = ?", (str(sku),))
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()


# --- logs ---

def insert_log_entry(entry):
    """Insert a log entry dict (with timestamp/event/status plus extra fields)."""
    timestamp = entry.get("timestamp") or datetime.now(timezone.utc).isoformat()
    event = entry.get("event", "")
    status = entry.get("status", "")
    details = json.dumps(entry, ensure_ascii=False)
    with _lock:
        conn = _connect()
        try:
            conn.execute(
                "INSERT INTO logs (timestamp, event, status, details) VALUES (?, ?, ?, ?)",
                (timestamp, event, status, details),
            )
            conn.commit()
        finally:
            conn.close()


def log(event, status, **fields):
    """Append a new log entry and trim the table to MAX_LOG_ENTRIES."""
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "status": status,
        **fields,
    }
    insert_log_entry(entry)
    trim_logs()


def trim_logs():
    """Keep only the newest MAX_LOG_ENTRIES rows."""
    with _lock:
        conn = _connect()
        try:
            conn.execute(
                "DELETE FROM logs WHERE id NOT IN "
                "(SELECT id FROM logs ORDER BY id DESC LIMIT ?)",
                (MAX_LOG_ENTRIES,),
            )
            conn.commit()
        finally:
            conn.close()


def get_logs():
    """Return all log entries as flat dicts, newest first (matches the old
    reversed-ndjson read order)."""
    with _lock:
        conn = _connect()
        try:
            rows = conn.execute("SELECT details FROM logs ORDER BY id DESC").fetchall()
        finally:
            conn.close()
    logs = []
    for row in rows:
        try:
            logs.append(json.loads(row["details"]))
        except json.JSONDecodeError:
            continue
    return logs


# --- prompts ---

def save_prompt(name, content):
    """Insert or replace a prompt. name is the path relative to prompts/
    (e.g. 'title/generateTitlePrompt.txt' or 'categorizeImage.txt')."""
    updated_at = datetime.now(timezone.utc).isoformat()
    with _lock:
        conn = _connect()
        try:
            conn.execute(
                "INSERT INTO prompts (name, content, updated_at) VALUES (?, ?, ?) "
                "ON CONFLICT(name) DO UPDATE SET content=excluded.content, "
                "updated_at=excluded.updated_at",
                (name, content, updated_at),
            )
            conn.commit()
        finally:
            conn.close()


def get_prompt(name):
    with _lock:
        conn = _connect()
        try:
            row = conn.execute("SELECT content FROM prompts WHERE name = ?", (name,)).fetchone()
        finally:
            conn.close()
    return row["content"] if row else None


def prompt_exists(name):
    with _lock:
        conn = _connect()
        try:
            row = conn.execute("SELECT 1 FROM prompts WHERE name = ?", (name,)).fetchone()
        finally:
            conn.close()
    return row is not None


def list_prompts(prompt_type):
    """Return sorted .txt filenames directly under prompts/<prompt_type>/
    (matches the old os.listdir of that folder)."""
    prefix = f"{prompt_type}/"
    with _lock:
        conn = _connect()
        try:
            rows = conn.execute(
                "SELECT name FROM prompts WHERE name LIKE ? ORDER BY name",
                (prefix + "%",),
            ).fetchall()
        finally:
            conn.close()
    files = []
    for row in rows:
        rest = row["name"][len(prefix):]
        # only direct children of the type folder, .txt files
        if "/" not in rest and rest.endswith(".txt"):
            files.append(rest)
    return sorted(files)


# --- saved_3d_files ---

def save_saved_3d_file(record):
    """Insert a Saved 3D File record (GLOSSARY: "Saved 3D File") and return its id.
    created_at is stamped here (UTC ISO) when not supplied."""
    created_at = record.get("created_at") or datetime.now(timezone.utc).isoformat()
    with _lock:
        conn = _connect()
        try:
            cur = conn.execute(
                """
                INSERT INTO saved_3d_files (
                    ebay_listing_url, ebay_listing_title, source_site, source_url,
                    match_label, pipeline, file_path, images_dir, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.get("ebay_listing_url"),
                    record.get("ebay_listing_title"),
                    record.get("source_site"),
                    record.get("source_url"),
                    record.get("match_label"),
                    record.get("pipeline"),
                    record.get("file_path"),
                    record.get("images_dir"),
                    created_at,
                ),
            )
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()


def _saved_3d_file_row(row):
    return {
        "id": row["id"],
        "ebay_listing_url": row["ebay_listing_url"],
        "ebay_listing_title": row["ebay_listing_title"],
        "source_site": row["source_site"],
        "source_url": row["source_url"],
        "match_label": row["match_label"],
        "pipeline": row["pipeline"],
        "file_path": row["file_path"],
        "images_dir": row["images_dir"],
        "created_at": row["created_at"],
    }


def get_saved_3d_file(entry_id):
    with _lock:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT * FROM saved_3d_files WHERE id = ?", (entry_id,)
            ).fetchone()
        finally:
            conn.close()
    if row is None:
        return None
    return _saved_3d_file_row(row)


def list_saved_3d_files(page=1, page_size=25):
    """Paginated Saved 3D File records, newest first. Returns a dict with
    items/total/page/page_size."""
    page = max(1, int(page))
    page_size = max(1, int(page_size))
    offset = (page - 1) * page_size
    with _lock:
        conn = _connect()
        try:
            total = conn.execute("SELECT COUNT(*) AS n FROM saved_3d_files").fetchone()["n"]
            rows = conn.execute(
                "SELECT * FROM saved_3d_files ORDER BY id DESC LIMIT ? OFFSET ?",
                (page_size, offset),
            ).fetchall()
        finally:
            conn.close()
    return {
        "items": [_saved_3d_file_row(row) for row in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def update_saved_3d_file_paths(entry_id, file_path=None, images_dir=None):
    """Update the on-disk paths of a Saved 3D File after its files are written."""
    with _lock:
        conn = _connect()
        try:
            conn.execute(
                "UPDATE saved_3d_files SET file_path = COALESCE(?, file_path), "
                "images_dir = COALESCE(?, images_dir) WHERE id = ?",
                (file_path, images_dir, entry_id),
            )
            conn.commit()
        finally:
            conn.close()


def delete_saved_3d_file(entry_id):
    with _lock:
        conn = _connect()
        try:
            cur = conn.execute("DELETE FROM saved_3d_files WHERE id = ?", (entry_id,))
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()


# --- migration ---

def migrate_from_json():
    """One-time import of existing JSON files into the database. Files are kept."""
    counts = {"preferences": 0, "listings": 0, "logs": 0, "prompts": 0}

    config_path = os.path.join(PROJECT_ROOT, CONFIG_FILE)
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            for key, value in config.items():
                set_preference(key, value)
                counts["preferences"] += 1
        except Exception as e:
            print(f"[migration] could not import {CONFIG_FILE}: {e}")

    listings_dir = os.path.join(PROJECT_ROOT, GENERATED_LISTINGS_DIR)
    if os.path.isdir(listings_dir):
        for name in sorted(os.listdir(listings_dir)):
            if not name.endswith(".json"):
                continue
            try:
                with open(os.path.join(listings_dir, name), "r", encoding="utf-8") as f:
                    data = json.load(f)
                save_listing(data, filename=name)
                counts["listings"] += 1
            except Exception as e:
                print(f"[migration] could not import listing {name}: {e}")

    log_path = os.path.join(PROJECT_ROOT, LOG_FILE_NAME)
    if os.path.exists(log_path):
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    insert_log_entry(entry)
                    counts["logs"] += 1
            trim_logs()
        except Exception as e:
            print(f"[migration] could not import {LOG_FILE_NAME}: {e}")

    prompts_dir = os.path.join(PROJECT_ROOT, PROMPTS_DIR)
    if os.path.isdir(prompts_dir):
        for root, _dirs, files in os.walk(prompts_dir):
            for name in sorted(files):
                if not name.endswith(".txt"):
                    continue
                fpath = os.path.join(root, name)
                rel = os.path.relpath(fpath, prompts_dir).replace(os.sep, "/")
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        content = f.read()
                    save_prompt(rel, content)
                    counts["prompts"] += 1
                except Exception as e:
                    print(f"[migration] could not import prompt {rel}: {e}")

    print(f"[migration] axis.db migration complete: {counts}")
    return counts
