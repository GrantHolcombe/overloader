import { describe, expect, it } from "vitest";
import {
  atDay,
  convert,
  dayKey,
  today,
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
