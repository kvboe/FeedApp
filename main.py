from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

APP_NAME = "FeedApp"
DB_PATH = Path(os.getenv("DB_PATH", "/data/feedapp.db"))

app = FastAPI(title=APP_NAME)
BASE_DIR = Path(__file__).parent

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
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
        # Ensure subtype column exists
        try:
            conn.execute("ALTER TABLE events ADD COLUMN subtype TEXT;")
        except sqlite3.OperationalError:
            pass  # column likely exists

        conn.commit()


@app.on_event("startup")
def on_startup() -> None:
    _init_db()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _get_setting(key: str) -> str | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT value FROM settings WHERE key = ?;", (key,)
        ).fetchone()
    return row["value"] if row else None


def _set_setting(key: str, value: str) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO settings (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value;
            """,
            (key, value),
        )
        conn.commit()


def _get_entries(
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

    with _connect() as conn:
        rows = conn.execute(query, params).fetchall()
    
    entries = [dict(row) for row in rows]
    for i in range(len(entries) - 1):
        curr_entry = entries[i]
        prev_entry = entries[i+1]
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


def _get_sleep_state() -> dict[str, Any]:
    with _connect() as conn:
        row = conn.execute(
            "SELECT started_at FROM sleep_state WHERE id = 1;"
        ).fetchone()
    if not row:
        return {"active": False, "started_at": None}
    return {"active": True, "started_at": row["started_at"]}


def _get_daily_chart_data() -> dict[str, list[Any]]:
    labels = []
    data_points = []

    # Last 7 days including today
    today = datetime.now(timezone.utc).date()
    dates = [(today - timedelta(days=i)) for i in range(6, -1, -1)]

    with _connect() as conn:
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


def _get_stats() -> dict[str, Any]:
    now_dt = datetime.now(timezone.utc)
    with _connect() as conn:
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


def _format_duration(seconds: int | None) -> str:
    if not seconds:
        return "0m"
    minutes = seconds // 60
    hours = minutes // 60
    minutes = minutes % 60
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def _format_since(value: str | None) -> str:
    if not value:
        return ""
    try:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return ""
    delta = datetime.now(timezone.utc) - dt
    seconds = max(0, int(delta.total_seconds()))
    return _format_duration(seconds)


def _format_datetime(value: str | None, offset_minutes: int = 0) -> str:
    if not value:
        return ""
    try:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        # offset is (UTC - Local), so Local = UTC - offset
        local_dt = dt - timedelta(minutes=offset_minutes)
        return local_dt.strftime("%b %d, %H:%M")
    except ValueError:
        return value


def _format_datetime_input(value: str | None, offset_minutes: int = 0) -> str:
    if not value:
        return ""
    try:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        local_dt = dt - timedelta(minutes=offset_minutes)
    except ValueError:
        return ""
    return local_dt.strftime("%Y-%m-%dT%H:%M")


def _format_date_input(value: str | None, offset_minutes: int = 0) -> str:
    if not value:
        return ""
    try:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        local_dt = dt - timedelta(minutes=offset_minutes)
    except ValueError:
        return ""
    return local_dt.strftime("%Y-%m-%d")


def _format_time_input(value: str | None, offset_minutes: int = 0) -> str:
    if not value:
        return ""
    try:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        local_dt = dt - timedelta(minutes=offset_minutes)
    except ValueError:
        return ""
    return local_dt.strftime("%H:%M")


def _parse_datetime_input(
    value: str | None, fallback: datetime, offset_minutes: int = 0
) -> str:
    # offset_minutes is timezone difference in minutes (e.g. UTC+1 = -60)
    # We add it to convert Local -> UTC.
    if value:
        try:
            dt = datetime.fromisoformat(value)
            # If naive, assume it's local time from client
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc) + timedelta(minutes=offset_minutes)
            return dt.isoformat(timespec="seconds")
        except ValueError:
            pass
    return fallback.isoformat(timespec="seconds")


def _parse_date_time_input(
    date_value: str | None,
    time_value: str | None,
    fallback: datetime,
    offset_minutes: int = 0,
) -> str:
    date_value = (date_value or "").strip()
    time_value = (time_value or "").strip()
    if not date_value and not time_value:
        return fallback.isoformat(timespec="seconds")

    if not date_value:
        date_value = fallback.strftime("%Y-%m-%d")
    if not time_value:
        time_value = fallback.strftime("%H:%M")

    try:
        dt = datetime.fromisoformat(f"{date_value}T{time_value}")
        # Convert Local -> UTC using offset
        dt = dt.replace(tzinfo=timezone.utc) + timedelta(minutes=offset_minutes)
        return dt.isoformat(timespec="seconds")
    except ValueError:
        return fallback.isoformat(timespec="seconds")


def _get_ui_helpers(request: Request) -> dict[str, Any]:
    try:
        offset = int(request.cookies.get("timezone_offset", "0"))
    except ValueError:
        offset = 0

    return {
        "timezone_offset": offset,
        "format_duration": _format_duration,
        "format_since": _format_since,
        "format_datetime": lambda v: _format_datetime(v, offset),
        "format_datetime_input": lambda v: _format_datetime_input(v, offset),
        "format_date_input": lambda v: _format_date_input(v, offset),
        "format_time_input": lambda v: _format_time_input(v, offset),
    }


def _get_entry(entry_id: int) -> sqlite3.Row | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM events WHERE id = ?;",
            (entry_id,),
        ).fetchone()
    return row


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    start_date = request.query_params.get("start_date") or None
    end_date = request.query_params.get("end_date") or None
    sleep_state = _get_sleep_state()
    stats = _get_stats()
    chart_data = _get_daily_chart_data()

    birthdate_str = _get_setting("birthdate")
    age_days = None
    if birthdate_str:
        try:
            birth_date = datetime.strptime(birthdate_str, "%Y-%m-%d").date()
            age_days = (datetime.now(timezone.utc).date() - birth_date).days
        except ValueError:
            pass

    ctx = _get_ui_helpers(request)
    ctx.update(
        {
            "request": request,
            "sleep_state": sleep_state,
            "stats": stats,
            "chart_data": chart_data,
            "age_days": age_days,
            "start_date": start_date or "",
            "end_date": end_date or "",
            "active_page": "home",
            "app_name": APP_NAME,
        }
    )
    return templates.TemplateResponse("index.html", ctx)


@app.get("/history", response_class=HTMLResponse)
def history(request: Request) -> HTMLResponse:
    start_date = request.query_params.get("start_date") or None
    end_date = request.query_params.get("end_date") or None
    event_type = request.query_params.get("type") or None
    entries = _get_entries(
        start_date=start_date, end_date=end_date, event_type=event_type
    )
    ctx = _get_ui_helpers(request)
    ctx.update(
        {
            "request": request,
            "entries": entries,
            "start_date": start_date or "",
            "end_date": end_date or "",
            "event_type": event_type or "",
            "active_page": "history",
            "app_name": APP_NAME,
        }
    )
    return templates.TemplateResponse("history.html", ctx)


@app.get("/stats", response_class=HTMLResponse)
def stats_partial(request: Request) -> HTMLResponse:
    stats = _get_stats()
    ctx = _get_ui_helpers(request)
    ctx.update(
        {
            "request": request,
            "stats": stats,
            "stats_oob": False,
        }
    )
    return templates.TemplateResponse("_stats.html", ctx)


@app.get("/entries", response_class=HTMLResponse)
def entries_partial(request: Request) -> HTMLResponse:
    start_date = request.query_params.get("start_date") or None
    end_date = request.query_params.get("end_date") or None
    event_type = request.query_params.get("type") or None
    entries = _get_entries(
        start_date=start_date, end_date=end_date, event_type=event_type
    )
    ctx = _get_ui_helpers(request)
    ctx.update(
        {
            "request": request,
            "entries": entries,
            "start_date": start_date or "",
            "end_date": end_date or "",
            "event_type": event_type or "",
        }
    )
    return templates.TemplateResponse("_entries.html", ctx)


@app.post("/feed", response_class=HTMLResponse)
def log_feed(
    request: Request,
    amount_ml: int = Form(120),
    subtype: str = Form("formula"),
    notes: str = Form(""),
    created_at: str = Form(""),
    created_date: str = Form(""),
    created_time: str = Form(""),
    minutes_ago: int = Form(0),
    timezone_offset: int = Form(0),
    start_date: str = Form(""),
    end_date: str = Form(""),
) -> HTMLResponse:
    now_dt = datetime.now(timezone.utc)
    created_at_dt = now_dt - timedelta(minutes=minutes_ago or 0)
    if created_date or created_time:
        created_at = _parse_date_time_input(
            created_date, created_time, created_at_dt, timezone_offset
        )
    else:
        created_at = _parse_datetime_input(created_at, created_at_dt, timezone_offset)
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO events (type, subtype, amount_ml, notes, created_at)
            VALUES (?, ?, ?, ?, ?);
            """,
            ("feed", subtype, amount_ml, notes.strip() or None, created_at),
        )
        conn.commit()

    entries = _get_entries(
        start_date=start_date or None,
        end_date=end_date or None,
    )
    stats = _get_stats()
    ctx = _get_ui_helpers(request)
    ctx.update(
        {
            "request": request,
            "entries": entries,
            "stats": stats,
            "stats_oob": False,
            "start_date": start_date or "",
            "end_date": end_date or "",
        }
    )
    response = templates.TemplateResponse("_feed_response.html", ctx)
    response.headers["HX-Trigger"] = '{"showToast": "Feed logged!"}'
    return response


