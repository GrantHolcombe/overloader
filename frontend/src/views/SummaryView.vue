<script setup lang="ts">
// Weekly training summary: days, sets and volume for a week, and sets per muscle group,
// each against the week before. Pro in the plan; built ungated until billing (ROADMAP.md).
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { api } from "../lib/api";
import { dayRange, shiftDay, today } from "../lib/lifting";
import { session } from "../lib/session";
import {
  compact,
  formatWeek,
  signed,
  summarizeWeek,
  weekStart,
  type SummaryEntry,
  type WeekSummary,
} from "../lib/summary";

const route = useRoute();
const router = useRouter();
const unit = computed(() => session.user?.unit ?? "lb");

// The week lives in the URL (?week=2026-11-23), so going into an exercise and back keeps it.
const thisWeek = computed(() => weekStart(today()));
const week = computed(() => {
  const w = route.query.week;
  return typeof w === "string" && /^\d{4}-\d{2}-\d{2}$/.test(w) && w <= thisWeek.value
    ? weekStart(w)
    : thisWeek.value;
});
const isThisWeek = computed(() => week.value === thisWeek.value);

function openWeek(start: string) {
  router.replace({ query: start >= thisWeek.value ? {} : { week: start } });
}

function goBack() {
  if (router.options.history.state.back) router.back();
  else router.push("/");
}

const entries = ref<SummaryEntry[]>([]);
const loadedWeek = ref("");
const loading = ref(false);
const error = ref("");

// One request covers the week and the one before it, for the comparisons.
watch(
  week,
  async (start) => {
    loading.value = true;
    error.value = "";
    try {
      const [from] = dayRange(shiftDay(start, -7));
      const [, to] = dayRange(shiftDay(start, 6));
      const rows = await api.logsBetween(from, to);
      if (week.value === start) {
        entries.value = rows;
        loadedWeek.value = start;
      }
    } catch (e) {
      error.value = (e as Error).message;
    } finally {
      loading.value = false;
    }
  },
  { immediate: true },
);

const summary = computed<WeekSummary | null>(() =>
  loadedWeek.value === week.value ? summarizeWeek(entries.value, week.value, unit.value) : null,
);
// Bars share one scale across both weeks, so this week and last compare at a glance.
const maxSets = computed(() =>
  Math.max(1, ...(summary.value?.groups.flatMap((g) => [g.sets, g.previous.sets]) ?? [])),
);
const pct = (sets: number) => `${(sets / maxSets.value) * 100}%`;

const stats = computed(() => {
  const s = summary.value;
  if (!s) return [];
  const vol = (n: number) => `${compact(n)} ${unit.value}`;
  return [
    { label: "Days trained", value: String(s.total.days), diff: signed(s.total.days - s.previous.days) },
    { label: "Sets", value: String(s.total.sets), diff: signed(s.total.sets - s.previous.sets) },
    { label: "Volume", value: vol(s.total.volume), diff: signed(s.total.volume - s.previous.volume, compact) },
    {
      label: "Exercises",
      value: String(s.total.exercises.length),
      diff: signed(s.total.exercises.length - s.previous.exercises.length),
    },
  ];
});
const vsLabel = computed(() => (isThisWeek.value ? "vs last week" : "vs week before"));
</script>

