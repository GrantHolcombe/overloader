# Every Rep Has a Spotter

*In the gym, a spotter doesn't lift the weight for you. They watch the bar, know when to step
in, and decide when a set is done. That's how I use an AI coding agent: it moves a lot of
weight, and I decide what gets lifted.*

Overloader is built with an AI coding agent (Claude Code) as a tool. This log records the calls
I made: where I set direction, steered, corrected or overruled the agent, set its limits, or
weighed a trade-off myself. The code shows *what* was built; this shows the engineering
judgment behind it.

Newest first. Each entry: the situation, what I decided, and why.

---

## How I work with the agent

Carried over from [Setups.Bike](https://github.com/GrantHolcombe/setups.bike):

- **No secrets in chat.** Passwords, keys and connection strings never pass through the
  conversation. I put them in `backend/.env` or the provider's console myself.
- **I approve every deploy and every delete.**
- **Local first.** Changes are checked on localhost before anything ships.
- **Docs stay current.** Roadmap, database notes and the style guide change in the same commit as
  the code, and the work is tracked on a private GitHub Project board.

---

## 2026-11-26: Freemium, and where the paywall goes

**Situation:** Before Phase 1, I decided Overloader should make money the same way Setups.Bike
does: a free tier and a Pro subscription through Stripe. I asked the agent for options on what
a usable free tier looks like and what's worth paying for, and for tickets covering terms,
privacy and the rest of the legal work.

**Decision:** I approved this split (proposed by the agent, in `docs/ROADMAP.md`):
- **Free, unlimited:** logging, the full catalog, history, the top-weight chart, PR badges,
  offline and per-set logging, CSV export and account deletion.
- **Pro, $2.99/month or $24/year** (same as Setups.Bike): advanced charts (est. 1RM, volume,
  ranges), muscle-group volume, routines, unlimited custom exercises (free gets 5), and a plate
  calculator.
- The Setups.Bike rules carry over: limits enforced in the API, nothing deleted when Pro lapses,
  billing behind a kill switch and tested in a Stripe sandbox first.

**Why:** The free tier has to be genuinely useful every day or nobody builds the habit that
makes Pro worth buying. Charging for analysis and convenience, never for someone's own data,
keeps the paywall fair and avoids privacy-law problems with export and deletion.

---

## 2026-11-26: Reviewing the agent's defaults instead of inheriting them

**Situation:** To get a working app quickly, the agent picked several defaults while scaffolding
and listed them on the roadmap as open for review rather than treating them as settled.

**Decision:** I went through each one and kept all four:
- **Sign-in lasts 30 days,** not Setups.Bike's 7. Re-entering an email code at the rack is
  friction, and the token only opens your own lifting log.
- **One weight × reps × sets row per entry** stays the main way to log. Per-set detail (drop
  sets, pyramids) stays an optional Phase 1 feature.
- **One chart point per day,** so logging an exercise twice in a session doesn't make the trend
  line zigzag.
- **Dark first, following the phone's light/dark setting,** with the orange accent from the logo.

**Why:** Defaults become decisions whether or not anyone makes them. Having the agent flag its
own guesses, and then confirming them, keeps the product calls mine.

---

## 2026-11-26: Six code boxes and an in-app modal, from the first run-through

**Situation:** After my first run of the app, two things felt off. The sign-in code was one text
field, and deleting a log used the browser's `confirm()` popup.

**Decision:**
- **Code entry:** use six boxes, one per digit, like Setups.Bike's sign-in. The agent ported
  that component to Vue, keeping paste-to-fill, autofill and auto-submit.
- **Delete:** use the app's own modal, not a browser alert. It's now the one confirmation
  pattern in the style guide, and browser dialogs are off-limits.

**Why:** Both apps should feel the same where they do the same thing, and a native popup looks
out of place in an installed PWA. It also can't be styled and reads like an error on a phone.

---

## 2026-11-26: Stack, scope and where it runs

**Situation:** Starting a new portfolio project: a lifting log that makes progressive overload
easy to track.

**Decision:**
- **Scope for v1:** email sign-in, a searchable list of common gym equipment, quick logging of
  weight, reps and sets, the last entry always visible, and a chart of every log per exercise.
- **Stack:** Vue on the front end, Python FastAPI with Postgres on Neon on the back end. Both are
  deliberately different from Setups.Bike (React, Node Lambdas) to show range.
- **Sign-in:** by email, like Setups.Bike's one-time code, so there are no passwords to store
  or leak.
- **Where it runs:** a PWA on localhost first, the frontend headed for S3, and the API's host
  left open until I've compared options, rather than committing to one up front.
- **Visibility:** a public repo for the portfolio, with a private project board so the plan and
  backlog stay mine.

**Why:** A small, finished, well-tested app shows more than a large unfinished one. Deferring
the API host keeps the code portable (plain ASGI app, any Postgres URL) while I weigh cost and
cold-start trade-offs.
