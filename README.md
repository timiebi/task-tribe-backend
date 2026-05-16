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

1. Create a free PostgreSQL database at [neon.tech](https://neon.tech) and copy the connection string.
2. Deploy this repo on [Render](https://render.com) as a **Web Service**:
   - **Build command:** `./build.sh` or `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate --noinput`
   - **Start command:** `gunicorn config.wsgi:application` (or use the `Procfile`)
3. Set environment variables:

```env
DATABASE_URL=postgresql://...
DJANGO_SECRET_KEY=<long-random-secret>
DEBUG=False
ALLOWED_HOSTS=your-app.onrender.com
CORS_ALLOWED_ORIGINS=https://your-frontend.pages.dev
CSRF_TRUSTED_ORIGINS=https://your-frontend.pages.dev
```

Point the frontend `NEXT_PUBLIC_API_URL` at `https://your-app.onrender.com/api`.

## API

| Resource | Endpoint |
|----------|----------|
| Health | `GET /api/health/` |
| Auth | `/api/auth/login/`, `register/`, `me/`, `logout/` |
| Notebooks, notes, plans, tasks, events | `/api/notebooks/`, etc. |

Authenticated routes use `Authorization: Token <token>`.
# task-tribe-backend
