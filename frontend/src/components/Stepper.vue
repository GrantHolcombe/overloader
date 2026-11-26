<script setup lang="ts">
// A number field with big − / + buttons, so a set can be logged one-handed between reps.
const props = withDefaults(
  defineProps<{ label: string; step?: number; min?: number; max?: number; decimals?: boolean }>(),
  { step: 1, min: 0, max: 9999, decimals: false },
);
const model = defineModel<number>({ required: true });

function bump(dir: 1 | -1) {
  const next = Math.round((model.value + dir * props.step) * 100) / 100;
  model.value = Math.min(props.max, Math.max(props.min, next));
}

function onInput(event: Event) {
  const value = Number((event.target as HTMLInputElement).value);
  if (!Number.isNaN(value)) model.value = value;
}

const id = `stepper-${Math.random().toString(36).slice(2, 8)}`;
</script>

<template>
  <div class="stepper">
    <label class="label" :for="id">{{ label }}</label>
    <div class="controls">
      <button type="button" class="btn" :aria-label="`Less ${label.toLowerCase()}`" @click="bump(-1)">−</button>
      <input
        :id="id"
        class="input"
        type="number"
        :inputmode="decimals ? 'decimal' : 'numeric'"
        :step="decimals ? 'any' : 1"
        :min="min"
        :max="max"
        :value="model"
        @input="onInput"
        @focus="($event.target as HTMLInputElement).select()"
      />
      <button type="button" class="btn" :aria-label="`More ${label.toLowerCase()}`" @click="bump(1)">+</button>
    </div>
  </div>
</template>

<style scoped>
.controls {
  display: grid;
  grid-template-columns: var(--tap) 1fr var(--tap);
  gap: 8px;
}
.controls .btn {
  padding: 0;
  font-size: 1.5rem;
}
.controls .input {
  text-align: center;
  font-size: 1.3rem;
  font-weight: 700;
  padding: 0 4px;
  -moz-appearance: textfield;
  appearance: textfield;
}
.controls .input::-webkit-outer-spin-button,
.controls .input::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}
</style>
