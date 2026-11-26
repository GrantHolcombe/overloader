<script setup lang="ts">
// A date input that never allows a day after today. `max` greys out future days in Chrome and
// Android, but iOS Safari's picker ignores it, so a future pick is also snapped back to today
// with a short note.
import { ref } from "vue";
import { today } from "../lib/lifting";

// hideLabel keeps the label for screen readers when a heading nearby already says what it is.
withDefaults(defineProps<{ id: string; label: string; hideLabel?: boolean }>(), {
  hideLabel: false,
});
const model = defineModel<string>({ required: true });
const clamped = ref(false);

function onChange(event: Event) {
  const input = event.target as HTMLInputElement;
  const max = today();
  // Clearing the field (some pickers allow it) also falls back to today.
  if (!input.value || input.value > max) {
    clamped.value = Boolean(input.value);
    model.value = max;
    input.value = max;
  } else {
    clamped.value = false;
    model.value = input.value;
  }
}
</script>

<template>
  <div class="date-field">
    <label :class="hideLabel ? 'sr-only' : 'label'" :for="id">{{ label }}</label>
    <div class="row">
      <input
        :id="id"
        class="input"
        type="date"
        :value="model"
        :max="today()"
        required
        @change="onChange"
      />
      <slot />
    </div>
    <p v-if="clamped" class="note" role="status">Future dates aren't allowed, so it's set to today.</p>
  </div>
</template>

<style scoped>
.row {
  display: flex;
  gap: 8px;
  min-width: 0;
}
/* iOS Safari gives date inputs a wide intrinsic size that ignores width: 100%, which pushed
   the picker button off the edge of narrow containers like the edit dialog. */
.input {
  flex: 1;
  min-width: 0;
  max-width: 100%;
  -webkit-appearance: none;
  appearance: none;
  display: flex;
  align-items: center;
}
.input::-webkit-date-and-time-value {
  text-align: left;
}
.note {
  margin: 6px 0 0;
  font-size: 0.85rem;
  color: var(--text-muted);
}
</style>
