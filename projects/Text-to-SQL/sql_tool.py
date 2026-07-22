"""
Safe, read-only SQL execution against the user's local database.

Two layers of protection, because LLM-generated SQL must never be trusted
to modify data:
  1. SELECT-only check on the query string
  2. the SQLite connection is opened read-only at the OS level (mode=ro)
"""

import sqlite3
from pathlib import Path

from config import DB_FILENAME

DB_PATH = Path(__file__).parent / DB_FILENAME


def db_exists() -> bool:
    return DB_PATH.exists()


def run_sql(query: str):
    """
    Returns (success: bool, result_rows: list | None, message: str).
    On success, result_rows is the actual returned rows (capped).
    On failure, result_rows is None and message explains why.
    """
    stripped = query.strip().lstrip("(").strip()
    if not stripped.upper().startswith("SELECT"):
        return False, None, "rejected: only SELECT statements are allowed"

    try:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, timeout=10)
        cur = conn.cursor()
        cur.execute(query)
        rows = cur.fetchmany(50)
        conn.close()
        if not rows:
            return True, [], "(query succeeded, no rows returned)"
        return True, rows, "ok"
    except sqlite3.Error as e:
        return False, None, f"SQL error: {e}"


def format_rows(rows) -> str:
    if not rows:
        return "(no rows)"
    return "\n".join(str(r) for r in rows[:20])
