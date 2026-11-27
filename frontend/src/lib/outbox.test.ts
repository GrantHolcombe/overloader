import { beforeEach, describe, expect, it } from "vitest";
import type { LogEntry } from "./lifting";
import {
  enqueue,
  flush,
  isRetryable,
  newClientId,
  outbox,
  pendingEntries,
  type QueuedLog,
  type SendResult,
} from "./outbox";

let n = 0;
function item(overrides: Partial<QueuedLog> = {}): QueuedLog {
  const client_id = `id-${++n}`;
  return {
    client_id,
    user_id: 1,
    exercise_id: 7,
    unit: "lb",
    body: { weight: 135, reps: 8, sets: 3, performed_at: `2026-11-27T10:0${n % 10}:00Z`, client_id },
    ...overrides,
  };
}

const saved = (_i?: QueuedLog): SendResult => ({ ok: true, entry: { id: 100 } as LogEntry });
const failed = (status: number): SendResult => ({ ok: false, status, message: `HTTP ${status}` });

beforeEach(() => {
  outbox.items = [];
  outbox.rejected = [];
  outbox.syncing = false;
  outbox.version = 0;
});

describe("flush", () => {
  it("sends oldest first and empties the queue", async () => {
    const a = item();
    const b = item();
    enqueue(a);
    enqueue(b);
    const order: string[] = [];
    const sent = await flush(1, async (i) => (order.push(i.client_id), saved(i)));
    expect(sent).toBe(2);
    expect(order).toEqual([a.client_id, b.client_id]);
    expect(outbox.items).toEqual([]);
    expect(outbox.version).toBe(2);
  });

  it("stops at the first one that can't get through and keeps the rest", async () => {
    const [a, b, c] = [item(), item(), item()];
    [a, b, c].forEach(enqueue);
    const sent = await flush(1, async (i) => (i.client_id === b.client_id ? failed(0) : saved(i)));
    expect(sent).toBe(1);
    expect(outbox.items.map((i) => i.client_id)).toEqual([b.client_id, c.client_id]);
  });

  it("keeps everything on server errors and when signed out (401)", async () => {
    for (const status of [502, 503, 401]) {
      outbox.items = [];
      enqueue(item());
      await flush(1, async () => failed(status));
      expect(outbox.items).toHaveLength(1);
    }
    expect(outbox.rejected).toEqual([]);
  });

  it("drops an entry the API refuses, reports it and carries on", async () => {
    const [bad, good] = [item(), item()];
    enqueue(bad);
    enqueue(good);
    const sent = await flush(1, async (i) => (i.client_id === bad.client_id ? failed(404) : saved(i)));
    expect(sent).toBe(1);
    expect(outbox.items).toEqual([]);
    expect(outbox.rejected).toEqual([{ item: bad, message: "HTTP 404" }]);
  });

  it("only sends the signed-in user's entries", async () => {
    const mine = item();
    const theirs = item({ user_id: 2 });
    enqueue(mine);
    enqueue(theirs);
    await flush(1, async (i) => saved(i));
    expect(outbox.items).toEqual([theirs]);
    expect(await flush(undefined, async (i) => saved(i))).toBe(0);
  });

  it("doesn't run twice at once", async () => {
    enqueue(item());
    let calls = 0;
    const slow = async (i: QueuedLog) => (calls++, await new Promise((r) => setTimeout(r, 5)), saved(i));
    await Promise.all([flush(1, slow), flush(1, slow)]);
    expect(calls).toBe(1);
  });
});

describe("pendingEntries", () => {
  it("shapes queued entries like saved ones, with negative ids", () => {
    enqueue(item());
    enqueue(item({ exercise_id: 8 }));
    const perSet = item();
    perSet.body = {
      set_details: [
        { weight: 135, reps: 8 },
        { weight: 155, reps: 5 },
      ],
      performed_at: "2026-11-27T11:00:00Z",
      client_id: perSet.client_id,
    };
    enqueue(perSet);
    const rows = pendingEntries(1, 7);
    expect(rows.map((r) => r.id)).toEqual([-1, -2]);
    expect(rows[0]).toMatchObject({ weight: 135, reps: 8, sets: 3, set_details: [], unit: "lb" });
    expect(rows[1]).toMatchObject({ weight: 155, reps: 5, sets: 2, performed_at: "2026-11-27T11:00:00Z" });
    expect(pendingEntries(2, 7)).toEqual([]);
  });
});

describe("helpers", () => {
  it("retries network and server trouble, not client errors", () => {
    expect([0, 408, 429, 500, 502, 503].every(isRetryable)).toBe(true);
    expect([400, 401, 403, 404, 422].some(isRetryable)).toBe(false);
  });

  it("makes v4 UUIDs", () => {
    const id = newClientId();
    expect(id).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/);
    expect(newClientId()).not.toBe(id);
  });
});
