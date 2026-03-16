"""Abstract base class for all legal data sources."""

from abc import ABC, abstractmethod
from datetime import date

from pydantic import BaseModel, HttpUrl


class RawDocument(BaseModel):
    """Source-neutral transfer object produced by every LegalSource.

    pipeline.py maps this to DocumentCreate before persisting.
    """

    title: str
    url: str  # plain str — validated by the source, stored as-is
    source: str
    publication_date: date
    legal_area: str = "environmental_law"
    raw_text: str | None = None


class LegalSource(ABC):
    """Abstract base for all ingestion sources.

    To add a new source:
      1. Subclass LegalSource
      2. Set `name` and optionally `legal_area`
      3. Implement `fetch_new_documents()`
      4. Register the instance in pipeline.py
    """

    name: str
    legal_area: str = "environmental_law"

    @abstractmethod
    async def fetch_new_documents(self) -> list[RawDocument]:
        """Fetch documents published since the last check.

        Returns:
            List of RawDocument instances ready for pipeline processing.
            Should return an empty list (not raise) if no new documents exist.
        """
        ...
