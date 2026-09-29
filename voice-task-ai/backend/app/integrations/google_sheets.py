"""
Google Sheets integration.

Uses a simple Apps Script Web App as a webhook instead of the full
Google Sheets API — this avoids needing OAuth consent flows, service
account credentials, or any new heavy Python dependencies (just httpx,
already a project dependency). The Apps Script itself lives in the
user's Google Sheet and handles the actual SpreadsheetApp.appendRow call.

If GOOGLE_SHEETS_WEBHOOK_URL isn't configured, this integration is
silently skipped — it's optional, not required for the app to function.
"""
import httpx

from app.config import settings


def is_configured() -> bool:
    return bool(settings.GOOGLE_SHEETS_WEBHOOK_URL)


def append_order_row(order) -> None:
    """
    Sends one Order record to the configured Google Sheet.
    Never raises — a Sheets failure should never break saving the order
    to the real database, which already succeeded by the time this runs.
    """
    if not is_configured():
        print("[google_sheets] Skipped — GOOGLE_SHEETS_WEBHOOK_URL is not set.")
        return

    payload = {
        "order_id": order.id,
        "customer": order.customer_name or "",
        "description": order.description or "",
        "quantity": order.quantity,
        "amount": order.amount,
        "currency": order.currency,
        "delivery_date": order.delivery_date.isoformat() if order.delivery_date else "",
        "status": order.status.value,
        "created_at": order.created_at.isoformat(),
    }

    try:
        response = httpx.post(settings.GOOGLE_SHEETS_WEBHOOK_URL, json=payload, timeout=10.0)
        print(f"[google_sheets] POST to webhook -> status {response.status_code}")
        print(f"[google_sheets] Response body: {response.text[:300]}")
    except httpx.HTTPError as exc:
        print(f"[google_sheets] Request failed: {exc}")
