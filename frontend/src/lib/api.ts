import type { BreastSide, Entry, EntryFilters, EntryPage, FeedSubtype, Settings, SleepState, Summary } from "./types";
import { dayRangeToUtc } from "./time";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`/api${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...init?.headers },
    });
  } catch {
    throw new ApiError(0, "You're offline");
  }
  if (!res.ok) {
    let msg = res.statusText || "Request failed";
    try {
      const body = await res.json();
      if (typeof body.detail === "string") msg = body.detail;
      else if (Array.isArray(body.detail)) msg = "Please check the values";
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, msg);
  }
  return (res.status === 204 ? undefined : await res.json()) as T;
}

const json = (body: unknown) => JSON.stringify(body);

export const PAGE_SIZE = 30;

export type PageCursor = Pick<Entry, "created_at" | "id">;

export const api = {
  summary: () => {
    // IANA zone lets the server apply DST per day; the offset is a fallback.
    const q = new URLSearchParams({ tz_offset: String(new Date().getTimezoneOffset()) });
    try {
      const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
      if (tz) q.set("tz", tz);
    } catch {
      /* old browser: offset only */
    }
    return request<Summary>(`/summary?${q}`);
  },

  /** Keyset-paged history: pass the last item of the previous page as `cursor`. */
  entries: (filters: Partial<EntryFilters>, cursor: PageCursor | null = null, limit = PAGE_SIZE) => {
    const q = new URLSearchParams({ limit: String(limit) });
    if (cursor) {
      q.set("before_created_at", cursor.created_at);
      q.set("before_id", String(cursor.id));
    }
    if (filters.type) q.set("type", filters.type);
    const { start, end } = dayRangeToUtc(filters.from ?? "", filters.to ?? "");
    if (start) q.set("start", start);
    if (end) q.set("end", end);
    return request<EntryPage>(`/entries?${q}`);
  },

  logFeed: (body: { subtype: FeedSubtype; side?: BreastSide; amount_ml: number; notes?: string; created_at?: string }) =>
    request<Entry>("/feeds", { method: "POST", body: json(body) }),

  logWeight: (body: { weight_g: number; notes?: string; created_at?: string }) =>
    request<Entry>("/weights", { method: "POST", body: json(body) }),

  /** Explicit start/stop: the server answers 409 if the state already changed elsewhere. */
  sleep: (action: "start" | "stop", notes?: string) =>
    request<SleepState & { entry: Entry | null }>("/sleep", {
      method: "POST",
      body: json({ action, notes }),
    }),

  updateEntry: (id: number, body: Partial<Pick<Entry, "amount_ml" | "subtype" | "side" | "notes" | "created_at" | "started_at" | "ended_at">>) =>
    request<Entry>(`/entries/${id}`, { method: "PATCH", body: json(body) }),

  deleteEntry: (id: number) => request<void>(`/entries/${id}`, { method: "DELETE" }),

  settings: () => request<Settings>("/settings"),
  saveSettings: (body: Settings) => request<Settings>("/settings", { method: "PUT", body: json(body) }),
};
