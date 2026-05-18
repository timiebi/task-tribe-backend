from django.conf import settings
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import AppNotification, Event, PushSubscription, Task
from .push import build_payload, push_to_user


@api_view(["GET"])
@permission_classes([AllowAny])
def public_key(request):
    if not settings.VAPID_PUBLIC_KEY:
        return Response(
            {"detail": "Push notifications aren't configured on the server yet."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    return Response({"public_key": settings.VAPID_PUBLIC_KEY})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def subscribe(request):
    data = request.data or {}
    endpoint = data.get("endpoint")
    keys = data.get("keys") or {}
    p256dh = keys.get("p256dh")
    auth = keys.get("auth")
    user_agent = (data.get("user_agent") or request.META.get("HTTP_USER_AGENT", ""))[:300]

    if not (endpoint and p256dh and auth):
        return Response(
            {"detail": "Your browser didn't provide a complete subscription."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    sub, _ = PushSubscription.objects.update_or_create(
        endpoint=endpoint,
        defaults={
            "user": request.user,
            "p256dh": p256dh,
            "auth": auth,
            "user_agent": user_agent,
        },
    )
    return Response({"id": sub.id, "endpoint": sub.endpoint})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def unsubscribe(request):
    endpoint = (request.data or {}).get("endpoint")
    if not endpoint:
        return Response(
            {"detail": "Please provide a subscription endpoint."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    PushSubscription.objects.filter(user=request.user, endpoint=endpoint).delete()
    return Response({"detail": "Unsubscribed."})


def _frontend_url(path: str) -> str:
    base = settings.APP_FRONTEND_URL.rstrip("/")
    return f"{base}{path}" if path.startswith("/") else f"{base}/{path}"


def send_due_reminders() -> dict:
    """Send pushes for due tasks/events and mark them.

    Idempotent: only fires for items that are due and not yet marked.
    Returns a small summary dict for logging/HTTP response.
    """
    now = timezone.now()
    task_sent = 0
    event_sent = 0

    due_tasks = Task.objects.select_related("user").filter(
        remind_at__lte=now,
        reminded=False,
        completed=False,
    )
    for task in due_tasks:
        payload = build_payload(
            title=task.title or "Task reminder",
            body=task.description or "This task is due now.",
            url=_frontend_url("/?tab=tasks"),
            tag=f"task-{task.id}",
            data={"kind": "task", "id": task.id},
        )
        push_to_user(task.user, payload)
        task.reminded = True
        task.save(update_fields=["reminded", "updated_at"])
        task_sent += 1

    due_events = Event.objects.select_related("user").filter(
        remind_at__lte=now,
        notified=False,
    )
    for event in due_events:
        payload = build_payload(
            title=event.title or "Reminder",
            body=event.description or f"Starts {event.starts_at.isoformat()}",
            url=_frontend_url("/?tab=events"),
            tag=f"event-{event.id}",
            data={"kind": "event", "id": event.id},
        )
        push_to_user(event.user, payload)
        event.notified = True
        event.save(update_fields=["notified"])
        event_sent += 1

    return {"tasks": task_sent, "events": event_sent}


@api_view(["POST"])
@permission_classes([AllowAny])
def run_due_reminders(request):
    secret = settings.CRON_SECRET
    if not secret:
        return Response(
            {"detail": "Cron secret isn't configured."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    provided = request.headers.get("X-Cron-Secret") or request.GET.get("secret", "")
    if provided != secret:
        return Response(
            {"detail": "Not authorized."},
            status=status.HTTP_401_UNAUTHORIZED,
        )
    result = send_due_reminders()
    return Response({"status": "ok", **result})


__all__ = [
    "public_key",
    "subscribe",
    "unsubscribe",
    "run_due_reminders",
    "send_due_reminders",
]
