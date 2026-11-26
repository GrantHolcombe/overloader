<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { api, type Exercise, type RecentExercise } from "../lib/api";
import { formatEntry, matches, relativeDay } from "../lib/lifting";

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

const equipmentTypes = computed(() => [...new Set(exercises.value.map((e) => e.equipment))].sort());

const results = computed(() =>
  exercises.value.filter(
    (e) => (!equipment.value || e.equipment === equipment.value) && matches(query.value, e),
  ),
);

const searching = computed(() => query.value.trim() !== "" || equipment.value !== null);

function toggleEquipment(type: string) {
  equipment.value = equipment.value === type ? null : type;
}
</script>

<template>
  <main>
    <header class="topbar">
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

    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <p v-else-if="loading" class="muted">Loading…</p>

    <template v-else-if="!searching && recent.length">
      <h2>Recent</h2>
      <ul class="list">
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
              <small>{{ e.equipment }} · {{ e.muscle_group }}</small>
            </span>
            <span aria-hidden="true" class="muted">›</span>
          </RouterLink>
        </li>
      </ul>
      <p v-else class="muted">Nothing matches "{{ query }}". Try fewer words.</p>
    </template>
  </main>
</template>
