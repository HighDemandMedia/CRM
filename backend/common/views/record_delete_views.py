from django.core import signing
from django.db import transaction
from django.db.models import Q
from django.db.models.deletion import Collector, ProtectedError, RestrictedError
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from common.permissions import HasOrgContext, is_org_admin
from accounts.models import Account
from contacts.models import Contact
from opportunity.models import Opportunity
from invoices.models import Invoice, Estimate, RecurringInvoice
import hashlib
import json

MODELS={'company':Account,'contact':Contact,'deal':Opportunity}

class ExplicitRecordCollector(Collector):
    """Detach company deals unless explicitly included in the confirmed selection."""
    def __init__(self, *args, selected_deals, **kwargs):
        super().__init__(*args, **kwargs)
        self.selected_deals = selected_deals

    def related_objects(self, related_model, related_fields, objs):
        rows = super().related_objects(related_model, related_fields, objs)
        # Billing documents keep their stored client details; only detach the CRM link.
        if related_model in (Invoice, Estimate, RecurringInvoice):
            account = related_model._meta.get_field('account')
            if account in related_fields:
                self.add_field_update(account, None, rows)
                return rows.none()
        if related_model is Opportunity:
            account = Opportunity._meta.get_field('account')
            if account in related_fields:
                self.add_field_update(account, None, rows.exclude(pk__in=self.selected_deals))
                return rows.filter(pk__in=self.selected_deals)
        return rows


class RecordDeleteView(APIView):
    permission_classes=(IsAuthenticated,HasOrgContext)

    def record(self,kind,pk,lock=False):
        if kind not in MODELS: raise serializers.ValidationError('Invalid record type.')
        rows=MODELS[kind].objects.filter(org=self.request.profile.org)
        if lock: rows=rows.select_for_update()
        record=get_object_or_404(rows,pk=pk)
        if not is_org_admin(self.request.profile) and record.created_by_id!=self.request.user.pk:
            raise PermissionDenied('Only an administrator or the record creator can delete this record.')
        return record

    def associated(self, record):
        org = record.org
        if isinstance(record, Account):
            contacts = Contact.objects.filter(Q(account=record) | Q(account_contacts=record), org=org)
            deals = Opportunity.objects.filter(account=record, org=org)
            companies = Account.objects.none()
        elif isinstance(record, Contact):
            companies = Account.objects.filter(Q(pk=record.account_id) | Q(contacts=record), org=org)
            deals = Opportunity.objects.filter(contacts=record, org=org)
            contacts = Contact.objects.none()
        else:
            companies = Account.objects.filter(pk=record.account_id, org=org)
            contacts = record.contacts.filter(org=org)
            deals = Opportunity.objects.none()
        return list(companies.distinct()) + list(contacts.distinct()) + list(deals.distinct())

    def impact(self, record, include_associated=False):
        associated = self.associated(record)
        selected = [record] + (associated if include_associated else [])
        if any(not is_org_admin(self.request.profile) and obj.created_by_id != self.request.user.pk for obj in selected):
            return None, {'blocked': True, 'message': 'You do not have permission to delete all associated records.'}
        collector = ExplicitRecordCollector(using=record._state.db, selected_deals=[obj.pk for obj in selected if isinstance(obj, Opportunity)])
        try:
            for model in MODELS.values():
                objects = [obj for obj in selected if isinstance(obj, model)]
                if objects:
                    collector.collect(objects)
        except (ProtectedError, RestrictedError):
            return None, {'blocked': True, 'message': 'This selection contains a relationship that cannot be detached.'}
        groups={}
        for model,objects in collector.data.items():
            groups.setdefault(model,set()).update(str(obj.pk) for obj in objects)
        for query in collector.fast_deletes:
            groups.setdefault(query.model,set()).update(str(pk) for pk in query.values_list('pk',flat=True))
        # Internal join rows are links, not separate customer records.
        labels={'accounts.account':'Companies','contacts.contact':'Contacts','opportunity.opportunity':'Deals','common.comment':'Notes','common.attachments':'Attachments'}
        counts=[{'label':labels.get(model._meta.label_lower,str(model._meta.verbose_name_plural).capitalize()),'count':len(ids)} for model,ids in groups.items() if not model._meta.auto_created and ids]
        fingerprint=hashlib.sha256(json.dumps([sorted((model._meta.label_lower,sorted(ids)) for model,ids in groups.items()), sorted((obj._meta.label_lower,str(obj.pk)) for obj in associated)]).encode()).hexdigest()
        return collector, {'blocked':False,'counts':counts,'fingerprint':fingerprint, 'associated': [{'kind': next(k for k,m in MODELS.items() if isinstance(obj,m)), 'name': obj.name or str(obj.pk)} for obj in associated]}

    def get(self,request,kind,pk):
        record=self.record(kind,pk)
        include = request.query_params.get('include_associated') == 'true'
        _,impact=self.impact(record, include)
        payload={'name':record.name,'id':str(record.pk),**impact}
        if not impact['blocked']:
            payload['token']=signing.dumps({'kind':kind,'id':str(pk),'name':record.name,'fingerprint':impact['fingerprint'],'user':str(request.user.pk),'include_associated':include},salt='record-delete')
        return Response(payload)

    @transaction.atomic
    def post(self,request,kind,pk):
        record=self.record(kind,pk,True)
        try: preview=signing.loads(request.data.get('token',''),salt='record-delete',max_age=900)
        except signing.BadSignature: raise serializers.ValidationError('The confirmation expired. Close this dialog and try again.')
        if any(preview.get(k)!=v for k,v in {'kind':kind,'id':str(pk),'user':str(request.user.pk),'name':record.name}.items()):
            raise serializers.ValidationError('The record changed. Close this dialog and review it again.')
        expected=record.name or str(record.pk)
        if request.data.get('confirmation')!=expected:
            raise serializers.ValidationError('The confirmation must match exactly.')
        collector,impact=self.impact(record, preview.get('include_associated', False))
        if impact['blocked']: return Response(impact,status=409)
        if impact['fingerprint']!=preview['fingerprint']:
            return Response({'message':'The linked records changed. Close this dialog and review the consequences again.'},status=409)
        collector.delete()
        return Response({'deleted':True})
