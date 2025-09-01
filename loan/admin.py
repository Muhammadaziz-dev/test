from django.contrib import admin, messages
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from .models import DebtUser, DebtDocument, DocumentProduct, DebtImportOffer
from django.db.models import Sum

class DocumentProductInline(admin.TabularInline):
    model = DocumentProduct
    extra = 0
    readonly_fields = ('amount',)
    autocomplete_fields = ['product']

    # Hujjat o'chirilgan bo'lsa — to'liq read-only
    def get_readonly_fields(self, request, obj=None):
        base = list(super().get_readonly_fields(request, obj))
        if obj and getattr(obj, 'is_deleted', False):
            return ('product', 'quantity', 'price', 'amount', 'currency', 'exchange_rate', 'income')
        return base

    def has_add_permission(self, request, obj=None):
        if obj and getattr(obj, 'is_deleted', False):
            return False
        return super().has_add_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if obj and getattr(obj, 'is_deleted', False):
            return False
        return super().has_delete_permission(request, obj)

@admin.register(DebtUser)
class DebtUserAdmin(admin.ModelAdmin):
    list_display = ("id", 'full_name', 'phone_number', 'balance_display', 'currency', 'store', 'is_deleted', 'deleted_at', 'id')
    search_fields = ('first_name', 'last_name', 'phone_number')
    list_filter = ('store', 'currency', 'is_deleted')
    readonly_fields = ('transferred', 'accepted', 'balance', 'created_at', 'is_deleted', 'deleted_at')
    actions = ['recalculate_balance', 'soft_delete_selected', 'restore_selected', 'hard_delete_selected']

    def full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"
    full_name.short_description = 'Ism Familiya'

    def balance_display(self, obj):
        color = 'green' if obj.balance >= 0 else 'red'
        from django.utils.html import format_html
        return format_html('<b style="color: {}">{} {}</b>', color, obj.balance, obj.currency)
    balance_display.short_description = 'Balans'

    def recalculate_balance(self, request, queryset):
        for user in queryset:
            user.recalculate_balance()
        self.message_user(request, _(f"{queryset.count()} ta foydalanuvchi balansi qayta hisoblandi."), messages.SUCCESS)

    def soft_delete_selected(self, request, queryset):
        done = 0
        for u in queryset:
            if u.is_deleted:
                continue
            u.soft_delete(); done += 1
        if done:
            self.message_user(request, _(f"{done} ta debtor soft delete qilindi."), messages.SUCCESS)
    soft_delete_selected.short_description = _("Soft delete")

    def restore_selected(self, request, queryset):
        done = 0
        for u in queryset:
            if not u.is_deleted:
                continue
            u.restore(); done += 1
        if done:
            self.message_user(request, _(f"{done} ta debtor tiklandi."), messages.SUCCESS)
    restore_selected.short_description = _("Restore")

    def hard_delete_selected(self, request, queryset):
        count = queryset.count()
        for u in queryset:
            u.hard_delete()
        self.message_user(request, _(f"{count} ta debtor butunlay o‘chirildi."), messages.SUCCESS)
    hard_delete_selected.short_description = _("Hard delete (butunlay)")

