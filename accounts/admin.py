from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    fieldsets = UserAdmin.fieldsets + (
        ("Qo‘shimcha ma’lumotlar", {
            "fields": ("phone_number", "gender", "profile_image")
        }),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Qo‘shimcha ma’lumotlar", {
            "fields": ("phone_number", "gender", "profile_image")
        }),
    )
    list_display = ["username", "email", "phone_number", "gender", "is_staff"]
    search_fields = ["username", "email", "phone_number"]