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

from gestion_dashboard.controllers import database as db  # noqa: E402
from gestion_dashboard.styles.theme import inject_css     # noqa: E402
from gestion_dashboard.views.pages import (               # noqa: E402
    analyses,
    dashboard,
    epargne_page,
    immobilier,
    journal,
    login,
    mensuel,
    parametres,
    previsionnel,
    rapport_pdf,
)


# ─── Session bootstrap ────────────────────────────────────────────────────────

def _init_session_state() -> None:
    today = datetime.date.today()
    if "annee_selectionnee" not in st.session_state:
        st.session_state["annee_selectionnee"] = today.year
    if "mois_selectionne" not in st.session_state:
        st.session_state["mois_selectionne"] = today.month


# ─── Auth guard ───────────────────────────────────────────────────────────────

def _check_auth() -> bool:
    """Return True when a valid user session exists.

    Also ensures the thread-local data directory is pointed at the correct
    user folder on every Streamlit rerun (the OS thread may change between
    reruns, so we must re-apply it each time).
    """
    user = st.session_state.get("user")
    if user is None:
        login.show()
        return False
    # Re-set data dir for this thread/rerun
    db.set_user_data_dir(user.id)
    return True


# ─── Sidebar ──────────────────────────────────────────────────────────────────

def _sidebar() -> None:
    user = st.session_state.get("user")
    with st.sidebar:
        # ── Branding + user info ───────────────────────────────────────────
        display = user.display_name if user else "—"
        initials = "".join(w[0].upper() for w in display.split()[:2]) or "?"
        st.markdown(
            f"""
<div class="sidebar-logo">
  <div class="title">💰 Budget Personnel</div>
  <div class="subtitle">Tableau de bord financier</div>
</div>
<div style="
    display:flex; align-items:center; gap:10px;
    padding:10px 4px 14px; border-bottom:1px solid #ECF0F1;
">
  <div style="
      width:34px; height:34px; border-radius:50%;
      background:#5B4FBE; color:white;
      display:flex; align-items:center; justify-content:center;
      font-size:13px; font-weight:700; flex-shrink:0;
  ">{initials}</div>
  <div>
    <div style="font-size:13px; font-weight:600; color:#2C3E50;">{display}</div>
    <div style="font-size:11px; color:#7F8C8D;">@{user.username if user else ''}</div>
  </div>
</div>
""",
            unsafe_allow_html=True,
        )

        # ── Year selector ──────────────────────────────────────────────────
        annee = st.session_state.get("annee_selectionnee", datetime.date.today().year)
        st.caption(f"Année en cours : **{annee}**")
        annee_new = st.number_input(
            "Changer d'année",
            min_value=2020, max_value=2035,
            value=annee, step=1,
            label_visibility="collapsed",
            key="sidebar_annee",
        )
        if annee_new != annee:
            st.session_state["annee_selectionnee"] = annee_new
            st.rerun()

        st.markdown("---")

        # ── Account section ────────────────────────────────────────────────
        with st.expander("⚙️ Mon compte"):
            _account_panel(user)

        # ── Logout ────────────────────────────────────────────────────────
        if st.button("🚪 Se déconnecter", use_container_width=True):
            _logout()


def _account_panel(user) -> None:
    """Compact change-password form inside the sidebar expander."""
    if user is None:
        return

    st.caption(f"Compte créé le {user.created_at[:10]}")

    with st.form("form_change_pw", clear_on_submit=True):
        old_pw  = st.text_input("Mot de passe actuel",   type="password")
        new_pw  = st.text_input("Nouveau mot de passe",  type="password")
        new_pw2 = st.text_input("Confirmer",             type="password")
        submitted = st.form_submit_button("Modifier le mot de passe")

    if submitted:
        from gestion_dashboard.controllers.auth import change_password
        if new_pw != new_pw2:
            st.error("Les mots de passe ne correspondent pas.")
        else:
            ok, err = change_password(user.id, old_pw, new_pw)
            if ok:
                st.success("Mot de passe modifié ✓")
            else:
                st.error(err)


def _logout() -> None:
    """Clear the session and reset the thread-local data dir."""
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    db.set_user_data_dir(None)
    st.rerun()


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    _init_session_state()
    inject_css()

    if not _check_auth():
        return  # login page rendered by _check_auth; stop here

    pg = st.navigation(
        {
            "🏠 Vue principale": [
                st.Page(dashboard.show,    title="Dashboard",     icon="📊", url_path="dashboard",   default=True),
                st.Page(parametres.show,   title="Paramètres",    icon="⚙️",  url_path="parametres"),
            ],
            "💳 Gestion mensuelle": [
                st.Page(mensuel.show,      title="Vue Mensuelle", icon="📅", url_path="mensuel"),
                st.Page(journal.show,      title="Journal",       icon="📓", url_path="journal"),
            ],
            "💼 Patrimoine": [
                st.Page(epargne_page.show, title="Épargne",       icon="🌱", url_path="epargne"),
                st.Page(immobilier.show,   title="Immobilier",    icon="🏘️",  url_path="immobilier"),
            ],
            "📋 Planification": [
                st.Page(previsionnel.show, title="Prévisionnel",  icon="📦", url_path="previsionnel"),
                st.Page(analyses.show,     title="Analyses",      icon="📈", url_path="analyses"),
            ],
            "📤 Export": [
                st.Page(rapport_pdf.show,  title="Rapport PDF",   icon="📄", url_path="rapport-pdf"),
            ],
        },
        position="sidebar",
    )

    _sidebar()
    pg.run()


if __name__ == "__main__":
    main()