@admin.register(DebtDocument)
class DebtDocumentAdmin(admin.ModelAdmin):
    list_display = ('id','debtuser', 'method', 'total_amount', 'cash_amount', 'product_amount', 'currency',
                    'date', 'is_deleted', 'deleted_at')
    list_filter = ('store', 'method', 'currency', 'is_deleted', 'date')
    search_fields = ('debtuser__first_name', 'debtuser__last_name', 'debtuser__phone_number', 'phone_number')
    inlines = [DocumentProductInline]
    autocomplete_fields = ['debtuser', 'owner']
    readonly_fields = ('total_amount', 'income', 'date', 'is_deleted', 'deleted_at')
    date_hierarchy = 'date'
    ordering = ['-date']
    actions = ['soft_delete_selected', 'restore_selected', 'hard_delete_selected']

    fieldsets = (
        (None, {
            'fields': (
                'store', 'phone_number', 'first_name', 'last_name', 'debtuser', 'owner',
                'method', 'currency', 'exchange_rate',
                'cash_amount', 'product_amount', 'total_amount', 'income', 'date',
                'is_deleted', 'deleted_at',
            )
        }),
    )

    def save_related(self, request, form, formsets, change):
        # Avval barcha inline’larni saqlab oladi
        super().save_related(request, form, formsets, change)

        obj = form.instance  # hozirgina saqlangan DebtDocument
        # Inline productlar asosida yig‘indini olamiz
        total_products = obj.products.aggregate(s=Sum('amount'))['s'] or Decimal('0.00')
        new_total = (obj.cash_amount or Decimal('0.00')) + total_products

        # Model.save() yon effektlarini (kassa txn qayta yozish) chaqirmasdan to‘g‘ridan-to‘g‘ri update:
        DebtDocument.objects.filter(pk=obj.pk).update(
            product_amount=total_products,
            total_amount=new_total,
        )

        # Admin sahifada ko‘rinib turishi uchun RAM’dagi obyektni ham yangilaymiz
        obj.product_amount = total_products
        obj.total_amount = new_total

        # (ixtiyoriy, lekin foydali) balansni ham yangilab qo‘yish
        if obj.debtuser_id and not obj.is_mirror and not obj.is_deleted:
            obj.debtuser.recalculate_balance()

    # O'chirilgan hujjatlarda hamma maydonlarni read-only qilish
    def get_readonly_fields(self, request, obj=None):
        base = list(super().get_readonly_fields(request, obj))
        if obj and getattr(obj, 'is_deleted', False):
            # barcha editable maydonlarni ham qo'shib, to'liq read-only
            all_fields = {
                'store', 'phone_number', 'first_name', 'last_name', 'debtuser', 'owner',
                'method', 'currency', 'exchange_rate',
                'cash_amount', 'product_amount', 'total_amount', 'income', 'date',
                'is_deleted', 'deleted_at',
            }
            return tuple(sorted(set(base) | all_fields))
        return base

    # Actions
    def soft_delete_selected(self, request, queryset):
        done, skipped = 0, 0
        for doc in queryset:
            if getattr(doc, 'is_deleted', False):
                skipped += 1
                continue
            try:
                doc.soft_delete()
                done += 1
            except Exception as e:
                self.message_user(request, _(f"#{doc.pk} soft delete xatosi: {e}"), messages.ERROR)
        if done:
            self.message_user(request, _(f"{done} ta hujjat soft delete qilindi."), messages.SUCCESS)
        if skipped:
            self.message_user(request, _(f"{skipped} ta hujjat allaqachon o'chirilgan edi."), messages.WARNING)
    soft_delete_selected.short_description = _("Soft delete (restore qilish mumkin)")

    def restore_selected(self, request, queryset):
        done, skipped = 0, 0
        for doc in queryset:
            if not getattr(doc, 'is_deleted', False):
                skipped += 1
                continue
            try:
                doc.restore()
                done += 1
            except Exception as e:
                self.message_user(request, _(f"#{doc.pk} restore xatosi: {e}"), messages.ERROR)
        if done:
            self.message_user(request, _(f"{done} ta hujjat tiklandi."), messages.SUCCESS)
        if skipped:
            self.message_user(request, _(f"{skipped} ta hujjat o‘chirilmagan edi."), messages.WARNING)
    restore_selected.short_description = _("Restore (soft delete dan qaytarish)")

    def hard_delete_selected(self, request, queryset):
        done = 0
        for doc in queryset:
            try:
                # Eslatma: bu haqiqiy o‘chirish. CashTransaction FKs CASCADE bo'ladi.
                doc.hard_delete()
                done += 1
            except Exception as e:
                self.message_user(request, _(f"#{doc.pk} hard delete xatosi: {e}"), messages.ERROR)
        if done:
            self.message_user(request, _(f"{done} ta hujjat butunlay o‘chirildi."), messages.SUCCESS)
    hard_delete_selected.short_description = _("Hard delete (butunlay o‘chirish)")

    # O'chirilgan hujjatda inline'lar read-only bo'lishi uchun TabularInline ichida ham tekshiruv bor.
    def has_delete_permission(self, request, obj=None):
        # Adminning "Delete" tugmasi soft delete’ni chaqiradi (model.delete -> soft_delete)
        return super().has_delete_permission(request, obj)


@admin.register(DocumentProduct)
class DocumentProductAdmin(admin.ModelAdmin):
    list_display = ('document', 'product', 'quantity', 'price', 'amount', 'currency')
    search_fields = ('product__name',)
    list_filter = ('currency',)
    autocomplete_fields = ['product', 'document']
    readonly_fields = ('amount',)

    def has_add_permission(self, request):
        return super().has_add_permission(request)

    def has_change_permission(self, request, obj=None):
        # Hujjati o'chirilgan bo'lsa — tahrirga ruxsat bermaymiz
        if obj and obj.document and getattr(obj.document, 'is_deleted', False):
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if obj and obj.document and getattr(obj.document, 'is_deleted', False):
            return False
        return super().has_delete_permission(request, obj)

@admin.register(DebtImportOffer)
class DebtImportOfferAdmin(admin.ModelAdmin):
    list_display = ("id", "debtor_user", "status", "created_by", "applied_store", "applied_document", "created_at", "expires_at")
    search_fields = ("debtor_user__username", "debtor_user__phone_number")
    list_filter = ("status", "created_at")