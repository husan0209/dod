from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import GameSession, GameType


@receiver(post_save, sender=GameSession)
def update_game_statistics(sender, instance, created, **kwargs):
    """Обновить статистику после завершения игры"""
    if created or not instance.completed_at:
        return
    
    game_type = instance.game_type
    
    # Обновить счётчики
    game_type.total_bets += 1
    game_type.total_wagered_usd += instance.bet_amount_usd
    
    if instance.win_amount > 0:
        game_type.total_won_usd += instance.win_amount
    
    game_type.save(update_fields=['total_bets', 'total_wagered_usd', 'total_won_usd'])
