from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


def user_profile_path(instance, filename):
    return f'users/{instance.username}/profiles/{filename}'

class CustomUser(AbstractUser):
    class Gender(models.TextChoices):
        MALE = 'male', _('Erkak')
        FEMALE = 'female', _('Ayol')

    phone_number = models.CharField(_("Telefon raqam"), max_length=15, unique=True)
    profile_image = models.ImageField(
        _("Profil rasmi"),
        upload_to=user_profile_path,
        blank=True,
        null=True
    )
    gender = models.CharField(_("Jinsi"), max_length=6, choices=Gender.choices, null=True, blank=True)


    def __str__(self):
        return self.get_full_name() or self.username

    class Meta:
        ordering = ['-id']