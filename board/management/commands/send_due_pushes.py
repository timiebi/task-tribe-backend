from django.core.management.base import BaseCommand

from board.push_views import send_due_reminders


class Command(BaseCommand):
    help = "Send web-push notifications for tasks and events that are due."

    def handle(self, *args, **options):
        result = send_due_reminders()
        self.stdout.write(
            self.style.SUCCESS(
                f"Sent pushes — tasks: {result['tasks']}, events: {result['events']}"
            )
        )
