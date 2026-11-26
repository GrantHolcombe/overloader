<script setup lang="ts">
// Yes/no confirmation on top of AppModal. Focus starts on Cancel, the safe choice.
import AppModal from "./AppModal.vue";

withDefaults(
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
</script>

<template>
  <AppModal :open="open" :title="title" :busy="busy" @close="emit('cancel')">
    <slot />
    <template #actions>
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
    </template>
  </AppModal>
</template>
