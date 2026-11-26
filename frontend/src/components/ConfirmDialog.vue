<script setup lang="ts">
// The app's one confirmation modal. Built on <dialog>.showModal(), which gives focus trapping,
// Escape to cancel and an inert page behind it for free.
import { ref, watch } from "vue";

const props = withDefaults(
  defineProps<{
    open: boolean;
    title: string;
    confirmLabel?: string;
    danger?: boolean;
    busy?: boolean;
  }>(),
  { confirmLabel: "Confirm", danger: false, busy: false },
);
const emit = defineEmits<{ confirm: []; cancel: [] }>();

const dialog = ref<HTMLDialogElement>();

watch(
  () => props.open,
  (open) => {
    if (open && !dialog.value?.open) dialog.value?.showModal();
    if (!open && dialog.value?.open) dialog.value.close();
  },
  { flush: "post" },
);

// A tap on the backdrop (the dialog element itself, outside its content) cancels.
function onClick(event: MouseEvent) {
  if (event.target === dialog.value && !props.busy) emit("cancel");
}
</script>

<template>
  <dialog
    ref="dialog"
    class="confirm"
    aria-labelledby="confirm-title"
    @cancel.prevent="!busy && emit('cancel')"
    @click="onClick"
  >
    <div class="content">
      <h2 id="confirm-title">{{ title }}</h2>
      <div class="body"><slot /></div>
      <div class="actions">
        <button type="button" class="btn" :disabled="busy" autofocus @click="emit('cancel')">
          Cancel
        </button>
        <button
          type="button"
          class="btn"
          :class="danger ? 'btn-danger' : 'btn-primary'"
          :disabled="busy"
          @click="emit('confirm')"
        >
          {{ confirmLabel }}
        </button>
      </div>
    </div>
  </dialog>
</template>

<style scoped>
.confirm {
  width: min(420px, calc(100vw - 32px));
  padding: 0;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--surface);
  color: var(--text);
}
.confirm::backdrop {
  background: rgb(0 0 0 / 0.6);
}
.content {
  padding: 20px;
}
h2 {
  margin: 0 0 8px;
  color: var(--text);
  font-size: 1.2rem;
}
.body {
  color: var(--text-muted);
}
.actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-top: 20px;
}
</style>
