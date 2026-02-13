from datetime import datetime, timedelta, timezone
from typing import Any
from fastapi import Request

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def format_duration(seconds: int | None) -> str:
    if not seconds:
        return "0m"
    minutes = seconds // 60
    hours = minutes // 60
    minutes = minutes % 60
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"

def format_since(value: str | None) -> str:
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
    return format_duration(seconds)

def format_datetime(value: str | None, offset_minutes: int = 0) -> str:
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

def format_datetime_input(value: str | None, offset_minutes: int = 0) -> str:
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

def format_date_input(value: str | None, offset_minutes: int = 0) -> str:
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

def format_time_input(value: str | None, offset_minutes: int = 0) -> str:
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

def parse_datetime_input(
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

def parse_date_time_input(
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

def get_ui_helpers(request: Request) -> dict[str, Any]:
    try:
        offset = int(request.cookies.get("timezone_offset", "0"))
    except ValueError:
        offset = 0

    return {
        "timezone_offset": offset,
        "format_duration": format_duration,
        "format_since": format_since,
        "format_datetime": lambda v: format_datetime(v, offset),
        "format_datetime_input": lambda v: format_datetime_input(v, offset),
        "format_date_input": lambda v: format_date_input(v, offset),
        "format_time_input": lambda v: format_time_input(v, offset),
    }
