import pytest
from django.test import TestCase
from django.utils import timezone
from apps.sports.models import (
    Sport, Country, League, Team, Event, MarketType, Market,
    Outcome, Bet, BetItem, BetSettings
)


class SportsModelsTestCase(TestCase):
    """Basic tests for sports betting models"""
    fixtures = ['sports', 'countries', 'market_types']

    def test_fixtures_loaded(self):
        """Test that initial fixtures are loaded"""
        self.assertEqual(Sport.objects.count(), 12)
        self.assertEqual(Country.objects.count(), 7)
        self.assertEqual(MarketType.objects.count(), 17)

    def test_sport_creation(self):
        """Test creating a new sport"""
        sport = Sport.objects.create(
            name="Test Sport",
            name_en="Test Sport",
            slug="test-sport",
            icon="🎯",
            sort_order=99
        )
        self.assertEqual(sport.name, "Test Sport")
        self.assertEqual(str(sport), "Test Sport")

    def test_event_creation_and_methods(self):
        """Test creating an event and its methods"""
        sport = Sport.objects.get(slug='football')
        country = Country.objects.get(code='RU')
        league = League.objects.create(
            sport=sport,
            country=country,
            name="Test League",
            name_en="Test League",
            short_name="TL",
            slug="test-league",
            season="2024/2025"
        )
        home_team = Team.objects.create(
            sport=sport,
            name="Home Team",
            name_en="Home Team",
            short_name="HT"
        )
        away_team = Team.objects.create(
            sport=sport,
            name="Away Team",
            name_en="Away Team",
            short_name="AT"
        )

        # Create event
        event = Event.objects.create(
            sport=sport,
            league=league,
            home_team=home_team,
            away_team=away_team,
            start_time=timezone.now() + timezone.timedelta(hours=2),
            status='prematch'
        )

        # Test methods
        self.assertTrue(event.is_bettable())
        self.assertFalse(event.is_started())
        self.assertFalse(event.is_settled())
        self.assertIn("через", event.get_time_until_start())
        self.assertEqual(event.get_formatted_score(), "— : —")

        # Test automatic name generation
        expected_name = f"{home_team.name} — {away_team.name}"
        self.assertEqual(event.name, expected_name)

    def test_market_and_outcome_creation(self):
        """Test creating market and outcomes"""
        sport = Sport.objects.get(slug='football')
        event = Event.objects.create(
            sport=sport,
            league=League.objects.create(
                sport=sport,
                name="Test League",
                name_en="Test League",
                short_name="TL",
                slug="test-league-2",
                season="2024/2025"
            ),
            home_team=Team.objects.create(sport=sport, name="Team A", name_en="Team A", short_name="TA"),
            away_team=Team.objects.create(sport=sport, name="Team B", name_en="Team B", short_name="TB"),
            start_time=timezone.now() + timezone.timedelta(hours=2)
        )

        market_type = MarketType.objects.get(code='1x2')
        market = Market.objects.create(
            event=event,
            market_type=market_type,
            name="Test Market",
            parameter=None
        )

        # Create outcomes based on template
        for outcome_data in market_type.outcomes_template:
            Outcome.objects.create(
                market=market,
                code=outcome_data['code'],
                name=outcome_data['name'],
                odd=2.0,
                odd_initial=2.0
            )

        self.assertEqual(Outcome.objects.filter(market=market).count(), 3)

    def test_bet_settings_singleton(self):
        """Test BetSettings singleton behavior"""
        settings1 = BetSettings.get_settings()
        settings2 = BetSettings.get_settings()
        self.assertEqual(settings1.id, settings2.id)
        self.assertEqual(settings1.min_stake_usd, 0.50)

    def test_relationships(self):
        """Test model relationships"""
        sport = Sport.objects.get(slug='football')
        country = Country.objects.get(code='GB')
        league = League.objects.filter(sport=sport, country=country).first()
        if not league:
            league = League.objects.create(
                sport=sport,
                country=country,
                name="Premier League",
                name_en="Premier League",
                short_name="PL",
                slug="premier-league-test",
                season="2024/2025"
            )

        # Check relationships
        self.assertIn(league, sport.leagues.all())
        self.assertIn(league, country.leagues.all())
