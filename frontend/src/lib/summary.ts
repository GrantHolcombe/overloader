// Weekly training summary: totals for a week and per muscle group, compared with the week
// before. Pure functions over log entries (each with its exercise), so the muscle-group heat map
// can reuse the per-group totals later.
import { dayKey, liftMetrics, setsOf, shiftDay, type LogEntry, type Unit } from "./lifting";

/** Always listed, trained or not, so a skipped group stands out. Others appear when logged. */
export const MAIN_GROUPS = ["Chest", "Back", "Legs", "Shoulders", "Arms", "Core"] as const;

export type SummaryEntry = LogEntry & { exercise: { id: number; name: string; muscle_group: string } };

export interface Totals {
  /** Distinct days with at least one entry. */
  days: number;
  sets: number;
  reps: number;
  /** Weight × reps over every set, in the display unit. Bodyweight sets (0) add sets, not volume. */
  volume: number;
  /** Exercise names, in the order first done. */
  exercises: string[];
}

export interface GroupRow extends Totals {
  group: string;
  /** The same group in the week before. */
  previous: Totals;
}

export interface WeekSummary {
  /** Monday, YYYY-MM-DD. */
  start: string;
  total: Totals;
  previous: Totals;
  /** Most sets first; untrained main groups last, in body order. */
  groups: GroupRow[];
}

/** The Monday on or before a day (weeks run Monday to Sunday). */
export function weekStart(day: string): string {
  const [y, m, d] = day.split("-").map(Number) as [number, number, number];
  const weekday = new Date(y, m - 1, d, 12).getDay(); // 0 = Sunday
  return shiftDay(day, -((weekday + 6) % 7));
}

/** "Nov 23 – 29", or "Nov 30 – Dec 6" across a month. */
export function formatWeek(start: string): string {
  const end = shiftDay(start, 6);
  const at = (day: string) => new Date(`${day}T12:00:00`);
  const month = (day: string) => at(day).toLocaleDateString(undefined, { month: "short" });
  const date = (day: string) => at(day).getDate();
  return month(start) === month(end)
    ? `${month(start)} ${date(start)} – ${date(end)}`
    : `${month(start)} ${date(start)} – ${month(end)} ${date(end)}`;
}

const empty = (): Totals => ({ days: 0, sets: 0, reps: 0, volume: 0, exercises: [] });

export function totals(entries: SummaryEntry[], unit: Unit): Totals {
  const t = empty();
  const days = new Set<string>();
  for (const entry of entries) {
    days.add(dayKey(entry.performed_at));
    const sets = setsOf(entry);
    t.sets += sets.length;
    t.reps += sets.reduce((sum, s) => sum + s.reps, 0);
    t.volume += liftMetrics(entry, unit).volume;
    if (!t.exercises.includes(entry.exercise.name)) t.exercises.push(entry.exercise.name);
  }
  t.days = days.size;
  return t;
}

function byGroup(entries: SummaryEntry[]): Map<string, SummaryEntry[]> {
  const groups = new Map<string, SummaryEntry[]>();
  for (const entry of entries) {
    const list = groups.get(entry.exercise.muscle_group) ?? [];
    list.push(entry);
    groups.set(entry.exercise.muscle_group, list);
  }
  return groups;
}

/**
 * Summarizes the week starting `start` (a Monday) against the week before it. `entries` may
 * cover both weeks (and nothing else matters: they're split by local day).
 */
export function summarizeWeek(entries: SummaryEntry[], start: string, unit: Unit): WeekSummary {
  const sorted = [...entries].sort((a, b) => a.performed_at.localeCompare(b.performed_at));
  const prevStart = shiftDay(start, -7);
  const end = shiftDay(start, 7);
  const inRange = (from: string, to: string) =>
    sorted.filter((e) => {
      const day = dayKey(e.performed_at);
      return day >= from && day < to;
    });
  const thisWeek = inRange(start, end);
  const lastWeek = inRange(prevStart, start);

  const now = byGroup(thisWeek);
  const before = byGroup(lastWeek);
  const names = new Set<string>([...MAIN_GROUPS, ...now.keys(), ...before.keys()]);
  const order = (g: string) => {
    const i = (MAIN_GROUPS as readonly string[]).indexOf(g);
    return i === -1 ? MAIN_GROUPS.length : i;
  };
  const groups = [...names]
    .map((group) => ({
      group,
      ...totals(now.get(group) ?? [], unit),
      previous: totals(before.get(group) ?? [], unit),
    }))
    .sort((a, b) => b.sets - a.sets || order(a.group) - order(b.group) || a.group.localeCompare(b.group));

  return { start, total: totals(thisWeek, unit), previous: totals(lastWeek, unit), groups };
}

/** "+3", "−2" or "" for no change, for "vs last week" labels. */
export function signed(diff: number, format: (n: number) => string = String): string {
  if (Math.abs(diff) < 0.005) return "";
  return `${diff > 0 ? "+" : "−"}${format(Math.abs(diff))}`;
}

/** Big volumes read better short: 8,450 → "8,450", 124,300 → "124K". */
export function compact(n: number): string {
  return Math.round(n).toLocaleString(undefined, n >= 100_000 ? { notation: "compact", maximumFractionDigits: 1 } : {});
}
