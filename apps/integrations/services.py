import logging
from math import isfinite
from urllib.parse import urlsplit

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

ODDS_CACHE_KEY = 'integration_demo_odds_v1'
PREDICTIONS_CACHE_KEY = 'integration_demo_manifold_v1'
CACHE_TTL_SECONDS = 120
REQUEST_TIMEOUT_SECONDS = 8

DEMO_ODDS = [
    {
        'home': 'Demo FC',
        'away': 'Sample United',
        'commence_time': 'Демо-матч · данные для проверки интерфейса',
        'bookmakers': [{
            'name': 'DOD Demo',
            'markets': [{
                'outcomes': [
                    {'name': 'Demo FC', 'price': 1.85},
                    {'name': 'Ничья', 'price': 3.40},
                    {'name': 'Sample United', 'price': 4.20},
                ],
            }],
        }],
    },
    {
        'home': 'Test City',
        'away': 'Preview Athletic',
        'commence_time': 'Демо-матч · реальные ставки отключены',
        'bookmakers': [{
            'name': 'DOD Demo',
            'markets': [{
                'outcomes': [
                    {'name': 'Test City', 'price': 2.10},
                    {'name': 'Ничья', 'price': 3.10},
                    {'name': 'Preview Athletic', 'price': 3.45},
                ],
            }],
        }],
    },
]


def get_odds_feed(force_refresh=False):
    """Read odds from The Odds API when configured, otherwise return labeled demo data."""
    if not settings.THE_ODDS_API_KEY:
        return {
            'source': 'Демо-данные DOD',
            'mode': 'demo',
            'events': DEMO_ODDS,
            'error': '',
        }

    if not force_refresh:
        cached = cache.get(ODDS_CACHE_KEY)
        if cached is not None:
            return cached

    try:
        response = requests.get(
            f'https://api.the-odds-api.com/v4/sports/{settings.THE_ODDS_API_SPORT}/odds/',
            params={
                'apiKey': settings.THE_ODDS_API_KEY,
                'regions': 'us',
                'markets': 'h2h',
                'oddsFormat': 'decimal',
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            raise ValueError('The Odds API returned an unexpected response.')
        events = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            bookmakers = item.get('bookmakers')
            if not isinstance(bookmakers, list):
                bookmakers = []
            market_data = None
            bookmaker_name = 'Источник коэффициентов'
            for bookmaker in bookmakers:
                if not isinstance(bookmaker, dict):
                    continue
                markets = bookmaker.get('markets')
                if not isinstance(markets, list):
                    continue
                market_data = next(
                    (
                        market for market in markets
                        if isinstance(market, dict) and market.get('key') == 'h2h'
                    ),
                    None,
                )
                if market_data:
                    bookmaker_name = bookmaker.get('title') or bookmaker.get('key') or bookmaker_name
                    break

            outcomes = market_data.get('outcomes', []) if market_data else []
            if not isinstance(outcomes, list):
                outcomes = []
            events.append({
                'home': item.get('home_team') or 'Команда не указана',
                'away': item.get('away_team') or 'Команда не указана',
                'commence_time': item.get('commence_time') or '',
                'bookmakers': [{
                    'name': bookmaker_name,
                    'markets': [{'outcomes': outcomes}],
                }],
            })
        result = {
            'source': 'The Odds API',
            'mode': 'live',
            'events': events[:12],
            'error': '',
        }
        cache.set(ODDS_CACHE_KEY, result, CACHE_TTL_SECONDS)
        return result
    except (requests.RequestException, ValueError) as exc:
        logger.warning('Unable to load The Odds API feed (%s).', type(exc).__name__)
        return {
            'source': 'The Odds API',
            'mode': 'error',
            'events': [],
            'error': 'Не удалось получить коэффициенты. Проверьте ключ и доступность API.',
        }


def get_prediction_feed(force_refresh=False):
    """Read public, unresolved binary markets from Manifold's unauthenticated API."""
    if not force_refresh:
        cached = cache.get(PREDICTIONS_CACHE_KEY)
        if cached is not None:
            return cached

    try:
        response = requests.get(
            'https://api.manifold.markets/v0/markets',
            params={'limit': 30},
            headers={'User-Agent': 'DOD-demo-integration/1.0'},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            raise ValueError('Manifold returned an unexpected response.')

        markets = []
        for item in payload:
            if (
                not isinstance(item, dict)
                or item.get('isResolved')
                or item.get('outcomeType') != 'BINARY'
            ):
                continue
            probability = item.get('probability')
            question = item.get('question')
            url = item.get('url')
            if (
                not isinstance(question, str)
                or not isinstance(probability, (int, float))
                or not isfinite(probability)
                or not 0 <= probability <= 1
                or not isinstance(url, str)
                or urlsplit(url).scheme != 'https'
                or urlsplit(url).hostname != 'manifold.markets'
            ):
                continue
            volume = item.get('volume24Hours') or item.get('volume') or 0
            if not isinstance(volume, (int, float)) or not isfinite(volume) or volume < 0:
                volume = 0
            markets.append({
                'question': question,
                'probability': round(probability * 100, 1),
                'url': url,
                'volume': volume,
            })
            if len(markets) == 8:
                break

        result = {
            'source': 'Manifold',
            'mode': 'live',
            'markets': markets,
            'error': '',
        }
        cache.set(PREDICTIONS_CACHE_KEY, result, CACHE_TTL_SECONDS)
        return result
    except (requests.RequestException, ValueError) as exc:
        logger.warning('Unable to load Manifold prediction feed (%s).', type(exc).__name__)
        return {
            'source': 'Manifold',
            'mode': 'error',
            'markets': [],
            'error': 'Не удалось получить рынки Manifold. Попробуйте обновить страницу позже.',
        }
