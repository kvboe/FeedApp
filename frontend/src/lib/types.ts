export type EventType = "feed" | "sleep" | "weight";
export type FeedSubtype = "formula" | "breast_milk";
export type BreastSide = "left" | "right";

export interface Entry {
  id: number;
  type: EventType | string;
  subtype: FeedSubtype | null;
  side: BreastSide | null;
  amount_ml: number | null;
  duration_sec: number | null;
  started_at: string | null;
  ended_at: string | null;
  notes: string | null;
  created_at: string;
  time_since_prev: number | null;
}

export interface EntryPage {
  items: Entry[];
  has_more: boolean;
}

export interface SleepState {
  active: boolean;
  started_at: string | null;
}

export interface DayTotal {
  date: string;
  total_ml: number;
  count: number;
}

export interface Summary {
  last_feed: Entry | null;
  /** Latest mother's-milk feed with a known side (for the alternate-side default). */
  last_breast: Entry | null;
  last_sleep: Entry | null;
  last_weight: Entry | null;
  sleep: SleepState;
  week: DayTotal[];
  birthdate: string | null;
}

export interface Settings {
  birthdate: string | null;
}

export interface EntryFilters {
  type: EventType | null;
  from: string; // local YYYY-MM-DD
  to: string;
}
