Converts informal, code-switched Pakistani voice notes — Urdu, Roman Urdu, Sindhi, Roman Sindhi, English, or any mix — into structured business actions: tasks, orders, payments, and reminders.

Speak or send a voice note. VoiceTask AI transcribes it, understands what you meant, and files it automatically — no typing required.

**Status:** Fully working end-to-end system, built during an AI Intern Developer internship at Sapphire Consulting (Aug – Sep 2026).

---

## 🎥 Demo

[https://drive.google.com/file/d/1HXrKap6vAn4Gpb5gDSU1BrIigpfBHLMd/view?usp=drive_link)

*Click the image above to watch the full demo — or paste your YouTube/Loom link directly here.*
# VoiceTask AI

Turns informal voice notes — Urdu, Roman Urdu, or English — into structured
business records. A user sends a voice message (or a typed message) on
Discord, and the backend transcribes it, works out what it means, and
automatically creates a **Task**, **Order**, or **Payment**. Low-confidence
notes are held for manual review instead of being guessed at.

## How it works

```
Voice note (or a typed message)
      │
      ▼
1. Ingest        – validate + save the audio file
2. Transcribe     – speech to text (Gemini)
3. Extract        – astructured data from the transcript (Gemini)
4. Decide         – auto-create, or send for review, based on confidence
5. Create record  – Task / Order / Payment, saved to Postgres
6. Reply          – the result is sent back on Discord
```

A typed message skips steps 1–2 and is extracted directly.

## Features

- **Discord bot** — the input channel. Connects out to Discord, so no
  public URL or tunnel is needed.
  - **Voice message or audio file**, in any channel the bot can see →
    transcribed and processed automatically.
  - **Typed text** → processed only when the bot is **@mentioned**, or
    sent as a **DM**, so ordinary channel chat isn't turned into tasks.
- **Google Sheets** — every order created is automatically logged to a
  spreadsheet.
- **Google Calendar** — confirming a meeting or appointment with a
  specific date and time automatically creates a real calendar event,
  with a generated Jitsi video call link.
- **Email broadcast** — whenever a voice note is transcribed, the audio
  and transcript (plus English/Urdu translations) are emailed to a group
  member list, so people don't have to listen to the original clip.

## Tech stack

- **API:** FastAPI (Python)
- **Database:** PostgreSQL, via SQLAlchemy + Alembic migrations
- **AI:** Google Gemini — transcription, extraction, and translation
- **Discord:** discord.py

## Project structure

```
backend/
├── app/
│   ├── main.py               FastAPI app, routes, Discord bot startup
│   ├── config.py             All settings (reads from .env)
│   ├── api/                  HTTP endpoints, one file per resource
│   ├── services/
│   │   └── discord_bot.py    The Discord bot
│   ├── ai/                   Gemini calls, prompts
│   ├── models/                SQLAlchemy models
│   ├── schemas/               Pydantic request/response shapes
│   ├── integrations/          Google Sheets, Calendar, Jitsi, email
│   └── utils/                  Small helpers (date/currency/language parsing)
├── alembic/                  Database migrations
├── tests/                    Pytest test suite
├── requirements.txt
└── .env                      Your local secrets (not committed)
```

## Setup

### 1. Prerequisites

- Python 3.11+
- PostgreSQL, running locally or reachable over the network
- A free [Gemini API key](https://aistudio.google.com/apikey)

### 2. Install

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Configure

Copy `.env.example` to `.env` and fill in at least:

```
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/voicetask_ai
GEMINI_API_KEY=your-key-here
```

Google Sheets, Google Calendar, and the email broadcast are each optional
— every one stays off until its own settings below are filled in.

### 4. Set up the database

```bash
alembic upgrade head
```

### 5. Run

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8081
```

- API root: `http://localhost:8081/`
- Health check: `http://localhost:8081/api/health`
- Interactive API docs: `http://localhost:8081/docs`

## Discord setup

1. Go to [discord.com/developers/applications](https://discord.com/developers/applications) → **New Application**.
2. **Bot** tab → **Reset Token** → copy it.
3. Same tab → turn on **Message Content Intent**.
4. **OAuth2 → URL Generator** → scope `bot` → permissions `Send Messages`, `Attach Files`, `View Channels`, `Read Message History` → open the generated URL and add the bot to a server.
5. In `.env`:
   ```
   DISCORD_BOT_TOKEN=your-token-here
   ```
6. Restart the server. You should see `[discord_bot] Logged in as ...`.

## Google Sheets setup (optional)

Uses a simple Google Apps Script Web App as a webhook — no OAuth flow or
service account needed.

1. Create a Google Sheet, then **Extensions → Apps Script**, and deploy a
   script that appends a row on each `doPost` request.
2. In `.env`:
   ```
   GOOGLE_SHEETS_WEBHOOK_URL=https://script.google.com/macros/s/.../exec
   ```

## Google Calendar setup (optional)

Same approach — an Apps Script Web App that creates a calendar event.

1. Deploy a script whose `doPost(e)` reads `title`, `start_datetime`, and
   `duration_minutes` from the request body and calls
   `CalendarApp.getDefaultCalendar().createEvent(...)`.
2. In `.env`:
   ```
   GOOGLE_CALENDAR_WEBHOOK_URL=https://script.google.com/macros/s/.../exec
   MEETING_DEFAULT_DURATION_MINUTES=60
   ```

## Email broadcast setup (optional)

Uses plain SMTP — works with Gmail (with an App Password), Outlook, or
any other provider.

```
GROUP_BROADCAST_ENABLED=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=you@example.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=you@example.com
GROUP_MEMBER_EMAILS=person1@example.com,person2@example.com
```

## Testing

```bash
pytest
```

## Troubleshooting

- **`ModuleNotFoundError`:** the virtual environment isn't active, or `pip install -r requirements.txt` hasn't been run in it.
- **Discord bot won't log in:** double check the token was copied from the **Bot** tab (not OAuth2), and that no old value is set as a Windows environment variable of the same name, which would override `.env`.
- **Google Sheets/Calendar silently does nothing:** check the server logs for a `[google_sheets]` or `[google_calendar]` line — both print the response status from the Apps Script webhook, and skip silently (by design) if their URL isn't configured.

## Security note

Never commit `.env`. If any token or webhook URL has been shared, pasted
into a chat, or otherwise exposed, reset it at the source (Discord's
Developer Portal, Google's Apps Script deployment, etc.) before using it
in production.

- **Google Calendar demo:** [https://calendar.google.com/calendar/u/0?cid=aDQxMjQxMjMxMkBnbWFpbC5jb20]
- **Google Sheets (Orders) demo:** [https://docs.google.com/spreadsheets/d/e/2PACX-1vQSbgqrO6wzKTtS-JHbDDdixhzDb9dWAbVh2mnrUyNURgUTMCguVx1riEfJUmwABnJ1ofKilikfGEn7/pubhtml]
- **Sample Jitsi meeting:** https://meet.jit.si/VoiceTaskAI-Meeting-with-Ali-a7565c38


## 👤 Author

**Muhammad Muzzamil**
AI Intern Developer — Sapphire Consulting
[LinkedIn](https://www.linkedin.com/in/muzzamil-zafar-719711295) · muzzamilzafar111@gmail.com

