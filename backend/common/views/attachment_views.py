"""Downloading a file attached to a record.

`Attachments` is generic: one table hangs off leads, deals, contacts,
accounts, tickets, tasks and invoices through a ContentType. Until this view
existed there was no authenticated way to fetch the bytes, so every client
built the file's `/media/` path instead and offered that as the download.
That path is guarded by `RLSContextMiddleware` alone, which requires *an* org
context rather than *the* org, so it refuses an anonymous caller and waves
through every authenticated one, of any tenant. It also refuses the ordinary
case, because a link opened in the phone's browser or a plain `<a href>` from
the web app carries no Authorization header at all. Both clients were
therefore offering a download that could not work and, where it did work,
worked for the wrong people.

**Reading an attachment is reading the record it hangs off**, so this view
asks that record's own read predicate rather than inventing a second one.
Every one of the seven predicates below already exists and is already used by
that model's detail view. A content type not in the map is refused: a new
attachable model must opt in here deliberately, because the failure mode of
the other default is handing out somebody's file.
"""

import logging

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common import swagger_params
from common.models import Attachments
from common.permissions import HasOrgContext

logger = logging.getLogger(__name__)


def _readers():
    """content_type.model -> a predicate answering "may this caller read it".

    Built lazily inside the function because these modules import from
    `common`, and importing them at `common.views` module level would close
    the circle.
    """
    from accounts.access import has_account_access
    from cases.access import has_case_read_access
    from contacts.access import has_contact_access
    from invoices.permissions import has_object_access
    from leads.access import has_lead_access
    from opportunity.access import has_deal_access
    from tasks.access import has_task_access

    return {
        "lead": lambda request, obj: has_lead_access(
            request.profile, request.user, obj
        ),
        "opportunity": lambda request, obj: has_deal_access(
            request.profile, request.user, obj
        ),
        "contact": lambda request, obj: has_contact_access(request.profile, obj),
        "account": lambda request, obj: has_account_access(request.profile, obj),
        "case": lambda request, obj: has_case_read_access(request.profile, obj),
        "task": lambda request, obj: has_task_access(request.profile, obj),
        "invoice": has_object_access,
    }


def may_read_attachment(request, attachment):
    """True when the caller may read the record this file is attached to.

    Deny by default, twice over. An unmapped content type is refused, and so
    is an attachment whose parent row has been deleted out from under it: a
    dangling `object_id` is not an absence of a rule, it is a record nobody
    can be checked against.
    """
    reader = _readers().get(attachment.content_type.model)
    if reader is None:
        return False
    parent = attachment.content_object
    if parent is None:
        return False
    # The org filter on the attachment does not cover the parent, and a
    # ContentType lookup crosses tenants freely, so check it here as well.
    if getattr(parent, "org_id", None) != request.profile.org_id:
        return False
    return reader(request, parent)


def may_delete_attachment(request, attachment):
    """Deletion follows the parent's current scope, never the uploader alone."""
    from common.rbac import MODEL_MODULES, configured, permitted

    if not may_read_attachment(request, attachment):
        return False
    if request.profile.role == "ADMIN":
        return True
    parent = attachment.content_object
    if parent._meta.label_lower in MODEL_MODULES:
        return configured(request.profile) and permitted(
            request.profile, parent, "delete_attachments"
        )
    # Preview modules keep their existing uploader restriction. Their endpoints
    # cannot be used to delete files on another type of record.
    return attachment.created_by_id == request.user.pk


@transaction.atomic
def delete_attachment(request, pk, expected_model=None):
    try:
        attachment = get_object_or_404(
            Attachments.objects.select_related("content_type"),
            pk=pk,
            org_id=request.profile.org_id,
        )
    except (DjangoValidationError, ValueError):
        raise Http404("No such attachment.")
    if expected_model and attachment.content_type.model != expected_model:
        raise Http404("No such attachment.")
    if not may_delete_attachment(request, attachment):
        raise PermissionDenied(
            "Your permission set does not allow deleting this attachment."
        )
    # Deletion and its storage-cleanup receipt commit together. Storage failures
    # are retried by the worker without restoring a downloadable database row.
    attachment.delete()
    return Response({"error": False, "message": "Attachment deleted."})


class AttachmentDeleteView(APIView):
    permission_classes = (IsAuthenticated, HasOrgContext)

    @extend_schema(tags=["Attachments"], operation_id="attachments_delete")
    def delete(self, request, pk, format=None):
        return delete_attachment(request, pk)


class AttachmentDownloadView(APIView):
    """`GET /api/attachments/<pk>/download/`, streamed with the file's name."""

    permission_classes = (IsAuthenticated, HasOrgContext)

    @extend_schema(
        tags=["Attachments"],
        operation_id="attachments_download",
        parameters=swagger_params.organization_params,
        responses={(200, "application/octet-stream"): OpenApiTypes.BINARY},
    )
    def get(self, request, pk, format=None):
        attachment = get_object_or_404(
            Attachments.objects.select_related("content_type"),
            id=pk,
            org=request.profile.org,
        )
        if not may_read_attachment(request, attachment):
            return Response(
                {
                    "error": True,
                    "errors": "You do not have Permission to perform this action",
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        if not attachment.attachment:
            raise Http404("That attachment has no file.")
        attachment.attachment.open("rb")
        from contacts.signals import record, related_contact

        contact = related_contact(attachment)
        if contact:
            record(
                contact,
                "VIEW",
                "Attachment download requested",
                {"File": {"before": None, "after": attachment.file_name}},
            )
        return FileResponse(
            attachment.attachment,
            as_attachment=True,
            filename=attachment.file_name or "attachment",
        )
