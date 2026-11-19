import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { Trash2 } from "lucide-react";
import { BottomSheet } from "../components/BottomSheet";
import { EntryAvatar, entryMeta } from "../components/EntryRow";
import { Label, PrimaryButton, Segmented } from "../components/ui";
import { useDeleteEntry, useUpdateEntry } from "../lib/queries";
import type { BreastSide, Entry, FeedSubtype } from "../lib/types";
import { formatDateTime, formatDuration, fromLocalInputs, localDateKey, localTimeValue, parse } from "../lib/time";

export function EditSheet({ entry, onClose }: { entry: Entry | null; onClose: () => void }) {
  // Keep the last entry around while the sheet animates out.
  const [shown, setShown] = useState(entry);
  useEffect(() => {
    if (entry) setShown(entry);
  }, [entry]);

  const meta = shown ? entryMeta(shown, 18) : null;
  return (
    <BottomSheet
      open={!!entry}
      onClose={onClose}
      title={
        meta && (
          <span className="flex items-center gap-3">
            <EntryAvatar meta={meta} size="size-9" />
            {meta.label}
          </span>
        )
      }
    >
      {shown && <EditForm key={shown.id} entry={shown} onDone={onClose} />}
    </BottomSheet>
  );
}

function DateTimeRow({
  label,
  date,
  time,
  onDate,
  onTime,
}: {
  label: string;
  date: string;
  time: string;
  onDate: (v: string) => void;
  onTime: (v: string) => void;
}) {
  return (
    <div>
      <Label>{label}</Label>
      <div className="grid grid-cols-[1.4fr_1fr] gap-2">
        <input aria-label={`${label} date`} className="field" type="date" value={date} onChange={(e) => onDate(e.target.value)} />
        <input aria-label={`${label} time`} className="field" type="time" value={time} onChange={(e) => onTime(e.target.value)} />
      </div>
    </div>
  );
}

function split(iso: string | null): [string, string] {
  const d = parse(iso);
  return d ? [localDateKey(d), localTimeValue(d)] : ["", ""];
}

