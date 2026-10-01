import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("common", "0045_event_cancellation_history"),
        ("opportunity", "0020_deal_phone_email"),
    ]
    operations = [
        migrations.AddField(
            model_name="salesappointment",
            name="deal",
            field=models.ForeignKey(
                to="opportunity.opportunity",
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="sales_appointments",
            ),
        )
    ]
