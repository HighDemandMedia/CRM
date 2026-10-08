"""Sorting must happen before slicing a ticket list into pages."""

import pytest

from cases.models import Case


@pytest.mark.django_db
@pytest.mark.parametrize(
    "ordering, expected",
    [("category", ["A", "B", "C"]), ("-category", ["C", "B", "A"])],
)
def test_ticket_order_across_pages(admin_client, org_a, org_b, ordering, expected):
    for category in ["C", "A", "B"]:
        Case.objects.create(name="Pagination test", category=category, org=org_a)
    Case.objects.create(name="Pagination test", category="Foreign", org=org_b)
    categories = []
    ids = []
    for offset in range(3):
        response = admin_client.get(
            "/api/cases/",
            {
                "search": "Pagination test",
                "ordering": ordering,
                "limit": 1,
                "offset": offset,
                "slim": "true",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["cases_count"] == 3
        assert len(data["cases"]) == 1
        categories.append(data["cases"][0]["category"])
        ids.append(data["cases"][0]["id"])
    assert categories == expected
    assert len(set(ids)) == 3
