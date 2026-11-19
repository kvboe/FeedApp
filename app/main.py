from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone, tzinfo
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import crud
from .config import APP_NAME, BASE_DIR
from .database import get_connection, init_db
from .schemas import (
    Entry,
    EntryPage,
    EntryUpdate,
    EventType,
    FeedCreate,
    Settings,
    SleepAction,
    SleepActionResult,
    Summary,
    WeightCreate,
)
from .utils import now_iso, parse_iso, to_iso

DIST_DIR = BASE_DIR / "frontend" / "dist"


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title=APP_NAME, lifespan=lifespan)
api = APIRouter(prefix="/api")

_WRITE_METHODS = {"POST", "PUT", "PATCH"}


@app.middleware("http")
async def require_json_writes(request: Request, call_next):
    """CSRF guard: writes must be sent as application/json.

    FastAPI parses a body with *no* Content-Type as JSON, and a browser sends such a
    "simple" request cross-site without a CORS preflight, so any web page opened on a
    device in the same network could otherwise log entries. A JSON Content-Type forces
    a preflight, which fails because this API allows no other origins.
    """
    if request.method in _WRITE_METHODS and request.url.path.startswith("/api/"):
        ctype = request.headers.get("content-type", "").split(";")[0].strip().lower()
        if ctype != "application/json":
            return JSONResponse({"detail": "Content-Type must be application/json"}, status_code=415)
    return await call_next(request)


def _clean_notes(notes: str | None) -> str | None:
    return (notes or "").strip() or None


