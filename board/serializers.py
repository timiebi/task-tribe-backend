from rest_framework import serializers

from .models import Event, Note, Notebook, Plan, Task


class NotebookSerializer(serializers.ModelSerializer):
    note_count = serializers.SerializerMethodField()

    class Meta:
        model = Notebook
        fields = [
            "id",
            "name",
            "description",
            "note_count",
            "created_at",
            "updated_at",
        ]

    def get_note_count(self, obj):
        return obj.notes.count()


class NoteSerializer(serializers.ModelSerializer):
    notebook_name = serializers.CharField(source="notebook.name", read_only=True)

    class Meta:
        model = Note
        fields = [
            "id",
            "notebook",
            "notebook_name",
            "title",
            "content",
            "is_pinned",
            "created_at",
            "updated_at",
        ]


class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = [
            "id",
            "title",
            "content",
            "start_date",
            "end_date",
            "status",
            "created_at",
            "updated_at",
        ]


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = [
            "id",
            "title",
            "description",
            "due_date",
            "priority",
            "status",
            "is_daily",
            "completed",
            "created_at",
            "updated_at",
        ]


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = [
            "id",
            "title",
            "description",
            "starts_at",
            "remind_at",
            "notified",
            "created_at",
            "updated_at",
        ]
