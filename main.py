from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import APP_NAME, BASE_DIR
from app.crud import (
    create_feed,
    create_weight,
    delete_event,
    get_daily_chart_data,
    get_entries,
    get_entry,
    get_setting,
    get_sleep_state,
    get_stats,
    set_setting,
    toggle_sleep_state,
    update_feed_event,
    update_other_event,
)
from app.database import init_db
from app.utils import (
    get_ui_helpers,
    now_iso,
    parse_date_time_input,
    parse_datetime_input,
)

app = FastAPI(title=APP_NAME)

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    start_date = request.query_params.get("start_date") or None
    end_date = request.query_params.get("end_date") or None
    sleep_state = get_sleep_state()
    stats = get_stats()
    chart_data = get_daily_chart_data()

    birthdate_str = get_setting("birthdate")
    age_days = None
    if birthdate_str:
        try:
            birth_date = datetime.strptime(birthdate_str, "%Y-%m-%d").date()
            age_days = (datetime.now(timezone.utc).date() - birth_date).days
        except ValueError:
            pass

    ctx = get_ui_helpers(request)
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
    entries = get_entries(
        start_date=start_date, end_date=end_date, event_type=event_type
    )
    ctx = get_ui_helpers(request)
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
    stats = get_stats()
    ctx = get_ui_helpers(request)
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
    entries = get_entries(
        start_date=start_date, end_date=end_date, event_type=event_type
    )
    ctx = get_ui_helpers(request)
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
        created_at = parse_date_time_input(
            created_date, created_time, created_at_dt, timezone_offset
        )
    else:
        created_at = parse_datetime_input(created_at, created_at_dt, timezone_offset)

    create_feed(subtype, amount_ml, notes.strip() or None, created_at)

    entries = get_entries(
        start_date=start_date or None,
        end_date=end_date or None,
    )
    stats = get_stats()
    ctx = get_ui_helpers(request)
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

    sleep_state_res = toggle_sleep_state(notes.strip() or "")

    entries = get_entries(
        start_date=start_date or None,
        end_date=end_date or None,
    )
    sleep_state = get_sleep_state()
    stats = get_stats()

    ctx = get_ui_helpers(request)
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
    entry = get_entry(entry_id)
    if not entry:
        return HTMLResponse(status_code=404, content="Not found")
    ctx = get_ui_helpers(request)
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
    entry = get_entry(entry_id)
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
            created_at_value = parse_date_time_input(
                created_date, created_time, now_dt, timezone_offset
            )
        else:
            created_at_value = parse_datetime_input(created_at, now_dt, timezone_offset)
        update_feed_event(
            entry_id, amount, subtype_val, notes.strip() or None, created_at_value
        )
    else:
        if started_date or started_time:
            started_at = parse_date_time_input(
                started_date, started_time, now_dt, timezone_offset
            )
        else:
            started_at = parse_datetime_input(started_at, now_dt, timezone_offset)

        if ended_date or ended_time:
            ended_at = parse_date_time_input(
                ended_date, ended_time, now_dt, timezone_offset
            )
        else:
            ended_at = parse_datetime_input(ended_at, now_dt, timezone_offset)
        started_dt = datetime.fromisoformat(started_at)
        ended_dt = datetime.fromisoformat(ended_at)
        if ended_dt < started_dt:
            ended_dt = started_dt
            ended_at = ended_dt.isoformat(timespec="seconds")
        duration_sec = int((ended_dt - started_dt).total_seconds())
        update_other_event(
            entry_id, started_at, ended_at, duration_sec, notes.strip() or None
        )

    updated = get_entry(entry_id)
    stats = get_stats()
    ctx = get_ui_helpers(request)
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
def delete_entry_route(entry_id: int) -> HTMLResponse:
    delete_event(entry_id)
    response = HTMLResponse(status_code=200, content="")
    response.headers["HX-Trigger"] = '{"showToast": "Entry deleted!"}'
    return response


@app.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request) -> HTMLResponse:
    birthdate = get_setting("birthdate") or ""
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
        set_setting("birthdate", birthdate)
    return settings_page(request)


@app.post("/weight", response_class=HTMLResponse)
def log_weight_route(
    request: Request,
    weight_g: int = Form(...),
    notes: str = Form(""),
    created_at: str = Form(""),
    timezone_offset: int = Form(0),
) -> HTMLResponse:
    now_dt = datetime.now(timezone.utc)
    created_at = parse_datetime_input(created_at, now_dt, timezone_offset)

    create_weight(weight_g, notes.strip() or None, created_at)

    response = HTMLResponse(
        status_code=200, content="<script>window.location.reload()</script>"
    )
    response.headers["HX-Trigger"] = '{"showToast": "Weight logged!"}'
    return response
