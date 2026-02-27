from decimal import Decimal
from ..models import CasinoSettings
from ..services.provably_fair import ProvablyFairService
from ..services.casino_service import CasinoService
from .base import BaseGame


class SlotsGame(BaseGame):
    """
    Слоты: 5 барабанов × 3 ряда, 20 линий выплат.
    """

    SYMBOLS = {
        0: '🍒', 1: '🍋', 2: '🍊', 3: '🍇',
        4: '🔔', 5: '⭐', 6: '💎', 7: '7️⃣'
    }

    PAYLINES = [
        # 20 стандартных линий (упрощённо, первые 5)
        [0, 0, 0, 0, 0],  # верхняя
        [1, 1, 1, 1, 1],  # средняя
        [2, 2, 2, 2, 2],  # нижняя
        [0, 1, 2, 1, 0],  # V
        [2, 1, 0, 1, 2],  # ^
        # ... остальные 15 линий
    ]

    PAYTABLE = {
        0: [0, 2, 5, 10],      # 🍒
        1: [0, 3, 8, 15],      # 🍋
        2: [0, 4, 10, 20],     # 🍊
        3: [0, 5, 15, 30],     # 🍇
        4: [0, 8, 25, 50],     # 🔔
        5: [0, 10, 40, 100],   # ⭐
        6: [0, 25, 100, 500],  # 💎
        7: [0, 50, 250, 1000], # 7️⃣
    }

    def __init__(self):
        super().__init__('slots')

    def play(self, user, bet_amount, currency_code):
        """Сыграть в Slots."""
        settings = CasinoSettings.get_settings()
        
        # Валидация
        if bet_amount < settings.slots_min_bet or bet_amount > settings.slots_max_bet:
            raise ValueError("Неверная сумма ставки")
        
        # Создать сессию
        session, result_hash = CasinoService.create_game_session(
            user, 'slots', bet_amount, currency_code
        )
        
        # Сгенерировать барабаны
        reels = ProvablyFairService.generate_slots_reels(result_hash)
        
        # Проверить выигрыш
        wins = self.check_paylines(reels)
        total_multiplier = sum(win['multiplier'] for win in wins)
        win_amount = bet_amount * total_multiplier
        
        # Завершить игру
        game_data = {
            "reels": reels,
            "paylines": wins,
            "total_multiplier": total_multiplier
        }
        
        CasinoService.complete_game(session, win_amount, game_data)
        
        return session

    def check_paylines(self, reels):
        """Проверить 20 линий на выигрыш."""
        wins = []
        
        for line_idx, positions in enumerate(self.PAYLINES[:5]):  # Только первые 5 для упрощения
            line_symbols = [reels[col][row] for col, row in enumerate(positions)]
            
            # Найти первый символ
            first_symbol = line_symbols[0]
            
            # Считать совпадения
            matches = 0
            for symbol in line_symbols:
                if symbol == first_symbol:
                    matches += 1
                else:
                    break
            
            if matches >= 3:
                multiplier = self.PAYTABLE[first_symbol][matches - 1]
                wins.append({
                    'line': line_idx,
                    'symbols': line_symbols[:matches],
                    'multiplier': multiplier
                })
        
        return wins

    def validate_bet(self, user, bet_data):
        settings = CasinoSettings.get_settings()
        bet_amount = bet_data.get('bet_amount', 0)
        if bet_amount < settings.slots_min_bet or bet_amount > settings.slots_max_bet:
            return False, "Неверная сумма ставки"
        return True, ""

    def get_result(self, game_session):
        return game_session.game_data
