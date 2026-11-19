import { useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { CalendarDays, X } from "lucide-react";
import { Chip, Label, Press, Skeleton, Spinner } from "../components/ui";
import { EntryRow } from "../components/EntryRow";
import { useEntries } from "../lib/queries";
import { useNav } from "../lib/nav";
import type { Entry, EntryFilters, EventType } from "../lib/types";
import { dayLabel, formatDuration, localDateKey, parse } from "../lib/time";

const EMPTY: EntryFilters = { type: null, from: "", to: "" };

export function History() {
  const { editEntry } = useNav();
  const [filters, setFilters] = useState<EntryFilters>(EMPTY);
  const [showDates, setShowDates] = useState(false);
  const query = useEntries(filters);
  const entries = query.data;

  const today = localDateKey(new Date());
  const isToday = filters.from === today && filters.to === today;
  const active = filters.type !== null || !!filters.from || !!filters.to;

  const toggleType = (t: EventType) => setFilters((f) => ({ ...f, type: f.type === t ? null : t }));

  const groups = useMemo(() => groupByDay(entries ?? []), [entries]);

  // Infinite scroll
  const sentinel = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = sentinel.current;
    if (!el) return;
    const io = new IntersectionObserver(
      ([e]) => {
        if (e.isIntersecting && query.hasNextPage && !query.isFetchingNextPage) query.fetchNextPage();
      },
      { rootMargin: "400px" },
    );
    io.observe(el);
    return () => io.disconnect();
  }, [query.hasNextPage, query.isFetchingNextPage, query.fetchNextPage]);

  return (
    <div>
      <motion.h1
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="px-1 pb-4 pt-2 text-[34px] font-bold tracking-tight"
      >
        History
      </motion.h1>

      {/* Filters */}
      <div className="sticky top-0 z-20 -mx-4 bg-bg/85 px-4 pb-3 pt-safe backdrop-blur-xl">
        <div className="-mx-4 flex gap-2 overflow-x-auto px-4 no-scrollbar">
          <AnimatePresence initial={false}>
            {active && (
              <motion.div
                initial={{ width: 0, opacity: 0 }}
                animate={{ width: "auto", opacity: 1 }}
                exit={{ width: 0, opacity: 0 }}
                className="shrink-0 overflow-hidden"
              >
                <Press
                  aria-label="Clear filters"
                  onClick={() => {
                    setFilters(EMPTY);
                    setShowDates(false);
                  }}
                  className="grid size-10 place-items-center rounded-full bg-surface-2 text-muted"
                >
                  <X size={18} strokeWidth={2.6} />
                </Press>
              </motion.div>
            )}
          </AnimatePresence>
          <Chip
            active={isToday}
            onClick={() => (isToday ? setFilters(EMPTY) : setFilters({ type: null, from: today, to: today }))}
          >
            Today
          </Chip>
          <Chip active={filters.type === "feed"} onClick={() => toggleType("feed")}>
            Feeds
          </Chip>
          <Chip active={filters.type === "sleep"} onClick={() => toggleType("sleep")}>
            Sleep
          </Chip>
          <Chip active={filters.type === "weight"} onClick={() => toggleType("weight")}>
            Weight
          </Chip>
          <Chip active={showDates || (!isToday && !!(filters.from || filters.to))} onClick={() => setShowDates((s) => !s)}>
            <span className="flex items-center gap-1.5">
              <CalendarDays size={16} strokeWidth={2.4} /> Dates
            </span>
          </Chip>
        </div>
        <AnimatePresence initial={false}>
          {showDates && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ type: "spring", stiffness: 400, damping: 36 }}
              className="overflow-hidden"
            >
              <div className="grid grid-cols-2 gap-2 pt-3">
                <div>
                  <Label htmlFor="from">From</Label>
                  <input
                    id="from"
                    type="date"
                    className="field"
                    value={filters.from}
                    max={filters.to || undefined}
                    onChange={(e) => setFilters((f) => ({ ...f, from: e.target.value }))}
                  />
                </div>
                <div>
                  <Label htmlFor="to">To</Label>
                  <input
                    id="to"
                    type="date"
                    className="field"
                    value={filters.to}
                    min={filters.from || undefined}
                    onChange={(e) => setFilters((f) => ({ ...f, to: e.target.value }))}
                  />
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* List */}
      {query.isLoading ? (
        <div className="mt-2 space-y-3">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-40 rounded-[28px]" />
          ))}
        </div>
      ) : groups.length === 0 ? (
        <motion.div initial={{ opacity: 0, scale: 0.96 }} animate={{ opacity: 1, scale: 1 }} className="mt-16 text-center">
          <div className="text-5xl">🗂️</div>
          <p className="mt-3 text-[17px] font-semibold">No entries</p>
          <p className="text-[15px] text-muted">{active ? "Try a different filter." : "Logged feeds and sleep will show up here."}</p>
        </motion.div>
      ) : (
        <div className="mt-1 flex flex-col gap-3">
          <AnimatePresence initial={false}>
            {groups.map((g) => (
              <motion.section
                key={g.key}
                layout="position"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.96 }}
                className="rounded-[28px] bg-surface px-3 pb-2 pt-4"
              >
                <div className="flex items-baseline justify-between px-2 pb-1">
                  <h2 className="text-[15px] font-semibold">{dayLabel(g.key)}</h2>
                  <span className="text-[13px] text-muted">{groupSummary(g.items)}</span>
                </div>
                <ul>
                  <AnimatePresence initial={false}>
                    {g.items.map((e, i) => (
                      <EntryRow key={e.id} entry={e} index={i} onClick={() => editEntry(e)} />
                    ))}
                  </AnimatePresence>
                </ul>
              </motion.section>
            ))}
          </AnimatePresence>
        </div>
      )}

      <div ref={sentinel} className="flex h-16 items-center justify-center text-muted">
        {query.isFetchingNextPage && <Spinner />}
      </div>
    </div>
  );
}

function groupByDay(entries: Entry[]) {
  const out: { key: string; items: Entry[] }[] = [];
  for (const e of entries) {
    const d = parse(e.created_at);
    const key = d ? localDateKey(d) : "unknown";
    const last = out.at(-1);
    if (last?.key === key) last.items.push(e);
    else out.push({ key, items: [e] });
  }
  return out;
}

function groupSummary(items: Entry[]): string {
  const feeds = items.filter((e) => e.type === "feed");
  const ml = feeds.reduce((s, e) => s + (e.amount_ml ?? 0), 0);
  const sleep = items.filter((e) => e.type === "sleep").reduce((s, e) => s + (e.duration_sec ?? 0), 0);
  const parts: string[] = [];
  if (feeds.length) parts.push(`${ml.toLocaleString("en-GB")} ml`);
  if (sleep) parts.push(`${formatDuration(sleep)} sleep`);
  return parts.join(" · ");
}
