from django.apps import AppConfig


class CashboxConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'cashbox'

    def ready(self):
        from auditlog.registry import auditlog
        from cashbox.models import Cashbox, CashTransaction
        auditlog.register(Cashbox)
        auditlog.register(CashTransaction)
