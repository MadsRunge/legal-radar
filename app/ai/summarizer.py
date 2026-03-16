"""AI summarization and novelty scoring for legal documents.

Uses DeepSeek (primary, cheaper) or xAI Grok as fallback.
Both expose an OpenAI-compatible chat completions API.
"""

import json
from dataclasses import dataclass, field

from loguru import logger
from openai import AsyncOpenAI

from app.core.config import get_settings


@dataclass
class SummarizationResult:
    """Output produced by the summarizer for a single document."""

    summary_text: str
    novelty_score: float  # 0.0–1.0
    principial: bool
    affected_laws: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)


_SYSTEM_PROMPT = """You are a senior Danish legal analyst. Given the text of a legal document,
produce a concise plain-language summary and score its novelty relative to established law.

Respond in JSON with keys:
- summary_text (string, in Danish)
- novelty_score (float, 0-1)
- principial (bool, true if landmark/principial decision)
- affected_laws (list of law identifiers, e.g. ["Miljøbeskyttelsesloven § 41"])
- keywords (list of short Danish keywords)
"""


async def summarize_document(
    text: str,
    title: str = "",
) -> SummarizationResult:
    """Summarize a legal document using DeepSeek (falls back to Grok, then stub).

    Args:
        text: Full document text.
        title: Optional document title for context.

    Returns:
        SummarizationResult populated by the AI model.
    """
    settings = get_settings()

    if settings.DEEPSEEK_KEY:
        return await _call_openai_compat(
            api_key=settings.DEEPSEEK_KEY,
            base_url="https://api.deepseek.com",
            model="deepseek-chat",
            text=text,
            title=title,
        )

    if settings.GROK_XAI_KEY:
        return await _call_openai_compat(
            api_key=settings.GROK_XAI_KEY,
            base_url="https://api.x.ai/v1",
            model="grok-3",
            text=text,
            title=title,
        )

    logger.warning("No AI key configured (DEEPSEEK_KEY / GROK_XAI_KEY) — returning stub")
    return _stub_result(title)


async def _call_openai_compat(
    api_key: str,
    base_url: str,
    model: str,
    text: str,
    title: str,
) -> SummarizationResult:
    client = AsyncOpenAI(api_key=api_key, base_url=base_url)
    try:
        response = await client.chat.completions.create(
            model=model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": f"Title: {title}\n\n{text[:12000]}"},
            ],
        )
        data = json.loads(response.choices[0].message.content)
        result = SummarizationResult(
            summary_text=data.get("summary_text", ""),
            novelty_score=float(data.get("novelty_score", 0.5)),
            principial=bool(data.get("principial", False)),
            affected_laws=data.get("affected_laws", []),
            keywords=data.get("keywords", []),
        )
        logger.debug("AI summary generated", model=model, title=title, novelty=result.novelty_score)
        return result
    except Exception as exc:
        logger.warning("AI call failed", model=model, title=title, error=str(exc))
        return _stub_result(title)


def _stub_result(title: str) -> SummarizationResult:
    return SummarizationResult(
        summary_text=f"[Stub] Summary for: {title or 'Untitled document'}",
        novelty_score=0.5,
        principial=False,
        affected_laws=[],
        keywords=[],
    )
