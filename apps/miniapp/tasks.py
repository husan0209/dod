# apps/miniapp/tasks.py

import logging
from datetime import timedelta
from django.utils import timezone
from django.db.models import Count, Sum, Avg
from django.core.cache import cache
from celery import shared_task

from apps.miniapp.models import TelegramUser, MiniAppSession
from apps.miniapp.services.notification_service import notification_service

logger = logging.getLogger(__name__)


@shared_task
def update_miniapp_analytics():
    """
    Обновить метрики Mini App в кэше каждые 5 минут.
    """
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    try:
        # Общие метрики
        total_users = TelegramUser.objects.count()
        active_users_today = TelegramUser.objects.filter(
            last_app_open__gte=today_start
        ).count()

        total_sessions = MiniAppSession.objects.count()
        sessions_today = MiniAppSession.objects.filter(
            started_at__gte=today_start
        ).count()

        # Среднее время сессии
        avg_session_duration = MiniAppSession.objects.filter(
            ended_at__isnull=False
        ).aggregate(avg_duration=Avg('duration_seconds'))['avg_duration'] or 0

        # Платформы
        platform_stats = MiniAppSession.objects.values('platform').annotate(
            count=Count('platform')
        ).order_by('-count')

        platforms = {}
        total_platforms = sum(stat['count'] for stat in platform_stats)
        for stat in platform_stats:
            platforms[stat['platform']] = {
                'count': stat['count'],
                'percentage': round((stat['count'] / total_platforms) * 100, 1) if total_platforms > 0 else 0
            }

        # Воронка конверсии (упрощённая)
        opened_app = TelegramUser.objects.filter(
            app_opens_count__gt=0
        ).count()

        authenticated = TelegramUser.objects.filter(
            user__isnull=False
        ).count()

        made_deposit = 0  # Would need to integrate with wallet models
        made_bet = 0     # Would need to integrate with betting models

        funnel = {
            'opened_app': opened_app,
            'authenticated': authenticated,
            'made_deposit': made_deposit,
            'made_bet': made_bet
        }

        # Популярные разделы (по сессиям)
        popular_pages = MiniAppSession.objects.values('pages_visited').annotate(
            count=Count('id')
        ).order_by('-count')[:5]

        popular_sections = {}
        for item in popular_pages:
            pages = item['pages_visited'] or []
            for page in pages:
                section = page.split('/')[1] if '/' in page else page
                popular_sections[section] = popular_sections.get(section, 0) + item['count']

        # Сохранить в кэш
        analytics_data = {
            'total_users': total_users,
            'active_users_today': active_users_today,
            'total_sessions': total_sessions,
            'sessions_today': sessions_today,
            'avg_session_duration': round(avg_session_duration / 60, 1) if avg_session_duration else 0,  # minutes
            'platforms': platforms,
            'funnel': funnel,
            'popular_sections': dict(sorted(popular_sections.items(), key=lambda x: x[1], reverse=True)[:5]),
            'updated_at': now.isoformat()
        }

        cache.set('miniapp_analytics', analytics_data, 3600)  # Cache for 1 hour
        logger.info("Mini App analytics updated")

    except Exception as e:
        logger.error(f"Error updating Mini App analytics: {e}")


@shared_task
def cleanup_expired_sessions():
    """
    Закрыть неактивные сессии Mini App (> 30 мин) каждый час.
    """
    cutoff_time = timezone.now() - timedelta(minutes=30)

    try:
        expired_sessions = MiniAppSession.objects.filter(
            is_active=True,
            last_activity_at__lt=cutoff_time
        )

        updated_count = 0
        for session in expired_sessions:
            session.is_active = False
            session.ended_at = session.last_activity_at
            session.duration_seconds = int((session.ended_at - session.started_at).total_seconds())
            session.save()
            updated_count += 1

        if updated_count > 0:
            logger.info(f"Cleaned up {updated_count} expired Mini App sessions")

    except Exception as e:
        logger.error(f"Error cleaning up Mini App sessions: {e}")


