"""Security boundaries shared by record, identity and notification endpoints."""

from datetime import datetime, timedelta
from datetime import timezone as tz
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.core.exceptions import ValidationError as ModelValidationError
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import Account
from cases.analytics import _bucket_dates, _coerce_window
from cases.approvals import Approval, ApprovalRule
from cases.models import Case, CaseWatcher, Solution
from common.kanban import place_in_column
from common.models import Notification, PersonalAccessToken, Profile
from common.notifications import create, visible_notifications
from common.rbac import validate_record_fields
from common.serializer import CreateUserSerializer
from common.tests.test_expanded_permissions import set_role
from contacts.models import Contact
from opportunity.models import Opportunity

pytestmark = pytest.mark.django_db


def test_member_editor_cannot_rename_global_login(regular_user, org_a):
    serializer = CreateUserSerializer(
        instance=regular_user, data={"email": "takeover@example.com"}, partial=True
    )
    assert not serializer.is_valid()
    assert "email" in serializer.errors
    same = CreateUserSerializer(
        instance=regular_user, data={"email": regular_user.email.upper()}, partial=True
    )
    assert same.is_valid(), same.errors


@pytest.mark.parametrize(
    "field",
    [
        "account",
        "contacts",
        "contact",
        "companies",
        "opportunity",
        "case",
        "lead",
        "parent",
        "parent_id",
    ],
)
def test_all_association_aliases_require_capability(user_profile, field):
    set_role(user_profile, tasks={"associations": "none"})
    request = SimpleNamespace(
        profile=user_profile, data={field: "target"}, path="/api/tasks/", FILES={}
    )
    with pytest.raises(PermissionDenied):
        validate_record_fields(request, "tasks", None, creating=True)
    request.data = {"name": "Ordinary edit"}
    validate_record_fields(request, "tasks", None)


def test_ticket_notification_revokes_stored_copy(user_profile, org_a, user_client):
    set_role(user_profile)
    ticket = Case.objects.create(org=org_a, name="Private ticket")
    assert create(user_profile, "case.commented", entity=ticket) is None
    ticket.assigned_to.add(user_profile)
    row = create(user_profile, "case.commented", entity=ticket)
    assert row is not None
    assert (
        visible_notifications(Notification.objects.all(), user_profile)
        .filter(pk=row.pk)
        .exists()
    )
    # Watcher status cannot override a configured role after assignment is removed.
    CaseWatcher.objects.create(org=org_a, case=ticket, profile=user_profile)
    ticket.assigned_to.clear()
    assert (
        not visible_notifications(Notification.objects.all(), user_profile)
        .filter(pk=row.pk)
        .exists()
    )
    data = user_client.get("/api/notifications/?delivery=true").json()
    assert str(row.pk) not in str(data)


def test_mention_does_not_grant_ticket_access(org_a, admin_profile, user_profile):
    from cases.tests.test_watchers_mentions import _comment

    set_role(user_profile)
    ticket = Case.objects.create(org=org_a, name="Private")
    _comment(ticket, "@" + user_profile.user.email.split("@")[0], admin_profile)
    assert not CaseWatcher.objects.filter(case=ticket, profile=user_profile).exists()
    assert not Notification.objects.filter(
        recipient=user_profile, entity_id=ticket.pk
    ).exists()


def test_direct_save_requires_approval_but_allows_approved_close(org_a, user_profile):
    ticket = Case.objects.create(org=org_a, name="Approval guarded")
    rule = ApprovalRule.objects.create(org=org_a, name="Required")
    ticket.status = "Closed"
    ticket.closed_on = timezone.localdate()
    with pytest.raises(ModelValidationError):
        ticket.save(update_fields=["status", "closed_on"])
    ticket.refresh_from_db()
    assert ticket.status == "New"
    Approval.objects.create(
        org=org_a, case=ticket, rule=rule, requested_by=user_profile, state="approved"
    )
    ticket.status = "Closed"
    ticket.save(update_fields=["status", "closed_on"])
    Approval.objects.filter(case=ticket).delete()
    ticket.name = "Allowed edit after close"
    ticket.save()


