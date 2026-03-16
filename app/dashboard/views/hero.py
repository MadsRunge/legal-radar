"""Top hero section for the dashboard."""

from dash import html

from app.dashboard.components.primitives import badge
from app.dashboard.theme import THEME


def build_hero_section() -> html.Section:
    """Build the dashboard hero banner."""
    return html.Section(
        style={
            "background": (
                "linear-gradient(180deg, rgba(122, 31, 36, 0.06) 0%, rgba(122, 31, 36, 0.0) 100%), "
                "radial-gradient(circle at top left, #fffdf9 0%, #f3ece3 48%, #eadfce 100%)"
            ),
            "borderRadius": THEME["radius_lg"],
            "borderTop": f"6px solid {THEME['primary']}",
            "border": f"1px solid {THEME['border']}",
            "padding": "38px 40px",
            "boxShadow": THEME["shadow"],
            "color": THEME["text"],
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
                                    "marginBottom": "18px",
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
                                    "fontSize": "60px",
                                    "lineHeight": "0.92",
                                    "fontFamily": THEME["font_serif"],
                                    "fontWeight": "700",
                                    "letterSpacing": "-0.03em",
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
                                    "fontSize": "19px",
                                    "lineHeight": "1.8",
                                    "color": THEME["muted"],
                                    "maxWidth": "700px",
                                },
                            ),
                        ],
                    ),
                    html.Div(
                        style={
                            "flex": "0 0 280px",
                            "background": (
                                "linear-gradient(135deg, #7a1f24 0%, #8f2a30 68%, #a83d3a 100%)"
                            ),
                            "border": f"1px solid {THEME['primary']}",
                            "borderRadius": THEME["radius_md"],
                            "padding": "24px",
                            "color": THEME["surface"],
                            "boxShadow": "0 18px 36px rgba(122, 31, 36, 0.18)",
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
                                    "color": "#f3ddd5",
                                },
                            ),
                            html.H3(
                                "Seneste juridiske ændringer",
                                style={
                                    "margin": "0 0 10px",
                                    "fontSize": "30px",
                                    "lineHeight": "1.1",
                                    "fontFamily": THEME["font_serif"],
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
                                    "color": "#f7ebe6",
                                },
                            ),
                        ],
                    ),
                ],
            )
        ],
    )
