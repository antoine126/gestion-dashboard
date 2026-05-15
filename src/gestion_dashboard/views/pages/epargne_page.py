"""Module Épargne & Patrimoine financier — projections et objectifs."""
from __future__ import annotations

import streamlit as st

from gestion_dashboard.controllers import database as db
from gestion_dashboard.controllers import epargne as ep_calc
from gestion_dashboard.styles.theme import alert_html
from gestion_dashboard.views.components import charts


def show() -> None:
    st.markdown(
        '<div class="page-header"><h1>🌱 Épargne & Patrimoine Financier</h1>'
        "<p>Vue consolidée, projections et objectifs d'épargne.</p></div>",
        unsafe_allow_html=True,
    )

    produits = db.get_produits_epargne()

    if not produits:
        st.markdown(
            alert_html(
                "Aucun produit d'épargne configuré. "
                "Rendez-vous dans <b>Paramètres → Épargne</b> pour en ajouter.",
                "info",
            ),
            unsafe_allow_html=True,
        )
        return

    total_solde = sum(p.solde_actuel for p in produits)
    total_vers = sum(p.versement_mensuel for p in produits)

    # ── Summary KPIs ───────────────────────────────────────────────────────
    k1, k2, k3 = st.columns(3)
    k1.metric("💰 Patrimoine total", f"{total_solde:,.0f} €")
    k2.metric("📅 Versements mensuels", f"{total_vers:,.0f} €")
    k3.metric("📈 Projection +1 an", f"{ep_calc.projection_interes_composes(total_solde, total_vers, 0, 1):,.0f} €")

    st.markdown("---")

    # ── Portfolio donut chart ───────────────────────────────────────────────
    patrimoine = ep_calc.calcul_patrimoine_financier(produits)
    if patrimoine:
        col_donut, col_table = st.columns([1, 1])
        with col_donut:
            st.markdown('<div class="section-header">Répartition du patrimoine</div>', unsafe_allow_html=True)
            st.plotly_chart(
                charts.chart_donut_epargne(
                    labels=list(patrimoine.keys()),
                    values=list(patrimoine.values()),
                ),
                width="stretch",
            )
        with col_table:
            st.markdown('<div class="section-header">Détail par produit</div>', unsafe_allow_html=True)
            for pe in produits:
                proj_1an = ep_calc.projection_interes_composes(
                    pe.solde_actuel, pe.versement_mensuel, pe.taux_annuel, 1
                )
                progress_pct = (
                    pe.solde_actuel / pe.objectif * 100
                    if pe.objectif and pe.objectif > 0
                    else None
                )
                with st.container():
                    st.markdown(
                        f"**{pe.produit}** "
                        f"<span style='font-size:12px;color:#7F8C8D'>{pe.type_produit}</span>",
                        unsafe_allow_html=True,
                    )
                    col_s, col_v, col_p = st.columns(3)
                    col_s.metric("Solde", f"{pe.solde_actuel:,.0f} €")
                    col_v.metric("Versement/mois", f"{pe.versement_mensuel:,.0f} €")
                    col_p.metric("Projection +1 an", f"{proj_1an:,.0f} €")
                    if progress_pct is not None:
                        st.progress(min(progress_pct / 100, 1.0), text=f"Objectif : {pe.objectif:,.0f} € ({progress_pct:.1f}%)")
                    st.markdown("---")

    # ── Individual projection simulator ────────────────────────────────────
    st.markdown('<div class="section-header">Simulateur de projection</div>', unsafe_allow_html=True)

    prod_names = [p.produit for p in produits]
    selected_prod_name = st.selectbox("Produit à simuler", prod_names)
    selected = next((p for p in produits if p.produit == selected_prod_name), produits[0])

    sc1, sc2, sc3, sc4 = st.columns(4)
    with sc1:
        sim_solde = st.number_input("Solde initial (€)", value=float(selected.solde_actuel), min_value=0.0, step=100.0)
    with sc2:
        sim_vers = st.number_input("Versement mensuel (€)", value=float(selected.versement_mensuel), min_value=0.0, step=50.0)
    with sc3:
        sim_taux = st.number_input("Taux annuel (%)", value=float(selected.taux_annuel), min_value=0.0, max_value=20.0, step=0.1)
    with sc4:
        sim_horizon = st.slider("Horizon (ans)", 1, 30, 10)

    years = list(range(0, sim_horizon + 1))
    projections = ep_calc.projection_annuelle_cumul(sim_solde, sim_vers, sim_taux, sim_horizon)

    objectif_sim = float(selected.objectif) if selected.objectif else None
    st.plotly_chart(
        charts.chart_projection_epargne(years, projections, selected.produit, objectif_sim),
        width="stretch",
    )

    # Horizons table
    horizons_data = ep_calc.projection_serie(sim_solde, sim_vers, sim_taux, [1, 3, 5, 10, 20, 30])
    import pandas as pd
    df_proj = pd.DataFrame([
        {"Horizon": f"{h} an{'s' if h > 1 else ''}", "Montant projeté": f"{v:,.0f} €"}
        for h, v in horizons_data.items()
    ])
    st.dataframe(df_proj, width="stretch", hide_index=True)

    # ── Scenario comparison ────────────────────────────────────────────────
    st.markdown('<div class="section-header">Comparaison de scénarios</div>', unsafe_allow_html=True)
    import plotly.graph_objects as go
    from gestion_dashboard.styles.theme import CHART_PALETTE

    scenarios = {
        f"Versement actuel ({sim_vers:,.0f} €/mois)": sim_vers,
        f"+50 €/mois ({sim_vers + 50:,.0f} €)": sim_vers + 50,
        f"+100 €/mois ({sim_vers + 100:,.0f} €)": sim_vers + 100,
        f"×2 ({sim_vers * 2:,.0f} €/mois)": sim_vers * 2,
    }
    fig_sc = go.Figure()
    fig_sc.update_layout(
        title="Comparaison de scénarios d'épargne",
        xaxis_title="Années",
        yaxis_title="Montant (€)",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif"),
        legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5),
        xaxis=dict(gridcolor="#ECF0F1"),
        yaxis=dict(gridcolor="#ECF0F1"),
    )
    for i, (label, vers) in enumerate(scenarios.items()):
        proj = ep_calc.projection_annuelle_cumul(sim_solde, vers, sim_taux, sim_horizon)
        fig_sc.add_trace(go.Scatter(
            x=years, y=proj, name=label,
            line=dict(color=CHART_PALETTE[i % len(CHART_PALETTE)], width=2),
            mode="lines",
            hovertemplate=f"Année %{{x}}: %{{y:,.0f}} €<extra>{label}</extra>",
        ))
    if objectif_sim:
        fig_sc.add_hline(y=objectif_sim, line_dash="dash", line_color="#27AE60",
                         annotation_text=f"Objectif: {objectif_sim:,.0f} €")
    st.plotly_chart(fig_sc, width="stretch")

    # ── Goal calculator ────────────────────────────────────────────────────
    st.markdown('<div class="section-header">Calculateur d\'objectif</div>', unsafe_allow_html=True)
    gc1, gc2, gc3, gc4 = st.columns(4)
    with gc1:
        goal_target = st.number_input("Objectif (€)", min_value=0.0, step=1000.0, value=20000.0)
    with gc2:
        goal_solde = st.number_input("Solde actuel (€)", min_value=0.0, step=100.0, value=sim_solde)
    with gc3:
        goal_taux = st.number_input("Taux (%)", min_value=0.0, max_value=20.0, step=0.1, value=sim_taux)
    with gc4:
        goal_mois = st.number_input("Dans combien de mois ?", min_value=1, step=1, value=24)

    if goal_target > goal_solde:
        vers_need = ep_calc.versement_necessaire_pour_objectif(
            goal_target, goal_solde, goal_taux, goal_mois
        )
        st.markdown(
            alert_html(
                f"Pour atteindre <b>{goal_target:,.0f} €</b> en {goal_mois} mois avec "
                f"un taux de {goal_taux:.1f}%, il vous faut verser <b>{vers_need:,.0f} €/mois</b>.",
                "info",
            ),
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            alert_html("✓ Votre solde actuel dépasse déjà cet objectif !", "success"),
            unsafe_allow_html=True,
        )
