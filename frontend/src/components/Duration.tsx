import NumberFlow, { NumberFlowGroup } from "@number-flow/react";
import { durationParts, formatDuration, secondsBetween } from "../lib/time";
import { useNow } from "../lib/hooks";

const unit = "text-[0.5em] font-semibold text-muted ml-[0.08em] mr-[0.25em]";
const two = { minimumIntegerDigits: 2 } as const;

/** "2h 14m" with rolling digits. Seconds shown only when `seconds` is set. */
export function DurationFlow({
  value,
  showSeconds = false,
  className = "",
}: {
  value: number;
  showSeconds?: boolean;
  className?: string;
}) {
  const { h, m, s } = durationParts(value);
  const d = Math.floor(h / 24);
  return (
    <NumberFlowGroup>
      <span className={`inline-flex items-baseline tabular-nums ${className}`}>
        {d >= 1 ? (
          <>
            <NumberFlow value={d} />
            <span className={unit}>d</span>
            <NumberFlow value={h % 24} />
            <span className={unit}>h</span>
          </>
        ) : (
          <>
            {h > 0 && (
              <>
                <NumberFlow value={h} />
                <span className={unit}>h</span>
              </>
            )}
            <NumberFlow value={m} format={h > 0 ? two : undefined} />
            <span className={unit}>m</span>
            {showSeconds && (
              <>
                <NumberFlow value={s} format={two} />
                <span className={unit}>s</span>
              </>
            )}
          </>
        )}
      </span>
    </NumberFlowGroup>
  );
}

export function Amount({ value, suffix, className = "" }: { value: number; suffix: string; className?: string }) {
  return (
    <span className={`inline-flex items-baseline tabular-nums ${className}`}>
      <NumberFlow value={value} locales="en-GB" />
      <span className={unit}>{suffix}</span>
    </span>
  );
}

/**
 * Ticking counters live in these leaf components so only they re-render every
 * second — not the whole screen around them.
 */
export function LiveDuration({ since, showSeconds = false, className = "" }: { since: Date; showSeconds?: boolean; className?: string }) {
  const now = useNow(1000);
  return <DurationFlow value={secondsBetween(since, now)} showSeconds={showSeconds} className={className} />;
}

export function LiveDurationText({ since }: { since: Date }) {
  const now = useNow(1000);
  return <>{formatDuration(secondsBetween(since, now))}</>;
}
