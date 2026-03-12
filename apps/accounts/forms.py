from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, AuthenticationForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from phonenumber_field.formfields import PhoneNumberField

from .models import User


class CustomUserCreationForm(UserCreationForm):
    """
    Форма регистрации нового пользователя по email.
    """
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'Введите email',
            'autocomplete': 'email'
        })
    )
    username = forms.CharField(
        required=True,
        max_length=30,
        min_length=3,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Введите имя пользователя',
            'autocomplete': 'username'
        })
    )
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Введите пароль',
            'autocomplete': 'new-password'
        })
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Подтвердите пароль',
            'autocomplete': 'new-password'
        })
    )
    phone = PhoneNumberField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': '+7XXXXXXXXXX',
            'autocomplete': 'tel'
        })
    )
    language = forms.ChoiceField(
        choices=[('ru', 'Русский'), ('en', 'English')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("email", "username", "password1", "password2", "phone", "language")
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("Пользователь с этим email уже зарегистрирован.")
        return email
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError("Пользователь с этим именем уже существует.")
        return username
    
    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if phone and User.objects.filter(phone=phone).exists():
            raise ValidationError("Пользователь с этим номером телефона уже существует.")
        return phone
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email'].lower()
        user.username = self.cleaned_data['username'].lower()
        if commit:
            user.save()
        return user


class CustomUserChangeForm(UserChangeForm):
    """
    Форма изменения профиля пользователя.
    """
    class Meta:
        model = User
        fields = ("email", "username", "first_name", "last_name", "phone", "avatar", "date_of_birth", "country", "language", "timezone", "preferred_currency")
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-input', 'readonly': 'readonly'}),
            'username': forms.TextInput(attrs={'class': 'form-input', 'readonly': 'readonly'}),
            'first_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Имя'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Фамилия'}),
            'phone': forms.TextInput(attrs={'class': 'form-input'}),
            'avatar': forms.FileInput(attrs={'class': 'form-file', 'accept': 'image/*'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'country': forms.Select(attrs={'class': 'form-select'}),
            'language': forms.Select(attrs={'class': 'form-select'}),
            'timezone': forms.Select(attrs={'class': 'form-select'}),
            'preferred_currency': forms.Select(attrs={'class': 'form-select'}),
        }


class EmailAuthenticationForm(AuthenticationForm):
    """
    Форма входа по email и пароль.
    """
    username = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'Email',
            'autocomplete': 'email'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Пароль',
            'autocomplete': 'current-password'
        })
    )


class EmailVerificationForm(forms.Form):
    """
    Форма для ввода кода подтверждения email.
    """
    code = forms.CharField(
        max_length=64,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Введите код из письма',
            'autocomplete': 'off'
        })
    )


class PhoneVerificationForm(forms.Form):
    """
    Форма ввода номера телефона для верификации.
    """
    phone = PhoneNumberField(
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': '+7XXXXXXXXXX',
            'autocomplete': 'tel'
        })
    )


class PhoneVerificationCodeForm(forms.Form):
    """
    Форма ввода SMS кода подтверждения.
    """
    code = forms.CharField(
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': '000000',
            'autocomplete': 'off',
            'inputmode': 'numeric'
        })
    )
    
    def clean_code(self):
        code = self.cleaned_data.get('code')
        if code and not code.isdigit():
            raise ValidationError("Код должен состоять из цифр.")
        return code


class PasswordResetForm(forms.Form):
    """
    Форма запроса сброса пароля.
    """
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'Email',
            'autocomplete': 'email'
        })
    )


class SetPasswordForm(forms.Form):
    """
    Форма для установки нового пароля (сброс пароля / смена пароля).
    """
    new_password1 = forms.CharField(
        label="Новый пароль",
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Новый пароль',
            'autocomplete': 'new-password'
        })
    )
    new_password2 = forms.CharField(
        label="Подтвердите пароль",
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Подтвердите пароль',
            'autocomplete': 'new-password'
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('new_password1')
        password2 = cleaned_data.get('new_password2')
        
        if password1 and password2 and password1 != password2:
            raise ValidationError("Пароли не совпадают.")
        
        if password1:
            try:
                validate_password(password1)
            except ValidationError as e:
                self.add_error('new_password1', e)
        
        return cleaned_data


class ChangePasswordForm(forms.Form):
    """
    Форма смены пароля (требует старый пароль).
    """
    old_password = forms.CharField(
        label="Текущий пароль",
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Текущий пароль',
            'autocomplete': 'current-password'
        })
    )
    new_password1 = forms.CharField(
        label="Новый пароль",
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Новый пароль',
            'autocomplete': 'new-password'
        })
    )
    new_password2 = forms.CharField(
        label="Подтвердите пароль",
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Подтвердите пароль',
            'autocomplete': 'new-password'
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('new_password1')
        password2 = cleaned_data.get('new_password2')
        
        if password1 and password2 and password1 != password2:
            raise ValidationError("Новые пароли не совпадают.")
        
        if password1:
            try:
                validate_password(password1)
            except ValidationError as e:
                self.add_error('new_password1', e)
        
        return cleaned_data


class Enable2FAForm(forms.Form):
    """
    Форма подтверждения TOTP кода при включении 2FA.
    """
    totp_code = forms.CharField(
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': '000000',
            'autocomplete': 'off',
            'inputmode': 'numeric'
        })
    )
    
    def clean_totp_code(self):
        code = self.cleaned_data.get('totp_code')
        if code and not code.isdigit():
            raise ValidationError("Код должен состоять из 6 цифр.")
        return code


class Disable2FAForm(forms.Form):
    """
    Форма отключения 2FA (требует пароль для подтверждения).
    """
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Пароль',
            'autocomplete': 'current-password'
        })
    )


class Verify2FAForm(forms.Form):
    """
    Форма при вводе TOTP кода при входе.
    """
    totp_code = forms.CharField(
        max_length=6,
        min_length=6,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Код из приложения (если есть)',
            'autocomplete': 'off',
            'inputmode': 'numeric'
        })
    )
    backup_code = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'или резервный код',
            'autocomplete': 'off'
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        totp_code = cleaned_data.get('totp_code')
        backup_code = cleaned_data.get('backup_code')
        
        if not (totp_code or backup_code):
            raise ValidationError("Введите либо TOTP код, либо резервный код.")
        
        return cleaned_data


class LinkPhoneForm(forms.Form):
    """
    Форма для привязки номера телефона к аккаунту.
    """
    phone = PhoneNumberField(
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': '+7XXXXXXXXXX',
            'autocomplete': 'tel'
        })
    )
