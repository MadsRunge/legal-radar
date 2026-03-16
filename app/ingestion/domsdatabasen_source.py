"""Ingestion source: Domsdatabasen (domsdatabasen.dk).

Domsdatabasen is the official Danish court decision database, operated by the
Danish Court Administration (Domstolsstyrelsen).

Strategy:
  1. Fetch the search/listing page via httpx
  2. Extract links to individual decision pages using stdlib html.parser
  3. Scrape each decision page with Firecrawl (complex HTML, sometimes JS-rendered)
  4. Parse title, court, date, and full text from the returned markdown
"""

import re
from datetime import date, datetime
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

import httpx
from loguru import logger

from app.ingestion.base_source import LegalSource, RawDocument
from app.ingestion.firecrawl_client import FirecrawlClient, FirecrawlError

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_URL = "https://domsdatabasen.dk"
LISTING_URL = f"{BASE_URL}/"  # recent decisions shown on homepage / search

REQUEST_TIMEOUT = 20.0
MAX_DECISIONS = 20  # Firecrawl credits are not free — cap per run


# ---------------------------------------------------------------------------
# Link extractor
# ---------------------------------------------------------------------------

class _LinkExtractor(HTMLParser):
    """Extracts hrefs from <a> tags that look like decision detail pages."""

    def __init__(self, base_url: str) -> None:
        super().__init__()
        self._base = base_url
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        href = dict(attrs).get("href") or ""
        if not href or href.startswith(("#", "mailto:", "tel:")):
            return
        full = urljoin(self._base, href)
        parsed = urlparse(full)
        # Accept only same-domain paths that look like decision detail pages
        if parsed.netloc == urlparse(self._base).netloc and _is_decision_path(parsed.path):
            if full not in self.links:
                self.links.append(full)

    def handle_endtag(self, tag: str) -> None:
        pass


def _is_decision_path(path: str) -> bool:
    """Heuristic: decision URLs on domsdatabasen.dk contain /afgoerelse/ or similar."""
    patterns = ["/afgoerelse/", "/dom/", "/kendelse/", "/decision/"]
    return any(p in path.lower() for p in patterns)


# ---------------------------------------------------------------------------
# Markdown parser helpers
# ---------------------------------------------------------------------------

_DATE_RE = re.compile(r"\b(\d{1,2})[./\-](\d{1,2})[./\-](\d{2,4})\b")
_COURT_KEYWORDS = ["landsret", "højesteret", "byret", "sø- og handelsret", "vestre", "østre"]


def _extract_title(markdown: str) -> str:
    """Return first H1 or H2 heading, or first non-empty line."""
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()
        if stripped:
            return stripped[:200]
    return "Unnamed decision"


def _extract_date(markdown: str) -> date:
    match = _DATE_RE.search(markdown)
    if match:
        d, m, y = int(match.group(1)), int(match.group(2)), int(match.group(3))
        if y < 100:
            y += 2000
        try:
            return datetime(y, m, d).date()
        except ValueError:
            pass
    return date.today()


def _extract_court(markdown: str) -> str:
    lower = markdown.lower()
    for kw in _COURT_KEYWORDS:
        if kw in lower:
            return kw.title()
    return "Unknown court"


# ---------------------------------------------------------------------------
# Source implementation
# ---------------------------------------------------------------------------

class DomsdatabasenSource(LegalSource):
    """Fetches recent court decisions from domsdatabasen.dk via Firecrawl."""

    name = "domsdatabasen"
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
                "Listing page fetch failed", source=self.name, error=str(exc)
            )
            return []

        extractor = _LinkExtractor(self._listing_url)
        extractor.feed(html)
        logger.debug(
            "Decision URLs extracted", source=self.name, count=len(extractor.links)
        )
        return extractor.links
