import { describe, expect, it } from "vitest";
import { dayKey } from "./lifting";
import { compact, formatWeek, signed, summarizeWeek, totals, weekStart, type SummaryEntry } from "./summary";

let id = 0;
// Noon local time on a day, so the entry lands on that local day in any time zone.
function entry(day: string, name: string, group: string, lift: Partial<SummaryEntry> = {}): SummaryEntry {
  const [y, m, d] = day.split("-").map(Number) as [number, number, number];
  return {
    id: ++id,
    exercise_id: 1,
    weight: 100,
    unit: "lb",
    reps: 10,
    sets: 3,
    set_details: [],
    performed_at: new Date(y, m - 1, d, 12).toISOString(),
    exercise: { id: 1, name, muscle_group: group },
    ...lift,
  };
}

describe("weekStart", () => {
  it("is the Monday on or before the day", () => {
    expect(weekStart("2026-11-23")).toBe("2026-11-23"); // Monday
    expect(weekStart("2026-11-27")).toBe("2026-11-23"); // Friday
    expect(weekStart("2026-11-29")).toBe("2026-11-23"); // Sunday
    expect(weekStart("2026-12-01")).toBe("2026-11-30"); // across a month
  });
});

describe("formatWeek", () => {
  it("shows the month once inside a month, twice across one", () => {
    expect(formatWeek("2026-11-23")).toMatch(/Nov 23 – 29/);
    expect(formatWeek("2026-11-30")).toMatch(/Nov 30 – Dec 6/);
  });
});

describe("totals", () => {
  it("counts days, sets, reps and volume, per set for per-set entries", () => {
    const t = totals(
      [
        entry("2026-11-23", "Bench Press", "Chest"), // 3 × 10 @ 100
        entry("2026-11-23", "Bench Press", "Chest", {
          set_details: [
            { weight: 135, reps: 8 },
            { weight: 155, reps: 5 },
          ],
          sets: 2,
        }),
        entry("2026-11-25", "Pull-Up", "Back", { weight: 0, reps: 8, sets: 4 }),
      ],
      "lb",
    );
    expect(t).toEqual({
      days: 2,
      sets: 9,
      reps: 30 + 13 + 32,
      volume: 3000 + 135 * 8 + 155 * 5, // bodyweight sets add nothing
      exercises: ["Bench Press", "Pull-Up"],
    });
  });

  it("converts volume to the display unit", () => {
    const t = totals([entry("2026-11-23", "Squat", "Legs", { weight: 100, unit: "kg", reps: 1, sets: 1 })], "lb");
    expect(t.volume).toBeCloseTo(220.46, 1);
  });
});

describe("summarizeWeek", () => {
  const entries = [
    entry("2026-11-16", "Bench Press", "Chest"), // last week
    entry("2026-11-18", "Squat", "Legs", { sets: 5 }),
    entry("2026-11-23", "Bench Press", "Chest", { sets: 4 }), // this week
    entry("2026-11-24", "Row", "Back", { sets: 5 }),
    entry("2026-11-29", "Burpee", "Full body", { weight: 0, sets: 2 }),
    entry("2026-11-30", "Bench Press", "Chest"), // next week: ignored
  ];
  const week = summarizeWeek(entries, "2026-11-23", "lb");

  it("totals this week and last", () => {
    expect(week.total).toMatchObject({ days: 3, sets: 11 });
    expect(week.previous).toMatchObject({ days: 2, sets: 8 });
  });

  it("lists every main group, extras when logged, most sets first", () => {
    expect(week.groups.map((g) => [g.group, g.sets, g.previous.sets])).toEqual([
      ["Back", 5, 0],
      ["Chest", 4, 3],
      ["Full body", 2, 0],
      ["Legs", 0, 5], // untrained main groups follow in body order
      ["Shoulders", 0, 0],
      ["Arms", 0, 0],
      ["Core", 0, 0],
    ]);
  });

  it("splits by local day", () => {
    expect(week.groups.find((g) => g.group === "Chest")!.exercises).toEqual(["Bench Press"]);
    expect(dayKey(entries[2]!.performed_at)).toBe("2026-11-23");
  });

  it("handles an empty week", () => {
    const none = summarizeWeek([], "2026-11-23", "kg");
    expect(none.total.sets).toBe(0);
    expect(none.groups).toHaveLength(6);
  });
});

describe("formatting", () => {
  it("signs differences and hides no change", () => {
    expect(signed(3)).toBe("+3");
    expect(signed(-2)).toBe("−2");
    expect(signed(0)).toBe("");
  });

  it("shortens only big volumes", () => {
    expect(compact(8450)).toBe((8450).toLocaleString());
    expect(compact(124_300)).not.toContain("124,300");
  });
});
