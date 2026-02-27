from django.db import transaction
from django.utils import timezone
from decimal import Decimal
from apps.wallet.services import TransactionService
from ..models import GameSession, UserSeed
from .provably_fair import ProvablyFairService


class CasinoService:
    """
    Общая логика казино.
    """

    @staticmethod
    def create_game_session(user, game_type_code, bet_amount, currency_code):
        """
        Создать GameSession.
        Списать ставку.
        Получить seeds.
        """
        from .models import GameType, Currency
        from apps.wallet.models import Wallet
        
        game_type = GameType.objects.get(code=game_type_code)
        currency = Currency.objects.get(code=currency_code)
        wallet = Wallet.objects.get(user=user, currency=currency)
        
        # Проверить баланс
        if wallet.balance < bet_amount:
            raise ValueError("Недостаточно средств")
        
        # Получить seeds
        user_seed = ProvablyFairService.get_or_create_user_seed(user)
        
        # Увеличить nonce
        user_seed.nonce += 1
        user_seed.save(update_fields=['nonce'])
        
        # Сгенерировать result_hash
        result_hash = ProvablyFairService.generate_game_result(
            user_seed.server_seed, user_seed.client_seed, user_seed.nonce
        )
        
        # Списать ставку
        bet_transaction = TransactionService.withdraw(
            wallet=wallet,
            amount=bet_amount,
            type='bet',
            reference_type='casino_game'
        )
        
        # Создать GameSession
        import uuid
        game_id = f"{game_type_code.upper()}-{timezone.now().strftime('%Y%m%d')}-{secrets.token_hex(3).upper()}"
        
        bet_amount_usd = bet_amount * currency.usd_rate
        
        session = GameSession.objects.create(
            game_id=game_id,
            user=user,
            wallet=wallet,
            game_type=game_type,
            currency=currency,
            bet_amount=bet_amount,
            bet_amount_usd=bet_amount_usd,
            server_seed=user_seed.server_seed,
            server_seed_hash=user_seed.server_seed_hash,
            client_seed=user_seed.client_seed,
            nonce=user_seed.nonce,
            bet_transaction=bet_transaction,
            ip_address='',  # TODO: get from request
        )
        
        return session, result_hash

    @staticmethod
    def complete_game(game_session, win_amount, game_data):
        """
        Завершить игру.
        Зачислить выигрыш (если есть).
        """
        with transaction.atomic():
            game_session.game_data = game_data
            game_session.win_amount = win_amount
            game_session.win_multiplier = win_amount / game_session.bet_amount if game_session.bet_amount > 0 else 0
            game_session.profit = win_amount - game_session.bet_amount
            game_session.completed_at = timezone.now()
            
            if win_amount > 0:
                game_session.status = 'won'
                win_transaction = TransactionService.deposit(
                    wallet=game_session.wallet,
                    amount=win_amount,
                    type='win',
                    reference='casino_game',
                    description=f"Выигрыш в {game_session.game_type.name}"
                )
                game_session.win_transaction = win_transaction
            else:
                game_session.status = 'lost'
            
            game_session.save()
            
            # Проверить big_win
            if win_amount >= 100:  # Настраиваемый порог
                # TODO: уведомление о большом выигрыше
                pass
            
            return game_session
