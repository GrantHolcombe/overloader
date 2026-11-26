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
  - Modals with a text field use `placement="top"` so the phone keyboard doesn't cover it
    (`ExerciseFormDialog.vue`, which creates/edits custom exercises).
  - `EditEntryDialog.vue` for editing a log entry. Steppers stack one per row inside a modal,
    since two side by side leave the number box too narrow at phone width.
- **Dates:** `components/DateField.vue`, a native date input that never allows a day after
  today. `max` greys out future days on Chrome/Android; iOS Safari's picker ignores `max`, so a
  future pick snaps back to today with a short note. It also undoes iOS's wide intrinsic width
  (`appearance: none; min-width: 0`), which pushed the picker off narrow dialogs. The primary
  button names a non-today date ("Log for Fri, Nov 20"), and a ghost "Today" button resets it.
- **Custom exercises** show a small accent `.tag` ("Custom") before their detail line, a
  "Custom" filter chip appears first once you have one, and an empty search offers to add the
  query as a custom exercise.
- **Quick / Per set:** a segmented control at the top of the log form and the edit dialog.
  Per set uses `components/SetsEditor.vue`: one row per set (number, weight, reps, remove) with
  plain number inputs rather than steppers so four columns fit at phone width; "+ Add set"
  copies the last set. Switching to per set expands the quick numbers into identical sets;
  switching back keeps the heaviest set and the count. The form opens in whichever mode last
  time used.
- **Records and "last time":** `lib/lifting.ts` works them out from the history (est. 1RM
  decides "beat / match / below"; ties and the very first entry are never records). On the log
  form a `.nudge` card under the steppers updates live: neutral for match/below, green title for
  beating last time, orange border and title when the lift would be a new PR. History rows that
  set a record get a "PR" `.tag` and list which records; a new PR shows an orange `.toast.pr`
  for 3.5 s instead of the green "Logged".
- **Day view:** "View a day" next to the Recent heading switches it to one day (heading shows
  the day; date field plus ‹ › arrows, › disabled on today; "Back to recent" returns). The day is
  in the URL (`/?day=2026-11-21`), and the exercise page's ‹ goes *back* rather than home, so
  leaving an exercise returns to the same day. Use `hide-label` on a DateField when a heading
  already names it (`.sr-only` keeps it for screen readers).
- **Tap to edit:** history rows are buttons that open the edit dialog; the row's detail line
  says "tap to edit".
- **Feedback:** errors in `.error` with `role="alert"`; success as a short `.toast`
  (`role="status"`).
