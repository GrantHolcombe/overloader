<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import ConfirmDialog from "../components/ConfirmDialog.vue";
import DateField from "../components/DateField.vue";
import EditEntryDialog, { type EntryPatch } from "../components/EditEntryDialog.vue";
import ExerciseFormDialog from "../components/ExerciseFormDialog.vue";
import SetsEditor from "../components/SetsEditor.vue";
import Stepper from "../components/Stepper.vue";
import { useRouter } from "vue-router";
import { api, ApiError, type Exercise, type ExerciseFields } from "../lib/api";
import { enqueue, isRetryable, newClientId, outbox, pendingEntries, remove } from "../lib/outbox";
import {
  atDay,
  compareToLast,
  convert,
  dayKey,
  describeDiff,
  entryBefore,
  formatDay,
  formatEntry,
  personalRecords,
  PR_LABELS,
  relativeDay,
  setsOf,
  summarizeSets,
  today,
  validSets,
  weightStep,
  wouldSetRecords,
  type SetValues,
  type LogEntry,
  type PRKind,
} from "../lib/lifting";
import { session } from "../lib/session";

const props = defineProps<{ id: number }>();
const router = useRouter();

// Back to wherever this was opened from (the home screen, a day view, search), or home when
// the page was opened directly.
function goBack() {
  if (router.options.history.state.back) router.back();
  else router.push("/");
}

const exercise = ref<Exercise>();
const logs = ref<LogEntry[]>([]);
const error = ref("");
const saving = ref(false);
const toast = ref("");
const toastKind = ref<"ok" | "pr">("ok");
const unit = computed(() => session.user?.unit ?? "lb");

// Quick: one weight x reps, done for every set. Per set: each set has its own weight and reps.
const mode = ref<"quick" | "sets">("quick");
const weight = ref(0);
const reps = ref(8);
const sets = ref(3);
const setRows = ref<SetValues[]>([]);

const round = (n: number) => Math.round(n * 100) / 100;

function switchMode(next: "quick" | "sets") {
  if (next === mode.value) return;
  if (next === "sets") {
    // Start with the quick numbers as that many identical sets, ready to adjust.
    setRows.value = setsOf({ weight: weight.value, unit: unit.value, reps: reps.value, sets: sets.value });
  } else if (setRows.value.length) {
    ({ weight: weight.value, reps: reps.value, sets: sets.value } = summarizeSets(setRows.value));
  }
  mode.value = next;
}

const formValid = computed(() =>
  mode.value === "sets" ? validSets(setRows.value) : validSets([{ weight: weight.value, reps: reps.value }]),
);
// The day this entry is for. Stays put after logging, so backfilling a past workout is quick;
// a page reload starts from today again.
const logDay = ref(today());
const isToday = computed(() => logDay.value === today());

// Newest first, the order the API returns.
function sortLogs(list: LogEntry[]) {
  return [...list].sort(
    (a, b) => b.performed_at.localeCompare(a.performed_at) || b.id - a.id,
  );
}

// Entries saved on this phone but not yet synced (offline queue) count everywhere: last time,
// records, history. They have negative ids until the server gives them real ones.
const pending = computed(() => pendingEntries(session.user?.id, props.id));
const entries = computed(() => sortLogs([...pending.value, ...logs.value]));
const isPending = (entry: LogEntry) => entry.id < 0;

const last = computed(() => entries.value[0]);

// Group the history by day, newest first.
const history = computed(() => {
  const groups: { day: string; label: string; entries: LogEntry[] }[] = [];
  for (const entry of entries.value) {
    const day = dayKey(entry.performed_at);
    let group = groups.at(-1);
    if (!group || group.day !== day) {
      group = { day, label: relativeDay(entry.performed_at), entries: [] };
      groups.push(group);
    }
    group.entries.push(entry);
  }
  return groups;
});

// Which entries set a record when they were logged (worked out from the history, so edits and
// backdated entries are always reflected).
const records = computed(() => personalRecords(entries.value));
const recordText = (kinds: PRKind[]) => kinds.map((k) => PR_LABELS[k]).join(", ");

