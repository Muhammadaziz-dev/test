from django.apps import AppConfig


class PlatformUserConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'platform_user'

    def ready(self):
        import platform_user.signals