from decimal import Decimal
from ..models import CasinoSettings
from ..services.provably_fair import ProvablyFairService
from ..services.casino_service import CasinoService
from .base import BaseGame


class RouletteGame(BaseGame):
    """
    Roulette: европейская (0-36), красное/чёрное, etc.
    """

    RED_NUMBERS = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}
    BLACK_NUMBERS = {2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35}

    BET_TYPES = {
        'number': 36,
        'red': 2,
        'black': 2,
        'even': 2,
        'odd': 2,
        'low': 2,      # 1-18
        'high': 2,     # 19-36
        'dozen_1': 3,  # 1-12
        'dozen_2': 3,  # 13-24
        'dozen_3': 3,  # 25-36
        'column_1': 3, # колонка 1
        'column_2': 3, # колонка 2
        'column_3': 3, # колонка 3
    }

    def __init__(self):
        super().__init__('roulette')

    def play(self, user, bets, currency_code):
        """Сыграть в Roulette."""
        settings = CasinoSettings.get_settings()
        
        # Валидация ставок
        total_bet = sum(bet['amount'] for bet in bets)
        if total_bet < settings.roulette_min_bet or total_bet > settings.roulette_max_bet:
            raise ValueError("Неверная сумма ставки")
        
        for bet in bets:
            if bet['type'] not in self.BET_TYPES:
                raise ValueError(f"Неверный тип ставки: {bet['type']}")
            if bet['amount'] <= 0:
                raise ValueError("Сумма ставки должна быть положительной")
        
        # Создать сессию
        session, result_hash = CasinoService.create_game_session(
            user, 'roulette', total_bet, currency_code
        )
        
        # Сгенерировать результат
        winning_number = ProvablyFairService.generate_roulette_result(result_hash)
        winning_color = self.get_color(winning_number)
        
        # Проверить ставки
        total_win = 0
        bet_results = []
        
        for bet in bets:
            won, payout = self.check_bet_result(bet, winning_number)
            win_amount = bet['amount'] * payout if won else 0
            total_win += win_amount
            
            bet_results.append({
                'type': bet['type'],
                'amount': bet['amount'],
                'won': won,
                'payout': payout,
                'win_amount': win_amount
            })
        
        # Завершить игру
        game_data = {
            'winning_number': winning_number,
            'winning_color': winning_color,
            'bets': bet_results
        }
        
        CasinoService.complete_game(session, total_win, game_data)
        
        return session

    def check_bet_result(self, bet, winning_number):
        """Проверить одну ставку."""
        bet_type = bet['type']
        
        if bet_type == 'number':
            return winning_number == bet.get('number'), self.BET_TYPES['number']
        elif bet_type == 'red':
            return winning_number in self.RED_NUMBERS, self.BET_TYPES['red']
        elif bet_type == 'black':
            return winning_number in self.BLACK_NUMBERS, self.BET_TYPES['black']
        elif bet_type == 'even':
            return winning_number > 0 and winning_number % 2 == 0, self.BET_TYPES['even']
        elif bet_type == 'odd':
            return winning_number % 2 == 1, self.BET_TYPES['odd']
        elif bet_type == 'low':
            return 1 <= winning_number <= 18, self.BET_TYPES['low']
        elif bet_type == 'high':
            return 19 <= winning_number <= 36, self.BET_TYPES['high']
        elif bet_type == 'dozen_1':
            return 1 <= winning_number <= 12, self.BET_TYPES['dozen_1']
        elif bet_type == 'dozen_2':
            return 13 <= winning_number <= 24, self.BET_TYPES['dozen_2']
        elif bet_type == 'dozen_3':
            return 25 <= winning_number <= 36, self.BET_TYPES['dozen_3']
        # Колонки (упрощённо)
        elif bet_type == 'column_1':
            return winning_number % 3 == 1, self.BET_TYPES['column_1']
        elif bet_type == 'column_2':
            return winning_number % 3 == 2, self.BET_TYPES['column_2']
        elif bet_type == 'column_3':
            return winning_number % 3 == 0 and winning_number != 0, self.BET_TYPES['column_3']
        
        return False, 0

    def get_color(self, number):
        """Получить цвет числа."""
        if number == 0:
            return 'green'
        elif number in self.RED_NUMBERS:
            return 'red'
        else:
            return 'black'

    def validate_bet(self, user, bet_data):
        settings = CasinoSettings.get_settings()
        bets = bet_data.get('bets', [])
        total_bet = sum(bet['amount'] for bet in bets)
        if total_bet < settings.roulette_min_bet or total_bet > settings.roulette_max_bet:
            return False, "Неверная сумма ставки"
        return True, ""

    def get_result(self, game_session):
        return game_session.game_data
