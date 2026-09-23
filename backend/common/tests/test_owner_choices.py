import pytest

@pytest.mark.django_db
@pytest.mark.parametrize('endpoint',['/api/contacts/','/api/accounts/','/api/cases/'])
def test_owner_choices_include_saved_name(admin_client, user_profile, endpoint):
    user_profile.user.name = 'Saved Display Name'
    user_profile.user.save()
    response = admin_client.get(endpoint)
    assert response.status_code == 200
    row = next(row for row in response.data['users'] if str(row['id']) == str(user_profile.pk))
    assert row['user__name'] == 'Saved Display Name'
