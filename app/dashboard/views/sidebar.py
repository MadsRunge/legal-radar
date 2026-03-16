"""Filter sidebar and option builders."""

from dash import dcc, html

from app.dashboard.components.primitives import info_panel
from app.dashboard.theme import THEME
from app.dashboard.utils.formatters import pretty_slug


def build_filter_options(
    documents: list[dict[str, object]] | None,
) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    """Build dynamic dropdown options from loaded documents."""
    items = documents or []
    legal_areas = sorted(
        {
            pretty_slug(str(doc.get("legal_area"))) if doc.get("legal_area") else "Ikke angivet": str(doc.get("legal_area", ""))
            for doc in items
        }.items()
    )
    sources = sorted({str(doc.get("source", "")) for doc in items if doc.get("source")})
    document_kinds = sorted(
        {
            pretty_slug(str(doc.get("document_kind"))) if doc.get("document_kind") else "Ikke angivet": str(doc.get("document_kind", ""))
            for doc in items
            if doc.get("document_kind") is not None
        }.items()
    )

    legal_area_options = [{"label": "Alle retsområder", "value": ""}] + [
        {"label": label, "value": value} for label, value in legal_areas
    ]
    source_options = [{"label": "Alle kilder", "value": ""}] + [
        {"label": source, "value": source} for source in sources
    ]
    document_kind_options = [{"label": "Alle dokumenttyper", "value": ""}] + [
        {"label": label, "value": value} for label, value in document_kinds
    ]
    return legal_area_options, source_options, document_kind_options


