from abc import ABC, abstractmethod
from decimal import Decimal
from django.utils import timezone
from apps.wallet.services import TransactionService
from ..models import GameSession
from ..services.casino_service import CasinoService
from ..services.provably_fair import ProvablyFairService


class BaseGame(ABC):
    """
    Общий интерфейс для всех игр.
    """

    def __init__(self, game_type_code):
        self.game_type_code = game_type_code

    @abstractmethod
    def validate_bet(self, user, bet_data):
        """
        Валидация ставки перед игрой.
        Возвращает: (valid, error_message)
        """
        pass

    @abstractmethod
    def play(self, user, bet_data):
        """
        Запустить игру.
        Возвращает: GameSession
        """
        pass

    @abstractmethod
    def get_result(self, game_session):
        """
        Получить результат игры.
        Возвращает: dict с результатом
        """
        pass

    def create_game_session(self, user, game_type_code, bet_amount, currency_code):
        """
        Создать GameSession.
        Списать ставку.
        Получить seeds.
        """
        return CasinoService.create_game_session(user, game_type_code, bet_amount, currency_code)

    def complete_game(self, game_session, win_amount, game_data):
        """
        Завершить игру.
        Зачислить выигрыш (если есть).
        """
        return CasinoService.complete_game(game_session, win_amount, game_data)
