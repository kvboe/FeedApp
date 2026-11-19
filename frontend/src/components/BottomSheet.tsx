import { useEffect, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { AnimatePresence, motion, useDragControls, type PanInfo } from "motion/react";
import { X } from "lucide-react";
import { Press } from "./ui";

interface Props {
  open: boolean;
  onClose: () => void;
  title?: ReactNode;
  children: ReactNode;
}

/**
 * iOS/Revolut-style bottom sheet: springs up, dims the page, drag the
 * handle (or the header) down to dismiss.
 */
export function BottomSheet({ open, onClose, title, children }: Props) {
  const drag = useDragControls();

  useEffect(() => {
    if (!open) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = prev;
      window.removeEventListener("keydown", onKey);
    };
  }, [open, onClose]);

  const onDragEnd = (_: unknown, info: PanInfo) => {
    if (info.offset.y > 120 || info.velocity.y > 600) onClose();
  };

  return createPortal(
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-50 flex items-end justify-center">
          <motion.div
            className="absolute inset-0 bg-black/60 backdrop-blur-[2px]"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.25 }}
            onClick={onClose}
          />
          <motion.div
            role="dialog"
            aria-modal="true"
            className="relative flex max-h-[92dvh] w-full max-w-lg flex-col rounded-t-[32px] bg-surface shadow-2xl"
            initial={{ y: "100%" }}
            animate={{ y: 0 }}
            exit={{ y: "100%" }}
            transition={{ type: "spring", stiffness: 380, damping: 38, mass: 0.9 }}
            drag="y"
            dragListener={false}
            dragControls={drag}
            dragConstraints={{ top: 0, bottom: 0 }}
            dragElastic={{ top: 0.05, bottom: 0.8 }}
            onDragEnd={onDragEnd}
          >
            <div
              className="shrink-0 cursor-grab touch-none px-5 pb-2 pt-2.5 active:cursor-grabbing"
              onPointerDown={(e) => drag.start(e)}
            >
              <div className="mx-auto h-1.5 w-10 rounded-full bg-surface-3" />
              <div className="mt-3 flex items-center justify-between gap-3">
                <h2 className="text-[22px] font-bold tracking-tight">{title}</h2>
                <Press
                  aria-label="Close"
                  onClick={onClose}
                  onPointerDown={(e) => e.stopPropagation()}
                  className="grid size-9 place-items-center rounded-full bg-surface-2 text-muted"
                >
                  <X size={18} strokeWidth={2.5} />
                </Press>
              </div>
            </div>
            <div className="overflow-y-auto overscroll-contain px-5 pb-safe pt-2">{children}</div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>,
    document.body,
  );
}