@app.post("/sleep/toggle", response_class=HTMLResponse)
def toggle_sleep(
    request: Request,
    notes: str = Form(""),
    start_date: str = Form(""),
    end_date: str = Form(""),
) -> HTMLResponse:
    now = _now_iso()
    with _connect() as conn:
        row = conn.execute(
            "SELECT started_at FROM sleep_state WHERE id = 1;"
        ).fetchone()
        if row:
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
        else:
            conn.execute(
                "INSERT OR REPLACE INTO sleep_state (id, started_at) VALUES (1, ?);",
                (now,),
            )
        conn.commit()

    entries = _get_entries(
        start_date=start_date or None,
        end_date=end_date or None,
    )
    sleep_state = _get_sleep_state()
    stats = _get_stats()

    ctx = _get_ui_helpers(request)
    ctx.update(
        {
            "request": request,
            "entries": entries,
            "sleep_state": sleep_state,
            "stats": stats,
            "stats_oob": True,
            "start_date": start_date or "",
            "end_date": end_date or "",
            "oob": True,
        }
    )
    response = templates.TemplateResponse("_sleep_toggle_response.html", ctx)
    if sleep_state["active"]:
        response.headers["HX-Trigger"] = '{"showToast": "Sleep started..."}'
    else:
        response.headers["HX-Trigger"] = '{"showToast": "Sleep logged !"}'
    return response


