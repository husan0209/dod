from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Dict

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from apps.casino.games.crash import CrashGameImpl
from apps.casino.models import CrashGame


class CrashConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            await self.close(code=4001)
            return

        self.group_name = "casino_crash"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        current_round = await self._get_or_create_current_round()
        await self.send_json(
            {
                "type": "round",
                "round": self._serialize_round(current_round),
            }
        )

    async def disconnect(self, close_code):
        group_name = getattr(self, "group_name", None)
        if group_name:
            await self.channel_layer.group_discard(group_name, self.channel_name)

    async def receive_json(self, content: Dict[str, Any], **kwargs):
        msg_type = content.get("type")
        if msg_type == "ping":
            await self.send_json({"type": "pong"})
            return

        if msg_type == "cashout":
            crash_game_id = content.get("crash_game_id")
            multiplier_raw = content.get("multiplier")
            if not crash_game_id or multiplier_raw is None:
                await self.send_json({"type": "error", "message": "missing_fields"})
                return

            try:
                multiplier = Decimal(str(multiplier_raw))
            except (InvalidOperation, TypeError, ValueError):
                await self.send_json({"type": "error", "message": "bad_multiplier"})
                return

            user = self.scope["user"]
            try:
                await self._cashout(user_id=user.id, crash_game_id=crash_game_id, multiplier=multiplier)
            except Exception:
                await self.send_json({"type": "error", "message": "cashout_failed"})
                return

            await self.send_json({"type": "cashout", "status": "ok"})
            return

        await self.send_json({"type": "error", "message": "unknown_type"})

    @database_sync_to_async
    def _get_or_create_current_round(self) -> CrashGame:
        current_round = (
            CrashGame.objects.filter(status__in=["waiting", "running"])
            .order_by("-created_at")
            .first()
        )
        if current_round:
            return current_round
        return CrashGameImpl.create_round()

    @database_sync_to_async
    def _cashout(self, user_id, crash_game_id: str, multiplier: Decimal) -> None:
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user = User.objects.get(id=user_id)
        CrashGameImpl.cashout(user=user, crash_game_id=crash_game_id, current_multiplier=multiplier)

    def _serialize_round(self, crash_game: CrashGame) -> Dict[str, Any]:
        return {
            "id": str(crash_game.id),
            "round_id": crash_game.round_id,
            "status": crash_game.status,
            "server_seed_hash": crash_game.server_seed_hash,
            "players_count": crash_game.players_count,
            "total_bet": str(crash_game.total_bet),
            "started_at": crash_game.started_at.isoformat() if crash_game.started_at else None,
            "crashed_at": crash_game.crashed_at.isoformat() if crash_game.crashed_at else None,
            "created_at": crash_game.created_at.isoformat() if crash_game.created_at else None,
        }


class MinesConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            await self.close(code=4001)
            return
        await self.accept()
        await self.send_json({"type": "ready"})

    async def receive_json(self, content: Dict[str, Any], **kwargs):
        msg_type = content.get("type")
        if msg_type == "ping":
            await self.send_json({"type": "pong"})
            return
        await self.send_json({"type": "error", "message": "unknown_type"})
