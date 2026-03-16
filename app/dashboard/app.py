"""Dash dashboard for Legal Radar.

Fetches data from the FastAPI backend and renders:
- A filterable table of recent legal updates
- Novelty score indicator
- AI summary panel
"""

import httpx
import dash
from dash import Input, Output, callback, dash_table, dcc, html

from app.core.config import get_settings

settings = get_settings()
API_BASE = f"http://{settings.API_HOST}:{settings.API_PORT}"

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

dash_app = dash.Dash(
    __name__,
    title="Legal Radar",
    suppress_callback_exceptions=True,
)

# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------

dash_app.layout = html.Div(
    style={"fontFamily": "Inter, sans-serif", "padding": "24px", "maxWidth": "1200px", "margin": "0 auto"},
    children=[
        html.H1("Legal Radar", style={"color": "#1a1a2e", "marginBottom": "4px"}),
        html.P("AI-powered legal monitoring dashboard", style={"color": "#666", "marginBottom": "24px"}),

        # Filters
        html.Div(
            style={"display": "flex", "gap": "16px", "marginBottom": "24px", "alignItems": "flex-end"},
            children=[
                html.Div([
                    html.Label("Legal Area", style={"fontSize": "12px", "fontWeight": "600", "color": "#555"}),
                    dcc.Dropdown(
                        id="filter-legal-area",
                        options=[
                            {"label": "All areas", "value": ""},
                            {"label": "Environment", "value": "environment"},
                            {"label": "Planning Law", "value": "planning_law"},
                            {"label": "Nature Protection", "value": "nature_protection"},
                            {"label": "Waste Regulation", "value": "waste_regulation"},
                            {"label": "Water Regulation", "value": "water_regulation"},
                        ],
                        value="",
                        clearable=False,
                        style={"width": "220px"},
                    ),
                ]),
                html.Div([
                    html.Label("Case type", style={"fontSize": "12px", "fontWeight": "600", "color": "#555"}),
                    dcc.Checklist(
                        id="filter-principial",
                        options=[{"label": "  Principial cases only", "value": "principial"}],
                        value=[],
                        style={"paddingTop": "8px"},
                    ),
                ]),
                html.Button(
                    "Refresh",
                    id="btn-refresh",
                    n_clicks=0,
                    style={
                        "padding": "8px 20px",
                        "backgroundColor": "#4361ee",
                        "color": "white",
                        "border": "none",
                        "borderRadius": "6px",
                        "cursor": "pointer",
                    },
                ),
            ],
        ),

        # Document table
        html.Div(id="documents-container"),

        # Detail panel (shown when a row is selected)
        html.Div(id="detail-panel", style={"marginTop": "32px"}),

        # Interval auto-refresh (every 5 minutes)
        dcc.Interval(id="auto-refresh", interval=5 * 60 * 1000, n_intervals=0),
    ],
)

# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------


@callback(
    Output("documents-container", "children"),
    Input("btn-refresh", "n_clicks"),
    Input("auto-refresh", "n_intervals"),
    Input("filter-legal-area", "value"),
    Input("filter-principial", "value"),
)
def update_documents_table(
    _n_clicks: int,
    _n_intervals: int,
    legal_area: str,
    principial_filter: list[str],
) -> object:
    """Fetch documents from API and render the table."""
    params: dict[str, object] = {"page_size": 50}
    if legal_area:
        params["legal_area"] = legal_area
    if "principial" in (principial_filter or []):
        params["principial_only"] = True

    try:
        response = httpx.get(f"{API_BASE}/documents", params=params, timeout=10.0)
        response.raise_for_status()
        data = response.json()
        items = data.get("items", [])
    except Exception as exc:
        return html.Div(
            f"Could not load documents: {exc}",
            style={"color": "red", "padding": "16px"},
        )

    if not items:
        return html.P("No documents found.", style={"color": "#888"})

    table_data = [
        {
            "Title": item.get("title", ""),
            "Source": item.get("source", ""),
            "Legal Area": item.get("legal_area", ""),
            "Published": item.get("publication_date", ""),
            "ID": item.get("id", ""),
        }
        for item in items
    ]

    return dash_table.DataTable(
        id="documents-table",
        columns=[
            {"name": "Title", "id": "Title"},
            {"name": "Source", "id": "Source"},
            {"name": "Legal Area", "id": "Legal Area"},
            {"name": "Published", "id": "Published"},
            {"name": "ID", "id": "ID", "hidden": True},
        ],
        data=table_data,
        row_selectable="single",
        style_table={"overflowX": "auto"},
        style_cell={
            "textAlign": "left",
            "padding": "10px 14px",
            "fontFamily": "Inter, sans-serif",
            "fontSize": "14px",
        },
        style_header={
            "backgroundColor": "#f0f2ff",
            "fontWeight": "700",
            "borderBottom": "2px solid #4361ee",
        },
        style_data_conditional=[
            {"if": {"row_index": "odd"}, "backgroundColor": "#fafafa"},
        ],
        page_size=20,
    )


