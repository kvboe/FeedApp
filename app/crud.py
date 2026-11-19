from datetime import datetime, time, timedelta, tzinfo
from typing import Any

from app.database import get_connection
from app.utils import now_iso, parse_iso, to_iso

# All timestamps are stored as normalised UTC strings ("YYYY-MM-DDTHH:MM:SS+00:00",
# enforced by utils.to_iso and the startup migration), so plain string comparison
# orders them chronologically and lets SQLite use the created_at indexes.


class SleepStateConflict(Exception):
    """Raised when a start/stop request does not match the current sleep state."""


def _row(row: Any) -> dict[str, Any] | None:
    return dict(row) if row else None


# ---------------------------------------------------------------- settings


def get_setting(key: str) -> str | None:
    with get_connection() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = ?;", (key,)).fetchone()
    return row["value"] if row else None


def set_setting(key: str, value: str | None) -> None:
    with get_connection() as conn:
        if value is None:
            conn.execute("DELETE FROM settings WHERE key = ?;", (key,))
        else:
            conn.execute(
                """
                INSERT INTO settings (key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value;
                """,
                (key, value),
            )


# ----------------------------------------------------------------- entries


def get_entries(
    limit: int = 30,
    before: tuple[str, int] | None = None,
    start: str | None = None,
    end: str | None = None,
    event_type: str | None = None,
) -> tuple[list[dict[str, Any]], bool]:
    """Newest-first page of events using keyset pagination.

    `before` is the (created_at, id) of the last row of the previous page, so
    rows inserted or deleted meanwhile never shift items across pages.
    `start` (inclusive) and `end` (exclusive) are normalised UTC ISO strings.
    One extra row is fetched so `time_since_prev` is correct for the last item
    and so we know whether more rows exist.
    """
    clauses: list[str] = []
    params: list[Any] = []
    if before:
        clauses.append("(created_at < ? OR (created_at = ? AND id < ?))")
        params.extend([before[0], before[0], before[1]])
    if start:
        clauses.append("created_at >= ?")
        params.append(start)
    if end:
        clauses.append("created_at < ?")
        params.append(end)
    if event_type in ("feed", "sleep", "weight"):
        clauses.append("type = ?")
        params.append(event_type)

    query = "SELECT * FROM events"
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY created_at DESC, id DESC LIMIT ?;"
    params.append(limit + 1)

    with get_connection() as conn:
        rows = [dict(r) for r in conn.execute(query, params).fetchall()]

    for curr, prev in zip(rows, rows[1:]):
        try:
            diff = parse_iso(curr["created_at"]) - parse_iso(prev["created_at"])
            curr["time_since_prev"] = int(diff.total_seconds())
        except (ValueError, TypeError):
            curr["time_since_prev"] = None

    return rows[:limit], len(rows) > limit


def get_entry(entry_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        return _row(conn.execute("SELECT * FROM events WHERE id = ?;", (entry_id,)).fetchone())


def create_feed(
    subtype: str, side: str | None, amount_ml: int, notes: str | None, created_at: str
) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO events (type, subtype, side, amount_ml, notes, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?);",
            ("feed", subtype, side, amount_ml, notes, created_at),
        )
        return int(cur.lastrowid)


def create_weight(weight_g: int, notes: str | None, created_at: str) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO events (type, amount_ml, notes, created_at) VALUES (?, ?, ?, ?);",
            ("weight", weight_g, notes, created_at),
        )
        return int(cur.lastrowid)


def delete_event(entry_id: int) -> bool:
    with get_connection() as conn:
        cur = conn.execute("DELETE FROM events WHERE id = ?;", (entry_id,))
        return cur.rowcount > 0


def update_event(entry_id: int, fields: dict[str, Any]) -> None:
    if not fields:
        return
    cols = ", ".join(f"{k} = ?" for k in fields)
    with get_connection() as conn:
        conn.execute(f"UPDATE events SET {cols} WHERE id = ?;", (*fields.values(), entry_id))


