# Overloader

A lifting log built for the gym floor: find an exercise, log weight × reps × sets in a couple of
taps, see what you did last time, and chart every entry to keep progressive overload on track.

- **Sign in by email.** No passwords: the API emails a 6-digit one-time code.
- **Searchable catalog** of ~90 common gym exercises (barbell, dumbbell, machine, cable,
  bodyweight, kettlebell), filterable by equipment.
- **Fast logging.** The form starts from your last entry, so matching it is one tap and beating
  it is two.
- **Progress chart** per exercise: top weight, estimated 1RM (Epley) or volume, per day.
- **Installable PWA** (works from the home screen; the catalog is cached for weak gym signal).

## Stack

| Part | Tech |
| --- | --- |
| Frontend | Vue 3 + TypeScript, Vite, vue-router, Chart.js, vite-plugin-pwa (S3 later) |
| API | Python 3.14, FastAPI, SQLAlchemy 2, Alembic, PyJWT |
| Database | Postgres on [Neon](https://neon.tech) |
| Email | [Resend](https://resend.com) (in dev, codes print in the API console) |
| CI | GitHub Actions: ruff + pytest against Postgres 18, vitest + type-check + build |

```
frontend/   Vue PWA            backend/   FastAPI app, Alembic migrations, pytest
docs/       roadmap, database, style guide, decisions log
```

## Run it locally

Needs Python 3.13+, Node 24+ and a Postgres database (a free Neon project works).

**API** (port 8000):

```powershell
cd backend
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
copy .env.example .env    # then fill in DATABASE_URL and JWT_SECRET
.venv\Scripts\alembic upgrade head
.venv\Scripts\uvicorn app.main:app --reload --port 8000
```

API docs are at http://localhost:8000/docs. With no `RESEND_API_KEY`, sign-in codes print in
this console.

**Web** (port 5180, proxies `/api` to :8000):

```powershell
cd frontend
npm install
npm run dev
```

**Tests:** `npm test` in `frontend/`; `pytest` in `backend/` with `TEST_DATABASE_URL` set to a
database the tests may wipe (CI uses a throwaway Postgres container).

> **Windows note:** if `import sqlalchemy` fails with *"An Application Control policy has blocked
> this file"* (Smart App Control), reinstall it without its compiled extension:
> `$env:DISABLE_SQLALCHEMY_CEXT=1; .venv\Scripts\python -m pip install --force-reinstall --no-deps --no-binary sqlalchemy sqlalchemy`

## Docs

[Roadmap](docs/ROADMAP.md) · [Database](docs/DATABASE.md) · [Style guide](docs/STYLE_GUIDE.md) ·
[Human in the loop: decisions log](docs/HUMAN_IN_THE_LOOP.md)

---

Source shown for portfolio purposes. All rights reserved; see [LICENSE](LICENSE).
