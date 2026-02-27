from allauth.account.adapter import DefaultAccountAdapter

from apps.referral.services.referral_service import ReferralService


class CustomAccountAdapter(DefaultAccountAdapter):

    def save_user(self, request, user, form, commit=True):
        user = super().save_user(request, user, form, commit)

        if commit:
            ReferralService.process_referral_registration(user, request)

        return user
