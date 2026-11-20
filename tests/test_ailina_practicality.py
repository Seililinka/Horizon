"""AiLina-specific practical value ranking and Telegram public engagement tests."""
from datetime import datetime, timezone

from bs4 import BeautifulSoup

from src.models import ClassificationResult, ContentAnalysis, ContentItem, ProcessingResult, SourceType, TelegramChannelConfig, TelegramConfig
from src.orchestrator import HorizonOrchestrator
from src.scrapers.telegram import TelegramScraper


def _item(score, practical, *, taaft=False, profile="ailina"):
    return ContentItem(
        id="test-news",
        title="Testing practical value",
        source_type=SourceType.RSS,
        url="https://example.com/news",
        published_at=datetime.now(timezone.utc),
        metadata={"feed_name": "TAAFT"} if taaft else {"category": "telegram-ai"},
        processing=ProcessingResult(
            classification=ClassificationResult(profile=profile, method="source_override"),
            analysis=ContentAnalysis(
                score=score, practicality_score=practical, reason="test", summary="test"
            ),
        ),
    )


def test_practicality_boost_prioritizes_actionable_news():
    practical = _item(6.0, 9.0)
    theoretical = _item(6.0, 2.0)
    assert HorizonOrchestrator.editorial_rank_score(practical) == 7.5
    assert HorizonOrchestrator.editorial_rank_score(theoretical) == 6.0


def test_taaft_bonus_and_practicality_stay_bounded():
    item = _item(9.0, 9.0, taaft=True)
    assert HorizonOrchestrator.editorial_rank_score(item) == 10.0
    assert item.processing.analysis.score == 9.0


def test_practicality_boost_only_applies_to_ailina():
    other = _item(6.0, 9.0, profile="tech-news")
    assert HorizonOrchestrator.editorial_rank_score(other) == 6.0


def test_public_telegram_engagement_is_parsed_without_fake_numbers():
    import unittest.mock
    html = """
    <div class="tgme_widget_message" data-post="bugnotfeature/123">
      <div class="tgme_widget_message_text js-message_text">Useful AI tutorial with a concrete workflow.</div>
      <time datetime="2026-11-20T12:00:00Z"></time>
      <span class="tgme_widget_message_views">1.2K</span>
      <div class="tgme_widget_message_reactions">
         <span class="tgme_widget_message_reaction_count">53</span>
         <span class="tgme_widget_message_reaction_count">7</span>
      </div>
    </div>
    """
    msg = BeautifulSoup(html, "html.parser").select_one(".tgme_widget_message")
    scraper = TelegramScraper(TelegramConfig(), unittest.mock.AsyncMock())
    item = scraper._parse_message(
        msg, TelegramChannelConfig(channel="bugnotfeature"),
        datetime(2026, 11, 20, 0, 0, tzinfo=timezone.utc)
    )
    assert item.metadata["views"] == 1200
    assert item.metadata["reactions"] == 60


def test_public_count_keeps_missing_data_unknown():
    assert TelegramScraper._parse_public_count(None) is None
    assert TelegramScraper._parse_public_count(
        BeautifulSoup("<span>2,5M</span>", "html.parser").span
    ) == 2500000
