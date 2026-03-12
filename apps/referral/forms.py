from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from .models import Referral, PromoLink, Commission, PartnerPayout
from django.contrib.auth import get_user_model

User = get_user_model()


class ReferralStatusUpdateForm(forms.ModelForm):
    """Форма для обновления статуса реферала"""
    
    class Meta:
        model = Referral
        fields = ['status']
        widgets = {
            'status': forms.Select(attrs={
                'class': 'w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-indigo-500'
            })
        }

    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('status')
        
        if not status:
            raise ValidationError(_('Статус обязателен'))
        
        return cleaned_data


class ReferralManualAdjustmentForm(forms.Form):
    """Форма для ручного корректирования данных реферала"""
    
    ADJUSTMENT_TYPE_CHOICES = [
        ('balance_adjustment', 'Корректировка баланса'),
        ('commission_adjustment', 'Корректировка комиссии'),
        ('fraud_flag', 'Добавить фрод флаг'),
        ('remove_fraud_flag', 'Удалить фрод флаг'),
    ]
    
    adjustment_type = forms.ChoiceField(
        choices=ADJUSTMENT_TYPE_CHOICES,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-indigo-500'
        }),
        label='Тип корректировки'
    )
    
    amount = forms.DecimalField(
        max_digits=18,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-indigo-500',
            'placeholder': 'Сумма (если применимо)'
        }),
        label='Сумма'
    )
    
    reason = forms.CharField(
        max_length=500,
        required=True,
        widget=forms.Textarea(attrs={
            'class': 'w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-indigo-500',
            'rows': 3,
            'placeholder': 'Причина корректировки'
        }),
        label='Причина'
    )
    
    flag_value = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-indigo-500',
            'placeholder': 'Значение флага'
        }),
        label='Значение флага (для фрод флагов)'
    )

    def clean(self):
        cleaned_data = super().clean()
        adjustment_type = cleaned_data.get('adjustment_type')
        amount = cleaned_data.get('amount')
        flag_value = cleaned_data.get('flag_value')
        
        if adjustment_type in ['balance_adjustment', 'commission_adjustment']:
            if amount is None:
                raise ValidationError(_('Сумма обязательна для этого типа корректировки'))
        
        if adjustment_type in ['fraud_flag', 'remove_fraud_flag']:
            if not flag_value:
                raise ValidationError(_('Значение флага обязательно'))
        
        return cleaned_data


class PromoLinkForm(forms.ModelForm):
    """Форма для создания/редактирования промо-ссылок"""
    
    class Meta:
        model = PromoLink
        fields = ['name', 'slug', 'utm_source', 'utm_medium', 'utm_campaign', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-indigo-500',
                'placeholder': 'Название ссылки (например: VK Campaign)',
                'required': True
            }),
            'slug': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-indigo-500',
                'placeholder': 'Уникальный слаг (vk-campaign)',
                'required': True
            }),
            'utm_source': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-indigo-500',
                'placeholder': 'Источник трафика (например: vk)',
            }),
            'utm_medium': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-indigo-500',
                'placeholder': 'Средство (например: social)',
            }),
            'utm_campaign': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-indigo-500',
                'placeholder': 'Кампания (например: march2025)',
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 rounded border-slate-600',
            }),
        }
        labels = {
            'name': 'Название',
            'slug': 'Слаг (ID)',
            'utm_source': 'UTM Source (факультативно)',
            'utm_medium': 'UTM Medium (факультативно)',
            'utm_campaign': 'UTM Campaign (факультативно)',
            'is_active': 'Активна',
        }

    def clean_slug(self):
        slug = self.cleaned_data.get('slug')
        if slug and not slug.replace('-', '').replace('_', '').isalnum():
            raise ValidationError(_('Слаг может содержать только буквы, цифры, дефисы и подчеркивания'))
        return slug


class CommissionApprovalForm(forms.ModelForm):
    """Форма для одобрения комиссий"""
    
    class Meta:
        model = Commission
        fields = ['status', 'notes']
        widgets = {
            'status': forms.Select(attrs={
                'class': 'w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-indigo-500'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-indigo-500',
                'rows': 3,
                'placeholder': 'Дополнительные примечания'
            }),
        }
        labels = {
            'status': 'Статус',
            'notes': 'Примечания',
        }


class PartnerPayoutForm(forms.ModelForm):
    """Форма для создания выплат партнёру"""
    
    class Meta:
        model = PartnerPayout
        fields = ['amount', 'payout_method']
        widgets = {
            'amount': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-indigo-500',
                'placeholder': 'Сумма для выплаты',
                'step': '0.01',
                'min': '0',
                'required': True
            }),
            'payout_method': forms.Select(attrs={
                'class': 'w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-indigo-500',
                'required': True
            }),
        }
        labels = {
            'amount': 'Сумма выплаты',
            'payout_method': 'Способ выплаты',
        }

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount and amount <= 0:
            raise ValidationError(_('Сумма должна быть больше нуля'))
        return amount
