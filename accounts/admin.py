from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Division, User


@admin.register(Division)
class DivisionAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at")
    search_fields = ("name",)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "email", "role", "division", "is_active", "is_staff")
    list_filter = ("role", "division", "is_active")
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Helpdesk info", {"fields": ("role", "division", "phone_number")}),
    )
