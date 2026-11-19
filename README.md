# FeedApp

A fast, installable Progressive Web App for tracking a baby's **feeds**, **sleep** and **weight**, with a Revolut-inspired UI and fluid animations.

**Version 2.0.0.** This is a full rewrite of the original FastAPI + HTMX + Jinja app as a React single-page app on a FastAPI JSON API. See [What's new in 2.0.0](#whats-new-in-200).

## Features

- **Feeding**
  - Log ml of **Formula** or **Mother's milk**.
  - For mother's milk, choose the **left or right breast**. The next feed suggests the other side and shows when and which side was used last.
  - Smart defaults pick the last type and amount.
  - Quick amount chips and ±10 ml steppers.
  - Backdating: "15 min ago", "30 min ago", "1 h ago", or a custom number of minutes.
- **Sleep**: one-tap Start / Wake up with a live timer, an optional note, and a "sleeping" indicator on the dashboard. It is safe with several phones: a stale screen cannot stop a sleep it meant to start.
- **Weight**: log grams, see the change since the last weigh-in, and a trend sparkline.
- **Dashboard**
  - A live "since last feed" counter.
  - Current and previous sleep.
  - A 7-day feeding chart; tap a bar to see that day.
  - Recent entries.
  - The baby's age ("Day N", months and days).
- **History**
  - Entries grouped by day, like a list of bank transactions.
  - Daily totals and the time since the previous entry.
  - Filters: Today, Feeds, Sleep, Weight, date range.
  - Infinite scroll.
- **Edit and delete** any entry in a bottom sheet:
  - Feed: type, breast side, amount, time.
  - Sleep: start and end.
  - Weight: grams and time.
- **Settings**: the baby's birth date and the theme (Auto / Dark / Light).
- **Timezone aware**: data is stored in UTC and shown in the device's local time. Day filters and the chart follow local days, including across DST changes.
- **PWA**
  - Manifest, PNG and maskable icons.
  - A service worker that caches the app shell, with a fresh cache for every build.
  - Home-screen shortcuts: Log feed and Sleep.
- **Polish**: spring animations, rolling-digit counters, haptic feedback, and toasts. Reduced-motion settings are respected.

## Tech stack

| Layer    | Tech |
|----------|------|
| Frontend | React 19, TypeScript, Vite, Tailwind CSS 4, Motion (animations), TanStack Query, NumberFlow (rolling digits), Lucide icons, Inter |
| Backend  | Python 3.12, FastAPI (JSON API under `/api`), Pydantic, SQLite |
| Deploy   | Multi-stage Docker image: Node builds the SPA, and Python serves the API and the static build |

## Run the prebuilt image

GitHub Actions publishes images for **amd64** and **arm64** (including Raspberry Pi 4/5) to GitHub Container Registry. See `.github/workflows/docker.yml`.

```bash
docker run -d --name feedapp --restart unless-stopped \
  -p 8001:8000 -v feedapp_data:/data \
  ghcr.io/kvboe/feedapp:latest
```

Or with Compose:

```yaml
services:
  feedapp:
    image: ghcr.io/kvboe/feedapp:latest
    ports:
      - "8001:8000"
    volumes:
      - feedapp_data:/data
    restart: unless-stopped

volumes:
  feedapp_data:
```

| Tag | Built from |
|-----|------------|
| `latest`, `main` | the `main` branch |
| `v2.0.0` | the `v2.0.0` branch |
| `2.1.0`, `2.1`, `2` | the git tag `v2.1.0` |
| `sha-<commit>` | a single commit |

To update, run `docker pull ghcr.io/kvboe/feedapp:latest` and recreate the container. Data in the volume is kept.

## Build and run with Docker Compose

```bash
docker compose up -d --build
```

Open **http://localhost:8001**. To use another host port, change `ports` in `docker-compose.yml`.

The SQLite database is stored at `/data/feedapp.db` inside the `feedapp_data` compose volume. Docker names this volume `<project>_feedapp_data`, for example `feedapp_feedapp_data`. Data survives restarts and rebuilds.

Useful commands:

```bash
docker compose logs -f      # follow logs
docker compose down         # stop (data is kept)
```

### Install on a phone

1. Open the app's address in Safari (iOS) or Chrome (Android).
2. Choose **Add to Home Screen**.

Browsers enable the service worker (offline app shell) only on `localhost` or over **HTTPS**, for example behind a reverse proxy or Tailscale Serve. Over plain `http://` on a LAN address everything else works normally.

### Upgrading from v1

v2 reads the v1 database as-is. On startup it:

- adds a nullable `side` column for the breast side (older entries have no side);
- rewrites any non-canonical timestamps to UTC;
- creates two indexes.

These changes are additive, but v1 was never tested against a migrated database. Back up the volume first:

```bash
docker run --rm -v feedapp_feedapp_data:/data -v "$PWD":/backup alpine \
  cp /data/feedapp.db /backup/feedapp-backup.db
docker compose up -d --build
```

## Configuration

| Variable  | Default | Purpose |
|-----------|---------|---------|
| `DB_PATH` | `feedapp.db` (Docker: `/data/feedapp.db`) | SQLite database file; the folder is created if missing |

## Local development

```bash
# Backend (http://127.0.0.1:8000)
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend with hot reload (http://localhost:5173, proxies /api to :8000)
cd frontend
npm install
npm run dev
```

Other frontend scripts:

| Script | What it does |
|--------|--------------|
| `npm run typecheck` | TypeScript check |
| `npm run build` | Production build to `frontend/dist` |
| `npm run preview` | Serve the production build |

If Node is not installed locally, build with Docker instead:

```bash
docker run --rm -u $(id -u):$(id -g) -v $PWD/frontend:/app -w /app node:22-alpine sh -c "npm ci && npm run build"
```

FastAPI serves `frontend/dist` automatically once it is built. Without a build, non-API routes return HTTP 503 with a "Frontend not built" message.

## API

All timestamps are ISO 8601. The API returns UTC (`…+00:00`) and accepts any offset.

| Method  | Path | Purpose |
|---------|------|---------|
| GET     | `/api/summary?tz=&tz_offset=` | Last feed, last breast-side feed, last sleep, last weight, sleep state, 7-day totals and birth date. Week totals follow DST when given an IANA `tz`. |
| GET     | `/api/entries?type=&start=&end=&limit=&before_created_at=&before_id=` | History, newest first. Keyset-paged: pass the last item of the previous page. |
| GET     | `/api/entries/{id}` | A single entry |
| POST    | `/api/feeds` | `{subtype: "formula" \| "breast_milk", side?: "left" \| "right", amount_ml, notes?, created_at?}`. `side` is stored only for `breast_milk`. |
| POST    | `/api/weights` | `{weight_g, notes?, created_at?}` |
| POST    | `/api/sleep` | `{action: "start" \| "stop", notes?}`. Returns 409 if the state already changed, for example on another phone. |
| PATCH   | `/api/entries/{id}` | Partial edit; only the fields sent are changed. Switching a feed to formula clears its side. |
| DELETE  | `/api/entries/{id}` | Delete an entry |
| GET/PUT | `/api/settings` | `{birthdate}` |

Interactive docs are at `/docs`.

## Project structure

```
app/                 FastAPI backend
  main.py            routes, SPA hosting
  crud.py            SQL queries
  database.py        connection handling, schema and startup migrations
  schemas.py         Pydantic models
frontend/            React SPA
  src/screens/       Home, History, Settings
  src/sheets/        Feed, Sleep, Weight, Edit bottom sheets
  src/components/    UI kit (BottomSheet, Segmented, EntryRow, WeekChart, …)
  src/lib/           API client, queries, time helpers, types
  public/            manifest, service worker, icons
Dockerfile           multi-stage build (multi-arch ready)
.github/workflows/  CI: build and publish the image to ghcr.io
docker-compose.yml   production service on port 8001
```

## What's new in 2.0.0

- **New stack**: a React + TypeScript SPA replaces the Jinja/HTMX templates, and the backend is now a typed JSON API.
- **New design**: a Revolut-style dark/light UI with bottom sheets, animated tab and sheet transitions, and live counters.
- **Breast side**: left or right for mother's-milk feeds, with an alternating-side suggestion.
- **Edits**: partial edits keep the stored seconds, so sleep durations no longer shift.
- **Validation**: date and time fields are validated before saving.
- **Concurrency**: sleep start and stop are safe when used from several devices at once.
- **Date correctness**: DST-correct 7-day totals.
- **History**: stable keyset pagination with no duplicates when new entries arrive, plus database indexes.
- **PWA**: a service worker with a per-build cache, so updates arrive reliably.

## License

MIT
