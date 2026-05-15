"""Module Prévisionnel Annuel — planification des grosses dépenses."""
from __future__ import annotations

import datetime

import pandas as pd
import streamlit as st

from gestion_dashboard.controllers import database as db
from gestion_dashboard.models.budget import PlanningDepense
from gestion_dashboard.models.enums import MOIS, STATUTS_PREVISIONNEL
from gestion_dashboard.styles.theme import alert_html, badge_html
from gestion_dashboard.views.components import charts


def _get_annee() -> int:
    return st.session_state.get("annee_selectionnee", datetime.date.today().year)


def _badge_for_statut(statut: str) -> str:
    color_map = {
        "À venir": "gray",
        "Payé": "green",
        "En cours": "orange",
        "Annulé": "red",
    }
    return badge_html(statut, color_map.get(statut, "gray"))


def show() -> None:
    annee = _get_annee()

    st.markdown(
        '<div class="page-header"><h1>📦 Prévisionnel Annuel</h1>'
        f"<p>Planifiez vos grosses dépenses pour {annee}.</p></div>",
        unsafe_allow_html=True,
    )

    items = db.get_previsionnel(annee)

    # ── KPIs ───────────────────────────────────────────────────────────────
    total_estime = sum(i.montant_estime for i in items)
    total_reel = sum(i.montant_reel for i in items if i.montant_reel is not None)
    reste_a_venir = sum(i.montant_estime for i in items if i.statut == "À venir")
    mois_restants = max(1, 12 - datetime.date.today().month + 1)
    mensualite_sug = reste_a_venir / mois_restants if reste_a_venir > 0 else 0

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("📋 Total prévu", f"{total_estime:,.0f} €")
    k2.metric("✅ Total réel payé", f"{total_reel:,.0f} €")
    k3.metric("⏳ Reste à venir", f"{reste_a_venir:,.0f} €")
    k4.metric("💡 Mensualité suggérée", f"{mensualite_sug:,.0f} €/mois")

    if mensualite_sug > 0:
        st.markdown(
            alert_html(
                f"Pour couvrir les dépenses à venir ({reste_a_venir:,.0f} €) sur "
                f"{mois_restants} mois restants, provisionnez <b>{mensualite_sug:,.0f} €/mois</b>.",
                "info",
            ),
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # ── Add new forecast item ──────────────────────────────────────────────
    categories = db.get_categories()
    cat_options = [None] + [c.id for c in categories]
    cat_labels = {c.id: f"{c.icone} {c.nom}" for c in categories}

    with st.expander("➕ Ajouter une dépense prévisionnelle", expanded=len(items) == 0):
        with st.form("form_previsionnel"):
            fc1, fc2, fc3 = st.columns([3, 2, 2])
            with fc1:
                new_lib = st.text_input("Libellé")
            with fc2:
                new_mois = st.selectbox("Mois prévu", range(1, 13), format_func=lambda m: MOIS[m - 1])
            with fc3:
                new_statut = st.selectbox("Statut", STATUTS_PREVISIONNEL)
            nc1, nc2, nc3, nc4 = st.columns(4)
            with nc1:
                new_estime = st.number_input("Montant estimé (€)", min_value=0.0, step=100.0)
            with nc2:
                new_reel_val = st.number_input("Montant réel (€) — optionnel", min_value=0.0, step=100.0)
            with nc3:
                new_note = st.text_input("Note (optionnel)")
            with nc4:
                new_cat_id = st.selectbox(
                    "Catégorie (optionnel)",
                    options=cat_options,
                    format_func=lambda cid: cat_labels.get(cid, "— Aucune —") if cid else "— Aucune —",
                )
            if st.form_submit_button("Ajouter", type="primary"):
                if new_lib and new_estime > 0:
                    db.save_planning_depense(PlanningDepense(
                        id=0,
                        annee=annee,
                        libelle=new_lib,
                        mois_prevu=new_mois,
                        montant_estime=new_estime,
                        montant_reel=new_reel_val if new_reel_val > 0 else None,
                        statut=new_statut,
                        note=new_note,
                        categorie_id=new_cat_id,
                    ))
                    st.success(f"✓ {new_lib} ajouté.")
                    st.rerun()
                else:
                    st.warning("Renseignez un libellé et un montant estimé.")

    # ── Planning table ─────────────────────────────────────────────────────
    st.markdown('<div class="section-header">Tableau de planification</div>', unsafe_allow_html=True)

    if items:
        # Sort by month
        items_sorted = sorted(items, key=lambda i: i.mois_prevu)

        df = pd.DataFrame([
            {
                "Mois": MOIS[i.mois_prevu - 1],
                "Libellé": i.libelle,
                "Catégorie": cat_labels.get(i.categorie_id, "") if i.categorie_id else "",
                "Estimé (€)": i.montant_estime,
                "Réel (€)": i.montant_reel or "",
                "Écart (€)": (i.montant_reel - i.montant_estime) if i.montant_reel else "",
                "Statut": i.statut,
                "Note": i.note,
                "_id": i.id,
            }
            for i in items_sorted
        ])

        col_config = {
            "Estimé (€)": st.column_config.NumberColumn(format="%.0f €"),
            "Réel (€)": st.column_config.NumberColumn(format="%.0f €"),
        }
        st.dataframe(df.drop(columns=["_id"]), width="stretch", hide_index=True, column_config=col_config)

        # Edit/delete per item
        st.markdown("**Modifier ou supprimer :**")
        for item in items_sorted:
            with st.expander(
                f"{MOIS[item.mois_prevu - 1]} — {item.libelle} "
                f"({item.montant_estime:,.0f} €) [{item.statut}]",
                expanded=False,
            ):
                ic1, ic2, ic3 = st.columns(3)
                with ic1:
                    upd_lib = st.text_input("Libellé", value=item.libelle, key=f"pv_lib_{item.id}")
                    upd_mois = st.selectbox(
                        "Mois", range(1, 13),
                        format_func=lambda m: MOIS[m - 1],
                        index=item.mois_prevu - 1,
                        key=f"pv_mois_{item.id}",
                    )
                with ic2:
                    upd_estime = st.number_input("Estimé (€)", value=item.montant_estime, min_value=0.0, step=100.0, key=f"pv_est_{item.id}")
                    upd_reel = st.number_input(
                        "Réel (€)",
                        value=float(item.montant_reel) if item.montant_reel else 0.0,
                        min_value=0.0, step=100.0,
                        key=f"pv_reel_{item.id}",
                    )
                with ic3:
                    upd_statut = st.selectbox(
                        "Statut",
                        STATUTS_PREVISIONNEL,
                        index=STATUTS_PREVISIONNEL.index(item.statut) if item.statut in STATUTS_PREVISIONNEL else 0,
                        key=f"pv_stat_{item.id}",
                    )
                    upd_note = st.text_input("Note", value=item.note, key=f"pv_note_{item.id}")
                    cur_cat_idx = cat_options.index(item.categorie_id) if item.categorie_id in cat_options else 0
                    upd_cat_id = st.selectbox(
                        "Catégorie",
                        options=cat_options,
                        index=cur_cat_idx,
                        format_func=lambda cid: cat_labels.get(cid, "— Aucune —") if cid else "— Aucune —",
                        key=f"pv_cat_{item.id}",
                    )

                col_save, col_del = st.columns(2)
                with col_save:
                    if st.button("💾 Enregistrer", key=f"save_pv_{item.id}"):
                        db.save_planning_depense(PlanningDepense(
                            id=item.id,
                            annee=annee,
                            libelle=upd_lib,
                            mois_prevu=upd_mois,
                            montant_estime=upd_estime,
                            montant_reel=upd_reel if upd_reel > 0 else None,
                            statut=upd_statut,
                            note=upd_note,
                            categorie_id=upd_cat_id,
                        ))
                        st.success("✓ Mis à jour.")
                        st.rerun()
                with col_del:
                    if st.button("🗑️ Supprimer", key=f"del_pv_{item.id}"):
                        db.delete_planning_depense(item.id)
                        st.rerun()

        # ── Timeline chart ─────────────────────────────────────────────────
        st.markdown('<div class="section-header">Calendrier des dépenses</div>', unsafe_allow_html=True)
        if items_sorted:
            st.plotly_chart(
                charts.chart_previsionnel_timeline(items_sorted, MOIS),
                width="stretch",
            )
    else:
        st.info("Aucune dépense prévisionnelle pour cette année. Ajoutez-en une ci-dessus.")

    # ── JSON Export ────────────────────────────────────────────────────────
    st.markdown("---")
    if st.button("📥 Exporter toutes les données (JSON)"):
        json_data = db.export_to_json()
        st.download_button(
            "⬇️ Télécharger backup.json",
            data=json_data.encode("utf-8"),
            file_name=f"budget_backup_{annee}.json",
            mime="application/json",
        )