def _entry_or_404(entry_id: int) -> dict:
    entry = crud.get_entry(entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    return entry


def _iso_param(value: str | None, name: str) -> str | None:
    """Validate an ISO datetime query param and normalise it to stored format."""
    if not value:
        return None
    try:
        return to_iso(parse_iso(value))
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Invalid {name} datetime") from None


def _resolve_tz(tz: str | None, tz_offset: int) -> tzinfo:
    """Prefer the IANA zone (DST-correct); fall back to a fixed JS offset."""
    if tz:
        try:
            return ZoneInfo(tz)
        except (ZoneInfoNotFoundError, ValueError):
            pass
    return timezone(timedelta(minutes=-tz_offset))


# ------------------------------------------------------------------ reads


@api.get("/health", include_in_schema=False)
def health() -> dict:
    """Liveness probe for Docker: the app is up and the database answers."""
    with get_connection() as conn:
        conn.execute("SELECT 1;").fetchone()
    return {"status": "ok"}


@api.get("/summary", response_model=Summary)
def summary(
    tz: str | None = Query(None, max_length=64),
    tz_offset: int = Query(0, ge=-900, le=900),
) -> dict:
    return crud.get_summary(_resolve_tz(tz, tz_offset))


@api.get("/entries", response_model=EntryPage)
def entries(
    start: str | None = None,
    end: str | None = None,
    type: EventType | None = None,
    limit: int = Query(30, ge=1, le=200),
    before_created_at: str | None = None,
    before_id: int | None = None,
) -> dict:
    before = None
    if before_created_at and before_id is not None:
        before = (_iso_param(before_created_at, "before_created_at"), before_id)
    items, has_more = crud.get_entries(
        limit=limit,
        before=before,
        start=_iso_param(start, "start"),
        end=_iso_param(end, "end"),
        event_type=type,
    )
    return {"items": items, "has_more": has_more}


@api.get("/entries/{entry_id}", response_model=Entry)
def entry(entry_id: int) -> dict:
    return _entry_or_404(entry_id)


# ----------------------------------------------------------------- writes


@api.post("/feeds", response_model=Entry, status_code=201)
def log_feed(body: FeedCreate) -> dict:
    created_at = to_iso(body.created_at) if body.created_at else now_iso()
    side = body.side if body.subtype == "breast_milk" else None
    entry_id = crud.create_feed(
        body.subtype, side, body.amount_ml, _clean_notes(body.notes), created_at
    )
    return crud.get_entry(entry_id)


@api.post("/weights", response_model=Entry, status_code=201)
def log_weight(body: WeightCreate) -> dict:
    created_at = to_iso(body.created_at) if body.created_at else now_iso()
    entry_id = crud.create_weight(body.weight_g, _clean_notes(body.notes), created_at)
    return crud.get_entry(entry_id)


@api.post("/sleep", response_model=SleepActionResult)
def sleep_action(body: SleepAction) -> dict:
    try:
        if body.action == "start":
            result = crud.start_sleep()
        else:
            result = crud.stop_sleep(_clean_notes(body.notes))
    except crud.SleepStateConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    entry_id = result.pop("entry_id")
    result["entry"] = crud.get_entry(entry_id) if entry_id else None
    return result


@api.patch("/entries/{entry_id}", response_model=Entry)
def update_entry(entry_id: int, body: EntryUpdate) -> dict:
    """Partial update: only the fields present in the body are changed."""
    entry = _entry_or_404(entry_id)
    given = body.model_fields_set
    fields: dict = {}

    if "notes" in given:
        fields["notes"] = _clean_notes(body.notes)

    if entry["type"] in ("feed", "weight"):
        if body.amount_ml is not None:
            fields["amount_ml"] = body.amount_ml
        if body.created_at is not None:
            fields["created_at"] = to_iso(body.created_at)
        if entry["type"] == "feed":
            if body.subtype is not None:
                fields["subtype"] = body.subtype
            subtype = fields.get("subtype", entry["subtype"])
            if subtype != "breast_milk":
                if entry.get("side") is not None:
                    fields["side"] = None  # a side only makes sense for mother's milk
            elif "side" in given:
                fields["side"] = body.side
    elif body.started_at is not None or body.ended_at is not None:
        # Untouched bounds keep their stored (second-precise) values.
        started = body.started_at or _stored(entry["started_at"])
        ended = body.ended_at or _stored(entry["ended_at"])
        if started is None or ended is None:
            raise HTTPException(status_code=422, detail="Sleep needs both start and end")
        if ended < started:
            raise HTTPException(status_code=422, detail="End must be after start")
        fields.update(
            started_at=to_iso(started),
            ended_at=to_iso(ended),
            duration_sec=int((ended - started).total_seconds()),
            created_at=to_iso(ended),
        )

    crud.update_event(entry_id, fields)
    return crud.get_entry(entry_id)


def _stored(value: str | None) -> datetime | None:
    return parse_iso(value) if value else None


@api.delete("/entries/{entry_id}", status_code=204)
def delete_entry(entry_id: int) -> Response:
    if not crud.delete_event(entry_id):
        raise HTTPException(status_code=404, detail="Entry not found")
    return Response(status_code=204)


# --------------------------------------------------------------- settings


@api.get("/settings", response_model=Settings)
def get_settings() -> dict:
    return {"birthdate": crud.get_setting("birthdate")}


@api.put("/settings", response_model=Settings)
def save_settings(body: Settings) -> dict:
    crud.set_setting("birthdate", body.birthdate.isoformat() if body.birthdate else None)
    return get_settings()


app.include_router(api)


# ------------------------------------------------------------ SPA hosting

if (DIST_DIR / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=DIST_DIR / "assets"), name="assets")


@app.get("/{path:path}", include_in_schema=False)
def spa(path: str) -> Response:
    if path.startswith("api/"):
        raise HTTPException(status_code=404)
    index = DIST_DIR / "index.html"
    if not index.is_file():
        return Response(
            "Frontend not built. Run the frontend build (see README).",
            status_code=503,
            media_type="text/plain",
        )
    candidate = (DIST_DIR / path).resolve()
    if path and candidate.is_file() and DIST_DIR.resolve() in candidate.parents:
        return _file(candidate)
    return _file(index)


def _file(path: Path) -> FileResponse:
    # HTML / service worker / manifest must always revalidate so updates ship.
    no_cache = path.suffix in {".html", ".webmanifest"} or path.name == "sw.js"
    headers = {"Cache-Control": "no-cache"} if no_cache else {"Cache-Control": "public, max-age=86400"}
    return FileResponse(path, headers=headers)