# ------------------------------------------------------------------- sleep


def get_sleep_state() -> dict[str, Any]:
    with get_connection() as conn:
        row = conn.execute("SELECT started_at FROM sleep_state WHERE id = 1;").fetchone()
    return {"active": bool(row), "started_at": row["started_at"] if row else None}


def start_sleep() -> dict[str, Any]:
    now = now_iso()
    with get_connection() as conn:
        # Take the write lock before reading so concurrent requests serialise.
        conn.execute("BEGIN IMMEDIATE;")
        if conn.execute("SELECT 1 FROM sleep_state WHERE id = 1;").fetchone():
            raise SleepStateConflict("Sleep is already in progress")
        conn.execute("INSERT INTO sleep_state (id, started_at) VALUES (1, ?);", (now,))
    return {"active": True, "started_at": now, "entry_id": None}


def stop_sleep(notes: str | None) -> dict[str, Any]:
    now = now_iso()
    with get_connection() as conn:
        conn.execute("BEGIN IMMEDIATE;")
        row = conn.execute("SELECT started_at FROM sleep_state WHERE id = 1;").fetchone()
        if not row:
            raise SleepStateConflict("No sleep in progress")
        started_at = row["started_at"]
        duration = int((parse_iso(now) - parse_iso(started_at)).total_seconds())
        cur = conn.execute(
            """
            INSERT INTO events (type, duration_sec, started_at, ended_at, notes, created_at)
            VALUES ('sleep', ?, ?, ?, ?, ?);
            """,
            (max(duration, 0), started_at, now, notes, now),
        )
        conn.execute("DELETE FROM sleep_state WHERE id = 1;")
        entry_id = int(cur.lastrowid)
    return {"active": False, "started_at": None, "entry_id": entry_id}


# ----------------------------------------------------------------- summary


def _latest(conn: Any, event_type: str) -> dict[str, Any] | None:
    return _row(
        conn.execute(
            "SELECT * FROM events WHERE type = ? ORDER BY created_at DESC, id DESC LIMIT 1;",
            (event_type,),
        ).fetchone()
    )


def get_week(tz: tzinfo) -> list[dict[str, Any]]:
    """Feed totals for the last 7 local days in timezone `tz`.

    Each feed is converted with the zone's rules for *its own* instant, so
    weeks crossing a DST change bucket correctly.
    """
    today = datetime.now(tz).date()
    days = [today - timedelta(days=i) for i in range(6, -1, -1)]
    start_utc = to_iso(datetime.combine(days[0], time(), tzinfo=tz))
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT amount_ml, created_at FROM events WHERE type = 'feed' AND created_at >= ?;",
            (start_utc,),
        ).fetchall()

    totals = {d: [0, 0] for d in days}
    for r in rows:
        try:
            local_day = parse_iso(r["created_at"]).astimezone(tz).date()
        except (ValueError, TypeError):
            continue
        if local_day in totals:
            totals[local_day][0] += r["amount_ml"] or 0
            totals[local_day][1] += 1
    return [{"date": d.isoformat(), "total_ml": t[0], "count": t[1]} for d, t in totals.items()]


def get_summary(tz: tzinfo) -> dict[str, Any]:
    with get_connection() as conn:
        last_feed = _latest(conn, "feed")
        last_breast = _row(
            conn.execute(
                "SELECT * FROM events WHERE type = 'feed' AND subtype = 'breast_milk'"
                " AND side IS NOT NULL ORDER BY created_at DESC, id DESC LIMIT 1;"
            ).fetchone()
        )
        last_sleep = _latest(conn, "sleep")
        last_weight = _latest(conn, "weight")
    return {
        "last_feed": last_feed,
        "last_breast": last_breast,
        "last_sleep": last_sleep,
        "last_weight": last_weight,
        "sleep": get_sleep_state(),
        "week": get_week(tz),
        "birthdate": get_setting("birthdate"),
    }
