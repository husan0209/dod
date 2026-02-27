from decimal import Decimal
from ..models import CasinoSettings
from ..services.provably_fair import ProvablyFairService
from ..services.casino_service import CasinoService
from .base import BaseGame


class PlinkoGame(BaseGame):
    """
    Plinko: шарик падает через пины, 3 уровня риска.
    """

    MULTIPLIERS = {
        'low': {
            8: [110, 41, 10, 5, 3, 1.5, 1, 0.5, 0.3],
            12: [110, 41, 10, 5, 3, 1.5, 1, 0.5, 0.3],  # упрощённо
            16: [110, 41, 10, 5, 3, 1.5, 1, 0.5, 0.3],  # упрощённо
        },
        'medium': {
            8: [110, 41, 10, 5, 3, 1.5, 1, 0.5, 0.3],
            12: [110, 41, 10, 5, 3, 1.5, 1, 0.5, 0.3],
            16: [110, 41, 10, 5, 3, 1.5, 1, 0.5, 0.3],
        },
        'high': {
            8: [110, 41, 10, 5, 3, 1.5, 1, 0.5, 0.3],
            12: [110, 41, 10, 5, 3, 1.5, 1, 0.5, 0.3],
            16: [110, 41, 10, 5, 3, 1.5, 1, 0.5, 0.3],
        }
    }

    def __init__(self):
        super().__init__('plinko')

    def play(self, user, bet_amount, rows, risk, currency_code):
        """Сыграть в Plinko."""
        settings = CasinoSettings.get_settings()
        
        # Валидация
        if bet_amount < settings.plinko_min_bet or bet_amount > settings.plinko_max_bet:
            raise ValueError("Неверная сумма ставки")
        
        if rows not in (8, 12, 16):
            raise ValueError("Количество рядов должно быть 8, 12 или 16")
        
        if risk not in ('low', 'medium', 'high'):
            raise ValueError("Риск должен быть low, medium или high")
        
        # Создать сессию
        session, result_hash = CasinoService.create_game_session(
            user, 'plinko', bet_amount, currency_code
        )
        
        # Сгенерировать путь
        path, landing = ProvablyFairService.generate_plinko_path(result_hash, rows)
        
        # Получить множитель
        multiplier = self.get_multiplier(rows, risk, landing)
        win_amount = bet_amount * multiplier
        
        # Завершить игру
        game_data = {
            "rows": rows,
            "risk": risk,
            "path": path,
            "landing_position": landing,
            "multiplier": multiplier
        }
        
        CasinoService.complete_game(session, win_amount, game_data)
        
        return session

    def get_multiplier(self, rows, risk, landing):
        """Получить множитель для позиции."""
        multipliers = self.MULTIPLIERS[risk][rows]
        # Зеркально: позиция 0 = multipliers[0], позиция rows = multipliers[-1]
        if landing <= rows // 2:
            index = landing
        else:
            index = rows - landing
        
        return Decimal(str(multipliers[index]))

    def validate_bet(self, user, bet_data):
        settings = CasinoSettings.get_settings()
        bet_amount = bet_data.get('bet_amount', 0)
        rows = bet_data.get('rows', 16)
        risk = bet_data.get('risk', 'medium')
        
        if bet_amount < settings.plinko_min_bet or bet_amount > settings.plinko_max_bet:
            return False, "Неверная сумма ставки"
        
        if rows not in (8, 12, 16):
            return False, "Количество рядов должно быть 8, 12 или 16"
        
        if risk not in ('low', 'medium', 'high'):
            return False, "Риск должен быть low, medium или high"
        
        return True, ""

    def get_result(self, game_session):
        return game_session.game_data
