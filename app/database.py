import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager

from app.config import DB_PATH

_TS_COLUMNS = ("created_at", "started_at", "ended_at")
_CANONICAL_GLOB = "[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]+00:00"


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    """Open a connection, commit on success, roll back on error, always close."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()


def _normalise_timestamps(conn: sqlite3.Connection) -> None:
    """Rewrite any non-canonical timestamps to UTC "…+00:00" (same instant).

    Queries compare created_at as plain strings, which is only chronological
    when every value has the same format. A no-op on already-clean databases.
    """
    from app.utils import parse_iso, to_iso

    for col in _TS_COLUMNS:
        rows = conn.execute(
            f"SELECT id, {col} AS v FROM events WHERE {col} IS NOT NULL AND {col} NOT GLOB ?;",
            (_CANONICAL_GLOB,),
        ).fetchall()
        for r in rows:
            try:
                fixed = to_iso(parse_iso(r["v"]))
            except ValueError:
                continue
            conn.execute(f"UPDATE events SET {col} = ? WHERE id = ?;", (fixed, r["id"]))


def init_db() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                subtype TEXT,
                amount_ml INTEGER,
                duration_sec INTEGER,
                started_at TEXT,
                ended_at TEXT,
                notes TEXT,
                created_at TEXT NOT NULL
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sleep_state (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                started_at TEXT NOT NULL
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            );
            """
        )
        # Migrations for older setups: subtype (v1), breast side (v2)
        for column in ("subtype", "side"):
            try:
                conn.execute(f"ALTER TABLE events ADD COLUMN {column} TEXT;")
            except sqlite3.OperationalError:
                pass
        _normalise_timestamps(conn)
        # (created_at) serves history paging; (type, created_at) serves
        # type-filtered history and the "latest feed/sleep/weight" lookups.
        conn.execute("CREATE INDEX IF NOT EXISTS idx_events_created ON events(created_at);")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_events_type_created ON events(type, created_at);"
        )
