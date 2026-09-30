Converts informal, code-switched Pakistani voice notes — Urdu, Roman Urdu, Sindhi, Roman Sindhi, English, or any mix — into structured business actions: tasks, orders, payments, and reminders.

Speak or send a voice note. VoiceTask AI transcribes it, understands what you meant, and files it automatically — no typing required.

**Status:** Fully working end-to-end system, built during an AI Intern Developer internship at Sapphire Consulting (Aug – Sep 2026).

---

## 🎥 Demo

[https://drive.google.com/file/d/1HXrKap6vAn4Gpb5gDSU1BrIigpfBHLMd/view?usp=drive_link)

*Click the image above to watch the full demo — or paste your YouTube/Loom link directly here.*

---

## ✨ Features

- **Multilingual transcription** — Whisper handles Urdu, Roman Urdu, Sindhi, Roman Sindhi, English, and code-switched speech.
- **AI intent extraction** — Google's Gemini API pulls structured intent, contact, deadline, amount, and priority from casual speech.
- **Confidence-based automation** — auto-creates high-confidence results, asks for confirmation on medium-confidence ones, and requires manual review below 0.60.
- **Multi-channel input** — submit voice notes via the web dashboard or directly through a Discord bot.
- **Gmail notifications** — the cleaned transcript is emailed automatically as soon as a voice note is processed.
- **Google Calendar sync** — meeting intents become calendar events with an auto-generated Jitsi video link.
- **Google Sheets sync** — confirmed orders are pushed to a live spreadsheet, no manual entry.
- **Pakistani currency & date normalization** — understands phrasing like *"25 hazar"*, *"2 lakh"*, *"kal"*, *"5 baje"* and resolves them correctly.

---

## 🛠️ Tech Stack

**Backend:** Python 3.11+, FastAPI, Pydantic, SQLAlchemy, PostgreSQL, Alembic, Uvicorn
**AI:** Whisper (speech-to-text), Gemini API (intent extraction), Pydantic (output validation)
**Frontend:** React, Vite, Tailwind CSS, Axios, React Router
**Integrations:** Discord bot, Gmail, Google Calendar, Google Sheets, Jitsi

---

## 🔄 How It Works

```
Voice Note (Dashboard or Discord)
        │
        ▼
  Whisper (Speech-to-Text)
        │
        ▼
  Transcript Cleaning
        │
        ▼
  Language Detection
        │
        ▼
  Gmail Notification
        │
        ▼
  Gemini AI Intent Extraction
        │
        ▼
  Pydantic Validation
        │
        ▼
  Confidence Check ──► User Review (if needed)
        │
        ▼
  Task / Order / Payment / Reminder
        │
        ▼
  Dashboard + Google Sheets / Google Calendar (Jitsi link)
```

---

## 📸 Screenshots

| Dashboard | Tasks |
|---|---|
| ![Dashboard](docs/screenshots/dashboard.png) | ![Tasks](docs/screenshots/tasks.png) |

| Discord Bot | Google Calendar |
|---|---|
| ![Discord](docs/screenshots/discord.png) | ![Calendar](docs/screenshots/calendar.png) |

> Add your screenshot files to a `docs/screenshots/` folder in the repo with these names (or update the paths above) so they render here.

---

## 🚀 Getting Started

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
cp .env.example .env         # then fill in your API keys
alembic upgrade head
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Environment Variables

Copy `backend/.env.example` to `backend/.env` and fill in:

```
GEMINI_API_KEY=
DATABASE_URL=
SECRET_KEY=
DISCORD_BOT_TOKEN=
GMAIL_ADDRESS=
GOOGLE_CALENDAR_CREDENTIALS=
GOOGLE_SHEETS_CREDENTIALS=
```

---

## 📡 Key API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/voice-notes/upload` | Upload a voice note |
| POST | `/api/voice-notes/process/{id}` | Run the AI pipeline on a voice note |
| GET | `/api/tasks` | List all tasks |
| POST | `/api/tasks/{id}/complete` | Mark a task complete |
| GET | `/api/orders` | List all orders |
| GET | `/api/payments` | List all payments |
| GET | `/api/analytics/summary` | Dashboard statistics |

Full endpoint list in the [project report](#).

---

## 🔗 Live Links

- **Google Calendar demo:** [https://calendar.google.com/calendar/u/0/r/week/2026/11/15]
- **Google Sheets (Orders) demo:** [https://docs.google.com/spreadsheets/d/1RdE6gEUPyFX76u4ldSGJFDswHxRqge-lQzFS7RJ9HZc/edit?gid=0#gid=0]
- **Sample Jitsi meeting:** https://meet.jit.si/VoiceTaskAI-Database-Project-Meeting-6813a8d3

---

## 👤 Author

**Muhammad Muzzamil**
AI Intern Developer — Sapphire Consulting
[LinkedIn](https://www.linkedin.com/in/muzzamil-zafar-719711295) · muzzamilzafar111@gmail.com
