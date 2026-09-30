"""Saved design and connection settings must work in both public renderers."""

import pytest

from webforms.appearance import form_appearance
from webforms.models import WebForm


@pytest.mark.django_db
class TestBuilder:
    def test_settings_roundtrip_and_safe_public_render(
        self, admin_client, unauthenticated_client, org_a
    ):
        response = admin_client.post(
            "/api/webforms/",
            {
                "name": "Website contact",
                "target_model": "Contact",
                "connection_mode": "new",
                "website_form_id": "contact-form",
                "appearance": {
                    "title": "<img src=x onerror=alert(1)>",
                    "description": "Tell us more",
                    "button_color": "#ffff00",
                    "font": "georgia",
                    "columns": 2,
                    "radius": 12,
                    "width": 720,
                },
            },
            format="json",
        )
        assert response.status_code == 201, response.data
        form = WebForm.objects.get(id=response.data["id"])
        assert form.appearance["columns"] == 2
        assert 'data-form="#contact-form"' in response.data["connector_js"]
        assert response.data["connection_mode"] == "new"
        form.is_published = True
        form.save()
        base = f"/api/public/forms/{org_a.id}/{form.id}/"
        html = unauthenticated_client.get(base + "embed/").content.decode()
        assert "<img src=x" not in html
        assert "&lt;img src=x" in html
        assert "repeat(2, minmax(0, 1fr))" in html
        assert "background: #ffff00; color: #000000" in html
        assert "Georgia, serif" in html
        script = unauthenticated_client.get(base + "embed.js").content.decode()
        assert '"columns": 2' in script
        assert "title.textContent = design.title" in script
        # Ordinary settings saves keep the existing design.
        updated = admin_client.put(
            f"/api/webforms/{form.id}/", {"name": "Renamed"}, format="json"
        )
        assert updated.status_code == 200
        assert updated.data["appearance"]["width"] == 720

    @pytest.mark.parametrize(
        "appearance",
        [
            {"button_color": "red; background:url(https://example.com)"},
            {"font": "url(x)"},
            {"width": 10000},
            {"columns": 3},
            {"radius": -1},
            {"unexpected_css": "x"},
            {"title": "x" * 121},
            [],
        ],
    )
    def test_rejects_unsafe_or_unbounded_design(self, admin_client, appearance):
        response = admin_client.post(
            "/api/webforms/",
            {"name": "Bad design", "appearance": appearance},
            format="json",
        )
        assert response.status_code == 400
        assert not WebForm.objects.exists()

    def test_render_boundary_revalidates_outside_api_writes(self):
        form = WebForm(
            name="Unsafe", appearance={"button_color": "red;} body{display:none"}
        )
        assert form_appearance(form)["button_color"] == "#343234"

    def test_rejects_selector_injection(self, admin_client):
        response = admin_client.post(
            "/api/webforms/",
            {"name": "Bad selector", "website_form_id": 'a" onload="alert(1)'},
            format="json",
        )
        assert response.status_code == 400