def test_cascade_rolls_back_when_child_requires_approval(org_a, admin_client):
    parent = Case.objects.create(
        org=org_a, name="Parent", is_problem=True, priority="Low"
    )
    child = Case.objects.create(org=org_a, name="Child", parent=parent, priority="High")
    ApprovalRule.objects.create(
        org=org_a, name="High requires approval", match_priority="High"
    )
    response = admin_client.post(
        f"/api/cases/{parent.pk}/close-with-children/", {"cascade": True}, format="json"
    )
    assert response.status_code == 400, response.data
    parent.refresh_from_db()
    child.refresh_from_db()
    assert parent.status == child.status == "New"


@pytest.mark.parametrize("value", ["t", "y", "TRUE", "1", True, 1])
@pytest.mark.parametrize("method", ["patch", "put"])
def test_kb_boolean_encodings_cannot_publish(
    user_client, regular_user, org_a, value, method, monkeypatch
):
    # Exercise the dormant KB handler without changing production module availability.
    monkeypatch.setattr("common.demo_access.unavailable_in_demo", lambda path: False)
    article = Solution.objects.create(
        org=org_a,
        title="Own approved draft",
        status="approved",
        created_by=regular_user,
    )
    response = getattr(user_client, method)(
        f"/api/cases/solutions/{article.pk}/",
        {"title": article.title, "description": "Article body", "is_published": value},
        format="json",
    )
    assert response.status_code == 403, response.data
    article.refresh_from_db()
    assert not article.is_published


def test_kb_admin_can_publish_and_author_can_edit_draft(
    admin_client, user_client, regular_user, org_a, monkeypatch
):
    monkeypatch.setattr("common.demo_access.unavailable_in_demo", lambda path: False)
    article = Solution.objects.create(
        org=org_a, title="Draft", status="approved", created_by=regular_user
    )
    assert (
        user_client.patch(
            f"/api/cases/solutions/{article.pk}/",
            {"title": "Edited", "is_published": "f"},
            format="json",
        ).status_code
        == 200
    )
    assert (
        admin_client.patch(
            f"/api/cases/solutions/{article.pk}/", {"is_published": "t"}, format="json"
        ).status_code
        == 200
    )


def test_refresh_prevalidated_token_cannot_be_consumed_twice(regular_user):
    token = RefreshToken.for_user(regular_user)
    encoded = str(token)
    token.blacklist()
    # Models two workers that both validated before the first blacklist insert.
    with patch.object(RefreshToken, "check_blacklist", return_value=None):
        response = APIClient().post(
            "/api/auth/refresh-token/", {"refresh": encoded}, format="json"
        )
    assert response.status_code == 401


@pytest.mark.parametrize("credential", ["org_key", "pat"])
def test_org_key_only_lists_its_org(
    org_a, org_b, admin_profile, admin_user, admin_client, credential
):
    Profile.objects.create(org=org_b, user=admin_user, role="ADMIN")
    client = APIClient()
    if credential == "pat":
        raw, _ = PersonalAccessToken.generate(
            profile=admin_profile, name="security-test"
        )
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {raw}")
    else:
        client.credentials(HTTP_TOKEN=org_a.api_key)
    response = client.get("/api/org/")
    assert response.status_code == 200, response.data
    assert str(org_a.pk) in str(response.data)
    assert str(org_b.pk) not in str(response.data)
    assert str(org_b.pk) in str(admin_client.get("/api/org/").data)


@pytest.mark.parametrize("configured_role", [True, False])
def test_hidden_company_not_exposed_in_contact_or_deal(
    org_a, user_profile, user_client, configured_role
):
    if configured_role:
        set_role(user_profile)
    account = Account.objects.create(org=org_a, name="Secret company")
    contact = Contact.objects.create(org=org_a, first_name="Visible", account=account)
    contact.assigned_to.add(user_profile)
    deal = Opportunity.objects.create(org=org_a, name="Visible deal", account=account)
    deal.assigned_to.add(user_profile)
    for url in (
        f"/api/contacts/{contact.pk}/",
        f"/api/opportunities/{deal.pk}/",
        "/api/opportunities/kanban/",
    ):
        response = user_client.get(url)
        assert response.status_code == 200, response.data
        assert account.name not in str(response.data)
        assert str(account.pk) not in str(response.data)
    account.assigned_to.add(user_profile)
    assert account.name in str(user_client.get(f"/api/contacts/{contact.pk}/").data)