@app.get("/entries/{entry_id}/edit", response_class=HTMLResponse)
def edit_entry(entry_id: int, request: Request) -> HTMLResponse:
    entry = _get_entry(entry_id)
    if not entry:
        return HTMLResponse(status_code=404, content="Not found")
    ctx = _get_ui_helpers(request)
    ctx.update(
        {
            "request": request,
            "entry": entry,
        }
    )
    return templates.TemplateResponse("_entry_edit.html", ctx)


@app.post("/entries/{entry_id}", response_class=HTMLResponse)
def update_entry(
    entry_id: int,
    request: Request,
    amount_ml: int | None = Form(None),
    subtype: str | None = Form(None),
    created_at: str = Form(""),
    created_date: str = Form(""),
    created_time: str = Form(""),
    started_at: str = Form(""),
    started_date: str = Form(""),
    started_time: str = Form(""),
    ended_at: str = Form(""),
    ended_date: str = Form(""),
    ended_time: str = Form(""),
    notes: str = Form(""),
    timezone_offset: int = Form(0),
) -> HTMLResponse:
    entry = _get_entry(entry_id)
    if not entry:
        return HTMLResponse(status_code=404, content="Not found")
    now_dt = datetime.now(timezone.utc)

    if entry["type"] == "feed":
        amount = amount_ml if amount_ml is not None else entry["amount_ml"]
        subtype_val = (
            subtype
            if subtype is not None
            else (entry["subtype"] if "subtype" in entry.keys() else None)
        )
        if created_date or created_time:
            created_at_value = _parse_date_time_input(
                created_date, created_time, now_dt, timezone_offset
            )
        else:
            created_at_value = _parse_datetime_input(
                created_at, now_dt, timezone_offset
            )
        with _connect() as conn:
            conn.execute(
                """
                UPDATE events
                SET amount_ml = ?, subtype = ?, notes = ?, created_at = ?
                WHERE id = ?;
                """,
                (
                    amount,
                    subtype_val,
                    notes.strip() or None,
                    created_at_value,
                    entry_id,
                ),
            )
            conn.commit()
    else:
        if started_date or started_time:
            started_at = _parse_date_time_input(
                started_date, started_time, now_dt, timezone_offset
            )
        else:
            started_at = _parse_datetime_input(started_at, now_dt, timezone_offset)

        if ended_date or ended_time:
            ended_at = _parse_date_time_input(
                ended_date, ended_time, now_dt, timezone_offset
            )
        else:
            ended_at = _parse_datetime_input(ended_at, now_dt, timezone_offset)
        started_dt = datetime.fromisoformat(started_at)
        ended_dt = datetime.fromisoformat(ended_at)
        if ended_dt < started_dt:
            ended_dt = started_dt
            ended_at = ended_dt.isoformat(timespec="seconds")
        duration_sec = int((ended_dt - started_dt).total_seconds())
        with _connect() as conn:
            conn.execute(
                """
                UPDATE events
                SET started_at = ?, ended_at = ?, duration_sec = ?, notes = ?, created_at = ?
                WHERE id = ?;
                """,
                (
                    started_at,
                    ended_at,
                    duration_sec,
                    notes.strip() or None,
                    ended_at,
                    entry_id,
                ),
            )
            conn.commit()

    updated = _get_entry(entry_id)
    stats = _get_stats()
    ctx = _get_ui_helpers(request)
    ctx.update(
        {
            "request": request,
            "entry": updated,
            "stats": stats,
            "stats_oob": True,
        }
    )
    response = templates.TemplateResponse("_entry_update_response.html", ctx)
    response.headers["HX-Trigger"] = '{"showToast": "Entry updated!"}'
    return response


