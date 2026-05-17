import secrets

from django.conf import settings
from django.db import models


class UserOwnedModel(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="%(class)ss",
    )

    class Meta:
        abstract = True


class Notebook(UserOwnedModel):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return self.name


class Note(UserOwnedModel):
    notebook = models.ForeignKey(
        Notebook,
        on_delete=models.CASCADE,
        related_name="notes",
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=300)
    content = models.TextField(blank=True)
    is_pinned = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_pinned", "-updated_at"]

    def __str__(self):
        return self.title


class Plan(UserOwnedModel):
    title = models.CharField(max_length=300)
    content = models.TextField(blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ("draft", "Draft"),
            ("active", "Active"),
            ("done", "Done"),
        ],
        default="active",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return self.title


class Task(UserOwnedModel):
    PRIORITY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
    ]
    STATUS_CHOICES = [
        ("todo", "To Do"),
        ("in_progress", "In Progress"),
        ("done", "Done"),
    ]

    title = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    due_date = models.DateTimeField(null=True, blank=True)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default="medium")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="todo")
    is_daily = models.BooleanField(default=False)
    completed = models.BooleanField(default=False)
    remind_at = models.DateTimeField(null=True, blank=True)
    reminded = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["completed", "-priority", "due_date", "-created_at"]

    def __str__(self):
        return self.title


class Event(UserOwnedModel):
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    starts_at = models.DateTimeField()
    remind_at = models.DateTimeField(null=True, blank=True)
    notified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["starts_at"]

    def __str__(self):
        return self.title


class SpaceConnection(models.Model):
    STATUS_PENDING = "pending"
    STATUS_ACCEPTED = "accepted"
    STATUS_DECLINED = "declined"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_ACCEPTED, "Accepted"),
        (STATUS_DECLINED, "Declined"),
    ]

    from_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="connections_sent",
    )
    to_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="connections_received",
        null=True,
        blank=True,
    )
    invite_email = models.EmailField()
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING
    )
    invite_token = models.CharField(max_length=64, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["from_user", "invite_email"],
                name="unique_invite_email_per_user",
            ),
        ]

    def save(self, *args, **kwargs):
        if not self.invite_token:
            self.invite_token = secrets.token_urlsafe(32)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.from_user} → {self.invite_email} ({self.status})"


class SharedItem(models.Model):
    ITEM_TASK = "task"
    ITEM_NOTE = "note"
    ITEM_PLAN = "plan"
    ITEM_EVENT = "event"
    ITEM_CHOICES = [
        (ITEM_TASK, "Task"),
        (ITEM_NOTE, "Note"),
        (ITEM_PLAN, "Plan"),
        (ITEM_EVENT, "Event"),
    ]

    shared_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="items_shared",
    )
    shared_with = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="items_received",
    )
    item_type = models.CharField(max_length=20, choices=ITEM_CHOICES)
    item_id = models.PositiveIntegerField()
    payload = models.JSONField()
    message = models.TextField(blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.item_type} from {self.shared_by} to {self.shared_with}"


class AppNotification(models.Model):
    KIND_INVITE = "connection_invite"
    KIND_ACCEPTED = "connection_accepted"
    KIND_SHARED = "item_shared"
    KIND_CHOICES = [
        (KIND_INVITE, "Connection invite"),
        (KIND_ACCEPTED, "Connection accepted"),
        (KIND_SHARED, "Item shared"),
    ]

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="app_notifications",
    )
    kind = models.CharField(max_length=32, choices=KIND_CHOICES)
    title = models.CharField(max_length=300)
    body = models.TextField(blank=True)
    payload = models.JSONField(default=dict, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.kind} → {self.recipient}"
