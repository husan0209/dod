from django.test import TestCase

from ..models import Category, Market, Outcome, AMMPool, UserPosition, Trade, PriceHistory, Comment, CommentLike


class CategoryModelTest(TestCase):

    def test_category_creation(self):
        category = Category.objects.create(
            name='Test Category',
            name_en='Test Category EN',
            slug='test-category',
            icon='🎯',
            description='Test description',
            color='#000000',
            sort_order=1,
            is_active=True,
        )
        self.assertEqual(category.name, 'Test Category')
        self.assertEqual(category.slug, 'test-category')
        self.assertTrue(category.is_active)


class MarketModelTest(TestCase):

    def setUp(self):
        self.category = Category.objects.create(
            name='Test Category',
            slug='test-category',
            icon='🎯',
            color='#000000',
        )

    def test_market_creation(self):
        market = Market.objects.create(
            title='Test Market',
            title_en='Test Market EN',
            slug='test-market',
            description='Test description',
            category=self.category,
            market_type='binary',
            opens_at='2024-01-01T00:00:00Z',
            closes_at='2024-12-31T23:59:59Z',
            initial_liquidity=1000,
            fee_percent=2.00,
        )
        self.assertEqual(market.title, 'Test Market')
        self.assertEqual(market.market_type, 'binary')
        self.assertEqual(market.status, 'draft')  # default


class OutcomeModelTest(TestCase):

    def setUp(self):
        self.category = Category.objects.create(
            name='Test Category',
            slug='test-category',
            icon='🎯',
            color='#000000',
        )
        self.market = Market.objects.create(
            title='Test Market',
            slug='test-market',
            description='Test description',
            category=self.category,
            opens_at='2024-01-01T00:00:00Z',
            closes_at='2024-12-31T23:59:59Z',
        )

    def test_outcome_creation(self):
        outcome = Outcome.objects.create(
            market=self.market,
            title='Yes',
            slug='yes',
            sort_order=0,
            current_price=0.50,
        )
        self.assertEqual(outcome.title, 'Yes')
        self.assertEqual(outcome.current_price, 0.50)


class TradeModelTest(TestCase):

    def setUp(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
        )
        self.category = Category.objects.create(
            name='Test Category',
            slug='test-category',
            icon='🎯',
            color='#000000',
        )
        self.market = Market.objects.create(
            title='Test Market',
            slug='test-market',
            description='Test description',
            category=self.category,
            opens_at='2024-01-01T00:00:00Z',
            closes_at='2024-12-31T23:59:59Z',
        )
        self.outcome = Outcome.objects.create(
            market=self.market,
            title='Yes',
            slug='yes',
            current_price=0.50,
        )

    def test_trade_creation(self):
        trade = Trade.objects.create(
            user=self.user,
            market=self.market,
            outcome=self.outcome,
            trade_type='buy',
            shares=10,
            price_per_share=0.50,
            total_cost=5.00,
            fee_amount=0.10,
            total_amount=5.10,
            price_before=0.50,
            price_after=0.51,
        )
        self.assertEqual(trade.trade_type, 'buy')
        self.assertEqual(trade.shares, 10)
        self.assertEqual(trade.total_amount, 5.10)
