import { describe, expect, it } from "vitest";
import {
  atDay,
  compareToLast,
  convert,
  dayKey,
  describeDiff,
  entryBefore,
  personalRecords,
  today,
  wouldSetRecords,
  dailySeries,
  estimatedOneRepMax,
  matches,
  relativeDay,
  type LogEntry,
} from "./lifting";

const entry = (over: Partial<LogEntry>): LogEntry => ({
  id: 1,
  exercise_id: 1,
  weight: 100,
  unit: "lb",
  reps: 5,
  sets: 3,
  performed_at: "2026-11-20T18:00:00",
  ...over,
});

describe("lifting math", () => {
  it("converts kg and lb both ways", () => {
    expect(convert(100, "kg", "lb")).toBeCloseTo(220.46, 2);
    expect(convert(220.46, "lb", "kg")).toBeCloseTo(100, 2);
    expect(convert(135, "lb", "lb")).toBe(135);
  });

  it("estimates 1RM with Epley, and a single is the weight", () => {
    expect(estimatedOneRepMax(100, 10)).toBeCloseTo(133.33, 2);
    expect(estimatedOneRepMax(100, 1)).toBe(100);
  });

  it("keeps the best entry per day for top weight, oldest day first", () => {
    const series = dailySeries(
      [
        entry({ weight: 140, performed_at: "2026-11-22T18:00:00" }),
        entry({ weight: 135, performed_at: "2026-11-20T18:00:00" }),
        entry({ weight: 145, performed_at: "2026-11-22T18:30:00" }),
      ],
      "top",
      "lb",
    );
    expect(series).toEqual([
      { day: "2026-11-20", value: 135 },
      { day: "2026-11-22", value: 145 },
    ]);
  });

  it("sums volume per day and converts units", () => {
    const series = dailySeries(
      [
        entry({ weight: 100, reps: 10, sets: 3 }),
        entry({ weight: 50, unit: "kg", reps: 1, sets: 1 }),
      ],
      "volume",
      "lb",
    );
    expect(series[0]!.value).toBeCloseTo(3000 + 110.2, 0);
  });
});

describe("search", () => {
  const bench = { name: "Incline Dumbbell Press", equipment: "Dumbbell", muscle_group: "Chest" };
  it("matches every word in any order, across fields", () => {
    expect(matches("press incline", bench)).toBe(true);
    expect(matches("db chest", bench)).toBe(false);
    expect(matches("dumbbell chest", bench)).toBe(true);
    expect(matches("", bench)).toBe(true);
  });
  it("treats hyphens as spaces", () => {
    expect(matches("pull up", { name: "Pull-Up", equipment: "Bodyweight", muscle_group: "Back" })).toBe(true);
  });
});

describe("dates", () => {
  it("puts a picked day at the given time of day, in local time", () => {
    const time = new Date("2026-11-26T19:45:00");
    const iso = atDay("2026-11-20", time);
    const d = new Date(iso);
    expect([d.getFullYear(), d.getMonth() + 1, d.getDate()]).toEqual([2026, 11, 20]);
    expect([d.getHours(), d.getMinutes()]).toEqual([19, 45]);
    expect(dayKey(iso)).toBe("2026-11-20");
  });
  it("gives today as a date-input value", () => {
    expect(today(new Date("2026-11-26T23:30:00"))).toBe("2026-11-26");
  });
});

describe("relativeDay", () => {
  const now = new Date("2026-11-26T12:00:00");
  it("names recent days", () => {
    expect(relativeDay("2026-11-26T08:00:00", now)).toBe("Today");
    expect(relativeDay("2026-11-25T20:00:00", now)).toBe("Yesterday");
    expect(relativeDay("2026-11-23T20:00:00", now)).toBe("3 days ago");
  });
});

describe("personal records", () => {
  const log = (id: number, day: string, weight: number, reps: number, unit: "lb" | "kg" = "lb") =>
    entry({ id, performed_at: `${day}T18:00:00`, weight, reps, sets: 3, unit });

  it("flags entries that beat everything before them, not the first one or ties", () => {
    const records = personalRecords([
      log(1, "2026-11-01", 135, 8),
      log(2, "2026-11-03", 135, 8), // a tie is not a record
      log(3, "2026-11-05", 140, 6), // heavier, but est. 1RM and volume are lower
      log(4, "2026-11-08", 135, 12), // more reps: est. 1RM and volume, not weight
    ]);
    expect(records.get(1)).toBeUndefined();
    expect(records.get(2)).toBeUndefined();
    expect(records.get(3)).toEqual(["weight"]);
    expect(records.get(4)).toEqual(["e1rm", "volume"]);
  });

  it("compares across units and goes by date, not list order", () => {
    const records = personalRecords([
      log(2, "2026-11-10", 70, 5, "kg"), // about 154 lb, logged later
      log(1, "2026-11-01", 150, 5),
    ]);
    expect(records.get(2)).toEqual(["weight", "e1rm", "volume"]);
    expect(records.get(1)).toBeUndefined();
  });

  it("says which records a lift would set", () => {
    const history = [log(1, "2026-11-01", 135, 8), log(2, "2026-11-05", 145, 5)];
    const lift = (weight: number, reps: number) => ({ weight, unit: "lb" as const, reps, sets: 3 });
    expect(wouldSetRecords(lift(150, 5), history)).toEqual(["weight", "e1rm"]);
    expect(wouldSetRecords(lift(145, 5), history)).toEqual([]);
    expect(wouldSetRecords(lift(999, 5), [])).toEqual([]);
  });
});

describe("compared with last time", () => {
  const last = entry({ weight: 150, reps: 7, sets: 3 });
  const lift = (weight: number, reps: number, sets = 3) => ({ weight, unit: "lb" as const, reps, sets });

  it("beats, matches or falls below by est. 1RM, then volume", () => {
    expect(compareToLast(lift(155, 7), last).status).toBe("beat");
    expect(compareToLast(lift(150, 7), last).status).toBe("match");
    expect(compareToLast(lift(150, 7, 4), last).status).toBe("beat");
    expect(compareToLast(lift(150, 6), last).status).toBe("below");
    expect(compareToLast(lift(160, 6), last).status).toBe("beat"); // heavier, fewer reps
  });

  it("describes the difference in the lift's unit", () => {
    expect(describeDiff(compareToLast(lift(155, 6), last), "lb")).toBe("+5 lb · −1 rep · same sets");
    expect(describeDiff(compareToLast(lift(150, 7), last), "lb")).toBe(
      "same weight · same reps · same sets",
    );
  });

  it("finds the entry before a moment", () => {
    const a = entry({ id: 1, performed_at: "2026-11-01T18:00:00" });
    const b = entry({ id: 2, performed_at: "2026-11-05T18:00:00" });
    expect(entryBefore([b, a], "2026-11-04T00:00:00")?.id).toBe(1);
    expect(entryBefore([b, a], "2026-11-30T00:00:00")?.id).toBe(2);
    expect(entryBefore([b, a], "2026-10-01T00:00:00")).toBeUndefined();
  });
});
