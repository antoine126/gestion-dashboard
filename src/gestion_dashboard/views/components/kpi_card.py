"""KPI card Streamlit component."""
from __future__ import annotations

import streamlit as st

from gestion_dashboard.styles.theme import kpi_card_html


def render_kpi_card(
    icon: str,
    label: str,
    value: float,
    delta: float | None = None,
    delta_label: str = "",
    format_str: str = "{:,.0f} €",
    delta_neutral: bool = False,
) -> None:
    """
    Render a styled KPI card using custom HTML.

    Parameters
    ----------
    icon : str
        Emoji displayed above the value.
    label : str
        Short descriptive label (displayed in small caps).
    value : float
        Main numeric value to display.
    delta : float, optional
        Trend value; displayed in green (positive) or red (negative).
    delta_label : str
        Suffix appended to the formatted delta string.
    format_str : str
        Python format string applied to ``value`` and ``delta``
        (default: ``"{:,.0f} €"``).
    delta_neutral : bool
        When ``True`` the delta is shown in grey regardless of sign.
    """
    formatted_value = format_str.format(value)
    delta_str = ""
    positive = True
    if delta is not None:
        sign = "+" if delta >= 0 else ""
        delta_str = f"{sign}{format_str.format(delta)}{' ' + delta_label if delta_label else ''}"
        positive = delta >= 0

    html = kpi_card_html(
        icon=icon,
        label=label,
        value=formatted_value,
        delta=delta_str,
        delta_positive=positive,
        delta_neutral=delta_neutral,
    )
    st.markdown(html, unsafe_allow_html=True)
