"""Module Paramètres — salaire, 50/30/20, charges fixes, épargne, catégories."""
from __future__ import annotations

import datetime

import streamlit as st

from gestion_dashboard.controllers import calculs
from gestion_dashboard.controllers import database as db
from gestion_dashboard.models.budget import (
    CategorieDepense,
    ChargeFix,
    Parametres,
    ProduitEpargne,
    Projet,
)
from gestion_dashboard.models.enums import (
    FREQUENCES_CHARGE,
    TYPES_PRODUIT_EPARGNE,
)
from gestion_dashboard.styles.theme import alert_html


def _fmt(v: float) -> str:
    return f"{v:,.0f} €"


def show() -> None:
    st.markdown(
        '<div class="page-header"><h1>⚙️ Paramètres</h1>'
        "<p>Configuration globale — ces valeurs se propagent sur tous les mois.</p></div>",
        unsafe_allow_html=True,
    )

    params = db.get_parametres()

    # ── Tabs ───────────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
        ["💰 Salaire & 50/30/20", "🔒 Charges fixes", "🌱 Épargne", "🏷️ Catégories", "🎯 Projets", "📋 Budgets par défaut"]
    )

    # ══ Tab 1 — Salaire & 50/30/20 ═════════════════════════════════════════
    with tab1:
        st.markdown('<div class="section-header">Salaire & répartition budgétaire</div>', unsafe_allow_html=True)

        col_form, col_preview = st.columns([1, 1])

        with col_form:
            salaire = st.number_input(
                "Salaire net mensuel (€)",
                min_value=0.0,
                value=float(params.salaire_net),
                step=50.0,
                format="%.2f",
                help="Votre revenu mensuel net après impôts.",
            )
            st.markdown("**Personnaliser les pourcentages :**")
            col_p1, col_p2, col_p3 = st.columns(3)
            with col_p1:
                taux_b = st.number_input("🏠 Besoins %", 0, 100, int(params.taux_besoins * 100), 5) / 100
            with col_p2:
                taux_l = st.number_input("🎬 Loisirs %", 0, 100, int(params.taux_loisirs * 100), 5) / 100
            with col_p3:
                taux_e = st.number_input("🌱 Épargne %", 0, 100, int(params.taux_epargne * 100), 5) / 100

            total_pct = taux_b + taux_l + taux_e
            if abs(total_pct - 1.0) > 0.01:
                st.markdown(
                    alert_html(
                        f"⚠️ La somme des pourcentages est {total_pct*100:.0f}% (recommandé : 100%).",
                        "warning",
                    ),
                    unsafe_allow_html=True,
                )

            annee_param = st.number_input(
                "Année de référence",
                min_value=2020,
                max_value=2030,
                value=int(params.annee),
            )

            if st.button("💾 Enregistrer les paramètres", type="primary"):
                new_params = Parametres(
                    salaire_net=salaire,
                    annee=annee_param,
                    taux_besoins=taux_b,
                    taux_loisirs=taux_l,
                    taux_epargne=taux_e,
                )
                db.save_parametres(new_params)
                st.session_state["annee_selectionnee"] = annee_param
                st.success("✓ Paramètres enregistrés.")
                st.rerun()

        with col_preview:
            if salaire > 0:
                rep = calculs.calcul_repartition_503020(salaire, taux_b, taux_l, taux_e)
                st.markdown("**Aperçu de vos enveloppes :**")
                st.markdown(f"""
| Enveloppe | Taux | Montant mensuel |
|---|---|---|
| 🏠 Besoins essentiels | {taux_b*100:.0f}% | **{rep.besoins:,.0f} €** |
| 🎬 Loisirs & envies   | {taux_l*100:.0f}% | **{rep.loisirs:,.0f} €** |
| 🌱 Épargne            | {taux_e*100:.0f}% | **{rep.epargne:,.0f} €** |
| **Total** | {(taux_b+taux_l+taux_e)*100:.0f}% | **{salaire:,.0f} €** |
""")
                charges = db.get_charges_fixes()
                total_charges = sum(c.montant_mensuel for c in charges)
                if total_charges > rep.besoins:
                    st.markdown(
                        alert_html(
                            f"⚠️ Vos charges fixes ({total_charges:,.0f} €) dépassent "
                            f"l'enveloppe Besoins ({rep.besoins:,.0f} €) !",
                            "danger",
                        ),
                        unsafe_allow_html=True,
                    )
            else:
                st.info("Saisissez un salaire pour voir l'aperçu.")

    # ══ Tab 2 — Charges fixes ═══════════════════════════════════════════════
    with tab2:
        st.markdown('<div class="section-header">Charges fixes mensuelles</div>', unsafe_allow_html=True)

        charges = db.get_charges_fixes(actif_only=False)
        total_cf = sum(c.montant_mensuel for c in charges if c.actif)
        st.caption(f"Total mensuel actif : **{total_cf:,.0f} €**")

        # Add new charge
        with st.expander("➕ Ajouter une charge fixe", expanded=len(charges) == 0):
            c1, c2, c3 = st.columns([3, 2, 2])
            with c1:
                new_lib = st.text_input("Libellé", key="new_cf_lib", placeholder="Loyer, EDF, …")
            with c2:
                new_mt = st.number_input("Montant (€)", min_value=0.0, step=10.0, key="new_cf_mt")
            with c3:
                new_freq = st.selectbox("Fréquence", FREQUENCES_CHARGE, key="new_cf_freq")
            if st.button("Ajouter", key="btn_add_cf"):
                if new_lib and new_mt > 0:
                    db.save_charge_fix(ChargeFix(id=0, libelle=new_lib, montant=new_mt, frequence=new_freq))
                    st.success(f"✓ {new_lib} ajouté.")
                    st.rerun()
                else:
                    st.warning("Renseignez un libellé et un montant.")

        # Display & edit existing charges
        if charges:
            for cf in charges:
                with st.container():
                    c1, c2, c3, c4, c5 = st.columns([3, 2, 2, 1, 1])
                    with c1:
                        st.text_input("Libellé", value=cf.libelle, key=f"cf_lib_{cf.id}", label_visibility="collapsed")
                    with c2:
                        st.number_input("€", value=float(cf.montant), step=10.0, key=f"cf_mt_{cf.id}", label_visibility="collapsed")
                    with c3:
                        freq_idx = FREQUENCES_CHARGE.index(cf.frequence) if cf.frequence in FREQUENCES_CHARGE else 0
                        st.selectbox("Fréq.", FREQUENCES_CHARGE, index=freq_idx, key=f"cf_freq_{cf.id}", label_visibility="collapsed")
                    with c4:
                        if st.button("💾", key=f"save_cf_{cf.id}", help="Enregistrer"):
                            updated = ChargeFix(
                                id=cf.id,
                                libelle=st.session_state[f"cf_lib_{cf.id}"],
                                montant=st.session_state[f"cf_mt_{cf.id}"],
                                frequence=st.session_state[f"cf_freq_{cf.id}"],
                                actif=cf.actif,
                            )
                            db.save_charge_fix(updated)
                            st.rerun()
                    with c5:
                        if st.button("🗑️", key=f"del_cf_{cf.id}", help="Supprimer"):
                            db.delete_charge_fix(cf.id)
                            st.rerun()
        else:
            st.info("Aucune charge fixe. Ajoutez-en une ci-dessus.")

    # ══ Tab 3 — Épargne programmée ══════════════════════════════════════════
    with tab3:
        st.markdown('<div class="section-header">Plans d\'épargne programmée</div>', unsafe_allow_html=True)

        produits = db.get_produits_epargne(actif_only=False)
        total_ep = sum(p.versement_mensuel for p in produits if p.actif)
        total_solde = sum(p.solde_actuel for p in produits if p.actif)
        col_a, col_b = st.columns(2)
        col_a.metric("Versements mensuels", f"{total_ep:,.0f} €")
        col_b.metric("Patrimoine total", f"{total_solde:,.0f} €")

        # Add new savings product
        with st.expander("➕ Ajouter un produit d'épargne", expanded=len(produits) == 0):
            pc1, pc2 = st.columns(2)
            with pc1:
                new_prod = st.text_input("Nom du produit", key="new_ep_prod", placeholder="Livret A, PEA, …")
                new_type = st.selectbox("Type", TYPES_PRODUIT_EPARGNE, key="new_ep_type")
                new_taux = st.number_input("Taux annuel (%)", 0.0, 20.0, 0.0, 0.1, key="new_ep_taux")
            with pc2:
                new_solde = st.number_input("Solde actuel (€)", 0.0, step=100.0, key="new_ep_solde")
                new_vers = st.number_input("Versement mensuel (€)", 0.0, step=50.0, key="new_ep_vers")
                new_obj = st.number_input("Objectif (€) — optionnel", 0.0, step=1000.0, key="new_ep_obj")
            if st.button("Ajouter", key="btn_add_ep"):
                if new_prod:
                    db.save_produit_epargne(ProduitEpargne(
                        id=0,
                        produit=new_prod,
                        type_produit=new_type,
                        solde_actuel=new_solde,
                        versement_mensuel=new_vers,
                        taux_annuel=new_taux,
                        objectif=new_obj if new_obj > 0 else None,
                    ))
                    st.success(f"✓ {new_prod} ajouté.")
                    st.rerun()

        # Edit existing products
        if produits:
            for pe in produits:
                with st.expander(f"{pe.produit} — {pe.solde_actuel:,.0f} €", expanded=False):
                    col1, col2 = st.columns(2)
                    with col1:
                        lib = st.text_input("Nom", value=pe.produit, key=f"ep_prod_{pe.id}")
                        tp = st.selectbox(
                            "Type",
                            TYPES_PRODUIT_EPARGNE,
                            index=TYPES_PRODUIT_EPARGNE.index(pe.type_produit)
                            if pe.type_produit in TYPES_PRODUIT_EPARGNE else 0,
                            key=f"ep_type_{pe.id}",
                        )
                        taux = st.number_input("Taux (%)", 0.0, 20.0, float(pe.taux_annuel), 0.1, key=f"ep_taux_{pe.id}")
                    with col2:
                        solde = st.number_input("Solde actuel (€)", 0.0, step=100.0, value=float(pe.solde_actuel), key=f"ep_sol_{pe.id}")
                        vers = st.number_input("Versement mensuel (€)", 0.0, step=50.0, value=float(pe.versement_mensuel), key=f"ep_vers_{pe.id}")
                        obj_val = float(pe.objectif) if pe.objectif else 0.0
                        obj = st.number_input("Objectif (€)", 0.0, step=1000.0, value=obj_val, key=f"ep_obj_{pe.id}")

                    col_s, col_d = st.columns(2)
                    with col_s:
                        if st.button("💾 Enregistrer", key=f"save_ep_{pe.id}"):
                            db.save_produit_epargne(ProduitEpargne(
                                id=pe.id,
                                produit=lib,
                                type_produit=tp,
                                solde_actuel=solde,
                                versement_mensuel=vers,
                                taux_annuel=taux,
                                objectif=obj if obj > 0 else None,
                                actif=pe.actif,
                            ))
                            st.success("✓ Enregistré.")
                            st.rerun()
                    with col_d:
                        if st.button("🗑️ Supprimer", key=f"del_ep_{pe.id}"):
                            db.delete_produit_epargne(pe.id)
                            st.rerun()
        else:
            st.info("Aucun produit d'épargne. Ajoutez-en un ci-dessus.")

    # ══ Tab 4 — Catégories de dépenses ══════════════════════════════════════
    with tab4:
        st.markdown('<div class="section-header">Catégories de dépenses variables</div>', unsafe_allow_html=True)

        categories = db.get_categories()

        with st.expander("➕ Ajouter une catégorie", expanded=False):
            cx1, cx2, cx3 = st.columns([3, 1, 2])
            with cx1:
                new_cat_nom = st.text_input("Nom", key="new_cat_nom")
            with cx2:
                new_cat_icone = st.text_input("Icône", value="📦", key="new_cat_icone", max_chars=4)
            with cx3:
                new_cat_color = st.color_picker("Couleur", "#BDC3C7", key="new_cat_col")
            if st.button("Ajouter catégorie", key="btn_add_cat"):
                if new_cat_nom:
                    max_ordre = max((c.ordre for c in categories), default=0)
                    db.save_categorie(CategorieDepense(
                        id=0, nom=new_cat_nom, icone=new_cat_icone,
                        couleur=new_cat_color, ordre=max_ordre + 1,
                    ))
                    st.success(f"✓ {new_cat_nom} ajouté.")
                    st.rerun()

        if categories:
            for cat in categories:
                c1, c2, c3, c4, c5 = st.columns([1, 3, 1, 1, 1])
                with c1:
                    st.markdown(f"<span style='font-size:20px'>{cat.icone}</span>", unsafe_allow_html=True)
                with c2:
                    st.text(cat.nom)
                with c3:
                    st.markdown(
                        f"<div style='width:20px;height:20px;border-radius:4px;"
                        f"background:{cat.couleur};margin-top:8px'></div>",
                        unsafe_allow_html=True,
                    )
                with c4:
                    pass
                with c5:
                    if st.button("🗑️", key=f"del_cat_{cat.id}", help="Supprimer"):
                        db.delete_categorie(cat.id)
                        st.rerun()
        else:
            st.info("Aucune catégorie.")

    # ══ Tab 5 — Projets personnels ══════════════════════════════════════════
    with tab5:
        st.markdown('<div class="section-header">Projets personnels</div>', unsafe_allow_html=True)
        st.caption("Définissez vos objectifs d'épargne projet (voiture, vacances, travaux…). "
                   "Allouez le surplus mensuel depuis la Vue Mensuelle.")

        projets = db.get_projets(actif_only=False)

        with st.expander("➕ Ajouter un projet", expanded=len(projets) == 0):
            pj1, pj2 = st.columns(2)
            with pj1:
                pj_nom = st.text_input("Nom du projet", key="new_pj_nom", placeholder="Achat voiture, Vacances…")
                pj_desc = st.text_input("Description (optionnel)", key="new_pj_desc")
            with pj2:
                pj_cible = st.number_input("Montant cible (€)", min_value=0.0, step=100.0, key="new_pj_cible")
                pj_date = st.date_input(
                    "Date souhaitée",
                    value=datetime.date.today().replace(month=12, day=31),
                    key="new_pj_date",
                )
            if st.button("Ajouter projet", key="btn_add_pj"):
                if pj_nom and pj_cible > 0:
                    db.save_projet(Projet(
                        id=0,
                        nom=pj_nom,
                        description=pj_desc,
                        montant_cible=pj_cible,
                        date_souhaitee=pj_date.isoformat(),
                        montant_alloue=0.0,
                        actif=True,
                    ))
                    st.success(f"✓ Projet « {pj_nom} » créé.")
                    st.rerun()
                else:
                    st.warning("Renseignez un nom et un montant cible.")

        if projets:
            for proj in projets:
                pct = min(100.0, proj.montant_alloue / proj.montant_cible * 100) if proj.montant_cible > 0 else 0.0
                with st.expander(
                    f"{'✅' if pct >= 100 else '🎯'} {proj.nom} — "
                    f"{proj.montant_alloue:,.0f} / {proj.montant_cible:,.0f} € ({pct:.0f}%)",
                    expanded=False,
                ):
                    col1, col2 = st.columns(2)
                    with col1:
                        edit_nom = st.text_input("Nom", value=proj.nom, key=f"pj_nom_{proj.id}")
                        edit_desc = st.text_input("Description", value=proj.description, key=f"pj_desc_{proj.id}")
                    with col2:
                        edit_cible = st.number_input(
                            "Montant cible (€)", 0.0, step=100.0,
                            value=float(proj.montant_cible), key=f"pj_cible_{proj.id}",
                        )
                        date_val = datetime.date.fromisoformat(proj.date_souhaitee) if proj.date_souhaitee else datetime.date.today()
                        edit_date = st.date_input("Date souhaitée", value=date_val, key=f"pj_date_{proj.id}")

                    st.progress(pct / 100, text=f"{proj.montant_alloue:,.0f} € / {proj.montant_cible:,.0f} €")

                    col_s, col_t, col_d = st.columns(3)
                    with col_s:
                        if st.button("💾 Enregistrer", key=f"save_pj_{proj.id}"):
                            db.save_projet(Projet(
                                id=proj.id,
                                nom=edit_nom,
                                description=edit_desc,
                                montant_cible=edit_cible,
                                date_souhaitee=edit_date.isoformat(),
                                montant_alloue=proj.montant_alloue,
                                actif=proj.actif,
                            ))
                            st.success("✓ Enregistré.")
                            st.rerun()
                    with col_t:
                        label_actif = "🔴 Désactiver" if proj.actif else "🟢 Réactiver"
                        if st.button(label_actif, key=f"toggle_pj_{proj.id}"):
                            db.save_projet(Projet(**{**proj.model_dump(), "actif": not proj.actif}))
                            st.rerun()
                    with col_d:
                        if st.button("🗑️ Supprimer", key=f"del_pj_{proj.id}"):
                            db.delete_projet(proj.id)
                            st.rerun()
        else:
            st.info("Aucun projet. Créez-en un ci-dessus.")

    # ══ Tab 6 — Budgets par défaut ══════════════════════════════════════════
    with tab6:
        st.markdown('<div class="section-header">Budgets mensuels par défaut</div>', unsafe_allow_html=True)
        st.caption(
            "Ces montants sont pré-remplis dans la Vue Mensuelle quand aucun budget "
            "spécifique n'a encore été défini pour un mois donné. Vous pouvez les "
            "modifier mois par mois directement depuis la Vue Mensuelle."
        )

        categories = db.get_categories()
        if not categories:
            st.info("Aucune catégorie configurée. Ajoutez-en dans l'onglet Catégories.")
        else:
            defauts = db.get_budgets_defaut()
            st.markdown("")

            col_labels, col_inputs = st.columns([2, 2])
            with col_labels:
                st.markdown("**Catégorie**")
            with col_inputs:
                st.markdown("**Budget mensuel par défaut (€)**")

            new_defauts: dict[int, float] = {}
            for cat in categories:
                c1, c2 = st.columns([2, 2])
                with c1:
                    st.markdown(
                        f"<div style='margin-top:8px'>{cat.icone} {cat.nom}</div>",
                        unsafe_allow_html=True,
                    )
                with c2:
                    new_defauts[cat.id] = st.number_input(
                        f"Défaut {cat.nom}",
                        min_value=0.0,
                        value=defauts.get(cat.id, 0.0),
                        step=10.0,
                        label_visibility="collapsed",
                        key=f"defaut_{cat.id}",
                    )

            st.markdown("")
            total_defaut = sum(new_defauts.values())
            st.caption(f"Total mensuel par défaut : **{total_defaut:,.0f} €**")

            if st.button("💾 Enregistrer les budgets par défaut", type="primary"):
                db.save_budgets_defaut(new_defauts)
                st.success("✓ Budgets par défaut enregistrés.")
                st.rerun()
