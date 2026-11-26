<script setup lang="ts">
import {
  CategoryScale,
  Chart as ChartJS,
  Filler,
  LinearScale,
  LineElement,
  PointElement,
  Tooltip,
} from "chart.js";
import { computed, onMounted, ref } from "vue";
import { Line } from "vue-chartjs";
import { api, type Exercise } from "../lib/api";
import { dailySeries, formatWeight, METRICS, type LogEntry, type Metric } from "../lib/lifting";
import { session } from "../lib/session";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Filler);

const props = defineProps<{ id: number }>();
const exercise = ref<Exercise>();
const logs = ref<LogEntry[]>([]);
const metric = ref<Metric>("top");
const error = ref("");
const unit = computed(() => session.user?.unit ?? "lb");

onMounted(async () => {
  try {
    [exercise.value, logs.value] = await Promise.all([api.exercise(props.id), api.logs(props.id)]);
  } catch (e) {
    error.value = (e as Error).message;
  }
});

const series = computed(() => dailySeries(logs.value, metric.value, unit.value));
const best = computed(() => Math.max(0, ...series.value.map((p) => p.value)));
const change = computed(() => {
  const s = series.value;
  return s.length > 1 ? s.at(-1)!.value - s[0]!.value : 0;
});
const metricInfo = computed(() => METRICS.find((m) => m.value === metric.value)!);

function shortDay(day: string) {
  return new Date(`${day}T12:00:00`).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function cssVar(name: string) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

const chartData = computed(() => {
  const accent = cssVar("--accent");
  return {
    labels: series.value.map((p) => shortDay(p.day)),
    datasets: [
      {
        data: series.value.map((p) => p.value),
        borderColor: accent,
        backgroundColor: `${accent}33`,
        pointBackgroundColor: accent,
        pointRadius: 4,
        pointHoverRadius: 6,
        borderWidth: 3,
        tension: 0.25,
        fill: true,
      },
    ],
  };
});

const chartOptions = computed(() => {
  const muted = cssVar("--text-muted");
  const grid = cssVar("--border");
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      tooltip: {
        callbacks: { label: (ctx: { parsed: { y: number | null } }) => formatWeight(ctx.parsed.y ?? 0, unit.value) },
      },
    },
    scales: {
      x: { ticks: { color: muted, maxRotation: 0, autoSkipPadding: 12 }, grid: { display: false } },
      y: { ticks: { color: muted }, grid: { color: grid } },
    },
  };
});
</script>

<template>
  <main>
    <header class="topbar">
      <RouterLink :to="`/exercise/${id}`" class="btn btn-ghost icon-btn" aria-label="Back to logging">‹</RouterLink>
      <h1>{{ exercise?.name ?? "…" }}</h1>
    </header>

    <div class="segmented" role="group" aria-label="Chart metric">
      <button v-for="m in METRICS" :key="m.value" :aria-pressed="metric === m.value" @click="metric = m.value">
        {{ m.label }}
      </button>
    </div>
    <p class="muted hint">{{ metricInfo.hint }}, in {{ unit }}.</p>

    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <p v-else-if="!series.length" class="muted">Log this exercise to start a chart.</p>
    <template v-else>
      <div class="stats">
        <div class="card">
          <span class="muted">Best</span>
          <strong>{{ formatWeight(best, unit) }}</strong>
        </div>
        <div class="card">
          <span class="muted">Since first log</span>
          <strong :class="{ up: change > 0 }">{{ change > 0 ? "+" : "" }}{{ formatWeight(change, unit) }}</strong>
        </div>
        <div class="card">
          <span class="muted">Sessions</span>
          <strong>{{ series.length }}</strong>
        </div>
      </div>
      <div class="card chart">
        <Line :data="chartData" :options="chartOptions" aria-label="Progress chart" role="img" />
      </div>
    </template>
  </main>
</template>

<style scoped>
.hint {
  font-size: 0.9rem;
  margin: 8px 0 16px;
}
.stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  margin-bottom: 12px;
}
.stats .card {
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}
.stats span {
  font-size: 0.8rem;
}
.stats strong {
  font-size: 1.05rem;
  overflow-wrap: anywhere;
}
.up {
  color: var(--success);
}
.chart {
  height: 320px;
  padding: 12px 8px;
}
</style>
