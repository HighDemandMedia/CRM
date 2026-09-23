from datetime import timedelta, datetime, time
import pytest
from django.utils import timezone
from common.models import Profile, SalesAppointment
from tasks.models import Task
from cases.models import Case
from opportunity.models import Opportunity

pytestmark = pytest.mark.django_db
URL = '/api/dashboard/day-summary/'

def test_counts_and_terminal_states(admin_client, admin_user, org_a):
    today=timezone.localdate()
    Task.objects.create(org=org_a,created_by=admin_user,title='Due',status='New',priority='High',due_date=today)
    Task.objects.create(org=org_a,created_by=admin_user,title='Late',status='In Progress',priority='High',due_date=today-timedelta(days=1))
    Task.objects.create(org=org_a,created_by=admin_user,title='Done',status='Completed',priority='High',due_date=today)
    Opportunity.objects.create(org=org_a,created_by=admin_user,name='Late deal',stage='PROPOSAL',closed_on=today-timedelta(days=2))
    Opportunity.objects.create(org=org_a,created_by=admin_user,name='Won',stage='CLOSED_WON',closed_on=today)
    Case.objects.create(org=org_a,created_by=admin_user,name='Late ticket',status='New',due_at=timezone.now()-timedelta(days=2))
    response=admin_client.get(URL)
    assert response.status_code==200
    assert response.data['counts']['tasks_today']==1
    assert response.data['counts']['overdue']==3
    assert [row['name'] for row in response.data['tasks']]==['Late','Due']
    assert response.data['counts']['deals']==1


def test_no_foreign_org_data(admin_client, org_b, admin_user):
    Task.objects.create(org=org_b,created_by=admin_user,title='Secret',status='New',priority='High',due_date=timezone.localdate())
    assert admin_client.get(URL,{'user':'all'}).data['tasks']==[]


def test_member_cannot_select_team_or_other_user(user_client, admin_profile):
    other=admin_profile
    assert user_client.get(URL,{'user':'all'}).status_code==403
    assert user_client.get(URL,{'user':str(other.pk)}).status_code==403


def test_event_day_boundaries_and_cancellation(admin_client, admin_user, org_a):
    host=Profile.objects.get(org=org_a,user=admin_user)
    start=timezone.make_aware(datetime.combine(timezone.localdate(), time.min))
    for i,(first,last,cancelled) in enumerate([(start-timedelta(hours=1),start+timedelta(minutes=20),None),(start+timedelta(hours=9),start+timedelta(hours=10),timezone.now()),(start+timedelta(days=1),start+timedelta(days=1,hours=1),None)]):
        SalesAppointment.objects.create(org=org_a,created_by=admin_user,host=host,title=f'Event {i}',starts_at=first,ends_at=last,cancelled_at=cancelled)
    data=admin_client.get(URL).data
    assert data['counts']['events']==1
    assert data['events'][0]['title']=='Event 0'


def test_admin_defaults_to_own_tasks_and_can_choose_team(admin_client, regular_user, org_a):
    Task.objects.create(org=org_a,created_by=regular_user,title='Colleague task',status='New',priority='Low',due_date=timezone.localdate())
    assert admin_client.get(URL).data['counts']['tasks']==0
    assert admin_client.get(URL,{'user':'all'}).data['counts']['tasks']==1


def test_task_reminder_window_and_completion(admin_client, admin_user, org_a):
    today = timezone.localdate()
    def task(name, days, reminder, status='New'):
        return Task.objects.create(org=org_a, created_by=admin_user, title=name, status=status, priority='Medium', due_date=today+timedelta(days=days), reminder_days=reminder)
    ready = task('Prepare tomorrow', 1, 1)
    task('Too early', 3, 1)
    task('Disabled', 1, None)
    task('Finished', 1, 1, 'Completed')
    task('Due today', 0, 0)
    response = admin_client.get(URL).data
    assert [row['id'] for row in response['reminders']] == [str(ready.pk)]
    assert response['counts']['reminders'] == 1
    assert response['counts']['tasks_today'] == 1
    ready.due_date = today + timedelta(days=4)
    ready.save()
    assert admin_client.get(URL).data['reminders'] == []


def test_reminders_follow_owner_and_org(admin_client, user_client, admin_user, regular_user, org_a, org_b):
    due = timezone.localdate()+timedelta(days=1)
    Task.objects.create(org=org_b,created_by=admin_user,title='Other org',status='New',priority='Low',due_date=due,reminder_days=1)
    own = Task.objects.create(org=org_a,created_by=admin_user,title='Assigned elsewhere',status='New',priority='Low',due_date=due,reminder_days=1)
    own.assigned_to.add(Profile.objects.get(user=regular_user, org=org_a))
    assert admin_client.get(URL).data['reminders'] == []
    assert len(admin_client.get(URL, {'user':'all'}).data['reminders']) == 1


def test_task_reminder_api_validation_and_roundtrip(admin_client):
    response = admin_client.post('/api/tasks/', {'title':'Reminder validation','status':'New','priority':'Low','reminder_days':1}, format='json')
    assert response.status_code == 400
    response = admin_client.post('/api/tasks/', {'title':'Reminder saved','status':'New','priority':'Low','due_date':timezone.localdate().isoformat(),'reminder_days':0}, format='json')
    assert response.status_code in (200,201)
    task = Task.objects.get(title='Reminder saved')
    assert task.reminder_days == 0
    url = f'/api/tasks/{task.pk}/'
    assert admin_client.patch(url, {'reminder_days':366}, format='json').status_code == 400
    assert admin_client.patch(url, {'due_date':None}, format='json').status_code == 400
    assert admin_client.patch(url, {'reminder_days':None,'due_date':None}, format='json').status_code == 200
    task.refresh_from_db()
    assert task.reminder_days is None


def test_custom_reminder_window(admin_client, admin_user, org_a):
    today = timezone.localdate()
    for days, lead in [(10, 10), (11, 10), (7, 7), (364, 365)]:
        Task.objects.create(org=org_a, created_by=admin_user, title=f"Custom {days}", status="New", priority="Low", due_date=today+timedelta(days=days), reminder_days=lead)
    assert {row['name'] for row in admin_client.get(URL).data['reminders']} == {'Custom 10', 'Custom 7', 'Custom 364'}
