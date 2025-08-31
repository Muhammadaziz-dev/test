from django.db import models
from django.utils.text import slugify

from platform_user.models import PlatformUser


def generate_unique_slug(model, name, base_slug=None):
    if not base_slug:
        base_slug = slugify(name)
    if not base_slug:
        base_slug = 'default-slug'

    unique_slug = base_slug
    counter = 1

    while model.objects.filter(slug=unique_slug).exists():
        unique_slug = f"{base_slug}-{counter}"
        counter += 1

    return unique_slug


class Category(models.Model):
    name = models.CharField(max_length=500)
    slug = models.SlugField(unique=True, blank=True, null=True, editable=False)
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name="Ota kategoriya"
    )
    image = models.ImageField(
        upload_to="product/category/images",
        blank=True,
        null=True
    )
    user = models.ForeignKey(
        PlatformUser,
        on_delete=models.CASCADE,
        related_name="categories"
    )

    class Meta:
        verbose_name = "Kategoriya"
        verbose_name_plural = "Kategoriyalar"
        ordering = ['name']

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(Category, self.name)
        super().save(*args, **kwargs)
