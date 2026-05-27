import logging

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def send_password_reset_email(*, user, reset_url: str) -> bool:
    subject = "Reset your Task Board password"
    message = (
        f"Hi {user.username},\n\n"
        f"Someone asked to reset your Task Board password. Open this link:\n\n"
        f"{reset_url}\n\n"
        f"If you didn't request this, you can ignore this email.\n\n"
        f"The link expires in 24 hours.\n"
    )
    from_email = settings.DEFAULT_FROM_EMAIL
    if not settings.EMAIL_HOST:
        if settings.DEBUG:
            logger.warning("Password reset link (email not configured): %s", reset_url)
            return True
        logger.error("EMAIL_HOST not configured; cannot send password reset.")
        return False

    try:
        send_mail(
            subject,
            message,
            from_email,
            [user.email],
            fail_silently=False,
        )
        return True
    except Exception:
        logger.exception("Failed to send password reset email to %s", user.email)
        return False
