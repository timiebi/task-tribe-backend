from django.db.models import Q
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Event, Note, Notebook, Plan, Task
from .timezone_utils import request_localdate
from .serializers import (
    EventSerializer,
    NoteSerializer,
    NotebookSerializer,
    PlanSerializer,
    TaskSerializer,
)


class UserScopedViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class NotebookViewSet(UserScopedViewSet):
    queryset = Notebook.objects.all()
    serializer_class = NotebookSerializer


class NoteViewSet(UserScopedViewSet):
    queryset = Note.objects.select_related("notebook").all()
    serializer_class = NoteSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        notebook_id = self.request.query_params.get("notebook")
        if notebook_id:
            qs = qs.filter(notebook_id=notebook_id)
        return qs

    def perform_create(self, serializer):
        notebook = serializer.validated_data.get("notebook")
        if notebook and notebook.user_id != self.request.user.id:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Notebook does not belong to you.")
        serializer.save(user=self.request.user)


class PlanViewSet(UserScopedViewSet):
    queryset = Plan.objects.all()
    serializer_class = PlanSerializer


class TaskViewSet(UserScopedViewSet):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        daily = self.request.query_params.get("daily")
        if daily == "true":
            qs = qs.filter(is_daily=True)
        elif daily == "false":
            qs = qs.filter(is_daily=False)
        status_param = self.request.query_params.get("status")
        if status_param:
            qs = qs.filter(status=status_param)
        return qs

    @action(detail=True, methods=["post"])
    def toggle_complete(self, request, pk=None):
        task = self.get_object()
        task.completed = not task.completed
        if task.completed:
            task.status = "done"
        elif task.status == "done":
            task.status = "todo"
        task.save()
        return Response(TaskSerializer(task).data)

    @action(detail=False, methods=["get"])
    def today(self, request):
        today = request_localdate(request)
        tasks = self.get_queryset().filter(
            Q(is_daily=True) | Q(due_date__date=today)
        )
        serializer = self.get_serializer(tasks, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def due_reminders(self, request):
        now = timezone.now()
        tasks = self.get_queryset().filter(
            remind_at__lte=now,
            reminded=False,
            completed=False,
        )
        serializer = self.get_serializer(tasks, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def mark_reminded(self, request, pk=None):
        task = self.get_object()
        task.reminded = True
        task.save(update_fields=["reminded", "updated_at"])
        return Response(self.get_serializer(task).data)


class EventViewSet(UserScopedViewSet):
    queryset = Event.objects.all()
    serializer_class = EventSerializer

    @action(detail=False, methods=["get"])
    def due_reminders(self, request):
        now = timezone.now()
        events = self.get_queryset().filter(
            remind_at__lte=now,
            notified=False,
        )
        serializer = self.get_serializer(events, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def mark_notified(self, request, pk=None):
        event = self.get_object()
        event.notified = True
        event.save()
        return Response(EventSerializer(event).data)
