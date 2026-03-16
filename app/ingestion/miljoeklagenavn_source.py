"""Ingestion source: Miljø- og Fødevareklagenævnet (naevneneshus.dk).

This is the Danish Environmental and Food Complaints Board — a key source of
administrative environmental law decisions.

Strategy:
  1. Fetch the decisions listing page via httpx
  2. Extract links to individual decision pages
  3. Scrape each decision with Firecrawl
  4. Parse topic, date, and full text from markdown
"""

import re
from datetime import date, datetime
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

import httpx
from loguru import logger

from app.ingestion.base_source import LegalSource, RawDocument
from app.ingestion.firecrawl_client import FirecrawlClient

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_URL = "https://naevneneshus.dk"
LISTING_URL = (
    f"{BASE_URL}/start-din-klage/miljoe-og-foedevareklagenaevnet/afgoerelser/"
)

REQUEST_TIMEOUT = 20.0
MAX_DECISIONS = 20


# ---------------------------------------------------------------------------
# Link extractor
# ---------------------------------------------------------------------------

class _DecisionLinkExtractor(HTMLParser):
    """Extracts hrefs to individual decision pages."""

    def __init__(self, base_url: str) -> None:
        super().__init__()
        self._base = base_url
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        href = dict(attrs).get("href") or ""
        if not href or href.startswith(("#", "mailto:")):
            return
        full = urljoin(self._base, href)
        parsed = urlparse(full)
        if (
            parsed.netloc == urlparse(self._base).netloc
            and _is_decision_path(parsed.path)
            and full not in self.links
        ):
            self.links.append(full)


def _is_decision_path(path: str) -> bool:
    patterns = ["/afg", "/afgoer", "/beslutning", "/decision"]
    lower = path.lower()
    return any(lower.count(p) > 0 for p in patterns) and len(path) > 40


# ---------------------------------------------------------------------------
# Markdown parsing helpers
# ---------------------------------------------------------------------------

_DATE_RE = re.compile(r"\b(\d{1,2})[./\-](\d{1,2})[./\-](\d{2,4})\b")
_ISO_DATE_RE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_TOPIC_PATTERNS = [
    re.compile(r"(?:Emne|Område|Topic)[:\s]+(.+)", re.IGNORECASE),
    re.compile(r"(?:Sagsnummer|Case)[:\s]+(.+)", re.IGNORECASE),
]


def _extract_title(markdown: str) -> str:
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()
        if stripped:
            return stripped[:200]
    return "Unnamed decision"


def _extract_date(markdown: str) -> date:
    # Try ISO date first
    m = _ISO_DATE_RE.search(markdown)
    if m:
        try:
            return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3))).date()
        except ValueError:
            pass
    # Fall back to Danish date format
    m2 = _DATE_RE.search(markdown)
    if m2:
        d, mo, y = int(m2.group(1)), int(m2.group(2)), int(m2.group(3))
        if y < 100:
            y += 2000
        try:
            return datetime(y, mo, d).date()
        except ValueError:
            pass
    return date.today()


def _extract_topic(markdown: str) -> str:
    for pattern in _TOPIC_PATTERNS:
        m = pattern.search(markdown)
        if m:
            return m.group(1).strip()[:200]
    return "Environmental decision"


# ---------------------------------------------------------------------------
# Source implementation
# ---------------------------------------------------------------------------

class MiljoeklagenævnSource(LegalSource):
    """Fetches environmental administrative decisions from naevneneshus.dk."""

    name = "miljoeklagenaevn"
    legal_area = "environmental_law"

    def __init__(
        self,
        listing_url: str = LISTING_URL,
        max_decisions: int = MAX_DECISIONS,
        firecrawl: FirecrawlClient | None = None,
    ) -> None:
        self._listing_url = listing_url
        self._max_decisions = max_decisions
        self._firecrawl = firecrawl or FirecrawlClient()

    async def fetch_new_documents(self) -> list[RawDocument]:
        """Scrape listing page, extract decision URLs, scrape each one."""
        logger.info("Checking source", source=self.name)

        decision_urls = await self._extract_decision_urls()
        if not decision_urls:
            logger.warning("No decision URLs found", source=self.name)
            return []

        capped = decision_urls[: self._max_decisions]
        logger.info("Scraping decisions", source=self.name, count=len(capped))

        results = await self._firecrawl.scrape_urls(capped)
        docs: list[RawDocument] = []

        for result in results:
            md = result.markdown
            topic = _extract_topic(md)
            docs.append(
                RawDocument(
                    title=_extract_title(md),
                    url=result.url,
                    source=self.name,
                    publication_date=_extract_date(md),
                    legal_area=self.legal_area,
                    raw_text=md or None,
                )
            )

        logger.info("Documents fetched", source=self.name, count=len(docs))
        return docs

    async def _extract_decision_urls(self) -> list[str]:
        """Fetch the listing page and parse out decision detail URLs."""
        try:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                resp = await client.get(self._listing_url, follow_redirects=True)
                resp.raise_for_status()
                html = resp.text
        except httpx.HTTPError as exc:
            logger.error(
                "Listing fetch failed", source=self.name, error=str(exc)
            )
            return []

        extractor = _DecisionLinkExtractor(self._listing_url)
        extractor.feed(html)
        logger.debug(
            "Decision URLs extracted", source=self.name, count=len(extractor.links)
        )
        return extractor.links