@app.delete("/entries/{entry_id}", response_class=HTMLResponse)
def delete_entry(entry_id: int) -> HTMLResponse:
    with _connect() as conn:
        conn.execute("DELETE FROM events WHERE id = ?", (entry_id,))
        conn.commit()
    response = HTMLResponse(status_code=200, content="")
    response.headers["HX-Trigger"] = '{"showToast": "Entry deleted!"}'
    return response


@app.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request) -> HTMLResponse:
    birthdate = _get_setting("birthdate") or ""
    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "birthdate": birthdate,
            "active_page": "settings",
            "app_name": APP_NAME,
        },
    )


@app.post("/settings", response_class=HTMLResponse)
def save_settings(request: Request, birthdate: str = Form("")) -> HTMLResponse:
    if birthdate:
        _set_setting("birthdate", birthdate)
    return settings_page(request)


@app.post("/weight", response_class=HTMLResponse)
def log_weight(
    request: Request,
    weight_g: int = Form(...),
    notes: str = Form(""),
    created_at: str = Form(""),
    timezone_offset: int = Form(0),
) -> HTMLResponse:
    now_dt = datetime.now(timezone.utc)
    created_at = _parse_datetime_input(created_at, now_dt, timezone_offset)

    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO events (type, amount_ml, notes, created_at)
            VALUES (?, ?, ?, ?);
            """,
            ("weight", weight_g, notes.strip() or None, created_at),
        )
        conn.commit()

    # Return stats or empty response, for now just empty to close modal/reset form if we use one
    # Or simpler: redirect to home or return feed response (which reloads list)
    # Let's return the updated feed/history list if we want to show it there.
    # For now, let's just return a success indicator or reload the page.
    # Actually, if called from index, we might want to reload stats or something.
    # Let's just return 200 OK for now and let HTMX handle it.

    response = HTMLResponse(
        status_code=200, content="<script>window.location.reload()</script>"
    )
    response.headers["HX-Trigger"] = '{"showToast": "Weight logged!"}'
    return response
