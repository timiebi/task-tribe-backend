import json
import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def _vapid_configured() -> bool:
    return bool(settings.VAPID_PRIVATE_KEY and settings.VAPID_PUBLIC_KEY)


def send_to_subscription(subscription, payload: dict) -> bool:
    """Send a single push. Returns True on success.

    Deletes the subscription on 404/410 (browser revoked it).
    """
    if not _vapid_configured():
        return False

    try:
        from pywebpush import WebPushException, webpush
    except ImportError:
        logger.warning("pywebpush is not installed; skipping push")
        return False

    try:
        webpush(
            subscription_info={
                "endpoint": subscription.endpoint,
                "keys": {
                    "p256dh": subscription.p256dh,
                    "auth": subscription.auth,
                },
            },
            data=json.dumps(payload),
            vapid_private_key=settings.VAPID_PRIVATE_KEY,
            vapid_claims={"sub": settings.VAPID_SUBJECT},
        )
        return True
    except WebPushException as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        if status in (404, 410):
            subscription.delete()
        else:
            logger.warning("Web push failed (%s): %s", status, exc)
        return False
    except Exception as exc:  # network failure, etc.
        logger.warning("Web push error: %s", exc)
        return False


def push_to_user(user, payload: dict) -> int:
    """Send the same payload to every subscription a user has.

    Returns the number of successful deliveries. Safe to call from anywhere;
    silently no-ops if VAPID isn't configured.
    """
    from .models import PushSubscription

    if not _vapid_configured():
        return 0

    sent = 0
    subs = list(PushSubscription.objects.filter(user=user))
    for sub in subs:
        if send_to_subscription(sub, payload):
            sent += 1
    return sent


def build_payload(
    *,
    title: str,
    body: str = "",
    url: str = "/",
    tag: str | None = None,
    data: dict | None = None,
) -> dict:
    payload = {
        "title": title,
        "body": body,
        "url": url,
    }
    if tag:
        payload["tag"] = tag
    if data:
        payload["data"] = data
    return payload