@shared_task
def send_daily_digest():
    """
    Отправить ежедневный дайджест активным пользователям.
    """
    yesterday = timezone.now() - timedelta(days=1)
    week_ago = timezone.now() - timedelta(days=7)

    try:
        # Получить активных пользователей (открывали app за последнюю неделю)
        active_users = TelegramUser.objects.filter(
            last_app_open__gte=week_ago,
            bot_notifications_enabled=True
        )

        for tg_user in active_users:
            try:
                # Собрать данные для дайджеста (mock data - would integrate with actual models)
                digest_data = {
                    'balance': 1234.56,  # Mock
                    'bets_today': 3,     # Mock
                    'wins_today': 2,     # Mock
                    'profit_today': 45.67,  # Mock
                    'casino_spent': 12.34,  # Mock
                    'markets_traded': 2,    # Mock
                    'popular_matches': "Реал Мадрид — Барселона\nМанСити — Ливерпуль"  # Mock
                }

                notification_service.send_daily_digest(tg_user, digest_data)

            except Exception as e:
                logger.error(f"Error sending digest to {tg_user.telegram_id}: {e}")

        logger.info(f"Daily digest sent to {active_users.count()} users")

    except Exception as e:
        logger.error(f"Error sending daily digests: {e}")


@shared_task
def generate_miniapp_report():
    """
    Сгенерировать отчёт по Mini App для админов ежедневно.
    """
    try:
        # Собрать статистику за день
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)

        new_users = TelegramUser.objects.filter(
            created_at__date=today
        ).count()

        sessions_today = MiniAppSession.objects.filter(
            started_at__date=today
        ).count()

        avg_session_time = MiniAppSession.objects.filter(
            started_at__date=today,
            duration_seconds__gt=0
        ).aggregate(avg_time=Avg('duration_seconds'))['avg_time'] or 0

        # Сохранить отчёт (в лог или файл)
        report = f"""
Mini App Daily Report - {today}
================================
New Users: {new_users}
Sessions: {sessions_today}
Avg Session Time: {round(avg_session_time / 60, 1)} minutes
"""

        logger.info(f"Daily Mini App report generated: {report}")

        # Could send email to admins here

    except Exception as e:
        logger.error(f"Error generating Mini App report: {e}")


@shared_task
def sync_telegram_user_data():
    """
    Синхронизировать данные Telegram пользователей ежедневно.
    Обновить username, premium статус, etc.
    """
    try:
        # В реальной реализации здесь был бы вызов Telegram Bot API
        # для получения актуальных данных пользователей
        # Но поскольку это симуляция, просто обновим timestamps

        updated_count = TelegramUser.objects.filter(
            updated_at__lt=timezone.now() - timedelta(days=1)
        ).update(updated_at=timezone.now())

        if updated_count > 0:
            logger.info(f"Synced data for {updated_count} Telegram users")

    except Exception as e:
        logger.error(f"Error syncing Telegram user data: {e}")


@shared_task
def send_promotional_notifications():
    """
    Отправить промо-уведомления пользователям (по расписанию).
    """
    try:
        # Получить пользователей, которые разрешили промо
        promo_users = TelegramUser.objects.filter(
            bot_notifications_enabled=True,
            notification_preferences__promotions=True
        )

        promo_message = """
🎉 *Специальное предложение!*

💰 +50% к первому пополнению
🎰 Бесплатные спины в казино
📊 Бонус на маркеты

[🎮 Получить бонус](https://t.me/DODPlatformBot?start=promo)
"""

        sent_count = 0
        for tg_user in promo_users:
            try:
                # Check rate limit (max 5/hour)
                # In real implementation, would check Redis cache for rate limiting

                import asyncio
                asyncio.run(notification_service.send_notification(tg_user, promo_message))
                sent_count += 1

            except Exception as e:
                logger.error(f"Error sending promo to {tg_user.telegram_id}: {e}")

        logger.info(f"Promotional notifications sent to {sent_count} users")

    except Exception as e:
        logger.error(f"Error sending promotional notifications: {e}")


@shared_task
def process_referral_rewards():
    """
    Обработать реферальные вознаграждения.
    """
    try:
        # Найти пользователей с новыми рефералами
        # This would need proper referral tracking logic
        # For now, just a placeholder - no users
        users_with_new_referrals = []

        for tg_user in users_with_new_referrals:
            # Calculate and add referral rewards
            # This would integrate with wallet system
            pass

        logger.info("Referral rewards processed")

    except Exception as e:
        logger.error(f"Error processing referral rewards: {e}")
