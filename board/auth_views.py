import logging

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .password_email import send_password_reset_email
from .timezone_utils import resolve_request_timezone_context

logger = logging.getLogger(__name__)


@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    from django.db import connection

    payload = {"status": "ok"}
    try:
        connection.ensure_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        Token.objects.exists()
        payload["database"] = "ok"
    except Exception as exc:
        payload["status"] = "degraded"
        payload["database"] = str(exc)
    return Response(payload)


@api_view(["GET"])
@permission_classes([AllowAny])
def time_context(request):
    """Return which timezone the server used for this request (debug / travel check)."""
    return Response(resolve_request_timezone_context(request))


@api_view(["POST"])
@permission_classes([AllowAny])
def login(request):
    username = request.data.get("username", "").strip()
    password = request.data.get("password", "")
    user = authenticate(username=username, password=password)
    if not user:
        return Response(
            {"detail": "That username or password doesn't match. Try again."},
            status=status.HTTP_401_UNAUTHORIZED,
        )
    token, _ = Token.objects.get_or_create(user=user)
    return Response({
        "token": token.key,
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
        },
    })


@api_view(["POST"])
@permission_classes([AllowAny])
def register(request):
    username = request.data.get("username", "").strip()
    password = request.data.get("password", "")
    email = request.data.get("email", "").strip()

    if not username or not password:
        return Response(
            {"detail": "Please enter a username and password."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if User.objects.filter(username=username).exists():
        return Response(
            {"detail": "That username is already taken. Pick another one."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if len(password) < 8:
        return Response(
            {"detail": "Use a password at least 8 characters long."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = User.objects.create_user(
        username=username,
        password=password,
        email=email,
    )
    if email:
        from .sharing import link_pending_invites_for_user

        link_pending_invites_for_user(user)
    token = Token.objects.create(user=user)
    return Response(
        {
            "token": token.key,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
            },
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    user = request.user
    return Response({
        "id": user.id,
        "username": user.username,
        "email": user.email,
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout(request):
    Token.objects.filter(user=request.user).delete()
    return Response({"detail": "Logged out."})


@api_view(["POST"])
@permission_classes([AllowAny])
def password_reset_request(request):
    email = request.data.get("email", "").strip().lower()
    if not email:
        return Response(
            {"detail": "Please enter the email on your account."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    generic = {
        "detail": "If that email is on an account, we sent reset instructions.",
    }

    user = User.objects.filter(email__iexact=email).first()
    if user and user.email:
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        base = settings.APP_FRONTEND_URL.rstrip("/")
        reset_url = f"{base}/reset-password?uid={uid}&token={token}"
        sent = send_password_reset_email(user=user, reset_url=reset_url)
        if not sent and not settings.DEBUG:
            logger.warning("Password reset email not sent for user id=%s", user.pk)

    return Response(generic)


@api_view(["POST"])
@permission_classes([AllowAny])
def password_reset_confirm(request):
    uid_b64 = request.data.get("uid", "")
    token = request.data.get("token", "")
    password = request.data.get("password", "")

    if len(password) < 8:
        return Response(
            {"detail": "Use a password at least 8 characters long."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        uid = force_str(urlsafe_base64_decode(uid_b64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        return Response(
            {"detail": "This reset link isn't valid. Request a new one."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not default_token_generator.check_token(user, token):
        return Response(
            {
                "detail": (
                    "This reset link expired or was already used. Request a new one."
                ),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    user.set_password(password)
    user.save(update_fields=["password"])
    Token.objects.filter(user=user).delete()
    return Response({"detail": "Password updated. You can sign in now."})
