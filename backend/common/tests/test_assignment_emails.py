from importlib import import_module
from unittest.mock import patch

import pytest
from django.core import mail

from common.testing import restore_rls_context

pytestmark = pytest.mark.django_db


@pytest.fixture(
    params=[
        "accounts.Account",
        "contacts.Contact",
        "cases.Case",
        "opportunity.Opportunity",
    ]
)
def assignment(request, org_a, admin_profile):
    module, name = request.param.split(".")
    model = getattr(import_module(f"{module}.models"), name)
    record = model.objects.create(
        org=org_a,
        **({"first_name": "Demo"} if name == "Contact" else {"name": "Demo"}),
    )
    record.assigned_to.add(admin_profile)
    task = import_module(f"{module}.tasks").send_email_to_assigned_user

    def deliver(recipients=None, org_id=None):
        try:
            task(
                recipients if recipients is not None else [admin_profile.pk],
                record.pk,
                str(org_id or org_a.pk),
            )
        finally:
            restore_rls_context()

    deliver.task = task
    return record, deliver


def test_assignment_is_sent_once_per_current_assignee(assignment, admin_profile):
    _, deliver = assignment
    deliver([admin_profile.pk, admin_profile.pk])
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [admin_profile.user.email]


@pytest.mark.parametrize(
    "change", ["unassign", "remove", "deactivate", "disable_user", "archive", "delete"]
)
def test_queued_assignment_rechecks_access(assignment, admin_profile, change):
    from django.utils import timezone

    record, deliver = assignment
    if change == "unassign":
        record.assigned_to.clear()
    elif change == "remove":
        admin_profile.removed_at = timezone.now()
        admin_profile.save(update_fields=["removed_at"])
    elif change == "deactivate":
        admin_profile.is_active = False
        admin_profile.save(update_fields=["is_active"])
    elif change == "disable_user":
        admin_profile.user.is_active = False
        admin_profile.user.save(update_fields=["is_active"])
    elif change == "archive":
        record.is_active = False
        record.save(update_fields=["is_active"])
    else:
        type(record).objects.filter(pk=record.pk).delete()
    deliver()
    assert not mail.outbox


def test_assignment_cannot_send_across_organizations(assignment, org_b, profile_b):
    _, deliver = assignment
    deliver(org_id=org_b.pk)
    deliver([profile_b.pk])
    assert not mail.outbox


def test_assignment_rechecks_record_permission(assignment, admin_profile, org_a):
    from common.models import CRMRole
    from common.rbac import default_rules

    _, deliver = assignment
    rules = default_rules("own")
    for module in ("contacts", "companies", "deals", "tickets"):
        rules[module]["view"] = "none"
    admin_profile.role = "USER"
    admin_profile.access_role = CRMRole.objects.create(
        org=org_a, name="No record access", rules=rules
    )
    admin_profile.save(update_fields=["role", "access_role"])
    deliver()
    assert not mail.outbox


def test_assignment_clears_context_even_if_delivery_fails(assignment):
    _, deliver = assignment
    with (
        patch(
            "common.assignment_emails.EmailMessage.send",
            side_effect=OSError("unavailable"),
        ),
        patch("common.assignment_emails.clear_rls_context") as clear,
        pytest.raises(OSError),
    ):
        deliver()
    clear.assert_called_once()


def test_assignment_waits_for_commit_and_ignores_rollback(
    assignment, admin_profile, django_capture_on_commit_callbacks
):
    from django.db import transaction

    record, deliver = assignment
    task = deliver.task
    args = ([admin_profile.pk], record.pk, str(record.org_id))
    with patch.object(task, "delay") as dispatch:
        with django_capture_on_commit_callbacks(execute=True):
            with transaction.atomic():
                task.delay_on_commit(*args)
                dispatch.assert_not_called()
        dispatch.assert_called_once_with(*args)
        dispatch.reset_mock()
        with django_capture_on_commit_callbacks(execute=True):
            with pytest.raises(RuntimeError), transaction.atomic():
                task.delay_on_commit(*args)
                raise RuntimeError("rollback")
        dispatch.assert_not_called()


@pytest.mark.parametrize("method", ["put", "patch"])
def test_contact_reassignment_notifies_only_new_assignees(
    admin_client, admin_profile, user_profile, org_a, method
):
    from contacts.models import Contact

    record = Contact.objects.create(
        org=org_a, first_name="Demo", source="ORGANIC", stage="LEAD", phone="3055550199"
    )
    record.assigned_to.add(admin_profile)
    data = {
        "first_name": "Demo",
        "email": "assignment@example.com",
        "source": "ORGANIC",
        "stage": "LEAD",
        "phone": "3055550199",
        "assigned_to": [str(user_profile.pk)],
    }
    with patch("contacts.views.send_email_to_assigned_user.delay_on_commit") as enqueue:
        response = getattr(admin_client, method)(
            f"/api/contacts/{record.pk}/", data, format="json"
        )
    assert response.status_code == 200, response.data
    assert enqueue.call_args.args[0] == [user_profile.pk]
    with patch("contacts.views.send_email_to_assigned_user.delay_on_commit") as enqueue:
        response = getattr(admin_client, method)(
            f"/api/contacts/{record.pk}/", data, format="json"
        )
    assert response.status_code == 200, response.data
    assert enqueue.call_args.args[0] == []
