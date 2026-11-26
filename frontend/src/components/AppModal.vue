<script setup lang="ts">
// The base for every modal in the app. Built on <dialog>.showModal(), which gives focus
// trapping, Escape to close and an inert page behind it for free.
import { ref, watch } from "vue";

// placement "top" is for modals with a text field: the phone keyboard covers the bottom half
// of the screen, so a centered dialog would hide what's being typed.
const props = withDefaults(
  defineProps<{ open: boolean; title: string; busy?: boolean; placement?: "center" | "top" }>(),
  { busy: false, placement: "center" },
);
const emit = defineEmits<{ close: [] }>();

const dialog = ref<HTMLDialogElement>();
const titleId = `modal-${Math.random().toString(36).slice(2, 8)}`;

watch(
  () => props.open,
  (open) => {
    if (open && !dialog.value?.open) dialog.value?.showModal();
    if (!open && dialog.value?.open) dialog.value.close();
  },
  { flush: "post" },
);

// A tap on the backdrop (the dialog element itself, outside its content) closes.
function onClick(event: MouseEvent) {
  if (event.target === dialog.value && !props.busy) emit("close");
}
</script>

<template>
  <dialog
    ref="dialog"
    class="modal"
    :class="{ top: placement === 'top' }"
    :aria-labelledby="titleId"
    @cancel.prevent="!busy && emit('close')"
    @click="onClick"
  >
    <div class="content">
      <h2 :id="titleId">{{ title }}</h2>
      <div class="body"><slot /></div>
      <div class="actions"><slot name="actions" /></div>
    </div>
  </dialog>
</template>

<style scoped>
.modal {
  width: min(420px, calc(100vw - 32px));
  padding: 0;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--surface);
  color: var(--text);
}
.modal.top {
  margin-top: max(16px, env(safe-area-inset-top));
}
.modal::backdrop {
  background: rgb(0 0 0 / 0.6);
}
.content {
  padding: 20px;
  min-width: 0;
  overflow-x: hidden;
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
