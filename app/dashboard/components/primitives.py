"""Shared UI primitives used across the dashboard."""

from dash import html

from app.dashboard.theme import THEME


def badge(label: str, tone: str = "neutral") -> html.Span:
    """Render a small capsule badge."""
    palette = {
        "neutral": (THEME["surface_alt"], THEME["primary"]),
        "accent": (THEME["accent_soft"], THEME["accent"]),
        "primary": (THEME["primary_soft"], THEME["primary"]),
        "danger": (THEME["danger_soft"], THEME["danger"]),
    }
    background, color = palette[tone]
    return html.Span(
        label,
        style={
            "display": "inline-flex",
            "alignItems": "center",
            "padding": "6px 10px",
            "borderRadius": "999px",
            "backgroundColor": background,
            "color": color,
            "fontSize": "11px",
            "fontWeight": "700",
            "letterSpacing": "0.04em",
            "textTransform": "uppercase",
        },
    )


def metric_card(label: str, value: str, note: str) -> html.Div:
    """Render a compact metric card."""
    return html.Div(
        style={
            "flex": "1 1 180px",
            "minWidth": "180px",
            "backgroundColor": THEME["surface"],
            "border": f"1px solid {THEME['border']}",
            "borderRadius": THEME["radius_md"],
            "padding": "18px 18px 16px",
            "boxShadow": "0 8px 24px rgba(22, 51, 47, 0.06)",
        },
        children=[
            html.P(
                label,
                style={
                    "margin": "0 0 10px",
                    "color": THEME["muted"],
                    "fontSize": "12px",
                    "fontWeight": "700",
                    "textTransform": "uppercase",
                    "letterSpacing": "0.06em",
                },
            ),
            html.Div(
                value,
                style={
                    "color": THEME["text"],
                    "fontSize": "30px",
                    "fontWeight": "700",
                    "lineHeight": "1",
                },
            ),
            html.P(
                note,
                style={
                    "margin": "10px 0 0",
                    "color": THEME["muted"],
                    "fontSize": "13px",
                    "lineHeight": "1.4",
                },
            ),
        ],
    )


def info_panel(title: str, body: object, tone: str = "neutral") -> html.Div:
    """Render a bordered information panel."""
    palette = {
        "neutral": (THEME["surface"], THEME["border"], THEME["text"]),
        "accent": (THEME["accent_soft"], THEME["accent"], THEME["text"]),
        "danger": (THEME["danger_soft"], THEME["danger"], THEME["danger"]),
    }
    background, border, heading = palette[tone]
    return html.Div(
        style={
            "backgroundColor": background,
            "border": f"1px solid {border}",
            "borderRadius": THEME["radius_md"],
            "padding": "18px",
        },
        children=[
            html.H4(
                title,
                style={
                    "margin": "0 0 8px",
                    "color": heading,
                    "fontSize": "15px",
                    "fontWeight": "700",
                },
            ),
            html.Div(
                body,
                style={"color": THEME["text"], "fontSize": "14px", "lineHeight": "1.6"},
            ),
        ],
    )
