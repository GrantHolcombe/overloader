<script setup lang="ts">
// Edit a logged entry: fix a typo, switch between quick and per set, or move it to another day.
// The weight stays in the unit the entry was logged in.
import { computed, ref, watch } from "vue";
import type { LogBody } from "../lib/api";
import {
  atDay,
  dayKey,
  setsOf,
  summarizeSets,
  validSets,
  weightStep,
  type LogEntry,
  type SetValues,
} from "../lib/lifting";
import AppModal from "./AppModal.vue";
import DateField from "./DateField.vue";
import SetsEditor from "./SetsEditor.vue";
import Stepper from "./Stepper.vue";

export type EntryPatch = LogBody & { performed_at: string };

const props = withDefaults(defineProps<{ entry: LogEntry | null; busy?: boolean }>(), {
  busy: false,
});
const emit = defineEmits<{ save: [patch: EntryPatch]; cancel: [] }>();

const mode = ref<"quick" | "sets">("quick");
const weight = ref(0);
const reps = ref(1);
const sets = ref(1);
const setRows = ref<SetValues[]>([]);
const day = ref("");

watch(
  () => props.entry,
  (entry) => {
    if (!entry) return;
    weight.value = entry.weight;
    reps.value = entry.reps;
    sets.value = entry.sets;
    setRows.value = entry.set_details.map((s) => ({ ...s }));
    mode.value = entry.set_details.length ? "sets" : "quick";
    day.value = dayKey(entry.performed_at);
  },
  { immediate: true },
);

function switchMode(next: "quick" | "sets") {
  if (next === mode.value || !props.entry) return;
  if (next === "sets") {
    setRows.value = setsOf({
      weight: weight.value,
      unit: props.entry.unit,
      reps: reps.value,
      sets: sets.value,
    });
  } else if (setRows.value.length) {
    ({ weight: weight.value, reps: reps.value, sets: sets.value } = summarizeSets(setRows.value));
  }
  mode.value = next;
}

const valid = computed(
  () =>
    Boolean(day.value) &&
    (mode.value === "sets"
      ? validSets(setRows.value)
      : validSets([{ weight: weight.value, reps: reps.value }])),
);

function save() {
  if (!props.entry || !valid.value) return;
  // Keep the entry's own time of day; only the date moves.
  const performed_at = atDay(day.value, new Date(props.entry.performed_at));
  emit(
    "save",
    mode.value === "sets"
      ? { set_details: setRows.value, performed_at }
      : { weight: weight.value, reps: reps.value, sets: sets.value, performed_at },
  );
}
</script>

<template>
  <AppModal
    :open="entry !== null"
    title="Edit entry"
    :busy="busy"
    placement="top"
    @close="emit('cancel')"
  >
    <form v-if="entry" id="edit-entry" class="stack fields" @submit.prevent="save">
      <div class="segmented" role="group" aria-label="How this entry was logged">
        <button type="button" :aria-pressed="mode === 'quick'" @click="switchMode('quick')">
          Quick
        </button>
        <button type="button" :aria-pressed="mode === 'sets'" @click="switchMode('sets')">
          Per set
        </button>
      </div>
      <template v-if="mode === 'quick'">
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
      </template>
      <SetsEditor v-else v-model="setRows" :unit="entry.unit" id-prefix="edit" />
      <DateField id="edit-day" v-model="day" label="Date" />
    </form>
    <template #actions>
      <button type="button" class="btn" :disabled="busy" @click="emit('cancel')">Cancel</button>
      <button type="submit" form="edit-entry" class="btn btn-primary" :disabled="busy || !valid">
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
