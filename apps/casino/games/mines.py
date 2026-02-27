from django.db import transaction
from decimal import Decimal
from ..models import CasinoSettings
from ..services.provably_fair import ProvablyFairService
from ..services.casino_service import CasinoService
from .base import BaseGame


class MinesGame(BaseGame):
    """
    Mines: 5x5 поле, пользователь выбирает количество мин.
    """

    def __init__(self):
        super().__init__('mines')

    def start_game(self, user, bet_amount, mines_count, currency_code):
        """Начать игру Mines."""
        settings = CasinoSettings.get_settings()
        
        # Валидация
        if mines_count < 1 or mines_count > 24:
            raise ValueError("Количество мин должно быть от 1 до 24")
        if bet_amount < settings.mines_min_bet or bet_amount > settings.mines_max_bet:
            raise ValueError("Неверная сумма ставки")
        
        # Создать сессию
        session, result_hash = CasinoService.create_game_session(
            user, 'mines', bet_amount, currency_code
        )
        
        # Сгенерировать позиции мин
        mines_positions = ProvablyFairService.generate_mines_positions(
            result_hash, field_size=25, mines_count=mines_count
        )
        
        # Сохранить данные (без mines_positions для пользователя)
        game_data = {
            "field_size": 25,
            "mines_count": mines_count,
            "mines_positions": mines_positions,  # СКРЫТО
            "revealed": [],
            "current_multiplier": Decimal('1.00'),
            "is_mine_hit": False
        }
        
        session.game_data = game_data
        session.status = 'active'
        session.save()
        
        return session

    def reveal_cell(self, game_session_id, cell_index, user):
        """Открыть клетку."""
        with transaction.atomic():
            from ..models import GameSession
            session = GameSession.objects.select_for_update().get(id=game_session_id, user=user)
            
            if session.status != 'active':
                raise ValueError("Игра не активна")
            
            if cell_index in session.game_data['revealed']:
                raise ValueError("Клетка уже открыта")
            
            if not (0 <= cell_index < 25):
                raise ValueError("Неверный индекс клетки")
            
            mines_positions = session.game_data['mines_positions']
            revealed = session.game_data['revealed']
            
            if cell_index in mines_positions:
                # МИНА!
                session.game_data['is_mine_hit'] = True
                CasinoService.complete_game(session, 0, session.game_data)
                return {
                    "mine": True,
                    "mines_positions": mines_positions
                }
            else:
                # Безопасная клетка
                revealed.append(cell_index)
                current_multiplier = self.calculate_multiplier(len(revealed), session.game_data['mines_count'])
                session.game_data['revealed'] = revealed
                session.game_data['current_multiplier'] = current_multiplier
                session.save()
                
                next_multiplier = self.calculate_multiplier(len(revealed) + 1, session.game_data['mines_count'])
                
                return {
                    "mine": False,
                    "cell": cell_index,
                    "current_multiplier": current_multiplier,
                    "next_multiplier": next_multiplier
                }

    def cashout_mines(self, game_session_id, user):
        """Забрать деньги."""
        with transaction.atomic():
            from ..models import GameSession
            session = GameSession.objects.select_for_update().get(id=game_session_id, user=user)
            
            if session.status != 'active':
                raise ValueError("Игра не активна")
            
            if len(session.game_data['revealed']) < 1:
                raise ValueError("Надо открыть хотя бы одну клетку")
            
            win_amount = session.bet_amount * session.game_data['current_multiplier']
            CasinoService.complete_game(session, win_amount, session.game_data)
            
            return session

    def calculate_multiplier(self, revealed_count, mines_count):
        """Рассчитать множитель на основе открытых клеток."""
        # Простая формула: probability = (25 - mines_count - revealed_count) / (25 - revealed_count)
        # multiplier = 1 / probability
        safe_cells = 25 - mines_count
        remaining_safe = safe_cells - revealed_count
        
        if remaining_safe <= 0:
            return Decimal('0')
        
        probability = remaining_safe / (25 - revealed_count)
        multiplier = 1 / probability
        
        return Decimal(str(round(multiplier, 2)))

    def validate_bet(self, user, bet_data):
        settings = CasinoSettings.get_settings()
        bet_amount = bet_data.get('bet_amount', 0)
        mines_count = bet_data.get('mines_count', 5)
        if bet_amount < settings.mines_min_bet or bet_amount > settings.mines_max_bet:
            return False, "Неверная сумма ставки"
        if mines_count < 1 or mines_count > 24:
            return False, "Неверное количество мин"
        return True, ""

    def play(self, user, bet_data):
        bet_amount = bet_data['bet_amount']
        mines_count = bet_data['mines_count']
        currency_code = bet_data['currency_code']
        
        return self.start_game(user, bet_amount, mines_count, currency_code)

    def get_result(self, game_session):
        return game_session.game_data
