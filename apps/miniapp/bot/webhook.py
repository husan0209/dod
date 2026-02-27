# apps/miniapp/bot/webhook.py

import json
import hmac
import hashlib
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings
import logging

from .handlers import (
    start_command, balance_command, deposit_command,
    referral_command, support_command, settings_command, help_command,
    handle_callback, handle_inline_query
)

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def bot_webhook(request):
    """
    Webhook endpoint for Telegram bot updates.

    URL: /tg/bot/webhook/
    Method: POST
    Verification: X-Telegram-Bot-Api-Secret-Token
    """

    # Verify secret token
    secret_token = request.headers.get('X-Telegram-Bot-Api-Secret-Token')
    if not secret_token or secret_token != settings.TELEGRAM_WEBHOOK_SECRET:
        logger.warning("Invalid webhook secret token")
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    try:
        # Parse update
        update_data = json.loads(request.body.decode('utf-8'))
        logger.info(f"Received update: {update_data.get('update_id')}")

        # Process update
        response = process_update(update_data)

        # Always return 200 OK (even on errors)
        return JsonResponse(response or {'status': 'ok'})

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in webhook: {e}")
        return JsonResponse({'status': 'ok'})  # Still return OK
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return JsonResponse({'status': 'ok'})  # Don't break webhook


def process_update(update_data):
    """Process Telegram update."""
    update_type = get_update_type(update_data)

    try:
        if update_type == 'message':
            return handle_message(update_data['message'])
        elif update_type == 'callback_query':
            return handle_callback_query(update_data['callback_query'])
        elif update_type == 'inline_query':
            return handle_inline_query_update(update_data['inline_query'])
        elif update_type == 'chosen_inline_result':
            return handle_chosen_inline_result(update_data['chosen_inline_result'])
        else:
            logger.info(f"Unhandled update type: {update_type}")
            return {'status': 'ignored'}

    except Exception as e:
        logger.error(f"Error processing update {update_type}: {e}")
        return {'status': 'error'}


def get_update_type(update_data):
    """Determine update type."""
    if 'message' in update_data:
        return 'message'
    elif 'callback_query' in update_data:
        return 'callback_query'
    elif 'inline_query' in update_data:
        return 'inline_query'
    elif 'chosen_inline_result' in update_data:
        return 'chosen_inline_result'
    else:
        return 'unknown'


def handle_message(message):
    """Handle message update."""
    text = message.get('text', '')
    chat_id = message['chat']['id']

    if not text.startswith('/'):
        # Not a command, ignore
        return {'status': 'ignored'}

    # Parse command
    command = text.split()[0].lstrip('/')
    args = text.split()[1:] if len(text.split()) > 1 else []

    # Create mock update object for handlers
    update = MockUpdate(message, command, args)

    try:
        # Route to appropriate handler
        if command == 'start':
            # Run async handler synchronously (simplified)
            return handle_start_command(update)
        elif command == 'balance':
            return handle_balance_command(update)
        elif command == 'deposit':
            return handle_deposit_command(update)
        elif command == 'referral':
            return handle_referral_command(update)
        elif command == 'support':
            return handle_support_command(update)
        elif command == 'settings':
            return handle_settings_command(update)
        elif command == 'help':
            return handle_help_command(update)
        else:
            logger.info(f"Unknown command: {command}")
            return {'status': 'unknown_command'}

    except Exception as e:
        logger.error(f"Error handling command {command}: {e}")
        return {'status': 'error'}


def handle_callback_query(callback_query):
    """Handle callback query."""
    # Create mock update object
    update = MockUpdate(callback_query=callback_query)

    try:
        return handle_callback_command(update)
    except Exception as e:
        logger.error(f"Error handling callback: {e}")
        return {'status': 'error'}


def handle_inline_query_update(inline_query):
    """Handle inline query."""
    # Create mock update object
    update = MockUpdate(inline_query=inline_query)

    try:
        return handle_inline_query_command(update)
    except Exception as e:
        logger.error(f"Error handling inline query: {e}")
        return {'status': 'error'}


