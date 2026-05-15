"""CSS theme, color constants, and reusable HTML components.

Call ``inject_css()`` once at app startup (inside ``app.py``) to load
all custom styles into the Streamlit session.  The helper functions
``kpi_card_html`` and ``budget_bar_html`` return raw HTML strings that
should be rendered via ``st.markdown(..., unsafe_allow_html=True)``.
"""
from __future__ import annotations

import streamlit as st

# ─── Color palette ────────────────────────────────────────────────────────────

COLORS: dict[str, str] = {
    "primary":        "#5B4FBE",
    "secondary":      "#00B4A6",
    "positive":       "#27AE60",
    "negative":       "#E74C3C",
    "warning":        "#F39C12",
    "bg_main":        "#F8F9FA",
    "bg_card":        "#FFFFFF",
    "text_primary":   "#2C3E50",
    "text_secondary": "#7F8C8D",
    "border":         "#ECF0F1",
}

CHART_PALETTE: list[str] = [
    "#5B4FBE", "#00B4A6", "#27AE60", "#E67E22",
    "#9B59B6", "#1ABC9C", "#3498DB", "#E74C3C",
    "#95A5A6", "#F39C12", "#BDC3C7", "#2C3E50",
]

# ─── Global CSS ───────────────────────────────────────────────────────────────

_CSS = """
<style>
/* ── Global ─────────────────────────────────────────── */
[data-testid="stAppViewContainer"] { background-color: #F8F9FA; }
[data-testid="stSidebar"] {
    background-color: #FFFFFF;
    border-right: 1px solid #ECF0F1;
}
h1, h2, h3 { color: #2C3E50; }

/* ── KPI cards ───────────────────────────────────────── */
.kpi-card {
    background: #FFFFFF;
    border-radius: 12px;
    padding: 18px 20px;
    border: 1px solid #ECF0F1;
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    height: 100%;
    transition: box-shadow .2s;
    margin-bottom: 8px;
}
.kpi-card:hover { box-shadow: 0 4px 16px rgba(91,79,190,.12); }
.kpi-icon  { font-size: 22px; margin-bottom: 6px; }
.kpi-label {
    font-size: 12px;
    color: #7F8C8D;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: .6px;
    margin-bottom: 6px;
}
.kpi-value {
    font-size: 26px;
    font-weight: 700;
    color: #2C3E50;
    font-variant-numeric: tabular-nums;
    margin-bottom: 4px;
}
.kpi-delta { font-size: 13px; font-weight: 500; }
.kpi-delta.positive { color: #27AE60; }
.kpi-delta.negative { color: #E74C3C; }
.kpi-delta.neutral  { color: #7F8C8D; }

/* ── Section headers ─────────────────────────────────── */
.section-header {
    font-size: 18px;
    font-weight: 700;
    color: #2C3E50;
    margin: 20px 0 10px;
    padding-bottom: 6px;
    border-bottom: 2px solid #5B4FBE;
}

/* ── Status badges ───────────────────────────────────── */
.badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: .3px;
}
.badge-green  { background: #D5F5E3; color: #1E8449; }
.badge-orange { background: #FDEBD0; color: #B7770D; }
.badge-red    { background: #FADBD8; color: #C0392B; }
.badge-gray   { background: #F2F3F4; color: #626567; }
.badge-blue   { background: #D6EAF8; color: #1A5276; }
.badge-purple { background: #E8DAEF; color: #6C3483; }

/* ── Budget progress bars ────────────────────────────── */
.budget-bar-container {
    background: #ECF0F1;
    border-radius: 6px;
    height: 8px;
    margin: 5px 0;
    overflow: hidden;
}
.budget-bar-fill        { height: 8px; border-radius: 6px; transition: width .4s ease; }
.budget-bar-green       { background: #27AE60; }
.budget-bar-orange      { background: #F39C12; }
.budget-bar-red         { background: #E74C3C; }

/* ── Alert boxes ─────────────────────────────────────── */
.alert-warning {
    background: #FFF9E6;
    border-left: 4px solid #F39C12;
    padding: 10px 14px;
    border-radius: 0 8px 8px 0;
    color: #856404;
    margin: 6px 0;
    font-size: 14px;
}
.alert-danger {
    background: #FEF0F0;
    border-left: 4px solid #E74C3C;
    padding: 10px 14px;
    border-radius: 0 8px 8px 0;
    color: #842029;
    margin: 6px 0;
    font-size: 14px;
}
.alert-success {
    background: #F0FDF4;
    border-left: 4px solid #27AE60;
    padding: 10px 14px;
    border-radius: 0 8px 8px 0;
    color: #166534;
    margin: 6px 0;
    font-size: 14px;
}
.alert-info {
    background: #EBF5FB;
    border-left: 4px solid #5B4FBE;
    padding: 10px 14px;
    border-radius: 0 8px 8px 0;
    color: #1A5276;
    margin: 6px 0;
    font-size: 14px;
}

/* ── Page header ─────────────────────────────────────── */
.page-header h1 { font-size: 26px; font-weight: 700; margin-bottom: 2px; }
.page-header p  { color: #7F8C8D; font-size: 14px; margin-top: 0; }

/* ── Metric tweaks ───────────────────────────────────── */
[data-testid="metric-container"] {
    background: #FFFFFF;
    border: 1px solid #ECF0F1;
    border-radius: 10px;
    padding: 12px 16px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
}

/* ── Streamlit table ─────────────────────────────────── */
[data-testid="stDataFrame"] { border-radius: 8px; overflow: hidden; }

/* ── Form ────────────────────────────────────────────── */
[data-testid="stButton"] > button {
    border-radius: 8px;
    font-weight: 600;
}

/* ── Sidebar logo area ───────────────────────────────── */
.sidebar-logo {
    text-align: center;
    padding: 16px 0 8px;
    border-bottom: 1px solid #ECF0F1;
    margin-bottom: 12px;
}
.sidebar-logo .title {
    font-size: 18px;
    font-weight: 700;
    color: #5B4FBE;
}
.sidebar-logo .subtitle {
    font-size: 12px;
    color: #7F8C8D;
}
</style>
"""


