// Pure lifting math, kept out of components so it can be unit tested.

export type Unit = "lb" | "kg";

export interface LogEntry {
  id: number;
  exercise_id: number;
  weight: number;
  unit: Unit;
  reps: number;
  sets: number;
  performed_at: string;
}

export type Metric = "top" | "e1rm" | "volume";

export const METRICS: { value: Metric; label: string; hint: string }[] = [
  { value: "top", label: "Top weight", hint: "Heaviest weight logged that day" },
  { value: "e1rm", label: "Est. 1RM", hint: "Estimated one-rep max (Epley formula)" },
  { value: "volume", label: "Volume", hint: "Weight × reps × sets, summed for the day" },
];

const LB_PER_KG = 2.2046226218;

export function convert(weight: number, from: Unit, to: Unit): number {
  if (from === to) return weight;
  return from === "kg" ? weight * LB_PER_KG : weight / LB_PER_KG;
}

/** Epley: weight × (1 + reps / 30). A single rep is the weight itself. */
export function estimatedOneRepMax(weight: number, reps: number): number {
  return reps <= 1 ? weight : weight * (1 + reps / 30);
}

export function entryValue(entry: LogEntry, metric: Metric, unit: Unit): number {
  const w = convert(entry.weight, entry.unit, unit);
  if (metric === "top") return w;
  if (metric === "e1rm") return estimatedOneRepMax(w, entry.reps);
  return w * entry.reps * entry.sets;
}

/** Local calendar day, YYYY-MM-DD, so a late-night session doesn't land on "tomorrow" in UTC. */
export function dayKey(iso: string): string {
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

/** Today as YYYY-MM-DD in local time, for a date input's value and max. */
export function today(now = new Date()): string {
  return dayKey(now.toISOString());
}

/**
 * The moment to store for a date picked in a date input: that local day, at the time of day
 * taken from `timeFrom` (now for a new entry, the entry's own time when moving one).
 */
export function atDay(day: string, timeFrom: Date = new Date()): string {
  const [y, m, d] = day.split("-").map(Number) as [number, number, number];
  const moment = new Date(timeFrom);
  moment.setFullYear(y, m - 1, d);
  return moment.toISOString();
}

export function formatDay(day: string): string {
  return new Date(`${day}T12:00:00`).toLocaleDateString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
}

export interface DayPoint {
  day: string;
  value: number;
}

/** One point per day, oldest first: the best entry (top, e1rm) or the total (volume). */
export function dailySeries(entries: LogEntry[], metric: Metric, unit: Unit): DayPoint[] {
  const byDay = new Map<string, number>();
  for (const e of entries) {
    const key = dayKey(e.performed_at);
    const v = entryValue(e, metric, unit);
    const prev = byDay.get(key);
    if (prev === undefined) byDay.set(key, v);
    else byDay.set(key, metric === "volume" ? prev + v : Math.max(prev, v));
  }
  return [...byDay.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([day, value]) => ({ day, value: Math.round(value * 10) / 10 }));
}

/** Plate-friendly step for the weight stepper. */
export function weightStep(unit: Unit): number {
  return unit === "kg" ? 2.5 : 5;
}

export function formatWeight(weight: number, unit: Unit): string {
  const rounded = Math.round(weight * 100) / 100;
  return `${rounded.toLocaleString(undefined, { maximumFractionDigits: 2 })} ${unit}`;
}

export function formatEntry(e: LogEntry): string {
  return `${formatWeight(e.weight, e.unit)} × ${e.reps} reps × ${e.sets} ${e.sets === 1 ? "set" : "sets"}`;
}

export function relativeDay(iso: string, now = new Date()): string {
  const days = Math.round(
    (new Date(dayKey(now.toISOString())).getTime() - new Date(dayKey(iso)).getTime()) / 86_400_000,
  );
  if (days <= 0) return "Today";
  if (days === 1) return "Yesterday";
  if (days < 7) return `${days} days ago`;
  return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

/** Every search word must appear in the exercise's name, equipment or muscle group. */
export function matches(
  query: string,
  ex: { name: string; equipment: string; muscle_group: string },
): boolean {
  const hay = `${ex.name} ${ex.equipment} ${ex.muscle_group}`.toLowerCase().replace(/-/g, " ");
  return query
    .toLowerCase()
    .replace(/-/g, " ")
    .split(/\s+/)
    .filter(Boolean)
    .every((word) => hay.includes(word));
}
