# Changelog

## 2.0.0 (in testing)

A full rewrite: a React single-page app on a FastAPI JSON API. The 1.x database is read as-is.

### New

- **New design:** a Revolut-style dark and light UI with bottom sheets, animated tab and sheet transitions, rolling-digit counters and haptic feedback. Reduced-motion settings are respected.
- **Breast side:** left or right for mother's-milk feeds, with the last side and time shown when logging.
- **Dashboard:** a live "since last feed" counter, current and previous sleep, a tappable 7-day chart and the baby's age.
- **History:** entries grouped by day with daily totals, filters and infinite scroll.
- **Installable PWA:** manifest, maskable icons, home-screen shortcuts, and a service worker with a fresh cache for every build, so updates arrive reliably.
- **Health check:** `GET /api/health`, used by the Docker `HEALTHCHECK`.
- **Prebuilt images:** amd64 and arm64 (Raspberry Pi 4/5) on `ghcr.io/kvboe/feedapp`.

### Improved

- **Several phones:** sleep start and stop are safe when used at once; a stale screen can't stop a sleep it meant to start.
- **Edits:** only the changed fields are saved, so sleep durations no longer shift by seconds.
- **Dates and time zones:** timestamps are stored in UTC; daily totals follow each phone's local days, including across DST changes.
- **Validation:** dates, times and amounts are checked before saving.
- **History paging:** stable keyset pagination, with no duplicates when new entries arrive, plus database indexes.

### Security

- Write requests must use `Content-Type: application/json`, so a web page opened on a phone in the same network can't add entries cross-site.

## 1.x

The original FastAPI + HTMX + Jinja app. It lives on the [`legacy`](https://github.com/kvboe/FeedApp/tree/legacy) branch and is no longer developed.
