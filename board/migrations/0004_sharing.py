import secrets

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def gen_token():
    return secrets.token_urlsafe(32)


class Migration(migrations.Migration):

    dependencies = [
        ("board", "0003_task_reminders"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="SpaceConnection",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("invite_email", models.EmailField(max_length=254)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("accepted", "Accepted"),
                            ("declined", "Declined"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                (
                    "invite_token",
                    models.CharField(db_index=True, max_length=64, unique=True),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "from_user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="connections_sent",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "to_user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="connections_received",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="SharedItem",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "item_type",
                    models.CharField(
                        choices=[
                            ("task", "Task"),
                            ("note", "Note"),
                            ("plan", "Plan"),
                            ("event", "Event"),
                        ],
                        max_length=20,
                    ),
                ),
                ("item_id", models.PositiveIntegerField()),
                ("payload", models.JSONField()),
                ("message", models.TextField(blank=True)),
                ("read_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "shared_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="items_shared",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "shared_with",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="items_received",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="AppNotification",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "kind",
                    models.CharField(
                        choices=[
                            ("connection_invite", "Connection invite"),
                            ("connection_accepted", "Connection accepted"),
                            ("item_shared", "Item shared"),
                        ],
                        max_length=32,
                    ),
                ),
                ("title", models.CharField(max_length=300)),
                ("body", models.TextField(blank=True)),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("read_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "recipient",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="app_notifications",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="spaceconnection",
            constraint=models.UniqueConstraint(
                fields=("from_user", "invite_email"),
                name="unique_invite_email_per_user",
            ),
        ),
    ]
