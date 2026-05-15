"""Journal des dépenses — saisie rapide et tableau paginé."""
from __future__ import annotations

import datetime

import pandas as pd
import streamlit as st

from gestion_dashboard.controllers import database as db
from gestion_dashboard.controllers.export import export_synthese_mensuelle_xlsx
from gestion_dashboard.controllers import calculs
from gestion_dashboard.models.budget import Depense
from gestion_dashboard.models.enums import MODES_PAIEMENT, MOIS
from gestion_dashboard.views.components import charts


def _current_month_year() -> tuple[int, int]:
    today = datetime.date.today()
    return (
        st.session_state.get("mois_selectionne", today.month),
        st.session_state.get("annee_selectionnee", today.year),
    )


def show() -> None:
    mois, annee = _current_month_year()
    today = datetime.date.today()

    st.markdown(
        '<div class="page-header"><h1>📓 Journal des Dépenses</h1>'
        "<p>Saisie et consultation des dépenses du mois.</p></div>",
        unsafe_allow_html=True,
    )

    # Month selector
    col_m, col_a, _ = st.columns([2, 2, 4])
    with col_m:
        mois_choisi = st.selectbox(
            "Mois", range(1, 13), format_func=lambda m: MOIS[m - 1],
            index=mois - 1, key="journal_mois",
        )
    with col_a:
        annee_choisie = st.number_input("Année", 2020, 2030, annee, 1, key="journal_annee")

    if mois_choisi != mois or annee_choisie != annee:
        st.session_state["mois_selectionne"] = mois_choisi
        st.session_state["annee_selectionnee"] = annee_choisie
        st.rerun()

    # ── Load data ──────────────────────────────────────────────────────────
    categories = db.get_categories()
    cat_map = {c.id: c for c in categories}
    cat_nom_map = {c.id: f"{c.icone} {c.nom}" for c in categories}
    dep_list = db.get_depenses(mois, annee)

    # ── Quick-entry form ───────────────────────────────────────────────────
    st.markdown('<div class="section-header">➕ Saisie rapide</div>', unsafe_allow_html=True)
    with st.form("form_depense", clear_on_submit=True):
        c1, c2, c3, c4, c5 = st.columns([2, 3, 2, 2, 2])
        with c1:
            dep_date = st.date_input(
                "Date",
                value=today if today.month == mois and today.year == annee else datetime.date(annee, mois, 1),
            )
        with c2:
            dep_lib = st.text_input("Libellé", placeholder="Supermarché, Restaurant, …")
        with c3:
            cat_options = [(c.id, f"{c.icone} {c.nom}") for c in categories]
            if cat_options:
                cat_selected_id = st.selectbox(
                    "Catégorie",
                    options=[o[0] for o in cat_options],
                    format_func=lambda cid: cat_nom_map.get(cid, "?"),
                )
            else:
                cat_selected_id = 0
                st.warning("Créez des catégories dans Paramètres.")
        with c4:
            dep_mt = st.number_input("Montant (€)", min_value=0.01, step=1.0, format="%.2f")
        with c5:
            dep_mode = st.selectbox("Paiement", MODES_PAIEMENT)

        dep_note = st.text_input("Note (optionnel)", placeholder="…")
        submitted = st.form_submit_button("✚ Ajouter la dépense", type="primary", width="stretch")

        if submitted:
            if dep_lib and dep_mt > 0 and cat_selected_id:
                dep_mois = dep_date.month
                dep_annee = dep_date.year
                db.save_depense(Depense(
                    id=0,
                    date=dep_date.isoformat(),
                    libelle=dep_lib,
                    categorie_id=cat_selected_id,
                    montant=dep_mt,
                    mode_paiement=dep_mode,
                    note=dep_note,
                    mois=dep_mois,
                    annee=dep_annee,
                ))
                st.success(f"✓ {dep_lib} — {dep_mt:.2f} € ajouté.")
                st.rerun()
            else:
                st.warning("Renseignez le libellé, la catégorie et le montant.")

    # ── Filters ────────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">📋 Dépenses du mois</div>', unsafe_allow_html=True)

    if dep_list:
        total_mois = sum(d.montant for d in dep_list)
        st.caption(f"{len(dep_list)} dépenses · Total : **{total_mois:,.2f} €**")

    # Filter bar
    fcol1, fcol2, fcol3 = st.columns(3)
    with fcol1:
        filter_cat = st.multiselect(
            "Filtrer par catégorie",
            options=[c.id for c in categories],
            format_func=lambda cid: cat_nom_map.get(cid, "?"),
            default=[],
        )
    with fcol2:
        filter_mode = st.multiselect("Filtrer par paiement", MODES_PAIEMENT, default=[])
    with fcol3:
        filter_search = st.text_input("Recherche libellé", placeholder="Chercher…")

    filtered = dep_list
    if filter_cat:
        filtered = [d for d in filtered if d.categorie_id in filter_cat]
    if filter_mode:
        filtered = [d for d in filtered if d.mode_paiement in filter_mode]
    if filter_search:
        filtered = [d for d in filtered if filter_search.lower() in d.libelle.lower()]

    # ── Paginated table ────────────────────────────────────────────────────
    if filtered:
        PAGE_SIZE = 50
        total_pages = max(1, (len(filtered) - 1) // PAGE_SIZE + 1)
        page = st.number_input("Page", 1, total_pages, 1, key="dep_page") if total_pages > 1 else 1
        page_items = filtered[(page - 1) * PAGE_SIZE : page * PAGE_SIZE]

        df_display = pd.DataFrame([
            {
                "Date": d.date,
                "Libellé": d.libelle,
                "Catégorie": cat_nom_map.get(d.categorie_id, "?"),
                "Montant (€)": d.montant,
                "Paiement": d.mode_paiement,
                "Note": d.note,
                "_id": d.id,
            }
            for d in page_items
        ])

        st.dataframe(
            df_display.drop(columns=["_id"]),
            width="stretch",
            hide_index=True,
            column_config={
                "Montant (€)": st.column_config.NumberColumn(format="%.2f €"),
            },
        )

        # Delete actions
        st.markdown("**Supprimer une dépense :**")
        del_cols = st.columns(min(len(page_items), 5))
        for i, d in enumerate(page_items[:5]):
            with del_cols[i % 5]:
                if st.button(f"🗑️ {d.libelle[:12]}…" if len(d.libelle) > 12 else f"🗑️ {d.libelle}", key=f"del_dep_{d.id}"):
                    db.delete_depense(d.id)
                    st.rerun()
    else:
        st.info("Aucune dépense pour ce mois." if not dep_list else "Aucune dépense ne correspond aux filtres.")

    st.markdown("---")

    # ── Category summary + pie chart ───────────────────────────────────────
    col_sum, col_pie = st.columns(2)

    with col_sum:
        st.markdown('<div class="section-header">Totaux par catégorie</div>', unsafe_allow_html=True)
        analyses = calculs.calcul_analyse_budget(
            categories,
            db.get_budgets_variables(mois, annee),
            dep_list,
        )
        if any(a.reel > 0 for a in analyses):
            df_cat = pd.DataFrame([
                {
                    "Catégorie": f"{a.categorie_icone} {a.categorie_nom}",
                    "Total dépensé (€)": round(a.reel, 2),
                    "% du total": f"{a.reel / sum(a2.reel for a2 in analyses if a2.reel > 0) * 100:.1f}%"
                    if sum(a2.reel for a2 in analyses) > 0 else "0%",
                    "vs Budget": f"{a.ecart:+,.0f} €",
                }
                for a in analyses
                if a.reel > 0
            ])
            st.dataframe(df_cat, width="stretch", hide_index=True)
        else:
            st.info("Aucune dépense ce mois.")

    with col_pie:
        st.markdown('<div class="section-header">Répartition</div>', unsafe_allow_html=True)
        if analyses and any(a.reel > 0 for a in analyses):
            st.plotly_chart(
                charts.chart_categories_piechart(analyses, show_reel=True),
                width="stretch",
            )

    # ── Excel export ───────────────────────────────────────────────────────
    if dep_list:
        params = db.get_parametres()
        charges = db.get_charges_fixes()
        produits = db.get_produits_epargne()
        bv_list = db.get_budgets_variables(mois, annee)
        exc_list = db.get_revenus_exceptionnels(mois, annee)
        total_exc = sum(r.montant for r in exc_list)
        solde = calculs.calcul_solde_mensuel(
            salaire=params.salaire_net,
            revenus_exceptionnels=total_exc,
            charges_fixes=charges,
            produits_epargne=produits,
            budgets_variables=bv_list,
            depenses=dep_list,
            mois=mois,
            annee=annee,
        )
        xlsx_bytes = export_synthese_mensuelle_xlsx(
            solde=solde,
            analyses=analyses,
            categories=categories,
            depenses=dep_list,
        )
        st.download_button(
            "⬇️ Exporter le mois en Excel",
            data=xlsx_bytes,
            file_name=f"budget_{MOIS[mois-1].lower()}_{annee}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
