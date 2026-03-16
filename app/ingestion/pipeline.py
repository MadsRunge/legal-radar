"""Ingestion pipeline — orchestrates all legal sources.

Responsibilities:
  1. Iterate over all registered LegalSource instances
  2. Fetch new documents from each source
  3. Deduplicate by URL against existing database records
  4. Persist new documents via document_service.create_document()
  5. Trigger AI summarization for each saved document
"""

from dataclasses import dataclass, field

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.ai.summarizer import summarize_document
from app.db.database import AsyncSessionLocal
from app.db.models import DocumentORM
from app.ingestion.base_source import LegalSource, RawDocument
from app.ingestion.domsdatabasen_source import DomsdatabasenSource
from app.ingestion.folketing_source import FolketingSource
from app.ingestion.miljoeklagenavn_source import MiljoeklagenævnSource
from app.ingestion.retsinformation_source import RetsinformationSource
from app.models.document import DocumentCreate
from app.services.document_service import create_document


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

@dataclass
class SourceResult:
    source_name: str
    found: int = 0
    saved: int = 0
    skipped_duplicates: int = 0
    errors: list[str] = field(default_factory=list)


@dataclass
class PipelineResult:
    source_results: list[SourceResult] = field(default_factory=list)

    @property
    def total_found(self) -> int:
        return sum(r.found for r in self.source_results)

    @property
    def total_saved(self) -> int:
        return sum(r.saved for r in self.source_results)

    @property
    def total_errors(self) -> int:
        return sum(len(r.errors) for r in self.source_results)

    def log_summary(self) -> None:
        logger.info(
            "Pipeline complete",
            sources=len(self.source_results),
            found=self.total_found,
            saved=self.total_saved,
            errors=self.total_errors,
        )
        for r in self.source_results:
            logger.info(
                "Source result",
                source=r.source_name,
                found=r.found,
                saved=r.saved,
                duplicates=r.skipped_duplicates,
                errors=len(r.errors),
            )


# ---------------------------------------------------------------------------
# Default source registry
# ---------------------------------------------------------------------------

def default_sources() -> list[LegalSource]:
    """Return the default set of active legal sources."""
    return [
        RetsinformationSource(),
        FolketingSource(),
        DomsdatabasenSource(),
        MiljoeklagenævnSource(),
    ]


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

class IngestionPipeline:
    """Runs ingestion across all sources and persists new documents.

    Args:
        sources: List of LegalSource instances. Defaults to all registered sources.
        session_factory: SQLAlchemy async session factory. Defaults to the app factory.
    """

    def __init__(
        self,
        sources: list[LegalSource] | None = None,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
    ) -> None:
        self._sources = sources if sources is not None else default_sources()
        self._session_factory = session_factory or AsyncSessionLocal

    async def run_once(self) -> PipelineResult:
        """Execute one full ingestion pass across all sources.

        Returns:
            PipelineResult summarising what was found, saved, and any errors.
        """
        result = PipelineResult()

        for source in self._sources:
            source_result = SourceResult(source_name=source.name)
            logger.info("source_checked", source=source.name)

            try:
                docs = await source.fetch_new_documents()
            except Exception as exc:
                msg = f"Source fetch failed: {exc}"
                logger.error(msg, source=source.name)
                source_result.errors.append(msg)
                result.source_results.append(source_result)
                continue

            source_result.found = len(docs)
            logger.info("documents_found", source=source.name, count=len(docs))

            async with self._session_factory() as session:
                for doc in docs:
                    try:
                        saved_count = await self._process_document(
                            session, doc, source_result
                        )
                        source_result.saved += saved_count
                    except Exception as exc:
                        msg = f"Error processing {doc.url}: {exc}"
                        logger.error(msg, source=source.name)
                        source_result.errors.append(msg)

                await session.commit()

            result.source_results.append(source_result)

        result.log_summary()
        return result

    async def _process_document(
        self,
        session: AsyncSession,
        doc: RawDocument,
        source_result: SourceResult,
    ) -> int:
        """Persist a single document and trigger AI analysis.

        Returns:
            1 if saved, 0 if duplicate.
        """
        if await self._is_duplicate(session, doc.url):
            logger.debug("Duplicate skipped", url=doc.url)
            source_result.skipped_duplicates += 1
            return 0

        doc_create = DocumentCreate(
            title=doc.title,
            source=doc.source,
            url=doc.url,  # type: ignore[arg-type]  # Pydantic coerces str → HttpUrl
            publication_date=doc.publication_date,
            legal_area=doc.legal_area,
            raw_text=doc.raw_text,
        )
        saved = await create_document(session, doc_create)
        logger.info("documents_saved", source=doc.source, id=str(saved.id), title=doc.title)

        # Trigger AI summarisation (non-blocking — failures are logged, not raised)
        await self._trigger_ai(saved.raw_text or "", saved.title)

        return 1

    async def _is_duplicate(self, session: AsyncSession, url: str) -> bool:
        """Return True if a document with this URL already exists."""
        result = await session.execute(
            select(DocumentORM.id).where(DocumentORM.url == url).limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def _trigger_ai(self, text: str, title: str) -> None:
        """Call the AI summarizer; log and swallow any errors."""
        try:
            summary = await summarize_document(text, title)
            logger.debug(
                "AI summary generated",
                title=title,
                novelty=summary.novelty_score,
            )
        except Exception as exc:
            logger.warning("AI summarization failed", title=title, error=str(exc))
