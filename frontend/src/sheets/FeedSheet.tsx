import { useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { Minus, Plus } from "lucide-react";
import { BottomSheet } from "../components/BottomSheet";
import { Chip, Label, PrimaryButton, Press, Segmented } from "../components/ui";
import { useLogFeed } from "../lib/queries";
import { SIDE_LABEL } from "../components/EntryRow";
import type { BreastSide, FeedSubtype, Summary } from "../lib/types";
import { dayLabel, formatTime, localDateKey, parse } from "../lib/time";

const QUICK_AMOUNTS = [60, 90, 120, 150, 180];
const QUICK_AGO = [0, 15, 30, 60];

export function FeedSheet({ open, onClose, summary }: { open: boolean; onClose: () => void; summary?: Summary }) {
  return (
    <BottomSheet open={open} onClose={onClose} title="Log feed">
      {/* Remount on each open so smart defaults are re-read */}
      {open && <FeedForm onDone={onClose} summary={summary} />}
    </BottomSheet>
  );
}

function FeedForm({ onDone, summary }: { onDone: () => void; summary?: Summary }) {
  const last = summary?.last_feed;
  // Smart defaults: same rules as before — last subtype (Mother's if unknown) and last amount.
  const [subtype, setSubtype] = useState<FeedSubtype>(last?.subtype === "formula" ? "formula" : "breast_milk");
  const [amount, setAmount] = useState<string>(String(last?.amount_ml ?? 120));
  // Breastfeeding alternates sides, so suggest the opposite of the last one.
  const lastBreast = summary?.last_breast;
  const lastBreastAt = parse(lastBreast?.created_at);
  const [side, setSide] = useState<BreastSide | null>(
    lastBreast?.side === "left" ? "right" : lastBreast?.side === "right" ? "left" : null,
  );
  const [ago, setAgo] = useState(0);
  const [customAgo, setCustomAgo] = useState(false);
  const [notes, setNotes] = useState("");
  const log = useLogFeed();

  const ml = Math.max(0, parseInt(amount, 10) || 0);
  const color = subtype === "formula" ? "var(--formula)" : "var(--breast)";
  const step = (d: number) => setAmount(String(Math.max(0, ml + d)));
  const at = new Date(Date.now() - ago * 60_000);

  const breast = subtype === "breast_milk";
  const needsSide = breast && !side;

  const submit = () => {
    if (ml < 1 || needsSide) return;
    log.mutate(
      {
        subtype,
        side: breast ? side! : undefined,
        amount_ml: ml,
        notes: notes.trim() || undefined,
        created_at: ago ? at.toISOString() : undefined,
      },
      { onSuccess: onDone },
    );
  };

  return (
    <form
      className="flex flex-col gap-5 pb-2"
      onSubmit={(e) => {
        e.preventDefault();
        submit();
      }}
    >
      <Segmented
        value={subtype}
        onChange={setSubtype}
        options={[
          { value: "formula", label: "Formula", color: "var(--formula)" },
          { value: "breast_milk", label: "Mother's", color: "var(--breast)" },
        ]}
      />

      <AnimatePresence initial={false}>
        {breast && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="-mt-2 overflow-hidden"
          >
            <div className="pt-2">
              <Label>Breast</Label>
              <Segmented
                value={side}
                onChange={setSide}
                options={[
                  { value: "left", label: "Left", color: "var(--breast)" },
                  { value: "right", label: "Right", color: "var(--breast)" },
                ]}
              />
              {lastBreast?.side && lastBreastAt && (
                <p className="mt-2 px-1 text-[13px] text-muted">
                  Last: {SIDE_LABEL[lastBreast.side].toLowerCase()} · {dayLabel(localDateKey(lastBreastAt))}, {formatTime(lastBreastAt)}
                </p>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Big amount, Revolut-transfer style */}
      <div className="flex items-center justify-between gap-3 py-2">
        <Press
          aria-label="Less"
          onClick={() => step(-10)}
          className="grid size-12 shrink-0 place-items-center rounded-full bg-surface-2"
        >
          <Minus size={22} strokeWidth={2.6} />
        </Press>
        <div className="flex min-w-0 items-baseline justify-center">
          <motion.input
            key={subtype}
            initial={{ scale: 0.92, opacity: 0.6 }}
            animate={{ scale: 1, opacity: 1 }}
            aria-label="Amount in ml"
            inputMode="numeric"
            type="number"
            min={1}
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            onFocus={(e) => e.target.select()}
            className="w-[4ch] bg-transparent text-center text-[64px] font-bold leading-none tracking-tight tabular-nums outline-none"
            style={{ color, width: `${Math.max(2, amount.length) + 0.3}ch` }}
          />
          <span className="text-[24px] font-semibold text-muted">ml</span>
        </div>
        <Press
          aria-label="More"
          onClick={() => step(10)}
          className="grid size-12 shrink-0 place-items-center rounded-full bg-surface-2"
        >
          <Plus size={22} strokeWidth={2.6} />
        </Press>
      </div>

      <div className="-mx-5 flex gap-2 overflow-x-auto px-5 no-scrollbar">
        {QUICK_AMOUNTS.map((v) => (
          <Chip key={v} active={ml === v} onClick={() => setAmount(String(v))} className="flex-1">
            {v}
          </Chip>
        ))}
      </div>

      <div>
        <Label>When</Label>
        <div className="-mx-5 flex gap-2 overflow-x-auto px-5 no-scrollbar">
          {QUICK_AGO.map((v) => (
            <Chip
              key={v}
              active={!customAgo && ago === v}
              onClick={() => {
                setCustomAgo(false);
                setAgo(v);
              }}
            >
              {v === 0 ? "Now" : v < 60 ? `${v} min ago` : `${v / 60} h ago`}
            </Chip>
          ))}
          <Chip active={customAgo} onClick={() => setCustomAgo(true)}>
            Other
          </Chip>
        </div>
        <AnimatePresence initial={false}>
          {customAgo && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="overflow-hidden"
            >
              <div className="flex items-center gap-3 pt-3">
                <input
                  aria-label="Minutes ago"
                  className="field"
                  type="number"
                  inputMode="numeric"
                  min={0}
                  autoFocus
                  placeholder="Minutes ago"
                  value={ago || ""}
                  onChange={(e) => setAgo(Math.max(0, parseInt(e.target.value, 10) || 0))}
                />
                <span className="shrink-0 text-sm text-muted">min ago · {formatTime(at)}</span>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <input className="field" placeholder="Add a note" value={notes} onChange={(e) => setNotes(e.target.value)} />

      <PrimaryButton type="submit" loading={log.isPending} disabled={ml < 1 || needsSide} style={{ background: color }}>
        {needsSide ? "Choose a breast" : `Log ${ml} ml${breast ? ` · ${SIDE_LABEL[side!]}` : ""}${ago ? ` · ${formatTime(at)}` : ""}`}
      </PrimaryButton>
    </form>
  );
}
