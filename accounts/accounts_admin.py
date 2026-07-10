from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Division, User


@admin.register(Division)
class DivisionAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "code")


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "email", "role", "division", "is_active", "is_staff")
    list_filter = ("role", "division", "is_active")
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Helpdesk info", {"fields": ("role", "division", "phone_number", "company", "address", "position")}),
    )
