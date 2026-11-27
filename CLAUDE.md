# Overloader: notes for Claude sessions

- Public repo (portfolio). Never commit secrets: `backend/.env` is git-ignored, and passwords,
  keys and connection strings stay out of chat. Grant enters them himself.
- Work is tracked on Grant's private GitHub Project "Overloader" (draft cards, not issues, so
  the plan stays private). Move a card to In progress when starting and Done when finished.
- Layout: `frontend/` (Vue 3 + Vite PWA, port 5180) and `backend/` (FastAPI, port 8000). The
  Vite dev server proxies `/api` to the API, so local dev needs no CORS.
- Schema changes are Alembic migrations in `backend/migrations/versions/`; keep
  `backend/app/models.py` in step and update `docs/DATABASE.md` in the same change.
- The standard exercise list is `backend/catalog/exercises.csv`, not a migration. After
  `alembic upgrade head`, run `python -m app.catalog` (dry run) then `--apply`. Never delete a
  catalog row from the database; the sync retires it.
- `backend/Dockerfile` is the production image (Lambda Web Adapter 1.1.0, ARM64, non-root,
  `ENV=production` by default). Docker isn't installed on Grant's PC; the `image` job in
  `checks.yml` builds it on `ubuntu-24.04-arm` and smoke-tests migrate / catalog sync / serve.
  Keep the app free of Lambda-specific code.
- Production lives in `infra/` (two CloudFormation stacks Grant deploys as root in us-west-2;
  step-by-step in `infra/README.md`) and `.github/workflows/deploy-api.yml` (manual trigger).
  The API connects to Neon as `overloader_app` (migration 0004), never the owner. Behind
  Cloudflare set `ORIGIN_SECRET` and `CLIENT_IP_HEADER`. Ask Grant before running a deploy.
- The web app is served by the Cloudflare Worker `overloader-edge` (`cloudflare/edge/worker.js`,
  pasted into the dashboard) at overloader.hiregrant.today until the final domain: `/api/*` goes to
  the Lambda Function URL with the origin secret, everything else to the S3 bucket from
  `infra/web.yaml`. `deploy-web.yml` uploads the build (manual trigger; ask Grant first).
- Before pushing: `ruff check . && ruff format --check . && pytest` in `backend/` (pytest needs
  `TEST_DATABASE_URL`, a database it may wipe) and `npm test && npm run build` in `frontend/`.
  CI (`.github/workflows/checks.yml`) runs the same.
- No deploys exist yet. Decided 2026-11-26: the API runs on AWS Lambda as a container image
  (Lambda Web Adapter + uvicorn, ARM64, us-west-2 next to Neon) behind a Function URL, with
  Cloudflare in front; the frontend goes to S3 behind Cloudflare. Keep the app host-agnostic
  (no Lambda-specific code), so the same image can move to Fargate or Fly.io.
- UI follows `docs/STYLE_GUIDE.md`. Record Grant's engineering decisions in
  `docs/HUMAN_IN_THE_LOOP.md`, crediting him only for calls he made.
- Windows: Smart App Control blocks SQLAlchemy's compiled extension; see the README note.
