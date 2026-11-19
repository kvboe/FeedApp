import { useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { BottomSheet } from "../components/BottomSheet";
import { PrimaryButton } from "../components/ui";
import { useLogWeight } from "../lib/queries";
import type { Summary } from "../lib/types";
import { formatDateTime, parse } from "../lib/time";

export function WeightSheet({ open, onClose, summary }: { open: boolean; onClose: () => void; summary?: Summary }) {
  return (
    <BottomSheet open={open} onClose={onClose} title="Log weight">
      {open && <WeightForm onDone={onClose} summary={summary} />}
    </BottomSheet>
  );
}

function WeightForm({ onDone, summary }: { onDone: () => void; summary?: Summary }) {
  const last = summary?.last_weight;
  const [grams, setGrams] = useState("");
  const [notes, setNotes] = useState("");
  const log = useLogWeight();
  const g = parseInt(grams, 10) || 0;
  const delta = last?.amount_ml && g ? g - last.amount_ml : null;
  const lastAt = parse(last?.created_at);

  return (
    <form
      className="flex flex-col gap-5 pb-2"
      onSubmit={(e) => {
        e.preventDefault();
        if (g >= 1) log.mutate({ weight_g: g, notes: notes.trim() || undefined }, { onSuccess: onDone });
      }}
    >
      <div className="flex flex-col items-center py-3">
        <div className="flex items-baseline">
          <input
            aria-label="Weight in grams"
            autoFocus
            type="number"
            inputMode="numeric"
            min={1}
            placeholder={String(last?.amount_ml ?? 3500)}
            value={grams}
            onChange={(e) => setGrams(e.target.value)}
            className="bg-transparent text-center text-[64px] font-bold leading-none tracking-tight text-weight tabular-nums outline-none placeholder:text-faint"
            style={{ width: `${Math.max(4, (grams || String(last?.amount_ml ?? 3500)).length) + 0.3}ch` }}
          />
          <span className="text-[24px] font-semibold text-muted">g</span>
        </div>
        <div className="mt-2 h-6 text-[15px] font-medium">
          <AnimatePresence mode="wait">
            {delta !== null ? (
              <motion.span
                key="delta"
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className={delta >= 0 ? "text-success" : "text-danger"}
              >
                {delta >= 0 ? "+" : "−"}
                {Math.abs(delta).toLocaleString("en-GB")} g since last time
              </motion.span>
            ) : (
              <motion.span key="last" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="text-muted">
                {last && lastAt ? `Last: ${last.amount_ml?.toLocaleString("en-GB")} g · ${formatDateTime(lastAt)}` : "First weigh-in"}
              </motion.span>
            )}
          </AnimatePresence>
        </div>
      </div>

      <input className="field" placeholder="Add a note" value={notes} onChange={(e) => setNotes(e.target.value)} />

      <PrimaryButton type="submit" loading={log.isPending} disabled={g < 1} style={{ background: "var(--weight)", color: "#1a1200" }}>
        Save
      </PrimaryButton>
    </form>
  );
}
