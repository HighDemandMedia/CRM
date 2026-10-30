from datetime import date, datetime
from datetime import timezone as dt_timezone
from decimal import Decimal
from unittest.mock import patch

import pytest

from accounts.models import Account
from cases.models import Case
from common.models import Activity, CRMRole, SalesAppointment, Teams
from common.rbac import default_rules
from common.testing import rls_org
from contacts.models import Contact
from opportunity.models import Opportunity
from tasks.models import Task

URL = "/api/reports/crm/"
BASE = {"start": "2026-09-01", "end": "2026-09-30"}


def stamp(model, row, value, field="created_at"):
    model._base_manager.filter(pk=row.pk).update(**{field: value})


def get(client, **kwargs):
    with patch(
        "common.views.crm_report_views.timezone.now",
        return_value=datetime(2026, 10, 29, 12, tzinfo=dt_timezone.utc),
    ):
        return client.get(URL, {**BASE, **kwargs})


@pytest.mark.django_db
class TestCRMReports:
    def test_counts_previous_period_zero_buckets_and_pagination(
        self, admin_client, org_a
    ):
        for i in range(23):
            contact = Contact.objects.create(
                org=org_a, first_name=f"Contact {i}", stage="QUALIFIED"
            )
            stamp(Contact, contact, datetime(2026, 9, 4, 12, tzinfo=dt_timezone.utc))
        previous = Contact.objects.create(org=org_a, first_name="Before")
        stamp(Contact, previous, datetime(2026, 8, 14, 12, tzinfo=dt_timezone.utc))
        response = get(admin_client)
        assert response.status_code == 200, response.data
        data = response.data
        assert data["summary"]["count"] == 23
        assert data["summary"]["previous_count"] == 1
        assert data["summary"]["change_percent"] == 2200
        assert len(data["records"]) == 20 and data["pages"] == 2
        assert (
            len(data["series"]) == 30 and sum(r["count"] for r in data["series"]) == 23
        )
        assert data["group_by"] == "source"
        assert (
            next(s for s in data["state_breakdown"] if s["key"] == "QUALIFIED")["count"]
            == 23
        )
        second = get(admin_client, page=2).data
        assert len(second["records"]) == 3
        assert not {r["id"] for r in data["records"]} & {
            r["id"] for r in second["records"]
        }

    def test_currency_totals_do_not_duplicate_multiple_owners(
        self, admin_client, org_a, admin_profile, user_profile
    ):
        for currency, amount in [("USD", "100"), ("EUR", "70"), ("", "25")]:
            deal = Opportunity.objects.create(
                org=org_a,
                name="Sale",
                amount=Decimal(amount),
                currency=currency,
                stage="CLOSED_WON",
                closed_on=date(2026, 9, 30),
            )
            deal.assigned_to.set([admin_profile, user_profile])
        response = get(
            admin_client,
            object="deals",
            date_field="closed_on",
            owner=str(user_profile.pk),
        )
        assert response.status_code == 200, response.data
        assert response.data["summary"]["count"] == 3
        assert {
            r["currency"]: Decimal(r["amount"])
            for r in response.data["summary"]["amounts"]
        } == {"USD": Decimal(125), "EUR": Decimal(70)}
        assert response.data["date_label"] == "Expected close date"
        assert sum(r["count"] for r in response.data["breakdown"]) == 3

    def test_timezone_end_boundary_and_dst(self, admin_client, org_a):
        org_a.timezone = "America/New_York"
        org_a.save()
        for hour, minute in [(4, 59), (5, 0)]:
            row = Contact.objects.create(org=org_a, first_name=str(hour))
            stamp(
                Contact,
                row,
                datetime(2026, 11, 2, hour, minute, tzinfo=dt_timezone.utc),
            )
        start = Contact.objects.create(org=org_a, first_name="Start")
        stamp(Contact, start, datetime(2026, 11, 1, 4, tzinfo=dt_timezone.utc))
        response = get(admin_client, start="2026-11-01", end="2026-11-01")
        assert response.status_code == 200, response.data
        assert response.data["summary"]["count"] == 2
        assert response.data["series"] == [{"date": "2026-11-01", "count": 2}]

    def test_own_scope_denied_modules_export_and_other_org(
        self, user_client, user_profile, org_a, org_b
    ):
        rules = default_rules("own")
        rules["reports"]["view"] = "own"
        rules["deals"]["view"] = "none"
        role = CRMRole.objects.create(org=org_a, name="Restricted", rules=rules)
        user_profile.access_role = role
        user_profile.save()
        own = Contact.objects.create(org=org_a, first_name="Mine")
        own.assigned_to.add(user_profile)
        hidden = Contact.objects.create(org=org_a, first_name="Hidden")
        for row in [own, hidden]:
            stamp(Contact, row, datetime(2026, 9, 3, tzinfo=dt_timezone.utc))
        with rls_org(org_b):
            other = Contact.objects.create(org=org_b, first_name="Other tenant")
            stamp(Contact, other, datetime(2026, 9, 3, tzinfo=dt_timezone.utc))
        response = get(user_client)
        assert response.status_code == 200, response.data
        assert response.data["summary"]["count"] == 1
        assert response.data["records"][0]["name"] == "Mine"
        assert "deals" not in [r["key"] for r in response.data["objects"]]
        assert get(user_client, object="deals").status_code == 403
        assert get(user_client, download="csv").status_code == 403

    def test_team_scope_totals_not_multiplied(
        self, user_client, user_profile, admin_profile, org_a
    ):
        rules = default_rules("team")
        rules["reports"]["view"] = "team"
        role = CRMRole.objects.create(org=org_a, name="Team", rules=rules)
        user_profile.access_role = role
        user_profile.save()
        team = Teams.objects.create(org=org_a, name="Team")
        team.users.set([user_profile, admin_profile])
        record = Opportunity.objects.create(
            org=org_a,
            name="Shared",
            amount=100,
            currency="USD",
            closed_on=date(2026, 9, 1),
        )
        record.assigned_to.set([user_profile, admin_profile])
        record.teams.add(team)
        response = get(user_client, object="deals", date_field="closed_on")
        assert response.status_code == 200, response.data
        assert response.data["summary"]["count"] == 1
        assert Decimal(response.data["summary"]["amounts"][0]["amount"]) == 100

    def test_last_activity_excludes_views_and_merged_contacts(
        self, admin_client, org_a, admin_profile
    ):
        row = Contact.objects.create(org=org_a, first_name="Changed")
        stamp(Contact, row, datetime(2026, 8, 1, tzinfo=dt_timezone.utc))
        # The creation audit must share the historical record's creation date.
        creation = Activity.objects.get(
            org=org_a, entity_type="Contact", entity_id=row.pk, action="CREATE"
        )
        stamp(Activity, creation, datetime(2026, 8, 1, tzinfo=dt_timezone.utc))
        update = Activity.objects.create(
            org=org_a,
            user=admin_profile,
            entity_type="Contact",
            entity_id=row.pk,
            action="UPDATE",
        )
        stamp(Activity, update, datetime(2026, 9, 5, tzinfo=dt_timezone.utc))
        view = Activity.objects.create(
            org=org_a,
            user=admin_profile,
            entity_type="Contact",
            entity_id=row.pk,
            action="VIEW",
        )
        stamp(Activity, view, datetime(2026, 10, 5, tzinfo=dt_timezone.utc))
        merged = Contact.objects.create(org=org_a, first_name="Merged")
        stamp(Contact, merged, datetime(2026, 9, 5, tzinfo=dt_timezone.utc))
        stamp(
            Contact, merged, datetime(2026, 9, 6, tzinfo=dt_timezone.utc), "merged_at"
        )
        response = get(admin_client, date_field="last_activity_at")
        assert response.status_code == 200, response.data
        assert response.data["summary"]["count"] == 1
        assert response.data["records"][0]["id"] == str(row.pk)

    def test_events_count_once_and_cancelled_preserved(
        self, admin_client, user_client, org_a, admin_profile, user_profile, admin_user
    ):
        event = SalesAppointment.objects.create(
            org=org_a,
            title="Meeting",
            host=admin_profile,
            created_by=admin_user,
            starts_at=datetime(2026, 9, 5, 12, tzinfo=dt_timezone.utc),
            ends_at=datetime(2026, 9, 5, 13, tzinfo=dt_timezone.utc),
        )
        event.attendee_users.set([admin_profile, user_profile])
        event.cancelled_at = datetime(2026, 9, 4, tzinfo=dt_timezone.utc)
        event.save()
        response = get(user_client, object="events")
        assert response.status_code == 200, response.data
        assert response.data["summary"]["count"] == 1
        assert response.data["summary"]["statuses"] == {"Cancelled": 1}
        assert (
            get(admin_client, object="events", stage="scheduled").data["summary"][
                "count"
            ]
            == 0
        )
        event.attendee_users.clear()
        assert get(user_client, object="events").data["summary"]["count"] == 0

    @pytest.mark.parametrize(
        "object,model,values,date_field",
        [
            ("companies", Account, {"name": "Company"}, "created_at"),
            (
                "tasks",
                Task,
                {"title": "Task", "due_date": date(2026, 9, 8)},
                "due_date",
            ),
            (
                "tickets",
                Case,
                {
                    "name": "Ticket",
                    "resolved_at": datetime(2026, 9, 8, tzinfo=dt_timezone.utc),
                },
                "resolved_at",
            ),
        ],
    )
    def test_other_objects(
        self, admin_client, org_a, object, model, values, date_field
    ):
        row = model.objects.create(org=org_a, **values)
        stamp(model, row, datetime(2026, 9, 8, tzinfo=dt_timezone.utc))
        response = get(
            admin_client, object=object, date_field=date_field, interval="week"
        )
        assert response.status_code == 200, response.data
        assert response.data["summary"]["count"] == 1
        assert sum(r["count"] for r in response.data["series"]) == 1

    def test_csv_complete_not_just_current_page_and_safe(self, admin_client, org_a):
        org_a.pipeline_settings = {
            "Contact": [
                {"key": "LEAD", "label": "=FORMULA", "order": 0, "percentage": 0}
            ]
        }
        org_a.save()
        for i in range(21):
            row = Contact.objects.create(org=org_a, first_name=f"Row {i}")
            stamp(Contact, row, datetime(2026, 9, 3, tzinfo=dt_timezone.utc))
        response = get(admin_client, download="csv", group_by="stage")
        assert response.status_code == 200
        text = response.content.decode("utf-8-sig")
        assert "Records,21" in text
        assert "'=FORMULA,21" in text
        assert "Timezone," in text
        assert response["Cache-Control"] == "private, no-store"

    @pytest.mark.parametrize(
        "params",
        [
            {"start": "oops"},
            {"end": "2026-08-01"},
            {"object": "x"},
            {"date_field": "org__created_at"},
            {"group_by": "created_by__email"},
            {"owner": "bad-id"},
            {"stage": "bad"},
            {"page": "-1"},
            {"start": "2000-01-01"},
            {"start": "2024-01-01", "interval": "day"},
        ],
    )
    def test_bad_parameters(self, admin_client, params):
        assert get(admin_client, **params).status_code == 400

    def test_auth_required(self, unauthenticated_client):
        assert get(unauthenticated_client).status_code in (401, 403)

    @pytest.mark.parametrize(
        "key,model,fields",
        [
            ("contacts", Contact, {"first_name": "Selected"}),
            ("companies", Account, {"name": "Selected"}),
        ],
    )
    def test_qualification_metrics_exclude_merged_and_respect_owner(
        self, admin_client, org_a, admin_profile, user_profile, key, model, fields
    ):
        rows = [
            model.objects.create(org=org_a, **fields, stage=stage)
            for stage in ("QUALIFIED", "FOLLOW_UP", "LEAD")
        ]
        for row in rows:
            stamp(model, row, datetime(2026, 9, 4, tzinfo=dt_timezone.utc))
        rows[0].assigned_to.set([admin_profile, user_profile])
        stamp(model, rows[2], datetime(2026, 9, 5, tzinfo=dt_timezone.utc), "merged_at")
        report = get(admin_client, object=key).data
        values = {item["key"]: item["value"] for item in report["metrics"]}
        assert report["summary"]["count"] == 2
        assert values == {"qualified": 50, "follow_up": 1, "unassigned": 1}
        filtered = get(admin_client, object=key, owner=str(admin_profile.pk)).data
        assert filtered["summary"]["count"] == 1
        assert filtered["metrics"][0]["value"] == 100
        assert filtered["metrics"][2]["value"] == 0

    def test_deal_metrics_keep_currency_and_closed_denominator(
        self, admin_client, org_a
    ):
        for stage, amount, currency in [
            ("CLOSED_WON", 100, "USD"),
            ("CLOSED_LOST", 50, "USD"),
            ("PROSPECTING", 70, "EUR"),
        ]:
            row = Opportunity.objects.create(
                org=org_a,
                name=stage,
                stage=stage,
                amount=amount,
                currency=currency,
                closed_on=date(2026, 9, 2),
            )
            stamp(Opportunity, row, datetime(2026, 9, 4, tzinfo=dt_timezone.utc))
        response = get(admin_client, object="deals")
        assert response.status_code == 200, response.data
        values = {item["key"]: item for item in response.data["metrics"]}
        assert values["win_rate"]["value"] == 50
        assert values["overdue"]["value"] == 1
        assert values["open_value"]["amounts"] == [
            {"currency": "EUR", "amount": "70", "count": 1}
        ]
        assert values["won_value"]["amounts"] == [
            {"currency": "USD", "amount": "100", "count": 1}
        ]
        assert (
            get(admin_client, object="deals", stage="PROSPECTING").data["metrics"][2][
                "value"
            ]
            is None
        )

    def test_task_metrics_exclude_completed_from_overdue(self, admin_client, org_a):
        for status, due in [
            ("Completed", date(2026, 9, 1)),
            ("New", date(2026, 9, 1)),
            ("New", None),
        ]:
            row = Task.objects.create(
                org=org_a, title="Report task", status=status, due_date=due
            )
            stamp(Task, row, datetime(2026, 9, 4, tzinfo=dt_timezone.utc))
        report = get(admin_client, object="tasks").data
        values = {item["key"]: item["value"] for item in report["metrics"]}
        assert values == {"completion": 33.3, "overdue": 1, "unassigned": 3}

    @pytest.mark.parametrize("resolved_hour, expected", [(16, 4), (12, 0)])
    def test_ticket_resolution_ignores_missing_negative_and_reopened(
        self, admin_client, org_a, resolved_hour, expected
    ):
        created = datetime(2026, 9, 4, 12, tzinfo=dt_timezone.utc)
        due = datetime(2026, 9, 5, 12, tzinfo=dt_timezone.utc)
        for status, hour in [
            ("Resolved", resolved_hour),
            ("Closed", None),
            ("Resolved", 10),
            ("New", 18),
        ]:
            row = Case.objects.create(
                org=org_a, name="Report ticket", status=status, due_at=due
            )
            Case._base_manager.filter(pk=row.pk).update(
                created_at=created,
                resolved_at=created.replace(hour=hour) if hour is not None else None,
            )
        report = get(admin_client, object="tickets").data
        values = {item["key"]: item["value"] for item in report["metrics"]}
        assert values == {"active": 1, "overdue": 1, "resolution": expected}

    def test_event_metrics_exclude_cancelled_duration(
        self, admin_client, org_a, admin_profile, admin_user
    ):
        for cancelled in (False, True):
            SalesAppointment.objects.create(
                org=org_a,
                host=admin_profile,
                created_by=admin_user,
                title="Report event",
                starts_at=datetime(2026, 9, 4, 12, tzinfo=dt_timezone.utc),
                ends_at=datetime(2026, 9, 4, 14, tzinfo=dt_timezone.utc),
                cancelled_at=datetime(2026, 9, 3, tzinfo=dt_timezone.utc)
                if cancelled
                else None,
            )
        report = get(admin_client, object="events").data
        values = {item["key"]: item["value"] for item in report["metrics"]}
        assert values == {"upcoming": 0, "cancelled": 50, "hours": 2}

    @pytest.mark.parametrize(
        "key", ["contacts", "companies", "deals", "tasks", "tickets", "events"]
    )
    def test_empty_metric_rates_are_not_zero(self, admin_client, key):
        response = get(admin_client, object=key)
        assert response.status_code == 200, response.data
        for item in response.data["metrics"]:
            if item["unit"] == "percent":
                assert item["value"] is None
