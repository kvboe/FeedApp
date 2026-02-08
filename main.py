from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timedelta
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
        conn.commit()


@app.on_event("startup")
def on_startup() -> None:
    _init_db()


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _get_entries(
    limit: int = 10,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[sqlite3.Row]:
    query = "SELECT * FROM events"
    clauses: list[str] = []
    params: list[Any] = []

    if start_date:
        clauses.append("date(created_at) >= date(?)")
        params.append(start_date)
    if end_date:
        clauses.append("date(created_at) <= date(?)")
        params.append(end_date)

    if clauses:
        query += " WHERE " + " AND ".join(clauses)

    query += " ORDER BY datetime(created_at) DESC LIMIT ?;"
    params.append(limit)

    with _connect() as conn:
        rows = conn.execute(query, params).fetchall()
    return list(rows)


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
    today = datetime.now().date()
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
    now_dt = datetime.now()
    with _connect() as conn:
        last_feed = conn.execute(
            """
            SELECT amount_ml, created_at
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
    except ValueError:
        return ""
    delta = datetime.now() - dt
    seconds = max(0, int(delta.total_seconds()))
    return _format_duration(seconds)


def _format_datetime(value: str | None) -> str:
    if not value:
        return ""
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return value
    return dt.strftime("%d %b %Y, %H:%M")


def _format_datetime_input(value: str | None) -> str:
    if not value:
        return ""
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return ""
    return dt.strftime("%Y-%m-%dT%H:%M")


def _format_date_input(value: str | None) -> str:
    if not value:
        return ""
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return ""
    return dt.strftime("%Y-%m-%d")


def _format_time_input(value: str | None) -> str:
    if not value:
        return ""
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return ""
    return dt.strftime("%H:%M")


def _parse_datetime_input(value: str | None, fallback: datetime) -> str:
    if value:
        try:
            return datetime.fromisoformat(value).isoformat(timespec="seconds")
        except ValueError:
            pass
    return fallback.isoformat(timespec="seconds")


def _parse_date_time_input(
    date_value: str | None,
    time_value: str | None,
    fallback: datetime,
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
        return dt.isoformat(timespec="seconds")
    except ValueError:
        return fallback.isoformat(timespec="seconds")


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
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "sleep_state": sleep_state,
            "stats": stats,
            "chart_data": chart_data,
            "format_duration": _format_duration,
            "format_since": _format_since,
            "format_datetime": _format_datetime,
            "format_datetime_input": _format_datetime_input,
            "format_date_input": _format_date_input,
            "format_time_input": _format_time_input,
            "format_date_input": _format_date_input,
            "format_time_input": _format_time_input,
            "start_date": start_date or "",
            "end_date": end_date or "",
            "active_page": "home",
            "app_name": APP_NAME,
        },
    )


@app.get("/history", response_class=HTMLResponse)
def history(request: Request) -> HTMLResponse:
    start_date = request.query_params.get("start_date") or None
    end_date = request.query_params.get("end_date") or None
    entries = _get_entries(start_date=start_date, end_date=end_date)
    return templates.TemplateResponse(
        "history.html",
        {
            "request": request,
            "entries": entries,
            "format_duration": _format_duration,
            "format_datetime": _format_datetime,
            "format_datetime_input": _format_datetime_input,
            "start_date": start_date or "",
            "end_date": end_date or "",
            "active_page": "history",
            "app_name": APP_NAME,
        },
    )


@app.get("/stats", response_class=HTMLResponse)
def stats_partial(request: Request) -> HTMLResponse:
    stats = _get_stats()
    return templates.TemplateResponse(
        "_stats.html",
        {
            "request": request,
            "stats": stats,
            "stats_oob": False,
            "format_duration": _format_duration,
            "format_since": _format_since,
            "format_datetime": _format_datetime,
        },
    )


@app.get("/entries", response_class=HTMLResponse)
def entries_partial(request: Request) -> HTMLResponse:
    start_date = request.query_params.get("start_date") or None
    end_date = request.query_params.get("end_date") or None
    entries = _get_entries(start_date=start_date, end_date=end_date)
    return templates.TemplateResponse(
        "_entries.html",
        {
            "request": request,
            "entries": entries,
            "format_duration": _format_duration,
            "format_datetime": _format_datetime,
            "format_datetime_input": _format_datetime_input,
            "start_date": start_date or "",
            "end_date": end_date or "",
        },
    )


@app.post("/feed", response_class=HTMLResponse)
def log_feed(
    request: Request,
    amount_ml: int = Form(120),
    notes: str = Form(""),
    created_at: str = Form(""),
    created_date: str = Form(""),
    created_time: str = Form(""),
    minutes_ago: int = Form(0),
    start_date: str = Form(""),
    end_date: str = Form(""),
) -> HTMLResponse:
    now_dt = datetime.now()
    created_at_dt = now_dt - timedelta(minutes=minutes_ago or 0)
    if created_date or created_time:
        created_at = _parse_date_time_input(created_date, created_time, created_at_dt)
    else:
        created_at = _parse_datetime_input(created_at, created_at_dt)
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO events (type, amount_ml, notes, created_at)
            VALUES (?, ?, ?, ?);
            """,
            ("feed", amount_ml, notes.strip() or None, created_at),
        )
        conn.commit()

    entries = _get_entries(
        start_date=start_date or None,
        end_date=end_date or None,
    )
    stats = _get_stats()
    return templates.TemplateResponse(
        "_feed_response.html",
        {
            "request": request,
            "entries": entries,
            "stats": stats,
            "stats_oob": False,
            "format_duration": _format_duration,
            "format_since": _format_since,
            "format_datetime": _format_datetime,
            "format_datetime_input": _format_datetime_input,
            "start_date": start_date or "",
            "end_date": end_date or "",
        },
    )


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

    return templates.TemplateResponse(
        "_sleep_toggle_response.html",
        {
            "request": request,
            "entries": entries,
            "sleep_state": sleep_state,
            "stats": stats,
            "stats_oob": True,
            "format_duration": _format_duration,
            "format_since": _format_since,
            "format_datetime": _format_datetime,
            "format_datetime_input": _format_datetime_input,
            "format_date_input": _format_date_input,
            "format_time_input": _format_time_input,
            "start_date": start_date or "",
            "end_date": end_date or "",
            "oob": True,
        },
    )


@app.get("/entries/{entry_id}/edit", response_class=HTMLResponse)
def edit_entry(entry_id: int, request: Request) -> HTMLResponse:
    entry = _get_entry(entry_id)
    if not entry:
        return HTMLResponse(status_code=404, content="Not found")
    return templates.TemplateResponse(
        "_entry_edit.html",
        {
            "request": request,
            "entry": entry,
            "format_duration": _format_duration,
            "format_datetime": _format_datetime,
            "format_datetime_input": _format_datetime_input,
            "format_date_input": _format_date_input,
            "format_time_input": _format_time_input,
        },
    )


@app.post("/entries/{entry_id}", response_class=HTMLResponse)
def update_entry(
    entry_id: int,
    request: Request,
    amount_ml: int | None = Form(None),
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
) -> HTMLResponse:
    entry = _get_entry(entry_id)
    if not entry:
        return HTMLResponse(status_code=404, content="Not found")
    now_dt = datetime.now()

    if entry["type"] == "feed":
        amount = amount_ml if amount_ml is not None else entry["amount_ml"]
        if created_date or created_time:
            created_at_value = _parse_date_time_input(
                created_date, created_time, now_dt
            )
        else:
            created_at_value = _parse_datetime_input(created_at, now_dt)
        with _connect() as conn:
            conn.execute(
                """
                UPDATE events
                SET amount_ml = ?, notes = ?, created_at = ?
                WHERE id = ?;
                """,
                (amount, notes.strip() or None, created_at_value, entry_id),
            )
            conn.commit()
    else:
        if started_date or started_time:
            started_at = _parse_date_time_input(started_date, started_time, now_dt)
        else:
            started_at = _parse_datetime_input(started_at, now_dt)

        if ended_date or ended_time:
            ended_at = _parse_date_time_input(ended_date, ended_time, now_dt)
        else:
            ended_at = _parse_datetime_input(ended_at, now_dt)
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
    return templates.TemplateResponse(
        "_entry_update_response.html",
        {
            "request": request,
            "entry": updated,
            "stats": stats,
            "stats_oob": True,
            "format_duration": _format_duration,
            "format_since": _format_since,
            "format_datetime": _format_datetime,
        },
    )
