import { motion } from "motion/react";
import type { Entry } from "../lib/types";

/** Tiny animated trend line of the recorded weights (oldest → newest). */
export function WeightSparkline({ entries, width = 120, height = 44 }: { entries: Entry[]; width?: number; height?: number }) {
  const pts = [...entries].reverse().map((e) => e.amount_ml ?? 0);
  const min = Math.min(...pts);
  const max = Math.max(...pts);
  const span = max - min || 1;
  const pad = 4;
  const coords = pts.map((v, i) => [
    pad + (i / Math.max(1, pts.length - 1)) * (width - pad * 2),
    pad + (1 - (v - min) / span) * (height - pad * 2),
  ]);
  const d = coords.map(([x, y], i) => `${i ? "L" : "M"}${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
  const last = coords.at(-1)!;
  const area = `${d} L${last[0].toFixed(1)},${height} L${coords[0][0].toFixed(1)},${height} Z`;

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} aria-hidden className="shrink-0 overflow-visible">
      <defs>
        <linearGradient id="wfill" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0" stopColor="var(--weight)" stopOpacity="0.35" />
          <stop offset="1" stopColor="var(--weight)" stopOpacity="0" />
        </linearGradient>
      </defs>
      <motion.path d={area} fill="url(#wfill)" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.6, duration: 0.6 }} />
      <motion.path
        d={d}
        fill="none"
        stroke="var(--weight)"
        strokeWidth={2.5}
        strokeLinecap="round"
        strokeLinejoin="round"
        initial={{ pathLength: 0 }}
        animate={{ pathLength: 1 }}
        transition={{ duration: 1.1, ease: "easeInOut", delay: 0.2 }}
      />
      <motion.circle
        cx={last[0]}
        cy={last[1]}
        r={4}
        fill="var(--weight)"
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        transition={{ delay: 1.2, type: "spring", stiffness: 500, damping: 18 }}
      />
    </svg>
  );
}
