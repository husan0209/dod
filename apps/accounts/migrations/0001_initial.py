# Generated manually
import uuid
from decimal import Decimal

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import phonenumber_field.modelfields
from django.conf import settings
from django.core.validators import MinLengthValidator, MinValueValidator
from django_countries.fields import CountryField
from timezone_field import TimeZoneField

from apps.accounts.validators import username_validator, validate_avatar_file


def notification_default():
    return {
        "site_notifications": True,
        "email_notifications": True,
        "telegram_notifications": False,
        "bet_results": True,
        "promotions": True,
        "security_alerts": True,
        "referral_activity": True,
    }


def email_token_expires_default():
    return django.utils.timezone.now() + django.utils.timezone.timedelta(hours=24)


def phone_token_expires_default():
    return django.utils.timezone.now() + django.utils.timezone.timedelta(minutes=10)


def avatar_upload_path(instance, filename):
    return f"avatars/{instance.id}/{filename}"


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('id', models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ('email', models.EmailField(max_length=255, unique=True, db_index=True)),
                ('username', models.CharField(max_length=30, unique=True, validators=[MinLengthValidator(3), username_validator])),
                ('phone', phonenumber_field.modelfields.PhoneNumberField(blank=True, db_index=True, max_length=128, null=True, region=None, unique=True)),
                ('first_name', models.CharField(blank=True, max_length=50)),
                ('last_name', models.CharField(blank=True, max_length=50)),
                ('avatar', models.ImageField(blank=True, null=True, upload_to=avatar_upload_path, validators=[validate_avatar_file])),
                ('date_of_birth', models.DateField(blank=True, null=True)),
                ('country', CountryField(blank=True, max_length=2, null=True)),
                ('language', models.CharField(choices=[('ru', 'Русский'), ('en', 'English')], default='ru', max_length=2)),
                ('timezone', TimeZoneField(default='Europe/Moscow')),
                ('preferred_currency', models.CharField(choices=[('USD', 'USD'), ('EUR', 'EUR'), ('RUB', 'RUB'), ('UAH', 'UAH'), ('KZT', 'KZT'), ('UZS', 'UZS'), ('BYN', 'BYN'), ('BTC', 'BTC'), ('ETH', 'ETH'), ('USDT', 'USDT'), ('TON', 'TON')], default='USD', max_length=5)),
                ('balance', models.DecimalField(decimal_places=8, default=Decimal('0'), max_digits=18, validators=[MinValueValidator(0)])),
                ('is_email_verified', models.BooleanField(default=False)),
                ('is_phone_verified', models.BooleanField(default=False)),
                ('is_2fa_enabled', models.BooleanField(default=False)),
                ('two_fa_method', models.CharField(blank=True, choices=[('totp', 'Google Authenticator'), ('email', 'Email код')], max_length=10, null=True)),
                ('kyc_status', models.CharField(choices=[('none', 'Не подана'), ('pending', 'На проверке'), ('approved', 'Одобрена'), ('rejected', 'Отклонена')], default='none', max_length=10)),
                ('trust_level', models.IntegerField(choices=[(1, 'Новый'), (2, 'Базовый'), (3, 'Проверенный'), (4, 'Доверенный'), (5, 'VIP')], default=1)),
                ('is_online', models.BooleanField(default=False)),
                ('last_activity', models.DateTimeField(blank=True, null=True)),
                ('last_login_ip', models.GenericIPAddressField(blank=True, null=True)),
                ('registration_ip', models.GenericIPAddressField(blank=True, null=True)),
                ('registration_method', models.CharField(choices=[('email', 'Email'), ('google', 'Google'), ('telegram', 'Telegram'), ('phone', 'Телефон')], default='email', max_length=10)),
                ('referral_code', models.CharField(blank=True, max_length=20, unique=True)),
                ('notification_settings', models.JSONField(default=notification_default)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_staff', models.BooleanField(default=False)),
                ('is_active', models.BooleanField(default=True)),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now)),
                ('groups', models.ManyToManyField(blank=True, related_name='user_set', related_query_name='user', to='auth.group', verbose_name='groups')),
                ('user_permissions', models.ManyToManyField(blank=True, related_name='user_set', related_query_name='user', to='auth.permission', verbose_name='user permissions')),
                ('referred_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='referrals', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Пользователь',
                'verbose_name_plural': 'Пользователи',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddConstraint(
            model_name='user',
            constraint=models.CheckConstraint(check=models.Q(('balance__gte', 0)), name='user_balance_non_negative'),
        ),
        migrations.AddIndex(model_name='user', index=models.Index(fields=['email'], name='accounts_us_email_idx')),
        migrations.AddIndex(model_name='user', index=models.Index(fields=['username'], name='accounts_us_username_idx')),
        migrations.AddIndex(model_name='user', index=models.Index(fields=['phone'], name='accounts_us_phone_idx')),
        migrations.AddIndex(model_name='user', index=models.Index(fields=['referral_code'], name='accounts_us_referral_idx')),
        migrations.AddIndex(model_name='user', index=models.Index(fields=['created_at'], name='accounts_us_created_idx')),

        migrations.CreateModel(
            name='LoginHistory',
            fields=[
                ('id', models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ('ip_address', models.GenericIPAddressField()),
                ('country', models.CharField(blank=True, max_length=100, null=True)),
                ('city', models.CharField(blank=True, max_length=100, null=True)),
                ('device_type', models.CharField(choices=[('desktop', 'Компьютер'), ('mobile', 'Мобильный'), ('tablet', 'Планшет'), ('unknown', 'Неизвестно')], max_length=20)),
                ('browser', models.CharField(max_length=100)),
                ('os', models.CharField(max_length=100)),
                ('device_name', models.CharField(max_length=200)),
                ('user_agent', models.TextField()),
                ('login_method', models.CharField(choices=[('email', 'Email + пароль'), ('google', 'Google'), ('telegram', 'Telegram'), ('phone', 'Телефон + SMS')], max_length=20)),
                ('is_successful', models.BooleanField(default=True)),
                ('failure_reason', models.CharField(blank=True, max_length=50, null=True)),
                ('is_suspicious', models.BooleanField(default=False)),
                ('session_key', models.CharField(blank=True, max_length=40, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='login_history', to=settings.AUTH_USER_MODEL)),
            ],
            options={'verbose_name': 'История входов', 'ordering': ['-created_at']},
        ),
        migrations.AddIndex(model_name='loginhistory', index=models.Index(fields=['user', 'created_at'], name='accounts_loginhistory_user_created_idx')),
        migrations.AddIndex(model_name='loginhistory', index=models.Index(fields=['ip_address'], name='accounts_loginhistory_ip_idx')),

        migrations.CreateModel(
            name='ActiveSession',
            fields=[
                ('id', models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ('session_key', models.CharField(max_length=40, unique=True)),
                ('ip_address', models.GenericIPAddressField()),
                ('device_type', models.CharField(max_length=20)),
                ('browser', models.CharField(max_length=100)),
                ('os', models.CharField(max_length=100)),
                ('device_name', models.CharField(max_length=200)),
                ('country', models.CharField(blank=True, max_length=100, null=True)),
                ('is_current', models.BooleanField(default=False)),
                ('last_activity', models.DateTimeField(auto_now=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='active_sessions', to=settings.AUTH_USER_MODEL)),
            ],
            options={'verbose_name': 'Активная сессия', 'ordering': ['-last_activity']},
        ),

        migrations.CreateModel(
            name='EmailVerification',
            fields=[
                ('id', models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ('email', models.EmailField(max_length=254)),
                ('token', models.CharField(max_length=64, unique=True)),
                ('is_used', models.BooleanField(default=False)),
                ('expires_at', models.DateTimeField(default=email_token_expires_default)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at']},
        ),

        migrations.CreateModel(
            name='PhoneVerification',
            fields=[
                ('id', models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ('phone', phonenumber_field.modelfields.PhoneNumberField(max_length=128, region=None)),
                ('code', models.CharField(max_length=6)),
                ('is_used', models.BooleanField(default=False)),
                ('attempts', models.IntegerField(default=0)),
                ('expires_at', models.DateTimeField(default=phone_token_expires_default)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at']},
        ),

        migrations.CreateModel(
            name='BackupCode',
            fields=[
                ('id', models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ('code', models.CharField(max_length=128)),
                ('is_used', models.BooleanField(default=False)),
                ('used_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='backup_codes', to=settings.AUTH_USER_MODEL)),
            ],
        ),

        migrations.CreateModel(
            name='LinkedAccount',
            fields=[
                ('id', models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ('provider', models.CharField(choices=[('google', 'Google'), ('telegram', 'Telegram'), ('phone', 'Телефон')], max_length=20)),
                ('provider_id', models.CharField(max_length=255)),
                ('provider_email', models.EmailField(blank=True, max_length=254, null=True)),
                ('provider_username', models.CharField(blank=True, max_length=255, null=True)),
                ('provider_avatar', models.URLField(blank=True, null=True)),
                ('is_primary', models.BooleanField(default=False)),
                ('linked_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='linked_accounts', to=settings.AUTH_USER_MODEL)),
            ],
            options={'verbose_name': 'Привязанный аккаунт'},
        ),
        migrations.AlterUniqueTogether(name='linkedaccount', unique_together={('provider', 'provider_id')}),
    ]
