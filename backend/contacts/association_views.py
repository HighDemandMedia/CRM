from common.rbac import configured
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.response import Response
from accounts.models import Account
from opportunity.models import Opportunity
from common.permissions import is_org_admin
from contacts.views import ContactDetailView


class ContactAssociationView(ContactDetailView):
    http_method_names = ["get", "post", "head", "options"]
    def targets(self, kind):
        model = {'company': Account, 'deal': Opportunity}.get(kind)
        if not model:
            raise serializers.ValidationError('Invalid association type.')
        rows = model.objects.filter(org=self.request.profile.org, is_active=True)
        if not configured(self.request.profile) and not is_org_admin(self.request.profile):
            rows = rows.filter(Q(assigned_to=self.request.profile) | Q(created_by=self.request.user)).distinct()
        return rows

    def get(self, request, pk):
        contact = self.get_object(pk)
        self.assert_contact_access(contact)
        kind = request.query_params.get('kind')
        rows = self.targets(kind)
        search = request.query_params.get('search', '').strip()[:255]
        if search:
            rows = rows.filter(name__icontains=search)
        rows = rows.exclude(contacts=contact)
        if kind == 'company' and contact.account_id:
            rows = rows.exclude(pk=contact.account_id)
        return Response({'results': list(rows.order_by('name','id').values('id','name')[:30])})

    @transaction.atomic
    def post(self, request, pk):
        contact = self.get_object(pk)
        self.assert_contact_access(contact)
        # Serialize association edits for this contact without replacing other members.
        contact = type(contact).objects.select_for_update().get(pk=contact.pk)
        kind = request.data.get('kind')
        action = request.data.get('operation')
        if action not in ('add','remove'):
            raise serializers.ValidationError('Invalid association action.')
        target_id = serializers.UUIDField().run_validation(request.data.get('target'))
        target = get_object_or_404(self.targets(kind), pk=target_id)
        if action == 'add':
            target.contacts.add(contact)
        else:
            if kind == 'company' and contact.account_id == target.pk:
                contact.account = None
                contact.save(update_fields=['account','updated_at'])
            target.contacts.remove(contact)
        return Response({'saved': True})
