import { useEffect, useState, type ReactNode } from "react";
import { motion } from "motion/react";
import { Baby, Moon, Smartphone, Sun } from "lucide-react";
import { Card, CardTitle, Label, PrimaryButton, Segmented, Skeleton } from "../components/ui";
import { useSaveSettings, useSettings } from "../lib/queries";
import { ageDays, ageLabel, localDateKey } from "../lib/time";

type Theme = "system" | "dark" | "light";
const THEME_KEY = "feedapp.theme";

function readTheme(): Theme {
  try {
    const t = localStorage.getItem(THEME_KEY);
    return t === "dark" || t === "light" ? t : "system";
  } catch {
    return "system";
  }
}

export function applyTheme(t: Theme) {
  const root = document.documentElement;
  if (t === "system") delete root.dataset.theme;
  else root.dataset.theme = t;
  try {
    if (t === "system") localStorage.removeItem(THEME_KEY);
    else localStorage.setItem(THEME_KEY, t);
  } catch {
    /* ignore */
  }
}

const item = {
  hidden: { opacity: 0, y: 20 },
  show: (i: number) => ({ opacity: 1, y: 0, transition: { delay: i * 0.07, type: "spring" as const, stiffness: 260, damping: 28 } }),
} as const;

export function Settings() {
  const { data, isLoading } = useSettings();
  const save = useSaveSettings();
  const [birthdate, setBirthdate] = useState("");
  const [theme, setTheme] = useState<Theme>(readTheme);

  useEffect(() => {
    if (data) setBirthdate(data.birthdate ?? "");
  }, [data]);

  const day = ageDays(birthdate || null);
  const age = ageLabel(birthdate || null);
  const dirty = (data?.birthdate ?? "") !== birthdate;

  return (
    <div>
      <motion.h1 initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="px-1 pb-4 pt-2 text-[34px] font-bold tracking-tight">
        Settings
      </motion.h1>

      <div className="flex flex-col gap-3">
        <Card custom={0} variants={item} initial="hidden" animate="show">
          <div className="flex items-center gap-4">
            <motion.span
              className="grid size-16 place-items-center rounded-full bg-gradient-to-br from-accent to-accent-2 text-white shadow-xl shadow-accent/30"
              animate={{ rotate: [0, -6, 6, 0] }}
              transition={{ delay: 0.4, duration: 0.9 }}
            >
              <Baby size={30} strokeWidth={2.2} />
            </motion.span>
            <div>
              <div className="text-[22px] font-bold tracking-tight">{day !== null && day >= 0 ? `Day ${day}` : "Baby profile"}</div>
              <div className="text-[15px] text-muted">{age ?? "Add a birth date to see age"}</div>
            </div>
          </div>
        </Card>

        <Card custom={1} variants={item} initial="hidden" animate="show">
          <CardTitle>Baby profile</CardTitle>
          {isLoading ? (
            <Skeleton className="h-28" />
          ) : (
            <form
              className="flex flex-col gap-4"
              onSubmit={(e) => {
                e.preventDefault();
                save.mutate({ birthdate: birthdate || null });
              }}
            >
              <div>
                <Label htmlFor="birthdate">Birth date</Label>
                <input
                  id="birthdate"
                  type="date"
                  className="field"
                  value={birthdate}
                  max={localDateKey(new Date())}
                  onChange={(e) => setBirthdate(e.target.value)}
                />
              </div>
              <PrimaryButton type="submit" loading={save.isPending} disabled={!dirty}>
                Save
              </PrimaryButton>
            </form>
          )}
        </Card>

        <Card custom={2} variants={item} initial="hidden" animate="show">
          <CardTitle>Appearance</CardTitle>
          <Segmented<Theme>
            value={theme}
            onChange={(t) => {
              setTheme(t);
              applyTheme(t);
            }}
            options={[
              { value: "system", label: <Ico icon={<Smartphone size={16} strokeWidth={2.4} />}>Auto</Ico> },
              { value: "dark", label: <Ico icon={<Moon size={16} strokeWidth={2.4} />}>Dark</Ico> },
              { value: "light", label: <Ico icon={<Sun size={16} strokeWidth={2.4} />}>Light</Ico> },
            ]}
          />
        </Card>

        <motion.p custom={3} variants={item} initial="hidden" animate="show" className="px-2 pt-2 text-center text-[13px] text-faint">
          FeedApp 2.0 · Add to Home Screen to install
        </motion.p>
      </div>
    </div>
  );
}

function Ico({ icon, children }: { icon: ReactNode; children: ReactNode }) {
  return (
    <span className="flex items-center gap-1.5">
      {icon}
      {children}
    </span>
  );
}
