# FeedApp

A minimal, fast, and modern Progressive Web App (PWA) for tracking baby feeding, sleep, and weight. Built with **FastAPI**, **HTMX**, and **Tailwind CSS**.

## 🚀 Features

### Tracking
- **🍼 Feeding**: Log specific amounts (ml) for **Formula** or **Mother's Milk**.
  - **Smart Defaults**: The app remembers your last used feed type (Formula/Mother's) for quicker logging.
  - **Backdating**: Easily log feeds from "15 minutes ago" or set exact past times.
- **🌙 Sleep**: Simple "Start Sleep" / "Wake Up" timer. Manual entry editing supported.
- **⚖️ Weight**: Track development with weight logs (grams).

### Insights & Analysis
- **📊 Charts**: 7-day bar chart showing total daily feed volume.
- **📈 Stats**: Quick view of:
  - Time since last feed / duration.
  - Current sleep duration (real-time).
  - Last sleep session duration.
- **🗓️ History**: Distinct color-coded timeline edits for all event types.

### Technical & UX
- **🌍 Timezone Aware**: 
  - All data stored in **UTC** for consistency.
  - Displayed in **Local Time** based on your browser/device settings (User-friendly for travel or DST).
- **📱 PWA Support**: Installable on iOS/Android (Add to Home Screen) with proper manifest and icons.
- **🔔 Toast Notifications**: Immediate feedback for actions (Logged, Updated, Deleted).
- **⚡ Single Page Feel**: HTMX powers seamless transitions without full page reloads.

## 🛠️ Tech Stack

- **Backend**: Python 3.12+, FastAPI, SQLite.
- **Frontend**: Jinja2 Templates, HTMX (interactions), Tailwind CSS (styling), Chart.js.
- **Deployment**: Docker & Docker Compose.

## 🐳 Installation (Docker Compose) - Recommended

The easiest way to run FeedApp is using Docker Compose.

### Prerequisites
- Docker
- Docker Compose

### Steps

1. **Clone the repository** (or copy the files):
   ```bash
   git clone <repository-url>
   cd FeedApp
   ```

2. **Start the application**:
   ```bash
   docker compose up -d
   ```
   *This will build the image and start the container in the background.*

3. **Access the App**:
   Open your browser and navigate to:
   👉 **http://localhost:8001**

   *(Note: The default host port is 8001; you can change this in `docker-compose.yml` if needed)*

4. **Data Persistence**:
   A Docker volume `feedapp_data` is created to persist your SQLite database (`feedapp.db`). Your data will survive container restarts.

### Stopping the App
```bash
docker compose down
```

## 🐍 Manual Installation (Python)

If you prefer to run without Docker:

1. **Set up a virtual environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the server**:
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

4. **Access**:
   http://localhost:8000

## 📂 Project Structure

- `main.py`: Core application logic, API routes, and database handling.
- `templates/`: HTML templates (Jinja2) using HTMX attributes.
- `static/`: Assets (manifest, icons, etc.).
- `Dockerfile` & `docker-compose.yml`: Containerization config.

## 📝 License

MIT
