"""Module Analyses — comparaisons mois/catégorie, heatmap, tendances."""
from __future__ import annotations

import datetime

import pandas as pd
import streamlit as st

from gestion_dashboard.controllers import calculs
from gestion_dashboard.controllers import database as db
from gestion_dashboard.models.enums import MOIS, MOIS_COURT
from gestion_dashboard.styles.theme import alert_html
from gestion_dashboard.views.components import charts


def _get_annee() -> int:
    return st.session_state.get("annee_selectionnee", datetime.date.today().year)


def show() -> None:
    annee = _get_annee()

    st.markdown(
        '<div class="page-header"><h1>📈 Analyses Comparatives</h1>'
        f"<p>Analyse approfondie de votre budget {annee}.</p></div>",
        unsafe_allow_html=True,
    )

    # ── Load full year data ────────────────────────────────────────────────
    params = db.get_parametres()
    charges = db.get_charges_fixes()
    produits = db.get_produits_epargne()
    categories = db.get_categories()
    all_dep = db.get_all_depenses(annee)
    all_bv = db.get_all_budgets_variables(annee)

    soldes = []
    for mois in range(1, 13):
        exc = db.get_revenus_exceptionnels(mois, annee)
        bv_m = [b for b in all_bv if b.mois == mois]
        dep_m = [d for d in all_dep if d.mois == mois]
        total_exc = sum(r.montant for r in exc)
        soldes.append(
            calculs.calcul_solde_mensuel(
                salaire=params.salaire_net,
                revenus_exceptionnels=total_exc,
                charges_fixes=charges,
                produits_epargne=produits,
                budgets_variables=bv_m,
                depenses=dep_m,
                mois=mois,
                annee=annee,
            )
        )

    tab1, tab2, tab3 = st.tabs(["📊 Évolution mensuelle", "🌡️ Heatmap", "📉 Tendances"])

    # ══ Tab 1 — Monthly evolution ════════════════════════════════════════════
    with tab1:
        st.markdown('<div class="section-header">Dépenses mensuelles — Budgété vs Réel</div>', unsafe_allow_html=True)
        st.plotly_chart(charts.chart_barres_groupees(soldes), width="stretch")

        st.markdown('<div class="section-header">Évolution des soldes</div>', unsafe_allow_html=True)
        st.plotly_chart(charts.chart_evolution_mensuelle(soldes), width="stretch")

        # 12-month × categories table
        st.markdown('<div class="section-header">Tableau annuel par catégorie</div>', unsafe_allow_html=True)
        if categories:
            rows = []
            for cat in categories:
                row = {"Catégorie": f"{cat.icone} {cat.nom}"}
                for mois in range(1, 13):
                    dep_m = [d for d in all_dep if d.mois == mois and d.categorie_id == cat.id]
                    row[MOIS_COURT[mois - 1]] = round(sum(d.montant for d in dep_m), 0)
                row["Total"] = sum(row[m] for m in MOIS_COURT)
                rows.append(row)

            df_annual = pd.DataFrame(rows)
            st.dataframe(
                df_annual,
                width="stretch",
                hide_index=True,
                column_config={
                    m: st.column_config.NumberColumn(format="%.0f €") for m in MOIS_COURT + ["Total"]
                },
            )

            col_dl, _ = st.columns([1, 4])
            with col_dl:
                st.download_button(
                    "⬇️ Exporter CSV",
                    df_annual.to_csv(index=False).encode("utf-8"),
                    file_name=f"analyse_annuelle_{annee}.csv",
                    mime="text/csv",
                )
        else:
            st.info("Aucune catégorie configurée.")

    # ══ Tab 2 — Heatmap ══════════════════════════════════════════════════════
    with tab2:
        st.markdown('<div class="section-header">Heatmap des dépenses (€/mois)</div>', unsafe_allow_html=True)
        st.caption("Chaque cellule = montant total dépensé pour une catégorie un mois donné.")

        if categories and all_dep:
            cat_labels = [f"{c.icone} {c.nom}" for c in categories]
            matrix = []
            for cat in categories:
                row_vals = []
                for mois in range(1, 13):
                    total = sum(d.montant for d in all_dep if d.mois == mois and d.categorie_id == cat.id)
                    row_vals.append(total)
                matrix.append(row_vals)

            st.plotly_chart(
                charts.chart_heatmap(cat_labels, MOIS_COURT, matrix),
                width="stretch",
            )
        else:
            st.info("Aucune donnée disponible pour construire la heatmap.")

        # Category deep-dive
        if categories:
            st.markdown('<div class="section-header">Évolution d\'une catégorie</div>', unsafe_allow_html=True)
            selected_cat = st.selectbox(
                "Choisir une catégorie",
                options=categories,
                format_func=lambda c: f"{c.icone} {c.nom}",
            )
            if selected_cat:
                import plotly.graph_objects as go
                from gestion_dashboard.styles.theme import COLORS

                monthly_vals = [
                    sum(d.montant for d in all_dep if d.mois == m and d.categorie_id == selected_cat.id)
                    for m in range(1, 13)
                ]
                budget_vals = [
                    next((b.montant_budgete for b in all_bv if b.mois == m and b.categorie_id == selected_cat.id), 0.0)
                    for m in range(1, 13)
                ]
                fig_cat = go.Figure()
                fig_cat.add_trace(go.Bar(
                    x=MOIS_COURT, y=budget_vals, name="Budgété",
                    marker_color=COLORS["primary"], opacity=0.5,
                ))
                fig_cat.add_trace(go.Bar(
                    x=MOIS_COURT, y=monthly_vals, name="Réel",
                    marker_color=selected_cat.couleur,
                ))
                fig_cat.update_layout(
                    barmode="group",
                    title=f"{selected_cat.icone} {selected_cat.nom} — Budgété vs Réel par mois",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(family="Inter, sans-serif"),
                    xaxis=dict(gridcolor="#ECF0F1"),
                    yaxis=dict(gridcolor="#ECF0F1", title="€"),
                )
                st.plotly_chart(fig_cat, width="stretch")

    # ══ Tab 3 — Trends ═══════════════════════════════════════════════════════
    with tab3:
        st.markdown('<div class="section-header">Analyse de tendances</div>', unsafe_allow_html=True)

        mois_actuel = datetime.date.today().month if annee == datetime.date.today().year else 12
        soldes_actifs = soldes[:mois_actuel]

        if not soldes_actifs:
            st.info("Aucune donnée disponible.")
        else:
            # 50/30/20 comparison
            st.markdown("#### Répartition Théorique vs Réelle")
            if params.salaire_net > 0:
                rep = calculs.calcul_repartition_503020(
                    params.salaire_net,
                    params.taux_besoins,
                    params.taux_loisirs,
                    params.taux_epargne,
                )
                n_mois = len(soldes_actifs)
                total_charges = sum(s.total_charges_fixes for s in soldes_actifs)
                total_epargne = sum(s.total_epargne for s in soldes_actifs)
                total_var = sum(s.total_variables_reel for s in soldes_actifs)

                reel_dict = {
                    "Besoins réels": total_charges,
                    "Loisirs réels": total_var,
                    "Épargne réelle": total_epargne,
                }
                # Scale theoretical to same number of months
                from gestion_dashboard.models.budget import Repartition503020
                rep_scaled = Repartition503020(
                    besoins=rep.besoins * n_mois,
                    loisirs=rep.loisirs * n_mois,
                    epargne=rep.epargne * n_mois,
                    salaire=rep.salaire * n_mois,
                    taux_besoins=rep.taux_besoins,
                    taux_loisirs=rep.taux_loisirs,
                    taux_epargne=rep.taux_epargne,
                )
                st.plotly_chart(
                    charts.chart_double_piechart(rep_scaled, reel_dict),
                    width="stretch",
                )

            # Month-over-month comparison
            st.markdown("#### Comparaison mois en cours vs mois précédent")
            today = datetime.date.today()
            if today.month >= 2 and annee == today.year:
                cur = soldes[today.month - 1]
                prev = soldes[today.month - 2]
                col_cur, col_prev = st.columns(2)
                col_cur.metric("Dépenses réelles ce mois", f"{cur.total_variables_reel:,.0f} €",
                               delta=f"{cur.total_variables_reel - prev.total_variables_reel:+,.0f} €")
                col_prev.metric("Dépenses réelles mois précédent", f"{prev.total_variables_reel:,.0f} €")

            # Anomaly detection
            reels = [s.total_variables_reel for s in soldes_actifs if s.total_variables_reel > 0]
            if len(reels) >= 2:
                import numpy as np
                mean_reel = float(np.mean(reels))
                std_reel = float(np.std(reels))
                threshold = mean_reel * 1.2

                st.markdown("#### Détection de mois anormaux (dépassement > 20% de la moyenne)")
                mois_anormaux = [
                    (MOIS[s.mois - 1], s.total_variables_reel)
                    for s in soldes_actifs
                    if s.total_variables_reel > threshold
                ]
                if mois_anormaux:
                    for mois_nom, val in mois_anormaux:
                        st.markdown(
                            alert_html(
                                f"⚠️ <b>{mois_nom}</b> : {val:,.0f} € — "
                                f"{(val - mean_reel) / mean_reel * 100:+.0f}% par rapport à la moyenne ({mean_reel:,.0f} €).",
                                "warning",
                            ),
                            unsafe_allow_html=True,
                        )
                else:
                    st.markdown(
                        alert_html(
                            f"✓ Aucun mois anormal détecté. Moyenne : {mean_reel:,.0f} €/mois.",
                            "success",
                        ),
                        unsafe_allow_html=True,
                    )

                # vs year average
                st.markdown("#### Soldes par rapport à la moyenne annuelle")
                col_avg_l, col_avg_r = st.columns(2)
                with col_avg_l:
                    st.metric("Moyenne dépenses réelles", f"{mean_reel:,.0f} €/mois")
                with col_avg_r:
                    solde_moyen = sum(s.solde_disponible for s in soldes_actifs) / len(soldes_actifs)
                    st.metric("Solde disponible moyen", f"{solde_moyen:,.0f} €/mois")
