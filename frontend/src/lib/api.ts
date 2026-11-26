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
  /** Created by this user; only they see it. */
  custom: boolean;
  /** Taken out of the catalog; still opens for anyone with history. */
  retired: boolean;
}

// Must match EQUIPMENT and MUSCLE_GROUPS in backend/app/schemas.py.
export const EQUIPMENT = ["Barbell", "Dumbbell", "Machine", "Cable", "Bodyweight", "Kettlebell", "Band", "Other"] as const;
export const MUSCLE_GROUPS = ["Chest", "Back", "Legs", "Shoulders", "Arms", "Core", "Full body", "Other"] as const;

export interface ExerciseFields {
  name: string;
  equipment: (typeof EQUIPMENT)[number];
  muscle_group: (typeof MUSCLE_GROUPS)[number];
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
  createExercise: (body: ExerciseFields) =>
    request<Exercise>("/api/exercises", { method: "POST", body }),
  updateExercise: (id: number, body: Partial<ExerciseFields>) =>
    request<Exercise>(`/api/exercises/${id}`, { method: "PATCH", body }),
  deleteExercise: (id: number) => request<void>(`/api/exercises/${id}`, { method: "DELETE" }),
  recent: () => request<RecentExercise[]>("/api/exercises/recent"),
  logs: (exerciseId: number) => request<LogEntry[]>(`/api/exercises/${exerciseId}/logs`),
  addLog: (
    exerciseId: number,
    body: { weight: number; reps: number; sets: number; performed_at?: string },
  ) => request<LogEntry>(`/api/exercises/${exerciseId}/logs`, { method: "POST", body }),
  updateLog: (
    id: number,
    body: Partial<Pick<LogEntry, "weight" | "reps" | "sets" | "unit" | "performed_at">>,
  ) => request<LogEntry>(`/api/logs/${id}`, { method: "PATCH", body }),
  deleteLog: (id: number) => request<void>(`/api/logs/${id}`, { method: "DELETE" }),
};
