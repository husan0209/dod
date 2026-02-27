from django.test import TestCase
from django.contrib.auth import get_user_model
from decimal import Decimal
from ..models import GameType, GameSession, CrashGame, UserSeed, CasinoSettings
from ..services import ProvablyFairService


class GameTypeModelTest(TestCase):
    def setUp(self):
        self.game_type = GameType.objects.create(
            code='test',
            name='Test Game',
            name_en='Test Game',
            description='A test game',
            icon='🎮',
            house_edge=Decimal('5.00'),
            rtp=Decimal('95.00'),
            min_bet=Decimal('0.10'),
            max_bet=Decimal('100.00'),
            max_win_multiplier=Decimal('100.00')
        )

    def test_game_type_creation(self):
        self.assertEqual(self.game_type.code, 'test')
        self.assertEqual(self.game_type.name, 'Test Game')
        self.assertEqual(self.game_type.house_edge, Decimal('5.00'))


class UserSeedModelTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='testuser',
            email='test@example.com',
            password='password123'
        )

    def test_user_seed_creation(self):
        seed = ProvablyFairService.get_or_create_user_seed(self.user)
        self.assertIsNotNone(seed.server_seed)
        self.assertIsNotNone(seed.server_seed_hash)
        self.assertIsNotNone(seed.client_seed)
        self.assertEqual(seed.nonce, 0)


class CasinoSettingsModelTest(TestCase):
    def test_casino_settings_singleton(self):
        settings1 = CasinoSettings.get_settings()
        settings2 = CasinoSettings.get_settings()
        self.assertEqual(settings1, settings2)
