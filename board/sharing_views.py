from django.contrib.auth.models import User
from django.db.models import Q
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import AppNotification, SharedItem, SpaceConnection
from .sharing import (
    create_app_notification,
    get_owned_item,
    normalize_email,
    snapshot_item,
    users_are_connected,
)
from .sharing_serializers import (
    AcceptTokenSerializer,
    AppNotificationSerializer,
    InviteByEmailSerializer,
    ShareItemSerializer,
    SharedItemSerializer,
    SpaceConnectionSerializer,
)


def _connection_for_recipient(conn: SpaceConnection, user: User) -> bool:
    if conn.to_user_id == user.id:
        return True
    return bool(user.email) and conn.invite_email.lower() == user.email.lower()


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_connections(request):
    qs = SpaceConnection.objects.filter(
        status=SpaceConnection.STATUS_ACCEPTED,
    ).filter(Q(from_user=request.user) | Q(to_user=request.user))
    data = []
    seen = set()
    for conn in qs.select_related("from_user", "to_user"):
        other = conn.to_user if conn.from_user_id == request.user.id else conn.from_user
        if other and other.id not in seen:
            seen.add(other.id)
            data.append(
                {
                    "id": conn.id,
                    "user_id": other.id,
                    "username": other.username,
                    "email": other.email,
                }
            )
    return Response(data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_invites_sent(request):
    qs = SpaceConnection.objects.filter(from_user=request.user).exclude(
        status=SpaceConnection.STATUS_DECLINED
    )
    return Response(SpaceConnectionSerializer(qs, many=True).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def invite_by_email(request):
    ser = InviteByEmailSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    email = normalize_email(ser.validated_data["email"])

    if request.user.email and email == normalize_email(request.user.email):
        return Response(
            {"detail": "You can't invite your own email address."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    to_user = User.objects.filter(email__iexact=email).first()

    conn, created = SpaceConnection.objects.get_or_create(
        from_user=request.user,
        invite_email=email,
        defaults={"to_user": to_user, "status": SpaceConnection.STATUS_PENDING},
    )

    if not created:
        if conn.status == SpaceConnection.STATUS_ACCEPTED:
            return Response(
                {"detail": "You're already connected with them."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        conn.status = SpaceConnection.STATUS_PENDING
        conn.to_user = to_user
        conn.save(update_fields=["status", "to_user", "updated_at"])

    if to_user:
        create_app_notification(
            recipient=to_user,
            kind=AppNotification.KIND_INVITE,
            title=f"{request.user.username} wants to connect",
            body="Accept to share tasks, notes, and reminders with each other.",
            payload={
                "connection_id": conn.id,
                "from_username": request.user.username,
                "from_user_id": request.user.id,
                "invite_token": conn.invite_token,
            },
        )

    return Response(
        SpaceConnectionSerializer(conn).data,
        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
    )


def _accept_connection(conn: SpaceConnection, user: User) -> SpaceConnection:
    if conn.status == SpaceConnection.STATUS_ACCEPTED:
        return conn
    if not _connection_for_recipient(conn, user):
        from rest_framework.exceptions import PermissionDenied

        raise PermissionDenied("This invite wasn't sent to you.")

    conn.status = SpaceConnection.STATUS_ACCEPTED
    conn.to_user = user
    conn.save(update_fields=["status", "to_user", "updated_at"])

    create_app_notification(
        recipient=conn.from_user,
        kind=AppNotification.KIND_ACCEPTED,
        title=f"{user.username} accepted your invite",
        body="You can share tasks, notes, and reminders with each other now.",
        payload={"user_id": user.id, "username": user.username},
    )
    return conn


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def accept_connection(request, pk):
    try:
        conn = SpaceConnection.objects.get(pk=pk, status=SpaceConnection.STATUS_PENDING)
    except SpaceConnection.DoesNotExist:
        return Response(
            {"detail": "That invite is no longer available."},
            status=status.HTTP_404_NOT_FOUND,
        )

    conn = _accept_connection(conn, request.user)
    return Response(SpaceConnectionSerializer(conn).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def decline_connection(request, pk):
    try:
        conn = SpaceConnection.objects.get(pk=pk, status=SpaceConnection.STATUS_PENDING)
    except SpaceConnection.DoesNotExist:
        return Response(
            {"detail": "That invite is no longer available."},
            status=status.HTTP_404_NOT_FOUND,
        )

    if not _connection_for_recipient(conn, request.user):
        return Response(
            {"detail": "You can't respond to this invite."},
            status=status.HTTP_403_FORBIDDEN,
        )

    conn.status = SpaceConnection.STATUS_DECLINED
    conn.save(update_fields=["status", "updated_at"])
    return Response({"detail": "Invite declined."})


@api_view(["POST"])
@permission_classes([AllowAny])
def accept_by_token(request):
    ser = AcceptTokenSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    token = ser.validated_data["token"]

    try:
        conn = SpaceConnection.objects.get(
            invite_token=token, status=SpaceConnection.STATUS_PENDING
        )
    except SpaceConnection.DoesNotExist:
        return Response(
            {"detail": "This invite link isn't valid anymore."},
            status=status.HTTP_404_NOT_FOUND,
        )

    if not request.user.is_authenticated:
        return Response(
            {
                "detail": "Sign in first, then accept the invite.",
                "requires_login": True,
                "invite_email": conn.invite_email,
                "from_username": conn.from_user.username,
            },
            status=status.HTTP_401_UNAUTHORIZED,
        )

    conn = _accept_connection(conn, request.user)
    return Response(SpaceConnectionSerializer(conn).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def share_item(request):
    ser = ShareItemSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    data = ser.validated_data

    try:
        recipient = User.objects.get(pk=data["to_user_id"])
    except User.DoesNotExist:
        return Response(
            {"detail": "We couldn't find that person."},
            status=status.HTTP_404_NOT_FOUND,
        )

    if not users_are_connected(request.user, recipient):
        return Response(
            {
                "detail": "They need to accept your invite before you can share.",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    item = get_owned_item(request.user, data["item_type"], data["item_id"])
    payload = snapshot_item(item, data["item_type"])

    shared = SharedItem.objects.create(
        shared_by=request.user,
        shared_with=recipient,
        item_type=data["item_type"],
        item_id=data["item_id"],
        payload=payload,
        message=data.get("message", ""),
    )

    type_labels = {
        SharedItem.ITEM_TASK: "task",
        SharedItem.ITEM_NOTE: "note",
        SharedItem.ITEM_PLAN: "plan",
        SharedItem.ITEM_EVENT: "reminder",
    }
    label = type_labels.get(data["item_type"], "item")

    item_title = payload.get("title", "")
    create_app_notification(
        recipient=recipient,
        kind=AppNotification.KIND_SHARED,
        title=f"{request.user.username} shared a {label} with you",
        body=item_title or f"Open Notifications to view it.",
        payload={
            "shared_item_id": shared.id,
            "item_type": data["item_type"],
            "from_username": request.user.username,
        },
    )

    return Response(SharedItemSerializer(shared).data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def inbox_shares(request):
    qs = SharedItem.objects.filter(shared_with=request.user).select_related("shared_by")
    return Response(SharedItemSerializer(qs, many=True).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def mark_share_read(request, pk):
    try:
        item = SharedItem.objects.get(pk=pk, shared_with=request.user)
    except SharedItem.DoesNotExist:
        return Response(
            {"detail": "We couldn't find that shared item."},
            status=status.HTTP_404_NOT_FOUND,
        )
    if not item.read_at:
        item.read_at = timezone.now()
        item.save(update_fields=["read_at"])
    return Response(SharedItemSerializer(item).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_notifications(request):
    qs = AppNotification.objects.filter(recipient=request.user)[:100]
    return Response(AppNotificationSerializer(qs, many=True).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def unread_notification_count(request):
    count = AppNotification.objects.filter(
        recipient=request.user, read_at__isnull=True
    ).count()
    return Response({"count": count})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def mark_notification_read(request, pk):
    try:
        note = AppNotification.objects.get(pk=pk, recipient=request.user)
    except AppNotification.DoesNotExist:
        return Response(
            {"detail": "We couldn't find that notification."},
            status=status.HTTP_404_NOT_FOUND,
        )
    if not note.read_at:
        note.read_at = timezone.now()
        note.save(update_fields=["read_at"])
    return Response(AppNotificationSerializer(note).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def accept_invite_from_notification(request, pk):
    try:
        note = AppNotification.objects.get(
            pk=pk,
            recipient=request.user,
            kind=AppNotification.KIND_INVITE,
        )
    except AppNotification.DoesNotExist:
        return Response(
            {"detail": "We couldn't find that notification."},
            status=status.HTTP_404_NOT_FOUND,
        )

    conn_id = note.payload.get("connection_id")
    if not conn_id:
        return Response(
            {"detail": "This notification isn't valid anymore."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        conn = SpaceConnection.objects.get(
            pk=conn_id, status=SpaceConnection.STATUS_PENDING
        )
    except SpaceConnection.DoesNotExist:
        return Response(
            {"detail": "You've already accepted or declined this invite."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    conn = _accept_connection(conn, request.user)
    if not note.read_at:
        note.read_at = timezone.now()
        note.save(update_fields=["read_at"])

    return Response(
        {
            "connection": SpaceConnectionSerializer(conn).data,
            "notification": AppNotificationSerializer(note).data,
        }
    )
