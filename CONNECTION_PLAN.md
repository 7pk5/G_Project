# Miko × GSEB — Schedular ↔ Student App Connection Plan

---

## Current State (What Exists Now)

### `Schedular/assessment-planner-school.html`
A single self-contained HTML file. No backend, no database, no API calls.

- Teacher selects class, students, week type
- Tool calculates if students can be assessed before CP1
- Shows week-by-week, day-by-day schedule
- Generates a downloadable PDF plan
- **Nothing is saved anywhere** — refresh = everything resets

```
No server       ✗
No database     ✗
No login        ✗
No connection to student app  ✗
Just a calculator living in one HTML file  ✓
```

### `student/` — Flutter Web App (pre-built)

| File/Folder | What it is |
|---|---|
| `index.html` | App entry point |
| `main.dart.js` | Entire Flutter app compiled to JavaScript |
| `flutter_bootstrap.js` | Loads the Flutter engine |
| `canvaskit/` | WebAssembly rendering engine |
| `assets/audio/` | 4 pre-recorded TTS audio files |
| `assets/avatars/` | 10 student profile photos |
| `assets/packages/shared_core/mock/` | All app data — hardcoded JSON files |

**Mock JSON files:**

| File | Contains |
|---|---|
| `simulated_session_dialogue.json` | Full AI conversation script — 6 stages |
| `today_session.json` | Today's class list — 10 students with statuses |
| `class_sample.json` | Full class roster |
| `curriculum_sample.json` | Gujarat syllabus mapped to L1–L4 levels |
| `checkpoint_report_cp2.json` | Pre-made CP2 report |
| `holidays_2026.json` | Gujarat holiday calendar |

```
No server       ✗
No database     ✗
No real AI      ✗
No connection to Schedular  ✗
A scripted demo that simulates what the real product would do  ✓
```

---

## The Core Problem

The student app is **pre-compiled Flutter** — no source code available to modify directly. So we cannot change how it fetches data by editing Flutter files.

**Solution — Service Worker as a bridge:**

```
Student App                 Service Worker               Firebase
───────────                 ──────────────               ────────
fetch(today_session.json)
        │                   intercepts ───────────────▶  reads today's
        │                   returns real data ◀───────── plan from DB
        ▼
App renders with
real session data
```

The Service Worker sits between the app and its files, intercepts mock JSON requests, and swaps in real Firebase data. No Flutter recompile needed.

---

## Tech Stack

| What | Why |
|---|---|
| **Firebase Firestore** | Shared database — Schedular writes, Student reads |
| **Firebase Auth** | Teacher login — scopes data per school |
| **Firebase JS SDK** | Add to Schedular HTML directly, no build step |
| **Custom Service Worker** | Bridge for pre-compiled Flutter student app |
| **Plain HTML** | Teacher live dashboard — no framework needed |

---

## Database Structure

```
firestore/
├── schools/
│   └── {schoolId}/
│       ├── name: "Shri Ram Vidyalaya"
│       ├── sessions/
│       │   └── {date}/                   ← e.g. "2026-10-14"
│       │       ├── subject: "Mathematics"
│       │       ├── chapter: "Fractions"
│       │       ├── class: 5
│       │       ├── status: "active"
│       │       └── students/
│       │           ├── s001: { name, level, status, timeSpent }
│       │           ├── s002: { ... }
│       │           └── ...
│       └── plan/
│           └── {weekId}/                 ← weekly plan from Schedular
│               ├── week: 3
│               ├── subjects: [...]
│               └── studentOrder: [...]
```

---

## What Gets Built — 5 Pieces

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Schedular     │    │    Firebase       │    │  Student App    │
│   (upgraded)    │───▶│    Firestore      │◀───│  (via SW bridge)│
└─────────────────┘    └──────────────────┘    └─────────────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │  Teacher Dashboard   │
                    │  (live session view) │
                    └──────────────────────┘
