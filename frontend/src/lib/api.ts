import type { LogEntry, Unit } from "./lifting";
import { session, signOut, type User } from "./session";

// Empty in dev (Vite proxies /api to FastAPI). Set VITE_API_BASE when the API lives elsewhere.
const BASE = import.meta.env.VITE_API_BASE ?? "";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init: { method?: string; body?: unknown } = {}): Promise<T> {
  const headers: Record<string, string> = {};
  if (init.body !== undefined) headers["Content-Type"] = "application/json";
  if (session.token) headers.Authorization = `Bearer ${session.token}`;

  let res: Response;
  try {
    res = await fetch(BASE + path, {
      method: init.method ?? "GET",
      headers,
      body: init.body === undefined ? undefined : JSON.stringify(init.body),
    });
  } catch {
    throw new ApiError(0, "Can't reach the server. Check your connection.");
  }

  if (res.status === 401 && session.token) {
    signOut();
    location.assign("/signin");
  }
  if (!res.ok) {
    let message = `Something went wrong (${res.status})`;
    try {
      const data = await res.json();
      if (typeof data.detail === "string") message = data.detail;
      else if (res.status === 422) message = "Check the values and try again.";
    } catch {
      // Non-JSON error body; keep the generic message.
    }
    throw new ApiError(res.status, message);
  }
  return res.status === 204 ? (undefined as T) : res.json();
}

export interface Exercise {
  id: number;
  name: string;
  equipment: string;
  muscle_group: string;
}

export interface RecentExercise {
  exercise: Exercise;
  last: LogEntry;
}

export const api = {
  requestCode: (email: string) =>
    request<{ sent: boolean }>("/api/auth/request-code", { method: "POST", body: { email } }),
  verify: (email: string, code: string) =>
    request<{ token: string; user: User }>("/api/auth/verify", {
      method: "POST",
      body: { email, code },
    }),
  setUnit: (unit: Unit) => request<User>("/api/me", { method: "PATCH", body: { unit } }),
  exercises: () => request<Exercise[]>("/api/exercises"),
  exercise: (id: number) => request<Exercise>(`/api/exercises/${id}`),
  recent: () => request<RecentExercise[]>("/api/exercises/recent"),
  logs: (exerciseId: number) => request<LogEntry[]>(`/api/exercises/${exerciseId}/logs`),
  addLog: (exerciseId: number, body: { weight: number; reps: number; sets: number }) =>
    request<LogEntry>(`/api/exercises/${exerciseId}/logs`, { method: "POST", body }),
  deleteLog: (id: number) => request<void>(`/api/logs/${id}`, { method: "DELETE" }),
};
