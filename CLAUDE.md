# Overloader: notes for Claude sessions

- Public repo (portfolio). Never commit secrets: `backend/.env` is git-ignored, and passwords,
  keys and connection strings stay out of chat. Grant enters them himself.
- Work is tracked on Grant's private GitHub Project "Overloader" (draft cards, not issues, so
  the plan stays private). Move a card to In progress when starting and Done when finished.
- Layout: `frontend/` (Vue 3 + Vite PWA, port 5180) and `backend/` (FastAPI, port 8000). The
  Vite dev server proxies `/api` to the API, so local dev needs no CORS.
- Schema changes are Alembic migrations in `backend/migrations/versions/`; keep
  `backend/app/models.py` in step and update `docs/DATABASE.md` in the same change.
- Before pushing: `ruff check . && ruff format --check . && pytest` in `backend/` (pytest needs
  `TEST_DATABASE_URL`, a database it may wipe) and `npm test && npm run build` in `frontend/`.
  CI (`.github/workflows/checks.yml`) runs the same.
- No deploys exist yet. The frontend will go to S3; API hosting is undecided.
- UI follows `docs/STYLE_GUIDE.md`. Record Grant's engineering decisions in
  `docs/HUMAN_IN_THE_LOOP.md`, crediting him only for calls he made.
- Windows: Smart App Control blocks SQLAlchemy's compiled extension; see the README note.
