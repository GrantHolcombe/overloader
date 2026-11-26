<script setup lang="ts">
// Edit a logged entry: fix a typo or move it to another day. The weight stays in the unit the
// entry was logged in.
import { ref, watch } from "vue";
import { atDay, dayKey, weightStep, type LogEntry } from "../lib/lifting";
import AppModal from "./AppModal.vue";
import DateField from "./DateField.vue";
import Stepper from "./Stepper.vue";

export interface EntryPatch {
  weight: number;
  reps: number;
  sets: number;
  performed_at: string;
}

const props = withDefaults(defineProps<{ entry: LogEntry | null; busy?: boolean }>(), {
  busy: false,
});
const emit = defineEmits<{ save: [patch: EntryPatch]; cancel: [] }>();

const weight = ref(0);
const reps = ref(1);
const sets = ref(1);
const day = ref("");

watch(
  () => props.entry,
  (entry) => {
    if (!entry) return;
    weight.value = entry.weight;
    reps.value = entry.reps;
    sets.value = entry.sets;
    day.value = dayKey(entry.performed_at);
  },
  { immediate: true },
);

function save() {
  if (!props.entry || !day.value) return;
  emit("save", {
    weight: weight.value,
    reps: reps.value,
    sets: sets.value,
    // Keep the entry's own time of day; only the date moves.
    performed_at: atDay(day.value, new Date(props.entry.performed_at)),
  });
}
</script>

<template>
  <AppModal :open="entry !== null" title="Edit entry" :busy="busy" @close="emit('cancel')">
    <form v-if="entry" id="edit-entry" class="stack fields" @submit.prevent="save">
      <Stepper
        v-model="weight"
        :label="`Weight (${entry.unit})`"
        :step="weightStep(entry.unit)"
        :max="5000"
        decimals
      />
      <!-- Stacked, not side by side: the dialog is too narrow for two steppers in a row. -->
      <Stepper v-model="reps" label="Reps" :min="1" :max="1000" />
      <Stepper v-model="sets" label="Sets" :min="1" :max="100" />
      <DateField id="edit-day" v-model="day" label="Date" />
    </form>
    <template #actions>
      <button type="button" class="btn" :disabled="busy" @click="emit('cancel')">Cancel</button>
      <button type="submit" form="edit-entry" class="btn btn-primary" :disabled="busy || !day">
        {{ busy ? "Saving…" : "Save" }}
      </button>
    </template>
  </AppModal>
</template>

<style scoped>
.fields {
  color: var(--text);
  margin-top: 12px;
}
</style>
