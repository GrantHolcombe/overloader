<script setup lang="ts">
// Per-set entry: one row per set with its own weight and reps. "Add set" copies the last set,
// since the next one is usually the same or one plate different.
import { computed } from "vue";
import type { SetValues, Unit } from "../lib/lifting";

const props = defineProps<{ unit: Unit; idPrefix: string }>();
const sets = defineModel<SetValues[]>({ required: true });

const MAX_SETS = 100;

function update(index: number, field: keyof SetValues, raw: string) {
  const value = Number(raw);
  if (raw === "" || Number.isNaN(value)) return;
  sets.value = sets.value.map((s, i) => (i === index ? { ...s, [field]: value } : s));
}

function add() {
  const last = sets.value.at(-1) ?? { weight: 0, reps: 8 };
  if (sets.value.length < MAX_SETS) sets.value = [...sets.value, { ...last }];
}

function remove(index: number) {
  if (sets.value.length > 1) sets.value = sets.value.filter((_, i) => i !== index);
}

const select = (event: FocusEvent) => (event.target as HTMLInputElement).select();
const label = computed(() => `Weight (${props.unit})`);
</script>

<template>
  <div class="sets-editor">
    <div class="head" aria-hidden="true">
      <span>Set</span><span>{{ label }}</span><span>Reps</span><span></span>
    </div>
    <ol class="rows">
      <li v-for="(set, i) in sets" :key="i" class="row">
        <span class="n">{{ i + 1 }}</span>
        <input
          :id="`${idPrefix}-w-${i}`"
          class="input"
          type="number"
          inputmode="decimal"
          step="any"
          min="0"
          max="5000"
          :value="set.weight"
          :aria-label="`Set ${i + 1} ${label}`"
          @input="update(i, 'weight', ($event.target as HTMLInputElement).value)"
          @focus="select"
        />
        <input
          :id="`${idPrefix}-r-${i}`"
          class="input"
          type="number"
          inputmode="numeric"
          step="1"
          min="1"
          max="1000"
          :value="set.reps"
          :aria-label="`Set ${i + 1} reps`"
          @input="update(i, 'reps', ($event.target as HTMLInputElement).value)"
          @focus="select"
        />
        <button
          type="button"
          class="btn btn-ghost icon-btn"
          :aria-label="`Remove set ${i + 1}`"
          :disabled="sets.length === 1"
          @click="remove(i)"
        >
          ×
        </button>
      </li>
    </ol>
    <button type="button" class="btn btn-ghost add" :disabled="sets.length >= MAX_SETS" @click="add">
      + Add set
    </button>
  </div>
</template>

<style scoped>
.head,
.row {
  display: grid;
  grid-template-columns: 28px minmax(0, 1fr) minmax(0, 0.7fr) 44px;
  gap: 8px;
  align-items: center;
}
.head {
  font-size: 0.85rem;
  color: var(--text-muted);
  margin-bottom: 6px;
}
.rows {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 8px;
}
.n {
  text-align: center;
  font-weight: 700;
  color: var(--text-muted);
}
.input {
  text-align: center;
  font-size: 1.15rem;
  font-weight: 700;
  padding: 0 4px;
  min-width: 0;
  -moz-appearance: textfield;
  appearance: textfield;
}
.input::-webkit-outer-spin-button,
.input::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}
.icon-btn {
  font-size: 1.3rem;
  padding: 0;
}
.add {
  margin-top: 4px;
  padding: 0 4px;
  min-height: 44px;
  color: var(--accent);
}
</style>
