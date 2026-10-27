from django.db import migrations, models

import common.identifiers
from common.migration_operations.compact_ids import CompactBusinessIDs


class Migration(migrations.Migration):
    atomic = True
    dependencies = [
        ("accounts", "0019_alter_account_country"),
        ("admin", "0003_logentry_add_action_flag_choices"),
        ("auth", "0012_alter_user_first_name_max_length"),
        ("business_hours", "0001_initial"),
        ("cases", "0034_required_record_names"),
        ("common", "0084_csv_import_receipt"),
        ("contacts", "0024_alter_contact_country"),
        ("contenttypes", "0002_remove_content_type_name"),
        ("django_ses", "0002_blacklistedemail"),
        ("invoices", "0011_alter_estimate_client_country_and_more"),
        ("leads", "0017_alter_lead_country"),
        ("macros", "0001_initial"),
        ("opportunity", "0023_alter_opportunity_country"),
        ("orders", "0005_alter_order_billing_country_and_more"),
        ("sessions", "0001_initial"),
        ("tasks", "0017_required_record_names"),
        ("token_blacklist", "0013_alter_blacklistedtoken_options_and_more"),
        ("webforms", "0006_submission_confirmation"),
    ]
    operations = [
        CompactBusinessIDs(
            [
                (
                    "common",
                    migrations.CreateModel(
                        name="LegacyBusinessID",
                        fields=[
                            (
                                "id",
                                models.CharField(
                                    max_length=36, primary_key=True, serialize=False
                                ),
                            ),
                            (
                                "replacement",
                                models.CharField(max_length=36, unique=True),
                            ),
                        ],
                    ),
                ),
                (
                    "common",
                    migrations.CreateModel(
                        name="BusinessIDSequence",
                        fields=[
                            (
                                "prefix",
                                models.CharField(
                                    max_length=3, primary_key=True, serialize=False
                                ),
                            ),
                            ("last_number", models.PositiveBigIntegerField(default=0)),
                        ],
                    ),
                ),
                (
                    "common",
                    migrations.CreateModel(
                        name="OrganizationIDReservation",
                        fields=[
                            (
                                "id",
                                models.CharField(
                                    max_length=12, primary_key=True, serialize=False
                                ),
                            ),
                        ],
                    ),
                ),
                (
                    "common",
                    migrations.AlterField(
                        model_name="activity",
                        name="entity_id",
                        field=models.CharField(max_length=36),
                    ),
                ),
                (
                    "common",
                    migrations.AlterField(
                        model_name="attachments",
                        name="object_id",
                        field=models.CharField(max_length=36),
                    ),
                ),
                (
                    "common",
                    migrations.AlterField(
                        model_name="comment",
                        name="object_id",
                        field=models.CharField(max_length=36),
                    ),
                ),
                (
                    "common",
                    migrations.AlterField(
                        model_name="notification",
                        name="entity_id",
                        field=models.CharField(blank=True, max_length=36, null=True),
                    ),
                ),
                (
                    "common",
                    migrations.AlterField(
                        model_name="org",
                        name="id",
                        field=common.identifiers.BusinessIDField(
                            editable=False,
                            max_length=36,
                            prefix="HDM",
                            primary_key=True,
                            serialize=False,
                        ),
                    ),
                ),
                (
                    "common",
                    migrations.AlterField(
                        model_name="organizationclosure",
                        name="org_id",
                        field=models.CharField(
                            max_length=36, primary_key=True, serialize=False
                        ),
                    ),
                ),
                (
                    "common",
                    migrations.AlterField(
                        model_name="organizationlifecycleevent",
                        name="actor_id",
                        field=models.CharField(blank=True, max_length=36, null=True),
                    ),
                ),
                (
                    "common",
                    migrations.AlterField(
                        model_name="organizationlifecycleevent",
                        name="org_id",
                        field=models.CharField(db_index=True, max_length=36),
                    ),
                ),
                (
                    "common",
                    migrations.AlterField(
                        model_name="pendingfiledeletion",
                        name="org_id",
                        field=models.CharField(
                            blank=True, db_index=True, max_length=36, null=True
                        ),
                    ),
                ),
                (
                    "common",
                    migrations.AlterField(
                        model_name="portalaccesstoken",
                        name="resource_id",
                        field=models.CharField(max_length=36),
                    ),
                ),
                (
                    "common",
                    migrations.AlterField(
                        model_name="salesappointment",
                        name="id",
                        field=common.identifiers.BusinessIDField(
                            editable=False,
                            max_length=36,
                            prefix="EVT",
                            primary_key=True,
                            serialize=False,
                        ),
                    ),
                ),
                (
                    "common",
                    migrations.AlterField(
                        model_name="user",
                        name="id",
                        field=common.identifiers.BusinessIDField(
                            editable=False,
                            max_length=36,
                            prefix="USR",
                            primary_key=True,
                            serialize=False,
                        ),
                    ),
                ),
                (
                    "accounts",
                    migrations.AlterField(
                        model_name="account",
                        name="id",
                        field=common.identifiers.BusinessIDField(
                            editable=False,
                            max_length=36,
                            prefix="COM",
                            primary_key=True,
                            serialize=False,
                        ),
                    ),
                ),
                (
                    "cases",
                    migrations.AlterField(
                        model_name="case",
                        name="id",
                        field=common.identifiers.BusinessIDField(
                            editable=False,
                            max_length=36,
                            prefix="TKT",
                            primary_key=True,
                            serialize=False,
                        ),
                    ),
                ),
                (
                    "contacts",
                    migrations.AlterField(
                        model_name="contact",
                        name="id",
                        field=common.identifiers.BusinessIDField(
                            editable=False,
                            max_length=36,
                            prefix="CON",
                            primary_key=True,
                            serialize=False,
                        ),
                    ),
                ),
                (
                    "opportunity",
                    migrations.AlterField(
                        model_name="opportunity",
                        name="id",
                        field=common.identifiers.BusinessIDField(
                            editable=False,
                            max_length=36,
                            prefix="DEA",
                            primary_key=True,
                            serialize=False,
                        ),
                    ),
                ),
                (
                    "tasks",
                    migrations.AlterField(
                        model_name="task",
                        name="id",
                        field=common.identifiers.BusinessIDField(
                            editable=False,
                            max_length=36,
                            prefix="TSK",
                            primary_key=True,
                            serialize=False,
                        ),
                    ),
                ),
            ]
        )
    ]
