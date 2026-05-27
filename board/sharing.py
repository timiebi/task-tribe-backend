from django.contrib.auth.models import User
from django.db.models import Q
from rest_framework.exceptions import PermissionDenied, ValidationError

from .models import (
    AppNotification,
    Event,
    Note,
    Plan,
    SharedItem,
    SpaceConnection,
    Task,
)


def normalize_email(email: str) -> str:
    return email.strip().lower()


def users_are_connected(user_a: User, user_b: User) -> bool:
    if user_a.id == user_b.id:
        return False
    return SpaceConnection.objects.filter(
        status=SpaceConnection.STATUS_ACCEPTED,
    ).filter(
        Q(from_user=user_a, to_user=user_b) | Q(from_user=user_b, to_user=user_a)
    ).exists()


def create_app_notification(
    *,
    recipient: User,
    kind: str,
    title: str,
    body: str = "",
    payload: dict | None = None,
) -> AppNotification:
    notification = AppNotification.objects.create(
        recipient=recipient,
        kind=kind,
        title=title,
        body=body,
        payload=payload or {},
    )

    try:
        from .push import build_payload, push_to_user

        route_map = {
            AppNotification.KIND_INVITE: "/?tab=notifications",
            AppNotification.KIND_ACCEPTED: "/?tab=notifications",
            AppNotification.KIND_SHARED: "/?tab=notifications",
        }
        push_to_user(
            recipient,
            build_payload(
                title=title,
                body=body,
                url=route_map.get(kind, "/?tab=notifications"),
                tag=f"app-notification-{notification.id}",
                data={"kind": kind, "notification_id": notification.id},
            ),
        )
    except Exception:
        pass

    return notification


def link_pending_invites_for_user(user: User) -> None:
    pending = SpaceConnection.objects.filter(
        invite_email__iexact=user.email,
        status=SpaceConnection.STATUS_PENDING,
    )
    for conn in pending:
        conn.to_user = user
        conn.save(update_fields=["to_user", "updated_at"])
        create_app_notification(
            recipient=user,
            kind=AppNotification.KIND_INVITE,
            title=f"{conn.from_user.username} wants to connect",
            body="Accept to share tasks, notes, and reminders with each other.",
            payload={
                "connection_id": conn.id,
                "from_username": conn.from_user.username,
                "invite_token": conn.invite_token,
            },
        )


def get_owned_item(user: User, item_type: str, item_id: int):
    model_map = {
        SharedItem.ITEM_TASK: Task,
        SharedItem.ITEM_NOTE: Note,
        SharedItem.ITEM_PLAN: Plan,
        SharedItem.ITEM_EVENT: Event,
    }
    model = model_map.get(item_type)
    if not model:
        raise ValidationError({"item_type": "That type of item can't be shared."})
    try:
        return model.objects.get(pk=item_id, user=user)
    except model.DoesNotExist as exc:
        raise PermissionDenied("You can only share things you created.") from exc


def snapshot_item(item, item_type: str) -> dict:
    if item_type == SharedItem.ITEM_TASK:
        return {
            "title": item.title,
            "description": item.description,
            "due_date": item.due_date.isoformat() if item.due_date else None,
            "priority": item.priority,
            "status": item.status,
            "completed": item.completed,
            "is_daily": item.is_daily,
        }
    if item_type == SharedItem.ITEM_NOTE:
        return {
            "title": item.title,
            "content": item.content,
            "is_pinned": item.is_pinned,
        }
    if item_type == SharedItem.ITEM_PLAN:
        return {
            "title": item.title,
            "content": item.content,
            "start_date": str(item.start_date) if item.start_date else None,
            "end_date": str(item.end_date) if item.end_date else None,
            "status": item.status,
        }
    if item_type == SharedItem.ITEM_EVENT:
        return {
            "title": item.title,
            "description": item.description,
            "starts_at": item.starts_at.isoformat(),
            "remind_at": item.remind_at.isoformat() if item.remind_at else None,
        }
    return {}


def delete_notification_for_user(user: User, notification: AppNotification) -> dict:
    """Remove one activity alert; for shares, also remove the inbox copy."""
    if notification.recipient_id != user.id:
        raise PermissionError("Not your notification.")

    shared_removed = False
    if notification.kind == AppNotification.KIND_SHARED:
        raw = notification.payload.get("shared_item_id")
        if raw is not None:
            try:
                shared_id = int(raw)
            except (TypeError, ValueError):
                shared_id = None
            if shared_id is not None:
                deleted, _ = SharedItem.objects.filter(
                    pk=shared_id, shared_with=user
                ).delete()
                shared_removed = deleted > 0

    notification.delete()
    return {"deleted_shared_item": shared_removed}


def clear_notifications_for_user(user: User) -> dict:
    """Clear Activity"""
    notif_deleted, _ = AppNotification.objects.filter(recipient=user).delete()
    shared_deleted, _ = SharedItem.objects.filter(shared_with=user).delete()
    return {
        "deleted_notifications": notif_deleted,
        "deleted_shared_items": shared_deleted,
    }
