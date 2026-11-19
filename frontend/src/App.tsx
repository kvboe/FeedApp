import { useCallback, useEffect, useMemo, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { History as HistoryIcon, House, Settings as SettingsIcon } from "lucide-react";
import { Home } from "./screens/Home";
import { History } from "./screens/History";
import { Settings } from "./screens/Settings";
import { FeedSheet } from "./sheets/FeedSheet";
import { SleepSheet } from "./sheets/SleepSheet";
import { WeightSheet } from "./sheets/WeightSheet";
import { EditSheet } from "./sheets/EditSheet";
import { NavContext, TABS, tabFromPath, type Nav, type SheetKind, type Tab } from "./lib/nav";
import { useSummary } from "./lib/queries";
import { haptic } from "./lib/haptics";
import type { Entry } from "./lib/types";

const TAB_ITEMS: { id: Tab; label: string; icon: typeof House }[] = [
  { id: "home", label: "Home", icon: House },
  { id: "history", label: "History", icon: HistoryIcon },
  { id: "settings", label: "Settings", icon: SettingsIcon },
];

const order = (t: Tab) => TABS.findIndex((x) => x.id === t);

export function App() {
  const [tab, setTab] = useState<Tab>(() => tabFromPath(location.pathname));
  const [dir, setDir] = useState(0);
  const [sheet, setSheet] = useState<SheetKind | null>(null);
  const [editing, setEditing] = useState<Entry | null>(null);
  const { data: summary } = useSummary();

  // Path <-> tab sync (back button works, URLs are shareable)
  useEffect(() => {
    const onPop = () => {
      const next = tabFromPath(location.pathname);
      setTab((prev) => {
        setDir(order(next) - order(prev));
        return next;
      });
    };
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  // PWA shortcuts: /?action=feed|sleep|weight
  useEffect(() => {
    const action = new URLSearchParams(location.search).get("action");
    if (action === "feed" || action === "sleep" || action === "weight") {
      setSheet(action);
      history.replaceState(null, "", location.pathname);
    }
  }, []);

  const go = useCallback(
    (next: Tab) => {
      if (next === tab) {
        window.scrollTo({ top: 0, behavior: "smooth" });
        return;
      }
      haptic("tap");
      setDir(order(next) - order(tab));
      setTab(next);
      history.pushState(null, "", TABS.find((t) => t.id === next)!.path);
      window.scrollTo({ top: 0 });
    },
    [tab],
  );

  const nav = useMemo<Nav>(
    () => ({ tab, go, openSheet: setSheet, editEntry: setEditing }),
    [tab, go],
  );

  const closeSheet = useCallback(() => setSheet(null), []);
  const closeEdit = useCallback(() => setEditing(null), []);

  return (
    <NavContext.Provider value={nav}>
      <main className="mx-auto min-h-dvh max-w-lg overflow-x-clip px-4 pb-32 pt-safe">
        <AnimatePresence mode="popLayout" initial={false} custom={dir}>
          <motion.div
            key={tab}
            custom={dir}
            variants={{
              enter: (d: number) => ({ opacity: 0, x: d > 0 ? 60 : d < 0 ? -60 : 0 }),
              center: { opacity: 1, x: 0 },
              exit: (d: number) => ({ opacity: 0, x: d > 0 ? -60 : d < 0 ? 60 : 0 }),
            }}
            initial="enter"
            animate="center"
            exit="exit"
            transition={{ type: "spring", stiffness: 380, damping: 36 }}
          >
            {tab === "home" && <Home />}
            {tab === "history" && <History />}
            {tab === "settings" && <Settings />}
          </motion.div>
        </AnimatePresence>
      </main>

      <TabBar tab={tab} go={go} />

      <FeedSheet open={sheet === "feed"} onClose={closeSheet} summary={summary} />
      <SleepSheet open={sheet === "sleep"} onClose={closeSheet} summary={summary} />
      <WeightSheet open={sheet === "weight"} onClose={closeSheet} summary={summary} />
      <EditSheet entry={editing} onClose={closeEdit} />
    </NavContext.Provider>
  );
}

function TabBar({ tab, go }: { tab: Tab; go: (t: Tab) => void }) {
  return (
    <nav className="pointer-events-none fixed inset-x-0 bottom-0 z-40 flex justify-center px-4 pb-safe">
      <motion.div
        initial={{ y: 100 }}
        animate={{ y: 0 }}
        transition={{ type: "spring", stiffness: 300, damping: 30, delay: 0.15 }}
        className="pointer-events-auto mb-1 flex w-full max-w-sm items-center gap-1 rounded-full border border-line bg-surface/80 p-1.5 shadow-2xl shadow-black/30 backdrop-blur-2xl"
      >
        {TAB_ITEMS.map(({ id, label, icon: Icon }) => {
          const active = id === tab;
          return (
            <motion.button
              key={id}
              type="button"
              whileTap={{ scale: 0.92 }}
              onClick={() => go(id)}
              aria-current={active ? "page" : undefined}
              className={`relative flex h-12 flex-1 items-center justify-center gap-2 rounded-full text-[13px] font-semibold transition-colors ${
                active ? "text-fg" : "text-muted"
              }`}
            >
              {active && (
                <motion.span
                  layoutId="tab-pill"
                  className="absolute inset-0 rounded-full bg-surface-3"
                  transition={{ type: "spring", stiffness: 500, damping: 38 }}
                />
              )}
              <Icon size={20} strokeWidth={active ? 2.6 : 2.2} className="relative" />
              <AnimatePresence initial={false}>
                {active && (
                  <motion.span
                    className="relative overflow-hidden whitespace-nowrap"
                    initial={{ width: 0, opacity: 0 }}
                    animate={{ width: "auto", opacity: 1 }}
                    exit={{ width: 0, opacity: 0 }}
                    transition={{ type: "spring", stiffness: 500, damping: 40 }}
                  >
                    {label}
                  </motion.span>
                )}
              </AnimatePresence>
            </motion.button>
          );
        })}
      </motion.div>
    </nav>
  );
}
