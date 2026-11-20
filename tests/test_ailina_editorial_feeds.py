"""Regression tests for AiLina editorial RSS category and intake improvements."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from xml.etree import ElementTree as ET

import httpx
import pytest

from src.models import RSSSourceConfig
from src.scrapers.rss import RSSScraper


NOW = datetime(2026, 11, 20, 0, 0, tzinfo=timezone.utc)
FEED = """<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0"><channel><title>TAAFT</title>
  <item><guid>main</guid><title>New AI model</title>
    <link>https://newsletter.theresanaiforthat.com/p/test</link>
    <pubDate>Fri, 20 Nov 2026 10:00:00 +0000</pubDate>
    <category>taaft</category><description>Actual product release.</description></item>
  <item><guid>prompt</guid><title>Prompt of the Day</title>
    <link>https://newsletter.theresanaiforthat.com/p/test</link>
    <pubDate>Fri, 20 Nov 2026 10:00:00 +0000</pubDate>
    <category>taaft-prompt</category><description>Practical user task.</description></item>
  <item><guid>gadget</guid><title>New AI wearable</title>
    <link>https://newsletter.theresanaiforthat.com/p/test</link>
    <pubDate>Fri, 20 Nov 2026 10:00:00 +0000</pubDate>
    <category>taaft-device</category><description>Consumer hardware.</description></item>
</channel></rss>"""


async def read(feed: str = FEED, *, name: str = "TAAFT", limit=None):
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(
                200,
                content=feed.encode("utf-8"),
                headers={"Content-Type": "application/rss+xml"},
            )
        )
    ) as client:
        source = RSSSourceConfig(
            name=name,
            url="https://example.org/feed.xml",
            category="taaft" if name == "TAAFT" else "research",
            fetch_limit=limit,
            profile="ailina",
        )
        return await RSSScraper([source], client).fetch(NOW)


def test_daily_prompt_and_gadget_keep_independent_quotas():
    items = asyncio.run(read()).items
    assert len(items) == 3
    assert [item.metadata["category"] for item in items] == [
        "taaft", "taaft-prompt", "taaft-device"
    ]
    assert all(item.metadata["feed_name"] == "TAAFT" for item in items)
    assert len(set(item.id for item in items)) == 3


def test_normal_rss_categories_ignore_taaft_tags():
    items = asyncio.run(read(name="Other")).items
    assert len(items) == 3
    assert {item.metadata["category"] for item in items} == {"research"}


def test_fetch_limit_bounds_high_volume_feed():
    items = asyncio.run(read(limit=2)).items
    assert [item.title for item in items] == [
        "New AI model", "Prompt of the Day"
    ]


@pytest.mark.parametrize("limit", [0, 101])
def test_invalid_rss_limits_are_rejected(limit):
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        RSSSourceConfig(name="invalid", url="https://example.org/feed", fetch_limit=limit)


def test_lancet_rdf_rss_uses_dc_date():
    feed = """<?xml version="1.0"?>
    <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
       xmlns="http://purl.org/rss/1.0/"
       xmlns:dc="http://purl.org/dc/elements/1.1/">
       <channel rdf:about="https://www.thelancet.com/rssfeed/test">
         <title>Journal</title><link>https://thelancet.com</link>
         <description>Research</description></channel>
       <item rdf:about="https://example.org/lancet-study">
         <title>Clinical machine-learning validation</title>
         <link>https://example.org/lancet-study</link>
         <description>Independent multicentre trial.</description>
         <dc:date>2026-11-20T10:00:00Z</dc:date>
       </item>
    </rdf:RDF>"""
    result = asyncio.run(read(feed, name="Lancet"))
    assert result.status == "success"
    assert len(result.items) == 1
    assert result.items[0].published_at.date().isoformat() == "2026-11-20"
    assert result.items[0].metadata["category"] == "research"
