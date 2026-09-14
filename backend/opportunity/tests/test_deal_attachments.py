import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from opportunity.models import Opportunity


@pytest.mark.django_db
def test_deal_upload_list_and_download(
    admin_client, org_a, org_b, settings, tmp_path
):
    settings.MEDIA_ROOT = str(tmp_path)
    account = Opportunity.objects.create(name="Attachment test", org=org_a)
    url = f"/api/opportunities/{account.pk}/"
    response = admin_client.post(
        url,
        {
            "opportunity_attachment": SimpleUploadedFile(
                "company.txt", b"Company document", content_type="text/plain"
            )
        },
        format="multipart",
    )
    assert response.status_code == 200, response.data
    files = admin_client.get(url).data["attachments"]
    assert len(files) == 1
    assert files[0]["file_name"] == "company.txt"
    download = admin_client.get(f"/api/attachments/{files[0]['id']}/download/")
    assert download.status_code == 200
    assert b"".join(download.streaming_content) == b"Company document"
    foreign = Opportunity.objects.create(name="Foreign", org=org_b)
    response = admin_client.post(
        f"/api/opportunities/{foreign.pk}/",
        {"opportunity_attachment": SimpleUploadedFile("other.txt", b"No")},
        format="multipart",
    )
    assert response.status_code == 404
