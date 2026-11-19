# FeedApp

A fast, installable Progressive Web App for tracking a baby's **feeds**, **sleep** and **weight**, with a Revolut-inspired UI and fluid animations.

## Features

- **Feeding**: log ml of **Formula** or **Mother's milk**. For mother's milk, choose the **left or right breast**; the next feed suggests the other side. Smart defaults pick the last type and amount. Quick amount chips, ±10 ml steppers, and backdating ("15 min ago", "1 h ago" or a custom number of minutes).
- **Sleep**: one-tap Start/Stop with a live timer, an optional note, and a "sleeping" indicator in the header.
- **Weight**: log grams, see the change since the last weigh-in, and a trend sparkline.
- **Dashboard**: a live "since last feed" counter, current and previous sleep, a 7-day feeding chart (tap a bar to see that day), recent entries, and the baby's age ("Day N", months and days).
- **History**: entries grouped by day like a bank-transactions list, with daily totals, the time since the previous entry, filters (Today / Feeds / Sleep / Weight / date range) and infinite scroll.
- **Edit and delete** any entry in a bottom sheet (feed: type, amount, time; sleep: start and end; weight: grams and time).
- **Settings**: the baby's birth date and the theme (Auto / Dark / Light).
- **Timezone aware**: stored in UTC and shown in the device's local time. Day filters and the chart follow local days.
- **PWA**: manifest, PNG and maskable icons, a service worker that caches the app shell, and home-screen shortcuts.

## Tech stack

| Layer    | Tech |
|----------|------|
| Frontend | React 19, TypeScript, Vite, Tailwind CSS 4, Motion (animations), TanStack Query, NumberFlow (rolling digits), Lucide icons, Inter |
| Backend  | Python 3.12, FastAPI (JSON API under `/api`), SQLite |
| Deploy   | Multi-stage Docker image (Node builds the SPA, Python serves the API and the static build) |

## Run with Docker Compose (recommended)

```bash
docker compose up -d --build
```

Open **http://localhost:8001**. Data lives in the `feedapp_data` volume (`/data/feedapp.db`). Existing v1 databases work as-is: on startup the app adds a nullable `side` column, and older entries simply have no side.

## Local development

```bash
# Backend (http://127.0.0.1:8000)
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend (http://localhost:5173, proxies /api to :8000)
cd frontend
npm install
npm run dev
```

Without Node installed locally, you can use Docker:

```bash
docker run --rm -u $(id -u):$(id -g) -v $PWD/frontend:/app -w /app node:22-alpine sh -c "npm ci && npm run build"
```

FastAPI serves `frontend/dist` automatically once it is built.

## API

| Method | Path | Purpose |
|--------|------|---------|
| GET    | `/api/summary?tz=&tz_offset=` | Last feed, sleep and weight, sleep state, 7-day totals (DST-aware with an IANA `tz`), birth date |
| GET    | `/api/entries?type=&start=&end=&limit=&before_created_at=&before_id=` | History, newest first, keyset-paged (pass the last item of the previous page) |
| POST   | `/api/feeds` | `{subtype, side?: "left" \| "right", amount_ml, notes?, created_at?}` (`side` applies only to `breast_milk`) |
| POST   | `/api/weights` | `{weight_g, notes?, created_at?}` |
| POST   | `/api/sleep` | `{action: "start" \| "stop", notes?}`; returns 409 if the state already changed (e.g. on another phone) |
| PATCH  | `/api/entries/{id}` | Partial edit: only the fields sent are changed |
| DELETE | `/api/entries/{id}` | Delete an entry |
| GET/PUT| `/api/settings` | `{birthdate}` |

Interactive docs: `/docs`.

## Project structure

```
app/            FastAPI app (main.py routes, crud.py SQL, schemas.py models)
frontend/       React SPA
  src/screens/  Home, History, Settings
  src/sheets/   Feed, Sleep, Weight, Edit bottom sheets
  src/components/ UI kit (BottomSheet, Segmented, EntryRow, WeekChart, …)
  public/       manifest, service worker, icons
Dockerfile      multi-stage build
```

## License

MIT
