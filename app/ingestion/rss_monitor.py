"""Async RSS feed monitor for legal sources."""

from dataclasses import dataclass, field
from datetime import date

import httpx
from loguru import logger


@dataclass
class RSSEntry:
    """Parsed entry from an RSS feed."""

    title: str
    url: str
    source: str
    published: date
    raw_content: str = ""
    legal_area: str = "general"
    tags: list[str] = field(default_factory=list)


@dataclass
class RSSFeed:
    """Configuration for a monitored RSS feed."""

    name: str
    url: str
    legal_area: str = "general"


# --- Feed registry (extend as needed) ---

REGISTERED_FEEDS: list[RSSFeed] = [
    RSSFeed(
        name="EUR-Lex Latest",
        url="https://eur-lex.europa.eu/tools/rss.do?other",
        legal_area="EU law",
    ),
]


async def fetch_feed_raw(feed: RSSFeed, client: httpx.AsyncClient) -> str:
    """Download raw XML for a feed.

    Args:
        feed: Feed configuration.
        client: Shared httpx async client.

    Returns:
        Raw XML string.

    Raises:
        httpx.HTTPError: On network or HTTP failures.
    """
    logger.debug("Fetching RSS feed", name=feed.name, url=feed.url)
    response = await client.get(feed.url, follow_redirects=True, timeout=30.0)
    response.raise_for_status()
    return response.text


def parse_feed(raw_xml: str, feed: RSSFeed) -> list[RSSEntry]:
    """Parse raw RSS XML into a list of RSSEntry objects.

    This is a stub implementation. Replace with a proper XML parser
    (e.g. feedparser or xml.etree.ElementTree) for production use.

    Args:
        raw_xml: Raw XML string from the feed.
        feed: Source feed configuration.

    Returns:
        List of parsed entries (empty in stub).
    """
    logger.warning("parse_feed is a stub — implement XML parsing for production")
    return []


async def monitor_feeds(
    feeds: list[RSSFeed] | None = None,
) -> list[RSSEntry]:
    """Fetch and parse all registered (or provided) RSS feeds.

    Args:
        feeds: Override list of feeds; defaults to REGISTERED_FEEDS.

    Returns:
        Aggregated list of new entries across all feeds.
    """
    target_feeds = feeds if feeds is not None else REGISTERED_FEEDS
    all_entries: list[RSSEntry] = []

    async with httpx.AsyncClient() as client:
        for feed in target_feeds:
            try:
                raw_xml = await fetch_feed_raw(feed, client)
                entries = parse_feed(raw_xml, feed)
                all_entries.extend(entries)
                logger.info("Feed processed", name=feed.name, entries=len(entries))
            except Exception as exc:
                logger.error("Failed to process feed", name=feed.name, error=str(exc))

    return all_entries
