"""
Central application configuration.
Loads settings from environment variables (via .env in local dev).
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # --- App ---
    APP_NAME: str = "VoiceTask AI"
    ENV: str = os.getenv("ENV", "development")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me-in-production")

    # --- Database ---
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://postgres:postgres@localhost:5432/voicetask_ai",
    )

    # --- AI / OpenAI ---
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    # --- Gemini (transcription + LLM extraction) ---
    # Free API key from https://aistudio.google.com/apikey
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")

    # --- Google Sheets (optional) ---
    # Apps Script Web App URL — leave blank to disable this integration.
    GOOGLE_SHEETS_WEBHOOK_URL: str = os.getenv("GOOGLE_SHEETS_WEBHOOK_URL", "")

    # --- Telegram bot automation (optional) ---
    # Free bot token from @BotFather on Telegram. When set (and
    # TELEGRAM_POLL_ENABLED=true), the app automatically polls Telegram
    # for incoming voice messages, ingests them as VoiceNotes, and
    # transcribes them — no manual upload needed.
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_POLL_ENABLED: bool = os.getenv("TELEGRAM_POLL_ENABLED", "false").lower() == "true"

    # --- Google Calendar (optional) ---
    # Apps Script Web App URL — leave blank to disable this integration.
    # When set, confirming a "meeting" or "appointment" intent with a
    # specific date+time automatically creates a real calendar event.
    GOOGLE_CALENDAR_WEBHOOK_URL: str = os.getenv("GOOGLE_CALENDAR_WEBHOOK_URL", "")
    MEETING_DEFAULT_DURATION_MINUTES: int = int(os.getenv("MEETING_DEFAULT_DURATION_MINUTES", "60"))

    # --- Slack voice-message automation (optional) ---
    # Slack app credentials from Basic Information / OAuth & Permissions.
    SLACK_ENABLED: bool = os.getenv("SLACK_ENABLED", "false").lower() == "true"
    SLACK_BOT_TOKEN: str = os.getenv("SLACK_BOT_TOKEN", "")
    SLACK_SIGNING_SECRET: str = os.getenv("SLACK_SIGNING_SECRET", "")
    SLACK_MAX_EVENT_AGE_SECONDS: int = int(os.getenv("SLACK_MAX_EVENT_AGE_SECONDS", "300"))

    # --- WhatsApp Cloud API (optional) ---
    # From Meta for Developers -> your app -> WhatsApp. See .env.example.
    WHATSAPP_ENABLED: bool = os.getenv("WHATSAPP_ENABLED", "false").lower() == "true"
    WHATSAPP_ACCESS_TOKEN: str = os.getenv("WHATSAPP_ACCESS_TOKEN", "").strip()
    WHATSAPP_PHONE_NUMBER_ID: str = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "").strip()
    WHATSAPP_VERIFY_TOKEN: str = os.getenv("WHATSAPP_VERIFY_TOKEN", "").strip()
    WHATSAPP_APP_SECRET: str = os.getenv("WHATSAPP_APP_SECRET", "").strip()
    WHATSAPP_GRAPH_VERSION: str = os.getenv("WHATSAPP_GRAPH_VERSION", "v24.0").strip()

    # --- Discord bot (optional) ---
    # discord.com/developers/applications -> your app -> Bot -> Reset Token.
    # Needs the "Message Content Intent" toggle turned on in the same tab.
    DISCORD_BOT_TOKEN: str = os.getenv("DISCORD_BOT_TOKEN", "").strip()

    # --- Microsoft Teams bot (optional) ---
    # From an Azure Bot resource's Configuration page. Leave blank to
    # disable — the webhook endpoint will reject requests if unset.
    MICROSOFT_APP_ID: str = os.getenv("MICROSOFT_APP_ID", "")
    MICROSOFT_APP_PASSWORD: str = os.getenv("MICROSOFT_APP_PASSWORD", "")

    # --- Group email broadcast (optional) ---
    # Whenever a voice note is transcribed, email the audio + transcript
    # to every address in GROUP_MEMBER_EMAILS. Uses plain SMTP — works
    # with Gmail (with an App Password), Outlook, or any SMTP provider.
    GROUP_BROADCAST_ENABLED: bool = os.getenv("GROUP_BROADCAST_ENABLED", "false").lower() == "true"
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM_EMAIL: str = os.getenv("SMTP_FROM_EMAIL", "")
    GROUP_MEMBER_EMAILS: str = os.getenv("GROUP_MEMBER_EMAILS", "")  # comma-separated

    # --- LINE Messaging API (optional) ---
    # From the LINE Developers Console (console.line.biz) — a Messaging
    # API channel's "Channel secret" and "Channel access token".
    LINE_CHANNEL_SECRET: str = os.getenv("LINE_CHANNEL_SECRET", "")
    LINE_CHANNEL_ACCESS_TOKEN: str = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")

    # --- Uploads ---
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "../data/audio")
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "25"))
    ALLOWED_AUDIO_EXTENSIONS: set = {".mp3", ".wav", ".m4a", ".webm", ".ogg", ".opus", ".oga", ".aac"}

    # --- CORS ---
    FRONTEND_ORIGIN: str = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")


settings = Settings()
