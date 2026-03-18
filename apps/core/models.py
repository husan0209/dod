import uuid
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.cache import cache


class PlatformSettings(models.Model):
    """Глобальные настройки платформы. Singleton."""

    # Общие настройки
    site_name = models.CharField(max_length=100, default='DOD')
    is_maintenance_mode = models.BooleanField(default=False, verbose_name='Технические работы')
    maintenance_message = models.TextField(blank=True, default='На сайте проводятся технические работы. Пожалуйста, зайдите позже.')
    
    # Реферальная программа
    referral_commission_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=10.00,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    referral_signup_bonus_usd = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    # Финансовые ограничения
    min_withdrawal_usd = models.DecimalField(max_digits=10, decimal_places=2, default=10.00)
    max_daily_withdrawal_usd = models.DecimalField(max_digits=10, decimal_places=2, default=5000.00)
    withdrawal_fee_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    
    # KYC настройки
    require_kyc_for_withdrawal = models.BooleanField(default=True)
    kyc_auto_approve_limit_usd = models.DecimalField(max_digits=10, decimal_places=2, default=100.00)
    
    # Поддержка
    support_email = models.EmailField(default='support@dod.com')
    telegram_support_link = models.URLField(blank=True)
    
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Настройки платформы'
        verbose_name_plural = 'Настройки платформы'

    def __str__(self):
        return "Global Platform Settings"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)
        cache.delete('platform_settings')

    @classmethod
    def get_settings(cls):
        return cache.get_or_set('platform_settings', lambda: cls.objects.get_or_create(pk=1)[0])


class Banner(models.Model):
    """Рекламные баннеры для слайдеров."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200, verbose_name='Заголовок')
    subtitle = models.CharField(max_length=300, blank=True, verbose_name='Подзаголовок')
    image = models.ImageField(upload_to='content/banners/', verbose_name='Изображение')
    link = models.CharField(max_length=500, blank=True, verbose_name='Ссылка')
    
    location = models.CharField(
        max_length=50,
        choices=[('main', 'Главная'), ('sports', 'Спорт'), ('casino', 'Казино'), ('miniapp', 'Mini App')],
        default='main'
    )
    
    is_active = models.BooleanField(default=True, verbose_name='Активен')
    sort_order = models.IntegerField(default=0, verbose_name='Порядок')
    
    start_date = models.DateTimeField(null=True, blank=True, verbose_name='Дата начала')
    end_date = models.DateTimeField(null=True, blank=True, verbose_name='Дата окончания')
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Баннер'
        verbose_name_plural = 'Баннеры'
        ordering = ['sort_order', '-created_at']

    def __str__(self):
        return self.title


class Promotion(models.Model):
    """Акции и спецпредложения."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200, verbose_name='Название акции')
    slug = models.SlugField(unique=True)
    short_description = models.TextField(max_length=500, verbose_name='Краткое описание')
    content = models.TextField(verbose_name='Полный текст (HTML)')
    
    image = models.ImageField(upload_to='content/promotions/', verbose_name='Обложка')
    badge_text = models.CharField(max_length=50, blank=True, verbose_name='Текст на бейдже')  # например "HOT" или "NEW"
    
    is_active = models.BooleanField(default=True, verbose_name='Активна')
    is_featured = models.BooleanField(default=False, verbose_name='Закреплена')
    
    start_date = models.DateTimeField(null=True, blank=True, verbose_name='Дата старта')
    end_date = models.DateTimeField(null=True, blank=True, verbose_name='Дата окончания')
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Акция'
        verbose_name_plural = 'Акции'
        ordering = ['-is_featured', '-created_at']

    def __str__(self):
        return self.title


class StaticPage(models.Model):
    """Статичные страницы (О нас, Правила, Контакты)."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200, verbose_name='Заголовок')
    slug = models.SlugField(unique=True)
    content = models.TextField(verbose_name='Контент (HTML)')
    
    meta_title = models.CharField(max_length=200, blank=True)
    meta_description = models.TextField(blank=True)
    
    is_active = models.BooleanField(default=True, verbose_name='Активна')
    show_in_footer = models.BooleanField(default=True, verbose_name='В футере')
    
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Статическая страница'
        verbose_name_plural = 'Статические страницы'

    def __str__(self):
        return self.title
