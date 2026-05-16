from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("board", "0002_user_ownership"),
    ]

    operations = [
        migrations.AddField(
            model_name="task",
            name="remind_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="task",
            name="reminded",
            field=models.BooleanField(default=False),
        ),
    ]
