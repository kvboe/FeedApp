from datetime import date
from typing import Literal

from pydantic import AwareDatetime, BaseModel, Field

FeedSubtype = Literal["formula", "breast_milk"]
BreastSide = Literal["left", "right"]
EventType = Literal["feed", "sleep", "weight"]


class Entry(BaseModel):
    id: int
    type: str
    subtype: str | None = None
    side: str | None = None  # breast_milk only: "left" | "right"
    amount_ml: int | None = None
    duration_sec: int | None = None
    started_at: str | None = None
    ended_at: str | None = None
    notes: str | None = None
    created_at: str
    time_since_prev: int | None = None


class EntryPage(BaseModel):
    items: list[Entry]
    has_more: bool


class FeedCreate(BaseModel):
    subtype: FeedSubtype = "formula"
    side: BreastSide | None = None  # ignored for formula
    amount_ml: int = Field(ge=1, le=5000)
    notes: str | None = None
    created_at: AwareDatetime | None = None


class WeightCreate(BaseModel):
    weight_g: int = Field(ge=1, le=100000)
    notes: str | None = None
    created_at: AwareDatetime | None = None


class SleepAction(BaseModel):
    # Explicit intent: the client says what it believes it is doing, so a
    # stale screen can never stop a sleep it meant to start (or vice versa).
    action: Literal["start", "stop"]
    notes: str | None = None


class SleepState(BaseModel):
    active: bool
    started_at: str | None = None


class SleepActionResult(SleepState):
    entry: Entry | None = None


class EntryUpdate(BaseModel):
    amount_ml: int | None = Field(default=None, ge=1, le=100000)
    subtype: FeedSubtype | None = None
    side: BreastSide | None = None
    notes: str | None = None
    created_at: AwareDatetime | None = None
    started_at: AwareDatetime | None = None
    ended_at: AwareDatetime | None = None


class DayTotal(BaseModel):
    date: str  # local YYYY-MM-DD
    total_ml: int
    count: int


class Summary(BaseModel):
    last_feed: Entry | None
    last_breast: Entry | None  # latest mother's-milk feed with a known side
    last_sleep: Entry | None
    last_weight: Entry | None
    sleep: SleepState
    week: list[DayTotal]
    birthdate: str | None


class Settings(BaseModel):
    birthdate: date | None = None
