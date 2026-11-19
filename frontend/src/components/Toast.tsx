import { createContext, useCallback, useContext, useMemo, useRef, useState, type ReactNode } from "react";
import { AnimatePresence, motion } from "motion/react";
import { Check, CircleAlert, Info } from "lucide-react";

type Kind = "success" | "error" | "info";
interface ToastItem {
  id: number;
  message: string;
  kind: Kind;
}

const Ctx = createContext<{ show: (message: string, kind?: Kind) => void } | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toast, setToast] = useState<ToastItem | null>(null);
  const timer = useRef<number | undefined>(undefined);

  const show = useCallback((message: string, kind: Kind = "info") => {
    window.clearTimeout(timer.current);
    setToast({ id: Date.now(), message, kind });
    timer.current = window.setTimeout(() => setToast(null), 2200);
  }, []);

  const value = useMemo(() => ({ show }), [show]);

  return (
    <Ctx.Provider value={value}>
      {children}
      <div className="pointer-events-none fixed inset-x-0 top-0 z-[100] flex justify-center pt-safe">
        <AnimatePresence mode="popLayout">
          {toast && (
            <motion.div
              key={toast.id}
              role="status"
              initial={{ y: -60, opacity: 0, scale: 0.9 }}
              animate={{ y: 8, opacity: 1, scale: 1 }}
              exit={{ y: -40, opacity: 0, scale: 0.95 }}
              transition={{ type: "spring", stiffness: 500, damping: 32 }}
              className="pointer-events-auto flex items-center gap-2.5 rounded-full bg-surface-3/95 py-2.5 pl-2.5 pr-5 text-sm font-semibold text-fg shadow-2xl shadow-black/40 backdrop-blur-xl"
              onClick={() => setToast(null)}
            >
              <motion.span
                initial={{ scale: 0, rotate: -90 }}
                animate={{ scale: 1, rotate: 0 }}
                transition={{ delay: 0.08, type: "spring", stiffness: 600, damping: 20 }}
                className={`grid size-7 place-items-center rounded-full text-white ${
                  toast.kind === "success" ? "bg-success" : toast.kind === "error" ? "bg-danger" : "bg-accent"
                }`}
              >
                {toast.kind === "success" ? (
                  <Check size={16} strokeWidth={3} />
                ) : toast.kind === "error" ? (
                  <CircleAlert size={16} strokeWidth={2.5} />
                ) : (
                  <Info size={16} strokeWidth={2.5} />
                )}
              </motion.span>
              {toast.message}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </Ctx.Provider>
  );
}

export function useToast() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useToast outside ToastProvider");
  return ctx;
}