```

### Piece 1 — Schedular gets Firebase + Confirm button
- Firebase JS SDK added to existing HTML (no rebuild)
- Teacher login with email/password
- "Confirm Plan" button writes weekly schedule to Firestore
- Each day's session auto-generated from the confirmed plan

### Piece 2 — Service Worker bridge for Student app
- Intercepts `fetch(today_session.json)` → returns today's Firestore session
- Intercepts `fetch(simulated_session_dialogue.json)` → returns chapter-matched dialogue
- After each student finishes → writes result back to Firestore

### Piece 3 — Teacher live dashboard
- Simple HTML page with Firestore real-time listener
- Shows who is done, in progress, pending, or flagged
- Updates live without refreshing

### Piece 4 — Auto session report
- End of day → Firestore summary auto-written
- CP1/CP2 progress tracked across weeks automatically

### Piece 5 — Teacher auth + school scoping
- Each school gets its own Firestore path
- Teacher logs in once, all data scoped to their school only

---

## Build Order & Timeline

```
Week 1 — Foundation
  Day 1-2:  Firebase project setup + Firestore schema
  Day 3-4:  Teacher auth + Schedular login screen
  Day 5:    Schedular "Confirm Plan" → writes to Firestore

Week 2 — Student Bridge
  Day 1-2:  Service Worker intercepts today_session.json
  Day 3-4:  Service Worker intercepts dialogue.json per chapter
  Day 5:    Student completion writes status back to Firestore

Week 3 — Teacher Dashboard + Reports
  Day 1-2:  Live dashboard HTML (real-time Firestore listener)
  Day 3-4:  End of day session report generation
  Day 5:    CP1/CP2 progress tracking across weeks

Week 4 — Polish
  Day 1-2:  Multi-school support
  Day 3-4:  Offline handling (what if iPad loses WiFi mid-session)
  Day 5:    End-to-end testing
