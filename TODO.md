# Voice Journal — Project TODO

A local-first app to record your thoughts via speech, then automatically summarize, organize, and save them as structured journal entries — powered by Whisper and Ollama.

Read [GLOSSARY.md](./GLOSSARY.md) first. *Entry*, *Draft*, *Recording*, *Transcript*, and *Journal Day* all have precise meanings, and the tasks below assume them.

**MVP cut line:** Phases 1–5 plus the MVP slice of Phase 6. Everything marked *post-MVP* stays untouched until the core loop — record → transcribe → process → save → read — works end to end. The dashboard and export features are the easiest places to burn effort before the thing that matters is proven.

---

## Phase 1 — Repo Setup

- [x] Initialize repository: `git init nightly-journal-app`
- [x] Add `README.md` with project overview and setup instructions
- [x] Add `GLOSSARY.md` defining the domain vocabulary
- [x] Record the non-obvious decisions as ADRs in `docs/adr/`
- [x] Create the storage folders: `journals/` and `journals/.trash/`, each with a `.gitkeep` (`backend/`, `frontend/`, and `scripts/` arrive with their first real files — git can't track empty directories)
- [x] Add `.gitignore` (node_modules, __pycache__, .env, journals/, *.wav, *.mp3, *.webm)
- [x] Add `LICENSE` file
- [x] Pin Python version with `.python-version`
- [x] Add `.env.example` with all config variables documented, including `RETAIN_AUDIO`, `DAY_BOUNDARY_HOUR`, and `BACKEND_HOST=127.0.0.1`
- [x] Add `requirements.txt`

**Open from Phase 1:**

- [ ] Confirm the `LICENSE` copyright holder — currently "Daniel Simpson", inferred from the repo URL rather than confirmed
- [ ] Commit the Phase 1 files — `.gitignore`, `.env.example`, `.python-version`, `LICENSE`, `requirements.txt`, and `journals/` are still untracked
- `backend/`, `frontend/`, and `scripts/` are intentionally absent until their first real files land in Phase 2–3; git cannot track empty directories, so creating them now would achieve nothing on clone

```
nightly-journal-app/
├── frontend/                   # Web UI
│   ├── index.html
│   ├── style.css
│   └── app.js
├── backend/
│   ├── main.py                 # FastAPI entrypoint
│   ├── stt.py                  # Whisper transcription
│   ├── llm.py                  # Ollama summarize/organize client
│   ├── journal.py              # Entry creation, storage, retrieval
│   ├── index.py                # In-memory entry index, built at startup
│   └── models.py               # Pydantic data models
├── journals/                   # Local storage for entries (gitignored)
│   ├── .trash/                 # Deleted entries, kept for recovery
│   └── .gitkeep
├── docs/
│   └── adr/                    # Architecture decision records
├── scripts/
│   └── setup.sh                # One-shot install script
├── .env.example
├── requirements.txt
├── GLOSSARY.md
├── TODO.md
└── README.md
```

---

## Phase 2 — Audio Recording (Frontend)

- [x] Call `/health` on page load; enable recording/transcription only when `transcription.ready` is true, and show processing readiness from `processing.ready`
- [x] Implement `MediaRecorder` API in `app.js` to capture mic audio
- [x] Add a large, prominent record button with clear start/stop states
- [x] Show a live recording timer while capturing
- [x] Animate a waveform during recording (Web Audio API + canvas or CSS bars)
- [x] Save the Recording as a `webm` or `wav` blob in memory
- [x] Allow the user to preview/playback the Recording before submitting
- [x] Add a "re-record" option to discard and start over
- [x] POST the blob to `/transcribe`
- [x] Treat the client-side timer as a UI hint only — the backend measures the authoritative duration

---

## Phase 3 — Speech-to-Text (Whisper)

- [ ] Install faster-whisper: `pip install faster-whisper`
- [ ] Write `backend/stt.py` with a `transcribe(audio_path)` function returning transcript **and** measured duration
- [ ] Add `/transcribe` POST endpoint in `main.py` — accept audio, return both
- [ ] Load the model at startup, not on first request, so failures surface before anyone records
- [ ] Default `WHISPER_DEVICE=auto`: prefer CUDA, fall back to CPU with a loud warning rather than crashing
- [ ] Report the device actually in use via `/health`
- [ ] Return HTTP 200 from `/health` whenever the API is responsive, with `status` set to `ready` or `degraded` and separate transcription and processing readiness
- [ ] Check Ollama reachability at startup and on each `/health` request with a 2-second timeout; keep the backend running in degraded state if Ollama is unavailable
- [ ] Save the Recording temporarily, transcribe, then delete it — unless `RETAIN_AUDIO=true`
- [ ] Enforce the 2-second minimum here, using the measured duration
- [ ] Stop browser recording at 10 minutes and reject backend-measured audio longer than 600 seconds; do not auto-submit when the UI stops
- [ ] Choose default model size (`base` is a good balance of speed vs accuracy)
- [ ] Make model size configurable via `.env` (`WHISPER_MODEL=base`)
- [ ] Handle errors gracefully: empty audio, too-short clips, noisy input
- [ ] Return the Transcript to the frontend and display it for review before processing

---

## Phase 4 — LLM Processing (Ollama)

- [ ] Install Ollama and pull a model: `ollama pull llama3`
- [ ] Write `backend/llm.py` using Ollama's JSON-constrained output mode
- [ ] Design and test the core prompt (see Prompt Design section below)
- [ ] Add `/process` POST endpoint — accept a Transcript, return a **Draft**; never write to disk
- [ ] Validate the response against the Pydantic schema
- [ ] On validation failure, retry **once** with a repair prompt, then fail with a clear error
- [ ] On failure, keep the Transcript in the Draft so the user never loses a transcription
- [ ] Return `{ "error": { "code": "...", "message": "...", "retryable": true } }` for failures: `503 OLLAMA_UNAVAILABLE`, `502 PROCESSING_FAILED` after repair, or `504 PROCESSING_TIMEOUT`
- [ ] Enforce one 120-second total `/process` deadline, including the optional repair attempt; make failures user-retryable without exposing raw provider errors or returning a partial Draft
- [ ] Return the complete object — no streaming (parsing partial JSON isn't worth the complexity)
- [ ] Make model name and temperature configurable via `.env`
- [ ] Test with multiple models and document quality differences in README

### Prompt Design

- [ ] **Single structured prompt** returning one JSON object — not separate calls per field
- [ ] **System prompt** establishing a thoughtful, non-judgmental journaling assistant persona
- [ ] **Summarization** — condense rambling thoughts into a clean, first-person paragraph
- [ ] **Title generation** — a short, meaningful title (max 10 words)
- [ ] **Mood detection** — constrained to the fixed enum; reject anything outside it
- [ ] **Tag extraction** — 3–5 lowercase topic tags
- [ ] Pass the author's existing tags into the prompt as preferred vocabulary, to stop `mental health` / `mental-health` / `wellbeing` drift
- [ ] **Action items** — extract any tasks or commitments mentioned (may be empty)

---

## Phase 5 — Journal Entry Storage

- [ ] Define the Entry schema in `backend/models.py`:
  - `id` (uuid)
  - `created_at` (ISO timestamp, UTC)
  - `edited_at` (ISO timestamp, nullable — set on first PATCH)
  - `title` (LLM-generated)
  - `raw_transcript` (verbatim from Whisper, immutable)
  - `summary` (LLM-processed)
  - `mood` (closed enum with a valence of −1 / 0 / +1)
  - `tags` (list of strings)
  - `action_items` (optional list)
  - `audio_duration_seconds` (measured by the backend)
- [ ] Write `backend/journal.py` with save, load, list, delete functions
- [ ] Store entries as `journals/YYYY-MM-DD_slug_ab12cd34.json`, where the suffix is the first 8 chars of the uuid ([ADR 0001](./docs/adr/0001-entry-filename-identity.md))
- [ ] Resolve an Entry by ID via directory glob on that suffix — no index file
- [ ] Build an in-memory index at startup by parsing every file once; update it on write
- [ ] Implement Journal Day bucketing from `DAY_BOUNDARY_HOUR` in local time ([ADR 0002](./docs/adr/0002-journal-day-boundary.md))
- [ ] Add `POST /entries` — commit a reviewed Draft to disk
- [ ] Add `/entries` GET endpoint — return list of all entries (metadata only, served from the index)
- [ ] Add `/entries/{id}` GET endpoint — return full entry by ID
- [ ] Add `/entries/{id}` DELETE endpoint — move the file to `journals/.trash/`, don't unlink
- [ ] Add `/entries/{id}` PATCH endpoint — allow editing title, summary, mood, tags, action items
- [ ] Reject PATCH attempts on `raw_transcript`, `id`, `created_at`, `audio_duration_seconds`
- [ ] Set `edited_at` on first PATCH
- [ ] Ensure `journals/` and `journals/.trash/` are created on startup if missing

---

## Phase 6 — Frontend Journal UI

### MVP slice

- [ ] Build main layout: sidebar (entry list) + main panel (record / view entry)
- [ ] **Recording panel:**
  - [ ] Record button with animated state (idle → recording → processing)
  - [ ] Display the Transcript once Whisper returns it
  - [ ] Show the Draft once processing completes
  - [ ] "Save entry" and "Discard" buttons — Save calls `POST /entries`
  - [ ] Warn before navigating away with an unsaved Draft (it lives only in memory)
- [ ] **Entry list (sidebar):**
  - [ ] Show title, Journal Day, mood indicator, and tags per entry
  - [ ] Group by Journal Day; sort by most recent
- [ ] **Entry detail view:**
  - [ ] Display title, date, mood, tags, and summary
  - [ ] Collapsible section to show the raw Transcript
  - [ ] Delete button with confirmation
- [ ] Responsive layout — works well on both desktop and tablet

### Post-MVP

- [ ] Filter by tag
- [ ] Search by keyword across titles and summaries
- [ ] Edit mode for title, summary, mood, and tags (never the Transcript)
- [ ] Re-process button — re-runs the model over the stored Transcript and produces a **new Draft** to confirm, rather than overwriting in place (a hand-edited entry must not be silently destroyed)

---

## Phase 7 — Mood & Insights Dashboard *(post-MVP)*

- [ ] Add a `/insights` GET endpoint that aggregates entry data
- [ ] Build a simple dashboard view in the frontend:
  - [ ] Mood over time chart, plotted on valence (−1 / 0 / +1)
  - [ ] Most frequent tags (bar chart or tag cloud)
  - [ ] Streak tracker — consecutive Journal Days with at least one Entry, counting the current day inclusive so the streak doesn't read 0 every morning
  - [ ] Total entries count and total words recorded
- [ ] Use a lightweight charting lib (Chart.js or D3) — no build step needed via CDN

---

## Phase 8 — Export & Backup *(post-MVP)*

- [ ] Add `/export` GET endpoint that returns all entries as a single JSON file
- [ ] Add Markdown export: render each entry as a `.md` file
- [ ] Bundle multiple entries into a `.zip` for download
- [ ] Optional: export a single entry as a formatted PDF
- [ ] Optional: plain text export for import into Obsidian or Notion

---

## Phase 9 — DevEx & Tooling

- [ ] Write `scripts/setup.sh` — install Python deps, check Ollama, create journals/ dir
- [ ] Add `Makefile` targets: `make start`, `make backend`, `make frontend`, `make clean`
- [ ] Add hot-reload for backend: `uvicorn --reload --host 127.0.0.1`
- [ ] Serve frontend via FastAPI static files or a separate `live-server`
- [ ] Write at least one full-pipeline integration test: record audio → transcribe → process → save → retrieve, injecting fake Whisper and Ollama dependencies
- [ ] Keep routine API/pipeline tests independent of model downloads and services; add an opt-in live smoke test using a short audio fixture and fixed transcript, asserting non-empty transcription and a schema-valid Draft
- [ ] Add a test that a Journal Day boundary case (00:40 entry) buckets to the previous day
- [ ] Add basic input validation and error handling throughout the API
- [ ] Lint with `ruff check backend/`

---

## Stretch Goals

These define the end-state product; see the README roadmap for the product vision.

- [ ] Opt-in desktop-only wake word, detected locally with a visible listening indicator; never save or transcribe audio before the wake word
- [ ] One optional neutral evening reminder at an Author-chosen time; never mention Streaks, and skip it after an Entry is saved for that Journal Day
- [ ] Local desktop text-to-speech for Summaries and Weekly Reviews
- [ ] Encrypt Entries and the search index at rest with a non-recoverable journal passphrase
- [ ] Semantic search across entries using local embeddings (`nomic-embed-text` via Ollama), with an encrypted index — the point at which the in-memory index should be revisited
- [ ] Opt-in Weekly Reviews for Monday–Sunday Journal Days: generate on first unlock after the week ends, catch up missed weeks, skip empty weeks, mark outdated when sources change, and allow regenerate/delete but not edit
- [ ] Installable desktop app packaging
- [ ] Optional LAN phone capture: off by default, HTTPS with a guided local certificate, shared LAN password, all-phone sign-out on password change, capture/review/save only, no offline capture or archive browsing
- [ ] Allow a phone to enter the separate journal passphrase only to unlock saving for its current recording session; never store it on the phone
- [ ] Optional Prompts shown before recording and saved with the Entry as context, separate from the Transcript
- [ ] Include Prompts and Weekly Reviews in JSON/Markdown exports; derive optional PDF or app-specific files locally from the same content

Deliberately **not** planned: multi-user support. There is exactly one Author per installation, and adding users would change the storage model, the privacy model, and the meaning of a Streak.

---

## Stack Summary

| Layer | Tool | Notes |
|---|---|---|
| Audio recording | MediaRecorder API | Browser-native, no deps |
| Speech-to-text | faster-whisper | Local, GPU-accelerated with CPU fallback |
| LLM processing | Ollama (Llama 3 / Mistral) | Summarize, tag, detect mood; JSON-constrained output |
| Storage | JSON files on disk | Source of truth; portable, no DB needed |
| Indexing | In-memory, built at startup | Pure derived state — safe to throw away and rebuild |
| Backend | FastAPI + uvicorn | Lightweight Python API, bound to localhost |
| Frontend | Vanilla HTML/JS | Keep it simple, no framework needed |
| Charts | Chart.js | CDN import, no build step |