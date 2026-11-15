from django.contrib import admin
from django import forms

from .models import (
    Category,
    Item,
    StaffCartItemPriceChange,
    StaffCartItemRemoval,
    StaffCredential,
    StudentId,
)
from .permissions import is_manager, user_role


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = (
        "category_id",
        "category_name",
        "tax_exempt",
        "student_discount_exempt",
        "employee_discount_exempt",
    )
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
        "tax_exempt",
        "student_discount_exempt",
    )

    list_filter = ("category", "tax_exempt", "student_discount_exempt")
    search_fields = ("item",)

    def has_add_permission(self, request):
        return is_manager(request.user)


@admin.register(StudentId)
class StudentIdAdmin(admin.ModelAdmin):
    list_display = ("student_id", "is_active")
    list_filter = ("is_active",)
    search_fields = ("student_id",)

    def has_add_permission(self, request):
        return is_manager(request.user)


class StaffCredentialForm(forms.ModelForm):
    pin = forms.CharField(
        label="Staff PIN",
        required=False,
        widget=forms.PasswordInput(
            render_value=False,
            attrs={"autocomplete": "new-password"},
        ),
        help_text="Use 4 to 12 digits. Leave blank when editing to keep the current PIN.",
    )

    class Meta:
        model = StaffCredential
        fields = ("user",)

    def clean_user(self):
        user = self.cleaned_data["user"]
        if not user.is_active or user_role(user) == "Student":
            raise forms.ValidationError("Choose an active Manager or Operator account.")
        return user

    def clean_pin(self):
        pin = self.cleaned_data["pin"]
        if not pin and not self.instance.pk:
            raise forms.ValidationError("Enter a PIN for this staff account.")
        if pin and (not pin.isascii() or not pin.isdigit() or not 4 <= len(pin) <= 12):
            raise forms.ValidationError("PINs must contain 4 to 12 digits.")
        return pin


@admin.register(StaffCredential)
class StaffCredentialAdmin(admin.ModelAdmin):
    form = StaffCredentialForm
    fields = ("user", "pin")
    list_display = ("user",)
    search_fields = ("user__username",)

    def save_model(self, request, obj, form, change):
        pin = form.cleaned_data["pin"]
        if pin:
            obj.set_pin(pin)
        super().save_model(request, obj, form, change)

    def has_add_permission(self, request):
        return is_manager(request.user)

    def has_change_permission(self, request, obj=None):
        return is_manager(request.user)

    def has_delete_permission(self, request, obj=None):
        return is_manager(request.user)


@admin.register(StaffCartItemRemoval)
class StaffCartItemRemovalAdmin(admin.ModelAdmin):
    list_display = (
        "item_name",
        "item_code",
        "quantity_removed",
        "student_user_id",
        "staff_user_id",
        "removed_at",
    )
    list_filter = ("removed_at",)
    search_fields = ("item_name", "item_code", "student_user_id", "staff_user_id")
    readonly_fields = (
        "student_user_id",
        "staff_user_id",
        "cart_item_id",
        "item_name",
        "item_code",
        "variant_size",
        "variant_color",
        "quantity_removed",
        "removed_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(StaffCartItemPriceChange)
class StaffCartItemPriceChangeAdmin(admin.ModelAdmin):
    list_display = (
        "item_name",
        "item_code",
        "original_price",
        "new_price",
        "student_user_id",
        "staff_user_id",
        "changed_at",
    )
    list_filter = ("changed_at",)
    search_fields = ("item_name", "item_code", "reason", "student_user_id", "staff_user_id")
    readonly_fields = (
        "student_user_id",
        "staff_user_id",
        "cart_item_id",
        "item_name",
        "item_code",
        "original_price",
        "new_price",
        "reason",
        "changed_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
