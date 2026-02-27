import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings

from apps.accounts.models import User


class AdminRole(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50, unique=True, verbose_name='Название роли')
    slug = models.SlugField(unique=True, verbose_name='Слаг')
    description = models.TextField(blank=True, verbose_name='Описание')
    
    # Permissions structure
    permissions = models.JSONField(default=dict, verbose_name='Права доступа')
    
    # Hierarchy
    level = models.IntegerField(default=0, verbose_name='Уровень доступа')
    
    # System settings
    is_system = models.BooleanField(default=False, verbose_name='Системная роль')
    is_active = models.BooleanField(default=True, verbose_name='Активна')
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Роль администратора'
        verbose_name_plural = 'Роли администраторов'
        ordering = ['-level']

    def __str__(self):
        return f"{self.name} (level {self.level})"


class AdminProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='admin_profile', verbose_name='Пользователь')
    role = models.ForeignKey(AdminRole, on_delete=models.PROTECT, verbose_name='Роль')
    
    # Custom permissions (override role permissions)
    custom_permissions = models.JSONField(default=dict, verbose_name='Индивидуальные права')
    
    # Notification settings
    receive_admin_notifications = models.BooleanField(default=True, verbose_name='Получать уведомления админа')
    notification_channels = models.JSONField(
        default=dict,
        verbose_name='Каналы уведомлений',
        help_text='{"email": true, "telegram": true, "dashboard": true}'
    )
    
    # Work schedule
    work_schedule = models.JSONField(
        default=dict,
        verbose_name='График работы',
        help_text='{"mon": {"start": "09:00", "end": "18:00"}, ...}'
    )
    
    # Statistics
    total_actions = models.IntegerField(default=0, verbose_name='Всего действий')
    last_action_at = models.DateTimeField(null=True, blank=True, verbose_name='Последнее действие')
    
    # IP whitelist
    ip_whitelist = models.JSONField(default=list, verbose_name='Белый список IP')
    
    # Activity
    is_admin_active = models.BooleanField(default=True, verbose_name='Активен как админ')
    deactivated_at = models.DateTimeField(null=True, blank=True, verbose_name='Деактивирован')
    deactivated_reason = models.TextField(blank=True, verbose_name='Причина деактивации')
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Профиль администратора'
        verbose_name_plural = 'Профили администраторов'

    def __str__(self):
        return f"{self.user.username} - {self.role.name}"

    def has_permission(self, module, action):
        """Check if admin has permission for module.action"""
        # Superadmin has all permissions
        if self.role.slug == 'superadmin':
            return True

        # Check custom permissions first (override role)
        if module in self.custom_permissions:
            custom = self.custom_permissions[module]
            if action in custom:
                return custom[action]

        # Check role permissions
        role_perms = self.role.permissions
        if module in role_perms:
            return role_perms[module].get(action, False)

        return False

    def get_permission_value(self, module, action):
        """Get permission value (can be number or boolean)"""
        # Check custom permissions first
        if module in self.custom_permissions:
            custom = self.custom_permissions[module]
            if action in custom:
                return custom[action]

        # Check role permissions
        role_perms = self.role.permissions
        if module in role_perms:
            return role_perms[module].get(action)

        return None
