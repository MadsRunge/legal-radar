"""Dash dashboard entrypoint and callback wiring."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import dash
from dash import ALL, Input, Output, State, callback, ctx, dcc, html

from app.core.config import get_settings
from app.dashboard.theme import PAGE_SIZE, THEME
from app.dashboard.utils.api import fetch_json
from app.dashboard.views.detail import build_detail_panel
from app.dashboard.views.feed import build_documents_feed
from app.dashboard.views.hero import build_hero_section
from app.dashboard.views.overview import build_overview_panel
from app.dashboard.views.sidebar import build_filter_options, build_filter_sidebar

settings = get_settings()
API_BASE = f"http://{settings.API_HOST}:{settings.API_PORT}"

dash_app = dash.Dash(
    __name__,
    title="Legal Radar",
    suppress_callback_exceptions=True,
)

dash_app.layout = html.Div(
    style={
        "minHeight": "100vh",
        "background": "radial-gradient(circle at top left, #efe4cf 0%, #f4efe5 45%, #ebe2d2 100%)",
        "padding": "28px 18px 56px",
        "fontFamily": '"Avenir Next", "Segoe UI", sans-serif',
        "color": THEME["text"],
    },
    children=[
        dcc.Store(id="documents-store"),
        dcc.Store(id="dashboard-state"),
        dcc.Store(id="selected-document-id"),
        html.Div(
            style={
                "maxWidth": "1380px",
                "margin": "0 auto",
                "display": "flex",
                "flexDirection": "column",
                "gap": "22px",
            },
            children=[
                build_hero_section(),
                dcc.Loading(
                    color=THEME["primary"],
                    children=html.Div(id="overview-panel"),
                ),
                html.Div(
                    style={
                        "display": "flex",
                        "gap": "22px",
                        "alignItems": "flex-start",
                        "flexWrap": "wrap",
                    },
                    children=[
                        build_filter_sidebar(),
                        html.Div(
                            style={
                                "flex": "999 1 760px",
                                "minWidth": "320px",
                                "display": "flex",
                                "flexDirection": "column",
                                "gap": "22px",
                            },
                            children=[
                                dcc.Loading(
                                    color=THEME["primary"],
                                    children=html.Div(id="documents-feed"),
                                ),
                                dcc.Loading(
                                    color=THEME["primary"],
                                    children=html.Div(id="detail-panel"),
                                ),
                            ],
                        ),
                    ],
                ),
            ],
        ),
        dcc.Interval(id="auto-refresh", interval=5 * 60 * 1000, n_intervals=0),
    ],
)


@callback(
    Output("documents-store", "data"),
    Output("dashboard-state", "data"),
    Input("btn-refresh", "n_clicks"),
    Input("auto-refresh", "n_intervals"),
    Input("filter-principial", "value"),
)
def load_documents(
    _n_clicks: int,
    _n_intervals: int,
    principial_filter: list[str],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Load the latest documents for the dashboard."""
    params: dict[str, object] = {"page_size": PAGE_SIZE}
    if "principial" in (principial_filter or []):
        params["principial_only"] = True

    fetched_at = datetime.now().strftime("%d.%m.%Y %H:%M")

    try:
        payload = fetch_json(API_BASE, "/documents", params=params)
        items = payload.get("items", [])
        return items, {
            "status": "ready",
            "fetched_at": fetched_at,
            "message": "",
            "page_size": PAGE_SIZE,
            "total": payload.get("total", len(items)),
        }
    except Exception as exc:
        return [], {
            "status": "error",
            "fetched_at": fetched_at,
            "message": str(exc),
            "page_size": PAGE_SIZE,
            "total": 0,
        }


@callback(
    Output("filter-legal-area", "options"),
    Output("filter-source", "options"),
    Output("overview-panel", "children"),
    Input("documents-store", "data"),
    Input("dashboard-state", "data"),
)
def update_filter_options_and_overview(
    documents: list[dict[str, Any]] | None,
    dashboard_state: dict[str, Any] | None,
) -> tuple[list[dict[str, str]], list[dict[str, str]], object]:
    """Update dynamic filter options and overview state."""
    legal_area_options, source_options = build_filter_options(documents)
    overview = build_overview_panel(documents, dashboard_state)
    return legal_area_options, source_options, overview


@callback(
    Output("filter-search", "value"),
    Output("filter-legal-area", "value"),
    Output("filter-source", "value"),
    Output("filter-principial", "value"),
    Output("filter-has-text", "value"),
    Input("btn-clear-filters", "n_clicks"),
    prevent_initial_call=True,
)
def clear_filters(_n_clicks: int) -> tuple[str, str, str, list[str], list[str]]:
    """Reset all dashboard filters."""
    return "", "", "", [], []


@callback(
    Output("selected-document-id", "data"),
    Input("documents-store", "data"),
    Input({"type": "open-document", "document_id": ALL}, "n_clicks"),
    State("selected-document-id", "data"),
)
def select_document(
    documents: list[dict[str, Any]] | None,
    _clicks: list[int] | None,
    current_document_id: str | None,
) -> str | None:
    """Keep a stable selected document and switch when a card button is clicked."""
    items = documents or []
    triggered = ctx.triggered_id

    if isinstance(triggered, dict):
        return str(triggered.get("document_id"))

    document_ids = {str(doc.get("id")) for doc in items if doc.get("id")}
    if current_document_id in document_ids:
        return current_document_id

    if items:
        first_id = items[0].get("id")
        return str(first_id) if first_id else None

    return None


@callback(
    Output("documents-feed", "children"),
    Input("documents-store", "data"),
    Input("dashboard-state", "data"),
    Input("filter-search", "value"),
    Input("filter-legal-area", "value"),
    Input("filter-source", "value"),
    Input("filter-has-text", "value"),
    Input("selected-document-id", "data"),
)
def render_documents_feed(
    documents: list[dict[str, Any]] | None,
    dashboard_state: dict[str, Any] | None,
    search_value: str,
    legal_area: str,
    source: str,
    has_text_only: list[str],
    selected_document_id: str | None,
) -> object:
    """Render the document feed."""
    return build_documents_feed(
        documents,
        dashboard_state,
        search_value,
        legal_area,
        source,
        has_text_only,
        selected_document_id,
    )


@callback(
    Output("detail-panel", "children"),
    Input("selected-document-id", "data"),
    Input("documents-store", "data"),
)
def render_detail_panel(
    selected_document_id: str | None,
    documents: list[dict[str, Any]] | None,
) -> object:
    """Render the selected document detail panel."""
    return build_detail_panel(API_BASE, selected_document_id, documents)


if __name__ == "__main__":
    dash_app.run(
        host=settings.DASH_HOST,
        port=settings.DASH_PORT,
        debug=not settings.is_production,
    )
