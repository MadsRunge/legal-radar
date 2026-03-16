"""Ingestion source: Retsinformation (retsinformation.dk).

Retsinformation is the official Danish legal gazette — primary source for
laws, executive orders, and environmental regulations.

Strategy:
  1. Fetch the RSS feed for recent documents
  2. Filter entries by environmental keywords
  3. Fetch full document HTML and strip to plain text
  4. Return as RawDocument list
"""

import re
import xml.etree.ElementTree as ET
from datetime import date, datetime
from html.parser import HTMLParser

import httpx
from loguru import logger

from app.ingestion.base_source import LegalSource, RawDocument

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

RSS_URL = "https://www.retsinformation.dk/api/rss"

ENVIRONMENTAL_KEYWORDS: frozenset[str] = frozenset(
    {"miljø", "natur", "planlov", "affald", "vand", "klima", "forurening", "biodiversitet"}
)

REQUEST_TIMEOUT = 20.0
MAX_DOCUMENTS = 50  # cap per run to avoid overwhelming the pipeline


# ---------------------------------------------------------------------------
# HTML text extractor
# ---------------------------------------------------------------------------

class _TextExtractor(HTMLParser):
    """Minimal HTML → plain text extractor using stdlib only."""

    _SKIP_TAGS = {"script", "style", "head", "nav", "footer", "header"}

    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in self._SKIP_TAGS:
            self._skip += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in self._SKIP_TAGS:
            self._skip = max(0, self._skip - 1)

    def handle_data(self, data: str) -> None:
        if not self._skip:
            stripped = data.strip()
            if stripped:
                self._parts.append(stripped)

    @property
    def text(self) -> str:
        return "\n".join(self._parts)


def _html_to_text(html: str) -> str:
    parser = _TextExtractor()
    parser.feed(html)
    return parser.text


# ---------------------------------------------------------------------------
# Keyword matching
# ---------------------------------------------------------------------------

def _matches_environmental(text: str) -> bool:
    """Return True if any environmental keyword appears in the text."""
    lower = text.lower()
    return any(kw in lower for kw in ENVIRONMENTAL_KEYWORDS)


# ---------------------------------------------------------------------------
# Date parsing
# ---------------------------------------------------------------------------

_DATE_FORMATS = [
    "%a, %d %b %Y %H:%M:%S %z",
    "%a, %d %b %Y %H:%M:%S GMT",
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%d",
]


def _parse_date(raw: str | None) -> date:
    if not raw:
        return date.today()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(raw.strip(), fmt).date()
        except ValueError:
            continue
    logger.warning("Could not parse date, using today", raw=raw)
    return date.today()


# ---------------------------------------------------------------------------
# XML namespace helper
# ---------------------------------------------------------------------------

_NS_RE = re.compile(r"\{[^}]*\}")


def _tag(el: ET.Element) -> str:
    return _NS_RE.sub("", el.tag)


# ---------------------------------------------------------------------------
# Source implementation
# ---------------------------------------------------------------------------

class RetsinformationSource(LegalSource):
    """Fetches recent environmental law documents from retsinformation.dk RSS."""

    name = "retsinformation"
    legal_area = "environmental_law"

    def __init__(
        self,
        rss_url: str = RSS_URL,
        max_documents: int = MAX_DOCUMENTS,
    ) -> None:
        self._rss_url = rss_url
        self._max_documents = max_documents

    async def fetch_new_documents(self) -> list[RawDocument]:
        """Fetch RSS feed and return env-law documents with full text."""
        logger.info("Checking source", source=self.name)
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            entries = await self._fetch_rss_entries(client)
            env_entries = [e for e in entries if _matches_environmental(e["title"] + " " + e.get("summary", ""))]
            logger.info(
                "RSS entries after keyword filter",
                source=self.name,
                total=len(entries),
                matched=len(env_entries),
            )

            docs: list[RawDocument] = []
            for entry in env_entries[: self._max_documents]:
                raw_text = await self._fetch_full_text(client, entry["url"])
                docs.append(
                    RawDocument(
                        title=entry["title"],
                        url=entry["url"],
                        source=self.name,
                        publication_date=entry["pub_date"],
                        legal_area=self.legal_area,
                        raw_text=raw_text,
                    )
                )

        logger.info("Documents fetched", source=self.name, count=len(docs))
        return docs

    async def _fetch_rss_entries(
        self, client: httpx.AsyncClient
    ) -> list[dict[str, object]]:
        try:
            resp = await client.get(self._rss_url, follow_redirects=True)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            logger.error("RSS fetch failed", source=self.name, error=str(exc))
            return []

        return self._parse_rss(resp.text)

    def _parse_rss(self, xml_text: str) -> list[dict[str, object]]:
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as exc:
            logger.error("RSS parse error", source=self.name, error=str(exc))
            return []

        entries: list[dict[str, object]] = []
        # Handle both RSS 2.0 (<item>) and Atom (<entry>)
        for item in root.iter():
            if _tag(item) not in ("item", "entry"):
                continue

            title = ""
            url = ""
            summary = ""
            pub_date: date = date.today()

            for child in item:
                t = _tag(child)
                text = (child.text or "").strip()
                if t == "title":
                    title = text
                elif t in ("link", "id"):
                    url = url or text
                elif t in ("description", "summary", "content"):
                    summary = text
                elif t in ("pubDate", "published", "updated"):
                    pub_date = _parse_date(text)

            if title and url:
                entries.append(
                    {"title": title, "url": url, "summary": summary, "pub_date": pub_date}
                )

        return entries

    async def _fetch_full_text(
        self, client: httpx.AsyncClient, url: str
    ) -> str | None:
        try:
            resp = await client.get(url, follow_redirects=True)
            resp.raise_for_status()
            return _html_to_text(resp.text)
        except httpx.HTTPError as exc:
            logger.warning("Full text fetch failed", url=url, error=str(exc))
            return None
