"""
Provably Fair Service

Система для доказуемо честной генерации результатов казино.
Использует криптографический HMAC-SHA256 для гарантии честности.

ПРИНЦИП:
  1. До игры: Показываем пользователю хеш серверного seed
  2. Пользователь может установить свой client_seed  
  3. Результат = HMAC_SHA256(server_seed, client_seed:nonce)
  4. После игры: Раскрываем серверный seed
  5. Любой может проверить: SHA256(seed) == показанный хеш
  6. Пересчитать результат и убедиться в честности
"""

import secrets
import hmac
import hashlib
import math
from decimal import Decimal
from typing import Dict, List, Tuple
from django.db import models
from ..models import UserSeed


class ProvablyFairService:
    """
    Сервис для управления честностью игр.
    Все методы статические для простоты использования.
    """

    @staticmethod
    def generate_server_seed() -> str:
        """
        Генерировать новый серверный seed.
        256 бит энтропии (64 hex символа).
        
        Returns:
            str: Hex строка 64 символа
        """
        return secrets.token_hex(32)

    @staticmethod
    def hash_seed(seed: str) -> str:
        """
        SHA-256 хеш seed.
        
        Args:
            seed: Строка seed
            
        Returns:
            str: Hex строка SHA-256
        """
        return hashlib.sha256(seed.encode()).hexdigest()

    @staticmethod
    def generate_client_seed() -> str:
        """
        Сгенерировать дефолтный client_seed.
        
        Returns:
            str: Hex строка 32 символа
        """
        return secrets.token_hex(16)

    @staticmethod
    def get_or_create_user_seed(user) -> 'UserSeed':
        """
        Получить или создать seeds для пользователя.
        
        Args:
            user: User объект
            
        Returns:
            UserSeed: Объект пользовательского seed
        """
        seed, created = UserSeed.objects.get_or_create(
            user=user,
            defaults={
                'server_seed': ProvablyFairService.generate_server_seed(),
                'client_seed': ProvablyFairService.generate_client_seed(),
                'nonce': 0
            }
        )
        
        if created:
            seed.server_seed_hash = ProvablyFairService.hash_seed(seed.server_seed)
            seed.save()
        
        return seed

    @staticmethod
    def rotate_server_seed(user) -> Dict:
        """
        Сменить серверный seed.
        Старый seed РАСКРЫВАЕТСЯ.
        Новый seed генерируется, показывается только хеш.
        
        Args:
            user: User объект
            
        Returns:
            dict: {
                'revealed_seed': старый seed (теперь открытый),
                'new_seed_hash': хеш нового seed
            }
        """
        user_seed = UserSeed.objects.get(user=user)
        
        # Сохранить старый (раскрыть)
        user_seed.previous_server_seed = user_seed.server_seed
        user_seed.previous_server_seed_hash = user_seed.server_seed_hash
        
        # Сгенерировать новый
        new_seed = ProvablyFairService.generate_server_seed()
        user_seed.server_seed = new_seed
        user_seed.server_seed_hash = ProvablyFairService.hash_seed(new_seed)
        
        # Сбросить nonce
        user_seed.nonce = 0
        
        user_seed.save()
        
        return {
            "revealed_seed": user_seed.previous_server_seed,
            "new_seed_hash": user_seed.server_seed_hash
        }

    @staticmethod
    def change_client_seed(user, new_client_seed):
        """Пользователь меняет свой client_seed."""
        user_seed = UserSeed.objects.get(user=user)
        user_seed.client_seed = new_client_seed
        user_seed.save()

    @staticmethod
    def generate_game_result(server_seed, client_seed, nonce):
        """Генерация случайного числа из seeds."""
        message = f"{client_seed}:{nonce}"
        h = hmac.new(
            server_seed.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        return h

    @staticmethod
    def hash_to_float(hash_hex, offset=0):
        """Извлечь float 0.0-1.0 из hex hash."""
        hex_part = hash_hex[offset*8 : offset*8 + 8]
        int_value = int(hex_part, 16)
        float_value = int_value / 0xFFFFFFFF  # 4294967295
        return float_value

    @staticmethod
    def hash_to_int(hash_hex, max_value, offset=0):
        """Извлечь целое число 0 - (max_value-1)."""
        float_val = ProvablyFairService.hash_to_float(hash_hex, offset)
        return int(float_val * max_value)

    @staticmethod
    def generate_crash_point(hash_hex, house_edge_percent=3):
        """Генерация точки краша для Crash."""
        h = int(hash_hex[:13], 16)
        e = 2**52
        
        # house_edge% шанс на мгновенный краш (1.00x)
        if h % (100 / house_edge_percent) == 0:
            return Decimal('1.00')
        
        # Формула: (100 * e - h) / (e - h) / 100
        crash_point = (100 * e - h) / (e - h) / 100
        
        # Ограничить и округлить
        crash_point = max(1.00, crash_point)
        crash_point = round(Decimal(crash_point), 2)
        
        return crash_point

    @staticmethod
    def generate_dice_result(hash_hex):
        """Генерация результата для Dice (0.00 - 99.99)."""
        float_val = ProvablyFairService.hash_to_float(hash_hex)
        result = float_val * 10000
        result = math.floor(result) / 100
        return Decimal(result)

    @staticmethod
    def generate_roulette_result(hash_hex):
        """Генерация числа для Roulette (0-36)."""
        return ProvablyFairService.hash_to_int(hash_hex, 37)

    @staticmethod
    def generate_slots_reels(hash_hex, reels=5, rows=3, symbols=8):
        """Генерация барабанов для Slots."""
        result = []
        for reel in range(reels):
            reel_values = []
            for row in range(rows):
                offset = reel * rows + row
                symbol = ProvablyFairService.hash_to_int(hash_hex, symbols, offset)
                reel_values.append(symbol)
            result.append(reel_values)
        return result

    @staticmethod
    def generate_mines_positions(hash_hex, field_size=25, mines_count=5):
        """Генерация позиций мин для Mines."""
        positions = set()
        offset = 0
        while len(positions) < mines_count:
            pos = ProvablyFairService.hash_to_int(hash_hex, field_size, offset)
            positions.add(pos)
            offset += 1
            # Если не хватает энтропии → генерировать новый hash
            if offset >= 8:
                hash_hex = ProvablyFairService.hash_seed(hash_hex)
                offset = 0
        return sorted(list(positions))

    @staticmethod
    def generate_plinko_path(hash_hex, rows=16):
        """Генерация пути шарика для Plinko."""
        path = []
        for i in range(rows):
            direction = ProvablyFairService.hash_to_int(hash_hex, 2, i)  # 0=лево, 1=право
            path.append(direction)
        
        # Позиция = количество "право"
        landing = sum(path)
        return path, landing

    @staticmethod
    def verify_game(server_seed, server_seed_hash, client_seed, nonce, game_type, game_data):
        """Проверить честность игры."""
        # Проверить SHA256(server_seed) == server_seed_hash
        if ProvablyFairService.hash_seed(server_seed) != server_seed_hash:
            return {
                "verified": False,
                "server_seed_valid": False,
                "error": "Server seed не совпадает!"
            }
        
        # Вычислить result_hash
        result_hash = ProvablyFairService.generate_game_result(server_seed, client_seed, nonce)
        
        # Вычислить результат по типу игры
        if game_type == 'crash':
            calculated_result = ProvablyFairService.generate_crash_point(result_hash)
            stored_result = game_data.get('crash_point')
        elif game_type == 'dice':
            calculated_result = ProvablyFairService.generate_dice_result(result_hash)
            stored_result = game_data.get('result')
        elif game_type == 'roulette':
            calculated_result = ProvablyFairService.generate_roulette_result(result_hash)
            stored_result = game_data.get('winning_number')
        elif game_type == 'slots':
            calculated_result = ProvablyFairService.generate_slots_reels(result_hash)
            stored_result = game_data.get('reels')
        elif game_type == 'mines':
            calculated_result = ProvablyFairService.generate_mines_positions(
                result_hash, 
                game_data.get('field_size', 25), 
                game_data.get('mines_count', 5)
            )
            stored_result = game_data.get('mines_positions')
        elif game_type == 'plinko':
            calculated_result = ProvablyFairService.generate_plinko_path(result_hash, game_data.get('rows', 16))
            stored_result = (game_data.get('path'), game_data.get('landing_position'))
        else:
            return {"verified": False, "error": "Неизвестный тип игры"}
        
        # Сравнить
        match = calculated_result == stored_result
        
        return {
            "verified": True,
            "server_seed_valid": True,
            "calculated_result": calculated_result,
            "stored_result": stored_result,
            "match": match
        }

    @staticmethod
    def get_slot_weights() -> Dict[int, float]:
        """Веса символов для Slots (RTP ≈ 96%)."""
        return {
            0: 0.25,    # 🍒 Cherry
            1: 0.20,    # 🍋 Lemon
            2: 0.18,    # 🍊 Orange
            3: 0.15,    # 🍇 Grapes
            4: 0.10,    # 🔔 Bell
            5: 0.07,    # ⭐ Star
            6: 0.035,   # 💎 Diamond
            7: 0.015    # 7️⃣ Seven
        }

    @staticmethod
    def get_slot_paylines() -> List[List[int]]:
        """20 стандартных линий выплат для Slots."""
        return [
            [1, 1, 1, 1, 1],  # Средняя
            [0, 0, 0, 0, 0],  # Верхняя
            [2, 2, 2, 2, 2],  # Нижняя
            [0, 1, 2, 1, 0],  # V-форма
            [2, 1, 0, 1, 2],  # ^-форма
            [0, 1, 1, 1, 0],
            [2, 1, 1, 1, 2],
            [1, 0, 1, 0, 1],
            [1, 2, 1, 2, 1],
            [0, 0, 1, 0, 0],
            [2, 2, 1, 2, 2],
            [1, 0, 0, 0, 1],
            [1, 2, 2, 2, 1],
            [0, 1, 0, 1, 0],
            [2, 1, 2, 1, 2],
            [0, 0, 2, 0, 0],
            [2, 2, 0, 2, 2],
            [0, 2, 1, 2, 0],
            [2, 0, 1, 0, 2],
            [1, 1, 0, 1, 1],
        ]

    @staticmethod
    def get_slot_paytable() -> Dict[int, Dict[int, int]]:
        """Таблица выплат для символов Slots."""
        return {
            0: {3: 2, 4: 5, 5: 10},        # 🍒
            1: {3: 3, 4: 8, 5: 15},        # 🍋
            2: {3: 4, 4: 10, 5: 20},       # 🍊
            3: {3: 5, 4: 15, 5: 30},       # 🍇
            4: {3: 8, 4: 25, 5: 50},       # 🔔
            5: {3: 10, 4: 40, 5: 100},     # ⭐
            6: {3: 25, 4: 100, 5: 500},    # 💎
            7: {3: 50, 4: 250, 5: 1000},   # 7️⃣
        }

    @staticmethod
    def calculate_mines_multiplier(safe_opened: int, mines_count: int,
                                  house_edge_percent: float = 2.0) -> float:
        """Рассчитать множитель для Mines."""
        from math import comb

        field_size = 25
        safe_count = field_size - mines_count

        if safe_opened == 0:
            return 1.0

        if safe_opened > safe_count:
            return 0.0

        total_ways = comb(field_size, safe_opened)
        safe_ways = comb(safe_count, safe_opened)

        if total_ways == 0:
            return 0.0

        probability = safe_ways / total_ways
        multiplier = (1.0 / probability) if probability > 0 else 0.0

        multiplier = multiplier * ((100 - house_edge_percent) / 100)

        return round(multiplier, 2)

    @staticmethod
    def calculate_plinko_multiplier(rows: int, risk: str, landing_position: int) -> float:
        """Рассчитать множитель для Plinko."""
        multipliers_by_rows_risk = {
            8: {
                'low': [400, 16, 2, 1, 0.5, 1, 2, 16, 400],
                'medium': [300, 10, 2, 1.2, 0.8, 1.2, 2, 10, 300],
                'high': [100, 4, 1.5, 1, 1, 1, 1.5, 4, 100],
            },
            12: {
                'low': [900, 100, 10, 3, 1.5, 1, 1, 1.5, 3, 10, 100, 900, 9000],
                'medium': [500, 50, 5, 2, 1.2, 0.8, 0.8, 1.2, 2, 5, 50, 500, 5000],
                'high': [200, 20, 3, 1.5, 1, 0.5, 0.5, 1, 1.5, 3, 20, 200, 2000],
            },
            16: {
                'low': [3000, 500, 100, 41, 10, 5, 3, 1.5, 1, 1.5, 3, 5, 10, 41, 100, 500, 3000],
                'medium': [1000, 200, 41, 10, 5, 3, 1.5, 1, 0.5, 1, 1.5, 3, 5, 10, 41, 200, 1000],
                'high': [300, 100, 20, 5, 3, 1.5, 1, 0.5, 0.3, 0.5, 1, 1.5, 3, 5, 20, 100, 300],
            }
        }

        config = multipliers_by_rows_risk.get(rows, {}).get(risk)
        if not config or landing_position >= len(config):
            return 1.0

        return config[landing_position]
