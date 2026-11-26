<script setup lang="ts">
import { useRegisterSW } from "virtual:pwa-register/vue";

// Registers the service worker; with registerType "autoUpdate" new versions apply on reload.
useRegisterSW({ immediate: true });
</script>

<template>
  <RouterView />
</template>
