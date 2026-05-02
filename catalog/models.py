from datetime import timedelta

from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class SiteSettings(models.Model):
    site_name = models.CharField(max_length=200, default='Katalog.uz')
    contact_info = models.CharField(max_length=300, default="Bog'lanish: info@katalog.uz")
    telegram_bot_token = models.CharField(max_length=200, default='8747827295:AAFFp9hVKUcnswXoFuQKdiVcqXMRBsrEf_c')
    telegram_group_id = models.CharField(max_length=50, default='-1003987890658')
    telegram_owner_id = models.CharField(max_length=50, default='1077506586')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Sozlamalar'
        verbose_name_plural = 'Sozlamalar'

    def __str__(self):
        return self.site_name

    @classmethod
    def get_settings(cls):
        settings, created = cls.objects.get_or_create(
            pk=1,
            defaults={
                'site_name': 'Katalog.uz',
                'contact_info': "Bog'lanish: info@katalog.uz",
                'telegram_bot_token': '8747827295:AAFFp9hVKUcnswXoFuQKdiVcqXMRBsrEf_c',
                'telegram_group_id': '-1003987890658',
                'telegram_owner_id': '1077506586',
            }
        )
        return settings


class Category(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'name']
        verbose_name_plural = 'Categories'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def product_count(self):
        return self.products.count()


class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    name = models.CharField(max_length=300)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    previous_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    price_changed_at = models.DateTimeField(null=True, blank=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='products/')
    is_available = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    is_new = models.BooleanField(default=False)
    new_badge_enabled = models.BooleanField(default=True)
    new_until = models.DateTimeField(null=True, blank=True)
    units_per_box = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return self.name

    @property
    def is_currently_new(self):
        from django.utils import timezone
        if not self.is_new or not self.new_badge_enabled:
            return False
        if self.new_until and timezone.now() > self.new_until:
            return False
        return True

    @property
    def show_price_change(self):
        from django.utils import timezone
        if not self.previous_price or not self.price_changed_at:
            return False
        return timezone.now() <= self.price_changed_at + timedelta(days=7)
