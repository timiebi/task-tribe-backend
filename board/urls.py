from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .auth_views import health, login, logout, me, register, time_context
from .push_views import public_key as push_public_key
from .push_views import run_due_reminders, subscribe as push_subscribe, unsubscribe as push_unsubscribe
from .sharing_views import (
    accept_by_token,
    accept_connection,
    accept_invite_from_notification,
    decline_connection,
    inbox_shares,
    invite_by_email,
    list_connections,
    list_invites_sent,
    list_notifications,
    mark_notification_read,
    mark_share_read,
    share_item,
    unread_notification_count,
)
from .views import (
    EventViewSet,
    NoteViewSet,
    NotebookViewSet,
    PlanViewSet,
    TaskViewSet,
)

router = DefaultRouter()
router.register("notebooks", NotebookViewSet)
router.register("notes", NoteViewSet)
router.register("plans", PlanViewSet)
router.register("tasks", TaskViewSet)
router.register("events", EventViewSet)

urlpatterns = [
    path("health/", health),
    path("time-context/", time_context),
    path("auth/login/", login),
    path("auth/register/", register),
    path("auth/me/", me),
    path("auth/logout/", logout),
    path("connections/", list_connections),
    path("connections/sent/", list_invites_sent),
    path("connections/invite/", invite_by_email),
    path("connections/accept-token/", accept_by_token),
    path("connections/<int:pk>/accept/", accept_connection),
    path("connections/<int:pk>/decline/", decline_connection),
    path("shares/", share_item),
    path("shares/inbox/", inbox_shares),
    path("shares/<int:pk>/read/", mark_share_read),
    path("notifications/", list_notifications),
    path("notifications/unread-count/", unread_notification_count),
    path("notifications/<int:pk>/read/", mark_notification_read),
    path(
        "notifications/<int:pk>/accept-invite/",
        accept_invite_from_notification,
    ),
    path("push/public-key/", push_public_key),
    path("push/subscribe/", push_subscribe),
    path("push/unsubscribe/", push_unsubscribe),
    path("push/run-due/", run_due_reminders),
    path("", include(router.urls)),
]
