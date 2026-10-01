from django.core.validators import MaxValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("tasks", "0014_task_reminder_days")]
    operations = [
        migrations.AlterField(
            model_name="task",
            name="reminder_days",
            field=models.PositiveSmallIntegerField(
                blank=True, null=True, validators=[MaxValueValidator(365)]
            ),
        )
    ]
