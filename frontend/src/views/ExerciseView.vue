<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import Stepper from "../components/Stepper.vue";
import { api, type Exercise } from "../lib/api";
import {
  convert,
  dayKey,
  formatEntry,
  relativeDay,
  weightStep,
  type LogEntry,
} from "../lib/lifting";
import { session } from "../lib/session";

const props = defineProps<{ id: number }>();

const exercise = ref<Exercise>();
const logs = ref<LogEntry[]>([]);
const error = ref("");
const saving = ref(false);
const toast = ref("");
const unit = computed(() => session.user?.unit ?? "lb");

const weight = ref(0);
const reps = ref(8);
const sets = ref(3);

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
    });
    logs.value = [entry, ...logs.value];
    showToast("Logged");
  } catch (e) {
    error.value = (e as Error).message;
  } finally {
    saving.value = false;
  }
}

async function remove(entry: LogEntry) {
  if (!confirm(`Delete ${formatEntry(entry)}? This can't be undone.`)) return;
  try {
    await api.deleteLog(entry.id);
    logs.value = logs.value.filter((l) => l.id !== entry.id);
    showToast("Deleted");
  } catch (e) {
    error.value = (e as Error).message;
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
    </header>
    <p v-if="exercise" class="muted sub">{{ exercise.equipment }} · {{ exercise.muscle_group }}</p>

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
      <button class="btn btn-primary btn-block" :disabled="saving">
        {{ saving ? "Saving…" : "Log it" }}
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
            <span class="grow">
              {{ formatEntry(entry) }}
              <small>{{ time(entry.performed_at) }}</small>
            </span>
            <button
              class="btn btn-ghost icon-btn"
              :aria-label="`Delete ${formatEntry(entry)}`"
              @click="remove(entry)"
            >
              ×
            </button>
          </li>
        </ul>
      </section>
    </template>

    <div v-if="toast" class="toast" role="status">{{ toast }}</div>
  </main>
</template>

<style scoped>
.sub {
  margin: -8px 0 16px;
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
.day h3 {
  font-size: 0.9rem;
  margin: 12px 0 6px;
}
</style>
