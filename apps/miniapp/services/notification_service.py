# apps/miniapp/services/notification_service.py

import logging
from django.conf import settings
from django.utils import timezone
from telegram import Bot
from telegram.error import TelegramError

from apps.miniapp.models import TelegramUser

logger = logging.getLogger(__name__)


class TelegramNotificationService:
    """
    Отправка уведомлений пользователям через бота.
    Интегрируется с NotificationService из этапа 9.
    """

    def __init__(self):
        self.bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)

    async def send_notification(self, tg_user: TelegramUser, message: str, keyboard=None):
        """
        Отправить уведомление пользователю.

        Args:
            tg_user: TelegramUser instance
            message: Текст сообщения
            keyboard: InlineKeyboardMarkup (optional)
        """
        if not tg_user.bot_notifications_enabled:
            return

        try:
            await self.bot.send_message(
                chat_id=tg_user.telegram_id,
                text=message,
                parse_mode='Markdown',
                reply_markup=keyboard,
                disable_web_page_preview=True
            )
            logger.info(f"Notification sent to {tg_user.telegram_id}")
        except TelegramError as e:
            logger.error(f"Failed to send notification to {tg_user.telegram_id}: {e}")

    def notify_bet_result(self, user, bet_data):
        """
        Уведомление о результате ставки.

        Args:
            user: User instance
            bet_data: dict with bet details
        """
        try:
            tg_user = user.telegram_profile
            if not self._should_notify(tg_user, 'bets_results'):
                return

            if bet_data['result'] == 'win':
                message = f"""
⚽ *Ставка завершена!*

{bot_data['match']}
Ваша ставка: {bet_data['outcome']} (коэфф. {bet_data['odds']})

🏆 *Результат: ВЫИГРЫШ!*
💰 Выигрыш: ${bet_data['payout']:.2f}
"""
            else:
                message = f"""
⚽ *Ставка завершена!*

{bot_data['match']}
Ваша ставка: {bet_data['outcome']} (коэфф. {bet_data['odds']})

❌ *Результат: ПРОИГРЫШ*
💰 Сумма: ${bet_data['amount']:.2f}
"""

            from telegram import InlineKeyboardMarkup, InlineKeyboardButton
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📊 Детали", web_app={"url": f"{settings.TELEGRAM_WEBAPP_URL}/sports/my-bets"})],
                [InlineKeyboardButton("🎮 Новая ставка", web_app={"url": f"{settings.TELEGRAM_WEBAPP_URL}/sports"})]
            ])

            # In real implementation, this would be async
            import asyncio
            asyncio.run(self.send_notification(tg_user, message, keyboard))

        except Exception as e:
            logger.error(f"Error sending bet result notification: {e}")

    def notify_market_resolution(self, user, market_data):
        """
        Уведомление о разрешении маркета.

        Args:
            user: User instance
            market_data: dict with market details
        """
        try:
            tg_user = user.telegram_profile
            if not self._should_notify(tg_user, 'market_resolved'):
                return

            if market_data['user_position'] > 0:
                if market_data['result'] == market_data['user_outcome']:
                    message = f"""
📊 *Маркет разрешён!*

{market_data['title']}
Результат: ✅ {market_data['result_text']}

Ваша позиция: {market_data['user_shares']} долей {market_data['user_outcome']}
💰 Выигрыш: ${market_data['payout']:.2f}
"""
                else:
                    message = f"""
📊 *Маркет разрешён!*

{market_data['title']}
Результат: {market_data['result_text']}

Ваша позиция: {market_data['user_shares']} долей {market_data['user_outcome']}
❌ Проигрыш позиции
"""

                from telegram import InlineKeyboardMarkup, InlineKeyboardButton
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("📊 Детали", web_app={"url": f"{settings.TELEGRAM_WEBAPP_URL}/predictions"})]
                ])

                import asyncio
                asyncio.run(self.send_notification(tg_user, message, keyboard))

        except Exception as e:
            logger.error(f"Error sending market resolution notification: {e}")

    def notify_deposit(self, user, deposit_data):
        """
        Уведомление о пополнении.

        Args:
            user: User instance
            deposit_data: dict with deposit details
        """
        try:
            tg_user = user.telegram_profile
            if not self._should_notify(tg_user, 'deposits'):
                return

            message = f"""
✅ *Пополнение баланса*

Сумма: ${deposit_data['amount']:.2f}
Метод: {deposit_data['method']}
Статус: {deposit_data['status']}
"""

            import asyncio
            asyncio.run(self.send_notification(tg_user, message))

        except Exception as e:
            logger.error(f"Error sending deposit notification: {e}")

    def notify_withdrawal(self, user, withdrawal_data):
        """
        Уведомление о выводе.

        Args:
            user: User instance
            withdrawal_data: dict with withdrawal details
        """
        try:
            tg_user = user.telegram_profile
            if not self._should_notify(tg_user, 'withdrawals'):
                return

            if withdrawal_data['status'] == 'completed':
                message = f"""
✅ *Вывод одобрен!*

Сумма: ${withdrawal_data['amount']:.2f} ({withdrawal_data['currency']})
Адрес: {withdrawal_data['address'][:20]}...
Статус: Обработан
"""
            elif withdrawal_data['status'] == 'pending':
                message = f"""
⏳ *Вывод в обработке*

Сумма: ${withdrawal_data['amount']:.2f} ({withdrawal_data['currency']})
Ожидайте 10-30 минут
"""
            else:
                message = f"""
❌ *Вывод отклонён*

Сумма: ${withdrawal_data['amount']:.2f} ({withdrawal_data['currency']})
Причина: {withdrawal_data.get('reason', 'Неизвестно')}
"""

            import asyncio
            asyncio.run(self.send_notification(tg_user, message))

        except Exception as e:
            logger.error(f"Error sending withdrawal notification: {e}")

    def notify_security_alert(self, user, alert_data):
        """
        Уведомление о безопасности.

        Args:
            user: User instance
            alert_data: dict with alert details
        """
        try:
            tg_user = user.telegram_profile
            if not self._should_notify(tg_user, 'security_alerts'):
                return

            message = f"""
⚠️ *Вход с нового устройства!*

Устройство: {alert_data['device']}
IP: {alert_data['ip']}
Местоположение: {alert_data['location']}
Время: {alert_data['time']}

Это вы?
"""

            from telegram import InlineKeyboardMarkup, InlineKeyboardButton
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Да, это я", callback_data="security_confirm")],
                [InlineKeyboardButton("❌ Нет, заблокировать", callback_data="security_block")]
            ])

            import asyncio
            asyncio.run(self.send_notification(tg_user, message, keyboard))

        except Exception as e:
            logger.error(f"Error sending security alert: {e}")

    def notify_referral(self, user, referral_data):
        """
        Уведомление о новом реферале.

        Args:
            user: User instance
            referral_data: dict with referral details
        """
        try:
            tg_user = user.telegram_profile
            if not self._should_notify(tg_user, 'referral_activity'):
                return

            message = f"""
🤝 *Новый реферал!*

Пользователь зарегистрировался по вашей ссылке.
Всего рефералов: {referral_data['total_referrals']}
"""

            import asyncio
            asyncio.run(self.send_notification(tg_user, message))

        except Exception as e:
            logger.error(f"Error sending referral notification: {e}")

    def send_daily_digest(self, tg_user: TelegramUser, digest_data):
        """
        Отправить ежедневный дайджест.

        Args:
            tg_user: TelegramUser instance
            digest_data: dict with digest content
        """
        if not tg_user.bot_notifications_enabled:
            return

        message = f"""
📊 *Ежедневный дайджест DOD*

💰 Баланс: ${digest_data.get('balance', 0):.2f}

⚽ Ставок сегодня: {digest_data.get('bets_today', 0)}
🏆 Выигрышей: {digest_data.get('wins_today', 0)}
📈 Прибыль: ${digest_data.get('profit_today', 0):.2f}

🎰 Казино: ${digest_data.get('casino_spent', 0):.2f}
📊 Маркеты: {digest_data.get('markets_traded', 0)} сделок

🔥 Популярные матчи сегодня:
{digest_data.get('popular_matches', 'Загружаются...')}

[🎮 Открыть DOD]({settings.TELEGRAM_WEBAPP_URL})
"""

        try:
            import asyncio
            asyncio.run(self.send_notification(tg_user, message))
        except Exception as e:
            logger.error(f"Error sending daily digest: {e}")

    def _should_notify(self, tg_user: TelegramUser, notification_type: str) -> bool:
        """
        Проверить, нужно ли отправлять уведомление.

        Args:
            tg_user: TelegramUser instance
            notification_type: Тип уведомления

        Returns:
            bool: True если нужно отправить
        """
        if not tg_user.bot_notifications_enabled:
            return False

        preferences = tg_user.notification_preferences or {}
        return preferences.get(notification_type, True)  # Default to True


# Global instance
notification_service = TelegramNotificationService()
