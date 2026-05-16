"""Page Streamlit — Export du rapport financier en PDF."""
from __future__ import annotations

import datetime

import streamlit as st

from gestion_dashboard.controllers import calculs
from gestion_dashboard.controllers import database as db
from gestion_dashboard.controllers.pdf_export import generate_rapport_pdf


def _get_annee() -> int:
    return st.session_state.get("annee_selectionnee", datetime.date.today().year)


def show() -> None:
    annee = _get_annee()

    st.markdown(
        '<div class="page-header"><h1>📄 Export PDF</h1>'
        f"<p>G&eacute;n&eacute;rez un rapport complet de votre budget {annee}.</p></div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="section-header">Contenu du rapport</div>',
        unsafe_allow_html=True,
    )

    col_opts, col_desc = st.columns([1, 2])

    with col_opts:
        include_piechart = st.checkbox("Répartition 50/30/20 vs Réel", value=True)
        include_mensuel = st.checkbox("Tableau de suivi mensuel (12 mois)", value=True)
        include_heatmap = st.checkbox("Heatmap des dépenses", value=True)

    with col_desc:
        st.markdown("""
Le rapport PDF généré contient :

- **Page de couverture** — année, salaire, date de génération
- **Dashboard Annuel** — KPIs + graphique d'évolution + barres groupées
- **Budget 50/30/20** *(optionnel)* — camembert théorique vs réel
- **Synthèse par catégorie** — tableau + camembert des dépenses réelles
- **Suivi mensuel** *(optionnel)* — récapitulatif des 12 mois (couleur par solde)
- **Analyses** *(optionnel)* — heatmap × catégorie/mois + répartition cumulée
""")

    st.markdown("---")

    if st.button("📄 Générer le rapport PDF", type="primary", use_container_width=False):
        with st.spinner("Chargement des données et génération des graphiques…"):
            try:
                _generate_and_offer_download(
                    annee=annee,
                    include_piechart=include_piechart,
                    include_mensuel=include_mensuel,
                    include_heatmap=include_heatmap,
                )
            except ImportError as exc:
                st.error(
                    f"**Dépendance manquante :** `{exc}`\n\n"
                    "Vérifiez que fpdf2 et kaleido sont bien installés :\n"
                    "```\nuv sync\n```"
                )
            except Exception as exc:
                st.error(f"**Erreur lors de la génération :** {exc}")


def _generate_and_offer_download(
    annee: int,
    include_piechart: bool,
    include_mensuel: bool,
    include_heatmap: bool,
) -> None:
    # ── Load data ──────────────────────────────────────────────────────────
    params = db.get_parametres()
    charges = db.get_charges_fixes()
    produits = db.get_produits_epargne()
    categories = db.get_categories()
    all_dep = db.get_all_depenses(annee)
    all_bv = db.get_all_budgets_variables(annee)

    # ── Build monthly balances ─────────────────────────────────────────────
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

    kpis = calculs.calcul_kpis_annuels(params, soldes, produits)
    analyses = calculs.calcul_analyse_budget(categories, all_bv, all_dep)

    repartition = None
    if include_piechart and params.salaire_net > 0:
        repartition = calculs.calcul_repartition_503020(
            params.salaire_net,
            params.taux_besoins,
            params.taux_loisirs,
            params.taux_epargne,
        )

    # ── Heatmap matrix ─────────────────────────────────────────────────────
    heatmap_matrix = None
    if include_heatmap and categories and all_dep:
        heatmap_matrix = [
            [
                sum(d.montant for d in all_dep if d.mois == m and d.categorie_id == cat.id)
                for m in range(1, 13)
            ]
            for cat in categories
        ]

    # ── Generate PDF ───────────────────────────────────────────────────────
    pdf_bytes = generate_rapport_pdf(
        annee=annee,
        parametres=params,
        kpis=kpis,
        soldes=soldes,
        analyses=analyses,
        repartition=repartition,
        categories=categories if include_heatmap else None,
        heatmap_matrix=heatmap_matrix,
        include_mensuel=include_mensuel,
        include_heatmap=include_heatmap,
    )

    st.success("✅ Rapport généré avec succès !")
    st.download_button(
        label="⬇️ Télécharger le rapport PDF",
        data=pdf_bytes,
        file_name=f"rapport_budget_{annee}.pdf",
        mime="application/pdf",
        type="primary",
    )
