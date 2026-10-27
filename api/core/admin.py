"""Admin for users and partners: operations issues accounts and tokens here (04 §1)."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import Partner, Setting, User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    fieldsets = (
        *(DjangoUserAdmin.fieldsets or ()),
        ("Travel agency", {"fields": ("role", "partner")}),
    )
    add_fieldsets = (
        *(DjangoUserAdmin.add_fieldsets or ()),
        ("Travel agency", {"fields": ("role", "partner")}),
    )
    list_display = ("username", "role", "partner", "is_active", "is_staff")
    list_filter = ("role", "is_active", "is_staff")


@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = ("name", "is_demo", "created_at")


@admin.register(Setting)
class SettingAdmin(admin.ModelAdmin):
    list_display = ("key", "value", "updated_at")
    readonly_fields = ("updated_at",)
