from unittest.mock import patch
import pytest
from django.apps import apps
from common.models import Org, Profile, PersonalAccessToken, Teams
from common.views.member_removal_views import RECORDS
from common.rbac import default_rules
from common.models import CRMRole

pytestmark=pytest.mark.django_db

def endpoint(member): return f'/api/members/{member.pk}/remove/'

def test_self_creator_and_non_admin_removal_are_blocked(admin_client, admin_profile, user_client, user_profile, org_a):
    assert admin_client.get(endpoint(admin_profile)).status_code == 403
    assert user_client.get(endpoint(admin_profile)).status_code == 403
    Org.objects.filter(pk=org_a.pk).update(owner=user_profile.user)
    assert admin_client.get(endpoint(user_profile)).status_code == 403
    assert admin_client.post(endpoint(user_profile), {'token':'invalid','confirmation':user_profile.user.email}, format='json').status_code == 403
    user_profile.refresh_from_db()
    assert user_profile.is_active and user_profile.removed_at is None


def test_changed_assignments_require_new_confirmation(admin_client, user_profile, org_a):
    preview=admin_client.get(endpoint(user_profile)).data
    record=apps.get_model('contacts','Contact').objects.create(org=org_a,first_name='New assignment')
    record.assigned_to.add(user_profile)
    response=admin_client.post(endpoint(user_profile),{'token':preview['token'],'confirmation':user_profile.user.email},format='json')
    assert response.status_code == 409
    user_profile.refresh_from_db()
    assert user_profile.is_active and record.assigned_to.filter(pk=user_profile.pk).exists()

def test_admin_cannot_manage_peer_or_promote(admin_client, user_profile):
    response=admin_client.post(f'/api/roles/members/{user_profile.pk}/',{'role_id':'ADMIN'},format='json')
    assert response.status_code==403
    assert admin_client.post('/api/invitations/',{'email':'newadmin@example.com','role':'ADMIN'},format='json').status_code==403
    assert admin_client.post('/api/users/',{'email':'legacyadmin@example.com','role':'ADMIN'},format='json').status_code==403
    user_profile.role='ADMIN';user_profile.save()
    role=CRMRole.objects.create(org=user_profile.org,name='Test member',rules=default_rules())
    assert admin_client.post(f'/api/roles/members/{user_profile.pk}/',{'role_id':str(role.pk)},format='json').status_code==403
    assert admin_client.patch(f'/api/user/{user_profile.user_id}/',{'role':'USER'},format='json').status_code==403
    assert admin_client.post(f'/api/user/{user_profile.user_id}/status/',{'status':'Inactive'},format='json').status_code==403
    assert admin_client.get(endpoint(user_profile)).status_code==403


def test_super_admin_can_manage_admin(admin_client, admin_profile, user_profile, org_a):
    Org.objects.filter(pk=org_a.pk).update(owner=admin_profile.user)
    user_profile.role='ADMIN';user_profile.save()
    response=admin_client.get(endpoint(user_profile))
    assert response.status_code==200, response.data
    result=admin_client.post(endpoint(user_profile),{'token':response.data['token'],'confirmation':user_profile.user.email},format='json')
    assert result.status_code==200, result.data
    user_profile.refresh_from_db()
    assert user_profile.removed_at and not user_profile.is_active


@pytest.mark.parametrize('reassign',[True,False])
def test_remove_retains_history_and_other_organization(admin_client, admin_profile, user_client, user_profile, org_a, org_b, reassign):
    other=Profile.objects.create(org=org_b,user=user_profile.user,role='USER',is_active=True)
    team=Teams.objects.create(org=org_a,name='Sales');team.users.add(user_profile)
    _,pat=PersonalAccessToken.generate(user_profile,'test')
    records=[]
    for model in RECORDS:
        cls=apps.get_model(model)
        kwargs={'title':'Retained'} if model=='tasks.task' else {'first_name':'Retained'} if model=='contacts.contact' else {'name':'Retained'}
        if model in ('tasks.task','cases.case'):
            for field in ('status','priority'):
                kwargs[field]=cls._meta.get_field(field).choices[0][0]
        record=cls.objects.create(org=org_a,created_by=user_profile.user,**kwargs)
        record.assigned_to.add(user_profile)
        records.append(record)
    response=admin_client.get(endpoint(user_profile))
    assert response.status_code==200, response.data
    assert all(count==1 for count in response.data['counts'].values())
    result=admin_client.post(endpoint(user_profile),{'token':response.data['token'],'confirmation':user_profile.user.email,'reassign_to':str(admin_profile.pk) if reassign else None},format='json')
    assert result.status_code==200, result.data
    user_profile.refresh_from_db();other.refresh_from_db();pat.refresh_from_db()
    assert user_profile.removed_at and not user_profile.is_active and other.is_active
    assert pat.revoked_at and not team.users.filter(pk=user_profile.pk).exists()
    for record in records:
        record.refresh_from_db()
        assert record.created_by_id==user_profile.user_id
        assert not record.assigned_to.filter(pk=user_profile.pk).exists()
        assert record.assigned_to.filter(pk=admin_profile.pk).exists()==reassign
    assert user_client.get('/api/contacts/').status_code in (401,403)
    assert user_profile.user.email not in str(admin_client.get('/api/users/').data)


def test_removal_confirmation_and_cross_org_target(admin_client,user_profile,profile_b):
    response=admin_client.get(endpoint(user_profile))
    assert admin_client.post(endpoint(user_profile),{'token':response.data['token'],'confirmation':'wrong'},format='json').status_code==400
    assert admin_client.post(endpoint(user_profile),{'token':response.data['token'],'confirmation':user_profile.user.email,'reassign_to':str(profile_b.pk)},format='json').status_code==404
    assert admin_client.get(endpoint(profile_b)).status_code==404
    user_profile.refresh_from_db();assert user_profile.is_active


def test_removed_member_can_only_return_by_new_invitation(admin_client,user_client,user_profile):
    response=admin_client.get(endpoint(user_profile))
    assert admin_client.post(endpoint(user_profile),{'token':response.data['token'],'confirmation':user_profile.user.email},format='json').status_code==200
    assert admin_client.post(f'/api/user/{user_profile.user_id}/status/',{'status':'Active'},format='json').status_code==404
    with patch('common.views.invitation_views.send_mail') as mail:
        result=admin_client.post('/api/invitations/',{'email':user_profile.user.email,'role':'USER'},format='json')
    assert result.status_code==201, result.data
    token=mail.call_args.args[1].split('token=')[1].split('\n')[0]
    result=user_client.post('/api/auth/accept-invitation/',{'token':token},format='json')
    assert result.status_code==200, result.data
    user_profile.refresh_from_db()
    assert user_profile.removed_at is None and user_profile.is_active
