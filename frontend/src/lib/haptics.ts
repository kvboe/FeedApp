const patterns = {
  tap: 8,
  success: [12, 40, 18],
  error: [30, 50, 30],
} as const;

export function haptic(kind: keyof typeof patterns = "tap") {
  try {
    navigator.vibrate?.(patterns[kind] as number | number[]);
  } catch {
    /* unsupported */
  }
}