@callback(
    Output("detail-panel", "children"),
    Input("documents-table", "selected_rows"),
    Input("documents-table", "data"),
)
def show_document_detail(
    selected_rows: list[int] | None,
    table_data: list[dict[str, str]] | None,
) -> object:
    """Fetch and display summary + novelty score for the selected document."""
    if not selected_rows or not table_data:
        return html.Div()

    row = table_data[selected_rows[0]]
    doc_id = row.get("ID", "")

    try:
        doc_resp = httpx.get(f"{API_BASE}/documents/{doc_id}", timeout=10.0)
        doc_resp.raise_for_status()
        doc = doc_resp.json()
    except Exception as exc:
        return html.Div(f"Error loading document: {exc}", style={"color": "red"})

    # Try to load summary for novelty score and principial flag
    summary = None
    try:
        sum_resp = httpx.get(f"{API_BASE}/documents/{doc_id}/summary", timeout=10.0)
        if sum_resp.status_code == 200:
            summary = sum_resp.json()
    except Exception:
        pass

    badges = []
    if summary and summary.get("principial"):
        badges.append(
            html.Span(
                "Principial Decision",
                style={
                    "backgroundColor": "#4361ee",
                    "color": "white",
                    "fontSize": "11px",
                    "fontWeight": "700",
                    "padding": "3px 10px",
                    "borderRadius": "12px",
                    "marginRight": "8px",
                    "letterSpacing": "0.5px",
                },
            )
        )

    novelty_section = []
    if summary and summary.get("novelty_score") is not None:
        score = float(summary["novelty_score"])
        novelty_section = [
            html.Div(
                style={"marginBottom": "16px"},
                children=[
                    html.Label(
                        f"Novelty Score: {score:.0%}",
                        style={"fontSize": "12px", "fontWeight": "600", "color": "#555", "marginBottom": "4px", "display": "block"},
                    ),
                    html.Div(
                        style={"backgroundColor": "#e0e0e0", "borderRadius": "4px", "height": "8px", "width": "100%"},
                        children=[
                            html.Div(
                                style={
                                    "backgroundColor": "#4361ee",
                                    "height": "8px",
                                    "borderRadius": "4px",
                                    "width": f"{score * 100:.0f}%",
                                }
                            )
                        ],
                    ),
                ],
            )
        ]

    raw_preview = (
        doc.get("raw_text", "")[:500] + "…"
        if doc.get("raw_text")
        else "No full text available."
    )

    return html.Div(
        style={
            "border": "1px solid #e0e0e0",
            "borderRadius": "8px",
            "padding": "24px",
            "backgroundColor": "#f9f9ff",
        },
        children=[
            html.Div(
                style={"display": "flex", "alignItems": "center", "marginBottom": "8px"},
                children=[html.H3(doc.get("title", ""), style={"margin": "0", "color": "#1a1a2e", "flex": "1"})] + badges,
            ),
            html.P(
                f"Source: {doc.get('source', '')} · Published: {doc.get('publication_date', '')} · Area: {doc.get('legal_area', '')}",
                style={"color": "#666", "fontSize": "13px", "marginBottom": "16px"},
            ),
            *novelty_section,
            html.Hr(),
            html.P(raw_preview, style={"lineHeight": "1.6"}),
        ],
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    dash_app.run(
        host=settings.DASH_HOST,
        port=settings.DASH_PORT,
        debug=not settings.is_production,
    )
