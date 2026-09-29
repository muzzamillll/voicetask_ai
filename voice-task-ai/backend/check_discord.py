import base64
import httpx
from app.config import settings

t = settings.DISCORD_BOT_TOKEN
parts = t.split(".")

print("length:", len(t))
print("dot-separated parts:", len(parts))

try:
    first = parts[0] + "=" * (-len(parts[0]) % 4)
    print("first part is a numeric id:", base64.b64decode(first).decode().isdigit())
except Exception:
    print("first part is a numeric id: False")

r = httpx.get(
    "https://discord.com/api/v10/users/@me",
    headers={"Authorization": f"Bot {t}"},
    timeout=15,
)
print("Discord answered:", r.status_code)