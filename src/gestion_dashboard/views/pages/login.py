"""Login and account-registration page.

Displayed full-screen when no user session is active.  On success the
``user`` key is written into ``st.session_state`` and the app reruns into
the authenticated shell.
"""
from __future__ import annotations

import streamlit as st

from gestion_dashboard.controllers import auth, database as db


# ─── CSS injected only for the login screen ───────────────────────────────────

_LOGIN_CSS = """
<style>
/* Hide sidebar on the login screen */
[data-testid="stSidebar"]          { display: none !important; }
[data-testid="collapsedControl"]   { display: none !important; }

/* Extra top-padding so the card sits nicely */
section.main > div.block-container { padding-top: 60px !important; }

/* Login card */
.login-card {
    background: #FFFFFF;
    border: 1px solid #ECF0F1;
    border-radius: 16px;
    padding: 36px 40px 32px;
    box-shadow: 0 4px 24px rgba(91,79,190,.10);
}
.login-logo-icon  { font-size: 40px; text-align: center; }
.login-app-title  { font-size: 22px; font-weight: 700; color: #5B4FBE;
                    text-align: center; margin: 6px 0 2px; }
.login-app-sub    { font-size: 13px; color: #7F8C8D; text-align: center;
                    margin-bottom: 28px; }
.login-divider    { border: none; border-top: 1px solid #ECF0F1; margin: 20px 0; }
</style>
"""


# ─── Public entry point ───────────────────────────────────────────────────────

def show() -> None:
    """Render the login / registration screen."""
    st.markdown(_LOGIN_CSS, unsafe_allow_html=True)

    # Centered narrow column
    _, col, _ = st.columns([1, 1.3, 1])

    with col:
        st.markdown("""
<div class="login-card">
  <div class="login-logo-icon">💰</div>
  <div class="login-app-title">Budget Personnel</div>
  <div class="login-app-sub">Tableau de bord financier multi-utilisateurs</div>
</div>
""", unsafe_allow_html=True)

        st.markdown("")  # breathing room

        if auth.has_any_user():
            tab_login, tab_register = st.tabs(["🔑 Se connecter", "👤 Créer un compte"])
            with tab_login:
                _login_form()
            with tab_register:
                _register_form()
        else:
            # No account yet — show registration prominently
            st.info(
                "**Bienvenue !** Aucun compte n'existe encore. "
                "Créez le premier compte pour commencer."
            )
            _register_form(first_run=True)


# ─── Forms ───────────────────────────────────────────────────────────────────

def _login_form() -> None:
    with st.form("form_login", clear_on_submit=False):
        username = st.text_input("Nom d'utilisateur", placeholder="votre_pseudo")
        password = st.text_input("Mot de passe", type="password", placeholder="••••••")
        submitted = st.form_submit_button(
            "Se connecter", type="primary", use_container_width=True
        )

    if submitted:
        if not username or not password:
            st.error("Remplissez tous les champs.")
            return
        user, err = auth.authenticate(username, password)
        if err:
            st.error(f"❌ {err}")
        else:
            _start_session(user)


def _register_form(first_run: bool = False) -> None:
    label = "Créer le premier compte" if first_run else "Créer mon compte"

    with st.form("form_register", clear_on_submit=True):
        display_name = st.text_input(
            "Nom affiché",
            placeholder="Marie Dupont",
            help="Ce nom apparaîtra dans la barre latérale.",
        )
        username = st.text_input(
            "Nom d'utilisateur",
            placeholder="marie_dupont",
            help="3 à 20 caractères : lettres, chiffres, underscore.",
        )
        col_pw, col_pw2 = st.columns(2)
        with col_pw:
            password = st.text_input(
                "Mot de passe", type="password", placeholder="••••••",
                help="Minimum 6 caractères."
            )
        with col_pw2:
            password2 = st.text_input(
                "Confirmer", type="password", placeholder="••••••"
            )
        submitted = st.form_submit_button(label, type="primary", use_container_width=True)

    if submitted:
        user, err = auth.register_user(
            username=username,
            password=password,
            display_name=display_name,
            password_confirm=password2,
        )
        if err:
            st.error(f"❌ {err}")
        else:
            st.success(f"✅ Compte créé ! Bienvenue, **{user.display_name}** !")
            _start_session(user)


# ─── Session bootstrap ────────────────────────────────────────────────────────

def _start_session(user) -> None:
    """Persist user in session state, set data dir, and rerun into the app."""
    st.session_state["user"] = user
    db.set_user_data_dir(user.id)
    st.rerun()
