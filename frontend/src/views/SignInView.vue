<script setup lang="ts">
import { nextTick, ref } from "vue";
import { useRouter } from "vue-router";
import { api } from "../lib/api";
import { signIn } from "../lib/session";

const router = useRouter();
const step = ref<"email" | "code">("email");
const email = ref("");
const code = ref("");
const busy = ref(false);
const error = ref("");
const codeInput = ref<HTMLInputElement>();

async function sendCode() {
  error.value = "";
  busy.value = true;
  try {
    await api.requestCode(email.value.trim());
    step.value = "code";
    code.value = "";
    await nextTick();
    codeInput.value?.focus();
  } catch (e) {
    error.value = (e as Error).message;
  } finally {
    busy.value = false;
  }
}

async function verify() {
  error.value = "";
  busy.value = true;
  try {
    const { token, user } = await api.verify(email.value.trim(), code.value);
    signIn(token, user);
    router.replace("/");
  } catch (e) {
    error.value = (e as Error).message;
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <main class="signin">
    <div class="brand">
      <img src="/favicon.svg" alt="" width="64" height="64" />
      <h1>Overloader</h1>
      <p class="muted">Log your lifts. Beat last time.</p>
    </div>

    <form v-if="step === 'email'" class="card stack" @submit.prevent="sendCode">
      <div>
        <label class="label" for="email">Email</label>
        <input
          id="email"
          v-model="email"
          class="input"
          type="email"
          autocomplete="email"
          inputmode="email"
          required
          placeholder="you@example.com"
        />
      </div>
      <button class="btn btn-primary btn-block" :disabled="busy || !email">
        {{ busy ? "Sending…" : "Email me a code" }}
      </button>
      <p class="muted small">No password. We'll email you a 6-digit code.</p>
      <p v-if="error" class="error" role="alert">{{ error }}</p>
    </form>

    <form v-else class="card stack" @submit.prevent="verify">
      <p>
        We sent a code to <strong>{{ email }}</strong
        >. It works for 10 minutes.
      </p>
      <div>
        <label class="label" for="code">Sign-in code</label>
        <input
          id="code"
          ref="codeInput"
          v-model="code"
          class="input code"
          inputmode="numeric"
          autocomplete="one-time-code"
          pattern="[0-9 ]*"
          maxlength="7"
          required
          placeholder="123456"
        />
      </div>
      <button class="btn btn-primary btn-block" :disabled="busy || code.replace(/\s/g, '').length !== 6">
        {{ busy ? "Checking…" : "Sign in" }}
      </button>
      <p v-if="error" class="error" role="alert">{{ error }}</p>
      <div class="row">
        <button type="button" class="btn btn-ghost" :disabled="busy" @click="sendCode">Send a new code</button>
        <button type="button" class="btn btn-ghost" @click="step = 'email'">Different email</button>
      </div>
    </form>
  </main>
</template>

<style scoped>
.signin {
  padding-top: 8vh;
}
.brand {
  text-align: center;
  margin-bottom: 24px;
}
.brand img {
  border-radius: 16px;
}
.brand h1 {
  margin-top: 12px;
  font-size: 2rem;
}
.brand p {
  margin: 4px 0 0;
}
.small {
  font-size: 0.9rem;
  margin: 0;
}
.code {
  font-size: 1.6rem;
  letter-spacing: 0.3em;
  text-align: center;
}
.row {
  display: flex;
  justify-content: space-between;
  flex-wrap: wrap;
}
</style>
