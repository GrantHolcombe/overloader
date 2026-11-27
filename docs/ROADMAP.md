# Roadmap

The live task list is the private GitHub Project board. This page is the overview.

## Phase 0: Local MVP (done)

- [x] Repo, CI (ruff, pytest on Postgres, vitest, type-check, build)
- [x] FastAPI API: email one-time-code sign-in, JWT, exercise catalog, log CRUD, recent list
- [x] Vue PWA: sign-in, searchable catalog with equipment filter, logging with last-time
      prefill, history, progress chart (top weight / est. 1RM / volume), unit setting
- [x] Neon project + dev database, first end-to-end run on localhost (2026-11-26)
- [x] Try it from a phone on the LAN; fix what's awkward (2026-11-26: 6-box code, in-app modal, code above keyboard, header logo)

## Phase 1: Make it a habit

- [x] Custom exercises, personal to each user (2026-11-26). The standard list is now edited in
      `backend/catalog/exercises.csv` and synced with one command; removed exercises are retired,
      never deleted.
- Merge two catalog exercises (move everyone's logs, retire the duplicate)
- "Suggest for everyone": promote a popular custom exercise into the catalog
- [x] View logs from a specific day in the Recent area (free, 2026-11-26)
- Muscle-group heat map on a body outline, shaded by how recently each group was trained (Pro)
- [x] Per-set logging (different weight or reps per set) alongside the quick weight × reps × sets
      (2026-11-26)
- [x] Personal-record badges and "beat last time" nudges (2026-11-26)
- [x] Edit an entry; log a past date (2026-11-26)
- Offline logging queue (save at the rack, sync when signal returns)

## Phase 2: Ship it

- [x] Pick the API host (decided 2026-11-26): **AWS Lambda running the API as a container image**
      (Lambda Web Adapter + uvicorn, ARM64, in us-west-2 next to Neon) behind a **Lambda Function
      URL**, with Cloudflare in front. About $0/month at this scale. The same image can move to
      Fargate or Fly.io later without code changes. Priced and set aside: Fargate (~$11/month, or
      ~$35 with a load balancer), App Runner (closed to new customers since April 30, 2026),
      Fly.io (~$2-4/month).
- [x] Dockerfile for the API (Lambda Web Adapter, runs the same locally and on Lambda; 2026-11-27)
- AWS stack as code (`infra/`, 2026-11-27): `registry.yaml` (ECR + GitHub deploy role) and
  `api.yaml` (Lambda image, ARM64, Function URL, logs-only role, reserved concurrency + kill
  switch, 30-day logs). Secrets are NoEcho stack parameters typed in the console. Waiting on Grant
  to create the stacks (`infra/README.md`).
- GitHub Actions deploy (`deploy-api.yml`, manual trigger for now): OIDC role, build and push
  the image, migrate + catalog sync, update the function, smoke test
- Neon production database and a least-privilege app role (migration `0004`: `overloader_app`;
  migrations run as the owner)
- Frontend on S3 behind Cloudflare, deployed by GitHub Actions: `infra/web.yaml`, the
  `overloader-edge` Worker and `deploy-web.yml`, at overloader.hiregrant.today until the final domain
- Resend sending domain, SPF/DKIM
- Domain and final app name
- Account deletion and data export
- Legal pages: Terms, Privacy, Refunds and cancellation (see below)

## Pro plan (split and pricing approved by Grant 2026-11-26)

Still open: whether to offer a free trial (Setups.Bike has none).

Freemium like Setups.Bike, with Stripe the same way: Checkout for buying, the Customer Portal
for managing and cancelling, and a signed webhook that keeps the plan in the database.

**The line:** everything that records your training, and everything that is your data, stays
free and unlimited. Pro sells *insight* (analysis on top of the log) and *convenience* (things
that save taps). Paywalling the logging itself would break the habit the app depends on, and
holding someone's own history hostage costs trust (and, for export and deletion, runs into
privacy law).

| | Free | Pro |
|---|---|---|
| Price | $0, no card | $2.99/month or $24/year (same as Setups.Bike) |
| Logging, full catalog, last time, full history, edit, past dates | ✅ unlimited | ✅ |
| Offline logging, per-set logging | ✅ | ✅ |
| PR badges, "beat last time" nudges | ✅ | ✅ |
| Progress chart: top weight, all time | ✅ | ✅ |
| Custom exercises | Up to 5 | Unlimited (`CUSTOM_EXERCISE_LIMIT` exists; unset until billing) |
| Charts: est. 1RM and volume, date ranges, compare exercises | — | ✅ |
| Weekly volume by muscle group, training summary | — | ✅ |
| Muscle-group heat map (body outline shaded by recency) | — | ✅ |
| View any past day's logs | ✅ | ✅ |
| Routines (saved workouts you log in order) | — | ✅ |
| Plate calculator, warm-up set suggestions | — | ✅ |
| Data export (CSV), account deletion | ✅ always | ✅ |

Rules (carried over from Setups.Bike):
- Limits are enforced in the API, not only the UI.
- If Pro lapses, nothing is deleted: extra custom exercises and routines become read-only, and
  the charts fall back to top weight.
- Billing ships behind a `BILLING_ENABLED_FOR` switch (only Grant at first), Stripe sandbox
  first, and Grant's account comped (`plan_source = 'comp'`).
- Note: est. 1RM and volume charts are free in the app today. With no users yet, moving them
  behind Pro takes nothing away from anyone.

**Depends on hosting:** Stripe's webhook needs a public HTTPS URL, so live billing waits for the
API host. Sandbox work can happen locally with `stripe listen --forward-to localhost:8000/...`.

**If it ever goes to the app stores**, Apple and Google rules for in-app purchases apply to
digital subscriptions sold inside a store app. As a PWA, Stripe is fine.

## Legal (needed before Pro or real users)

Port Setups.Bike's `legal/` setup (HTML templates filled from one `site.config.json`; any `TODO`
value fails the build) for:
- **Terms of Service**, including an exercise-risk / not-medical-advice disclaimer and
  subscription terms (auto-renewal, cancel anytime in the portal).
- **Privacy Policy**: what's stored (email, lifting logs, IP addresses for rate limits and
  logs), the processors (Neon, Resend, Stripe, the API host, Cloudflare), retention, export and
  deletion, minimum age 13. Check whether workout logs count as *consumer health data* under
  state laws such as Washington's My Health My Data Act, which has its own consent and
  privacy-policy rules.
- **Refunds and cancellation**, plus the auto-renewal disclosure shown next to the Subscribe
  button (California's automatic renewal law requires clear terms and online cancellation).
- A support email on the app's domain.

These are drafts for Grant's review, not legal advice; a template service or a lawyer's pass is
worth it before charging money.

## Scaffolding defaults (reviewed 2026-11-26)

The agent picked these to get started; Grant reviewed and kept them:

- Tokens last 30 days (Setups.Bike uses 7) so a phone at the gym rarely has to sign in again.
- A log entry is one weight × reps × sets row, matching the brief; per-set detail is Phase 1.
- Chart points are one per day (best entry for weight and 1RM, sum for volume).
- Dark theme by default with a light theme from the OS setting; orange accent.

Not changed in the review: the exercise catalog is shared and seeded by migration (per-user
custom exercises are Phase 1).
