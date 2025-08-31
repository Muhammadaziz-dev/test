from django.contrib import admin
from .models import Category


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'parent', 'slug')
    list_filter = ('user', 'parent')
    search_fields = ('name', 'slug')
    ordering = ('name',)

    readonly_fields = ('slug',)

    fieldsets = (
        (None, {
            'fields': ('name', 'parent', 'image', 'user')
        }),
        ('Slug (faqat o‘qiladi)', {
            'fields': ('slug',),
        }),
    )