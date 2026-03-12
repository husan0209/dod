from django import forms

from apps.wallet.models import KYCVerification


class KYCStep1Form(forms.ModelForm):
    """
    Шаг 1: личные данные и информация о документе.
    """

    class Meta:
        model = KYCVerification
        fields = [
            "document_type",
            "full_name",
            "document_number",
            "date_of_birth",
            "country_of_issue",
            "expiry_date",
            "address",
        ]
        widgets = {
            "date_of_birth": forms.DateInput(attrs={"type": "date"}),
            "expiry_date": forms.DateInput(attrs={"type": "date"}),
            "address": forms.Textarea(attrs={"rows": 3}),
        }


class KYCStep2Form(forms.ModelForm):
    """
    Шаг 2: загрузка фото документа.
    """

    class Meta:
        model = KYCVerification
        fields = ["document_front", "document_back"]


class KYCStep3Form(forms.ModelForm):
    """
    Шаг 3: селфи с документом.
    """

    class Meta:
        model = KYCVerification
        fields = ["selfie_with_document"]

