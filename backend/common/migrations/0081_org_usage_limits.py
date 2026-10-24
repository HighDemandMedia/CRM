from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("common", "0080_appointment_email_delivery")]

    operations = [
        migrations.AlterField(
            model_name="securityauditlog",
            name="event_type",
            field=models.CharField(
                max_length=50,
                db_index=True,
                choices=(
                    ("LOGIN_SUCCESS", "Login Success"),
                    ("LOGIN_FAILURE", "Login Failure"),
                    ("LOGOUT", "Logout"),
                    ("ORG_SWITCH", "Organization Switch"),
                    ("TOKEN_REFRESH", "Token Refresh"),
                    ("TOKEN_REVOKED", "Token Revoked"),
                    ("PERMISSION_DENIED", "Permission Denied"),
                    ("PERMISSION_SET_CHANGED", "Permission Set Changed"),
                    ("ORGANIZATION_LIMITS_CHANGED", "Organization Limits Changed"),
                    ("CROSS_ORG_ATTEMPT", "Cross-Org Access Attempt"),
                    ("API_KEY_USED", "API Key Used"),
                    ("API_KEY_INVALID", "Invalid API Key"),
                    ("MEMBERSHIP_REVOKED", "Membership Revoked"),
                    ("SUSPICIOUS_ACTIVITY", "Suspicious Activity"),
                    ("SAMPLE_DATA_CLEARED", "Vertical Pack Sample Data Cleared"),
                ),
            ),
        ),
        migrations.AddField(
            model_name="org",
            name="usage_limits",
            field=models.JSONField(default=dict, blank=True, editable=False),
        ),
    ]
