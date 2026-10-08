"""Open-only lists must be filtered before applying limit and offset."""

import pytest

from tasks.models import Task


@pytest.mark.django_db
def test_open_tasks_fill_pages_and_have_filtered_totals(admin_client, org_a, org_b):
    for index in range(7):
        Task.objects.create(title=f"Paging {index}", org=org_a, status="New")
    for index in range(9):
        Task.objects.create(title=f"Paging done {index}", org=org_a, status="Completed")
    Task.objects.create(title="Paging foreign", org=org_b, status="New")

    ids = []
    for offset, size in [(0, 3), (3, 3), (6, 1)]:
        response = admin_client.get(
            "/api/tasks/",
            {
                "search": "Paging",
                "exclude_completed": "true",
                "limit": 3,
                "offset": offset,
                "slim": "true",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["tasks_count"] == data["totals"]["count"] == 7
        assert len(data["tasks"]) == size
        assert all(task["status"] == "New" for task in data["tasks"])
        ids.extend(task["id"] for task in data["tasks"])
    assert len(set(ids)) == 7

    explicit = admin_client.get(
        "/api/tasks/",
        {
            "search": "Paging",
            "exclude_completed": "true",
            "status": "Completed",
            "limit": 3,
            "slim": "true",
        },
    ).json()
    assert explicit["tasks_count"] == 9
    assert all(task["status"] == "Completed" for task in explicit["tasks"])
