import pytest
from django.core.exceptions import ValidationError

from accounts.models import Account
from common.models import Org
from common.utils import COUNTRIES
from contacts.models import Contact
from opportunity.models import Opportunity


@pytest.mark.parametrize(
    "model,field",
    [
        (Org, "country"),
        (Org, "default_country"),
        (Contact, "country"),
        (Account, "country"),
        (Opportunity, "country"),
    ],
)
@pytest.mark.parametrize("code", ["BQ", "CW", "SX", "SS", "JP", "DE", "UY", "AN"])
def test_country_choices_accept_current_and_preserve_historical_codes(
    model, field, code
):
    model._meta.get_field(field).validate(code, model())


def test_country_catalog_is_unique_and_rejects_unknown_codes():
    codes = [code for code, _ in COUNTRIES]
    assert len(codes) == len(set(codes)) == 250  # 249 assigned + legacy AN
    with pytest.raises(ValidationError):
        Contact._meta.get_field("country").validate("ZZ", Contact())


@pytest.mark.django_db
@pytest.mark.parametrize("route", ["contacts", "accounts", "opportunities"])
def test_new_country_can_be_created_and_updated_through_api(admin_client, route):
    response = admin_client.post(
        f"/api/{route}/", {"name": "Country QA", "country": "CW"}, format="json"
    )
    assert response.status_code in (200, 201), response.data
    model = {"contacts": Contact, "accounts": Account, "opportunities": Opportunity}[
        route
    ]
    record = model.objects.get(pk=response.data["id"])
    assert record.country == "CW"
    response = admin_client.patch(
        f"/api/{route}/{record.pk}/", {"country": "SS"}, format="json"
    )
    assert response.status_code == 200, response.data
    record.refresh_from_db()
    assert record.country == "SS"
    response = admin_client.patch(
        f"/api/{route}/{record.pk}/", {"country": "ZZ"}, format="json"
    )
    assert response.status_code == 400, response.data
    record.refresh_from_db()
    assert record.country == "SS"
