from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .auth_views import health, login, logout, me, register
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
    path("auth/login/", login),
    path("auth/register/", register),
    path("auth/me/", me),
    path("auth/logout/", logout),
    path("", include(router.urls)),
]
