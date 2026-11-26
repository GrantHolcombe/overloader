<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import DateField from "../components/DateField.vue";
import ExerciseFormDialog from "../components/ExerciseFormDialog.vue";
import { api, type Exercise, type ExerciseFields, type RecentExercise } from "../lib/api";
import {
  dayRange,
  formatDay,
  formatEntry,
  formatShort,
  matches,
  relativeDay,
  shiftDay,
  today,
  type LogEntry,
} from "../lib/lifting";

const router = useRouter();
const route = useRoute();
// The filter chip that shows only your own exercises (not an equipment type).
const CUSTOM = "Custom";

const exercises = ref<Exercise[]>([]);
const recent = ref<RecentExercise[]>([]);
const query = ref("");
const equipment = ref<string | null>(null);
const error = ref("");
const loading = ref(true);

onMounted(async () => {
  try {
    [exercises.value, recent.value] = await Promise.all([api.exercises(), api.recent()]);
  } catch (e) {
    error.value = (e as Error).message;
  } finally {
    loading.value = false;
  }
});

const equipmentTypes = computed(() => {
  const types = [...new Set(exercises.value.map((e) => e.equipment))].sort();
  return exercises.value.some((e) => e.custom) ? [CUSTOM, ...types] : types;
});

const results = computed(() =>
  exercises.value.filter((e) => {
    const filter = equipment.value;
    const passes = !filter || (filter === CUSTOM ? e.custom : e.equipment === filter);
    return passes && matches(query.value, e);
  }),
);

// Day view: the Recent area can show everything logged on one day instead. The day lives in the
// URL (?day=2026-11-20), so going into an exercise and back returns to the same day.
const viewDay = computed(() => {
  const day = route.query.day;
  return typeof day === "string" && /^\d{4}-\d{2}-\d{2}$/.test(day) && day <= today() ? day : null;
});
const dayEntries = ref<(LogEntry & { exercise: Exercise })[]>([]);
const dayLoading = ref(false);
const dayError = ref("");

function openDay(day: string | null) {
  router.replace({ query: day ? { day: day > today() ? today() : day } : {} });
}

watch(
  viewDay,
  async (day) => {
    if (!day) return;
    dayLoading.value = true;
    dayError.value = "";
    try {
      const [start, end] = dayRange(day);
      const entries = await api.logsBetween(start, end);
      if (viewDay.value === day) dayEntries.value = entries; // ignore a slower, older answer
    } catch (e) {
      dayError.value = (e as Error).message;
    } finally {
      dayLoading.value = false;
    }
  },
  { immediate: true },
);

// One row per exercise, in the order it was first done that day.
const dayGroups = computed(() => {
  const groups = new Map<number, { exercise: Exercise; entries: LogEntry[] }>();
  for (const entry of dayEntries.value) {
    const group = groups.get(entry.exercise.id) ?? { exercise: entry.exercise, entries: [] };
    group.entries.push(entry);
    groups.set(entry.exercise.id, group);
  }
  return [...groups.values()];
});

const creating = ref(false);
const saving = ref(false);
const formError = ref("");

function openCreate() {
  formError.value = "";
  creating.value = true;
}

async function create(fields: ExerciseFields) {
  formError.value = "";
  saving.value = true;
  try {
    const exercise = await api.createExercise(fields);
    creating.value = false;
    router.push(`/exercise/${exercise.id}`);
  } catch (e) {
    formError.value = (e as Error).message;
  } finally {
    saving.value = false;
  }
}

const searching = computed(() => query.value.trim() !== "" || equipment.value !== null);

function toggleEquipment(type: string) {
  equipment.value = equipment.value === type ? null : type;
}
</script>