// The lift on the form, compared with the entries before the day it's being logged for.
const lift = computed(() => ({
  weight: weight.value,
  unit: unit.value,
  reps: reps.value,
  sets: sets.value,
  ...(mode.value === "sets" ? { set_details: setRows.value } : {}),
}));
const priorEntries = computed(() => {
  if (isToday.value) return entries.value;
  const moment = atDay(logDay.value);
  return entries.value.filter((e) => e.performed_at < moment);
});
const previous = computed(() =>
  isToday.value ? entries.value[0] : entryBefore(entries.value, atDay(logDay.value)),
);
const comparison = computed(() =>
  previous.value ? compareToLast(lift.value, previous.value) : null,
);
const upcomingRecords = computed(() => wouldSetRecords(lift.value, priorEntries.value));
const NUDGE = { beat: "Beats last time", match: "Matches last time", below: "Below last time" };

function prefill() {
  // Start from last time, so matching it is one tap and beating it is two.
  // A per-set last time starts the form in per-set mode with the same sets.
  const prev = last.value;
  if (!prev) return;
  weight.value = round(convert(prev.weight, prev.unit, unit.value));
  reps.value = prev.reps;
  sets.value = prev.sets;
  if (prev.set_details.length) {
    setRows.value = prev.set_details.map((x) => ({
      weight: round(convert(x.weight, prev.unit, unit.value)),
      reps: x.reps,
    }));
    mode.value = "sets";
  }
}

onMounted(async () => {
  try {
    [exercise.value, logs.value] = await Promise.all([api.exercise(props.id), api.logs(props.id)]);
    prefill();
  } catch (e) {
    error.value = (e as Error).message;
  }
});

// A queued entry just synced: reload the history so it shows with its real id.
watch(
  () => outbox.version,
  async () => {
    try {
      logs.value = await api.logs(props.id);
    } catch {
      // Still flaky; the queued copy stays visible until the next sync.
    }
  },
);

async function save() {
  error.value = "";
  saving.value = true;
  try {
    const body = {
      ...(mode.value === "sets"
        ? { set_details: setRows.value.map((x) => ({ ...x })) }
        : { weight: weight.value, reps: reps.value, sets: sets.value }),
      // When it was lifted, not when it reaches the server (it may wait in the queue).
      performed_at: isToday.value ? new Date().toISOString() : atDay(logDay.value),
      client_id: newClientId(),
    };
    let entry: LogEntry;
    try {
      // No signal at all: don't wait for a request that can't go anywhere.
      if (!navigator.onLine) throw new ApiError(0, "Offline");
      entry = await api.addLog(props.id, body);
    } catch (e) {
      if (!(e instanceof ApiError) || !isRetryable(e.status) || !session.user) throw e;
      // Keep it on the phone and send it when there's signal (see outbox.ts).
      enqueue({ client_id: body.client_id, user_id: session.user.id, exercise_id: props.id, unit: unit.value, body });
      const queued = pending.value.find((p) => p.client_id === body.client_id);
      const set = queued && records.value.get(queued.id);
      showToast(set ? `New PR! ${recordText(set)} · saved on this phone` : "Saved on this phone · syncs when you have signal", set ? "pr" : "ok");
      return;
    }
    logs.value = sortLogs([entry, ...logs.value]);
    const set = records.value.get(entry.id);
    if (set) showToast(`New PR! ${recordText(set)}`, "pr");
    else showToast(isToday.value ? "Logged" : `Logged for ${formatDay(logDay.value)}`);
  } catch (e) {
    error.value = (e as Error).message;
  } finally {
    saving.value = false;
  }
}

const pendingDelete = ref<LogEntry | null>(null);
const deleting = ref(false);

async function confirmDelete() {
  const entry = pendingDelete.value;
  if (!entry) return;
  if (isPending(entry)) {
    // Not on the server yet: just take it off the queue.
    remove((entry as LogEntry & { client_id: string }).client_id);
    pendingDelete.value = null;
    showToast("Deleted");
    return;
  }
  error.value = "";
  deleting.value = true;
  try {
    await api.deleteLog(entry.id);
    logs.value = logs.value.filter((l) => l.id !== entry.id);
    showToast("Deleted");
  } catch (e) {
    error.value = (e as Error).message;
  } finally {
    deleting.value = false;
    pendingDelete.value = null;
  }
}

const editing = ref<LogEntry | null>(null);
const savingEdit = ref(false);

async function saveEdit(patch: EntryPatch) {
  const entry = editing.value;
  if (!entry) return;
  error.value = "";
  savingEdit.value = true;
  try {
    const updated = await api.updateLog(entry.id, patch);
    logs.value = sortLogs(logs.value.map((l) => (l.id === updated.id ? updated : l)));
    editing.value = null;
    showToast("Saved");
  } catch (e) {
    error.value = (e as Error).message;
    editing.value = null;
  } finally {
    savingEdit.value = false;
  }
}

