"""Formatting helpers for dashboard display."""

from datetime import datetime


def format_date(value: str | None) -> str:
    """Format ISO dates for dashboard display."""
    if not value:
        return "Ukendt dato"
    try:
        return datetime.fromisoformat(value).strftime("%d.%m.%Y")
    except ValueError:
        return value


def pretty_slug(value: str | None) -> str:
    """Convert a snake_case label into a human-friendly title."""
    if not value:
        return "Ikke angivet"
    return value.replace("_", " ").strip().title()


def excerpt(text: str | None, limit: int = 220) -> str:
    """Return a trimmed single-line preview of text content."""
    if not text:
        return "Intet tekstuddrag tilgængeligt endnu."
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1].rstrip() + "…"
