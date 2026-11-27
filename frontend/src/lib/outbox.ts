// The offline queue: log entries saved on this phone while there's no signal, sent oldest first
// when it comes back. Each entry carries a client_id, so a retry of a request whose reply was
// lost returns the entry the API already saved instead of logging it twice (see migration 0005).
//
// Kept in localStorage (a handful of small entries; survives closing the app). iOS has no
// Background Sync, so sending happens while the app is open: at start, when the phone comes
// back online, when the app returns to the foreground, and every 30 seconds while anything waits.
import { reactive } from "vue";
import type { LogBody } from "./api";
import { summarizeSets, type LogEntry, type Unit } from "./lifting";

export interface QueuedLog {
  client_id: string;
  /** Only sent while this user is signed in. */
  user_id: number;
  exercise_id: number;
  /** In the user's unit at the time (the API defaults to it). */
  unit: Unit;
  /** What gets POSTed. performed_at is always set: when it was logged, not when it synced. */
  body: LogBody & { performed_at: string; client_id: string };
}

export type SendResult = { ok: true; entry: LogEntry } | { ok: false; status: number; message: string };

const KEY = "overloader.outbox";
const RETRY_MS = 30_000;

function load(): QueuedLog[] {
  try {
    const raw = globalThis.localStorage?.getItem(KEY);
    if (raw) return JSON.parse(raw);
  } catch {
    // Blocked storage: the queue lives in memory only.
  }
  return [];
}

export const outbox = reactive({
  items: load(),
  syncing: false,
  /** Entries the API refused (e.g. the exercise was deleted); shown once, then dismissed. */
  rejected: [] as { item: QueuedLog; message: string }[],
  /** Bumped after each entry syncs, so open views can refresh. */
  version: 0,
});

function save() {
  try {
    globalThis.localStorage?.setItem(KEY, JSON.stringify(outbox.items));
  } catch {
    // Not fatal while the app stays open.
  }
}

/** A v4 UUID. crypto.randomUUID needs HTTPS, which LAN testing (http://192.168…) doesn't have. */
export function newClientId(): string {
  if (typeof crypto.randomUUID === "function") return crypto.randomUUID();
  const b = crypto.getRandomValues(new Uint8Array(16));
  b[6] = (b[6] & 0x0f) | 0x40;
  b[8] = (b[8] & 0x3f) | 0x80;
  const hex = [...b].map((x) => x.toString(16).padStart(2, "0")).join("");
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

/** Network down or the API unreachable/failing: worth keeping and trying again later. */
export const isRetryable = (status: number) => status === 0 || status === 408 || status === 429 || status >= 500;

export function enqueue(item: QueuedLog) {
  outbox.items.push(item);
  save();
}

export function remove(clientId: string) {
  outbox.items = outbox.items.filter((i) => i.client_id !== clientId);
  save();
}

export const waitingFor = (userId: number | undefined) =>
  outbox.items.filter((i) => i.user_id === userId);

export type PendingEntry = LogEntry & { client_id: string };

/** A queued entry shaped like a saved one, with a negative id (it has no real one yet). */
export function toEntry(item: QueuedLog, id = -1): PendingEntry {
  const { body } = item;
  const set_details = "set_details" in body ? body.set_details : [];
  const summary = "set_details" in body
    ? summarizeSets(body.set_details)
    : { weight: body.weight, reps: body.reps, sets: body.sets };
  return {
    id,
    exercise_id: item.exercise_id,
    unit: item.unit,
    ...summary,
    set_details,
    performed_at: body.performed_at,
    client_id: item.client_id,
  };
}

/** Queued entries for one exercise, for the history list. */
export function pendingEntries(userId: number | undefined, exerciseId: number): PendingEntry[] {
  return waitingFor(userId)
    .filter((i) => i.exercise_id === exerciseId)
    .map((i, n) => toEntry(i, -(n + 1)));
}

/**
 * Sends this user's queued entries, oldest first. Stops at the first one that can't get through
 * (no signal, server trouble, signed out) and leaves it and the rest for next time. An entry the
 * API refuses outright is taken off the queue and reported in outbox.rejected.
 * Returns how many were sent.
 */
export async function flush(
  userId: number | undefined,
  send: (item: QueuedLog) => Promise<SendResult>,
): Promise<number> {
  if (outbox.syncing || userId === undefined) return 0;
  outbox.syncing = true;
  let sent = 0;
  try {
    for (const item of waitingFor(userId)) {
      const result = await send(item);
      if (result.ok) {
        remove(item.client_id);
        sent++;
        outbox.version++;
        continue;
      }
      if (isRetryable(result.status) || result.status === 401) break;
      remove(item.client_id);
      outbox.rejected.push({ item, message: result.message });
    }
  } finally {
    outbox.syncing = false;
  }
  return sent;
}

/** Wires up the automatic retries. Call once at startup. */
export function startOutbox(trigger: () => void) {
  trigger();
  window.addEventListener("online", trigger);
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") trigger();
  });
  window.setInterval(() => {
    if (outbox.items.length && navigator.onLine) trigger();
  }, RETRY_MS);
}
