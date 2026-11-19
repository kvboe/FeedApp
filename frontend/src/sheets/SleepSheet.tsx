import { useState } from "react";
import { motion } from "motion/react";
import { Moon, Sunrise } from "lucide-react";
import { BottomSheet } from "../components/BottomSheet";
import { PrimaryButton } from "../components/ui";
import { LiveDuration } from "../components/Duration";
import { useSleepAction } from "../lib/queries";
import type { Summary } from "../lib/types";
import { formatDateTime, formatDuration, parse } from "../lib/time";

export function SleepSheet({ open, onClose, summary }: { open: boolean; onClose: () => void; summary?: Summary }) {
  const active = !!summary?.sleep.active;
  return (
    <BottomSheet open={open} onClose={onClose} title={active ? "Sleeping" : "Sleep"}>
      {open && <SleepForm onDone={onClose} summary={summary} />}
    </BottomSheet>
  );
}

function SleepForm({ onDone, summary }: { onDone: () => void; summary?: Summary }) {
  const [notes, setNotes] = useState("");
  const sleep = useSleepAction();
  const active = !!summary?.sleep.active;
  const started = parse(summary?.sleep.started_at);
  const last = summary?.last_sleep;

  return (
    <form
      className="flex flex-col items-center gap-5 pb-2"
      onSubmit={(e) => {
        e.preventDefault();
        sleep.mutate({ action: active ? "stop" : "start", notes: notes.trim() || undefined }, { onSuccess: onDone });
      }}
    >
      <div className="relative my-2 grid size-40 place-items-center">
        {active &&
          [0, 1, 2].map((i) => (
            <motion.span
              key={i}
              className="absolute inset-0 rounded-full bg-sleep/25"
              initial={{ scale: 0.6, opacity: 0.8 }}
              animate={{ scale: 1.35, opacity: 0 }}
              transition={{ repeat: Infinity, duration: 3, delay: i, ease: "easeOut" }}
            />
          ))}
        <motion.span
          className="relative grid size-28 place-items-center rounded-full bg-sleep text-white shadow-2xl shadow-sleep/40"
          animate={active ? { scale: [1, 1.05, 1] } : { scale: 1, rotate: [0, -8, 8, 0] }}
          transition={active ? { repeat: Infinity, duration: 4, ease: "easeInOut" } : { duration: 1.2 }}
        >
          {active ? <Moon size={48} strokeWidth={2} fill="currentColor" /> : <Moon size={48} strokeWidth={2} />}
        </motion.span>
      </div>

      {active && started ? (
        <div className="text-center">
          <LiveDuration since={started} showSeconds className="text-[52px] font-bold tracking-tight" />
          <div className="mt-1 text-[15px] text-muted">Since {formatDateTime(started)}</div>
        </div>
      ) : (
        <div className="text-center">
          <div className="text-[28px] font-bold tracking-tight">Ready for a nap?</div>
          <div className="mt-1 text-[15px] text-muted">
            {last ? `Previous sleep · ${formatDuration(last.duration_sec)}` : "No sleep logged yet"}
          </div>
        </div>
      )}

      <input className="field" placeholder="Add a note" value={notes} onChange={(e) => setNotes(e.target.value)} />

      <PrimaryButton type="submit" tone="sleep" loading={sleep.isPending}>
        {active ? (
          <>
            <Sunrise size={20} strokeWidth={2.5} /> Wake up
          </>
        ) : (
          <>
            <Moon size={20} strokeWidth={2.5} /> Start sleep
          </>
        )}
      </PrimaryButton>
    </form>
  );
}
