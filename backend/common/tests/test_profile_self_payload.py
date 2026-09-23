"""What `/api/auth/profile/` tells you about yourself, and about nobody else.

The mobile profile screen reads this endpoint and the web one reads
`/api/profile/`, so the two described the same person differently: teams and
last sign-in were on one and not the other. Both are here now, and both are
only ever the caller's own.
"""

import pytest

from common.models import Teams

URL = "/api/auth/profile/"


@pytest.mark.django_db
class TestSelfProfilePayload:
    def test_lists_the_teams_you_are_on(self, user_client, user_profile, org_a):
        team = Teams.objects.create(name="Support", org=org_a)
        team.users.add(user_profile)
        response = user_client.get(URL)
        assert response.status_code == 200
        assert response.json()["teams"] == ["Support"]

    def test_a_team_you_are_not_on_is_absent(self, user_client, admin_profile, org_a):
        team = Teams.objects.create(name="Finance", org=org_a)
        team.users.add(admin_profile)
        response = user_client.get(URL)
        assert response.json()["teams"] == []

    def test_carries_your_own_last_sign_in(self, user_client, regular_user):
        response = user_client.get(URL)
        assert "last_login" in response.json()

    def test_the_shared_profile_serializer_still_says_nothing_about_sign_ins(
        self, admin_client, user_profile
    ):
        """`ProfileSerializer` is nested into lists of OTHER people.

        Widening it the way this one was widened would publish when every
        colleague last signed in, which is why only the self endpoint carries
        it. `user_details` has always held `last_login`, and that is a
        pre-existing question, not one this change opens; what matters here is
        that the top-level field did not spread.
        """
        response = admin_client.get("/api/users/")
        assert response.status_code == 200
        rows = response.json().get("active_users", {}).get("active_users", [])
        assert all("last_login" not in row for row in rows)

    def test_unauthenticated_is_refused(self, unauthenticated_client):
        # 403 rather than 401: the middleware refuses on the missing org
        # context before DRF gets to say the caller is unauthenticated.
        assert unauthenticated_client.get(URL).status_code == 403

@pytest.mark.django_db
def test_profile_language_saved_and_validated(user_client, user_profile, admin_profile):
    response = user_client.patch('/api/profile/', {'language': 'Spanish'}, format='json')
    assert response.status_code == 200
    user_profile.refresh_from_db()
    admin_profile.refresh_from_db()
    assert user_profile.language == 'Spanish'
    assert admin_profile.language == ''
    assert user_client.get('/api/profile/').data['user_obj']['language'] == 'Spanish'
    assert user_client.patch('/api/profile/', {'language': 'Invalid'}, format='json').status_code == 400
    user_profile.refresh_from_db()
    assert user_profile.language == 'Spanish'
    assert user_client.patch('/api/profile/', {'language': ''}, format='json').status_code == 200
    user_profile.refresh_from_db()
    assert user_profile.language == ''

@pytest.mark.django_db
def test_personal_preferences_validate_and_do_not_change_org(user_client, user_profile, admin_profile, org_a):
    from common import notifications
    previous_zone = org_a.timezone
    response = user_client.patch('/api/profile/', {
        'timezone': 'America/Los_Angeles',
        'notify_in_app': True, 'notify_mentions': False, 'notify_comments': True,
        'email_integration_mode': 'send',
    }, format='json')
    assert response.status_code == 200, response.data
    user_profile.refresh_from_db()
    assert user_profile.timezone == 'America/Los_Angeles'
    assert notifications.create(user_profile, 'case.mentioned') is None
    assert notifications.create(user_profile, 'case.commented') is not None
    org_a.refresh_from_db()
    admin_profile.refresh_from_db()
    assert org_a.timezone == previous_zone and admin_profile.timezone == ''
    assert user_client.patch('/api/profile/', {'timezone':'Invalid/Zone'},format='json').status_code == 400
    assert user_client.patch('/api/profile/', {'email_integration_mode':'all'},format='json').status_code == 400
    assert user_client.patch('/api/profile/', {'notify_in_app':False},format='json').status_code == 200
    user_profile.refresh_from_db()
    assert notifications.create(user_profile, 'case.commented') is None
    own = user_client.get('/api/profile/').data['user_obj']
    assert own['notify_in_app'] is False and own['email_integration_mode'] == 'send'
    assert own['integrations']['gmail']['status'] == 'setup_required'
    assert own['integrations']['google_calendar']['email'] is None

@pytest.mark.django_db
def test_profile_photo_upload_resize_and_remove(user_client, regular_user, tmp_path, settings):
    import io
    from PIL import Image
    from django.core.files.uploadedfile import SimpleUploadedFile
    settings.MEDIA_ROOT = str(tmp_path)
    raw = io.BytesIO()
    Image.new('RGB', (900, 600), 'blue').save(raw, format='PNG')
    response = user_client.post('/api/profile/photo/', {
        'photo': SimpleUploadedFile('photo.png', raw.getvalue(), content_type='image/png')
    }, format='multipart')
    assert response.status_code == 200, response.data
    regular_user.refresh_from_db()
    assert regular_user.profile_image.name.endswith('.jpg')
    stored = regular_user.profile_image.path
    with Image.open(stored) as result:
        assert result.width == 512 and result.height <= 512
    assert user_client.get('/api/profile/').data['user_obj']['photo_url']
    response = user_client.post('/api/profile/photo/', {
        'photo': SimpleUploadedFile('fake.png', b'not an image', content_type='image/png')
    }, format='multipart')
    assert response.status_code == 400
    regular_user.refresh_from_db()
    assert regular_user.profile_image.path == stored
    assert user_client.delete('/api/profile/photo/').status_code == 200
    regular_user.refresh_from_db()
    assert not regular_user.profile_image and not regular_user.profile_pic
    from pathlib import Path
    assert not Path(stored).exists()
