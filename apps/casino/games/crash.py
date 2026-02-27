import secrets
from django.db import transaction
from django.utils import timezone
from decimal import Decimal
from ..models import CrashGame, CrashBet, CasinoSettings
from ..services.provably_fair import ProvablyFairService
from ..services.casino_service import CasinoService
from .base import BaseGame


class CrashGameImpl(BaseGame):
    """
    Коэффициент растёт от 1.00x.
    Игрок должен забрать деньги до краша.
    МУЛЬТИПЛЕЕРНАЯ: все видят один раунд.
    """

    def __init__(self):
        super().__init__('crash')

    @staticmethod
    def create_round():
        """Создать новый раунд Crash."""
        settings = CasinoSettings.get_settings()
        
        # Сгенерировать seeds
        server_seed = ProvablyFairService.generate_server_seed()
        server_seed_hash = ProvablyFairService.hash_seed(server_seed)
        
        # Сгенерировать результат
        round_number = CrashGame.objects.count() + 1
        result_hash = ProvablyFairService.generate_game_result(
            server_seed, "crash_global", round_number
        )
        crash_point = ProvablyFairService.generate_crash_point(
            result_hash, settings.crash_house_edge
        )
        
        # Создать раунд
        round_id = f"CRASH-{round_number:06d}"
        crash_game = CrashGame.objects.create(
            round_id=round_id,
            crash_point=crash_point,
            server_seed=server_seed,
            server_seed_hash=server_seed_hash,
            status='waiting'
        )
        
        return crash_game

    @staticmethod
    def place_bet(user, bet_amount, currency_code, auto_cashout=None):
        """Поставить в текущий раунд."""
        settings = CasinoSettings.get_settings()
        
        # Валидация
        if bet_amount < settings.crash_min_bet or bet_amount > settings.crash_max_bet:
            raise ValueError("Неверная сумма ставки")
        
        if auto_cashout and auto_cashout < Decimal('1.01'):
            raise ValueError("Auto cashout должен быть >= 1.01")
        
        # Получить текущий раунд
        current_round = CrashGame.objects.filter(status='waiting').first()
        if not current_round:
            current_round = CrashGameLogic.create_round()
        
        # Проверить что пользователь ещё не ставил
        if CrashBet.objects.filter(crash_game=current_round, user=user).exists():
            raise ValueError("Вы уже поставили в этот раунд")
        
        # Создать сессию
        session, result_hash = CasinoService.create_game_session(
            user, 'crash', bet_amount, currency_code
        )
        
        # Создать ставку
        crash_bet = CrashBet.objects.create(
            crash_game=current_round,
            game_session=session,
            user=user,
            bet_amount=bet_amount,
            currency=session.currency,
            auto_cashout=auto_cashout
        )
        
        # Обновить раунд
        current_round.players_count += 1
        current_round.total_bet += bet_amount
        current_round.save()
        
        return session

    @staticmethod
    def start_round(crash_game_id):
        """Запустить раунд."""
        crash_game = CrashGame.objects.get(id=crash_game_id)
        crash_game.status = 'running'
        crash_game.started_at = timezone.now()
        crash_game.save()

    @staticmethod
    def cashout(user, crash_game_id, current_multiplier):
        """Забрать деньги."""
        with transaction.atomic():
            crash_game = CrashGame.objects.select_for_update().get(id=crash_game_id)
            crash_bet = CrashBet.objects.select_for_update().get(
                crash_game=crash_game, user=user, status='active'
            )
            
            if crash_game.status != 'running':
                raise ValueError("Раунд не активен")
            
            if current_multiplier > crash_game.crash_point:
                raise ValueError("Слишком поздно")
            
            # Рассчитать выигрыш
            win_amount = crash_bet.bet_amount * current_multiplier
            
            # Завершить ставку
            crash_bet.cashout_at = current_multiplier
            crash_bet.win_amount = win_amount
            crash_bet.status = 'cashed_out'
            crash_bet.cashed_out_at = timezone.now()
            crash_bet.save()
            
            # Завершить сессию
            CasinoService.complete_game(crash_bet.game_session, win_amount, {
                'crash_point': str(crash_game.crash_point),
                'cashout_at': str(current_multiplier),
                'auto_cashout': str(crash_bet.auto_cashout) if crash_bet.auto_cashout else None
            })
            
            # Обновить раунд
            crash_game.total_payout += win_amount
            crash_game.save()

    @staticmethod
    def end_round(crash_game_id):
        """Раунд окончен."""
        crash_game = CrashGame.objects.get(id=crash_game_id)
        crash_game.status = 'crashed'
        crash_game.crashed_at = timezone.now()
        
        # Все активные ставки = busted
        active_bets = CrashBet.objects.filter(crash_game=crash_game, status='active')
        for bet in active_bets:
            bet.status = 'busted'
            bet.save()
            CasinoService.complete_game(bet.game_session, 0, {
                'crash_point': str(crash_game.crash_point),
                'cashout_at': None,
                'auto_cashout': str(bet.auto_cashout) if bet.auto_cashout else None
            })
        
        crash_game.save()
        
        # Создать следующий раунд через 5 сек (через Celery)

    def validate_bet(self, user, bet_data):
        settings = CasinoSettings.get_settings()
        bet_amount = bet_data.get('bet_amount', 0)
        if bet_amount < settings.crash_min_bet or bet_amount > settings.crash_max_bet:
            return False, "Неверная сумма ставки"
        return True, ""

    def play(self, user, bet_data):
        bet_amount = bet_data['bet_amount']
        currency_code = bet_data['currency_code']
        auto_cashout = bet_data.get('auto_cashout')
        
        return self.place_bet(user, bet_amount, currency_code, auto_cashout)

    def get_result(self, game_session):
        return game_session.game_data
