"""Paginated conversations for contact/company records, never an entire mailbox."""

from django.db.models import Count, Max, OuterRef, Subquery
from django.db.models.functions import Lower, Trim
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.views import APIView

from common.google_integration import GoogleError, connection_status, decrypt
from common.google_mail import mail_rows, mail_summary, record_contacts, unique_messages
from common.permissions import HasOrgContext


class MailQuery(serializers.Serializer):
    offset = serializers.IntegerField(min_value=0, max_value=1000000, default=0)
    direction = serializers.ChoiceField(
        choices=["all", "sent", "received"], default="all"
    )
    q = serializers.CharField(
        max_length=200, required=False, allow_blank=True, default=""
    )
    contact = serializers.UUIDField(required=False)
    thread = serializers.CharField(max_length=128, required=False)


class RecordMailView(APIView):
    permission_classes = (IsAuthenticated, HasOrgContext)

    def post(self, request, kind, pk):
        from common.views.google_integration_views import own_connection, queue

        record_contacts(request.profile, kind, pk)
        conn = own_connection(request, "gmail")
        if conn.status != "connected":
            raise serializers.ValidationError("Connect Google first.")
        queue(conn)
        return Response(
            {"queued": True}, headers={"Cache-Control": "private, no-store"}
        )

    def get(self, request, kind, pk):
        query = MailQuery(data=request.query_params)
        query.is_valid(raise_exception=True)
        params = query.validated_data
        contacts = record_contacts(request.profile, kind, pk)
        if params.get("contact"):
            contacts = contacts.filter(pk=params["contact"])
        rows = mail_rows(request.profile, contacts)
        offset, page_size = params["offset"], 20
        if params.get("thread"):
            page = list(
                unique_messages(rows.filter(thread_id=params["thread"]))
                .select_related("connection")
                .order_by("occurred_at", "id")[offset : offset + page_size + 1]
            )
            results = [mail_summary(row) for row in page[:page_size]]
        else:
            matching = rows
            if params["direction"] != "all":
                matching = matching.filter(direction=params["direction"])
            if params["q"]:
                needle = params["q"].casefold()
                matched_threads = set()
                # Bodies stay encrypted at rest; search only this user's authorized
                # record messages, in bounded database batches, never in shared indexes.
                try:
                    for mail in (
                        matching.defer(None)
                        .only(
                            "thread_id",
                            "subject",
                            "sender",
                            "recipients",
                            "cc",
                            "encrypted_body",
                        )
                        .iterator(chunk_size=100)
                    ):
                        envelope = " ".join(
                            [mail.subject, mail.sender, *mail.recipients, *mail.cc]
                        )
                        if (
                            needle in envelope.casefold()
                            or needle in decrypt(mail.encrypted_body).casefold()
                        ):
                            matched_threads.add(mail.thread_id)
                except GoogleError:
                    raise serializers.ValidationError(
                        "Email search is unavailable. Reconnect Gmail and synchronize again."
                    )
                matching = matching.filter(thread_id__in=matched_threads)
            # Filters select conversations, while counts and previews describe the full thread.
            threads = rows.filter(thread_id__in=matching.values("thread_id"))
            latest = rows.filter(thread_id=OuterRef("thread_id")).order_by(
                "-occurred_at", "-id"
            )
            page = list(
                threads.order_by()
                .values("thread_id")
                .annotate(
                    last_at=Max("occurred_at"),
                    message_count=Count("message_id", distinct=True),
                    latest_id=Subquery(latest.values("id")[:1]),
                )
                .order_by("-last_at", "thread_id")[offset : offset + page_size + 1]
            )
            latest_rows = {
                str(row.pk): row
                for row in rows.filter(
                    pk__in=[item["latest_id"] for item in page[:page_size]]
                ).select_related("connection")
            }
            results = [
                {
                    **mail_summary(latest_rows[str(item["latest_id"])]),
                    "message_count": item["message_count"],
                }
                for item in page[:page_size]
            ]
        # Only expose contact identities already visible to this user and related to this record.
        selected_emails = {
            email.lower()
            for item in results
            for email in [item["sender"], *item["recipients"], *item["cc"]]
        }
        people = list(
            contacts.annotate(mail_address=Lower(Trim("email")))
            .filter(mail_address__in=selected_emails)
            .values("id", "first_name", "last_name", "email")
        )
        for item in results:
            participants = {
                email.lower()
                for email in [item["sender"], *item["recipients"], *item["cc"]]
            }
            item["contacts"] = [
                {
                    "id": str(person["id"]),
                    "name": " ".join(
                        filter(None, [person["first_name"], person["last_name"]])
                    )
                    or person["email"],
                }
                for person in people
                if person["email"].strip().lower() in participants
            ]
        return Response(
            {
                "results": results,
                "next_offset": offset + page_size if len(page) > page_size else None,
                "connection": connection_status(request.profile)["gmail"],
            },
            headers={"Cache-Control": "private, no-store"},
        )


class MailActionThrottle(SimpleRateThrottle):
    rate = "10/min"
    scope = "record_mail_actions"

    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": request.user.pk}


class RecordMailActionView(APIView):
    throttle_classes = (MailActionThrottle,)
    permission_classes = (IsAuthenticated, HasOrgContext)

    def post(self, request, kind, pk):
        from common.google_mail_actions import MailAction, perform_mail_action

        serializer = MailAction(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(
            perform_mail_action(request.profile, kind, pk, serializer.validated_data),
            headers={"Cache-Control": "private, no-store"},
        )
