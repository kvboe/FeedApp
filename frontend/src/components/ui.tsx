import { useId, type ComponentProps, type ReactNode } from "react";
import { motion } from "motion/react";
import { haptic } from "../lib/haptics";

export const spring = { type: "spring", stiffness: 420, damping: 34 } as const;
export const softSpring = { type: "spring", stiffness: 260, damping: 30 } as const;

type PressProps = ComponentProps<typeof motion.button> & { haptics?: boolean };

/** Button with a tactile press-scale, used everywhere. */
export function Press({ haptics = true, onClick, className = "", ...props }: PressProps) {
  return (
    <motion.button
      type="button"
      whileTap={{ scale: 0.94 }}
      transition={spring}
      onClick={(e) => {
        if (haptics) haptic("tap");
        onClick?.(e);
      }}
      className={`disabled:opacity-40 disabled:pointer-events-none ${className}`}
      {...props}
    />
  );
}

export function PrimaryButton({
  children,
  className = "",
  tone = "accent",
  loading,
  disabled,
  ...props
}: PressProps & { tone?: "accent" | "sleep" | "neutral" | "danger"; loading?: boolean }) {
  const tones = {
    accent: "bg-accent text-white shadow-lg shadow-accent/25",
    sleep: "bg-sleep text-white shadow-lg shadow-sleep/25",
    neutral: "bg-surface-2 text-fg",
    danger: "bg-danger/12 text-danger",
  } as const;
  return (
    <Press
      className={`relative flex h-14 w-full items-center justify-center gap-2 overflow-hidden rounded-full text-[17px] font-semibold ${tones[tone]} ${className}`}
      {...props}
      // After the spread: a caller's disabled={false} must never unlock a pending save.
      disabled={loading || disabled}
      aria-busy={loading || undefined}
    >
      {loading ? <Spinner /> : (children as ReactNode)}
    </Press>
  );
}

export function Spinner({ className = "size-5" }: { className?: string }) {
  return (
    <motion.span
      className={`inline-block rounded-full border-2 border-current border-t-transparent ${className}`}
      animate={{ rotate: 360 }}
      transition={{ repeat: Infinity, duration: 0.7, ease: "linear" }}
    />
  );
}

export function Card({ children, className = "", ...props }: ComponentProps<typeof motion.section>) {
  return (
    <motion.section className={`rounded-[28px] bg-surface p-5 ${className}`} {...props}>
      {children}
    </motion.section>
  );
}

export function CardTitle({ children, action }: { children: ReactNode; action?: ReactNode }) {
  return (
    <div className="mb-3 flex items-center justify-between">
      <h2 className="text-[15px] font-semibold text-muted">{children}</h2>
      {action}
    </div>
  );
}

export function Segmented<T extends string>({
  value,
  onChange,
  options,
}: {
  value: T | null; // null = nothing selected yet
  onChange: (v: T) => void;
  options: { value: T; label: ReactNode; color?: string }[];
}) {
  const id = useId();
  return (
    <div className="relative grid rounded-full bg-surface-2 p-1" style={{ gridTemplateColumns: `repeat(${options.length}, 1fr)` }}>
      {options.map((o) => {
        const active = o.value === value;
        return (
          <button
            key={o.value}
            type="button"
            onClick={() => {
              haptic("tap");
              onChange(o.value);
            }}
            className={`relative z-10 flex h-10 items-center justify-center gap-1.5 rounded-full text-[15px] font-semibold transition-colors duration-200 ${
              active ? "text-white" : "text-muted"
            }`}
          >
            {active && (
              <motion.span
                layoutId={`seg-${id}`}
                transition={spring}
                className="absolute inset-0 -z-10 rounded-full"
                style={{ background: o.color ?? "var(--accent)" }}
              />
            )}
            {o.label}
          </button>
        );
      })}
    </div>
  );
}

export function Chip({
  active,
  children,
  onClick,
  className = "",
}: {
  active?: boolean;
  children: ReactNode;
  onClick?: () => void;
  className?: string;
}) {
  return (
    <Press
      onClick={onClick}
      className={`relative h-10 shrink-0 whitespace-nowrap rounded-full px-4 text-[15px] font-semibold transition-colors duration-200 ${
        active ? "bg-fg text-bg" : "bg-surface-2 text-fg"
      } ${className}`}
    >
      {children}
    </Press>
  );
}

export function Label({ children, htmlFor }: { children: ReactNode; htmlFor?: string }) {
  return (
    <label htmlFor={htmlFor} className="mb-1.5 block px-1 text-[13px] font-medium text-muted">
      {children}
    </label>
  );
}

export function Skeleton({ className = "" }: { className?: string }) {
  return (
    <motion.div
      className={`rounded-2xl bg-surface-2 ${className}`}
      animate={{ opacity: [0.5, 1, 0.5] }}
      transition={{ repeat: Infinity, duration: 1.4, ease: "easeInOut" }}
    />
  );
}
