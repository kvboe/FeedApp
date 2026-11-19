const LOCALE = "en-GB";

export function parse(iso: string | null | undefined): Date | null {
  if (!iso) return null;
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? null : d;
}

export function secondsBetween(a: Date, b: Date): number {
  return Math.max(0, Math.floor((b.getTime() - a.getTime()) / 1000));
}

/** "2h 14m" / "14m" — same rules as the original app. */
export function formatDuration(seconds: number | null | undefined): string {
  if (!seconds || seconds < 0) return "0m";
  const totalMin = Math.floor(seconds / 60);
  const h = Math.floor(totalMin / 60);
  const m = totalMin % 60;
  if (h >= 24) {
    const d = Math.floor(h / 24);
    return `${d}d ${h % 24}h`;
  }
  return h ? `${h}h ${m}m` : `${m}m`;
}

/** Split a duration into parts for the large animated counters. */
export function durationParts(seconds: number): { h: number; m: number; s: number } {
  const s = Math.max(0, Math.floor(seconds));
  return { h: Math.floor(s / 3600), m: Math.floor((s % 3600) / 60), s: s % 60 };
}

export function formatTime(d: Date): string {
  return d.toLocaleTimeString(LOCALE, { hour: "2-digit", minute: "2-digit" });
}

export function formatDateTime(d: Date): string {
  return `${d.toLocaleDateString(LOCALE, { day: "numeric", month: "short" })}, ${formatTime(d)}`;
}

/** YYYY-MM-DD in local time. */
export function localDateKey(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

/** HH:MM in local time. */
export function localTimeValue(d: Date): string {
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

/**
 * Combine local date + time inputs into a Date. Returns null when either part
 * is empty or invalid; callers must reject that instead of guessing "now".
 */
export function fromLocalInputs(date: string, time: string): Date | null {
  if (!date || !time) return null;
  const d = new Date(`${date}T${time}`);
  return Number.isNaN(d.getTime()) ? null : d;
}

/** Local-day boundaries (start inclusive, end exclusive) as UTC ISO strings. */
export function dayRangeToUtc(from: string, to: string): { start?: string; end?: string } {
  const out: { start?: string; end?: string } = {};
  if (from) out.start = new Date(`${from}T00:00`).toISOString();
  if (to) {
    const e = new Date(`${to}T00:00`);
    e.setDate(e.getDate() + 1);
    out.end = e.toISOString();
  }
  return out;
}

export function dayLabel(key: string, now = new Date()): string {
  const today = localDateKey(now);
  const y = new Date(now);
  y.setDate(y.getDate() - 1);
  if (key === today) return "Today";
  if (key === localDateKey(y)) return "Yesterday";
  const d = new Date(`${key}T00:00`);
  const sameYear = d.getFullYear() === now.getFullYear();
  return d.toLocaleDateString(LOCALE, {
    weekday: "long",
    day: "numeric",
    month: "long",
    ...(sameYear ? {} : { year: "numeric" }),
  });
}

export function weekdayShort(key: string): string {
  return new Date(`${key}T00:00`).toLocaleDateString(LOCALE, { weekday: "short" });
}

/** Days since birth in local time (original "Day N"). */
export function ageDays(birthdate: string | null, now = new Date()): number | null {
  if (!birthdate) return null;
  const b = new Date(`${birthdate}T00:00`);
  if (Number.isNaN(b.getTime())) return null;
  const t = new Date(`${localDateKey(now)}T00:00`);
  return Math.round((t.getTime() - b.getTime()) / 86_400_000);
}

export function ageLabel(birthdate: string | null, now = new Date()): string | null {
  if (!birthdate) return null;
  const b = new Date(`${birthdate}T00:00`);
  if (Number.isNaN(b.getTime()) || b > now) return null;
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  let months = (today.getFullYear() - b.getFullYear()) * 12 + (today.getMonth() - b.getMonth());
  // Month-anniversaries clamp to the month's last day (born 31 Jan -> 28/29 Feb),
  // so the anchor never rolls over into the next month.
  let anchor = addMonthsClamped(b, months);
  if (anchor > today) anchor = addMonthsClamped(b, --months);
  const days = Math.round((today.getTime() - anchor.getTime()) / 86_400_000);
  if (months <= 0) return `${days} ${days === 1 ? "day" : "days"}`;
  const mo = `${months} ${months === 1 ? "month" : "months"}`;
  return days ? `${mo}, ${days} ${days === 1 ? "day" : "days"}` : mo;
}

function addMonthsClamped(d: Date, months: number): Date {
  const y = d.getFullYear();
  const m = d.getMonth() + months;
  const lastDay = new Date(y, m + 1, 0).getDate();
  return new Date(y, m, Math.min(d.getDate(), lastDay));
}
