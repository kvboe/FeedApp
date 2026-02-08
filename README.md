# FeedApp

Minimal, modern, and fast PWA for baby feeding and sleep tracking.

## Features
- Bottle feeding logging with optional backdating (minutes ago or exact time).
- Sleep tracking with start/stop and automatic duration calculation.
- Notes for diapers/medicine.
- Edit existing records (time, amount, notes; sleep start/end).
- Recent activity list (last 10) with color-coded types.
- PWA support with manifest and iOS meta tags.

## Tech Stack
- FastAPI (Python 3.12+)
- HTMX + Tailwind CSS
- SQLite
- Docker

## Run with Docker (recommended)
- Build and start the service using docker compose in the project root.
- Open http://localhost:8000 in a browser.
- The SQLite database is stored in a persistent Docker volume.

Configuration files:
- [Dockerfile](Dockerfile)
- [docker-compose.yml](docker-compose.yml)

## Run locally (venv)
- Install dependencies from [requirements.txt](requirements.txt).
- Start the server with Uvicorn using the app in [main.py](main.py).
- Set DB_PATH to a writable location (example: ./feedapp.db).

## Project Structure
- [main.py](main.py) — FastAPI app and routes
- [templates/](templates/) — HTMX templates
- [static/](static/) — PWA manifest and icon

## PWA
- Manifest: [static/manifest.json](static/manifest.json)
- Icon: [static/icon.svg](static/icon.svg)

## Notes
- This app is designed for a shared local database on a home server.
- For production use, consider adding authentication and HTTPS.
