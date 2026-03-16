"""Overview panel rendering."""

from dash import html

from app.dashboard.components.primitives import badge, info_panel, metric_card
from app.dashboard.theme import PAGE_SIZE, THEME
from app.dashboard.utils.formatters import format_date


def build_overview_panel(
    documents: list[dict[str, object]] | None,
    dashboard_state: dict[str, object] | None,
) -> object:
    """Render overview cards and error state."""
    items = documents or []
    state = dashboard_state or {}

    if state.get("status") == "error":
        return info_panel(
            "Data kunne ikke indlæses",
            html.Div(
                [
                    html.P(
                        (
                            "Dashboardet kunne ikke hente dokumenter fra API'et. "
                            "Kontrollér at FastAPI kører, og at dashboardet peger på den rigtige host/port."
                        ),
                        style={"margin": "0 0 8px"},
                    ),
                    html.Code(str(state.get("message", "")), style={"whiteSpace": "pre-wrap"}),
                ]
            ),
            tone="danger",
        )

    sources = sorted({str(doc.get("source", "")) for doc in items if doc.get("source")})
    with_text = sum(1 for doc in items if doc.get("raw_text"))
    latest_date = max((str(doc.get("publication_date") or "") for doc in items), default="")

    return html.Div(
        style={
            "display": "flex",
            "flexDirection": "column",
            "gap": "20px",
            "paddingBottom": "4px",
        },
        children=[
            html.Div(
                style={
                    "display": "flex",
                    "justifyContent": "space-between",
                    "alignItems": "flex-end",
                    "gap": "16px",
                    "flexWrap": "wrap",
                    "paddingBottom": "10px",
                    "borderBottom": f"1px solid {THEME['border']}",
                },
                children=[
                    html.Div(
                        children=[
                            html.P(
                                "Overblik",
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
                                "Seneste monitorering",
                                style={
                                    "margin": "0",
                                    "fontSize": "34px",
                                    "fontFamily": THEME["font_serif"],
                                },
                            ),
                        ]
                    ),
                    html.Div(
                        style={"display": "flex", "gap": "8px", "flexWrap": "wrap"},
                        children=[
                            badge(
                                f"Opdateret {state.get('fetched_at', 'ukendt tidspunkt')}",
                                "neutral",
                            ),
                            badge(
                                f"Viser op til {state.get('page_size', PAGE_SIZE)} dokumenter",
                                "primary",
                            ),
                        ],
                    ),
                ],
            ),
            html.Div(
                style={"display": "flex", "gap": "16px", "flexWrap": "wrap"},
                children=[
                    metric_card("Dokumenter i feed", str(len(items)), "Nyeste dokumenter hentet fra backend"),
                    metric_card("Kilder i spil", str(len(sources)), "Unikke myndigheds- og domskilder"),
                    metric_card("Med kildetekst", str(with_text), "Klar til preview og senere AI-fortolkning"),
                    metric_card(
                        "Nyeste offentliggørelse",
                        format_date(latest_date) if latest_date else "Ingen data",
                        "Seneste dato i den aktuelt indlæste mængde",
                    ),
                ],
            ),
        ],
    )
