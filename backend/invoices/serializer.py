"""Product representation retained for existing deal line items."""

from rest_framework import serializers

from invoices.models import Product


class ProductSerializer(serializers.ModelSerializer):
    """Serializer for Product catalog"""

    used_on = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = (
            "id",
            "name",
            "description",
            "sku",
            "price",
            "currency",
            "category",
            "is_active",
            "used_on",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def get_used_on(self, obj):
        """Distinct invoices this product is a line item on.

        Line items denormalise their own name and unit price, so retiring or
        even deleting a product never rewrites a historic invoice (the FK is
        SET_NULL); this count is why a retired product is still worth listing.
        `ProductListView` annotates `used_on_count` to avoid an N+1 across the
        list, so read that when present and fall back to a query on the single
        detail views.
        """
        annotated = getattr(obj, "used_on_count", None)
        if annotated is not None:
            return annotated
        return obj.invoice_line_items.values("invoice_id").distinct().count()
