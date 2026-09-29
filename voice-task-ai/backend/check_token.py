import os
import re
import httpx
from app.config import settings

t = settings.DISCORD_BOT_TOKEN

print("length:", len(t))
print("dots:", t.count("."))
print("odd characters:", [hex(ord(c)) for c in t if not re.match(r"[A-Za-z0-9._-]", c)] or "none")
print("Windows env var set:", "DISCORD_BOT_TOKEN" in os.environ)

r = httpx.get(
    "https://discord.com/api/v10/users/@me",
    headers={"Authorization": "Bot " + t},
    timeout=15,
)
print("Discord status:", r.status_code)