def handle_chosen_inline_result(chosen_result):
    """Handle chosen inline result."""
    logger.info(f"Chosen inline result: {chosen_result.get('result_id')}")
    return {'status': 'ok'}


# Mock classes to simulate python-telegram-bot objects
class MockUpdate:
    def __init__(self, message=None, callback_query=None, inline_query=None):
        self.message = MockMessage(message) if message else None
        self.callback_query = MockCallbackQuery(callback_query) if callback_query else None
        self.inline_query = MockInlineQuery(inline_query) if inline_query else None


class MockMessage:
    def __init__(self, data):
        self.text = data.get('text', '')
        self.chat = MockChat(data.get('chat', {}))
        self.from_user = MockUser(data.get('from', {}))
        self.date = MockDate(data.get('date', 0))


class MockChat:
    def __init__(self, data):
        self.id = data.get('id')


class MockUser:
    def __init__(self, data):
        self.id = data.get('id')
        self.first_name = data.get('first_name')
        self.last_name = data.get('last_name')
        self.username = data.get('username')
        self.language_code = data.get('language_code')
        self.photo_url = None  # Not available in webhook data


class MockDate:
    def __init__(self, timestamp):
        self.timestamp = lambda: timestamp


class MockCallbackQuery:
    def __init__(self, data):
        self.data = data.get('data')
        self.from_user = MockUser(data.get('from', {}))
        self.message = MockMessage(data.get('message', {})) if 'message' in data else None


class MockInlineQuery:
    def __init__(self, data):
        self.query = data.get('query', '')
        self.from_user = MockUser(data.get('from', {}))
        self.id = data.get('id')


# Simplified synchronous handlers (would be async in real implementation)
def handle_start_command(update):
    # Simulate async behavior
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Create mock context
    context = MockContext()

    try:
        loop.run_until_complete(start_command(update, context))
    except Exception as e:
        logger.error(f"Error in start command: {e}")
    finally:
        loop.close()

    return {'status': 'ok'}


def handle_balance_command(update):
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    context = MockContext()

    try:
        loop.run_until_complete(balance_command(update, context))
    except Exception as e:
        logger.error(f"Error in balance command: {e}")
    finally:
        loop.close()

    return {'status': 'ok'}


def handle_deposit_command(update):
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    context = MockContext()

    try:
        loop.run_until_complete(deposit_command(update, context))
    except Exception as e:
        logger.error(f"Error in deposit command: {e}")
    finally:
        loop.close()

    return {'status': 'ok'}


def handle_referral_command(update):
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    context = MockContext()

    try:
        loop.run_until_complete(referral_command(update, context))
    except Exception as e:
        logger.error(f"Error in referral command: {e}")
    finally:
        loop.close()

    return {'status': 'ok'}


def handle_support_command(update):
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    context = MockContext()

    try:
        loop.run_until_complete(support_command(update, context))
    except Exception as e:
        logger.error(f"Error in support command: {e}")
    finally:
        loop.close()

    return {'status': 'ok'}


def handle_settings_command(update):
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    context = MockContext()

    try:
        loop.run_until_complete(settings_command(update, context))
    except Exception as e:
        logger.error(f"Error in settings command: {e}")
    finally:
        loop.close()

    return {'status': 'ok'}


def handle_help_command(update):
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    context = MockContext()

    try:
        loop.run_until_complete(help_command(update, context))
    except Exception as e:
        logger.error(f"Error in help command: {e}")
    finally:
        loop.close()

    return {'status': 'ok'}


def handle_callback_command(update):
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    context = MockContext()

    try:
        loop.run_until_complete(handle_callback(update, context))
    except Exception as e:
        logger.error(f"Error in callback handler: {e}")
    finally:
        loop.close()

    return {'status': 'ok'}


def handle_inline_query_command(update):
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    context = MockContext()

    try:
        loop.run_until_complete(handle_inline_query(update, context))
    except Exception as e:
        logger.error(f"Error in inline query handler: {e}")
    finally:
        loop.close()

    return {'status': 'ok'}


class MockContext:
    def __init__(self):
        self.args = []
