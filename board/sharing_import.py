"""Copy a shared item snapshot into the recipient's own workspace."""

from django.utils import timezone

from .models import Event, Note, Plan, SharedItem, Task


def _attribution(shared: SharedItem) -> str:
    lines = [f"Shared by {shared.shared_by.username}"]
    if shared.message:
        lines.append(shared.message)
    return "\n".join(lines)


def _append_attribution(text: str, shared: SharedItem) -> str:
    note = _attribution(shared)
    base = (text or "").strip()
    if not base:
        return note
    return f"{base}\n\n---\n{note}"


def import_shared_item(user, shared: SharedItem, target_type: str):
    """Create a new owned item for ``user`` from a ``SharedItem`` snapshot."""
    if shared.shared_with_id != user.id:
        raise PermissionError("Not your shared item.")

    p = shared.payload or {}
    target = target_type

    if target == SharedItem.ITEM_TASK:
        return Task.objects.create(
            user=user,
            title=(p.get("title") or "Shared task")[:300],
            description=_append_attribution(p.get("description") or "", shared),
            due_date=p.get("due_date"),
            priority=p.get("priority") or "medium",
            status="todo",
            is_daily=bool(p.get("is_daily")),
            completed=False,
            remind_at=None,
            reminded=False,
        )

    if target == SharedItem.ITEM_NOTE:
        return Note.objects.create(
            user=user,
            notebook=None,
            title=(p.get("title") or "Shared note")[:300],
            content=_append_attribution(p.get("content") or "", shared),
            is_pinned=bool(p.get("is_pinned")),
        )

    if target == SharedItem.ITEM_PLAN:
        return Plan.objects.create(
            user=user,
            title=(p.get("title") or "Shared plan")[:300],
            content=_append_attribution(p.get("content") or "", shared),
            start_date=p.get("start_date"),
            end_date=p.get("end_date"),
            status=p.get("status") or "active",
        )

    if target == SharedItem.ITEM_EVENT:
        starts = p.get("starts_at") or timezone.now().isoformat()
        return Event.objects.create(
            user=user,
            title=(p.get("title") or "Shared reminder")[:300],
            description=_append_attribution(p.get("description") or "", shared),
            starts_at=starts,
            remind_at=p.get("remind_at"),
            notified=False,
        )

    raise ValueError(f"Unsupported target type: {target_type}")
