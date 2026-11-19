import type { ReactNode } from "react";
import { motion } from "motion/react";
import { Droplet, Milk, Moon, Pin, Weight } from "lucide-react";
import type { BreastSide, Entry } from "../lib/types";
import { formatDuration, formatTime, parse } from "../lib/time";

export const SIDE_LABEL: Record<BreastSide, string> = { left: "Left", right: "Right" };

export interface EntryMeta {
  label: string;
  color: string;
  icon: ReactNode;
  value: string;
}

export function entryMeta(e: Entry, size = 20): EntryMeta {
  if (e.type === "feed") {
    const breast = e.subtype === "breast_milk";
    return {
      label: breast ? (e.side ? `${SIDE_LABEL[e.side]} breast` : "Mother's milk") : "Formula",
      color: breast ? "var(--breast)" : "var(--formula)",
      icon: breast ? <Droplet size={size} strokeWidth={2.4} /> : <Milk size={size} strokeWidth={2.4} />,
      value: `${e.amount_ml ?? 0} ml`,
    };
  }
  if (e.type === "sleep") {
    return {
      label: "Sleep",
      color: "var(--sleep)",
      icon: <Moon size={size} strokeWidth={2.4} />,
      value: formatDuration(e.duration_sec),
    };
  }
  if (e.type === "weight") {
    return {
      label: "Weight",
      color: "var(--weight)",
      icon: <Weight size={size} strokeWidth={2.4} />,
      value: `${(e.amount_ml ?? 0).toLocaleString("en-GB")} g`,
    };
  }
  return { label: e.type, color: "var(--muted)", icon: <Pin size={size} />, value: "" };
}

export function EntryAvatar({ meta, size = "size-11" }: { meta: EntryMeta; size?: string }) {
  return (
    <span
      className={`grid ${size} shrink-0 place-items-center rounded-full`}
      style={{ color: meta.color, background: `color-mix(in srgb, ${meta.color} 16%, transparent)` }}
    >
      {meta.icon}
    </span>
  );
}

/** Transaction-style row: avatar · title/subtitle · value. */
export function EntryRow({ entry, onClick, index = 0 }: { entry: Entry; onClick?: () => void; index?: number }) {
  const meta = entryMeta(entry);
  const created = parse(entry.created_at);
  const sleepRange =
    entry.type === "sleep" && entry.started_at && entry.ended_at
      ? `${formatTime(parse(entry.started_at)!)} – ${formatTime(parse(entry.ended_at)!)}`
      : null;

  return (
    <motion.li
      layout="position"
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, x: -40, height: 0, marginTop: 0, transition: { duration: 0.25 } }}
      transition={{ type: "spring", stiffness: 400, damping: 34, delay: Math.min(index, 12) * 0.03 }}
      className="list-none"
    >
      <motion.button
        type="button"
        onClick={onClick}
        whileTap={{ scale: 0.98, backgroundColor: "var(--surface-2)" }}
        className="flex w-full items-center gap-3.5 rounded-2xl px-2 py-2.5 text-left"
      >
        <EntryAvatar meta={meta} />
        <div className="min-w-0 flex-1">
          <div className="truncate text-[16px] font-semibold">{meta.label}</div>
          <div className="truncate text-[13px] text-muted">
            {sleepRange ?? (created ? formatTime(created) : "")}
            {entry.time_since_prev ? <span className="text-faint"> · +{formatDuration(entry.time_since_prev)}</span> : null}
            {entry.notes ? <span> · {entry.notes}</span> : null}
          </div>
        </div>
        <div className="shrink-0 text-right text-[16px] font-semibold tabular-nums">{meta.value}</div>
      </motion.button>
    </motion.li>
  );
}
