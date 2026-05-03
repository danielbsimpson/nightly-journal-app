# Voice Journal

A local-first journaling app that turns your spoken thoughts into structured, searchable journal entries. Press record, speak freely, and let Whisper transcribe and Ollama summarize, tag, and organize everything — entirely on your own machine.

```
Microphone → Whisper (STT) → Ollama (LLM) → Structured Journal Entry → Local Storage
```

No cloud. No subscriptions. Your thoughts stay yours.

---

## What It Does

1. **Record** — hit the mic button and speak your thoughts, unfiltered
2. **Transcribe** — faster-whisper converts your speech to text locally on your GPU
3. **Process** — Ollama reads the transcript and generates:
   - A clean, readable **summary**
   - A meaningful **title**
   - A **mood / tone** label (reflective, anxious, grateful, excited…)
   - **Topic tags** (work, health, relationships, goals…)
   - Any **action items** you mentioned
4. **Save** — the entry is saved as a JSON file in your local `journals/` folder
5. **Review** — browse, search, filter, and edit past entries in the UI
6. **Insights** — visualize mood trends, streaks, and frequent topics over time

---

## Features

- 🎙 **Local speech-to-text** via faster-whisper (no audio ever leaves your machine)
- 🧠 **LLM-powered journaling** via Ollama — summarize, title, tag, and detect mood
- 📓 **Clean journal UI** with sidebar navigation, search, and tag filtering
- 📊 **Insights dashboard** — mood over time, tag cloud, and entry streaks
- 💾 **Plain JSON storage** — no database, entries are readable files you own
- 📤 **Export to Markdown, JSON, or ZIP** for backup or import into Obsidian/Notion
- 🔒 **Fully offline** — everything runs on localhost

---

## Requirements

- **OS:** Linux, macOS, or Windows (WSL2 recommended)
- **GPU:** NVIDIA GPU with 4 GB+ VRAM (CUDA 11.8+), or Apple Silicon (Metal)
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
│   └── models.py           # Pydantic schemas
├── journals/               # Your entries live here (gitignored)
│   └── .gitkeep
├── scripts/
│   └── setup.sh
├── .env.example
├── requirements.txt
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
uvicorn backend.main:app --reload --port 8000
```

### 5. Open the frontend

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
WHISPER_DEVICE=cuda         # cuda | cpu | auto
WHISPER_LANGUAGE=en         # or leave blank for auto-detect

# Storage
JOURNALS_DIR=./journals

# Backend
BACKEND_PORT=8000
CORS_ORIGIN=http://localhost:3000
```

---

## API Reference

| Endpoint | Method | Description |
|---|---|---|
| `/transcribe` | POST | Upload audio blob → returns raw transcript |
| `/process` | POST | Send transcript → returns structured entry JSON (streaming) |
| `/entries` | GET | List all entries (metadata only) |
| `/entries/{id}` | GET | Get full entry by ID |
| `/entries/{id}` | PATCH | Edit title or summary |
| `/entries/{id}` | DELETE | Delete an entry |
| `/insights` | GET | Aggregated mood, tag, and streak data |
| `/export` | GET | Download all entries as ZIP |
| `/health` | GET | Check backend + Ollama status |

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
  "title": "A Tough Day Redeemed by an Evening Run",
  "summary": "Work felt overwhelming with self-doubt...",
  "raw_transcript": "Today was really tough at work, I kept second-guessing...",
  "mood": "reflective",
  "tags": ["work", "mental health", "exercise", "productivity"],
  "action_items": ["Block focus time tomorrow morning"],
  "audio_duration_seconds": 47
}
```

Files are named `YYYY-MM-DD_slugified-title.json` for easy browsing in your filesystem.

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

Transcript: "..."
```

Adjust the mood vocabulary and tag style in `.env` or directly in `backend/llm.py`.

---

## Troubleshooting

**Whisper is slow / using CPU instead of GPU**
Confirm CUDA is available: `python -c "import torch; print(torch.cuda.is_available())"`. If False, reinstall PyTorch with the correct CUDA version for your system.

**Ollama returns malformed JSON**
Try a larger model — smaller models (e.g. `phi3:mini`) sometimes don't follow JSON instructions reliably. `llama3:8b` and `mistral:7b` are well-tested for structured output.

**Mic not working in the browser**
Browsers require HTTPS or `localhost` for microphone access. Accessing via an IP address (e.g. `192.168.x.x`) will be blocked. Use `localhost:8000` directly.

**Audio blob is empty or too short**
The app requires at least 2 seconds of audio. Very short clips may produce empty Whisper transcripts. Check the browser console for `MediaRecorder` errors.

**`journals/` directory not found**
The backend creates this on startup automatically. If running the frontend standalone without the backend, create it manually: `mkdir journals`.

---

## Roadmap

See [TODO.md](./TODO.md) for the full phased build checklist.

- [x] Project scaffolding and documentation
- [ ] MediaRecorder audio capture + Whisper transcription
- [ ] Ollama structured processing pipeline
- [ ] JSON entry storage and CRUD API
- [ ] Frontend journal UI with sidebar and detail view
- [ ] Mood & insights dashboard
- [ ] Export to Markdown / ZIP
- [ ] Semantic search with local embeddings
- [ ] Electron desktop app packaging

---

## Contributing

Issues and PRs welcome. Please open an issue before starting significant work. Keep pull requests focused on a single feature or fix.

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