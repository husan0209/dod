import secrets
import hashlib
import hmac
import math
from decimal import Decimal
from ..models import UserSeed


class ProvablyFairService:
    """
    Доказуемо честная генерация результатов.
    """

    @staticmethod
    def generate_server_seed():
        """Генерировать новый серверный seed."""
        seed = secrets.token_hex(32)  # 64 символа hex = 256 бит энтропии
        return seed

    @staticmethod
    def hash_seed(seed):
        """SHA-256 хеш seed."""
        return hashlib.sha256(seed.encode()).hexdigest()

    @staticmethod
    def generate_client_seed():
        """Сгенерировать дефолтный client_seed."""
        return secrets.token_hex(16)  # 32 символа hex

    @staticmethod
    def get_or_create_user_seed(user):
        """Получить или создать seeds для пользователя."""
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
    def rotate_server_seed(user):
        """Сменить серверный seed."""
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