// Custom exercises only: edit the name/equipment/muscle, or delete it with its history.
const editingExercise = ref(false);
const exerciseBusy = ref(false);
const exerciseError = ref("");
const confirmingExerciseDelete = ref(false);

function openExerciseEdit() {
  exerciseError.value = "";
  editingExercise.value = true;
}

async function saveExercise(fields: ExerciseFields) {
  exerciseError.value = "";
  exerciseBusy.value = true;
  try {
    exercise.value = await api.updateExercise(props.id, fields);
    editingExercise.value = false;
    showToast("Saved");
  } catch (e) {
    exerciseError.value = (e as Error).message;
  } finally {
    exerciseBusy.value = false;
  }
}

async function deleteExercise() {
  exerciseBusy.value = true;
  try {
    await api.deleteExercise(props.id);
    router.replace("/");
  } catch (e) {
    error.value = (e as Error).message;
    confirmingExerciseDelete.value = false;
  } finally {
    exerciseBusy.value = false;
  }
}

let toastTimer: number | undefined;
function showToast(message: string, kind: "ok" | "pr" = "ok") {
  toast.value = message;
  toastKind.value = kind;
  clearTimeout(toastTimer);
  toastTimer = window.setTimeout(() => (toast.value = ""), kind === "pr" ? 3500 : 1800);
}

const time = (iso: string) =>
  new Date(iso).toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
</script>

