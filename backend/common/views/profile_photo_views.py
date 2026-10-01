"""Own profile photo upload; re-encode images to discard metadata."""

import io
import uuid
import warnings

from django.core.files.base import ContentFile
from PIL import Image, ImageOps
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.permissions import HasOrgContext


class ProfilePhotoView(APIView):
    permission_classes = (IsAuthenticated, HasOrgContext)

    def post(self, request):
        upload = request.FILES.get("photo")
        if not upload or upload.size > 5 * 1024 * 1024:
            raise serializers.ValidationError(
                "Choose a JPG, PNG or WebP image up to 5 MB."
            )
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                image = Image.open(upload)
                if (
                    image.format not in ("JPEG", "PNG", "WEBP")
                    or image.width * image.height > 20_000_000
                ):
                    raise ValueError()
                image = ImageOps.exif_transpose(image)
                image.thumbnail((512, 512))
                image = image.convert("RGB")
                output = io.BytesIO()
                image.save(output, format="JPEG", quality=88)
        except (
            OSError,
            ValueError,
            Image.DecompressionBombError,
            Image.DecompressionBombWarning,
        ):
            raise serializers.ValidationError(
                "Choose a valid JPG, PNG or WebP image."
            ) from None
        user = request.user
        old_name = user.profile_image.name
        storage = user.profile_image.storage
        user.profile_image.save(
            f"{uuid.uuid4()}.jpg", ContentFile(output.getvalue()), save=False
        )
        user.save(update_fields=["profile_image"])
        if old_name:
            storage.delete(old_name)
        return Response({"saved": True})

    def delete(self, request):
        user = request.user
        old_name = user.profile_image.name
        storage = user.profile_image.storage
        user.profile_image = ""
        user.profile_pic = ""
        user.save(update_fields=["profile_image", "profile_pic"])
        if old_name:
            storage.delete(old_name)
        return Response({"saved": True})
