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


def _get_entries(limit: int = 10) -> list[sqlite3.Row]:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM events
            ORDER BY datetime(created_at) DESC
            LIMIT ?;
            """,
            (limit,),
        ).fetchall()
    return list(rows)


def _get_sleep_state() -> dict[str, Any]:
    with _connect() as conn:
        row = conn.execute(
            "SELECT started_at FROM sleep_state WHERE id = 1;"
        ).fetchone()
    if not row:
        return {"active": False, "started_at": None}
    return {"active": True, "started_at": row["started_at"]}


def _format_duration(seconds: int | None) -> str:
    if not seconds:
        return "0m"
    minutes = seconds // 60
    hours = minutes // 60
    minutes = minutes % 60
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


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


def _parse_datetime_input(value: str | None, fallback: datetime) -> str:
    if value:
        try:
            return datetime.fromisoformat(value).isoformat(timespec="seconds")
        except ValueError:
            pass
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
    entries = _get_entries()
    sleep_state = _get_sleep_state()
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "entries": entries,
            "sleep_state": sleep_state,
            "format_duration": _format_duration,
            "format_datetime": _format_datetime,
            "format_datetime_input": _format_datetime_input,
            "app_name": APP_NAME,
        },
    )


@app.get("/entries", response_class=HTMLResponse)
def entries_partial(request: Request) -> HTMLResponse:
    entries = _get_entries()
    return templates.TemplateResponse(
        "_entries.html",
        {
            "request": request,
            "entries": entries,
            "format_duration": _format_duration,
            "format_datetime": _format_datetime,
            "format_datetime_input": _format_datetime_input,
        },
    )


@app.post("/feed", response_class=HTMLResponse)
def log_feed(
    request: Request,
    amount_ml: int = Form(120),
    notes: str = Form(""),
    created_at: str = Form(""),
    minutes_ago: int = Form(0),
) -> HTMLResponse:
    now_dt = datetime.now()
    created_at_dt = now_dt - timedelta(minutes=minutes_ago or 0)
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

    entries = _get_entries()
    return templates.TemplateResponse(
        "_entries.html",
        {
            "request": request,
            "entries": entries,
            "format_duration": _format_duration,
            "format_datetime": _format_datetime,
            "format_datetime_input": _format_datetime_input,
        },
    )


@app.post("/sleep/toggle", response_class=HTMLResponse)
def toggle_sleep(request: Request, notes: str = Form("")) -> HTMLResponse:
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

    entries = _get_entries()
    sleep_state = _get_sleep_state()

    return templates.TemplateResponse(
        "_sleep_toggle_response.html",
        {
            "request": request,
            "entries": entries,
            "sleep_state": sleep_state,
            "format_duration": _format_duration,
            "format_datetime": _format_datetime,
            "format_datetime_input": _format_datetime_input,
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
        },
    )


@app.post("/entries/{entry_id}", response_class=HTMLResponse)
def update_entry(
    entry_id: int,
    request: Request,
    amount_ml: int | None = Form(None),
    created_at: str = Form(""),
    started_at: str = Form(""),
    ended_at: str = Form(""),
    notes: str = Form(""),
) -> HTMLResponse:
    entry = _get_entry(entry_id)
    if not entry:
        return HTMLResponse(status_code=404, content="Not found")
    now_dt = datetime.now()

    if entry["type"] == "feed":
        amount = amount_ml if amount_ml is not None else entry["amount_ml"]
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
        started_at = _parse_datetime_input(started_at, now_dt)
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
    return templates.TemplateResponse(
        "_entry_card.html",
        {
            "request": request,
            "entry": updated,
            "format_duration": _format_duration,
            "format_datetime": _format_datetime,
        },
    )
