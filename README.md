# Voice Journal

A local-first journaling app that turns your spoken thoughts into structured, searchable journal entries. Press record, speak freely, and let Whisper transcribe and Ollama summarize, tag, and organize everything — entirely on your own machine.

```
Microphone → Whisper (STT) → Ollama (LLM) → Structured Journal Entry → Local Storage
```

No cloud. No subscriptions. Everything runs on your own machine — see [Privacy & Threat Model](#privacy--threat-model) for exactly what that does and does not protect.

---

## What It Does

1. **Record** — hit the mic button and speak your thoughts, unfiltered
2. **Transcribe** — faster-whisper converts your speech to text locally; the audio itself is then discarded
3. **Process** — Ollama reads the transcript and produces a **draft** containing:
   - A clean, readable **summary**
   - A meaningful **title**
   - A **mood**, chosen from a fixed set (reflective, anxious, grateful, excited…)
   - **Topic tags** (work, health, relationships, goals…)
   - Any **action items** you mentioned
4. **Review & save** — you read the draft and either save it as a JSON file in your local `journals/` folder, or discard it
5. **Revisit** — browse past entries and correct anything the model got wrong
6. **Insights** — visualize mood trends, streaks, and frequent topics over time *(planned)*

The draft in step 4 lives in your browser and is never written to disk until you save it. The transcript, once saved, is never altered — see [What you can edit](#what-you-can-edit).

---

## Features

- 🎙 **Local speech-to-text** via faster-whisper — audio is transcribed on your machine, then deleted
- 🧠 **LLM-powered journaling** via Ollama — summarize, title, tag, and detect mood
- 📓 **Clean journal UI** with sidebar navigation and an entry detail view
- 💾 **Plain JSON storage** — no database, entries are readable files you own
- 🗑 **Recoverable deletes** — removed entries move to `journals/.trash/`, never straight to oblivion
- 🔒 **Runs entirely on localhost** — nothing is sent anywhere
- 📊 **Insights dashboard** — mood over time, tag cloud, and entry streaks *(planned)*
- 🔍 **Search and tag filtering** *(planned)*
- 📤 **Export to Markdown, JSON, or ZIP** *(planned)*

---

## Requirements

- **OS:** Linux, macOS, or Windows (WSL2 recommended)
- **GPU:** Recommended — NVIDIA with 4 GB+ VRAM (CUDA 11.8+), or Apple Silicon (Metal). Not required: without one, Whisper falls back to CPU and simply runs slower.
- **Python:** 3.10+
- **Browser:** Any modern browser (Chrome/Edge preferred for mic permissions)

### Recommended GPU / model pairings

| GPU VRAM | Whisper model | LLM model |
|---|---|---|
| 4 GB | `base` | `mistral:7b` |
| 6 GB | `small` | `llama3:8b` |
| 8 GB | `medium` | `llama3:8b` |
| 16 GB+ | `large-v3` | `llama3:13b` |

---

## Project Structure

```
nightly-journal-app/
├── frontend/
│   ├── index.html          # Main UI
│   ├── style.css
│   └── app.js              # Recording, API calls, UI logic
├── backend/
│   ├── main.py             # FastAPI app + route definitions
│   ├── stt.py              # faster-whisper transcription
│   ├── llm.py              # Ollama client (summarize, tag, mood)
│   ├── journal.py          # Entry CRUD and file storage
│   ├── index.py            # In-memory entry index, built at startup
│   └── models.py           # Pydantic schemas
├── journals/               # Your entries live here (gitignored)
│   ├── .trash/             # Deleted entries, kept for recovery
│   └── .gitkeep
├── docs/
│   └── adr/                # Architecture decision records
├── scripts/
│   └── setup.sh
├── .env.example
├── requirements.txt
├── GLOSSARY.md             # Project vocabulary — read this first
├── TODO.md
└── README.md
```

---

## Quickstart

### 1. Install Ollama and pull a model

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3
ollama serve
```

### 2. Clone and install

```bash
git clone https://github.com/danielbsimpson/nightly-journal-app.git
cd nightly-journal-app

python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

### 3. Configure

```bash
cp .env.example .env
# Edit .env — set your model names, ports, etc.
```

### 4. Start the backend

```bash
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

The Whisper model loads at startup, so a bad model name or a broken CUDA install fails here — before you've spoken into a microphone, rather than after.

### 5. Check everything is wired up

```bash
curl http://localhost:8000/health
```

This returns HTTP 200 whenever the API is responsive and reports stage-specific readiness. `status` is `ready` when both stages are available and `degraded` otherwise; `transcription.ready` includes the actual Whisper device, while `processing.ready` reports Ollama availability. The frontend enables recording/transcription when transcription is ready and processing only when processing is ready.

Ollama reachability is checked at startup and again for each `/health` request, with a 2-second timeout. If Ollama is unavailable, the backend still starts and reports degraded readiness; only processing is unavailable. Whisper startup failures remain fatal.

```json
{
  "status": "degraded",
  "transcription": { "ready": true, "device": "cpu" },
  "processing": { "ready": false }
}
```

### 6. Open the frontend

```bash
# Serve via FastAPI static files (default) — just open:
open http://localhost:8000

# Or use live-server for hot-reload during development:
npx live-server frontend/
```

---

## Configuration

```env
# Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3
OLLAMA_TEMPERATURE=0.5

# Whisper
WHISPER_MODEL=base          # tiny | base | small | medium | large-v3
WHISPER_DEVICE=auto         # auto | cuda | cpu — auto falls back to CPU with a warning
WHISPER_LANGUAGE=en         # or leave blank for auto-detect

# Storage
JOURNALS_DIR=./journals
RETAIN_AUDIO=false          # true keeps the source recording alongside its entry

# Journaling
DAY_BOUNDARY_HOUR=4         # a journal day runs 04:00 → 04:00 local time

# Backend
BACKEND_HOST=127.0.0.1      # do not expose this to your network — see Privacy below
BACKEND_PORT=8000
```

The mood vocabulary is deliberately **not** configurable — see [Mood vocabulary](#mood-vocabulary).

---

## API Reference

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | HTTP 200 when responsive; overall status and separate transcription/device and processing readiness |
| `/transcribe` | POST | Upload audio blob → returns transcript + measured duration |
| `/process` | POST | Send transcript → returns a **draft** entry (nothing is saved) |
| `/entries` | POST | Save a reviewed draft as an entry |
| `/entries` | GET | List all entries (metadata only) |
| `/entries/{id}` | GET | Get full entry by ID |
| `/entries/{id}` | PATCH | Correct any model-derived field — never the transcript |
| `/entries/{id}` | DELETE | Move an entry to `journals/.trash/` |
| `/insights` | GET | Aggregated mood, tag, and streak data *(planned)* |
| `/export` | GET | Download all entries as ZIP *(planned)* |

`/process` is a pure function: it reads a transcript and returns a draft without touching disk. The draft lives in the browser until you `POST /entries`. Responses are returned complete rather than streamed. Each request has a 120-second total deadline, including the optional single repair attempt. Failures use `{ "error": { "code": "...", "message": "...", "retryable": true } }`: Ollama unavailable returns `503 OLLAMA_UNAVAILABLE`, invalid output after repair returns `502 PROCESSING_FAILED`, and the deadline returns `504 PROCESSING_TIMEOUT`. The frontend keeps the transcript available for an explicit retry; no partial Draft or raw provider error is returned.

### Example: process a transcript

```bash
curl -X POST http://localhost:8000/process \
  -H "Content-Type: application/json" \
  -d '{"transcript": "Today was really tough at work, I kept second-guessing my decisions on the project. But I went for a long run in the evening and felt a lot better afterwards. Need to remember to block focus time tomorrow morning."}'
```

**Response:**
```json
{
  "title": "A Tough Day Redeemed by an Evening Run",
  "summary": "Work felt overwhelming with self-doubt around project decisions. An evening run helped reset mentally. A reminder to protect morning focus time was noted.",
  "mood": "reflective",
  "tags": ["work", "mental health", "exercise", "productivity"],
  "action_items": ["Block focus time tomorrow morning"]
}
```

---

## Journal Entry Schema

Each entry is stored as a JSON file in `journals/`:

```json
{
  "id": "a3f9c2d1-...",
  "created_at": "2025-11-04T19:32:00Z",
  "edited_at": null,
  "title": "A Tough Day Redeemed by an Evening Run",
  "summary": "Work felt overwhelming with self-doubt...",
  "raw_transcript": "Today was really tough at work, I kept second-guessing...",
  "mood": "reflective",
  "tags": ["work", "mental health", "exercise", "productivity"],
  "action_items": ["Block focus time tomorrow morning"],
  "audio_duration_seconds": 47
}
```

Files are named `YYYY-MM-DD_slugified-title_ab12cd34.json`, where the suffix is the first eight characters of the entry's `id`. This keeps the folder sortable and readable while making lookup by ID a simple glob. See [ADR 0001](./docs/adr/0001-entry-filename-identity.md) — note that renaming an entry's title does *not* rename its file.

`created_at` is stored in UTC, but entries are grouped into **journal days** that run from `DAY_BOUNDARY_HOUR` to the same hour next morning, so a 00:40 entry counts towards the night it describes. See [ADR 0002](./docs/adr/0002-journal-day-boundary.md).

### What you can edit

The transcript is the record; everything else is interpretation. `PATCH` may change the **title, summary, mood, tags, and action items** — anything the model produced, so you can correct it when it gets you wrong. It may never change `raw_transcript`, `id`, `created_at`, or `audio_duration_seconds`. The first edit sets `edited_at`, so a hand-corrected mood stays distinguishable from a generated one.

Since the recording is discarded after transcription, a transcript can never be regenerated — which is precisely why it is immutable.

---

## Mood vocabulary

Mood is a closed set fixed in code, not a configurable list. Each value carries a **valence** so that mood can be plotted on a real axis:

| Mood | Valence |
|---|---|
| `grateful` | +1 |
| `excited` | +1 |
| `hopeful` | +1 |
| `reflective` | 0 |
| `neutral` | 0 |
| `anxious` | −1 |
| `frustrated` | −1 |
| `sad` | −1 |

A per-installation vocabulary would leave the mood chart with no stable axis and would silently invalidate older entries whenever it changed. Valence exists to order the chart — it is not a score of your day.

---

## LLM Prompt Design

The core processing prompt asks Ollama to return a single JSON object from the transcript. A simplified version:

```
You are a thoughtful journaling assistant. Given a raw spoken transcript, 
return ONLY a JSON object with these fields:
- title: a short, meaningful title (max 10 words)
- summary: a clear, first-person summary (2–4 sentences)
- mood: one of [reflective, grateful, anxious, excited, frustrated, neutral, sad, hopeful]
- tags: array of 3–5 lowercase topic tags
- action_items: array of any tasks or commitments mentioned (can be empty)

Prefer these existing tags where they fit: {the author's current tags}

Transcript: "..."
```

Tags stay free-form, but the author's existing tags are passed in as preferred vocabulary. Without this, the model invents `mental health`, `mental-health`, and `wellbeing` for the same idea, and the tag filter fragments into uselessness at exactly the point it would start being valuable.

### Handling bad output

The request is sent with Ollama's JSON-constrained output mode and the response is validated against the entry schema. On a validation failure the backend retries **once** with a repair prompt. If the result is still invalid, `/process` returns `502 PROCESSING_FAILED`; unavailability returns `503 OLLAMA_UNAVAILABLE`, and exceeding the 120-second total request deadline returns `504 PROCESSING_TIMEOUT`. All use the stable error envelope described above, and the transcript remains in the browser draft for a user-triggered retry.

Routine API and full-pipeline tests inject fake Whisper and Ollama dependencies, so they do not download models or require model services. An opt-in live smoke test uses a short audio fixture with Whisper and a fixed transcript with Ollama, asserting a non-empty transcript and a schema-valid Draft rather than exact generated wording. Keep the planned multiple-model coverage and document observed quality differences.

---

## Privacy & Threat Model

Be clear about what "local-first" buys you here, because a journal is about as sensitive as personal data gets.

**What is protected:** no audio, transcript, or entry is ever sent off your machine. There is no telemetry, no account, and no network dependency beyond `localhost`.

**What is not protected:**

- **Entries are stored in plaintext.** Anyone who can read your filesystem can read your journal — including backup software, sync clients, and anyone with your unlocked machine.
- **There is no authentication.** The API trusts every caller. The trust boundary is the machine, not the user.
- **The backend binds to `127.0.0.1` by default. Leave it there.** Binding to `0.0.0.0` exposes an unauthenticated read/write journal API to everyone on your network.
- **Deleted entries go to `journals/.trash/`,** not oblivion. Empty it yourself if you need something truly gone.

Encryption at rest and optional phone capture over the local network are planned for the end product, not the current build; see the [Roadmap](#roadmap). Until then, treat `journals/` with the same care as the diary itself and leave the backend on `127.0.0.1`.

---

## Troubleshooting

**Whisper is running on CPU and feels slow**
`WHISPER_DEVICE=auto` prefers CUDA but falls back to CPU rather than crashing, so a broken CUDA install shows up as slowness, not an error. Check which device it actually chose with `curl localhost:8000/health`. If it says `cpu` and you expected otherwise, confirm with `python -c "import torch; print(torch.cuda.is_available())"` and reinstall PyTorch for your CUDA version.

**Backend fails on startup with a model error**
The Whisper model loads at startup by design, so model and device problems surface before you record rather than after. Check `WHISPER_MODEL` is a valid size and that you have the VRAM for it.

**Processing fails with a schema error**
The backend already requests JSON-constrained output and retries once with a repair prompt. If it still fails, your model is struggling with structured output — `llama3:8b` and `mistral:7b` are well-tested; very small models like `phi3:mini` are not. Your transcript is preserved in the draft, so you can retry without re-recording.

**Mic not working in the browser**
Browsers require HTTPS or `localhost` for microphone access. Accessing via an IP address (e.g. `192.168.x.x`) will be blocked. Use `localhost:8000` directly.

**"Recording too short"**
The backend requires at least 2 seconds and allows at most 10 minutes of audio, measuring duration itself during transcription. The UI stops capture at 10:00 but does not submit automatically; the user can then choose Transcribe. The backend rejects recordings measured at more than 600 seconds, so a client-side timer cannot bypass the limit. Very short clips produce empty transcripts, so they're rejected before reaching the model.

**I deleted an entry by accident**
It's in `journals/.trash/`. Move the file back into `journals/` and restart the backend to rebuild the index.

**An entry is filed under the wrong day**
Entries are grouped by journal day, which ends at `DAY_BOUNDARY_HOUR` (default 04:00), so a 01:00 entry counts towards the previous evening. Adjust the hour if your hours are unusual — note that changing it re-buckets existing entries and can change your streak.

**`journals/` directory not found**
The backend creates it on startup automatically. If running the frontend standalone without the backend, create it manually: `mkdir journals`.

---

## Roadmap

See [TODO.md](./TODO.md) for the full phased build checklist, and [GLOSSARY.md](./GLOSSARY.md) for the project's vocabulary.

**MVP — the core loop:**

- [x] Project scaffolding, documentation, and domain model
- [ ] MediaRecorder audio capture + Whisper transcription
- [ ] Ollama structured processing pipeline
- [ ] JSON entry storage and CRUD API
- [ ] Minimal journal UI — sidebar list and entry detail

**After the MVP:**

- [ ] Search, tag filtering, and inline editing
- [ ] Mood & insights dashboard
- [ ] Export to Markdown / ZIP
- [ ] Re-process an entry from its stored transcript
- [ ] Semantic search with local embeddings
- [ ] Encryption at rest
- [ ] Installable desktop app packaging

**End-state product:**

The ideal product is a low-friction nightly reflection ritual: speaking and saving Entries comes first, the Author can meaningfully revisit past writing, and nothing undermines trust or shames them. Streaks may motivate but are never gamified.

- **Devices:** an installable desktop app holds the journal. Optional LAN capture is off by default; when enabled, phones use HTTPS with a locally generated certificate (trusted once per phone with in-app guidance) and a shared LAN password. Changing that password signs out every phone. Phones can record, review, and save Entries, but cannot browse the archive or capture offline.
- **Privacy:** Entries and the search index are encrypted at rest with a journal passphrase that is separate from the LAN password and cannot be recovered. A phone may enter the passphrase only to unlock saving for its current recording session and never stores it. Export requires unlocking and produces clearly labelled plaintext.
- **Reflection:** the model structures, connects, and reflects back, but never advises or diagnoses. Optional Prompts are saved with an Entry as context, never as part of its Transcript.
- **Weekly Reviews:** opt-in interpretations covering Monday–Sunday Journal Days. They are generated on the first unlock after a week ends, catch up missed weeks, skip weeks without Entries, become outdated when source Entries change, and are regenerated only after confirmation. They can be regenerated or deleted, but not edited, and do not affect Streaks.
- **Revisiting:** keyword, Tag, and local semantic search; descriptive insights for mood valence, frequent Tags, Streak, and Entry counts; and an optional neutral evening reminder that never mentions Streaks and is skipped after an Entry is saved for that Journal Day.
- **Export and extras:** JSON and Markdown exports include Entries, Prompts, and Weekly Reviews, with optional PDF or app-specific files derived locally from the same content. The opt-in desktop-only wake word runs locally with a visible listening indicator and never stores audio before the wake word. Local text-to-speech can read Summaries and Weekly Reviews on the desktop.

---

## Contributing

Issues and PRs welcome. Please open an issue before starting significant work. Keep pull requests focused on a single feature or fix.

Read [GLOSSARY.md](./GLOSSARY.md) before contributing — terms like *entry*, *draft*, *transcript*, and *journal day* have precise meanings here, and the code is expected to use them consistently. Decisions that would be surprising without context are recorded in [docs/adr/](./docs/adr/).

```bash
# Backend dev
uvicorn backend.main:app --reload

# Lint
pip install ruff && ruff check backend/
```

---

## License

MIT — free to use, modify, and distribute. No warranty implied.

---

> *"The act of writing is the act of discovering what you believe."* — Flannery O'Connor