import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Dict, Iterator, List, Optional, Tuple


def _utc_now_iso() -> str:
    """Return current UTC time as ISO string with 'Z' suffix."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _default_sqlite_path() -> str:
    """
    Compute a safe default SQLite file path within this repository.

    We prefer SQLITE_DB env var (provided by the database container orchestration),
    but fall back to a local file so the backend can still run standalone.
    """
    # notes_backend/src/api/db.py -> notes_backend/
    container_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    return os.path.join(container_root, "notes.db")


# PUBLIC_INTERFACE
def get_sqlite_db_path() -> str:
    """Return the SQLite DB path from SQLITE_DB environment variable or a local fallback."""
    return os.getenv("SQLITE_DB") or _default_sqlite_path()


@contextmanager
def _connect() -> Iterator[sqlite3.Connection]:
    """
    Context manager yielding a sqlite3 connection.

    Uses row_factory so rows can be accessed by column name.
    """
    conn = sqlite3.connect(get_sqlite_db_path(), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        # Always enforce foreign keys as a best practice.
        conn.execute("PRAGMA foreign_keys = ON")
        yield conn
        conn.commit()
    finally:
        conn.close()


# PUBLIC_INTERFACE
def init_db() -> None:
    """Initialize the database schema if it does not already exist."""
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """.strip()
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_notes_updated_at ON notes(updated_at)")


def _row_to_note_dict(row: sqlite3.Row) -> Dict:
    """Convert a sqlite row into an API-friendly dict."""
    return {
        "id": int(row["id"]),
        "title": row["title"],
        "content": row["content"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


# PUBLIC_INTERFACE
def list_notes(limit: int = 100, offset: int = 0, q: Optional[str] = None) -> List[Dict]:
    """Return a list of notes, optionally filtered by a search query."""
    with _connect() as conn:
        params: Tuple = (limit, offset)
        where_clause = ""
        if q:
            where_clause = "WHERE title LIKE ? OR content LIKE ?"
            like = f"%{q}%"
            params = (like, like, limit, offset)

        cur = conn.execute(
            f"""
            SELECT id, title, content, created_at, updated_at
            FROM notes
            {where_clause}
            ORDER BY updated_at DESC, id DESC
            LIMIT ? OFFSET ?
            """.strip(),
            params,
        )
        return [_row_to_note_dict(r) for r in cur.fetchall()]


# PUBLIC_INTERFACE
def get_note(note_id: int) -> Optional[Dict]:
    """Return a single note by id, or None if not found."""
    with _connect() as conn:
        cur = conn.execute(
            """
            SELECT id, title, content, created_at, updated_at
            FROM notes
            WHERE id = ?
            """.strip(),
            (note_id,),
        )
        row = cur.fetchone()
        return _row_to_note_dict(row) if row else None


# PUBLIC_INTERFACE
def create_note(title: str, content: str) -> Dict:
    """Create a new note and return it."""
    now = _utc_now_iso()
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO notes (title, content, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            """.strip(),
            (title, content, now, now),
        )
        note_id = int(cur.lastrowid)
    # Re-read to ensure consistent output
    created = get_note(note_id)
    assert created is not None
    return created


# PUBLIC_INTERFACE
def update_note(note_id: int, title: Optional[str], content: Optional[str]) -> Optional[Dict]:
    """
    Update an existing note. Returns updated note, or None if not found.

    Title/content are partial updates.
    """
    existing = get_note(note_id)
    if not existing:
        return None

    new_title = title if title is not None else existing["title"]
    new_content = content if content is not None else existing["content"]
    now = _utc_now_iso()

    with _connect() as conn:
        conn.execute(
            """
            UPDATE notes
            SET title = ?, content = ?, updated_at = ?
            WHERE id = ?
            """.strip(),
            (new_title, new_content, now, note_id),
        )

    updated = get_note(note_id)
    assert updated is not None
    return updated


# PUBLIC_INTERFACE
def delete_note(note_id: int) -> bool:
    """Delete a note. Returns True if deleted, False if not found."""
    with _connect() as conn:
        cur = conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        return cur.rowcount > 0
