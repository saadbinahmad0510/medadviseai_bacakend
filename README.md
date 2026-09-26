# MedAdvise AI - Backend

Django + Django REST Framework API. Serves a Keras/TensorFlow model that
grades knee osteoarthritis severity (Kellgren-Lawrence 0-4) from an X-ray,
plus an offline rule-based chat. Uses SQLite locally by default and MySQL
in production (set `DB_ENGINE=mysql` and the `DB_*` vars).

**Research prototype — not a medical device, not for clinical decisions.**

## Setup

```bash
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux

pip install -r requirements.txt
copy .env.example .env         # Windows
# cp .env.example .env         # macOS/Linux

python manage.py migrate
python manage.py runserver
```

Verify it's running: `GET http://localhost:8000/api/health/` should return
`{"status": "ok"}`.

## Verify the model

The model is loaded once at startup (`ApiConfig.ready()`), and expects
**grayscale, 224x224, raw `[0, 255]` float32 input — never divide by 255**
(the scaling is inside the model; see `api/inference.py` and
`asset/metrics.json`'s `input_contract`). To sanity-check preprocessing and
accuracy against the 15 labeled sample X-rays in `asset/samples/`:

```bash
python manage.py verify_model
```

This prints the preprocessed array's min/max/mean first (max should be
~255, not ~1 — if it's ~1, the `/255` bug is present) and then a table of
predicted vs. true grade. Grades 0, 3, 4 should mostly match; Grade 1 will
show real errors (its F1 is only ~0.39 — see `/metrics` in the frontend).

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
| `/api/consultations/` | GET, POST | Bearer token | list/create consultations; POST accepts `symptoms` and/or an `image` (multipart) — an image triggers real KOA grading |
| `/api/chat/` | POST | Bearer token | `{message, consultation_id?}` → `{reply, intent}`, offline rule-based chat over the live prediction + `asset/metrics.json` |

Uploaded images are capped at 10MB and must be a readable image file;
media is served from `MEDIA_URL`/`MEDIA_ROOT` in dev (`DEBUG=True`).

## Docker

Requires Docker Desktop. From the project root (one level up):

```bash
docker compose up --build
```

This runs the backend against MySQL (via the `db` service) instead of SQLite.
