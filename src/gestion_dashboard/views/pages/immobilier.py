"""Module Patrimoine Immobilier — fiches biens, cashflow, vue consolidée."""
from __future__ import annotations

import streamlit as st

from gestion_dashboard.controllers import calculs
from gestion_dashboard.controllers import database as db
from gestion_dashboard.models.budget import BienImmobilier
from gestion_dashboard.models.enums import TYPES_BIEN_IMMOBILIER
from gestion_dashboard.styles.theme import alert_html, badge_html
from gestion_dashboard.views.components import charts


def _cashflow_color(cf: float) -> str:
    if cf >= 0:
        return "#27AE60"
    if cf > -200:
        return "#F39C12"
    return "#E74C3C"


def show() -> None:
    st.markdown(
        '<div class="page-header"><h1>🏘️ Patrimoine Immobilier</h1>'
        "<p>Fiches biens, analyse de cashflow et vue consolidée.</p></div>",
        unsafe_allow_html=True,
    )

    biens = db.get_biens_immobiliers()

    # ── Add new property ───────────────────────────────────────────────────
    with st.expander("➕ Ajouter un bien immobilier", expanded=len(biens) == 0):
        st.markdown("**Informations générales**")
        c1, c2, c3 = st.columns(3)
        with c1:
            new_nom = st.text_input("Nom / Adresse", key="bi_nom")
            new_type = st.selectbox("Type de bien", TYPES_BIEN_IMMOBILIER, key="bi_type")
        with c2:
            new_vachat = st.number_input("Valeur d'achat (€)", min_value=0.0, step=1000.0, key="bi_vachat")
            new_vactuelle = st.number_input("Valeur actuelle estimée (€)", min_value=0.0, step=1000.0, key="bi_vactuelle")
        with c3:
            new_date_achat = st.text_input("Date d'achat (AAAA-MM)", key="bi_date")
            new_adresse = st.text_input("Adresse (optionnel)", key="bi_adresse")

        st.markdown("**Crédit immobilier**")
        cr1, cr2, cr3, cr4 = st.columns(4)
        with cr1:
            new_cap_init = st.number_input("Capital initial (€)", min_value=0.0, step=1000.0, key="bi_cap_init")
        with cr2:
            new_cap_rest = st.number_input("Capital restant dû (€)", min_value=0.0, step=1000.0, key="bi_cap_rest")
        with cr3:
            new_mensualite = st.number_input("Mensualité crédit (€)", min_value=0.0, step=10.0, key="bi_mensualite")
        with cr4:
            new_taux_cred = st.number_input("Taux crédit (%)", min_value=0.0, max_value=10.0, step=0.05, key="bi_taux_cred")

        st.markdown("**Si bien locatif**")
        lo1, lo2, lo3, lo4 = st.columns(4)
        with lo1:
            new_loyer = st.number_input("Loyer mensuel brut (€)", min_value=0.0, step=10.0, key="bi_loyer")
            new_charges_loc = st.number_input("Charges locataire (€/mois)", min_value=0.0, step=5.0, key="bi_charges_loc")
        with lo2:
            new_charges_prop = st.number_input("Charges propriétaire (€/mois)", min_value=0.0, step=5.0, key="bi_charges_prop")
            new_tf = st.number_input("Taxe foncière (€/an)", min_value=0.0, step=50.0, key="bi_tf")
        with lo3:
            new_assur = st.number_input("Assurance (€/an)", min_value=0.0, step=10.0, key="bi_assur")
            new_frais_gest = st.number_input("Frais de gestion (€/mois)", min_value=0.0, step=5.0, key="bi_frais_gest")
        with lo4:
            new_vacance = st.number_input("Taux vacance locative (%)", min_value=0.0, max_value=100.0, step=1.0, key="bi_vacance")

        if st.button("Ajouter le bien", key="btn_add_bien"):
            if new_nom:
                db.save_bien_immobilier(BienImmobilier(
                    id=0, nom=new_nom, adresse=new_adresse, type_bien=new_type,
                    valeur_achat=new_vachat, valeur_actuelle=new_vactuelle,
                    date_achat=new_date_achat,
                    capital_initial=new_cap_init, capital_restant_du=new_cap_rest,
                    mensualite_credit=new_mensualite, taux_credit=new_taux_cred,
                    duree_restante_mois=0,
                    loyer_mensuel=new_loyer, charges_locataire=new_charges_loc,
                    charges_proprietaire=new_charges_prop, taxe_fonciere=new_tf,
                    assurance_annuelle=new_assur, frais_gestion=new_frais_gest,
                    taux_vacance=new_vacance,
                ))
                st.success(f"✓ {new_nom} ajouté.")
                st.rerun()
            else:
                st.warning("Renseignez au moins le nom du bien.")

    # ── Consolidated view ──────────────────────────────────────────────────
    if biens:
        total_brut = sum(b.valeur_actuelle or b.valeur_achat for b in biens)
        total_dette = sum(b.capital_restant_du for b in biens)
        total_cashflow = sum(calculs.calcul_cashflow_immobilier(b).cashflow_net_mensuel for b in biens)

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("🏠 Patrimoine brut", f"{total_brut:,.0f} €")
        k2.metric("🏦 Dettes restantes", f"{total_dette:,.0f} €")
        k3.metric("✦ Patrimoine net", f"{total_brut - total_dette:,.0f} €")
        k4.metric("💶 Cashflow total/mois", f"{total_cashflow:+,.0f} €", delta_color="normal")

        st.markdown("---")

        # ── Individual property cards ──────────────────────────────────────
        for bien in biens:
            cf = calculs.calcul_cashflow_immobilier(bien)
            is_locatif = bien.loyer_mensuel > 0

            with st.expander(
                f"🏘️ {bien.nom}  —  {bien.type_bien}  "
                f"{'| CF: ' + f'{cf.cashflow_net_mensuel:+,.0f} €/mois' if is_locatif else ''}",
                expanded=True,
            ):
                col_info, col_cf = st.columns([1, 1])

                with col_info:
                    st.markdown(f"""
**Type :** {bien.type_bien}
**Valeur d'achat :** {bien.valeur_achat:,.0f} €
**Valeur actuelle :** {bien.valeur_actuelle:,.0f} €
**Date d'achat :** {bien.date_achat or '—'}
""")
                    if bien.mensualite_credit > 0:
                        st.markdown(f"""
**Capital emprunté :** {bien.capital_initial:,.0f} €
**Capital restant dû :** {bien.capital_restant_du:,.0f} €
**Mensualité crédit :** {bien.mensualite_credit:,.0f} €/mois
**Taux crédit :** {bien.taux_credit:.2f}%
""")

                with col_cf:
                    if is_locatif:
                        cf_color = _cashflow_color(cf.cashflow_net_mensuel)
                        st.markdown(
                            f"<div style='background:{cf_color};color:white;border-radius:10px;"
                            f"padding:12px 18px;text-align:center'>"
                            f"<div style='font-size:12px;opacity:.9'>Cashflow net mensuel</div>"
                            f"<div style='font-size:26px;font-weight:700'>{cf.cashflow_net_mensuel:+,.0f} €</div>"
                            f"<div style='font-size:12px'>{cf.cashflow_net_annuel:+,.0f} €/an</div>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )
                        st.markdown(f"""
**Rentabilité brute :** {cf.rentabilite_brute:.2f}%
**Rentabilité nette :** {cf.rentabilite_nette:.2f}%
""")
                        st.plotly_chart(
                            charts.chart_waterfall_cashflow(cf, bien.nom),
                            width="stretch",
                        )
                    else:
                        st.info("Ce bien n'est pas locatif — aucun cashflow à afficher.")

                # Delete button
                if st.button(f"🗑️ Supprimer {bien.nom}", key=f"del_bi_{bien.id}"):
                    db.delete_bien_immobilier(bien.id)
                    st.rerun()
    else:
        st.markdown(
            alert_html(
                "Aucun bien immobilier enregistré. "
                "Cliquez sur « Ajouter un bien immobilier » pour démarrer.",
                "info",
            ),
            unsafe_allow_html=True,
        )
