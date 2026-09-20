# MedAdvise AI - Backend

Django + Django REST Framework API. Uses SQLite locally by default and MySQL in production (set `DB_ENGINE=mysql` and the `DB_*` vars).

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

pip install -r requirements.txt
copy .env.example .env        # Windows
# cp .env.example .env        # macOS/Linux

python manage.py migrate
python manage.py runserver
```

Verify it's running: `GET http://localhost:8000/api/health/` should return `{"status": "ok"}`.

If you already had a venv from before JWT auth/models were added, re-run `pip install -r requirements.txt` and `python manage.py migrate` to pick up the new dependency and migrations.

## Tests

```bash
python manage.py test
```

## API

| Endpoint | Method | Auth | Notes |
|---|---|---|---|
| `/api/health/` | GET | none | health check |
| `/api/auth/register/` | POST | none | `{username, email, password}` |
| `/api/token/` | POST | none | `{username, password}` → `{access, refresh}` |
| `/api/token/refresh/` | POST | none | `{refresh}` → `{access}` |
| `/api/consultations/` | GET, POST | Bearer token | list/create your own consultations |

## Docker

Requires Docker Desktop. From the project root (one level up):

```bash
docker compose up --build
```

This runs the backend against MySQL (via the `db` service) instead of SQLite.
