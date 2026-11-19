import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, PAGE_SIZE, type PageCursor } from "./api";
import type { Entry, EntryFilters } from "./types";
import { useToast } from "../components/Toast";
import { haptic } from "./haptics";

export const keys = {
  summary: ["summary"] as const,
  entries: (f: Partial<EntryFilters>) => ["entries", f] as const,
  settings: ["settings"] as const,
};

export function useSummary() {
  return useQuery({
    queryKey: keys.summary,
    queryFn: api.summary,
    refetchInterval: 30_000, // same cadence as the original stats panel
  });
}

export function useEntries(filters: Partial<EntryFilters>, pageSize = PAGE_SIZE) {
  return useInfiniteQuery({
    queryKey: [...keys.entries(filters), pageSize],
    queryFn: ({ pageParam }) => api.entries(filters, pageParam, pageSize),
    initialPageParam: null as PageCursor | null,
    getNextPageParam: (last) => {
      const tail = last.items.at(-1);
      return last.has_more && tail ? { created_at: tail.created_at, id: tail.id } : undefined;
    },
    // Keyset paging can't repeat rows, but de-dupe defensively (React keys, day totals).
    select: (data) => {
      const seen = new Set<number>();
      return data.pages.flatMap((p) => p.items).filter((e) => !seen.has(e.id) && !!seen.add(e.id));
    },
  });
}

export function useSettings() {
  return useQuery({ queryKey: keys.settings, queryFn: api.settings });
}

/** Wraps a mutation with cache invalidation, a toast and a haptic tick. */
function useAction<TVars, TRes>(
  fn: (vars: TVars) => Promise<TRes>,
  success: string | ((res: TRes) => string),
) {
  const qc = useQueryClient();
  const toast = useToast();
  return useMutation({
    mutationFn: fn,
    onSuccess: (res) => {
      haptic("success");
      toast.show(typeof success === "function" ? success(res) : success, "success");
      return Promise.all([
        qc.invalidateQueries({ queryKey: keys.summary }),
        qc.invalidateQueries({ queryKey: ["entries"] }),
      ]);
    },
    onError: (err: Error) => {
      haptic("error");
      toast.show(err.message || "Something went wrong", "error");
      // e.g. 409 on sleep: someone else changed the state — show the truth.
      return Promise.all([
        qc.invalidateQueries({ queryKey: keys.summary }),
        qc.invalidateQueries({ queryKey: ["entries"] }),
      ]);
    },
  });
}

export const useLogFeed = () => useAction(api.logFeed, "Feed logged!");
export const useLogWeight = () => useAction(api.logWeight, "Weight logged!");
export const useSleepAction = () =>
  useAction(
    ({ action, notes }: { action: "start" | "stop"; notes?: string }) => api.sleep(action, notes),
    (r) => (r.active ? "Sleep started…" : "Sleep logged!"),
  );
export const useUpdateEntry = () =>
  useAction(
    ({ id, ...body }: { id: number } & Parameters<typeof api.updateEntry>[1]) => api.updateEntry(id, body),
    "Entry updated!",
  );
export const useDeleteEntry = () => useAction((e: Entry) => api.deleteEntry(e.id), "Entry deleted!");

export function useSaveSettings() {
  const qc = useQueryClient();
  const toast = useToast();
  return useMutation({
    mutationFn: api.saveSettings,
    onSuccess: (data) => {
      haptic("success");
      qc.setQueryData(keys.settings, data);
      toast.show("Settings saved", "success");
      return qc.invalidateQueries({ queryKey: keys.summary });
    },
    onError: (err: Error) => toast.show(err.message, "error"),
  });
}
