"""Only validated repairs enter reusable repair memory."""
import hashlib
import sqlite3
from pathlib import Path

def init(db: Path) -> None:
    db.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db) as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS repairs (
            id INTEGER PRIMARY KEY, signature TEXT NOT NULL UNIQUE,
            failure_excerpt TEXT NOT NULL, repair_excerpt TEXT NOT NULL,
            validated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")

def remember(db: Path, failure: str, repair: str, *, validated: bool) -> bool:
    if not validated:
        return False
    init(db)
    signature = hashlib.sha256(failure.encode()).hexdigest()
    with sqlite3.connect(db) as conn:
        conn.execute("INSERT OR IGNORE INTO repairs(signature, failure_excerpt, repair_excerpt) VALUES(?,?,?)",
                     (signature, failure[-1500:], repair[-2500:]))
    return True

def examples(db: Path, limit: int = 3) -> list[tuple[str, str]]:
    if not db.exists():
        return []
    with sqlite3.connect(db) as conn:
        return conn.execute("SELECT failure_excerpt, repair_excerpt FROM repairs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