def build_filter_sidebar() -> html.Aside:
    """Build the persistent filter sidebar."""
    return html.Aside(
        style={
            "flex": "1 1 280px",
            "minWidth": "280px",
            "maxWidth": "320px",
            "backgroundColor": THEME["surface"],
            "border": f"1px solid {THEME['border']}",
            "borderTop": f"5px solid {THEME['primary']}",
            "borderRadius": THEME["radius_lg"],
            "padding": "26px 24px",
            "boxShadow": "0 14px 40px rgba(122, 31, 36, 0.06)",
            "position": "sticky",
            "top": "18px",
        },
        children=[
            html.Div(
                style={"display": "flex", "justifyContent": "space-between", "gap": "12px"},
                children=[
                    html.Div(
                        children=[
                            html.P(
                                "Filtre",
                                style={
                                    "margin": "0 0 6px",
                                    "color": THEME["muted"],
                                    "fontSize": "12px",
                                    "fontWeight": "700",
                                    "textTransform": "uppercase",
                                    "letterSpacing": "0.06em",
                                },
                            ),
                            html.H3(
                                "Arbejdsliste",
                                style={
                                    "margin": "0",
                                    "fontSize": "28px",
                                    "fontFamily": THEME["font_serif"],
                                },
                            ),
                        ]
                    ),
                    html.Button(
                        "Nulstil",
                        id="btn-clear-filters",
                        n_clicks=0,
                        style={
                            "height": "42px",
                            "padding": "0 16px",
                            "borderRadius": THEME["radius_sm"],
                            "border": f"1px solid {THEME['border']}",
                            "backgroundColor": THEME["surface_alt"],
                            "color": THEME["text"],
                            "fontWeight": "700",
                            "cursor": "pointer",
                        },
                    ),
                ],
            ),
            html.Div(
                style={
                    "display": "flex",
                    "flexDirection": "column",
                    "gap": "16px",
                    "marginTop": "20px",
                },
                children=[
                    html.Div(
                        children=[
                            html.Label(
                                "Søg i titel og tekst",
                                style={
                                    "fontSize": "13px",
                                    "fontWeight": "700",
                                    "color": THEME["text"],
                                    "display": "block",
                                    "marginBottom": "4px",
                                },
                            ),
                            dcc.Input(
                                id="filter-search",
                                type="text",
                                placeholder="fx habitat, bekendtgørelse, tilladelse",
                                style={
                                    "width": "100%",
                                    "marginTop": "6px",
                                    "padding": "13px 14px",
                                    "borderRadius": THEME["radius_sm"],
                                    "border": f"1px solid {THEME['border']}",
                                    "backgroundColor": "#fffefe",
                                },
                            ),
                        ]
                    ),
                    html.Div(
                        children=[
                            html.Label(
                                "Retsområde",
                                style={
                                    "fontSize": "13px",
                                    "fontWeight": "700",
                                    "color": THEME["text"],
                                    "display": "block",
                                    "marginBottom": "4px",
                                },
                            ),
                            dcc.Dropdown(
                                id="filter-legal-area",
                                value="",
                                clearable=False,
                                style={"marginTop": "6px"},
                            ),
                        ]
                    ),
                    html.Div(
                        children=[
                            html.Label(
                                "Kilde",
                                style={
                                    "fontSize": "13px",
                                    "fontWeight": "700",
                                    "color": THEME["text"],
                                    "display": "block",
                                    "marginBottom": "4px",
                                },
                            ),
                            dcc.Dropdown(
                                id="filter-source",
                                value="",
                                clearable=False,
                                style={"marginTop": "6px"},
                            ),
                        ]
                    ),
                    html.Div(
                        children=[
                            html.Label(
                                "Dokumenttype",
                                style={
                                    "fontSize": "13px",
                                    "fontWeight": "700",
                                    "color": THEME["text"],
                                    "display": "block",
                                    "marginBottom": "4px",
                                },
                            ),
                            dcc.Dropdown(
                                id="filter-document-kind",
                                value="",
                                clearable=False,
                                style={"marginTop": "6px"},
                            ),
                        ]
                    ),
                    html.Div(
                        children=[
                            html.Label(
                                "Prioritering",
                                style={
                                    "fontSize": "13px",
                                    "fontWeight": "700",
                                    "color": THEME["text"],
                                    "display": "block",
                                    "marginBottom": "4px",
                                },
                            ),
                            dcc.Checklist(
                                id="filter-principial",
                                options=[
                                    {
                                        "label": "Kun principielle / nyskabende sager",
                                        "value": "principial",
                                    }
                                ],
                                value=[],
                                style={"marginTop": "10px", "color": THEME["text"]},
                            ),
                            html.P(
                                "Denne filtrering bliver fuldt værdifuld, når summary-data er koblet på.",
                                style={
                                    "margin": "8px 0 0",
                                    "fontSize": "12px",
                                    "lineHeight": "1.5",
                                    "color": THEME["muted"],
                                },
                            ),
                        ]
                    ),
                    html.Div(
                        children=[
                            html.Label(
                                "Datakvalitet",
                                style={
                                    "fontSize": "13px",
                                    "fontWeight": "700",
                                    "color": THEME["text"],
                                    "display": "block",
                                    "marginBottom": "4px",
                                },
                            ),
                            dcc.Checklist(
                                id="filter-has-text",
                                options=[
                                    {"label": "Kun dokumenter med kildetekst", "value": "has_text"}
                                ],
                                value=[],
                                style={"marginTop": "10px", "color": THEME["text"]},
                            ),
                        ]
                    ),
                    html.Div(
                        style={
                            "display": "flex",
                            "gap": "10px",
                            "flexWrap": "wrap",
                            "paddingTop": "8px",
                        },
                        children=[
                            html.Button(
                                "Opdater data ->",
                                id="btn-refresh",
                                n_clicks=0,
                                style={
                                    "padding": "13px 18px",
                                    "borderRadius": THEME["radius_sm"],
                                    "border": f"1px solid {THEME['primary']}",
                                    "backgroundColor": THEME["primary"],
                                    "color": THEME["surface"],
                                    "fontWeight": "700",
                                    "cursor": "pointer",
                                    "letterSpacing": "0.02em",
                                },
                            ),
                        ],
                    ),
                    info_panel(
                        "Brugerflow",
                        html.Ul(
                            style={"margin": "0", "paddingLeft": "18px"},
                            children=[
                                html.Li("Scan overblikket for dagens bevægelse."),
                                html.Li("Filtrér til det retsområde eller den kilde, du følger."),
                                html.Li("Åbn et dokument og vurder relevans, praksis og tekstuddrag."),
                            ],
                        ),
                    ),
                ],
            ),
        ],
    )
