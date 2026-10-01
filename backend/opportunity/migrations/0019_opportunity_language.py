from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("opportunity", "0018_deal_properties")]
    operations = [
        migrations.AddField(
            model_name="opportunity",
            name="language",
            field=models.CharField(
                "Language",
                max_length=100,
                choices=[
                    ("English", "English"),
                    ("Spanish", "Spanish"),
                    ("French", "French"),
                    ("Portuguese", "Portuguese"),
                    ("Chinese", "Chinese"),
                    ("Arabic", "Arabic"),
                    ("Haitian Creole", "Haitian Creole"),
                    ("Russian", "Russian"),
                    ("German", "German"),
                    ("Italian", "Italian"),
                    ("Hindi", "Hindi"),
                    ("Other", "Other"),
                ],
                blank=True,
                default="",
            ),
        )
    ]
