<script setup lang="ts">
// One box per digit, ported from Setups.Bike's CodeInput. Pasting (or a phone's "from Mail"
// suggestion) anywhere fills them all; typing moves to the next box; Backspace on an empty box
// goes back. Reset it by giving the component a new key.
import { onMounted, ref } from "vue";

const props = withDefaults(defineProps<{ length?: number; disabled?: boolean }>(), { length: 6 });
const emit = defineEmits<{
  // every change, as the digits typed so far (gaps dropped)
  change: [code: string];
  // all boxes filled
  complete: [code: string];
}>();

const digits = ref<string[]>(Array(props.length).fill(""));
const boxes = ref<HTMLInputElement[]>([]);

function focus(i: number) {
  const el = boxes.value[Math.max(0, Math.min(props.length - 1, i))];
  if (el) {
    el.focus();
    el.select();
  }
}

onMounted(() => focus(0));

function update(next: string[]) {
  digits.value = next;
  const code = next.join("");
  emit("change", code);
  if (code.length === props.length) emit("complete", code);
}

// Put a run of digits in starting at box i (a paste, autofill, or one typed digit).
function fill(i: number, text: string) {
  const incoming = text.replace(/\D/g, "");
  if (!incoming) return;
  // A whole code always starts at the first box, wherever it was pasted.
  const start = incoming.length >= props.length ? 0 : i;
  const next = [...digits.value];
  incoming
    .slice(0, props.length - start)
    .split("")
    .forEach((d, k) => (next[start + k] = d));
  update(next);
  focus(Math.min(start + incoming.length, props.length - 1));
}

function onInput(i: number, event: Event) {
  const input = event.target as HTMLInputElement;
  const v = input.value;
  const old = digits.value[i] ?? "";
  if (v === "") {
    const next = [...digits.value];
    next[i] = "";
    update(next);
    return;
  }
  // Typed over an existing digit: keep only the new character.
  fill(i, v.length > 1 && old && v.includes(old) ? v.replace(old, "") || v : v);
  // Keep the DOM in step when the typed character was rejected (a letter, say).
  input.value = digits.value[i] ?? "";
}

function onPaste(i: number, event: ClipboardEvent) {
  event.preventDefault();
  fill(i, event.clipboardData?.getData("text") ?? "");
}

function onKeydown(i: number, event: KeyboardEvent) {
  if (event.key === "Backspace") {
    event.preventDefault();
    const next = [...digits.value];
    if (next[i]) {
      next[i] = "";
      update(next);
    } else if (i > 0) {
      next[i - 1] = "";
      update(next);
      focus(i - 1);
    }
  } else if (event.key === "ArrowLeft") {
    event.preventDefault();
    focus(i - 1);
  } else if (event.key === "ArrowRight") {
    event.preventDefault();
    focus(i + 1);
  }
}
</script>

<template>
  <div class="code-input" role="group" aria-label="Sign-in code" :style="{ '--n': length }">
    <input
      v-for="(d, i) in digits"
      :key="i"
      :ref="(el) => (boxes[i] = el as HTMLInputElement)"
      class="input"
      :value="d"
      :disabled="disabled"
      inputmode="numeric"
      pattern="[0-9]*"
      :autocomplete="i === 0 ? 'one-time-code' : 'off'"
      :aria-label="`Digit ${i + 1} of ${length}`"
      @input="onInput(i, $event)"
      @paste="onPaste(i, $event)"
      @keydown="onKeydown(i, $event)"
      @focus="($event.target as HTMLInputElement).select()"
    />
  </div>
</template>

<style scoped>
.code-input {
  display: grid;
  grid-template-columns: repeat(var(--n), 1fr);
  gap: 8px;
  max-width: 336px;
  margin: 0 auto;
}
.code-input .input {
  padding: 0;
  text-align: center;
  font-size: 1.5rem;
  font-weight: 700;
  min-width: 0;
}
</style>
