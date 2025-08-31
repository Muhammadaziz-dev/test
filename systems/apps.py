from django.apps import AppConfig


class SystemsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'systems'

    def ready(self):
        from auditlog.registry import auditlog
        from systems.models import ProductSale, StockTransfer, ProductEntrySystem
        auditlog.register(ProductEntrySystem)
        auditlog.register(ProductSale)
        auditlog.register(StockTransfer)