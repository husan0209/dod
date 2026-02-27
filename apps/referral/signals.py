from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

from .models import PartnerProfile, PartnerTier

User = get_user_model()


@receiver(post_save, sender=User)
def create_partner_profile(sender, instance, created, **kwargs):
    if created:
        starter_tier = PartnerTier.objects.filter(slug='starter').first()
        if starter_tier:
            PartnerProfile.objects.create(user=instance, tier=starter_tier)
