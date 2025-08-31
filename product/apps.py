from django.apps import AppConfig



class ProductConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'product'

    def ready(self):
        from auditlog.registry import auditlog
        from .models import Product, StockEntry
        auditlog.register(Product)
        auditlog.register(StockEntry)