def inject_css() -> None:
    """Inject global CSS into the running Streamlit session."""
    st.markdown(_CSS, unsafe_allow_html=True)


# ─── HTML component helpers ───────────────────────────────────────────────────

def kpi_card_html(
    icon: str,
    label: str,
    value: str,
    delta: str = "",
    delta_positive: bool = True,
    delta_neutral: bool = False,
) -> str:
    """Return the HTML markup for a KPI card."""
    if delta:
        cls = "neutral" if delta_neutral else ("positive" if delta_positive else "negative")
        delta_html = f'<div class="kpi-delta {cls}">{delta}</div>'
    else:
        delta_html = ""
    return f"""
<div class="kpi-card">
  <div class="kpi-icon">{icon}</div>
  <div class="kpi-label">{label}</div>
  <div class="kpi-value">{value}</div>
  {delta_html}
</div>"""


def budget_bar_html(
    label: str,
    value: float,
    budget: float,
    icone: str = "",
) -> str:
    """Return the HTML markup for a budget progress bar row."""
    if budget > 0:
        pct = value / budget * 100
    else:
        pct = 100.0 if value > 0 else 0.0

    if pct < 80:
        bar_cls, badge_cls, status = "budget-bar-green", "badge-green", "✓ Sous budget"
    elif pct <= 100:
        bar_cls, badge_cls, status = "budget-bar-orange", "badge-orange", "⚠ Attention"
    else:
        bar_cls, badge_cls, status = "budget-bar-red", "badge-red", "✗ Dépassement"

    bar_width = min(pct, 100)
    return f"""
<div style="margin:10px 0;">
  <div style="display:flex;justify-content:space-between;margin-bottom:3px;">
    <span style="font-size:14px;color:#2C3E50;font-weight:500;">{icone} {label}</span>
    <span style="font-size:13px;color:#7F8C8D;">{value:,.0f} € / {budget:,.0f} €</span>
  </div>
  <div class="budget-bar-container">
    <div class="budget-bar-fill {bar_cls}" style="width:{bar_width:.1f}%;"></div>
  </div>
  <div style="display:flex;justify-content:space-between;margin-top:2px;">
    <span class="badge {badge_cls}">{status}</span>
    <span style="font-size:11px;color:#7F8C8D;">{pct:.1f}%</span>
  </div>
</div>"""


def badge_html(text: str, color: str = "gray") -> str:
    """Return a coloured badge span."""
    cls_map = {
        "green": "badge-green", "orange": "badge-orange",
        "red": "badge-red", "gray": "badge-gray",
        "blue": "badge-blue", "purple": "badge-purple",
    }
    cls = cls_map.get(color, "badge-gray")
    return f'<span class="badge {cls}">{text}</span>'


def alert_html(message: str, kind: str = "info") -> str:
    """Return an alert box HTML string."""
    cls_map = {"info": "alert-info", "warning": "alert-warning",
               "danger": "alert-danger", "success": "alert-success"}
    return f'<div class="{cls_map.get(kind, "alert-info")}">{message}</div>'
