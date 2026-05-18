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
| Sharing | `/api/connections/`, `/api/shares/`, `/api/notifications/` |
| Web push | `/api/push/public-key/`, `subscribe/`, `unsubscribe/`, `run-due/` |

Authenticated routes use `Authorization: Token <token>`.

## Web push notifications (PWA)

This app supports real, background, OS-level push notifications via the standard
Web Push protocol with VAPID. No third-party push service is needed.

### One-time setup

1. **Generate VAPID keys** (only once for the lifetime of the app):

   ```bash
   python manage.py vapid_keygen
   ```

   It prints values for `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`,
   `VAPID_SUBJECT`, and `NEXT_PUBLIC_VAPID_PUBLIC_KEY`.

2. **Backend env vars** (Render → Environment):

   - `VAPID_PUBLIC_KEY` — from step 1
   - `VAPID_PRIVATE_KEY` — from step 1
   - `VAPID_SUBJECT` — `mailto:you@example.com`
   - `APP_FRONTEND_URL` — e.g. `https://task-board-frontend.kosutimiebinicholas.workers.dev`
   - `CRON_SECRET` — any long random string (used to authenticate the cron HTTP call)

3. **Frontend env var** (Cloudflare Pages → Settings → Environment variables):

   - `NEXT_PUBLIC_VAPID_PUBLIC_KEY` — same value as `VAPID_PUBLIC_KEY`

### Sending reminder pushes on a schedule

Pick **one** of these — both produce identical results:

**Option A — Render Cron Job (recommended).**

Create a new Render service of type *Cron Job* using the same repo. Set:

- Schedule: `* * * * *` (every minute)
- Command: `python manage.py send_due_pushes`
- Use the same env vars as the web service.

**Option B — Any external scheduler hitting an HTTP endpoint.**

For example, [cron-job.org](https://cron-job.org) (free). Configure a job that
runs every minute and sends:

```
POST https://<your-backend>/api/push/run-due/
Header: X-Cron-Secret: <the CRON_SECRET value>
```

The endpoint is idempotent and lightweight.

### How it works

- The frontend registers `/sw.js` as a service worker and subscribes to push
  via `pushManager.subscribe`, then stores that subscription server-side.
- When a task/event reminder is due, the cron sends a Web Push to every
  subscription belonging to the owner. The service worker shows a notification
  even if the tab/app is closed.
- When someone shares an item or sends a connection invite, the backend pushes
  immediately as well (no polling).
- Tapping a notification focuses the existing tab or opens the app at the
  right section (Tasks, Events, Notifications, …).

# task-tribe-backend
