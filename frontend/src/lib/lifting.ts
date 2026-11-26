// Pure lifting math, kept out of components so it can be unit tested.

export type Unit = "lb" | "kg";

export interface SetValues {
  weight: number;
  reps: number;
}

export interface LogEntry {
  id: number;
  exercise_id: number;
  /** For a per-set entry: the heaviest set's weight and reps, and the number of sets. */
  weight: number;
  unit: Unit;
  reps: number;
  sets: number;
  /** Empty for a quick entry (every set the same weight and reps). */
  set_details: SetValues[];
  performed_at: string;
}

export type Metric = "top" | "e1rm" | "volume";

export const METRICS: { value: Metric; label: string; hint: string }[] = [
  { value: "top", label: "Top weight", hint: "Heaviest weight logged that day" },
  { value: "e1rm", label: "Est. 1RM", hint: "Estimated one-rep max (Epley formula)" },
  { value: "volume", label: "Volume", hint: "Weight × reps of every set, summed for the day" },
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

/** A quick entry or a lift on the form; set_details, when present, wins over weight/reps/sets. */
export interface LiftValues {
  weight: number;
  unit: Unit;
  reps: number;
  sets: number;
  set_details?: SetValues[];
}

/** Every set of a lift, in its own unit (a quick entry's sets are all the same). */
export function setsOf(lift: LiftValues): SetValues[] {
  if (lift.set_details?.length) return lift.set_details;
  return Array.from({ length: lift.sets }, () => ({ weight: lift.weight, reps: lift.reps }));
}

/** A quick summary of per-set detail, as the API stores it: the heaviest set (the first one
 * if several tie) and how many sets. Used when switching the form from per set to quick. */
export function summarizeSets(sets: SetValues[]): { weight: number; reps: number; sets: number } {
  const top = sets.reduce((best, s) => (s.weight > best.weight ? s : best), sets[0]!);
  return { weight: top.weight, reps: top.reps, sets: sets.length };
}

/** True when every set has a weight of 0–5000 and 1–1000 whole reps (what the API accepts). */
export function validSets(sets: SetValues[]): boolean {
  return (
    sets.length >= 1 &&
    sets.length <= 100 &&
    sets.every(
      (s) =>
        Number.isFinite(s.weight) &&
        s.weight >= 0 &&
        s.weight <= 5000 &&
        Number.isInteger(s.reps) &&
        s.reps >= 1 &&
        s.reps <= 1000,
    )
  );
}

/** Top weight, best est. 1RM and total volume of a lift, converted to `unit`. */
export function liftMetrics(lift: LiftValues, unit: Unit): Record<Metric, number> {
  let top = 0;
  let e1rm = 0;
  let volume = 0;
  for (const set of setsOf(lift)) {
    const w = convert(set.weight, lift.unit, unit);
    top = Math.max(top, w);
    e1rm = Math.max(e1rm, estimatedOneRepMax(w, set.reps));
    volume += w * set.reps;
  }
  return { top, e1rm, volume };
}

export function entryValue(entry: LogEntry, metric: Metric, unit: Unit): number {
  return liftMetrics(entry, unit)[metric];
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

/** Local midnight at the start of a day and of the next one, as ISO timestamps. */
export function dayRange(day: string): [string, string] {
  const [y, m, d] = day.split("-").map(Number) as [number, number, number];
  return [new Date(y, m - 1, d).toISOString(), new Date(y, m - 1, d + 1).toISOString()];
}

/** The day `n` days after (or before, if negative) a YYYY-MM-DD day. */
export function shiftDay(day: string, n: number): string {
  const [y, m, d] = day.split("-").map(Number) as [number, number, number];
  return dayKey(new Date(y, m - 1, d + n, 12).toISOString());
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

/** Compact form for lists that show several entries on one line: "105 lb × 8 × 3". */
export function formatShort(e: LogEntry): string {
  if (e.set_details.length) return formatSets(e);
  return `${formatWeight(e.weight, e.unit)} × ${e.reps} × ${e.sets}`;
}

const num = (n: number) => (Math.round(n * 100) / 100).toLocaleString(undefined, { maximumFractionDigits: 2 });

/** Per-set entries list each set: "135×10, 155×6, 145×8 lb". */
function formatSets(e: LiftValues): string {
  return `${setsOf(e).map((s) => `${num(s.weight)}×${s.reps}`).join(", ")} ${e.unit}`;
}

export function formatEntry(e: LogEntry): string {
  if (e.set_details.length) return `${e.sets} ${e.sets === 1 ? "set" : "sets"}: ${formatSets(e)}`;
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

// ---------------------------------------------------------------------------------------------
// Personal records and "beat last time"
// ---------------------------------------------------------------------------------------------

export type PRKind = "weight" | "e1rm" | "volume";

export const PR_LABELS: Record<PRKind, string> = {
  weight: "Heaviest weight",
  e1rm: "Best est. 1RM",
  volume: "Most volume",
};

// Entries can be in different units, so records are compared in kg. Anything closer than this
// counts as a tie, and a tie isn't a new record.
const EPSILON_KG = 0.01;

function inKg(lift: LiftValues): Record<PRKind, number> {
  const m = liftMetrics(lift, "kg");
  return { weight: m.top, e1rm: m.e1rm, volume: m.volume };
}

const KINDS: PRKind[] = ["weight", "e1rm", "volume"];

function chronological(entries: LogEntry[]): LogEntry[] {
  return [...entries].sort((a, b) => a.performed_at.localeCompare(b.performed_at) || a.id - b.id);
}

/**
 * Which entries set a record when they were logged: each one is compared with every entry
 * before it in time. The very first entry is the baseline, not a record.
 */
export function personalRecords(entries: LogEntry[]): Map<number, PRKind[]> {
  const records = new Map<number, PRKind[]>();
  let best: Record<PRKind, number> | null = null;
  for (const entry of chronological(entries)) {
    const m = inKg(entry);
    if (best === null) {
      best = m;
      continue;
    }
    const current = best;
    const beaten = KINDS.filter((k) => m[k] > current[k] + EPSILON_KG);
    if (beaten.length) records.set(entry.id, beaten);
    for (const k of KINDS) current[k] = Math.max(current[k], m[k]);
  }
  return records;
}

/** The records a lift would set if it were logged now (none when there's no history yet). */
export function wouldSetRecords(lift: LiftValues, entries: LogEntry[]): PRKind[] {
  if (!entries.length) return [];
  const m = inKg(lift);
  const history = entries.map(inKg);
  return KINDS.filter((k) => history.every((h) => m[k] > h[k] + EPSILON_KG));
}

/** The latest entry before a moment ("last time" when backfilling a past day). */
export function entryBefore(entries: LogEntry[], iso: string): LogEntry | undefined {
  const before = chronological(entries).filter((e) => e.performed_at < iso);
  return before.at(-1);
}

export interface Comparison {
  status: "beat" | "match" | "below";
  /**
   * "quick" when both are quick entries: weight and reps per set. "sets" when either is per
   * set: the top set's weight and the total reps.
   */
  basis: "quick" | "sets";
  /** In the lift's own unit. */
  weightDiff: number;
  repsDiff: number;
  setsDiff: number;
}

/**
 * How a lift compares with last time. Est. 1RM decides, so fewer reps at a heavier weight can
 * still count as progress; if that's a tie, more total volume (an extra set) wins.
 */
export function compareToLast(lift: LiftValues, last: LogEntry): Comparison {
  const now = inKg(lift);
  const then = inKg(last);
  let status: Comparison["status"] = "match";
  if (now.e1rm > then.e1rm + EPSILON_KG) status = "beat";
  else if (now.e1rm < then.e1rm - EPSILON_KG) status = "below";
  else if (now.volume > then.volume + EPSILON_KG) status = "beat";
  else if (now.volume < then.volume - EPSILON_KG) status = "below";
  const perSet = Boolean(lift.set_details?.length || last.set_details.length);
  const mine = setsOf(lift);
  const theirs = setsOf(last);
  const top = (sets: SetValues[], unit: Unit) =>
    Math.max(...sets.map((x) => convert(x.weight, unit, lift.unit)));
  const totalReps = (sets: SetValues[]) => sets.reduce((sum, x) => sum + x.reps, 0);
  return {
    status,
    basis: perSet ? "sets" : "quick",
    weightDiff: Math.round((top(mine, lift.unit) - top(theirs, last.unit)) * 100) / 100,
    repsDiff: perSet ? totalReps(mine) - totalReps(theirs) : lift.reps - last.reps,
    setsDiff: mine.length - theirs.length,
  };
}

/** For example "+5 lb · −1 rep · same sets", or "top set +5 lb · +6 total reps · same sets". */
export function describeDiff(c: Comparison, unit: Unit): string {
  const signed = (n: number, text: string) => `${n > 0 ? "+" : "−"}${text}`;
  const count = (n: number, one: string, many: string) =>
    n === 0 ? `same ${many}` : signed(n, `${Math.abs(n)} ${Math.abs(n) === 1 ? one : many}`);
  const weightText =
    c.weightDiff === 0 ? "same weight" : signed(c.weightDiff, formatWeight(Math.abs(c.weightDiff), unit));
  const weight = c.basis === "sets" ? `top set ${weightText}` : weightText;
  const reps =
    c.basis === "sets" ? count(c.repsDiff, "total rep", "total reps") : count(c.repsDiff, "rep", "reps");
  return [weight, reps, count(c.setsDiff, "set", "sets")].join(" · ");
}
