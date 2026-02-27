# apps/core/metrics.py

from prometheus_client import Counter, Histogram, Gauge

# Бизнес-метрики
bets_placed_total = Counter(
    'dod_bets_placed_total',
    'Всего ставок',
    ['type', 'sport']
)

bets_amount_total = Counter(
    'dod_bets_amount_total',
    'Сумма ставок (USD)',
    ['type']
)

deposits_total = Counter(
    'dod_deposits_total',
    'Всего депозитов',
    ['method', 'currency']
)

withdrawals_total = Counter(
    'dod_withdrawals_total',
    'Всего выводов',
    ['method', 'status']
)

active_users_gauge = Gauge(
    'dod_active_users',
    'Активные пользователи сейчас'
)

websocket_connections = Gauge(
    'dod_websocket_connections',
    'WebSocket соединения',
    ['type']  # chat, casino, notifications
)

casino_rounds_total = Counter(
    'dod_casino_rounds_total',
    'Всего раундов казино',
    ['game']
)

ggr_total = Counter(
    'dod_ggr_total',
    'Gross Gaming Revenue (USD)'
)

prediction_trades_total = Counter(
    'dod_prediction_trades_total',
    'Сделки в маркетах',
    ['action']  # buy, sell
)