<template>
  <main>
    <header class="topbar">
      <button type="button" class="btn btn-ghost icon-btn" aria-label="Back" @click="goBack">‹</button>
      <h1>Training summary</h1>
    </header>

    <div class="week-nav">
      <button type="button" class="btn icon-btn" aria-label="Previous week" @click="openWeek(shiftDay(week, -7))">
        ‹
      </button>
      <div class="week-label">
        <strong>{{ isThisWeek ? "This week" : formatWeek(week) }}</strong>
        <small class="muted">{{ isThisWeek ? formatWeek(week) : "Mon – Sun" }}</small>
      </div>
      <button
        type="button"
        class="btn icon-btn"
        aria-label="Next week"
        :disabled="isThisWeek"
        @click="openWeek(shiftDay(week, 7))"
      >
        ›
      </button>
    </div>

    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <p v-else-if="!summary" class="muted">Loading…</p>

    <template v-else>
      <section class="stats" aria-label="Week totals">
        <div v-for="s in stats" :key="s.label" class="card stat">
          <span class="muted">{{ s.label }}</span>
          <strong>{{ s.value }}</strong>
          <small :class="{ up: s.diff.startsWith('+') }">
            {{ s.diff ? `${s.diff} ${vsLabel}` : `Same as ${vsLabel.slice(3)}` }}
          </small>
        </div>
      </section>

      <p v-if="!summary.total.sets" class="muted">
        Nothing logged {{ isThisWeek ? "yet this week" : `the week of ${formatWeek(week)}` }}.
      </p>

      <h2>Sets by muscle group</h2>
      <ul class="list groups">
        <li v-for="g in summary.groups" :key="g.group" class="group" :class="{ idle: !g.sets }">
          <div class="group-head">
            <span class="name">{{ g.group }}</span>
            <span class="count">
              <template v-if="g.sets">{{ g.sets }} {{ g.sets === 1 ? "set" : "sets" }}</template>
              <template v-else>Not trained</template>
              <small v-if="signed(g.sets - g.previous.sets)" :class="{ up: g.sets > g.previous.sets }">
                {{ signed(g.sets - g.previous.sets) }}
              </small>
            </span>
          </div>
          <div v-if="g.sets || g.previous.sets" class="bars" aria-hidden="true">
            <span class="bar now" :style="{ width: pct(g.sets) }" />
            <span class="bar before" :style="{ width: pct(g.previous.sets) }" />
          </div>
          <small v-if="g.sets" class="detail">
            {{ compact(g.volume) }} {{ unit }} · {{ g.exercises.join(", ") }}
          </small>
          <small v-else-if="g.previous.sets" class="detail">
            {{ g.previous.sets }} {{ g.previous.sets === 1 ? "set" : "sets" }} {{ isThisWeek ? "last week" : "the week before" }}
          </small>
        </li>
      </ul>
      <p class="legend muted">
        <span class="key now" aria-hidden="true" /> {{ isThisWeek ? "This week" : formatWeek(week) }}
        <span class="key before" aria-hidden="true" /> {{ isThisWeek ? "Last week" : "Week before" }}
      </p>
      <p class="note muted">
        Volume is weight × reps over every set, in {{ unit }}. Bodyweight sets count as sets but add
        no volume.
      </p>
    </template>
  </main>
</template>

<style scoped>
.week-nav {
  display: grid;
  grid-template-columns: var(--tap) 1fr var(--tap);
  align-items: center;
  gap: 8px;
}
.week-nav .btn {
  padding: 0;
}
.week-label {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}
.week-label small {
  font-size: 0.85rem;
}
.stats {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-top: 16px;
}
.stat {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 12px 14px;
  min-width: 0;
}
.stat span {
  font-size: 0.85rem;
}
.stat strong {
  font-size: 1.4rem;
  overflow-wrap: anywhere;
}
.stat small,
.count small {
  color: var(--text-muted);
  font-size: 0.8rem;
}
.up {
  color: var(--success) !important;
}
.groups {
  display: grid;
  gap: 0;
}
.group {
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.group-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 8px;
}
.name {
  font-weight: 600;
}
.count {
  display: flex;
  gap: 8px;
  align-items: baseline;
  font-variant-numeric: tabular-nums;
}
.idle .name,
.idle .count {
  color: var(--text-muted);
}
.bars {
  display: grid;
  gap: 3px;
}
.bar {
  display: block;
  height: 8px;
  min-width: 0;
  border-radius: 4px;
}
.bar.now {
  background: var(--accent);
}
.bar.before {
  height: 4px;
  background: var(--border);
}
.detail {
  color: var(--text-muted);
  font-size: 0.85rem;
  overflow-wrap: anywhere;
}
.legend {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.85rem;
  margin: 10px 0 0;
}
.key {
  display: inline-block;
  width: 14px;
  border-radius: 3px;
}
.key.now {
  height: 8px;
  background: var(--accent);
}
.key.before {
  height: 4px;
  margin-left: 10px;
  background: var(--border);
}
.note {
  font-size: 0.85rem;
}
</style>
