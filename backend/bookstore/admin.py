from django.contrib import admin
from .models import Category, Item


def is_manager(user):
    return user.is_superuser or user.groups.filter(name="Manager").exists()


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("category_id", "category_name")
    search_fields = ("category_name",)

    def has_add_permission(self, request):
        return is_manager(request.user)


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = (
        "item_id",
        "item",
        "category",
        "item_quantity",
        "item_price",
    )

    list_filter = ("category",)
    search_fields = ("item",)

    def has_add_permission(self, request):
        return is_manager(request.user)