<template>
  <main>
    <header class="topbar">
      <img src="/favicon.svg" alt="" width="36" height="36" class="logo" />
      <h1>Overloader</h1>
      <RouterLink to="/settings" class="btn btn-ghost icon-btn" aria-label="Settings">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <circle cx="12" cy="12" r="3" />
          <path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z" />
        </svg>
      </RouterLink>
    </header>

    <label class="label" for="search">Find an exercise</label>
    <input
      id="search"
      v-model="query"
      class="input"
      type="search"
      placeholder="Bench, squat, cable, legs…"
      autocomplete="off"
      enterkeyhint="search"
    />
    <div class="chips" role="group" aria-label="Filter by equipment" style="margin-top: 10px">
      <button
        v-for="type in equipmentTypes"
        :key="type"
        class="chip"
        :aria-pressed="equipment === type"
        @click="toggleEquipment(type)"
      >
        {{ type }}
      </button>
    </div>
    <button type="button" class="btn btn-ghost add" @click="openCreate">
      + New custom exercise
    </button>

    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <p v-else-if="loading" class="muted">Loading…</p>

    <template v-else-if="!searching && (recent.length || viewDay)">
      <div class="section-head">
        <h2>{{ viewDay ? formatDay(viewDay) : "Recent" }}</h2>
        <button v-if="!viewDay" type="button" class="btn btn-ghost link" @click="openDay(today())">
          View a day
        </button>
        <button v-else type="button" class="btn btn-ghost link" @click="openDay(null)">
          Back to recent
        </button>
      </div>

      <template v-if="viewDay">
        <DateField
          id="view-day"
          :model-value="viewDay"
          label="Day to show"
          hide-label
          @update:model-value="openDay"
        >
          <button
            type="button"
            class="btn icon-btn"
            aria-label="Previous day"
            @click="openDay(shiftDay(viewDay, -1))"
          >
            ‹
          </button>
          <button
            type="button"
            class="btn icon-btn"
            aria-label="Next day"
            :disabled="viewDay >= today()"
            @click="openDay(shiftDay(viewDay, 1))"
          >
            ›
          </button>
        </DateField>
        <p v-if="dayError" class="error" role="alert">{{ dayError }}</p>
        <p v-else-if="dayLoading && !dayGroups.length" class="muted">Loading…</p>
        <ul v-else-if="dayGroups.length" class="list day-list">
          <li v-for="g in dayGroups" :key="g.exercise.id">
            <RouterLink :to="`/exercise/${g.exercise.id}`" class="list-row">
              <span class="grow">
                {{ g.exercise.name }}
                <small>{{ g.entries.map(formatShort).join(", ") }}</small>
              </span>
              <span aria-hidden="true" class="muted">›</span>
            </RouterLink>
          </li>
        </ul>
        <p v-else class="muted">Nothing logged on {{ formatDay(viewDay) }}.</p>
      </template>

      <ul v-else class="list">
        <li v-for="r in recent" :key="r.exercise.id">
          <RouterLink :to="`/exercise/${r.exercise.id}`" class="list-row">
            <span class="grow">
              {{ r.exercise.name }}
              <small>{{ formatEntry(r.last) }} · {{ relativeDay(r.last.performed_at) }}</small>
            </span>
            <span aria-hidden="true" class="muted">›</span>
          </RouterLink>
        </li>
      </ul>
    </template>

    <template v-if="!loading && !error">
      <h2>{{ searching ? `${results.length} ${results.length === 1 ? "match" : "matches"}` : "All exercises" }}</h2>
      <ul v-if="results.length" class="list">
        <li v-for="e in results" :key="e.id">
          <RouterLink :to="`/exercise/${e.id}`" class="list-row">
            <span class="grow">
              {{ e.name }}
              <small><span v-if="e.custom" class="tag">Custom</span>{{ e.equipment }} · {{ e.muscle_group }}</small>
            </span>
            <span aria-hidden="true" class="muted">›</span>
          </RouterLink>
        </li>
      </ul>
      <div v-else class="empty">
        <p class="muted">Nothing matches "{{ query }}". Try fewer words, or add it yourself.</p>
        <button v-if="query.trim()" type="button" class="btn btn-block" @click="openCreate">
          Add "{{ query.trim() }}" as a custom exercise
        </button>
      </div>
    </template>

    <ExerciseFormDialog
      :open="creating"
      :initial-name="query"
      :busy="saving"
      :error="formError"
      @save="create"
      @cancel="creating = false"
    />
  </main>
</template>

<style scoped>
.section-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
}
.section-head h2 {
  margin-bottom: 8px;
}
.link {
  min-height: 44px;
  padding: 0 4px;
  color: var(--accent);
  font-size: 0.95rem;
}
.day-list {
  margin-top: 12px;
}
.add {
  margin-top: 4px;
  padding: 0 4px;
  min-height: 44px;
  color: var(--accent);
}
.empty p {
  margin: 0 0 10px;
}
</style>
