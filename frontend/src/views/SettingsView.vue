<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { api } from "../lib/api";
import type { Unit } from "../lib/lifting";
import { session, setUser, signOut } from "../lib/session";

const router = useRouter();
const error = ref("");

async function chooseUnit(unit: Unit) {
  error.value = "";
  try {
    setUser(await api.setUnit(unit));
  } catch (e) {
    error.value = (e as Error).message;
  }
}

function leave() {
  signOut();
  router.replace("/signin");
}
</script>

<template>
  <main>
    <header class="topbar">
      <RouterLink to="/" class="btn btn-ghost icon-btn" aria-label="Back to exercises">‹</RouterLink>
      <h1>Settings</h1>
    </header>

    <section class="stack">
      <div>
        <span class="label" id="unit-label">Weight unit</span>
        <div class="segmented" role="group" aria-labelledby="unit-label">
          <button :aria-pressed="session.user?.unit === 'lb'" @click="chooseUnit('lb')">Pounds (lb)</button>
          <button :aria-pressed="session.user?.unit === 'kg'" @click="chooseUnit('kg')">Kilograms (kg)</button>
        </div>
        <p class="muted small">Past entries keep the unit they were logged in; charts convert them.</p>
        <p v-if="error" class="error" role="alert">{{ error }}</p>
      </div>

      <div class="card">
        <span class="muted">Signed in as</span>
        <div>{{ session.user?.email }}</div>
      </div>
      <button class="btn btn-block" @click="leave">Sign out</button>
    </section>
  </main>
</template>

<style scoped>
.small {
  font-size: 0.9rem;
}
</style>
