from __future__ import annotations

from datetime import datetime
from pathlib import Path
import os
import sqlite3
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
        row = conn.execute("SELECT started_at FROM sleep_state WHERE id = 1;").fetchone()
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
        },
    )


@app.post("/feed", response_class=HTMLResponse)
def log_feed(
    request: Request,
    amount_ml: int = Form(120),
    notes: str = Form("")
) -> HTMLResponse:
    now = _now_iso()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO events (type, amount_ml, notes, created_at)
            VALUES (?, ?, ?, ?);
            """,
            ("feed", amount_ml, notes.strip() or None, now),
        )
        conn.commit()

    entries = _get_entries()
    return templates.TemplateResponse(
        "_entries.html",
        {
            "request": request,
            "entries": entries,
            "format_duration": _format_duration,
        },
    )


@app.post("/sleep/toggle", response_class=HTMLResponse)
def toggle_sleep(
    request: Request,
    notes: str = Form("")
) -> HTMLResponse:
    now = _now_iso()
    with _connect() as conn:
        row = conn.execute("SELECT started_at FROM sleep_state WHERE id = 1;").fetchone()
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
            "oob": True,
        },
    )
