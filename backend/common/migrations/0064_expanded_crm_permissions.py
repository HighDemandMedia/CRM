"""Expand policies without granting destructive operations to non-admin roles."""

from django.db import migrations


def expand(apps, schema_editor):
    Org = apps.get_model("common", "Org")
    Role = apps.get_model("common", "CRMRole")
    Profile = apps.get_model("common", "Profile")
    records = ("contacts", "companies", "deals", "tasks", "tickets")

    def baseline(scope):
        rules = {
            m: {
                "view": scope,
                "create": True,
                "edit": scope,
                "delete": "none",
                "export": "none",
                "reassign": "team" if scope == "team" else "none",
            }
            for m in records
        }
        return rules

    connection = schema_editor.connection
    with connection.cursor() as cursor:
        previous = None
        if connection.vendor == "postgresql":
            cursor.execute("SELECT current_setting('app.current_org', true)")
            previous = cursor.fetchone()[0]
        try:
            for org in Org.objects.all().iterator():
                if connection.vendor == "postgresql":
                    cursor.execute(
                        "SELECT set_config('app.current_org', %s, true)", [str(org.pk)]
                    )
                for name, scope in [("Member", "own"), ("Manager", "team")]:
                    Role.objects.get_or_create(
                        org_id=org.pk,
                        name=name,
                        defaults={
                            "scope": scope,
                            "rules": baseline(scope),
                            "description": "Own CRM records"
                            if scope == "own"
                            else "Team CRM records",
                        },
                    )
                for role in Role.objects.filter(org_id=org.pk):
                    rules = role.rules or {}
                    for module in records:
                        row = rules.setdefault(
                            module,
                            {
                                "view": "none",
                                "create": False,
                                "edit": "none",
                                "delete": "none",
                                "export": "none",
                                "reassign": "none",
                            },
                        )
                        row.setdefault("reassign", "none")
                        for action in ("stage", "notes", "attachments", "associations"):
                            row.setdefault(action, row.get("edit", "none"))
                    builtin = role.name in ("Member", "Manager")
                    scope = role.scope if builtin else "none"
                    rules.setdefault(
                        "calendar",
                        {
                            "view": scope,
                            "create": builtin,
                            "edit": scope,
                            "cancel": "none",
                            "reassign": "none",
                            "override_conflicts": False,
                            "export": "none",
                        },
                    )
                    rules.setdefault("reports", {"view": scope, "export": "none"})
                    role.rules = rules
                    role.save(update_fields=["rules"])
                member = Role.objects.get(org_id=org.pk, name="Member")
                Profile.objects.filter(
                    org_id=org.pk, role="USER", access_role__isnull=True
                ).update(access_role_id=member.pk)
        finally:
            if connection.vendor == "postgresql":
                cursor.execute(
                    "SELECT set_config('app.current_org', %s, true)", [previous or ""]
                )


class Migration(migrations.Migration):
    dependencies = [("common", "0063_optional_properties_phone_keys_per_org")]
    operations = [migrations.RunPython(expand, migrations.RunPython.noop)]
