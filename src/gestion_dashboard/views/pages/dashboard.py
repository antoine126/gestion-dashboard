"""Dashboard annuel — KPIs, graphiques et synthèse."""
from __future__ import annotations

import datetime

import streamlit as st

from gestion_dashboard.controllers import calculs
from gestion_dashboard.controllers import database as db
from gestion_dashboard.models.enums import MOIS
from gestion_dashboard.styles.theme import alert_html, kpi_card_html
from gestion_dashboard.views.components import charts
from gestion_dashboard.views.components.kpi_card import render_kpi_card


def _get_annee() -> int:
    return st.session_state.get("annee_selectionnee", datetime.date.today().year)


def _build_soldes(annee: int):
    params = db.get_parametres()
    charges = db.get_charges_fixes()
    produits = db.get_produits_epargne()
    soldes = []
    for mois in range(1, 13):
        exc = db.get_revenus_exceptionnels(mois, annee)
        bv = db.get_budgets_variables(mois, annee)
        dep = db.get_depenses(mois, annee)
        total_exc = sum(r.montant for r in exc)
        soldes.append(
            calculs.calcul_solde_mensuel(
                salaire=params.salaire_net,
                revenus_exceptionnels=total_exc,
                charges_fixes=charges,
                produits_epargne=produits,
                budgets_variables=bv,
                depenses=dep,
                mois=mois,
                annee=annee,
            )
        )
    return params, charges, produits, soldes


def show() -> None:
    annee = _get_annee()

    st.markdown(
        '<div class="page-header"><h1>📊 Dashboard Annuel</h1>'
        f'<p>Vue consolidée de votre budget {annee}</p></div>',
        unsafe_allow_html=True,
    )

    params, charges, produits, soldes = _build_soldes(annee)
    kpis = calculs.calcul_kpis_annuels(params, soldes, produits)

    # ── Alert if no salary configured ─────────────────────────────────────
    if params.salaire_net == 0:
        st.markdown(
            alert_html(
                "⚙️ Aucun salaire configuré — rendez-vous dans <b>Paramètres</b> pour démarrer.",
                "warning",
            ),
            unsafe_allow_html=True,
        )

    # ── KPI row 1 ──────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">Indicateurs clés</div>', unsafe_allow_html=True)
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        render_kpi_card("💰", "Revenus annuels", kpis.revenus_annuels)
    with c2:
        render_kpi_card("🔒", "Charges fixes", kpis.charges_fixes_annuelles)
    with c3:
        reste = kpis.reste_apres_fixes_epargne
        render_kpi_card(
            "✦", "Reste après fixes",
            reste,
            delta_neutral=True,
        )
    with c4:
        render_kpi_card("📊", "Var. budgétées", kpis.variables_budgetees)
    with c5:
        ecart_var = kpis.variables_reelles - kpis.variables_budgetees
        render_kpi_card(
            "📊", "Var. réelles",
            kpis.variables_reelles,
            delta=ecart_var,
            delta_label="vs budget",
        )
    with c6:
        render_kpi_card("⚖️", "Solde moy./mois", kpis.solde_mensuel_moyen)

    # ── KPI row 2 – épargne ────────────────────────────────────────────────
    st.markdown('<div class="section-header">Épargne</div>', unsafe_allow_html=True)
    e1, e2, e3, _ = st.columns(4)
    with e1:
        render_kpi_card("🌱", "Épargne mensuelle", kpis.epargne_mensuelle)
    with e2:
        render_kpi_card("📈", "Projection annuelle", kpis.projection_epargne_annuelle)
    with e3:
        render_kpi_card("🏦", "Épargne cumulée", kpis.total_epargne_cumulee)

    st.markdown("---")

    # ── Charts ─────────────────────────────────────────────────────────────
    col_l, col_r = st.columns(2)

    with col_l:
        st.markdown('<div class="section-header">Évolution mensuelle</div>', unsafe_allow_html=True)
        if any(s.total_revenus > 0 for s in soldes):
            st.plotly_chart(
                charts.chart_evolution_mensuelle(soldes),
                width="stretch",
            )
        else:
            st.info("Aucune donnée mensuelle pour le moment.")

    with col_r:
        st.markdown('<div class="section-header">Budget Théorique vs Réel</div>', unsafe_allow_html=True)
        total_charges_ann = kpis.charges_fixes_annuelles
        total_epargne_ann = kpis.epargne_mensuelle * 12
        total_var_ann = kpis.variables_reelles
        if kpis.revenus_annuels > 0:
            rep = calculs.calcul_repartition_503020(
                params.salaire_net,
                params.taux_besoins,
                params.taux_loisirs,
                params.taux_epargne,
            )
            reel_dict = {
                "Besoins réels": total_charges_ann,
                "Loisirs réels": total_var_ann,
                "Épargne réelle": total_epargne_ann,
            }
            st.plotly_chart(
                charts.chart_double_piechart(rep, reel_dict),
                width="stretch",
            )
            # Alert if needs exceed theoretical envelope
            if total_charges_ann > rep.besoins * 12 * 1.05:
                st.markdown(
                    alert_html(
                        f"⚠️ Vos charges fixes ({total_charges_ann:,.0f} €) dépassent "
                        f"l'enveloppe Besoins recommandée ({rep.besoins * 12:,.0f} €).",
                        "warning",
                    ),
                    unsafe_allow_html=True,
                )
        else:
            st.info("Configurez votre salaire pour voir ce graphique.")

    st.markdown("---")

    # ── Grouped bar chart ──────────────────────────────────────────────────
    st.markdown('<div class="section-header">Dépenses mensuelles</div>', unsafe_allow_html=True)
    st.plotly_chart(
        charts.chart_barres_groupees(soldes),
        width="stretch",
    )

    # ── Annual category table ──────────────────────────────────────────────
    st.markdown('<div class="section-header">Synthèse annuelle par catégorie</div>', unsafe_allow_html=True)
    categories = db.get_categories()
    all_dep = db.get_all_depenses(annee)
    all_bv = db.get_all_budgets_variables(annee)
    analyses = calculs.calcul_analyse_budget(categories, all_bv, all_dep)

    if analyses:
        import pandas as pd
        df = pd.DataFrame([
            {
                "Catégorie": f"{a.categorie_icone} {a.categorie_nom}",
                "Budgété (€)": round(a.budgete, 2),
                "Réel (€)": round(a.reel, 2),
                "Écart (€)": round(a.ecart, 2),
                "% Consommé": f"{a.pourcentage_consomme:.1f}%",
            }
            for a in analyses
        ])
        st.dataframe(df, width="stretch", hide_index=True)

        col_dl, _ = st.columns([1, 4])
        with col_dl:
            st.download_button(
                "⬇️ Exporter CSV",
                df.to_csv(index=False).encode("utf-8"),
                file_name=f"synthese_annuelle_{annee}.csv",
                mime="text/csv",
            )
    else:
        st.info("Aucune catégorie configurée.")