<template>
  <main>
    <header class="topbar">
      <button type="button" class="btn btn-ghost icon-btn" aria-label="Back" @click="goBack">‹</button>
      <h1>{{ exercise?.name ?? "…" }}</h1>
      <button
        v-if="exercise?.custom"
        type="button"
        class="btn btn-ghost"
        aria-label="Edit this custom exercise"
        @click="openExerciseEdit"
      >
        Edit
      </button>
    </header>
    <p v-if="exercise" class="muted sub">
      <template v-if="exercise.custom">Custom · </template>{{ exercise.equipment }} ·
      {{ exercise.muscle_group }}
    </p>
    <p v-if="exercise?.retired" class="muted retired">
      No longer in the exercise list. Your history is kept, and you can still log it here.
    </p>

    <section class="card last" aria-live="polite">
      <template v-if="last">
        <span class="muted">Last time · {{ relativeDay(last.performed_at) }}</span>
        <strong>{{ formatEntry(last) }}</strong>
      </template>
      <span v-else class="muted">No logs yet. Your first entry sets the baseline.</span>
    </section>

    <form class="stack log-form" @submit.prevent="save">
      <div class="segmented" role="group" aria-label="How to log">
        <button type="button" :aria-pressed="mode === 'quick'" @click="switchMode('quick')">
          Quick
        </button>
        <button type="button" :aria-pressed="mode === 'sets'" @click="switchMode('sets')">
          Per set
        </button>
      </div>
      <template v-if="mode === 'quick'">
        <Stepper
          v-model="weight"
          :label="`Weight (${unit})`"
          :step="weightStep(unit)"
          :max="5000"
          decimals
        />
        <div class="pair">
          <Stepper v-model="reps" label="Reps" :min="1" :max="1000" />
          <Stepper v-model="sets" label="Sets" :min="1" :max="100" />
        </div>
      </template>
      <SetsEditor v-else v-model="setRows" :unit="unit" id-prefix="log" />
      <div
        v-if="comparison"
        class="nudge"
        :class="upcomingRecords.length ? 'pr' : comparison.status"
        aria-live="polite"
      >
        <strong>{{ upcomingRecords.length ? "New PR if you log this" : NUDGE[comparison.status] }}</strong>
        <span>{{ describeDiff(comparison, unit) }}</span>
        <span v-if="upcomingRecords.length">{{ recordText(upcomingRecords) }}</span>
      </div>
      <DateField id="log-day" v-model="logDay" label="Date">
        <button v-if="!isToday" type="button" class="btn btn-ghost" @click="logDay = today()">
          Today
        </button>
      </DateField>
      <button class="btn btn-primary btn-block" :disabled="saving || !logDay || !formValid">
        {{ saving ? "Saving…" : isToday ? "Log it" : `Log for ${formatDay(logDay)}` }}
      </button>
      <p v-if="error" class="error" role="alert">{{ error }}</p>
    </form>

    <RouterLink
      v-if="logs.length"
      :to="`/exercise/${id}/progress`"
      class="btn btn-block"
      style="margin-top: 12px"
    >
      View progress chart
    </RouterLink>

    <template v-if="history.length">
      <h2>History</h2>
      <section v-for="group in history" :key="group.day" class="day">
        <h3 class="muted">{{ group.label }}</h3>
        <ul class="list">
          <li v-for="entry in group.entries" :key="entry.id" class="list-row">
            <button
              type="button"
              class="grow edit"
              :aria-label="isPending(entry) ? `${formatEntry(entry)}, waiting to sync` : `Edit ${formatEntry(entry)}`"
              :disabled="isPending(entry)"
              @click="editing = entry"
            >
              <span>
                <span v-if="records.get(entry.id)" class="tag">PR</span>{{ formatEntry(entry) }}
              </span>
              <small v-if="isPending(entry)" class="waiting">
                {{ time(entry.performed_at) }} · saved on this phone, waiting to sync
              </small>
              <small v-else-if="records.get(entry.id)">
                {{ time(entry.performed_at) }} · {{ recordText(records.get(entry.id)!) }}
              </small>
              <small v-else>{{ time(entry.performed_at) }} · tap to edit</small>
            </button>
            <button
              class="btn btn-ghost icon-btn"
              :aria-label="`Delete ${formatEntry(entry)}`"
              @click="pendingDelete = entry"
            >
              ×
            </button>
          </li>
        </ul>
      </section>
    </template>

    <ConfirmDialog
      :open="pendingDelete !== null"
      title="Delete this entry?"
      confirm-label="Delete"
      danger
      :busy="deleting"
      @confirm="confirmDelete"
      @cancel="pendingDelete = null"
    >
      <template v-if="pendingDelete">
        <strong class="entry">{{ formatEntry(pendingDelete) }}</strong>
        <span>{{ relativeDay(pendingDelete.performed_at) }}, {{ time(pendingDelete.performed_at) }}.</span>
        This can't be undone.
      </template>
    </ConfirmDialog>

    <EditEntryDialog
      :entry="editing"
      :busy="savingEdit"
      @save="saveEdit"
      @cancel="editing = null"
    />

    <ExerciseFormDialog
      :open="editingExercise && !confirmingExerciseDelete"
      :exercise="exercise ?? null"
      :busy="exerciseBusy"
      :error="exerciseError"
      @save="saveExercise"
      @delete="confirmingExerciseDelete = true"
      @cancel="editingExercise = false"
    />
    <ConfirmDialog
      :open="confirmingExerciseDelete"
      :title="`Delete ${exercise?.name ?? 'this exercise'}?`"
      confirm-label="Delete"
      danger
      :busy="exerciseBusy"
      @confirm="deleteExercise"
      @cancel="confirmingExerciseDelete = false"
    >
      <template v-if="logs.length">
        This also deletes its {{ logs.length }} logged {{ logs.length === 1 ? "entry" : "entries" }}.
      </template>
      This can't be undone.
    </ConfirmDialog>

    <div v-if="toast" class="toast" :class="{ pr: toastKind === 'pr' }" role="status">
      {{ toast }}
    </div>
  </main>
</template>

<style scoped>
.sub {
  margin: -8px 0 16px;
}
.retired {
  margin: -8px 0 16px;
  font-size: 0.9rem;
}
.last {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.last strong {
  font-size: 1.25rem;
}
.log-form {
  margin-top: 16px;
}
.pair {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.nudge {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 10px 14px;
  border-radius: var(--radius);
  border: 1px solid var(--border);
  background: var(--surface);
  font-size: 0.9rem;
  color: var(--text-muted);
}
.nudge strong {
  color: var(--text);
  font-size: 1rem;
}
.nudge.beat strong {
  color: var(--success);
}
.nudge.pr {
  border-color: var(--accent);
}
.nudge.pr strong {
  color: var(--accent);
}
.entry {
  display: block;
  color: var(--text);
  font-size: 1.1rem;
  margin-bottom: 2px;
}
.edit {
  all: unset;
  cursor: pointer;
  flex: 1;
  min-width: 0;
  min-height: 44px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}
.edit:disabled {
  cursor: default;
}
.waiting {
  color: var(--accent);
}
.edit:focus-visible {
  outline: 3px solid var(--accent);
  outline-offset: 2px;
  border-radius: 6px;
}
.day h3 {
  font-size: 0.9rem;
  margin: 12px 0 6px;
}
</style>
