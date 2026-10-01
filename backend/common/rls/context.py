"""Temporary tenant context for work outside the request middleware."""

from contextlib import contextmanager

from django.db import connection, transaction


@contextmanager
def org_context(org_id):
    if connection.vendor != "postgresql":
        yield
        return
    # A transaction-local setting is automatically restored at commit/rollback.
    # Explicit restoration also preserves an enclosing transaction's context.
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_setting('app.current_org', true)")
            previous = cursor.fetchone()[0] or ""
            cursor.execute(
                "SELECT set_config('app.current_org', %s, true)", [str(org_id)]
            )
        try:
            yield
        finally:
            if not connection.needs_rollback:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT set_config('app.current_org', %s, true)", [previous]
                    )
