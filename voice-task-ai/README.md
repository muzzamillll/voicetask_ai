# VoiceTask AI

Converts informal Pakistani voice notes (Urdu, Roman Urdu, Sindhi, Roman Sindhi,
English, and code-switched mixes) into structured business actions — tasks,
orders, payments, and reminders — via Whisper transcription and LLM-based
intent extraction.

## Status

**Phase 1 — Project Setup** ✅ (this commit)

Pipeline (implemented incrementally):

```
Voice Note → Whisper → Transcript Cleaning → Language Detection
→ LLM Extraction → Pydantic Validation → User Review → Database → Dashboard
```

## Stack

- **Backend:** Python 3.11+, FastAPI, Pydantic, SQLAlchemy, PostgreSQL, Alembic
- **AI:** Whisper (speech-to-text) + LLM (structured extraction)
- **Frontend:** React, Vite, Tailwind CSS, Axios, React Router

## Project structure

```
voice-task-ai/
  backend/
    app/
      main.py            # FastAPI entrypoint
      config.py           # Env-driven settings
      api/                # Route handlers (voice_notes, tasks, orders, ...)
      ai/                 # Whisper + LLM extraction services
      models/             # SQLAlchemy models
      schemas/            # Pydantic schemas
      services/           # Business logic
      integrations/       # Google Calendar / Sheets / Trello
      database/           # DB engine + session
      utils/              # date/currency/language parsers
    tests/
    requirements.txt
    .env.example
  frontend/
    src/
      components/
      pages/
      services/api.js
      App.jsx
  data/audio/             # uploaded voice notes (gitignored)
```

## Running locally

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # then fill in DATABASE_URL / OPENAI_API_KEY
uvicorn app.main:app --reload --port 8000
```

Verify: open http://localhost:8000/api/health → `{"status": "ok"}`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Verify: open http://localhost:5173 → the page should show
**Backend status: ok** once the API is running.

### Database (Phase 2+)

You'll need a local PostgreSQL instance. Create the database referenced in
`DATABASE_URL`:

```bash
createdb voicetask_ai
```

Alembic migrations are introduced in Phase 2.

## Roadmap

1. ✅ Project setup (this phase)
2. Database models + migrations
3. Voice note upload endpoint
4. Whisper transcription
5. Transcript cleaning + language detection
6. LLM structured extraction
7. Confidence scoring + review UI
8. Tasks CRUD
9. Dashboard UI
10. Orders & payments
11. Analytics
12. Google Calendar / Sheets / Trello integrations
