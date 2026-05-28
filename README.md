# Miko Web Portal — GSEB

A local web server that serves the Miko student assessment app, teacher schedular, and a Firebase-backed session bridge for GSEB schools.

---

## What's Inside

| Path | What it does |
|---|---|
| `server.py` | Python HTTP server — entry point for everything |
| `setup.html` | One-time Firebase seed page (run before first use) |
| `Schedular/` | Teacher assessment planner (calculates and generates weekly plan) |
| `student/` | Pre-compiled Flutter web app (student-facing) |
| `student/today.html` | Today's session view |
| `student/app.html` | Full student app shell |
| `student/miko-bridge-sw.js` | Service worker that bridges Flutter ↔ Firebase live data |
| `CONNECTION_PLAN.md` | Architecture doc — how Schedular connects to the student app via Firebase |

---

## Requirements

- Python 3.8+
- Internet connection (for Firebase Firestore calls)
- A browser (Chrome recommended for service worker support)

No npm, no pip installs, no build step required.

---

## Quick Start

### 1. Clone the repo

```bash
git clone https://github.com/7pk5/G_Project.git
cd G_Project
```

### 2. Start the server

```bash
python3 server.py
```

You'll see:

```
  Miko Web Portal
  ────────────────────────────────────
  Setup      →  http://localhost:8080/setup
  Schedular  →  http://localhost:8080/schedular
  App        →  http://localhost:8080/app
  Today      →  http://localhost:8080/today
  Student    →  http://localhost:8080/student/
  Debug      →  http://localhost:8080/debug
  ────────────────────────────────────
  Press Ctrl+C to stop
```

### 3. Seed the database (first time only)

Open `http://localhost:8080/setup` in your browser and click **Seed 100 Students**. This writes student data into Firebase Firestore under `schools/demo-school/students/`. Do this once before using the Schedular.

---

## Routes

| URL | What you get |
|---|---|
| `http://localhost:8080/` | Redirects to `/student/` |
| `http://localhost:8080/student/` | Flutter student app (live Firebase data) |
| `http://localhost:8080/today` | Today's session page |
| `http://localhost:8080/app` | App shell |
| `http://localhost:8080/setup` | Database seeder |
| `http://localhost:8080/schedular` | Teacher assessment planner |
| `http://localhost:8080/debug` | JSON debug view — shows live Firebase state |

---

## Firebase Configuration

The server connects to a Firebase project. Config is set via environment variables (see `.env.example`):

```
FIREBASE_PROJECT_ID=your-project-id
SCHOOL_ID=your-school-id
FIREBASE_API_KEY=your-api-key
```

The server fetches the current session from:
```
schools/demo-school/meta/current_session
```

and injects it into the Flutter app via the `/today_session.json` endpoint. Session data is cached for 30 seconds.

---

## How the Firebase Bridge Works

The Flutter app is pre-compiled — its source cannot be changed. Instead, a Service Worker (`miko-bridge-sw.js`) intercepts the app's JSON fetch calls and swaps in live Firebase data:

```
Flutter app
  └── fetch("today_session.json")
           │
           ▼
    Service Worker            ← intercepts
           │
           ▼
    server.py /today_session.json
           │
           ▼
    Firebase Firestore        ← reads current_session doc
           │
           ▼
    Returns real student list back to Flutter
```

No recompile needed. The app renders real data transparently.

---

## Debug Endpoint

Open `http://localhost:8080/debug` to see a JSON snapshot of:

- Whether Firestore is reachable
- Current session subject, chapter, class
- Student count and source (`firestore` / `firestore_generated` / `mock`)
- What data Flutter will actually receive

---

## Schedular

Open `http://localhost:8080/schedular` for the teacher assessment planner.

The planner helps teachers:
- Select class and students for assessment
- Pick week type (regular / short week)
- Calculate if all students can be assessed before CP1/CP2
- Generate a day-by-day schedule
- Download a PDF plan

See `CONNECTION_PLAN.md` for the full architecture plan connecting the Schedular to live Firebase sessions.

---

## Stopping the Server

Press `Ctrl+C` in the terminal where `server.py` is running.
