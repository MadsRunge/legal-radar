"""Ingestion source: Retsinformation (api.retsinformation.dk).

Uses the Retsinformation harvest service to get daily document updates.

Strategy:
  1. Query the harvest API for each of the last N days
  2. For each document, fetch the ELI XML and extract the title
  3. Filter by environmental keywords
  4. Fetch the full HTML page and strip to plain text
  5. Return as RawDocument list

API reference: https://api.retsinformation.dk
"""

import asyncio
import xml.etree.ElementTree as ET
from datetime import date, timedelta
from html.parser import HTMLParser

import httpx
from loguru import logger

from app.ingestion.base_source import LegalSource, RawDocument

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

HARVEST_URL = "https://api.retsinformation.dk/v1/Documents"
ELI_BASE = "https://www.retsinformation.dk/eli/accn"

ENVIRONMENTAL_KEYWORDS: frozenset[str] = frozenset(
    {"miljø", "natur", "planlov", "affald", "vand", "klima", "forurening", "biodiversitet"}
)

REQUEST_TIMEOUT = httpx.Timeout(connect=5.0, read=15.0, write=5.0, pool=5.0)
MAX_DOCUMENTS = 50
LOOKBACK_DAYS = 10  # harvest API maximum; rate limit: 1 req/10 sec → ~110 sec per full run
HARVEST_RATE_LIMIT_SLEEP = 11.0  # seconds between harvest API calls


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
            if len(stripped) > 1:
                self._parts.append(stripped)

    @property
    def text(self) -> str:
        return "\n".join(self._parts)


def _html_to_text(html: str) -> str:
    parser = _TextExtractor()
    parser.feed(html)
    return parser.text


# ---------------------------------------------------------------------------
# XML helpers
# ---------------------------------------------------------------------------

def _extract_xml_title(xml_text: str) -> str | None:
    """Extract DocumentTitle from ELI XML."""
    try:
        root = ET.fromstring(xml_text)
        for elem in root.iter():
            if elem.tag.endswith("DocumentTitle") and elem.text:
                return elem.text.strip()
    except ET.ParseError:
        pass
    return None


def _extract_xml_date(xml_text: str) -> date | None:
    """Extract DiesSigni (signing date) from ELI XML."""
    try:
        root = ET.fromstring(xml_text)
        for elem in root.iter():
            if elem.tag.endswith("DiesSigni") and elem.text:
                return date.fromisoformat(elem.text.strip())
    except (ET.ParseError, ValueError):
        pass
    return None


# ---------------------------------------------------------------------------
# Keyword matching
# ---------------------------------------------------------------------------

def _matches_environmental(text: str) -> bool:
    lower = text.lower()
    return any(kw in lower for kw in ENVIRONMENTAL_KEYWORDS)


# ---------------------------------------------------------------------------
# Source implementation
# ---------------------------------------------------------------------------

class RetsinformationSource(LegalSource):
    """Fetches recent environmental law documents from api.retsinformation.dk."""

    name = "retsinformation"
    legal_area = "environment"

    def __init__(
        self,
        lookback_days: int = LOOKBACK_DAYS,
        max_documents: int = MAX_DOCUMENTS,
        rate_limit_sleep: float = HARVEST_RATE_LIMIT_SLEEP,
    ) -> None:
        self._lookback_days = lookback_days
        self._max_documents = max_documents
        self._rate_limit_sleep = rate_limit_sleep

    async def fetch_new_documents(self) -> list[RawDocument]:
        logger.info("Checking source", source=self.name)
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            doc_refs = await self._fetch_recent_refs(client)
            logger.info("Harvest refs fetched", source=self.name, count=len(doc_refs))

            docs: list[RawDocument] = []
            # Over-fetch to account for keyword filter attrition
            for ref in doc_refs[: self._max_documents * 4]:
                if len(docs) >= self._max_documents:
                    break
                doc = await self._process_ref(client, ref)
                if doc:
                    docs.append(doc)

        logger.info("Documents fetched", source=self.name, count=len(docs))
        return docs

    async def _fetch_recent_refs(self, client: httpx.AsyncClient) -> list[dict]:
        """Query harvest API for each of the last N days."""
        refs: list[dict] = []
        today = date.today()
        for i, days_ago in enumerate(range(self._lookback_days)):
            if i > 0:
                await asyncio.sleep(self._rate_limit_sleep)
            d = (today - timedelta(days=days_ago)).isoformat()
            try:
                resp = await client.get(HARVEST_URL, params={"date": d})
                resp.raise_for_status()
                day_refs = resp.json()
                if day_refs:
                    logger.debug("Harvest results", source=self.name, date=d, count=len(day_refs))
                    refs.extend(day_refs)
            except httpx.HTTPError as exc:
                logger.warning("Harvest API failed", source=self.name, date=d, error=str(exc))
        return refs

    async def _process_ref(
        self, client: httpx.AsyncClient, ref: dict
    ) -> RawDocument | None:
        """Fetch XML metadata, keyword-filter, then fetch full HTML text."""
        accession: str = ref.get("accessionsnummer", "")
        change_date_str: str = ref.get("changeDate", "")
        xml_href: str = ref.get("href", "")

        if not accession or not xml_href:
            return None

        try:
            xml_resp = await client.get(xml_href, follow_redirects=True)
            xml_resp.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("XML fetch failed", source=self.name, accession=accession, error=str(exc))
            return None

        title = _extract_xml_title(xml_resp.text) or f"Dokument {accession}"
        if not _matches_environmental(title):
            return None

        pub_date = _extract_xml_date(xml_resp.text) or _parse_date(change_date_str)
        html_url = f"{ELI_BASE}/{accession}"

        raw_text: str | None = None
        try:
            html_resp = await client.get(html_url, follow_redirects=True)
            html_resp.raise_for_status()
            raw_text = _html_to_text(html_resp.text)
        except httpx.HTTPError as exc:
            logger.warning("HTML fetch failed", source=self.name, url=html_url, error=str(exc))

        return RawDocument(
            title=title,
            url=html_url,
            source=self.name,
            publication_date=pub_date,
            legal_area=self.legal_area,
            raw_text=raw_text,
        )


def _parse_date(raw: str) -> date:
    try:
        return date.fromisoformat(raw)
    except (ValueError, TypeError):
        return date.today()
