import type { ReactNode } from "react";
import { AnimatePresence, motion } from "motion/react";
import { Baby, ChevronRight, List, Moon, Plus, Sunrise, Weight } from "lucide-react";
import { Card, CardTitle, Press, Skeleton } from "../components/ui";
import { Amount, DurationFlow, LiveDuration, LiveDurationText } from "../components/Duration";
import { EntryRow, entryMeta } from "../components/EntryRow";
import { WeekChart } from "../components/WeekChart";
import { WeightSparkline } from "../components/WeightSparkline";
import { useEntries, useSleepAction, useSummary } from "../lib/queries";
import { useNow } from "../lib/hooks";
import { useNav } from "../lib/nav";
import { ageDays, ageLabel, formatDateTime, formatTime, parse } from "../lib/time";

const stagger = {
  hidden: {},
  show: { transition: { staggerChildren: 0.06, delayChildren: 0.05 } },
};
const rise = {
  hidden: { opacity: 0, y: 24 },
  show: { opacity: 1, y: 0, transition: { type: "spring", stiffness: 260, damping: 28 } },
} as const;

export function Home() {
  const { data: summary, isLoading } = useSummary();
  const { data: recent } = useEntries({}, 5);
  const { data: weights } = useEntries({ type: "weight" }, 30);
  const { openSheet, go, editEntry } = useNav();
  const sleepAction = useSleepAction();
  // Only date-level values (age) use this; live counters tick in leaf components.
  const now = useNow(60_000);

  const lastFeed = summary?.last_feed;
  const lastFeedAt = parse(lastFeed?.created_at);
  const sleeping = !!summary?.sleep.active;
  const sleepStart = parse(summary?.sleep.started_at);
  const day = ageDays(summary?.birthdate ?? null, now);
  const age = ageLabel(summary?.birthdate ?? null, now);
  const weekTotal = summary?.week.reduce((s, d) => s + d.total_ml, 0) ?? 0;

  return (
    <div className="relative">
      <HeroGlow sleeping={sleeping} />

      <motion.div variants={stagger} initial="hidden" animate="show" className="relative">
        {/* Header */}
        <motion.header variants={rise} className="flex items-center gap-3 px-1">
          <Press
            onClick={() => go("settings")}
            aria-label="Baby profile"
            className="grid size-10 place-items-center rounded-full bg-gradient-to-br from-accent to-accent-2 text-white shadow-lg shadow-accent/30"
          >
            <Baby size={20} strokeWidth={2.4} />
          </Press>
          <div className="min-w-0 flex-1 leading-tight">
            <div className="text-[17px] font-bold">{day !== null ? `Day ${day}` : "FeedApp"}</div>
            <div className="truncate text-[13px] text-muted">{age ?? "Set birth date in Settings"}</div>
          </div>
          <AnimatePresence>
            {sleeping && sleepStart && (
              <motion.button
                type="button"
                onClick={() => openSheet("sleep")}
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.8 }}
                className="flex items-center gap-2 rounded-full bg-sleep/20 py-1.5 pl-2 pr-3 text-[13px] font-semibold text-sleep backdrop-blur"
              >
                <motion.span
                  className="size-2 rounded-full bg-sleep"
                  animate={{ opacity: [1, 0.3, 1] }}
                  transition={{ repeat: Infinity, duration: 1.6 }}
                />
                <LiveDurationText since={sleepStart} />
              </motion.button>
            )}
          </AnimatePresence>
        </motion.header>

        {/* Balance-style hero */}
        <motion.div variants={rise} className="flex flex-col items-center pb-7 pt-10 text-center">
          <div className="text-[15px] font-medium text-muted">Since last feed</div>
          <div className="mt-1 text-[60px] font-bold leading-[1.05] tracking-[-0.03em]">
            {isLoading ? (
              <Skeleton className="mx-auto h-14 w-48" />
            ) : lastFeedAt ? (
              <LiveDuration since={lastFeedAt} />
            ) : (
              "—"
            )}
          </div>
          {lastFeed && lastFeedAt && (
            <motion.button
              type="button"
              whileTap={{ scale: 0.95 }}
              onClick={() => editEntry(lastFeed)}
              className="mt-3 flex items-center gap-1.5 rounded-full bg-surface/70 px-4 py-2 text-[14px] font-semibold shadow-sm shadow-black/5 backdrop-blur"
            >
              <span className="size-2 rounded-full" style={{ background: entryMeta(lastFeed).color }} />
              {lastFeed.amount_ml} ml · {entryMeta(lastFeed).label} · {formatTime(lastFeedAt)}
            </motion.button>
          )}
        </motion.div>

        {/* Quick actions */}
        <motion.div variants={rise} className="grid grid-cols-4 gap-2 pb-6">
          <Action label="Feed" onClick={() => openSheet("feed")} icon={<Plus size={24} strokeWidth={2.6} />} />
          <Action
            label={sleeping ? "Wake up" : "Sleep"}
            onClick={() => openSheet("sleep")}
            icon={sleeping ? <Sunrise size={22} strokeWidth={2.4} /> : <Moon size={22} strokeWidth={2.4} />}
            highlight={sleeping}
          />
          <Action label="Weight" onClick={() => openSheet("weight")} icon={<Weight size={22} strokeWidth={2.4} />} />
          <Action label="History" onClick={() => go("history")} icon={<List size={22} strokeWidth={2.4} />} />
        </motion.div>

        <div className="flex flex-col gap-3">
          {/* Sleep */}
          <Card variants={rise}>
            <CardTitle>Sleep</CardTitle>
            <div className="flex items-end justify-between gap-4">
              <div className="grid flex-1 grid-cols-2 gap-4">
                <Stat label="Current">
                  {sleeping && sleepStart ? (
                    <LiveDuration since={sleepStart} showSeconds className="text-sleep" />
                  ) : (
                    <span className="text-faint">—</span>
                  )}
                </Stat>
                <Stat label="Previous">
                  {summary?.last_sleep ? <DurationFlow value={summary.last_sleep.duration_sec ?? 0} /> : <span className="text-faint">—</span>}
                </Stat>
              </div>
              <Press
                onClick={() => sleepAction.mutate({ action: sleeping ? "stop" : "start" })}
                disabled={sleepAction.isPending || isLoading}
                className={`h-11 shrink-0 rounded-full px-5 text-[15px] font-semibold transition-colors ${
                  sleeping ? "bg-sleep text-white" : "bg-sleep/15 text-sleep"
                }`}
              >
                {sleeping ? "Stop" : "Start"}
              </Press>
            </div>
            {sleeping && sleepStart && <div className="mt-3 text-[13px] text-muted">Since {formatDateTime(sleepStart)}</div>}
          </Card>

          {/* Week chart */}
          <Card variants={rise}>
            <CardTitle action={<span className="text-[13px] text-muted">{weekTotal.toLocaleString("en-GB")} ml this week</span>}>
              Feeding · 7 days
            </CardTitle>
            {summary ? <WeekChart week={summary.week} /> : <Skeleton className="h-44" />}
          </Card>

          {/* Recent */}
          <Card variants={rise} className="px-3">
            <div className="px-2">
              <CardTitle
                action={
                  <Press onClick={() => go("history")} className="flex items-center text-[14px] font-semibold text-accent">
                    See all <ChevronRight size={16} strokeWidth={2.6} />
                  </Press>
                }
              >
                Recent
              </CardTitle>
            </div>
            {recent?.length ? (
              <ul>
                <AnimatePresence initial={false}>
                  {recent.map((e, i) => (
                    <EntryRow key={e.id} entry={e} index={i} onClick={() => editEntry(e)} />
                  ))}
                </AnimatePresence>
              </ul>
            ) : (
              <p className="px-2 pb-2 text-[15px] text-muted">No entries yet.</p>
            )}
          </Card>

          {/* Weight */}
          <Card variants={rise}>
            <CardTitle
              action={
                <Press onClick={() => openSheet("weight")} className="rounded-full bg-weight/15 px-3 py-1.5 text-[13px] font-semibold text-weight">
                  + Log
                </Press>
              }
            >
              Weight
            </CardTitle>
            {summary?.last_weight ? (
              <div className="flex items-end justify-between gap-4">
                <div>
                  <Amount value={summary.last_weight.amount_ml ?? 0} suffix="g" className="text-[32px] font-bold tracking-tight" />
                  <div className="text-[13px] text-muted">{formatDateTime(parse(summary.last_weight.created_at)!)}</div>
                </div>
                {weights && weights.length > 1 && <WeightSparkline entries={weights} />}
              </div>
            ) : (
              <p className="text-[15px] text-muted">No weight logged yet.</p>
            )}
          </Card>
        </div>
      </motion.div>
    </div>
  );
}

