from django.contrib import admin

from .models import Event, Note, Notebook, Plan, Task


@admin.register(Notebook)
class NotebookAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at", "updated_at")
    search_fields = ("name", "description")


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ("title", "notebook", "is_pinned", "updated_at")
    list_filter = ("is_pinned", "notebook")
    search_fields = ("title", "content")


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "start_date", "end_date", "updated_at")
    list_filter = ("status",)
    search_fields = ("title", "content")


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "status",
        "priority",
        "due_date",
        "is_daily",
        "completed",
        "updated_at",
    )
    list_filter = ("status", "priority", "is_daily", "completed")
    search_fields = ("title", "description")


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "starts_at", "remind_at", "notified")
    list_filter = ("notified",)
    search_fields = ("title", "description")
