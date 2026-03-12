"""
Сервис управления коэффициентами (odds).
"""
import logging
from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from apps.sports.models import Outcome, OddHistory, BetSettings

logger = logging.getLogger(__name__)


class OddsService:
    """Сервис управления коэффициентами"""

    @staticmethod
    @transaction.atomic
    def update_odd(outcome_id, new_odd, changed_by='system', reason=''):
        """
        Обновить коэффициент исхода.

        Args:
            outcome_id: UUID исхода
            new_odd: Decimal новый коэффициент
            changed_by:Str ('api', 'admin', 'system')
            reason: Str причина изменения

        Returns:
            dict с результатом
        """
        try:
            outcome = Outcome.objects.select_for_update().get(id=outcome_id)
        except Outcome.DoesNotExist:
            return {"success": False, "error": "Исход не найден"}

        new_odd = Decimal(str(new_odd))
        settings = BetSettings.get_settings()

        # Валидация коэффициента
        if new_odd < settings.min_odd or new_odd > settings.max_odd:
            return {
                "success": False,
                "error": f"Коэффициент должен быть в диапазоне {settings.min_odd} - {settings.max_odd}"
            }

        old_odd = outcome.odd

        if old_odd == new_odd:
            return {
                "success": True,
                "changed": False,
                "message": "Коэффициент не изменился"
            }

        # Сохранить историю
        outcome.odd_previous = old_odd
        outcome.odd = new_odd

        # Определить направление изменения
        if new_odd > old_odd:
            outcome.odd_direction = 'up'
        elif new_odd < old_odd:
            outcome.odd_direction = 'down'
        else:
            outcome.odd_direction = 'same'

        # Сохранить изменение в историю
        OddHistory.objects.create(
            outcome=outcome,
            odd_before=old_odd,
            odd_after=new_odd,
            changed_by=changed_by
        )

        outcome.save()

        logger.info(
            f"Коэффициент обновлен: {outcome.name} "
            f"{old_odd} → {new_odd} ({outcome.odd_direction}) "
            f"[{changed_by}: {reason}]"
        )

        return {
            "success": True,
            "changed": True,
            "outcome_id": str(outcome_id),
            "old_odd": float(old_odd),
            "new_odd": float(new_odd),
            "direction": outcome.odd_direction,
            "message": f"✅ Коэффициент обновлен: {old_odd} → {new_odd}"
        }

    @staticmethod
    @transaction.atomic
    def suspend_outcome(outcome_id, reason=''):
        """
        Приостановить исход (нельзя на него ставить).

        Args:
            outcome_id: UUID исхода
            reason: Причина приостановления

        Returns:
            dict с результатом
        """
        try:
            outcome = Outcome.objects.select_for_update().get(id=outcome_id)
        except Outcome.DoesNotExist:
            return {"success": False, "error": "Исход не найден"}

        outcome.is_suspended = True
        outcome.save()

        logger.info(f"Исход приостановлен: {outcome.name} [{reason}]")

        return {
            "success": True,
            "outcome_id": str(outcome_id),
            "message": f"✅ Исход {outcome.name} приостановлен"
        }

    @staticmethod
    @transaction.atomic
    def resume_outcome(outcome_id):
        """
        Возобновить исход.

        Args:
            outcome_id: UUID исхода

        Returns:
            dict с результатом
        """
        try:
            outcome = Outcome.objects.select_for_update().get(id=outcome_id)
        except Outcome.DoesNotExist:
            return {"success": False, "error": "Исход не найден"}

        outcome.is_suspended = False
        outcome.save()

        logger.info(f"Исход возобновлен: {outcome.name}")

        return {
            "success": True,
            "outcome_id": str(outcome_id),
            "message": f"✅ Исход {outcome.name} возобновлен"
        }

    @staticmethod
    def get_odd_history(outcome_id, limit=100):
        """
        Получить историю коэффициентов исхода.

        Args:
            outcome_id: UUID исхода
            limit: Лимит записей

        Returns:
            list[dict] с историей
        """
        history = OddHistory.objects.filter(
            outcome_id=outcome_id
        ).order_by('-changed_at')[:limit]

        return [
            {
                "timestamp": h.changed_at.isoformat(),
                "odd_before": float(h.odd_before),
                "odd_after": float(h.odd_after),
                "changed_by": h.changed_by,
            }
            for h in history
        ]

    @staticmethod
    def rollback_odds(outcome_id, steps=1):
        """
        Откатить коэффициент на N шагов назад.

        Args:
            outcome_id: UUID исхода
            steps: Количество шагов на откат

        Returns:
            dict с результатом
        """
        try:
            outcome = Outcome.objects.select_for_update().get(id=outcome_id)
        except Outcome.DoesNotExist:
            return {"success": False, "error": "Исход не найден"}

        # Получить историю
        history = OddHistory.objects.filter(
            outcome_id=outcome_id
        ).order_by('-changed_at')[:steps]

        if not history:
            return {"success": False, "error": "История коэффициентов не найдена"}

        # Откатить на нужное значение
        target_history = history[steps - 1] if len(history) >= steps else history[0]
        rollback_odd = target_history.odd_before

        return OddsService.update_odd(
            outcome_id,
            rollback_odd,
            changed_by='admin',
            reason=f'Откат на {steps} шаг(ов) назад'
        )
