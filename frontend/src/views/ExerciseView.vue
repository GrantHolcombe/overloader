<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import ConfirmDialog from "../components/ConfirmDialog.vue";
import DateField from "../components/DateField.vue";
import EditEntryDialog, { type EntryPatch } from "../components/EditEntryDialog.vue";
import ExerciseFormDialog from "../components/ExerciseFormDialog.vue";
import Stepper from "../components/Stepper.vue";
import { useRouter } from "vue-router";
import { api, type Exercise, type ExerciseFields } from "../lib/api";
import {
  atDay,
  convert,
  dayKey,
  formatDay,
  formatEntry,
  relativeDay,
  today,
  weightStep,
  type LogEntry,
} from "../lib/lifting";
import { session } from "../lib/session";

const props = defineProps<{ id: number }>();
const router = useRouter();

const exercise = ref<Exercise>();
const logs = ref<LogEntry[]>([]);
const error = ref("");
const saving = ref(false);
const toast = ref("");
const unit = computed(() => session.user?.unit ?? "lb");

const weight = ref(0);
const reps = ref(8);
const sets = ref(3);
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

const last = computed(() => logs.value[0]);

// Group the history by day, newest first.
const history = computed(() => {
  const groups: { day: string; label: string; entries: LogEntry[] }[] = [];
  for (const entry of logs.value) {
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

function prefill() {
  // Start from last time, so matching it is one tap and beating it is two.
  if (!last.value) return;
  weight.value = Math.round(convert(last.value.weight, last.value.unit, unit.value) * 100) / 100;
  reps.value = last.value.reps;
  sets.value = last.value.sets;
}

onMounted(async () => {
  try {
    [exercise.value, logs.value] = await Promise.all([api.exercise(props.id), api.logs(props.id)]);
    prefill();
  } catch (e) {
    error.value = (e as Error).message;
  }
});

async function save() {
  error.value = "";
  saving.value = true;
  try {
    const entry = await api.addLog(props.id, {
      weight: weight.value,
      reps: reps.value,
      sets: sets.value,
      ...(isToday.value ? {} : { performed_at: atDay(logDay.value) }),
    });
    logs.value = sortLogs([entry, ...logs.value]);
    showToast(isToday.value ? "Logged" : `Logged for ${formatDay(logDay.value)}`);
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
function showToast(message: string) {
  toast.value = message;
  clearTimeout(toastTimer);
  toastTimer = window.setTimeout(() => (toast.value = ""), 1800);
}

const time = (iso: string) =>
  new Date(iso).toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
</script>

<template>
  <main>
    <header class="topbar">
      <RouterLink to="/" class="btn btn-ghost icon-btn" aria-label="Back to exercises">‹</RouterLink>
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
      <DateField id="log-day" v-model="logDay" label="Date">
        <button v-if="!isToday" type="button" class="btn btn-ghost" @click="logDay = today()">
          Today
        </button>
      </DateField>
      <button class="btn btn-primary btn-block" :disabled="saving || !logDay">
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
              :aria-label="`Edit ${formatEntry(entry)}`"
              @click="editing = entry"
            >
              {{ formatEntry(entry) }}
              <small>{{ time(entry.performed_at) }} · tap to edit</small>
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

    <div v-if="toast" class="toast" role="status">{{ toast }}</div>
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
