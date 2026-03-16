"""AI summarization and novelty scoring for legal documents.

Uses the OpenAI chat completions API (compatible with any OpenAI-spec endpoint).
The concrete implementation is intentionally kept as a stub — swap in your
preferred model / prompt engineering approach.
"""

from dataclasses import dataclass, field

from loguru import logger

from app.core.config import get_settings


@dataclass
class SummarizationResult:
    """Output produced by the summarizer for a single document."""

    summary_text: str
    novelty_score: float  # 0.0–1.0
    principial: bool
    affected_laws: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)


_SYSTEM_PROMPT = """You are a senior legal analyst. Given the text of a legal document,
produce a concise plain-language summary and score its novelty relative to established law.

Respond in JSON with keys:
- summary_text (string)
- novelty_score (float, 0-1)
- principial (bool, true if landmark/principial decision)
- affected_laws (list of law identifiers)
- keywords (list of short keywords)
"""


async def summarize_document(
    text: str,
    title: str = "",
) -> SummarizationResult:
    """Summarize a legal document using the configured AI model.

    This is a stub that returns a placeholder result. Replace the body with
    a real OpenAI (or compatible) API call once the API key is configured.

    Args:
        text: Full document text.
        title: Optional document title for context.

    Returns:
        SummarizationResult populated by the AI model.
    """
    settings = get_settings()

    if not settings.OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY not set — returning stub summary")
        return _stub_result(title)

    # TODO: Replace stub with real API call, e.g.:
    #
    # import openai
    # client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    # response = await client.chat.completions.create(
    #     model="gpt-4o",
    #     response_format={"type": "json_object"},
    #     messages=[
    #         {"role": "system", "content": _SYSTEM_PROMPT},
    #         {"role": "user", "content": f"Title: {title}\n\n{text[:12000]}"},
    #     ],
    # )
    # data = json.loads(response.choices[0].message.content)
    # return SummarizationResult(**data)

    logger.info("AI summarization requested", title=title, text_length=len(text))
    return _stub_result(title)


def _stub_result(title: str) -> SummarizationResult:
    return SummarizationResult(
        summary_text=f"[Stub] Summary for: {title or 'Untitled document'}",
        novelty_score=0.5,
        principial=False,
        affected_laws=[],
        keywords=[],
    )
