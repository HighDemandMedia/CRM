"""Product catalogue retained for deal line items; billing lives in the lab."""

from django.contrib import admin

from invoices.models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    search_fields = ("name", "sku", "description")
