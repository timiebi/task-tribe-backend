"""Resolve per-request local dates using the client's IANA timezone header."""

from datetime import date

from django.conf import settings
from django.utils import timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

MAX_TIMEZONE_HEADER_LEN = 80


def resolve_request_timezone_context(request) -> dict:
    """Build timezone metadata for debugging and date-boundary logic.

    Reads ``X-Timezone`` (e.g. ``Africa/Lagos``, ``Europe/Paris``). Falls back to
    Django's configured ``TIME_ZONE`` when the header is missing or invalid.
    """
    requested = (request.headers.get("X-Timezone") or "").strip()
    server_tz = settings.TIME_ZONE
    source = "server_default"
    effective = server_tz

    if requested and len(requested) <= MAX_TIMEZONE_HEADER_LEN:
        try:
            tz = ZoneInfo(requested)
            effective = requested
            source = "client"
            today = timezone.localdate(timezone=tz)
            now = timezone.now().astimezone(tz)
        except ZoneInfoNotFoundError:
            source = "invalid_fallback"
            today = timezone.localdate()
            now = timezone.now()
    else:
        if requested:
            source = "invalid_fallback"
        today = timezone.localdate()
        now = timezone.now()

    return {
        "requested_timezone": requested or None,
        "effective_timezone": effective,
        "source": source,
        "today": today.isoformat(),
        "now": now.isoformat(),
        "server_timezone": server_tz,
        "header_valid": source == "client",
    }


def request_localdate(request) -> date:
    """Today's calendar date in the client's timezone when possible."""
    ctx = resolve_request_timezone_context(request)
    return date.fromisoformat(ctx["today"])
