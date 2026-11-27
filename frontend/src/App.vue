<script setup lang="ts">
import { useRegisterSW } from "virtual:pwa-register/vue";
import OutboxBanner from "./components/OutboxBanner.vue";
import { sendQueued } from "./lib/api";
import { flush, startOutbox } from "./lib/outbox";
import { session } from "./lib/session";

// Registers the service worker; with registerType "autoUpdate" new versions apply on reload.
useRegisterSW({ immediate: true });

// Send anything logged without signal as soon as there's a chance it gets through.
startOutbox(() => flush(session.user?.id, sendQueued));
</script>

<template>
  <OutboxBanner />
  <RouterView />
</template>
