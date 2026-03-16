"""Async wrapper around the Firecrawl SDK.

The Firecrawl Python SDK is synchronous, so all calls are dispatched via
`asyncio.to_thread()` to avoid blocking the event loop.
"""

import asyncio
from dataclasses import dataclass, field

from loguru import logger

from app.core.config import get_settings


class FirecrawlError(Exception):
    """Raised when a Firecrawl API call fails."""


@dataclass
class ScrapeResult:
    """Clean text extracted from a single URL."""

    url: str
    markdown: str
    metadata: dict[str, object] = field(default_factory=dict)


class FirecrawlClient:
    """Async Firecrawl client — scrapes URLs to clean markdown."""

    def __init__(self, api_key: str | None = None) -> None:
        resolved_key = api_key or get_settings().FIRECRAWL_API_KEY
        if not resolved_key:
            logger.warning("FIRECRAWL_API_KEY not set — scraping calls will fail")
        self._api_key = resolved_key
        self._app: object = None  # lazy-initialised

    def _get_app(self) -> object:
        """Lazily initialise the FirecrawlApp (avoids import cost at startup)."""
        if self._app is None:
            try:
                from firecrawl import FirecrawlApp  # type: ignore[import-untyped]
            except ImportError as exc:
                raise FirecrawlError(
                    "firecrawl-py is not installed. Run: uv add firecrawl-py"
                ) from exc
            self._app = FirecrawlApp(api_key=self._api_key)
        return self._app

    async def scrape_url(self, url: str) -> ScrapeResult:
        """Scrape a single URL and return clean markdown.

        Args:
            url: Fully qualified URL to scrape.

        Returns:
            ScrapeResult with markdown content.

        Raises:
            FirecrawlError: If the API call fails.
        """
        logger.debug("Firecrawl scraping URL", url=url)
        app = self._get_app()

        def _scrape() -> dict[str, object]:
            return app.scrape_url(url, params={"formats": ["markdown"]})  # type: ignore[union-attr]

        try:
            result: dict[str, object] = await asyncio.to_thread(_scrape)
        except Exception as exc:
            raise FirecrawlError(f"Firecrawl failed for {url}: {exc}") from exc

        markdown = str(result.get("markdown", ""))
        metadata = {k: v for k, v in result.items() if k != "markdown"}
        logger.debug("Firecrawl scrape complete", url=url, chars=len(markdown))
        return ScrapeResult(url=url, markdown=markdown, metadata=metadata)

    async def scrape_urls(
        self,
        urls: list[str],
        max_concurrency: int = 5,
    ) -> list[ScrapeResult]:
        """Scrape multiple URLs with bounded concurrency.

        Args:
            urls: List of URLs to scrape.
            max_concurrency: Maximum simultaneous Firecrawl calls.

        Returns:
            List of ScrapeResult (failed URLs are omitted and logged).
        """
        semaphore = asyncio.Semaphore(max_concurrency)
        results: list[ScrapeResult] = []

        async def _guarded(url: str) -> ScrapeResult | None:
            async with semaphore:
                try:
                    return await self.scrape_url(url)
                except FirecrawlError as exc:
                    logger.error("Firecrawl batch error", url=url, error=str(exc))
                    return None

        gathered = await asyncio.gather(*[_guarded(u) for u in urls])
        results = [r for r in gathered if r is not None]
        logger.info("Firecrawl batch complete", total=len(urls), success=len(results))
        return results
