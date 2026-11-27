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
- **Every push to `main` that touches `backend/` or `frontend/` deploys to production**
  (`deploy-api.yml` via `aws cloudformation deploy` with only `ImageTag` changed;
  `deploy-web.yml` to S3). Ask Grant before pushing to `main`; docs-only pushes don't deploy.
  Rollback: run deploy-api with `image_tag`.
- Production lives in `infra/` (registry, api and web stacks in us-west-2; step-by-step in
  `infra/README.md`). All IAM is in the registry stack, which only Grant deploys as root; GitHub's
  role can't change IAM. The API connects to Neon as `overloader_app` (migration 0004), never the
  owner. Secrets are NoEcho api-stack parameters; deploys keep their values.
- The web app is served by the Cloudflare Worker `overloader-edge` (`cloudflare/edge/worker.js`,
  pasted into the dashboard) at overloader.hiregrant.today until the final domain: `/api/*` goes to
  the Lambda Function URL with the origin secret and `X-Client-IP`, everything else to the S3
  bucket from `infra/web.yaml`.
- Before pushing: `ruff check . && ruff format --check . && pytest` in `backend/` (pytest needs
  `TEST_DATABASE_URL`, a database it may wipe) and `npm test && npm run build` in `frontend/`.
  CI (`.github/workflows/checks.yml`) runs the same.
- The API runs on AWS Lambda as a container image (Lambda Web Adapter + uvicorn, ARM64,
  us-west-2 next to Neon) behind a Function URL, with Cloudflare in front. Keep the app
  host-agnostic (no Lambda-specific code), so the same image can move to Fargate or Fly.io.
- UI follows `docs/STYLE_GUIDE.md`. Record Grant's engineering decisions in
  `docs/HUMAN_IN_THE_LOOP.md`, crediting him only for calls he made.
- Windows: Smart App Control blocks SQLAlchemy's compiled extension; see the README note.
