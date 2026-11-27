<script setup lang="ts">
// Tells you when entries are saved on the phone but not yet on the server, and when one
// couldn't be saved at all. Sits above every screen while either is true.
import { computed } from "vue";
import { sendQueued } from "../lib/api";
import { formatEntry } from "../lib/lifting";
import { flush, outbox, toEntry, waitingFor } from "../lib/outbox";
import { session } from "../lib/session";

const waiting = computed(() => waitingFor(session.user?.id).length);

function syncNow() {
  flush(session.user?.id, sendQueued);
}

const describe = (r: (typeof outbox.rejected)[number]) => formatEntry(toEntry(r.item));
</script>

<template>
  <div v-if="session.user && (waiting || outbox.rejected.length)" class="outbox" role="status">
    <div v-if="waiting" class="row">
      <span>
        <strong>{{ waiting }} {{ waiting === 1 ? "entry" : "entries" }} saved on this phone.</strong>
        {{ outbox.syncing ? "Syncing…" : `${waiting === 1 ? "It" : "They"}'ll sync when you have signal.` }}
      </span>
      <button type="button" class="btn btn-ghost" :disabled="outbox.syncing" @click="syncNow">
        Sync now
      </button>
    </div>
    <div v-for="(r, i) in outbox.rejected" :key="r.item.client_id" class="row rejected" role="alert">
      <span>
        <strong>Couldn't save {{ describe(r) }}.</strong> {{ r.message }}
      </span>
      <button type="button" class="btn btn-ghost" @click="outbox.rejected.splice(i, 1)">OK</button>
    </div>
  </div>
</template>

<style scoped>
.outbox {
  display: grid;
  gap: 8px;
  margin-bottom: 12px;
}
.row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 8px 8px 14px;
  border-radius: var(--radius);
  border: 1px solid var(--border);
  background: var(--surface);
  font-size: 0.9rem;
  color: var(--text-muted);
}
.row span {
  flex: 1;
  min-width: 0;
}
.row strong {
  color: var(--text);
}
.rejected {
  border-color: var(--danger);
}
</style>
