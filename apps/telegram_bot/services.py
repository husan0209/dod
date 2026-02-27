"""
Сервис отправки уведомлений в Telegram.
"""

from django.conf import settings
from django.contrib.auth import get_user_model
from .tasks import send_telegram_message_task

User = get_user_model()


class TelegramNotificationService:
    """
    Сервис для отправки уведомлений пользователям в Telegram.
    """

    @staticmethod
    def send_notification(user, title, message, buttons=None):
        """
        Отправить уведомление пользователю в Telegram.
        """
        if not user.telegram_id:
            return False

        # Проверить настройки
        if not user.notification_settings.get('telegram_notifications', False):
            return False

        send_telegram_message_task.delay(
            chat_id=user.telegram_id,
            text=f'{title}\n\n{message}',
            buttons=buttons,
        )
        return True

    @staticmethod
    def send_security_alert(user, device_info, location, time):
        """Отправить уведомление о входе с нового устройства."""
        buttons = [
            {'text': 'Это я', 'callback_data': 'security_confirm'},
            {'text': 'Заблокировать', 'callback_data': 'security_block'},
        ]

        return TelegramNotificationService.send_notification(
            user=user,
            title='🔐 Вход с нового устройства',
            message=f'Chrome, Windows • {location} • {time}\n\nЭто вы?',
            buttons=buttons,
        )

    @staticmethod
    def send_deposit_notification(user, amount, balance):
        """Уведомление о пополнении счета."""
        return TelegramNotificationService.send_notification(
            user=user,
            title='💰 Депозит подтверждён',
            message=f'+${amount} на ваш счёт\nБаланс: ${balance}',
        )

    @staticmethod
    def send_withdrawal_notification(user, amount, method, address):
        """Уведомление о выводе средств."""
        return TelegramNotificationService.send_notification(
            user=user,
            title='💵 Вывод одобрен',
            message=f'${amount} → {method}\nАдрес: {address}',
        )

    @staticmethod
    def send_ticket_reply(user, ticket_number, message_text):
        """Уведомление об ответе на тикет."""
        buttons = [
            {'text': 'Ответить на сайте', 'url': f'{settings.SITE_URL}/support/tickets/{ticket_number}/'},
        ]

        return TelegramNotificationService.send_notification(
            user=user,
            title=f'💬 Ответ на тикет #{ticket_number}',
            message=f'Оператор написал:\n{message_text[:200]}{"..." if len(message_text) > 200 else ""}',
            buttons=buttons,
        )

    @staticmethod
    def send_bet_result(user, bet_info, result, payout=None):
        """Уведомление о результате ставки."""
        if result == 'win':
            title = '🎉 Ставка выиграла!'
            message = f'{bet_info}\nВыигрыш: ${payout}'
        else:
            title = '❌ Ставка проиграла'
            message = f'{bet_info}'

        return TelegramNotificationService.send_notification(
            user=user,
            title=title,
            message=message,
        )


class TelegramBotService:
    """
    Сервис для работы с Telegram ботом.
    """

    @staticmethod
    def link_account(user, telegram_id):
        """
        Привязать Telegram аккаунт к пользователю.
        """
        # Проверить, не привязан ли уже к другому пользователю
        existing = User.objects.filter(telegram_id=telegram_id).exclude(id=user.id).first()
        if existing:
            existing.telegram_id = None
            existing.save()

        user.telegram_id = telegram_id
        user.save()

        return True

    @staticmethod
    def unlink_account(user):
        """
        Отвязать Telegram аккаунт.
        """
        user.telegram_id = None
        user.save()

        return True

    @staticmethod
    def generate_link_code(user):
        """
        Сгенерировать код для привязки аккаунта.
        """
        from django.core.cache import cache
        import secrets

        code = secrets.token_hex(3).upper()  # 6 символов
        cache.set(f'telegram_link:{code}', user.id, 600)  # 10 минут

        return code

    @staticmethod
    def verify_link_code(code, telegram_id):
        """
        Проверить код привязки и привязать аккаунт.
        """
        from django.core.cache import cache

        user_id = cache.get(f'telegram_link:{code}')
        if not user_id:
            return None, 'Код не найден или истёк'

        try:
            user = User.objects.get(id=user_id)
            TelegramBotService.link_account(user, telegram_id)
            cache.delete(f'telegram_link:{code}')
            return user, None
        except User.DoesNotExist:
            return None, 'Пользователь не найден'

    @staticmethod
    def get_user_balance(user):
        """Получить баланс пользователя."""
        return f"💰 Ваш баланс: ${user.balance:.2f} {user.preferred_currency}"

    @staticmethod
    def get_recent_bets(user, limit=5):
        """Получить последние ставки."""
        from apps.sports.models import Bet
        from apps.casino.models import GameSession
        from apps.predictions.models import Trade

        bets = []

        # Sports bets
        sports_bets = Bet.objects.filter(user=user).order_by('-created_at')[:limit]
        for bet in sports_bets:
            status_icon = '✅' if bet.status == 'won' else '❌' if bet.status == 'lost' else '⏳'
            bets.append(f"{status_icon} {bet.event.title}: {bet.selection} × {bet.odds} → ${bet.payout_amount:.2f}")

        # Casino games
        casino_games = GameSession.objects.filter(user=user).order_by('-started_at')[:limit]
        for game in casino_games:
            status_icon = '✅' if game.status == 'won' else '❌' if game.status == 'lost' else '⏳'
            bets.append(f"{status_icon} {game.game_type.name}: ${game.win_amount:.2f}")

        # Predictions
        predictions = Trade.objects.filter(user=user).order_by('-created_at')[:limit]
        for trade in predictions:
            status_icon = '📈' if trade.trade_type == 'buy' else '📉'
            bets.append(f"{status_icon} {trade.market.title}: {trade.outcome} → ${trade.total_amount:.2f}")

        return bets[:5]  # Ограничить 5

    @staticmethod
    def get_recent_tickets(user, limit=5):
        """Получить последние тикеты."""
        from apps.support.models import Ticket

        tickets = Ticket.objects.filter(user=user).order_by('-created_at')[:limit]
        result = []
        for ticket in tickets:
            status_text = {
                'new': 'Новый',
                'open': 'Открыт',
                'in_progress': 'В работе',
                'waiting_user': 'Ожидание вас',
                'waiting_admin': 'Ожидание оператора',
                'resolved': 'Решён',
                'closed': 'Закрыт',
                'reopened': 'Переоткрыт',
            }.get(ticket.status, ticket.status)
            result.append(f"#{ticket.ticket_number} — {status_text}")

        return result

    @staticmethod
    def get_referral_info(user):
        """Получить информацию о партнёрской программе."""
        from apps.referral.models import ReferralSettings

        settings = ReferralSettings.get_settings()
        profile = user.partner_profile if hasattr(user, 'partner_profile') else None

        if not profile or not profile.is_partner_active:
            return "🤝 Вы не участвуете в партнёрской программе."

        total_earned = profile.total_earned
        monthly_earned = profile.monthly_earned
        referrals_count = profile.total_referrals

        return f"""🤝 Ваша реферальная ссылка:
{settings.referral_base_url}/r/{user.referral_code}

Рефералов: {referrals_count}
Заработано всего: ${total_earned:.2f}
В этом месяце: ${monthly_earned:.2f}"""
