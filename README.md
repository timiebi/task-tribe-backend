# Task Board — Backend

Django REST API for the Task Board app (tasks, notes, plans, events, auth).

## Local setup

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py createsuperuser   # optional
python manage.py runserver
```

- API: http://127.0.0.1:8000/api/
- Admin: http://127.0.0.1:8000/admin/

Without `DATABASE_URL`, SQLite is used for local dev.

## Deploy (Render + Neon)

1. **Neon** — [console.neon.tech](https://console.neon.tech) → your project → **Connection string** (PostgreSQL).
2. **Render** — deploy as a **Web Service**:
   - **Build command:** `./build.sh` or `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate --noinput`
   - **Start command:** `gunicorn config.wsgi:application` (or use the `Procfile`)
3. Copy env vars from **`.env.render.example`** into Render → Environment (replace every placeholder).
4. On **Cloudflare Pages**, set `NEXT_PUBLIC_API_URL` from **`frontend/.env.local.example`** (production section).

| Where | File |
|-------|------|
| Neon → `DATABASE_URL` only | paste into Render (see `.env.render.example`) |
| Render → all backend vars | `.env.render.example` |
| Cloudflare → frontend API URL | `frontend/.env.local.example` |

## API

| Resource | Endpoint |
|----------|----------|
| Health | `GET /api/health/` |
| Auth | `/api/auth/login/`, `register/`, `me/`, `logout/` |
| Notebooks, notes, plans, tasks, events | `/api/notebooks/`, etc. |

Authenticated routes use `Authorization: Token <token>`.
# task-tribe-backend
