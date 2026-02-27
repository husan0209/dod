from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import OperatorProfile

User = get_user_model()


@receiver(post_save, sender=User)
def create_operator_profile(sender, instance, created, **kwargs):
    """Create OperatorProfile for new staff users."""
    if instance.is_staff and not hasattr(instance, 'operator_profile'):
        OperatorProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_operator_profile(sender, instance, **kwargs):
    """Save OperatorProfile when User is saved."""
    if hasattr(instance, 'operator_profile'):
        instance.operator_profile.save()
