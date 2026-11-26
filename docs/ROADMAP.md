# Roadmap

The live task list is the private GitHub Project board. This page is the overview.

## Phase 0: Local MVP (in progress)

- [x] Repo, CI (ruff, pytest on Postgres, vitest, type-check, build)
- [x] FastAPI API: email one-time-code sign-in, JWT, exercise catalog, log CRUD, recent list
- [x] Vue PWA: sign-in, searchable catalog with equipment filter, logging with last-time
      prefill, history, progress chart (top weight / est. 1RM / volume), unit setting
- [x] Neon project + dev database, first end-to-end run on localhost (2026-11-26)
- [ ] Try it at the gym from a phone on the LAN; fix what's awkward

## Phase 1: Make it a habit

- Custom exercises (per user)
- Per-set logging (different weight or reps per set) alongside the quick weight × reps × sets
- Personal-record badges and "beat last time" nudges
- Edit an entry; log a past date
- Offline logging queue (save at the rack, sync when signal returns)

## Phase 2: Ship it

- Pick the API host (candidates: AWS Lambda via Mangum, App Runner/Fargate, Fly.io, Render)
- Frontend on S3 behind Cloudflare, deployed by GitHub Actions (like hiregrant.today)
- Resend sending domain, SPF/DKIM
- Domain and final app name
- Account deletion and data export; privacy policy

## Defaults chosen during scaffolding (open for review)

These were picked by the agent to get started, not decided by Grant yet:

- Tokens last 30 days (Setups.Bike uses 7) so a phone at the gym rarely has to sign in again.
- A log entry is one weight × reps × sets row, matching the brief; per-set detail is Phase 1.
- The exercise catalog is shared and seeded by migration.
- Chart points are one per day (best entry for weight and 1RM, sum for volume).
- Dark theme by default with a light theme from the OS setting; orange accent.
