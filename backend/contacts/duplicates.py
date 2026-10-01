"""Read-only contact matches, limited to the caller's visible organization records."""

from uuid import UUID

from django.db.models import Case, IntegerField, Q, Value, When
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.permissions import HasOrgContext, is_org_admin
from common.rbac import configured, scoped
from common.validators import contact_phone_key
from contacts.models import Contact


class ContactDuplicatesView(APIView):
    permission_classes = (IsAuthenticated, HasOrgContext)

    def get(self, request):
        params = request.query_params
        name = " ".join(params.get("name", "").split())[:255]
        email = params.get("email", "").strip().lower()[:254]
        phone = contact_phone_key(params.get("phone", "")[:25])
        exclude = params.get("exclude", "")
        qs = scoped(Contact.objects.filter(org=request.profile.org), request.profile)
        if not configured(request.profile) and not is_org_admin(request.profile):
            qs = qs.filter(
                Q(assigned_to=request.profile) | Q(created_by=request.user)
            ).distinct()
        if exclude:
            try:
                exclude = UUID(exclude)
            except ValueError:
                raise ValidationError({"exclude": "Invalid contact ID."})
            qs = qs.exclude(pk=exclude)

        never = Q(pk__in=[])
        email_q = Q(email__iexact=email) if "@" in email else never
        phone_q = Q(phone_match_key=phone) if len(phone) >= 7 else never
        # Without a country code this is only a possible match, never proof of identity.
        alternative = (
            ("1" + phone)
            if len(phone) == 10
            else phone[1:]
            if len(phone) == 11 and phone.startswith("1")
            else ""
        )
        similar_phone_q = Q(phone_match_key=alternative) if alternative else never
        tokens = name.split()[:8]
        name_q = never
        if len(name) >= 3 and tokens:
            name_q = Q()
            for token in tokens:
                name_q &= Q(first_name__icontains=token) | Q(last_name__icontains=token)
        candidates = (
            qs.filter(email_q | phone_q | similar_phone_q | name_q)
            .annotate(
                match_rank=Case(
                    When(email_q, then=Value(0)),
                    When(phone_q, then=Value(1)),
                    When(similar_phone_q, then=Value(2)),
                    default=Value(3),
                    output_field=IntegerField(),
                )
            )
            .order_by("match_rank", "first_name", "id")
            .distinct()[:5]
        )
        results = []
        for contact in candidates:
            reasons = []
            if email and (contact.email or "").strip().lower() == email:
                reasons.append("Same email")
            if phone and contact.phone_match_key == phone:
                reasons.append("Same phone")
            elif alternative and contact.phone_match_key == alternative:
                reasons.append("Similar phone — check country code")
            if name and all(
                token.casefold() in contact.name.casefold() for token in tokens
            ):
                reasons.append(
                    "Same name"
                    if contact.name.casefold() == name.casefold()
                    else "Similar name"
                )
            results.append(
                {
                    "id": str(contact.pk),
                    "name": contact.name,
                    "email": contact.email or "",
                    "phone": contact.phone or "",
                    "reasons": reasons,
                }
            )
        return Response({"results": results})