function Action({ label, icon, onClick, highlight }: { label: string; icon: ReactNode; onClick: () => void; highlight?: boolean }) {
  return (
    <Press onClick={onClick} className="flex flex-col items-center gap-2">
      <span
        className={`grid size-14 place-items-center rounded-full backdrop-blur-xl transition-colors duration-300 ${
          highlight ? "bg-sleep text-white shadow-lg shadow-sleep/40" : "bg-surface/90 text-fg shadow-sm shadow-black/5"
        }`}
      >
        {icon}
      </span>
      <span className="text-[13px] font-medium">{label}</span>
    </Press>
  );
}

function Stat({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <div className="text-[13px] text-muted">{label}</div>
      <div className="mt-0.5 text-[24px] font-bold tracking-tight">{children}</div>
    </div>
  );
}

/** Animated gradient wash behind the hero, à la Revolut's account backdrop. */
function HeroGlow({ sleeping }: { sleeping: boolean }) {
  return (
    <div className="pointer-events-none absolute inset-x-[-1rem] -top-24 h-[30rem] overflow-hidden" aria-hidden>
      <motion.div
        className="absolute left-1/2 top-0 size-[26rem] -translate-x-1/2 rounded-full blur-[90px]"
        animate={{
          background: sleeping ? "var(--sleep)" : "var(--glow-a)",
          x: ["-60%", "-40%", "-60%"],
          scale: [1, 1.12, 1],
        }}
        transition={{
          background: { duration: 1.2 },
          x: { repeat: Infinity, duration: 14, ease: "easeInOut" },
          scale: { repeat: Infinity, duration: 10, ease: "easeInOut" },
        }}
        style={{ opacity: 0.55 }}
      />
      <motion.div
        className="absolute right-[-6rem] top-20 size-72 rounded-full blur-[80px]"
        animate={{ background: sleeping ? "#3b2a8c" : "var(--glow-b)", y: [0, 30, 0] }}
        transition={{ background: { duration: 1.2 }, y: { repeat: Infinity, duration: 12, ease: "easeInOut" } }}
        style={{ opacity: 0.6 }}
      />
      <div className="absolute inset-x-0 bottom-0 h-40 bg-gradient-to-b from-transparent to-bg" />
    </div>
  );
}
