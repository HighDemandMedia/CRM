from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone

from common.models import OrganizationInvitation, Profile, Teams
from common.views.invitation_views import digest

pytestmark = pytest.mark.django_db


def test_invite_pending_until_matching_authenticated_accept(
    admin_client, user_client, regular_user, org_a
):
    # Use a verified existing identity with no membership to exercise first-org joining.
    Profile.objects.filter(user=regular_user, org=org_a).delete()
    with patch("common.views.invitation_views.send_mail") as mail:
        response = admin_client.post(
            "/api/invitations/",
            {"email": regular_user.email, "role": "USER"},
            format="json",
        )
    assert response.status_code == 201
    assert not Profile.objects.filter(user=regular_user, org=org_a).exists()
    link = mail.call_args.args[1].split("token=")[1].split("\n")[0]
    assert OrganizationInvitation.objects.get().token_hash == digest(link)
    preview = user_client.post(
        "/api/auth/accept-invitation/", {"token": link, "preview": True}, format="json"
    )
    assert preview.status_code == 200
    assert not Profile.objects.filter(user=regular_user, org=org_a).exists()
    accepted = user_client.post(
        "/api/auth/accept-invitation/", {"token": link}, format="json"
    )
    assert accepted.status_code == 200
    assert Profile.objects.get(user=regular_user, org=org_a).role == "USER"
    assert (
        user_client.post(
            "/api/auth/accept-invitation/", {"token": link}, format="json"
        ).status_code
        == 400
    )


def test_invite_cannot_be_accepted_by_other_email(
    admin_client, user_client, org_a, admin_user
):
    row = OrganizationInvitation.objects.create(
        org=org_a,
        email="someone@example.com",
        token_hash=digest("x" * 32),
        invited_by=admin_user,
        expires_at=timezone.now() + timedelta(days=1),
    )
    assert (
        user_client.post(
            "/api/auth/accept-invitation/", {"token": "x" * 32}, format="json"
        ).status_code
        == 403
    )
    assert user_client.get("/api/invitations/").status_code == 403
    assert user_client.delete(f"/api/invitations/{row.pk}/").status_code == 403


def test_expired_and_cancelled_invites_fail(
    admin_client, user_client, regular_user, org_a
):
    row = OrganizationInvitation.objects.create(
        org=org_a,
        email=regular_user.email,
        token_hash=digest("a" * 32),
        expires_at=timezone.now() - timedelta(seconds=1),
    )
    assert (
        user_client.post(
            "/api/auth/accept-invitation/", {"token": "a" * 32}, format="json"
        ).status_code
        == 400
    )
    row.expires_at = timezone.now() + timedelta(days=1)
    row.revoked_at = timezone.now()
    row.save()
    assert (
        user_client.post(
            "/api/auth/accept-invitation/", {"token": "a" * 32}, format="json"
        ).status_code
        == 400
    )


def test_resend_invalidates_previous_link_and_scope(admin_client, org_b_client, org_a):
    with patch("common.views.invitation_views.send_mail"):
        first = admin_client.post(
            "/api/invitations/", {"email": "new@example.com"}, format="json"
        )
        old = OrganizationInvitation.objects.get().token_hash
        second = admin_client.post(
            "/api/invitations/", {"email": "new@example.com"}, format="json"
        )
    assert first.status_code == second.status_code == 201
    assert OrganizationInvitation.objects.count() == 1
    assert OrganizationInvitation.objects.get().token_hash != old
    assert org_b_client.get("/api/invitations/").data["invitations"] == []
    assert (
        org_b_client.delete(f"/api/invitations/{first.data['id']}/").status_code == 404
    )
    assert (
        admin_client.delete(f"/api/invitations/{first.data['id']}/").status_code == 200
    )


def test_failed_mail_is_not_reported_as_delivered(admin_client):
    with patch(
        "common.views.invitation_views.send_mail", side_effect=OSError("offline")
    ):
        assert (
            admin_client.post(
                "/api/invitations/", {"email": "new@example.com"}, format="json"
            ).status_code
            == 503
        )
    assert OrganizationInvitation.objects.count() == 1


def test_team_membership_patch_is_atomic_and_scoped(
    admin_client, admin_profile, user_client, regular_user, org_a, profile_b
):
    response = admin_client.post(
        "/api/teams/",
        {"name": "Sales", "assign_users": [str(admin_profile.pk)]},
        format="json",
    )
    assert response.status_code == 200
    team = Teams.objects.get(name="Sales")
    assert list(team.users.all()) == [admin_profile]
    assert (
        admin_client.patch(
            f"/api/teams/{team.pk}/",
            {"assign_users": [str(profile_b.pk)]},
            format="json",
        ).status_code
        == 400
    )
    assert list(team.users.all()) == [admin_profile]
    assert (
        user_client.patch(
            f"/api/teams/{team.pk}/", {"assign_users": []}, format="json"
        ).status_code
        == 403
    )
    assert (
        admin_client.patch(
            f"/api/teams/{team.pk}/", {"description": "Renamed"}, format="json"
        ).status_code
        == 200
    )
    assert list(team.users.all()) == [admin_profile]
    assert (
        admin_client.patch(
            f"/api/teams/{team.pk}/", {"assign_users": []}, format="json"
        ).status_code
        == 200
    )
    assert not team.users.exists()
