"""Document feed rendering helpers."""

from typing import Any

from dash import html

from app.dashboard.components.primitives import badge, info_panel
from app.dashboard.theme import THEME
from app.dashboard.utils.formatters import excerpt, format_date, pretty_slug


def filter_documents(
    documents: list[dict[str, Any]],
    search_value: str,
    legal_area: str,
    source: str,
    has_text_only: list[str],
) -> list[dict[str, Any]]:
    """Apply client-side filters to loaded documents."""
    query = (search_value or "").strip().lower()
    filtered = documents

    if legal_area:
        filtered = [doc for doc in filtered if doc.get("legal_area") == legal_area]

    if source:
        filtered = [doc for doc in filtered if doc.get("source") == source]

    if "has_text" in (has_text_only or []):
        filtered = [doc for doc in filtered if doc.get("raw_text")]

    if query:
        filtered = [
            doc
            for doc in filtered
            if query in " ".join(
                [
                    str(doc.get("title", "")),
                    str(doc.get("source", "")),
                    str(doc.get("legal_area", "")),
                    str(doc.get("raw_text", ""))[:800],
                ]
            ).lower()
        ]

    return filtered


def _render_document_card(document: dict[str, Any], selected: bool) -> html.Div:
    has_text = bool(document.get("raw_text"))
    return html.Div(
        style={
            "backgroundColor": THEME["surface"],
            "border": (
                f"1px solid {THEME['accent']}"
                if selected
                else f"1px solid {THEME['border']}"
            ),
            "borderTop": (
                f"5px solid {THEME['primary']}"
                if selected
                else f"4px solid {THEME['border']}"
            ),
            "borderRadius": THEME["radius_md"],
            "padding": "22px 22px 20px",
            "boxShadow": (
                "0 18px 40px rgba(122, 31, 36, 0.10)"
                if selected
                else "0 10px 24px rgba(122, 31, 36, 0.05)"
            ),
        },
        children=[
            html.Div(
                style={
                    "display": "flex",
                    "justifyContent": "space-between",
                    "gap": "16px",
                    "alignItems": "flex-start",
                    "marginBottom": "14px",
                    "flexWrap": "wrap",
                },
                children=[
                    html.Div(
                        style={"flex": "1 1 360px"},
                        children=[
                            html.H3(
                                str(document.get("title", "Untitled")),
                                style={
                                    "margin": "0 0 8px",
                                    "color": THEME["text"],
                                    "fontSize": "25px",
                                    "lineHeight": "1.2",
                                    "fontFamily": THEME["font_serif"],
                                },
                            ),
                            html.P(
                                f"{document.get('source', 'Ukendt kilde')} · "
                                f"{format_date(str(document.get('publication_date') or ''))}",
                                style={
                                    "margin": "0",
                                    "color": THEME["muted"],
                                    "fontSize": "13px",
                                },
                            ),
                        ],
                    ),
                    html.Button(
                        "Åbn analyse ->",
                        id={"type": "open-document", "document_id": document.get("id")},
                        n_clicks=0,
                        style={
                            "padding": "12px 18px",
                            "borderRadius": THEME["radius_sm"],
                            "border": f"1px solid {THEME['primary']}",
                            "backgroundColor": THEME["primary"] if selected else "transparent",
                            "color": THEME["surface"] if selected else THEME["primary"],
                            "fontWeight": "700",
                            "cursor": "pointer",
                            "minWidth": "140px",
                            "letterSpacing": "0.02em",
                        },
                    ),
                ],
            ),
            html.Div(
                style={
                    "display": "flex",
                    "gap": "8px",
                    "flexWrap": "wrap",
                    "marginBottom": "12px",
                },
                children=[
                    badge(pretty_slug(str(document.get("legal_area") or "")), "primary"),
                    badge(
                        "Kildetekst tilgængelig" if has_text else "Kun metadata",
                        "accent" if has_text else "neutral",
                    ),
                ],
            ),
            html.P(
                excerpt(str(document.get("raw_text") or "")),
                style={
                    "margin": "0",
                    "color": THEME["text"],
                    "fontSize": "15px",
                    "lineHeight": "1.8",
                },
            ),
        ],
    )


def build_documents_feed(
    documents: list[dict[str, Any]] | None,
    dashboard_state: dict[str, Any] | None,
    search_value: str,
    legal_area: str,
    source: str,
    has_text_only: list[str],
    selected_document_id: str | None,
) -> object:
    """Render the main document feed."""
    state = dashboard_state or {}
    items = documents or []

    if state.get("status") == "error":
        return html.Div()

    filtered = filter_documents(items, search_value, legal_area, source, has_text_only)

    header = html.Div(
        style={
            "display": "flex",
            "justifyContent": "space-between",
            "alignItems": "flex-end",
            "gap": "14px",
            "flexWrap": "wrap",
            "paddingBottom": "10px",
            "borderBottom": f"1px solid {THEME['border']}",
        },
        children=[
            html.Div(
                children=[
                    html.P(
                        "Dokumentfeed",
                        style={
                            "margin": "0 0 6px",
                            "color": THEME["muted"],
                            "fontSize": "12px",
                            "fontWeight": "700",
                            "textTransform": "uppercase",
                            "letterSpacing": "0.06em",
                        },
                    ),
                    html.H2(
                        f"{len(filtered)} fund i arbejdslisten",
                        style={
                            "margin": "0",
                            "fontSize": "34px",
                            "fontFamily": THEME["font_serif"],
                        },
                    ),
                ]
            ),
            html.P(
                "Vælg et dokument for at åbne analysepanelet til højre/nedenfor.",
                style={"margin": "0", "color": THEME["muted"], "fontSize": "14px"},
            ),
        ],
    )

    if not filtered:
        return html.Div(
            style={"display": "flex", "flexDirection": "column", "gap": "16px"},
            children=[
                header,
                info_panel(
                    "Ingen dokumenter matcher filtrene",
                    (
                        "Prøv at rydde søgning eller filtre. Dashboardet arbejder bedst som en "
                        "prioriteret arbejdsliste, så tomme resultater bør være tydelige."
                    ),
                    tone="accent",
                ),
            ],
        )

    cards = [
        _render_document_card(document, str(document.get("id")) == str(selected_document_id))
        for document in filtered
    ]

    return html.Div(
        style={"display": "flex", "flexDirection": "column", "gap": "16px"},
        children=[header, *cards],
    )
