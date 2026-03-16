"""Top hero section for the dashboard."""

from dash import html

from app.dashboard.components.primitives import badge
from app.dashboard.theme import THEME


def build_hero_section() -> html.Section:
    """Build the dashboard hero banner."""
    return html.Section(
        style={
            "background": "linear-gradient(135deg, #16332f 0%, #244641 55%, #355c55 100%)",
            "borderRadius": THEME["radius_lg"],
            "padding": "34px",
            "boxShadow": THEME["shadow"],
            "color": THEME["surface"],
        },
        children=[
            html.Div(
                style={
                    "display": "flex",
                    "justifyContent": "space-between",
                    "alignItems": "flex-start",
                    "gap": "20px",
                    "flexWrap": "wrap",
                },
                children=[
                    html.Div(
                        style={"maxWidth": "760px"},
                        children=[
                            html.Div(
                                style={
                                    "display": "flex",
                                    "gap": "10px",
                                    "flexWrap": "wrap",
                                    "marginBottom": "16px",
                                },
                                children=[
                                    badge("Dansk retsmonitorering", "accent"),
                                    badge("AI-resuméer", "primary"),
                                    badge("Principielle afgørelser", "primary"),
                                ],
                            ),
                            html.H1(
                                "Legal Radar",
                                style={
                                    "margin": "0 0 12px",
                                    "fontSize": "52px",
                                    "lineHeight": "0.95",
                                    "fontFamily": '"Iowan Old Style", "Palatino Linotype", serif',
                                    "fontWeight": "700",
                                },
                            ),
                            html.P(
                                (
                                    "Et samlet kontrolrum for nye domme, lovændringer og "
                                    "bekendtgørelser. Filtrér hurtigt, prioriter principielle "
                                    "udviklinger og gå direkte fra fund til vurdering."
                                ),
                                style={
                                    "margin": "0",
                                    "fontSize": "18px",
                                    "lineHeight": "1.7",
                                    "color": "#e5efe8",
                                    "maxWidth": "700px",
                                },
                            ),
                        ],
                    ),
                    html.Div(
                        style={
                            "flex": "0 0 280px",
                            "backgroundColor": "rgba(255, 253, 248, 0.08)",
                            "border": "1px solid rgba(255, 253, 248, 0.18)",
                            "borderRadius": "22px",
                            "padding": "18px",
                        },
                        children=[
                            html.P(
                                "Monitorering",
                                style={
                                    "margin": "0 0 10px",
                                    "fontSize": "12px",
                                    "fontWeight": "700",
                                    "letterSpacing": "0.08em",
                                    "textTransform": "uppercase",
                                    "color": "#d6e6de",
                                },
                            ),
                            html.H3(
                                "Seneste juridiske ændringer",
                                style={
                                    "margin": "0 0 10px",
                                    "fontSize": "24px",
                                    "lineHeight": "1.2",
                                },
                            ),
                            html.P(
                                (
                                    "UI-flowet er nu bygget til produktets formål og viser tydeligt, "
                                    "hvor AI-data kobles på næste gang."
                                ),
                                style={
                                    "margin": "0",
                                    "fontSize": "14px",
                                    "lineHeight": "1.6",
                                    "color": "#d6e6de",
                                },
                            ),
                        ],
                    ),
                ],
            )
        ],
    )
