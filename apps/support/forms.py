from django import forms
from .models import Ticket, Message, FAQArticle


class TicketCreateForm(forms.ModelForm):
    """Form for creating new tickets."""

    class Meta:
        model = Ticket
        fields = ['category', 'subject', 'description']
        widgets = {
            'subject': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Кратко опишите проблему'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Подробно опишите проблему, шаги воспроизведения, ожидаемый результат'
            }),
            'category': forms.Select(attrs={'class': 'form-control'}),
        }

    def clean_subject(self):
        subject = self.cleaned_data['subject']
        if len(subject) < 5:
            raise forms.ValidationError('Тема должна содержать минимум 5 символов')
        return subject

    def clean_description(self):
        description = self.cleaned_data['description']
        if len(description) < 20:
            raise forms.ValidationError('Описание должно содержать минимум 20 символов')
        return description


class TicketReplyForm(forms.Form):
    """Форма ответа в тикет"""
    text = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Введите ваш ответ...'
        }),
        required=True,
        min_length=1
    )


class TicketStatusForm(forms.Form):
    """Форма изменения статуса тикета (для операторов)"""
    status = forms.ChoiceField(
        choices=Ticket.STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    reason = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Причина изменения статуса (опционально)'
        })
    )


class TicketEscalateForm(forms.Form):
    """Форма эскалации тикета"""
    reason = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Причина эскалации'
        }),
        required=True,
        min_length=10
    )
    escalate_to = forms.ModelChoiceField(
        queryset=None,  # Будет установлен в view
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text='Оставить пустым для автоматического выбора'
    )


class FAQArticleForm(forms.ModelForm):
    class Meta:
        model = FAQArticle
        fields = ['question', 'answer', 'category', 'keywords']
