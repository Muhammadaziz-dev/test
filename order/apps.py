from django.apps import AppConfig


class OrderConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'order'

    def ready(self):
        import order.signals
        from auditlog.registry import auditlog
        from order.models import Order, ProductOrder
        auditlog.register(Order)
        auditlog.register(ProductOrder)