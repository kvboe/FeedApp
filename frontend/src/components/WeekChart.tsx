import { useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import type { DayTotal } from "../lib/types";
import { localDateKey, weekdayShort } from "../lib/time";
import { haptic } from "../lib/haptics";

/** Seven animated bars; tap a bar to see that day's total. */
export function WeekChart({ week }: { week: DayTotal[] }) {
  const today = localDateKey(new Date());
  const [selected, setSelected] = useState<string>(week.at(-1)?.date ?? today);
  const max = Math.max(1, ...week.map((d) => d.total_ml));
  const sel = week.find((d) => d.date === selected) ?? week.at(-1);

  return (
    <div>
      <div className="mb-4 flex items-baseline justify-between">
        <AnimatePresence mode="popLayout" initial={false}>
          <motion.div
            key={sel?.date}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.18 }}
          >
            <div className="text-[28px] font-bold leading-none tracking-tight tabular-nums">
              {(sel?.total_ml ?? 0).toLocaleString("en-GB")}
              <span className="ml-1 text-[17px] font-semibold text-muted">ml</span>
            </div>
            <div className="mt-1 text-[13px] text-muted">
              {sel?.date === today ? "Today" : sel ? weekdayShort(sel.date) : ""} · {sel?.count ?? 0}{" "}
              {sel?.count === 1 ? "feed" : "feeds"}
            </div>
          </motion.div>
        </AnimatePresence>
      </div>
      <div className="flex h-32 items-end gap-2">
        {week.map((d, i) => {
          const pct = d.total_ml / max;
          const active = d.date === sel?.date;
          return (
            <button
              key={d.date}
              type="button"
              className="flex h-full flex-1 flex-col items-center justify-end gap-2"
              onClick={() => {
                haptic("tap");
                setSelected(d.date);
              }}
              aria-label={`${weekdayShort(d.date)}: ${d.total_ml} ml`}
            >
              <div className="relative flex w-full flex-1 items-end">
                <motion.div
                  className="w-full rounded-[10px]"
                  initial={{ height: 0 }}
                  animate={{
                    height: `${Math.max(pct * 100, d.total_ml ? 6 : 3)}%`,
                    backgroundColor: active ? "var(--accent)" : "var(--surface-3)",
                  }}
                  transition={{ type: "spring", stiffness: 180, damping: 22, delay: i * 0.05 }}
                />
              </div>
              <span className={`text-[12px] font-medium ${active ? "text-fg" : "text-muted"}`}>
                {weekdayShort(d.date).slice(0, 2)}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
