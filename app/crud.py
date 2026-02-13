import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any

from app.database import get_connection
from app.utils import now_iso


def get_setting(key: str) -> str | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT value FROM settings WHERE key = ?;", (key,)
        ).fetchone()
    return row["value"] if row else None


def set_setting(key: str, value: str) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO settings (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value;
            """,
            (key, value),
        )
        conn.commit()


def get_entries(
    limit: int = 20,
    start_date: str | None = None,
    end_date: str | None = None,
    event_type: str | None = None,
) -> list[dict[str, Any]]:
    query = "SELECT * FROM events"
    clauses: list[str] = []
    params: list[Any] = []

    if start_date:
        clauses.append("date(created_at) >= date(?)")
        params.append(start_date)
    if end_date:
        clauses.append("date(created_at) <= date(?)")
        params.append(end_date)
    if event_type and event_type in ("feed", "sleep"):
        clauses.append("type = ?")
        params.append(event_type)

    if clauses:
        query += " WHERE " + " AND ".join(clauses)

    query += " ORDER BY datetime(created_at) DESC LIMIT ?;"
    params.append(limit)

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()

    entries = [dict(row) for row in rows]
    for i in range(len(entries) - 1):
        curr_entry = entries[i]
        prev_entry = entries[i + 1]
        try:
            curr_dt = datetime.fromisoformat(curr_entry["created_at"])
            prev_dt = datetime.fromisoformat(prev_entry["created_at"])
            if curr_dt.tzinfo is None:
                curr_dt = curr_dt.replace(tzinfo=timezone.utc)
            if prev_dt.tzinfo is None:
                prev_dt = prev_dt.replace(tzinfo=timezone.utc)

            diff = int((curr_dt - prev_dt).total_seconds())
            curr_entry["time_since_prev"] = diff
        except (ValueError, TypeError):
            pass

    return entries


def get_sleep_state() -> dict[str, Any]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT started_at FROM sleep_state WHERE id = 1;"
        ).fetchone()
    if not row:
        return {"active": False, "started_at": None}
    return {"active": True, "started_at": row["started_at"]}


def get_daily_chart_data() -> dict[str, list[Any]]:
    labels = []
    data_points = []

    # Last 7 days including today
    today = datetime.now(timezone.utc).date()
    dates = [(today - timedelta(days=i)) for i in range(6, -1, -1)]

    with get_connection() as conn:
        for d in dates:
            d_str = d.strftime("%Y-%m-%d")
            row = conn.execute(
                """
                SELECT SUM(amount_ml) as total
                FROM events
                WHERE type='feed' AND date(created_at) = ?
                """,
                (d_str,),
            ).fetchone()
            total = row["total"] or 0

            labels.append(d.strftime("%a"))  # Mon, Tue...
            data_points.append(total)

    return {"labels": labels, "data": data_points}


def get_stats() -> dict[str, Any]:
    now_dt = datetime.now(timezone.utc)
    with get_connection() as conn:
        last_feed = conn.execute(
            """
            SELECT amount_ml, subtype, created_at
            FROM events
            WHERE type = 'feed'
            ORDER BY datetime(created_at) DESC
            LIMIT 1;
            """
        ).fetchone()
        last_sleep = conn.execute(
            """
            SELECT duration_sec, ended_at
            FROM events
            WHERE type = 'sleep'
            ORDER BY datetime(created_at) DESC
            LIMIT 1;
            """
        ).fetchone()
        last_weight = conn.execute(
            """
            SELECT amount_ml, created_at
            FROM events
            WHERE type = 'weight'
            ORDER BY datetime(created_at) DESC
            LIMIT 1;
            """
        ).fetchone()
        sleep_row = conn.execute(
            "SELECT started_at FROM sleep_state WHERE id = 1;"
        ).fetchone()

    sleep_active = False
    current_sleep_duration = None
    sleep_started_at = None
    if sleep_row:
        sleep_active = True
        sleep_started_at = sleep_row["started_at"]
        try:
            started_dt = datetime.fromisoformat(sleep_started_at)
            current_sleep_duration = int((now_dt - started_dt).total_seconds())
        except ValueError:
            current_sleep_duration = None

    return {
        "last_feed": last_feed,
        "last_sleep": last_sleep,
        "last_weight": last_weight,
        "sleep_active": sleep_active,
        "sleep_started_at": sleep_started_at,
        "current_sleep_duration": current_sleep_duration,
    }


def get_entry(entry_id: int) -> sqlite3.Row | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM events WHERE id = ?;",
            (entry_id,),
        ).fetchone()
    return row


def create_feed(subtype: str, amount_ml: int, notes: str, created_at: str) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO events (type, subtype, amount_ml, notes, created_at)
            VALUES (?, ?, ?, ?, ?);
            """,
            ("feed", subtype, amount_ml, notes, created_at),
        )
        conn.commit()


def create_weight(weight_g: int, notes: str, created_at: str) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO events (type, amount_ml, notes, created_at)
            VALUES (?, ?, ?, ?);
            """,
            ("weight", weight_g, notes, created_at),
        )
        conn.commit()


def delete_event(entry_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM events WHERE id = ?", (entry_id,))
        conn.commit()


def update_feed_event(
    entry_id: int, amount_ml: int, subtype: str, notes: str | None, created_at: str
) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE events
            SET amount_ml = ?, subtype = ?, notes = ?, created_at = ?
            WHERE id = ?;
            """,
            (amount_ml, subtype, notes, created_at, entry_id),
        )
        conn.commit()


def update_other_event(
    entry_id: int, started_at: str, ended_at: str, duration_sec: int, notes: str | None
) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE events
            SET started_at = ?, ended_at = ?, duration_sec = ?, notes = ?, created_at = ?
            WHERE id = ?;
            """,
            (started_at, ended_at, duration_sec, notes, ended_at, entry_id),
        )
        conn.commit()


def toggle_sleep_state(notes: str) -> dict[str, Any]:
    # This returns state to help with notifications if needed,
    # but currently UI checks active state after fetch.
    now = now_iso()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT started_at FROM sleep_state WHERE id = 1;"
        ).fetchone()

        sleep_state = {"active": False}

        if row:
            # Wake up
            started_at = row["started_at"]
            started_dt = datetime.fromisoformat(started_at)
            ended_dt = datetime.fromisoformat(now)
            duration_sec = int((ended_dt - started_dt).total_seconds())

            conn.execute(
                """
                INSERT INTO events (type, duration_sec, started_at, ended_at, notes, created_at)
                VALUES (?, ?, ?, ?, ?, ?);
                """,
                (
                    "sleep",
                    duration_sec,
                    started_at,
                    now,
                    notes.strip() or None,
                    now,
                ),
            )
            conn.execute("DELETE FROM sleep_state WHERE id = 1;")
            sleep_state["active"] = False
        else:
            # Start sleep
            conn.execute(
                "INSERT OR REPLACE INTO sleep_state (id, started_at) VALUES (1, ?);",
                (now,),
            )
            sleep_state["active"] = True
        conn.commit()
    return sleep_state
