from django.db import models
from django.conf import settings

class Notification(models.Model):
    recipient  = models.ForeignKey(settings.AUTH_USER_MODEL,
                                   on_delete=models.CASCADE,
                                   related_name='notifications')
    verb       = models.CharField(max_length=255)
    data       = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    read       = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"To {self.recipient}: {self.verb}"
