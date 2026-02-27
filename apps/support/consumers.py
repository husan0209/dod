import json
import logging
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import models
from .models import Ticket, Message, ChatSession

logger = logging.getLogger(__name__)
User = get_user_model()


class ChatConsumer(AsyncJsonWebsocketConsumer):
    """
    WebSocket consumer для живого чата поддержки.

    Протокол сообщений (JSON):

    Клиент → Сервер:
      {"type": "message", "text": "Привет"}
      {"type": "typing", "is_typing": true}
      {"type": "read", "message_id": "uuid"}
      {"type": "end_chat"}

    Сервер → Клиент:
      {"type": "message", "data": {...}}
      {"type": "typing", "is_typing": true, "sender": "operator"}
      {"type": "read_receipt", "message_id": "uuid"}
      {"type": "operator_joined", "operator": {...}}
      {"type": "queue_update", "position": 3, "wait_time": "~5 мин"}
      {"type": "chat_ended", "reason": "operator"}
      {"type": "system", "text": "..."}
      {"type": "error", "message": "..."}
    """

    async def connect(self):
        """При подключении WebSocket."""
        self.user = self.scope['user']

        if not self.user.is_authenticated:
            await self.close(code=4001)
            return

        self.ticket_id = self.scope['url_route']['kwargs'].get('ticket_id')
        self.room_group_name = f'chat_{self.ticket_id}'

        # Проверить доступ
        has_access = await self.check_access()
        if not has_access:
            await self.close(code=4003)
            return

        # Присоединиться к группе
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name,
        )

        await self.accept()

        # Обновить channel name в ChatSession
        await self.update_channel_name()

        # Отправить историю сообщений
        history = await self.get_message_history()
        await self.send_json({
            'type': 'history',
            'messages': history,
        })

        # Если оператор — уведомить пользователя
        if self.user.is_staff:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'operator_joined_event',
                    'operator': {
                        'name': self.user.get_full_name() or self.user.username,
                        'avatar': self.user.get_avatar_url(),
                    },
                }
            )

    async def disconnect(self, close_code):
        """При отключении."""
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name,
        )

        # Обновить статус
        if self.user.is_staff:
            await self.set_operator_typing(False)
        else:
            await self.set_user_typing(False)

    async def receive_json(self, content):
        """Получение сообщения от клиента."""
        msg_type = content.get('type')

        if msg_type == 'message':
            await self.handle_message(content)
        elif msg_type == 'typing':
            await self.handle_typing(content)
        elif msg_type == 'read':
            await self.handle_read(content)
        elif msg_type == 'end_chat':
            await self.handle_end_chat()
        else:
            await self.send_json({
                'type': 'error',
                'message': 'Неизвестный тип сообщения',
            })

    async def handle_message(self, content):
        """Обработка нового сообщения."""
        text = content.get('text', '').strip()

        if not text:
            return

        if len(text) > 5000:
            await self.send_json({
                'type': 'error',
                'message': 'Сообщение слишком длинное (макс 5000)',
            })
            return

        # Rate limit: 1 сообщение в 2 секунды
        can_send = await self.check_rate_limit()
        if not can_send:
            await self.send_json({
                'type': 'error',
                'message': 'Слишком быстро. Подождите.',
            })
            return

        # Сохранить в БД
        message_data = await self.save_message(text)

        # Отправить всем в чате
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'data': message_data,
            }
        )

        # Сбросить typing
        if self.user.is_staff:
            await self.set_operator_typing(False)
        else:
            await self.set_user_typing(False)

    async def handle_typing(self, content):
        """Индикатор 'печатает'."""
        is_typing = content.get('is_typing', False)
        sender = 'operator' if self.user.is_staff else 'user'

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing_event',
                'is_typing': is_typing,
                'sender': sender,
            }
        )

    async def handle_read(self, content):
        """Пометка сообщения как прочитанного."""
        message_id = content.get('message_id')
        await self.mark_as_read(message_id)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'read_receipt_event',
                'message_id': message_id,
                'reader': 'operator' if self.user.is_staff else 'user',
            }
        )

    async def handle_end_chat(self):
        """Завершение чата."""
        ended_by = 'operator' if self.user.is_staff else 'user'
        await self.end_chat_session(ended_by)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_ended_event',
                'reason': ended_by,
            }
        )

    # ── Обработчики событий группы ──

    async def chat_message(self, event):
        """Отправка сообщения клиенту."""
        await self.send_json({
            'type': 'message',
            'data': event['data'],
        })

    async def typing_event(self, event):
        await self.send_json({
            'type': 'typing',
            'is_typing': event['is_typing'],
            'sender': event['sender'],
        })

    async def read_receipt_event(self, event):
        await self.send_json({
            'type': 'read_receipt',
            'message_id': event['message_id'],
            'reader': event['reader'],
        })

    async def operator_joined_event(self, event):
        await self.send_json({
            'type': 'operator_joined',
            'operator': event['operator'],
        })

    async def chat_ended_event(self, event):
        await self.send_json({
            'type': 'chat_ended',
            'reason': event['reason'],
        })

    async def queue_update_event(self, event):
        await self.send_json({
            'type': 'queue_update',
            'position': event['position'],
            'wait_time': event['wait_time'],
        })

    # ── Database операции ──

    @database_sync_to_async
    def check_access(self):
        """Проверка доступа к чату."""
        try:
            ticket = Ticket.objects.get(id=self.ticket_id)
            return (
              ticket.user == self.user
              or self.user.is_staff
            )
        except Ticket.DoesNotExist:
            return False

    @database_sync_to_async
    def save_message(self, text):
        """Сохранить сообщение в БД."""
        ticket = Ticket.objects.get(id=self.ticket_id)
        sender_type = 'operator' if self.user.is_staff else 'user'

        message = Message.objects.create(
            ticket=ticket,
            sender=self.user,
            sender_type=sender_type,
            text=text,
        )

        # Обновить тикет
        if sender_type == 'operator':
            if not ticket.first_response_at:
                ticket.first_response_at = timezone.now()
            ticket.status = 'waiting_user'
        else:
            ticket.status = 'waiting_admin'
        ticket.save(update_fields=['first_response_at', 'status', 'updated_at'])

        # Обновить ChatSession
        ChatSession.objects.filter(ticket=ticket).update(
            messages_count=models.F('messages_count') + 1,
        )

        return {
            'id': str(message.id),
            'text': message.text,
            'sender_type': sender_type,
            'sender_name': self.user.username,
            'sender_avatar': self.user.get_avatar_url(),
            'created_at': message.created_at.isoformat(),
            'attachments': [],
        }

    @database_sync_to_async
    def get_message_history(self):
        """Получить последние 50 сообщений."""
        ticket = Ticket.objects.get(id=self.ticket_id)
        messages = Message.objects.filter(
            ticket=ticket,
            is_internal=False,
        ).select_related('sender').order_by('-created_at')[:50]

        return [{
            'id': str(m.id),
            'text': m.text,
            'sender_type': m.sender_type,
            'sender_name': m.sender.username if m.sender else 'Система',
            'created_at': m.created_at.isoformat(),
            'is_system': m.is_system_message,
            'is_read': m.is_read_by_user if self.user.is_staff else m.is_read_by_operator,
        } for m in reversed(messages)]

    @database_sync_to_async
    def check_rate_limit(self):
        from django.core.cache import cache
        key = f'chat_rate:{self.user.id}'
        if cache.get(key):
            return False
        cache.set(key, True, 2)
        return True

    @database_sync_to_async
    def mark_as_read(self, message_id):
        if self.user.is_staff:
            Message.objects.filter(id=message_id).update(
                is_read_by_operator=True, read_at=timezone.now()
            )
        else:
            Message.objects.filter(id=message_id).update(
                is_read_by_user=True, read_at=timezone.now()
            )

    @database_sync_to_async
    def end_chat_session(self, ended_by):
        ChatSession.objects.filter(ticket_id=self.ticket_id).update(
            chat_status='ended',
            ended_at=timezone.now(),
            ended_by=ended_by,
        )
        if ended_by == 'operator':
            Ticket.objects.filter(id=self.ticket_id).update(
                status='resolved',
                resolved_at=timezone.now(),
            )

    @database_sync_to_async
    def update_channel_name(self):
        session = ChatSession.objects.filter(ticket_id=self.ticket_id).first()
        if session:
            if self.user.is_staff:
                session.operator_channel_name = self.channel_name
            else:
                session.user_channel_name = self.channel_name
            session.save()

    @database_sync_to_async
    def set_operator_typing(self, is_typing):
        ChatSession.objects.filter(ticket_id=self.ticket_id).update(
            operator_typing=is_typing
        )

    @database_sync_to_async
    def set_user_typing(self, is_typing):
        ChatSession.objects.filter(ticket_id=self.ticket_id).update(
            user_typing=is_typing
        )
