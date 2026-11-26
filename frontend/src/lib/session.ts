import { reactive } from "vue";
import type { Unit } from "./lifting";

export interface User {
  id: number;
  email: string;
  unit: Unit;
}

const KEY = "overloader.session";

function load(): { token: string | null; user: User | null } {
  try {
    const raw = localStorage.getItem(KEY);
    if (raw) return JSON.parse(raw);
  } catch {
    // Private mode or blocked storage: start signed out.
  }
  return { token: null, user: null };
}

export const session = reactive(load());

function save() {
  try {
    localStorage.setItem(KEY, JSON.stringify({ token: session.token, user: session.user }));
  } catch {
    // Not fatal; the user just signs in again next time.
  }
}

export function signIn(token: string, user: User) {
  session.token = token;
  session.user = user;
  save();
}

export function setUser(user: User) {
  session.user = user;
  save();
}

export function signOut() {
  session.token = null;
  session.user = null;
  save();
}
