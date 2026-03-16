"""Ingestion source: Folketing Open Data API (oda.ft.dk).

The Folketing ODA API is an OData REST API exposing parliamentary cases (sager),
documents, and actors. We query the Sag (case/bill) endpoint and filter for
environmental law proposals.

API reference: https://oda.ft.dk/api/
"""

from datetime import date, datetime

import httpx
from loguru import logger

from app.ingestion.base_source import LegalSource, RawDocument

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ODA_BASE = "https://oda.ft.dk/api"
SAG_ENDPOINT = f"{ODA_BASE}/Sag"

ENVIRONMENTAL_KEYWORDS: frozenset[str] = frozenset(
    {"miljø", "natur", "plan", "affald", "klima", "forurening", "vand", "biodiversitet"}
)

# Sag type IDs for law proposals in the ODA model:
# 3 = Lovforslag (law proposal), 31 = Beslutningsforslag
LAW_TYPE_IDS = {3, 31}

PAGE_SIZE = 100
REQUEST_TIMEOUT = 30.0
MAX_PAGES = 5  # cap to avoid very long runs; increase once production scheduling is in place


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _matches_environmental(text: str) -> bool:
    lower = text.lower()
    return any(kw in lower for kw in ENVIRONMENTAL_KEYWORDS)


def _parse_date(raw: str | None) -> date:
    if not raw:
        return date.today()
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw[:19], fmt[:len(fmt)]).date()
        except (ValueError, TypeError):
            continue
    return date.today()


def _build_url(sag_id: int) -> str:
    return f"https://www.ft.dk/samling/aktuelle/sag.aspx?id={sag_id}"


# ---------------------------------------------------------------------------
# Source implementation
# ---------------------------------------------------------------------------

class FolketingSource(LegalSource):
    """Fetches environmental law proposals from the Folketing ODA API."""

    name = "folketing"
    legal_area = "environmental_law"

    def __init__(
        self,
        max_pages: int = MAX_PAGES,
    ) -> None:
        self._max_pages = max_pages

    async def fetch_new_documents(self) -> list[RawDocument]:
        """Query the ODA API and return env-related law proposals."""
        logger.info("Checking source", source=self.name)
        docs: list[RawDocument] = []

        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            for page in range(self._max_pages):
                skip = page * PAGE_SIZE
                items, has_more = await self._fetch_page(client, skip)
                if not items:
                    break

                for item in items:
                    title: str = item.get("titel") or item.get("title") or ""
                    summary: str = item.get("resume") or item.get("resumé") or ""
                    sag_id: int = item.get("id", 0)

                    combined = f"{title} {summary}"
                    if not _matches_environmental(combined):
                        continue

                    pub_date = _parse_date(
                        item.get("opdateringsDato") or item.get("statusdato")
                    )

                    docs.append(
                        RawDocument(
                            title=title or f"Sag #{sag_id}",
                            url=_build_url(sag_id),
                            source=self.name,
                            publication_date=pub_date,
                            legal_area=self.legal_area,
                            raw_text=summary or None,
                        )
                    )

                if not has_more:
                    break

        logger.info("Documents fetched", source=self.name, count=len(docs))
        return docs

    async def _fetch_page(
        self,
        client: httpx.AsyncClient,
        skip: int,
    ) -> tuple[list[dict[str, object]], bool]:
        """Fetch a single page of Sag records.

        Returns:
            Tuple of (items list, has_more flag).
        """
        params: dict[str, object] = {
            "$top": PAGE_SIZE,
            "$skip": skip,
            "$orderby": "opdateringsDato desc",
            "$format": "json",
        }
        # Filter to law proposals only (type 3 = Lovforslag, 31 = Beslutningsforslag)
        type_filter = " or ".join(f"typeid eq {t}" for t in LAW_TYPE_IDS)
        params["$filter"] = f"({type_filter})"

        try:
            resp = await client.get(SAG_ENDPOINT, params=params)
            resp.raise_for_status()
            data = resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            logger.error("ODA API request failed", source=self.name, skip=skip, error=str(exc))
            return [], False

        items: list[dict[str, object]] = data.get("value", [])
        # OData uses @odata.nextLink to signal more pages
        has_more = bool(data.get("@odata.nextLink") or data.get("odata.nextLink"))
        return items, has_more
