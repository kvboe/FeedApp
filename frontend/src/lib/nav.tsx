import { createContext, useContext } from "react";
import type { Entry } from "./types";

export type Tab = "home" | "history" | "settings";
export type SheetKind = "feed" | "sleep" | "weight";

export interface Nav {
  tab: Tab;
  go: (tab: Tab) => void;
  openSheet: (kind: SheetKind) => void;
  editEntry: (entry: Entry) => void;
}

export const NavContext = createContext<Nav | null>(null);

export function useNav(): Nav {
  const ctx = useContext(NavContext);
  if (!ctx) throw new Error("useNav outside NavContext");
  return ctx;
}

export const TABS: { id: Tab; path: string }[] = [
  { id: "home", path: "/" },
  { id: "history", path: "/history" },
  { id: "settings", path: "/settings" },
];

export function tabFromPath(path: string): Tab {
  return TABS.find((t) => t.path === path)?.id ?? "home";
}