function EditForm({ entry, onDone }: { entry: Entry; onDone: () => void }) {
  const update = useUpdateEntry();
  const remove = useDeleteEntry();
  const [confirm, setConfirm] = useState(false);

  const isSleep = entry.type === "sleep";
  const [subtype, setSubtype] = useState<FeedSubtype>(entry.subtype === "breast_milk" ? "breast_milk" : "formula");
  const [side, setSide] = useState<BreastSide | null>(entry.side);
  const [amount, setAmount] = useState(String(entry.amount_ml ?? ""));
  const [[cDate, cTime], setCreated] = useState(split(entry.created_at));
  const [[sDate, sTime], setStarted] = useState(split(entry.started_at));
  const [[eDate, eTime], setEnded] = useState(split(entry.ended_at));
  const [notes, setNotes] = useState(entry.notes ?? "");

  useEffect(() => {
    if (!confirm) return;
    const t = window.setTimeout(() => setConfirm(false), 3000);
    return () => window.clearTimeout(t);
  }, [confirm]);

  // Only send what the user actually changed: re-sending untouched HH:MM
  // inputs would drop the stored seconds and silently shift sleep durations.
  const init = {
    created: split(entry.created_at),
    started: split(entry.started_at),
    ended: split(entry.ended_at),
  };
  const changed = (a: [string, string], b: [string, string]) => a[0] !== b[0] || a[1] !== b[1];
  const createdChanged = changed([cDate, cTime], init.created);
  const startedChanged = changed([sDate, sTime], init.started);
  const endedChanged = changed([eDate, eTime], init.ended);

  // Effective instants: stored value when untouched, parsed inputs otherwise.
  const startAt = startedChanged ? fromLocalInputs(sDate, sTime) : parse(entry.started_at);
  const endAt = endedChanged ? fromLocalInputs(eDate, eTime) : parse(entry.ended_at);
  const createdAt = createdChanged ? fromLocalInputs(cDate, cTime) : parse(entry.created_at);
  const amountNum = parseInt(amount, 10);

  let error: string | null = null;
  if (isSleep) {
    if (!startAt || !endAt) error = "Enter a full start and end date and time";
    else if (endAt < startAt) error = "End must be after start";
  } else {
    if (!createdAt) error = "Enter a full date and time";
    else if (!(amountNum >= 1)) error = entry.type === "weight" ? "Enter a weight in grams" : "Enter an amount in ml";
    // Older mother's-milk entries have no side; only demand one when switching from formula.
    else if (entry.type === "feed" && subtype === "breast_milk" && entry.subtype !== "breast_milk" && !side)
      error = "Choose a breast";
  }

  const sleepPreview = isSleep && startAt && endAt ? Math.max(0, Math.floor((endAt.getTime() - startAt.getTime()) / 1000)) : null;

  const save = () => {
    if (error) return;
    const body: Parameters<typeof update.mutate>[0] = { id: entry.id };
    const trimmed = notes.trim() || null;
    if (trimmed !== (entry.notes ?? null)) body.notes = trimmed;
    if (isSleep) {
      if (startedChanged) body.started_at = startAt!.toISOString();
      if (endedChanged) body.ended_at = endAt!.toISOString();
    } else {
      if (amountNum !== entry.amount_ml) body.amount_ml = amountNum;
      if (createdChanged) body.created_at = createdAt!.toISOString();
      if (entry.type === "feed" && subtype !== entry.subtype) body.subtype = subtype;
      if (entry.type === "feed" && subtype === "breast_milk" && side !== entry.side) body.side = side;
    }
    if (Object.keys(body).length === 1) {
      onDone(); // nothing changed
      return;
    }
    update.mutate(body, { onSuccess: onDone });
  };

  const created = parse(entry.created_at);

  return (
    <form
      className="flex flex-col gap-4 pb-2"
      onSubmit={(e) => {
        e.preventDefault();
        save();
      }}
    >
      <p className="-mt-1 px-1 text-[13px] text-muted">Logged {created ? formatDateTime(created) : ""}</p>

      {entry.type === "feed" && (
        <Segmented
          value={subtype}
          onChange={setSubtype}
          options={[
            { value: "formula", label: "Formula", color: "var(--formula)" },
            { value: "breast_milk", label: "Mother's", color: "var(--breast)" },
          ]}
        />
      )}

      <AnimatePresence initial={false}>
        {entry.type === "feed" && subtype === "breast_milk" && (
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
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {!isSleep && (
        <div>
          <Label htmlFor="edit-amount">{entry.type === "weight" ? "Weight (g)" : "Amount (ml)"}</Label>
          <input
            id="edit-amount"
            className="field text-[20px] font-semibold"
            type="number"
            inputMode="numeric"
            min={1}
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
          />
        </div>
      )}

      {isSleep ? (
        <>
          <DateTimeRow label="Start" date={sDate} time={sTime} onDate={(v) => setStarted([v, sTime])} onTime={(v) => setStarted([sDate, v])} />
          <DateTimeRow label="End" date={eDate} time={eTime} onDate={(v) => setEnded([v, eTime])} onTime={(v) => setEnded([eDate, v])} />
          <div className="flex items-center justify-between rounded-2xl bg-sleep/12 px-4 py-3 text-[15px]">
            <span className="text-muted">Duration</span>
            <span className="font-semibold text-sleep">{sleepPreview === null ? "—" : formatDuration(sleepPreview)}</span>
          </div>
        </>
      ) : (
        <DateTimeRow label="Time" date={cDate} time={cTime} onDate={(v) => setCreated([v, cTime])} onTime={(v) => setCreated([cDate, v])} />
      )}

      <div>
        <Label htmlFor="edit-notes">Notes</Label>
        <textarea id="edit-notes" className="field resize-none" rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} />
      </div>

      <AnimatePresence initial={false}>
        {error && (
          <motion.p
            role="alert"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden px-1 text-[14px] font-medium text-danger"
          >
            {error}
          </motion.p>
        )}
      </AnimatePresence>

      <PrimaryButton type="submit" loading={update.isPending} disabled={!!error}>
        Save changes
      </PrimaryButton>

      <PrimaryButton
        tone="danger"
        loading={remove.isPending}
        onClick={() => (confirm ? remove.mutate(entry, { onSuccess: onDone }) : setConfirm(true))}
      >
        <AnimatePresence mode="wait" initial={false}>
          <motion.span
            key={String(confirm)}
            initial={{ y: 14, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: -14, opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="flex items-center gap-2"
          >
            <Trash2 size={18} strokeWidth={2.4} />
            {confirm ? "Tap again to delete" : "Delete entry"}
          </motion.span>
        </AnimatePresence>
      </PrimaryButton>
    </form>
  );
}
