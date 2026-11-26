<script setup lang="ts">
// Create a custom exercise, or edit/delete one (pass `exercise`). Custom exercises are personal:
// only the person who made them sees them.
import { computed, nextTick, ref, watch } from "vue";
import { EQUIPMENT, MUSCLE_GROUPS, type Exercise, type ExerciseFields } from "../lib/api";
import AppModal from "./AppModal.vue";

const props = withDefaults(
  defineProps<{
    open: boolean;
    exercise?: Exercise | null;
    initialName?: string;
    busy?: boolean;
    error?: string;
  }>(),
  { exercise: null, initialName: "", busy: false, error: "" },
);
const emit = defineEmits<{ save: [fields: ExerciseFields]; delete: []; cancel: [] }>();

const name = ref("");
const equipment = ref<ExerciseFields["equipment"]>("Machine");
const muscle = ref<ExerciseFields["muscle_group"]>("Chest");
const nameInput = ref<HTMLInputElement>();
const editing = computed(() => props.exercise !== null);

watch(
  () => props.open,
  async (open) => {
    if (!open) return;
    const e = props.exercise;
    name.value = e?.name ?? props.initialName.trim();
    equipment.value = (e?.equipment as ExerciseFields["equipment"]) ?? "Machine";
    muscle.value = (e?.muscle_group as ExerciseFields["muscle_group"]) ?? "Chest";
    await nextTick();
    if (!editing.value) nameInput.value?.focus();
  },
  { immediate: true },
);

const valid = computed(() => name.value.trim().length > 0 && name.value.trim().length <= 80);

function save() {
  if (!valid.value) return;
  emit("save", { name: name.value.trim(), equipment: equipment.value, muscle_group: muscle.value });
}
</script>

<template>
  <AppModal
    :open="open"
    :title="editing ? 'Edit exercise' : 'New custom exercise'"
    :busy="busy"
    placement="top"
    @close="emit('cancel')"
  >
    <form id="exercise-form" class="stack fields" @submit.prevent="save">
      <p v-if="!editing" class="hint">Only you will see it.</p>
      <div>
        <label class="label" for="exercise-name">Name</label>
        <input
          id="exercise-name"
          ref="nameInput"
          v-model="name"
          class="input"
          maxlength="80"
          autocomplete="off"
          enterkeyhint="done"
          placeholder="e.g. Hammer Strength Row"
          required
        />
      </div>
      <div class="pair">
        <div>
          <label class="label" for="exercise-equipment">Equipment</label>
          <select id="exercise-equipment" v-model="equipment" class="input">
            <option v-for="e in EQUIPMENT" :key="e" :value="e">{{ e }}</option>
          </select>
        </div>
        <div>
          <label class="label" for="exercise-muscle">Muscle group</label>
          <select id="exercise-muscle" v-model="muscle" class="input">
            <option v-for="m in MUSCLE_GROUPS" :key="m" :value="m">{{ m }}</option>
          </select>
        </div>
      </div>
      <p v-if="error" class="error" role="alert">{{ error }}</p>
      <button
        v-if="editing"
        type="button"
        class="btn btn-ghost delete"
        :disabled="busy"
        @click="emit('delete')"
      >
        Delete this exercise…
      </button>
    </form>
    <template #actions>
      <button type="button" class="btn" :disabled="busy" @click="emit('cancel')">Cancel</button>
      <button type="submit" form="exercise-form" class="btn btn-primary" :disabled="busy || !valid">
        {{ busy ? "Saving…" : editing ? "Save" : "Create" }}
      </button>
    </template>
  </AppModal>
</template>

<style scoped>
.fields {
  color: var(--text);
  margin-top: 8px;
}
.hint {
  margin: 0;
  color: var(--text-muted);
  font-size: 0.9rem;
}
.pair {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}
.pair > div {
  min-width: 0;
}
select.input {
  padding: 0 10px;
}
.delete {
  color: var(--danger);
  justify-self: start;
  padding: 0;
}
</style>
