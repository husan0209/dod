from decimal import Decimal
from ..models import CasinoSettings
from ..services.provably_fair import ProvablyFairService
from ..services.casino_service import CasinoService
from .base import BaseGame


class DiceGame(BaseGame):
    """
    Dice: over/under цель от 0.01 до 99.98.
    """

    HOUSE_EDGE = Decimal('2.00')

    def __init__(self):
        super().__init__('dice')

    def play(self, user, bet_amount, target, condition, currency_code):
        """Сыграть в Dice."""
        settings = CasinoSettings.get_settings()
        
        # Валидация
        if bet_amount < settings.dice_min_bet or bet_amount > settings.dice_max_bet:
            raise ValueError("Неверная сумма ставки")
        
        if not (Decimal('0.01') <= target <= Decimal('99.98')):
            raise ValueError("Цель должна быть от 0.01 до 99.98")
        
        if condition not in ['over', 'under']:
            raise ValueError("Условие должно быть 'over' или 'under'")
        
        # Рассчитать шанс и множитель
        win_chance = (Decimal('99.99') - target) if condition == 'over' else target
        multiplier = (Decimal('100') - self.HOUSE_EDGE) / win_chance
        
        # Создать сессию
        session, result_hash = CasinoService.create_game_session(
            user, 'dice', bet_amount, currency_code
        )
        
        # Сгенерировать результат
        result = ProvablyFairService.generate_dice_result(result_hash)
        
        # Определить выигрыш
        if condition == 'over':
            won = result > target
        else:
            won = result < target
        
        win_amount = bet_amount * multiplier if won else 0
        
        # Завершить игру
        game_data = {
            "target": str(target),
            "condition": condition,
            "result": str(result),
            "multiplier": str(multiplier),
            "win_chance": str(win_chance)
        }
        
        CasinoService.complete_game(session, win_amount, game_data)
        
        return session

    def validate_bet(self, user, bet_data):
        settings = CasinoSettings.get_settings()
        bet_amount = bet_data.get('bet_amount', 0)
        target = bet_data.get('target', 50)
        condition = bet_data.get('condition', 'over')
        
        if bet_amount < settings.dice_min_bet or bet_amount > settings.dice_max_bet:
            return False, "Неверная сумма ставки"
        
        if not (Decimal('0.01') <= Decimal(target) <= Decimal('99.98')):
            return False, "Цель должна быть от 0.01 до 99.98"
        
        if condition not in ['over', 'under']:
            return False, "Условие должно быть 'over' или 'under'"
        
        win_chance = (Decimal('99.99') - Decimal(target)) if condition == 'over' else Decimal(target)
        if win_chance < Decimal('1') or win_chance > Decimal('98'):
            return False, "Шанс выигрыша должен быть от 1% до 98%"
        
        return True, ""

    def get_result(self, game_session):
        return game_session.game_data
