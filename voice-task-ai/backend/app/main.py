"""
VoiceTask AI — FastAPI entrypoint.

Phase 3: voice notes. Phase 8: tasks, orders, payments.
Channels: Slack, LINE, Teams and WhatsApp arrive as webhooks. The Discord bot
connects out over a websocket and is started in the lifespan below - no public
URL or ngrok is needed for it.
"""
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api import voice_notes, tasks, orders, payments, contacts, teams_webhook, analytics, line_webhook, slack_webhook

# Optional channels: if the file or its package isn't installed yet, the server
# still starts and just skips that channel (with a message) instead of crashing.
try:
    from app.api import whatsapp_webhook
except ImportError as exc:
    whatsapp_webhook = None
    print(f"[main] WhatsApp disabled (not installed): {exc}")

try:
    from app.services.discord_bot import run_discord_bot
except ImportError as exc:
    run_discord_bot = None
    print(f"[main] Discord disabled (run: pip install -r requirements.txt): {exc}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    discord_task = None

    if settings.DISCORD_BOT_TOKEN and run_discord_bot:
        discord_task = asyncio.create_task(run_discord_bot())

    yield

    if discord_task:
        discord_task.cancel()


app = FastAPI(
    title=settings.APP_NAME,
    description="Converts informal Pakistani voice notes into structured business actions.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(voice_notes.router)
app.include_router(tasks.router)
app.include_router(orders.router)
app.include_router(payments.router)
app.include_router(contacts.router)
app.include_router(teams_webhook.router)
app.include_router(analytics.router)
app.include_router(line_webhook.router)
app.include_router(slack_webhook.router)

if whatsapp_webhook:
    app.include_router(whatsapp_webhook.router)


@app.get("/")
def root():
    return {"service": settings.APP_NAME, "status": "running", "env": settings.ENV}


@app.get("/api/health")
def health_check():
    """Basic liveness check. Phase 2 will extend this to check DB connectivity."""
    return {"status": "ok"}
