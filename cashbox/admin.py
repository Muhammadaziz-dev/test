from django.contrib import admin
from .models import Cashbox, CashTransaction


@admin.register(Cashbox)
class CashboxAdmin(admin.ModelAdmin):
    list_display = ('id', 'store', 'balance')
    search_fields = ('store__name',)
    readonly_fields = ('balance',)
    list_select_related = ('store',)


@admin.register(CashTransaction)
class CashTransactionAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'cashbox', 'amount', 'is_out', 'created_at', 'note', 'get_full_note'
    )

    list_filter = ('is_out', 'created_at', 'cashbox__store__name')
    search_fields = ('note', 'manual_source', 'cashbox__store__name')
    date_hierarchy = 'created_at'
    list_select_related = ('cashbox', 'order')
    autocomplete_fields = ('cashbox', 'order')

    readonly_fields = ["get_full_note"]

    def get_full_note(self, obj):
        return obj.get_full_note()

    get_full_note.short_description = "To‘liq izoh"
