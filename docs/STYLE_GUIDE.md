# Style guide

Built for one hand, between sets, in a dim gym. Tokens live in `frontend/src/style.css`.

## Principles

- **Tap targets ≥ 44px**, primary controls 52px (`--tap`).
- **Numbers first.** Weight, reps and sets are the biggest text on the logging screen.
- **One primary action per screen** (orange `btn-primary`): "Email me a code", "Sign in", "Log it".
- **Mobile-first**, single column, max width 560px, 16px gutters, safe-area insets respected.

## Tokens

| Token | Dark (default) | Light | Use |
| --- | --- | --- | --- |
| `--bg` | `#14161a` | `#f5f6f8` | page |
| `--surface` / `--surface-2` | `#1e2127` / `#272b33` | `#fff` / `#eef0f3` | cards, inputs / buttons, tracks |
| `--border` | `#343944` | `#d9dde3` | dividers |
| `--text` / `--text-muted` | `#f2f3f5` / `#9aa1ad` | `#15171b` / `#5d6573` | |
| `--accent` / `--accent-text` | `#ff7a1a` / `#1a0d00` | `#e85f00` / `#fff` | primary buttons, chart line, active chip |
| `--danger`, `--success` | | | errors, toasts and gains |

## Components

- **Buttons:** `.btn` (secondary), `.btn-primary`, `.btn-ghost` (icon or text), `.btn-block`.
- **Inputs:** `.input` with a `.label` above; never placeholder-only labels.
- **Stepper** (`components/Stepper.vue`): − / value / + for weight, reps, sets. Weight steps
  5 lb or 2.5 kg.
- **Lists:** `.list` with `.list-row` (title, `<small>` detail line, chevron).
- **Chips** for filters, **segmented** control for 2–3 exclusive options; both use
  `aria-pressed`.
- **Code entry** (`components/CodeInput.vue`, ported from Setups.Bike): one box per digit.
  Typing advances, Backspace on an empty box goes back, and a paste or the phone's one-time-code
  suggestion fills every box. Filling the last box submits.
- **Modals** are all built on `components/AppModal.vue` (`<dialog>.showModal()`: focus trap,
  Escape and backdrop tap close; title, body slot, two-button `actions` slot). Never use the
  browser's `confirm()` or `alert()`.
  - `ConfirmDialog.vue` for yes/no. Focus starts on Cancel; destructive actions use `danger`
    (`.btn-danger`) and say they can't be undone.
  - `EditEntryDialog.vue` for editing a log entry. Steppers stack one per row inside a modal,
    since two side by side leave the number box too narrow at phone width.
- **Dates:** a native `<input type="date">` with `max` set to today (no future entries). The
  primary button names a non-today date ("Log for Fri, Nov 20"), and a ghost "Today" button
  resets it.
- **Tap to edit:** history rows are buttons that open the edit dialog; the row's detail line
  says "tap to edit".
- **Feedback:** errors in `.error` with `role="alert"`; success as a short `.toast`
  (`role="status"`).