```

---

## End-to-End Example — If Fully Built

---

### Sunday 8pm — Teacher at home

Teacher opens Schedular on laptop and logs in.

```
┌─────────────────────────────────────────┐
│  Assessment Planner · Class 5           │
│  Week of 14–18 Oct 2026                 │
│                                         │
│  Mon → Mathematics · Fractions (8 stu) │
│  Tue → Science · Plants        (8 stu) │
│  Wed → English · Paragraph     (8 stu) │
│  Thu → Mathematics · Fractions (8 stu) │
│  Fri → Buffer                          │
│                                         │
│  Student order auto-set by level        │
│  Aarav(L2) → Diya(L3) → Krish(L1)...  │
│                                         │
│  [ ✓ Confirm This Week's Plan ]         │
└─────────────────────────────────────────┘
```

Teacher clicks **Confirm**:
- Firestore gets 5 session documents written (one per school day)
- Each has student list, subject, chapter, and assessment order

---

### Monday 8:55am — School, iPad switches on

```
┌─────────────────────────────────────┐
│         🤖 Miko                     │
│                                     │
│  Good morning!                      │
│  Today: Mathematics · Fractions     │
│  8 students · est. 40 minutes       │
│                                     │
│  First up: Aarav Patel              │
│                                     │
│  [ Begin Session ]                  │
└─────────────────────────────────────┘
```

- Service Worker fires on app load
- Fetches today's date → finds matching session in Firestore
- App renders with real data — no teacher setup needed on iPad

---

### 9:00am — Aarav sits down

```
┌─────────────────────────────────────┐
│  👤 Aarav Patel · L2               │
│                                     │
│  🔊 "Hi Aarav! Today we're talking  │
│      about fractions. Ready?"       │
│                                     │
│  🔊 "A pizza is cut into 4 pieces.  │
│      You eat 2. What fraction       │
│      did you eat?"                  │
│                                     │
│  [pizza visual on screen]           │
│                                     │
│  [ Tap when Aarav finishes ]        │
└─────────────────────────────────────┘
```

Dialogue loaded from Firestore, matched to "Fractions" chapter.

Teacher taps → Miko evaluates:

```
┌─────────────────────────────────────┐
│  ✨ Level Up!  L2 → L3             │
│                                     │
│  🔊 "Excellent Aarav! You've really │
│      got fractions. See you         │
│      Thursday for the next round!"  │
│                                     │
│  [ Next Student → Diya Shah ]       │
└─────────────────────────────────────┘
```

Firestore updated instantly:
```
Aarav → status: done, level: L3, timeSpent: 4m20s
```

---

### 9:04am — Teacher's phone (anywhere in classroom)

```
┌─────────────────────────────────────┐
│  Live · Class 5 · Mathematics       │
│  Monday 14 Oct · Fractions          │
│  ─────────────────────────────────  │
│  ✅ Aarav Patel    L2→L3   4m20s   │
│  🔄 Diya Shah      in session       │
│  ⏳ Krish Mehta    pending          │
│  ⏳ Ananya Joshi   pending          │
│  ⚠️  Rohan Desai   needs support    │ ← AI flagged
│  ⏳ Priya Trivedi  pending          │
│  ─────────────────────────────────  │
│  2/8 done · ~32 min remaining      │
└─────────────────────────────────────┘
```

- Updates every time a student finishes
- Teacher can walk over to Rohan while session continues

---

### 9:45am — All 8 students done

```
┌─────────────────────────────────────┐
│  ✅ Session Complete                │
│  Mathematics · Fractions            │
│  8/8 students assessed              │
│                                     │
│  Level ups today: 3                 │
│  Aarav L2→L3  Diya L3→L4  Mira L1→L2│
│                                     │
│  Needs follow-up: Rohan (stuck L1)  │
│                                     │
│  Next session: Tomorrow             │
│  Science · Plants · 8 students      │
│                                     │
│  [ End Session ]                    │
└─────────────────────────────────────┘
```

- Firestore: session marked complete
- Report auto-written to database
- Next day's session already queued

---

### Friday — CP1 Progress (live, not hypothetical)

Schedular now shows real progress instead of just a calculator:

```
┌─────────────────────────────────────┐
│  CP1 Progress · Class 5             │
│  Week 3 of 8                        │
│  ─────────────────────────────────  │
│  Mathematics  ████████░░  32/40 stu │
│  Science      █████░░░░░  20/40 stu │
│  English      ███░░░░░░░  12/40 stu │
│  Social Sci   ░░░░░░░░░░   0/40 stu │
│  ─────────────────────────────────  │
│  On track for CP1 ✅               │
│  3 students need extra attention    │
│                                     │
│  [ Download CP1 Interim Report ]    │
└─────────────────────────────────────┘
```

---

## Before vs After

| | Before (Now) | After (Connected) |
|---|---|---|
| **Planning** | Teacher plans on Schedular, nothing saved | Plan saved to Firebase |
| **iPad setup** | Teacher manually sets up iPad every morning | iPad reads plan automatically on startup |
| **During session** | No visibility for teacher | Teacher sees live updates on phone |
| **Session data** | Lost on refresh | All results stored in Firebase |
| **Schedular** | Just a calculator with hypothetical numbers | Shows real progress against actual sessions done |
| **Reports** | None | Auto CP1/CP2 reports generated end of day |
| **Multi-day** | No memory between days | Full history across the year |
| **Multi-school** | Not possible | Each school has scoped data |

---

## What to Build First

**Piece 1 — Schedular → Firebase** is the fastest visible win.

- Add Firebase JS SDK to existing `assessment-planner-school.html`
- Add teacher login screen
- Add "Confirm Plan" button
- Write session data to Firestore

Everything else (student bridge, live dashboard, reports) builds on top of this foundation.

Once the plan is in Firebase, the rest is just reading it from different places.
