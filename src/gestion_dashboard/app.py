"""Streamlit application entry point.

Run with:
    uv run gestion-dashboard
or directly:
    streamlit run src/gestion_dashboard/app.py
"""
from __future__ import annotations

import datetime

import streamlit as st

# Page config must be the very first Streamlit call
st.set_page_config(
    page_title="Budget Personnel",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

from gestion_dashboard.styles.theme import inject_css  # noqa: E402
from gestion_dashboard.views.pages import (  # noqa: E402
    analyses,
    dashboard,
    epargne_page,
    immobilier,
    journal,
    mensuel,
    parametres,
    previsionnel,
)


def _init_session_state() -> None:
    today = datetime.date.today()
    if "annee_selectionnee" not in st.session_state:
        st.session_state["annee_selectionnee"] = today.year
    if "mois_selectionne" not in st.session_state:
        st.session_state["mois_selectionne"] = today.month


def _sidebar() -> None:
    with st.sidebar:
        st.markdown(
            '<div class="sidebar-logo">'
            '<div class="title">💰 Budget Personnel</div>'
            '<div class="subtitle">Tableau de bord financier</div>'
            "</div>",
            unsafe_allow_html=True,
        )

        annee = st.session_state.get("annee_selectionnee", datetime.date.today().year)
        st.caption(f"Année en cours : **{annee}**")

        annee_new = st.number_input(
            "Changer d'année",
            min_value=2020, max_value=2030,
            value=annee, step=1,
            label_visibility="collapsed",
            key="sidebar_annee",
        )
        if annee_new != annee:
            st.session_state["annee_selectionnee"] = annee_new
            st.rerun()

        st.markdown("---")
        # st.caption("Navigation")


def main() -> None:
    _init_session_state()
    inject_css()

    pg = st.navigation(
        {
            "🏠 Vue principale": [
                st.Page(dashboard.show,    title="Dashboard",      icon="📊", url_path="dashboard",    default=True),
                st.Page(parametres.show,   title="Paramètres",     icon="⚙️",  url_path="parametres"),
            ],
            "💳 Gestion mensuelle": [
                st.Page(mensuel.show,      title="Vue Mensuelle",  icon="📅",  url_path="mensuel"),
                st.Page(journal.show,      title="Journal",        icon="📓",  url_path="journal"),
            ],
            "💼 Patrimoine": [
                st.Page(epargne_page.show, title="Épargne",        icon="🌱",  url_path="epargne"),
                st.Page(immobilier.show,   title="Immobilier",     icon="🏘️",  url_path="immobilier"),
            ],
            "📋 Planification": [
                st.Page(previsionnel.show, title="Prévisionnel",   icon="📦",  url_path="previsionnel"),
                st.Page(analyses.show,     title="Analyses",       icon="📈",  url_path="analyses"),
            ],
        },
        position="sidebar"
    )
    
    _sidebar()
    
    pg.run()


if __name__ == "__main__":
    main()
