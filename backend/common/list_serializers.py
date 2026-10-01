"""Small relation labels for list screens; keep the normal visibility checks."""

from rest_framework import serializers

from accounts.models import Account
from common.models import Profile
from common.rbac import VisibleCRMSerializerMixin
from common.serializer import UserSerializer
from contacts.models import Contact


class AccountLabelSerializer(VisibleCRMSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ("id", "name")


class ContactLabelSerializer(VisibleCRMSerializerMixin, serializers.ModelSerializer):
    name = serializers.CharField(read_only=True)

    class Meta:
        model = Contact
        fields = ("id", "first_name", "last_name", "name", "email", "phone")


class OwnerLabelSerializer(serializers.ModelSerializer):
    user_details = UserSerializer(source="user", read_only=True)

    class Meta:
        model = Profile
        fields = ("id", "user_details")
