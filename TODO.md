# Voice Journal — Project TODO

A local-first app to record your thoughts via speech, then automatically summarize, organize, and save them as structured journal entries — powered by Whisper and Ollama.

---

## Phase 1 — Repo Setup

- [ ] Initialize repository: `git init nightly-journal-app`
- [ ] Create folder structure (see below)
- [ ] Add `.gitignore` (node_modules, __pycache__, .env, journals/, *.wav, *.mp3)
- [ ] Add `README.md` with project overview and setup instructions
- [ ] Add `LICENSE` file
- [ ] Pin Python version with `.python-version`
- [ ] Add `.env.example` with all config variables documented

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
│   └── models.py               # Pydantic data models
├── journals/                   # Local storage for journal entries (gitignored)
│   └── .gitkeep
├── scripts/
│   └── setup.sh                # One-shot install script
├── .env.example
├── requirements.txt
├── TODO.md
└── README.md
```

---

## Phase 2 — Audio Recording (Frontend)

- [ ] Implement `MediaRecorder` API in `app.js` to capture mic audio
- [ ] Add a large, prominent record button with clear start/stop states
- [ ] Show a live recording timer while capturing
- [ ] Animate a waveform during recording (Web Audio API + canvas or CSS bars)
- [ ] Save recorded audio as a `webm` or `wav` blob in memory
- [ ] Allow the user to preview/playback their recording before submitting
- [ ] Add a "re-record" option to discard and start over
- [ ] POST audio blob to `/transcribe` endpoint on the backend

---

## Phase 3 — Speech-to-Text (Whisper)

- [ ] Install faster-whisper: `pip install faster-whisper`
- [ ] Write `backend/stt.py` with a `transcribe(audio_path)` function
- [ ] Add `/transcribe` POST endpoint in `main.py` — accept audio, return transcript
- [ ] Save audio temporarily to disk, transcribe, then delete
- [ ] Choose default model size (`base` is a good balance of speed vs accuracy)
- [ ] Make model size configurable via `.env` (`WHISPER_MODEL=base`)
- [ ] Confirm GPU acceleration is working: `nvidia-smi` during transcription
- [ ] Handle errors gracefully: empty audio, too-short clips, noisy input
- [ ] Return transcript to frontend and display it for user review before processing

---

## Phase 4 — LLM Processing (Ollama)

- [ ] Install Ollama and pull a model: `ollama pull llama3`
- [ ] Write `backend/llm.py` with Ollama streaming client
- [ ] Design and test the core prompts (see Prompt Design section below)
- [ ] Add `/process` POST endpoint — accept raw transcript, return structured entry
- [ ] Implement streaming so the user sees the entry being written in real time
- [ ] Make model name and temperature configurable via `.env`
- [ ] Test with multiple models and document quality differences in README

### Prompt Design

- [ ] **Summarization prompt** — condense rambling thoughts into a clean paragraph
- [ ] **Title generation prompt** — create a short, meaningful entry title from content
- [ ] **Mood/tone detection prompt** — infer emotional tone (reflective, anxious, excited, etc.)
- [ ] **Tag extraction prompt** — pull out 3–5 relevant topic tags (e.g. work, health, goals)
- [ ] **Action items prompt** — optionally extract any tasks or commitments mentioned
- [ ] Combine all of the above into a single structured prompt returning JSON
- [ ] Add a system prompt that establishes a thoughtful, non-judgmental journaling assistant persona

---

## Phase 5 — Journal Entry Storage

- [ ] Define entry schema in `backend/models.py`:
  - `id` (uuid)
  - `created_at` (ISO timestamp)
  - `title` (LLM-generated)
  - `raw_transcript` (verbatim from Whisper)
  - `summary` (LLM-processed)
  - `mood` (detected tone)
  - `tags` (list of strings)
  - `action_items` (optional list)
  - `audio_duration_seconds`
- [ ] Write `backend/journal.py` with save, load, list, delete functions
- [ ] Store entries as individual JSON files in `journals/YYYY-MM-DD_title.json`
- [ ] Add `/entries` GET endpoint — return list of all entries (metadata only)
- [ ] Add `/entries/{id}` GET endpoint — return full entry by ID
- [ ] Add `/entries/{id}` DELETE endpoint
- [ ] Add `/entries/{id}` PATCH endpoint — allow editing the summary or title
- [ ] Ensure `journals/` directory is created on startup if it doesn't exist

---

## Phase 6 — Frontend Journal UI

- [ ] Build main layout: sidebar (entry list) + main panel (record / view entry)
- [ ] **Recording panel:**
  - [ ] Record button with animated state (idle → recording → processing)
  - [ ] Display live transcript as it's returned from Whisper
  - [ ] Show streaming LLM output as the entry is being written
  - [ ] "Save entry" and "Discard" buttons after processing
- [ ] **Entry list (sidebar):**
  - [ ] Show title, date, mood indicator, and tags per entry
  - [ ] Sort by most recent by default
  - [ ] Filter by tag
  - [ ] Search by keyword across titles and summaries
- [ ] **Entry detail view:**
  - [ ] Display title, date, mood, tags, and summary
  - [ ] Collapsible section to show the raw transcript
  - [ ] Edit mode for title and summary
  - [ ] Delete button with confirmation
  - [ ] Optional: re-process button to regenerate summary with a different prompt
- [ ] Responsive layout — works well on both desktop and tablet

---

## Phase 7 — Mood & Insights Dashboard

- [ ] Add a `/insights` GET endpoint that aggregates entry data
- [ ] Build a simple dashboard view in the frontend:
  - [ ] Mood over time chart (line or dot chart)
  - [ ] Most frequent tags (bar chart or tag cloud)
  - [ ] Streak tracker — how many consecutive days have entries
  - [ ] Total entries count and total words recorded
- [ ] Use a lightweight charting lib (Chart.js or D3) — no build step needed via CDN

---

## Phase 8 — Export & Backup

- [ ] Add `/export` GET endpoint that returns all entries as a single JSON file
- [ ] Add Markdown export: render each entry as a `.md` file
- [ ] Bundle multiple entries into a `.zip` for download
- [ ] Optional: export a single entry as a formatted PDF
- [ ] Optional: plain text export for import into Obsidian or Notion

---

## Phase 9 — DevEx & Tooling

- [ ] Write `scripts/setup.sh` — install Python deps, check Ollama, create journals/ dir
- [ ] Add `Makefile` targets: `make start`, `make backend`, `make frontend`, `make clean`
- [ ] Add hot-reload for backend: `uvicorn --reload`
- [ ] Serve frontend via FastAPI static files or a separate `live-server`
- [ ] Write at least one integration test: record audio → transcribe → process → save → retrieve
- [ ] Add basic input validation and error handling throughout the API
- [ ] Lint with `ruff check backend/`

---

## Stretch Goals

- [ ] Wake word to start recording hands-free ("Hey Journal...")
- [ ] Daily reminder / notification to make an entry (desktop notification API)
- [ ] Voice playback of the generated journal entry (TTS)
- [ ] Multi-user support with separate journal directories per user
- [ ] Encrypt the `journals/` folder at rest
- [ ] Semantic search across entries using local embeddings (`nomic-embed-text` via Ollama)
- [ ] Weekly summary — auto-generate a week-in-review entry from the past 7 entries
- [ ] Electron app packaging for a standalone desktop experience
- [ ] Mobile PWA support (record from phone, sync to desktop)
- [ ] Custom guided reflection prompts shown before recording

---

## Stack Summary

| Layer | Tool | Notes |
|---|---|---|
| Audio recording | MediaRecorder API | Browser-native, no deps |
| Speech-to-text | faster-whisper | Local, GPU-accelerated |
| LLM processing | Ollama (Llama 3 / Mistral) | Summarize, tag, detect mood |
| Storage | JSON files on disk | Simple, portable, no DB needed |
| Backend | FastAPI + uvicorn | Lightweight Python API |
| Frontend | Vanilla HTML/JS | Keep it simple, no framework needed |
| Charts | Chart.js | CDN import, no build step |