# expense/admin.py
from django.contrib import admin, messages
from django.utils.translation import gettext_lazy as _
from .models import Expense


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = (
        'date', 'store', 'user', 'get_full_reason', 'amount', 'currency',
        'exchange_rate', 'cash_transaction_display', 'is_deleted', 'deleted_at'
    )
    list_filter = ('store', 'user', 'reason', 'currency', 'is_deleted', 'date')
    search_fields = (
        'note', 'custom_reason', 'store__name',
        'user__user__username', 'user__user__phone_number'
    )
    readonly_fields = ('date', 'cash_transaction', 'exchange_rate', 'is_deleted', 'deleted_at')
    actions = ['soft_delete_selected', 'restore_selected', 'hard_delete_selected']
    ordering = ['-date']
    # Eslatma: autocomplete_fields qo'ymadik (E040 bo'lmasin)

    def get_readonly_fields(self, request, obj=None):
        # Soft-deleted yozuvni to'liq read-only qilamiz
        base = list(super().get_readonly_fields(request, obj))
        if obj and obj.is_deleted:
            base += [
                'store', 'user', 'reason', 'custom_reason',
                'amount', 'currency', 'note'
            ]
        return tuple(base)

    def cash_transaction_display(self, obj):
        if obj.cash_transaction:
            return f"#{obj.cash_transaction.pk} - {obj.cash_transaction.amount}"
        return "—"
    cash_transaction_display.short_description = "Kassa tranzaktsiyasi"

    # ----- Change view'dagi Delete tugmasini soft deletega yo'naltirish -----
    def delete_model(self, request, obj):
        try:
            obj.soft_delete()
            self.message_user(request, _("Xarajat soft delete qilindi."), messages.SUCCESS)
        except Exception as e:
            self.message_user(request, _("Soft delete xatosi: %s") % e, messages.ERROR)

    def delete_queryset(self, request, queryset):
        done, errors = 0, 0
        for obj in queryset:
            try:
                obj.soft_delete()
                done += 1
            except Exception:
                errors += 1
        if done:
            self.message_user(request, _(f"{done} ta xarajat soft delete qilindi."), messages.SUCCESS)
        if errors:
            self.message_user(request, _(f"{errors} ta yozuv soft delete qilinmadi."), messages.ERROR)

    # ----- Actions -----
    def soft_delete_selected(self, request, queryset):
        done, skipped = 0, 0
        for exp in queryset:
            if exp.is_deleted:
                skipped += 1
                continue
            try:
                exp.soft_delete()
                done += 1
            except Exception as e:
                self.message_user(request, _(f"#{exp.pk} soft delete xatosi: {e}"), messages.ERROR)
        if done:
            self.message_user(request, _(f"{done} ta xarajat soft delete qilindi."), messages.SUCCESS)
        if skipped:
            self.message_user(request, _(f"{skipped} ta xarajat allaqachon o'chirilgan edi."), messages.WARNING)
    soft_delete_selected.short_description = _("Soft delete")

    def restore_selected(self, request, queryset):
        done, skipped = 0, 0
        for exp in queryset:
            if not exp.is_deleted:
                skipped += 1
                continue
            try:
                exp.restore()
                done += 1
            except Exception as e:
                self.message_user(request, _(f"#{exp.pk} restore xatosi: {e}"), messages.ERROR)
        if done:
            self.message_user(request, _(f"{done} ta xarajat tiklandi."), messages.SUCCESS)
        if skipped:
            self.message_user(request, _(f"{skipped} ta xarajat o‘chirilmagan edi."), messages.WARNING)
    restore_selected.short_description = _("Restore")

    def hard_delete_selected(self, request, queryset):
        done = 0
        for exp in queryset:
            try:
                # hard delete: kassa item avval model.delete() ichida o'chiriladi
                exp.delete()
                done += 1
            except Exception as e:
                self.message_user(request, _(f"#{exp.pk} hard delete xatosi: {e}"), messages.ERROR)
        if done:
            self.message_user(request, _(f"{done} ta xarajat butunlay o‘chirildi."), messages.SUCCESS)
    hard_delete_selected.short_description = _("Hard delete (butunlay o‘chirish)")
