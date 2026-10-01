"""
Tests for dashboard views: ApiHomeView, ActivityListView.

Run with: pytest common/tests/test_dashboard.py -v
"""

import uuid

import pytest
from rest_framework import status

from common.models import Activity


@pytest.mark.django_db
class TestActivityListView:
    """Tests for GET /api/activities/"""

    url = "/api/activities/"

    def test_list_activities(self, admin_client, org_a, admin_profile):
        """Get recent activities."""
        Activity.objects.create(
            user=admin_profile,
            action="CREATE",
            entity_type="Account",
            entity_id=uuid.uuid4(),
            entity_name="Test Account",
            org=org_a,
        )
        response = admin_client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
        assert "activities" in response.data
        assert response.data["count"] >= 1

    def test_list_activities_with_limit(self, admin_client, org_a, admin_profile):
        """Test limit parameter."""
        for i in range(5):
            Activity.objects.create(
                user=admin_profile,
                action="CREATE",
                entity_type="Account",
                entity_id=uuid.uuid4(),
                entity_name=f"Account {i}",
                org=org_a,
            )
        response = admin_client.get(self.url + "?limit=2")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 2

    def test_list_activities_filter_by_entity_type(
        self, admin_client, org_a, admin_profile
    ):
        """Filter activities by entity_type."""
        Activity.objects.create(
            user=admin_profile,
            action="CREATE",
            entity_type="Account",
            entity_id=uuid.uuid4(),
            entity_name="Account Activity",
            org=org_a,
        )
        Activity.objects.create(
            user=admin_profile,
            action="CREATE",
            entity_type="Lead",
            entity_id=uuid.uuid4(),
            entity_name="Lead Activity",
            org=org_a,
        )
        response = admin_client.get(self.url + "?entity_type=Account")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1
