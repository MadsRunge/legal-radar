"""Ingestion source: Folketing Open Data API (oda.ft.dk).

The Folketing ODA API is an OData REST API exposing parliamentary cases (sager),
documents, and actors. We query the Sag (case/bill) endpoint and filter for
environmental law proposals.

API reference: https://oda.ft.dk/api/
"""

import re
from datetime import date, datetime, timedelta

import httpx
from loguru import logger

from app.ingestion.base_source import LegalSource, RawDocument
from app.models.document_asset import DocumentAssetCreate

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ODA_BASE = "https://oda.ft.dk/api"
SAG_ENDPOINT = f"{ODA_BASE}/Sag"
SAGDOKUMENT_ENDPOINT = f"{ODA_BASE}/SagDokument"

# Left-boundary patterns — matches Danish compound words starting with the keyword
# (e.g. "miljø" matches "miljøbeskyttelse") but avoids mid/suffix matches
# (e.g. "plan" does NOT match "handlingsplan", "vand" does NOT match "ejendomsvurdering")
_ENVIRONMENTAL_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\b" + kw, re.IGNORECASE)
    for kw in [
        "miljø", "natur", "planlov", "affald", "klima",
        "forurening", "vandmiljø", "havmiljø", "biodiversitet",
    ]
]

# Sag type IDs for law proposals in the ODA model:
# 3 = Lovforslag (law proposal), 31 = Beslutningsforslag
LAW_TYPE_IDS = {3, 31}

PAGE_SIZE = 100
REQUEST_TIMEOUT = httpx.Timeout(connect=10.0, read=20.0, write=5.0, pool=5.0)
MAX_PAGES = 10  # 10 × 100 = 1000 sager; rigeligt til 2 års historik med datofilter
LOOKBACK_YEARS = 2

# Sagdokument rolle-IDs → human-readable relation types
# (ODA rolleid values for Sagdokument; incomplete list — unknown roles → "other")
_ROLLE_MAP: dict[int, str] = {
    1: "proposal_text",
    2: "appendix",
    3: "committee_report",
    4: "amendment",
    5: "note",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _matches_environmental(text: str) -> bool:
    return any(p.search(text) for p in _ENVIRONMENTAL_PATTERNS)


def _parse_date(raw: str | None) -> date:
    if not raw:
        return date.today()
    try:
        return datetime.fromisoformat(raw).date()
    except (ValueError, TypeError):
        return date.today()


def _build_url(sag_id: int) -> str:
    return f"https://www.ft.dk/samling/aktuelle/sag.aspx?id={sag_id}"


# ---------------------------------------------------------------------------
# Source implementation
# ---------------------------------------------------------------------------

class FolketingSource(LegalSource):
    """Fetches environmental law proposals from the Folketing ODA API."""

    name = "folketing"
    legal_area = "environment"

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
                logger.info("ODA page fetched", source=self.name, page=page + 1, items=len(items))
                if not items:
                    break

                for item in items:
                    title: str = item.get("titel") or item.get("title") or ""
                    summary: str = item.get("resume") or item.get("resumé") or ""
                    sag_id: int = item.get("id", 0)

                    combined = f"{title} {summary}"
                    if not _matches_environmental(combined):
                        continue

                    # Defensive date parse — try lowercase first (ODA JSON), then camelCase
                    pub_date = _parse_date(
                        item.get("fremsatdato")
                        or item.get("statusdato")
                        or item.get("opdateringsdato")
                        or item.get("opdateringsDato")
                    )

                    # Fetch related Sagdokument records to build richer raw_text
                    assets = await self._fetch_sag_documents(client, sag_id)
                    doc_titles = [a.title for a in assets if a.title]
                    if doc_titles:
                        raw_text = summary + "\n\n" + "\n".join(doc_titles)
                    else:
                        raw_text = summary or None

                    docs.append(
                        RawDocument(
                            title=title or f"Sag #{sag_id}",
                            url=_build_url(sag_id),
                            source=self.name,
                            publication_date=pub_date,
                            legal_area=self.legal_area,
                            raw_text=raw_text,
                            external_id=sag_id if sag_id else None,
                            source_entity="Sag",
                            source_metadata={
                                "typeid": item.get("typeid"),
                                "statusdato": item.get("statusdato"),
                                "resume": summary,
                            },
                            assets=assets,
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
        cutoff = (date.today() - timedelta(days=LOOKBACK_YEARS * 365)).isoformat()
        type_filter = " or ".join(f"typeid eq {t}" for t in LAW_TYPE_IDS)
        params: dict[str, object] = {
            "$top": PAGE_SIZE,
            "$skip": skip,
            "$filter": f"({type_filter}) and opdateringsdato ge datetime'{cutoff}T00:00:00'",
        }

        try:
            resp = await client.get(SAG_ENDPOINT, params=params)
            resp.raise_for_status()
            data = resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            logger.error("ODA API request failed", source=self.name, skip=skip, error=str(exc))
            return [], False

        items: list[dict[str, object]] = data.get("value", [])
        has_more = (
            bool(data.get("@odata.nextLink") or data.get("odata.nextLink"))
            or len(items) == PAGE_SIZE
        )
        return items, has_more

    async def _fetch_sag_documents(
        self,
        client: httpx.AsyncClient,
        sag_id: int,
    ) -> list[DocumentAssetCreate]:
        """Fetch Sagdokument records for a given Sag and return as assets.

        Args:
            client: Shared httpx async client.
            sag_id: ODA Sag.id to look up.

        Returns:
            List of DocumentAssetCreate objects, one per related document.
        """
        if not sag_id:
            return []

        params: dict[str, object] = {
            "$filter": f"sagid eq {sag_id}",
            "$expand": "Dokument",
        }

        try:
            resp = await client.get(SAGDOKUMENT_ENDPOINT, params=params)
            resp.raise_for_status()
            data = resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning(
                "Sagdokument fetch failed",
                sag_id=sag_id,
                error=str(exc),
            )
            return []

        records = data.get("value", [])
        logger.debug("Sagdokument records fetched", sag_id=sag_id, count=len(records))

        assets: list[DocumentAssetCreate] = []
        for record in records:
            dok = record.get("Dokument") or {}
            rolle_id: int = record.get("rolleid") or 0
            relation_type = _ROLLE_MAP.get(rolle_id, "other")
            dok_id = record.get("dokumentid") or dok.get("id")
            pub_date_raw = dok.get("dato")

            assets.append(
                DocumentAssetCreate(
                    external_id=str(dok_id) if dok_id else None,
                    source_entity="Sagdokument",
                    relation_type=relation_type,
                    title=dok.get("titel") or None,
                    publication_date=_parse_date(pub_date_raw) if pub_date_raw else None,
                )
            )

        return assets