@pytest.mark.parametrize("configured_role", [True, False])
def test_tree_stops_at_hidden_parent(org_a, user_profile, user_client, configured_role):
    if configured_role:
        set_role(user_profile)
    parent = Case.objects.create(org=org_a, name="Secret parent", is_problem=True)
    child = Case.objects.create(org=org_a, name="Visible child", parent=parent)
    child.assigned_to.add(user_profile)
    for url in (f"/api/cases/{child.pk}/tree/", f"/api/cases/{child.pk}/"):
        response = user_client.get(url)
        assert response.status_code == 200, response.data
        assert str(parent.pk) not in str(response.data)
        assert parent.name not in str(response.data)
    assert user_client.get(f"/api/cases/{parent.pk}/tree/").status_code in (403, 404)
    parent.assigned_to.add(user_profile)
    assert user_client.get(f"/api/cases/{child.pk}/tree/").data["root"]["id"] == str(
        parent.pk
    )


@pytest.mark.parametrize("same", [True, False])
def test_kanban_rejects_impossible_neighbors(org_a, same):
    a = Opportunity.objects.create(org=org_a, name="a", kanban_order=Decimal(1000))
    b = Opportunity.objects.create(org=org_a, name="b", kanban_order=Decimal(2000))
    qs = Opportunity.objects.filter(org=org_a)
    with pytest.raises(ValidationError):
        place_in_column(qs, above_id=b.pk, below_id=b.pk if same else a.pk)
    assert place_in_column(qs, above_id=a.pk, below_id=b.pk) == Decimal(1500)


@pytest.mark.parametrize(
    "start,end",
    [
        (datetime(1, 1, 1, tzinfo=tz.utc), datetime(9999, 1, 1, tzinfo=tz.utc)),
        (
            datetime(9999, 12, 30, tzinfo=tz.utc),
            datetime(9999, 12, 31, 23, tzinfo=tz.utc),
        ),
        (datetime(2026, 1, 2, tzinfo=tz.utc), datetime(2026, 1, 1, tzinfo=tz.utc)),
    ],
)
def test_analytics_rejects_unbounded_or_reversed_window(start, end):
    with pytest.raises(ValidationError):
        _coerce_window(start, end)
    with pytest.raises(ValidationError):
        _bucket_dates(start, end)


def test_analytics_normal_window_remains_supported():
    end = datetime(2026, 4, 1, tzinfo=tz.utc)
    start = end - timedelta(days=30)
    assert len(_bucket_dates(*_coerce_window(start, end))) == 30


@pytest.mark.postgres_only
@pytest.mark.django_db(transaction=True)
def test_concurrent_refresh_has_one_winner():
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from django.db import connection, connections

    from common.models import User

    if connection.vendor != "postgresql":
        pytest.skip("Needs PostgreSQL unique-key concurrency semantics")
    user = User.objects.create_user(
        email="refresh-race@example.test", password="test-only"
    )
    token = RefreshToken.for_user(user)
    encoded = str(token)
    barrier = Barrier(2)
    original = RefreshToken.check_blacklist

    def validate_before_race(self):
        original(self)
        if self["jti"] == token["jti"]:
            barrier.wait(timeout=10)

    def refresh():
        try:
            return (
                APIClient()
                .post("/api/auth/refresh-token/", {"refresh": encoded}, format="json")
                .status_code
            )
        finally:
            connections.close_all()

    with patch.object(RefreshToken, "check_blacklist", validate_before_race):
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: refresh(), range(2)))
    assert sorted(results) == [200, 401]
