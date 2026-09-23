from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [("tasks", "0013_alter_taskpipeline_is_default")]
    operations = [migrations.AddField(model_name="task", name="reminder_days", field=models.PositiveSmallIntegerField(blank=True, null=True, choices=[(0, "On due date"), (1, "1 day before"), (2, "2 days before"), (3, "3 days before"), (7, "1 week before")]))]
