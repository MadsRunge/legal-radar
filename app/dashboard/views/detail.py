"""Document detail panel rendering."""

from typing import Any

import httpx
from dash import html

from app.dashboard.components.primitives import badge, info_panel, metric_card
from app.dashboard.theme import THEME
from app.dashboard.utils.api import fetch_json
from app.dashboard.utils.formatters import excerpt, format_date, pretty_slug


def build_detail_panel(
    api_base: str,
    selected_document_id: str | None,
    documents: list[dict[str, Any]] | None,
) -> object:
    """Render the analysis panel for the selected document."""
    items = documents or []
    if not items:
        return html.Div()

    if not selected_document_id:
        return info_panel(
            "Vælg et dokument",
            "Når du åbner et dokument fra feedet, vises analysefladen her.",
            tone="accent",
        )

    fallback_document = next(
        (doc for doc in items if str(doc.get("id")) == str(selected_document_id)),
        None,
    )

    try:
        document = fetch_json(api_base, f"/documents/{selected_document_id}")
    except Exception:
        if fallback_document is None:
            return info_panel(
                "Dokument kunne ikke hentes",
                "Det valgte dokument kunne ikke indlæses fra API'et.",
                tone="danger",
            )
        document = fallback_document

    summary: dict[str, Any] | None = None
    summary_state = "pending_endpoint"
    try:
        response = httpx.get(f"{api_base}/documents/{selected_document_id}/summary", timeout=10.0)
        if response.status_code == 200:
            summary = response.json()
            summary_state = "ready"
        elif response.status_code == 404:
            summary_state = "missing_endpoint"
        else:
            summary_state = "error"
    except Exception:
        summary_state = "missing_endpoint"

    if summary:
        summary_panel = html.Div(
            style={"display": "flex", "flexDirection": "column", "gap": "16px"},
            children=[
                info_panel("AI-resumé", summary.get("summary_text", "Ingen resumétekst modtaget.")),
                html.Div(
                    style={"display": "flex", "gap": "16px", "flexWrap": "wrap"},
                    children=[
                        metric_card(
                            "Novelty score",
                            f"{float(summary.get('novelty_score', 0.0)):.0%}",
                            "Hvor markant ændringen vurderes at være",
                        ),
                        metric_card(
                            "Praksisstatus",
                            "Principiel" if summary.get("principial") else "Ikke principiel",
                            "Automatisk markeret af analyse-laget",
                        ),
                    ],
                ),
                info_panel(
                    "Berørte regler og nøgleord",
                    html.Div(
                        style={"display": "flex", "gap": "8px", "flexWrap": "wrap"},
                        children=[
                            *[badge(law, "accent") for law in summary.get("affected_laws", [])],
                            *[badge(keyword, "primary") for keyword in summary.get("keywords", [])],
                        ]
                        or [html.Span("Ingen felter udfyldt endnu.")],
                    ),
                ),
            ],
        )
    else:
        message = (
            "Analysepanelet er klart til `summary_text`, `novelty_score`, `principial`, "
            "`affected_laws` og `keywords`, men summary-endpointet er endnu ikke koblet på."
        )
        if summary_state == "error":
            message = (
                "Dashboardet kunne ikke hente summary-data. Når endpointet er stabilt, "
                "vil AI-resumé og praksismarkering blive vist her."
            )
        summary_panel = info_panel("AI-analyse klar til integration", message, tone="accent")

    meta_badges = [
        badge(pretty_slug(str(document.get("legal_area") or "")), "primary"),
        badge(str(document.get("source", "Ukendt kilde")), "neutral"),
    ]
    if summary and summary.get("principial"):
        meta_badges.append(badge("Principiel udvikling", "accent"))

    preview_block = info_panel(
        "Dokumentuddrag",
        excerpt(str(document.get("raw_text") or ""), limit=1400),
    )

    relevance_block = info_panel(
        "Vurdering",
        html.Div(
            style={"display": "flex", "flexDirection": "column", "gap": "12px"},
            children=[
                html.Div(
                    [
                        html.Strong("Forventet målgruppe: "),
                        html.Span(
                            "jurister og fagpersoner med ansvar for "
                            f"{pretty_slug(str(document.get('legal_area') or '')).lower()}."
                        ),
                    ]
                ),
                html.Div(
                    [
                        html.Strong("Kildetype: "),
                        html.Span(str(document.get("source", "Ukendt kilde"))),
                    ]
                ),
                html.Div(
                    [
                        html.Strong("Næste integrationsskridt: "),
                        html.Span(
                            "koble AI-summary-felterne på, så dette panel kan vise hvad der "
                            "er ændret, hvilke regler der påvirkes, og hvem ændringen er relevant for."
                        ),
                    ]
                ),
            ],
        ),
    )

    return html.Div(
        style={
            "backgroundColor": THEME["surface"],
            "border": f"1px solid {THEME['border']}",
            "borderTop": f"5px solid {THEME['primary']}",
            "borderRadius": THEME["radius_lg"],
            "padding": "28px",
            "boxShadow": "0 16px 44px rgba(122, 31, 36, 0.08)",
            "display": "flex",
            "flexDirection": "column",
            "gap": "20px",
        },
        children=[
            html.Div(
                style={
                    "display": "flex",
                    "justifyContent": "space-between",
                    "alignItems": "flex-start",
                    "gap": "18px",
                    "flexWrap": "wrap",
                },
                children=[
                    html.Div(
                        style={"flex": "1 1 520px"},
                        children=[
                            html.P(
                                "Analyseflade",
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
                                str(document.get("title", "Ukendt dokument")),
                                style={
                                    "margin": "0 0 12px",
                                    "fontSize": "42px",
                                    "lineHeight": "1.05",
                                    "fontFamily": THEME["font_serif"],
                                },
                            ),
                            html.Div(
                                style={"display": "flex", "gap": "8px", "flexWrap": "wrap"},
                                children=meta_badges,
                            ),
                        ],
                    ),
                    html.Div(
                        style={
                            "flex": "0 0 220px",
                            "backgroundColor": THEME["surface_alt"],
                            "borderRadius": THEME["radius_md"],
                            "padding": "18px",
                            "border": f"1px solid {THEME['border']}",
                        },
                        children=[
                            html.P(
                                "Metadata",
                                style={
                                    "margin": "0 0 10px",
                                    "fontSize": "12px",
                                    "fontWeight": "700",
                                    "textTransform": "uppercase",
                                    "letterSpacing": "0.06em",
                                    "color": THEME["muted"],
                                },
                            ),
                            html.P(
                                f"Publiceret: {format_date(str(document.get('publication_date') or ''))}",
                                style={"margin": "0 0 8px", "fontSize": "14px"},
                            ),
                            html.A(
                                "Åbn original kilde",
                                href=str(document.get("url", "#")),
                                target="_blank",
                                rel="noreferrer",
                                style={
                                    "color": THEME["primary"],
                                    "fontWeight": "700",
                                    "textDecoration": "none",
                                },
                            ),
                        ],
                    ),
                ],
            ),
            summary_panel,
            html.Div(
                style={"display": "flex", "gap": "16px", "flexWrap": "wrap"},
                children=[
                    html.Div(style={"flex": "2 1 480px"}, children=[preview_block]),
                    html.Div(style={"flex": "1 1 280px"}, children=[relevance_block]),
                ],
            ),
        ],
    )
