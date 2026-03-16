"""HTTP helpers for the dashboard."""

from typing import Any

import httpx


def fetch_json(
    api_base: str,
    path: str,
    params: dict[str, object] | None = None,
) -> dict[str, Any]:
    """Fetch JSON from the backend API and raise on transport or HTTP errors."""
    response = httpx.get(f"{api_base}{path}", params=params, timeout=10.0)
    response.raise_for_status()
    return response.json()
