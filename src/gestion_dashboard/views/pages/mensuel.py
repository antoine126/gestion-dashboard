"""Vue mensuelle — charges fixes, épargne, dépenses variables et fonctionnalités v1.1."""
from __future__ import annotations

import datetime

import streamlit as st

from gestion_dashboard.controllers import calculs
from gestion_dashboard.controllers import database as db
from gestion_dashboard.models.budget import (
    AllocationProjet,
    BudgetVariable,
    EpargneExceptionnelle,
    RevenuExceptionnel,
)
from gestion_dashboard.models.enums import MOIS
from gestion_dashboard.styles.theme import alert_html, budget_bar_html


def _current_month_year() -> tuple[int, int]:
    today = datetime.date.today()
    return (
        st.session_state.get("mois_selectionne", today.month),
        st.session_state.get("annee_selectionnee", today.year),
    )


def _calcul_solde_reporte(mois: int, annee: int, params, charges, produits, budgets_defaut: dict | None = None) -> float:
    """Return the running balance carried into *mois* from all prior months.

    Positive  → surplus reporté  (green card).
    Negative  → déficit reporté  (red card).
    Zero      → nothing to carry (January, or perfectly balanced year so far).

    Each prior month is replayed exactly as displayed (we pass *cumul* as
    solde_reporte so s.solde_disponible == what the user saw that month).

    A month is *active* if it has at least one real entry (expense, exceptional
    revenue, exceptional saving, or project allocation).  Active months update
    the running balance.  Months with no entries at all are *neutral*: they
    neither build up a phantom surplus nor cancel a deficit.
    """
    cumul = 0.0
    _defauts = budgets_defaut or {}
    _all_cats = db.get_categories() if _defauts else []
    previsionnel_annee = db.get_previsionnel(annee)   # load once for the year
    for m in range(1, mois):
        bv = db.get_budgets_variables(m, annee)
        # Apply default budgets for categories not specifically set that month
        if _defauts:
            _bv_set = {b.categorie_id for b in bv}
            for _cat in _all_cats:
                if _cat.id not in _bv_set and _defauts.get(_cat.id, 0.0) > 0:
                    bv.append(BudgetVariable(
                        id=0, mois=m, annee=annee,
                        categorie_id=_cat.id,
                        montant_budgete=_defauts[_cat.id],
                    ))
        dep = db.get_depenses(m, annee)
        exc = db.get_revenus_exceptionnels(m, annee)
        ee = db.get_epargne_exceptionnelles(m, annee)
        alloc = db.get_allocations_projet(m, annee)
        prev = [p for p in previsionnel_annee if p.mois_prevu == m]
        total_exc = sum(r.montant for r in exc)
        s = calculs.calcul_solde_mensuel(
            salaire=params.salaire_net,
            revenus_exceptionnels=total_exc,
            charges_fixes=charges,
            produits_epargne=produits,
            budgets_variables=bv,
            depenses=dep,
            mois=m,
            annee=annee,
            epargnes_exceptionnelles=ee,
            items_previsionnel=prev,
            solde_reporte=cumul,        # ← chain: replay as displayed
            allocations_projet=alloc,
        )
        displayed = s.solde_disponible  # exactly what the user saw for month m
        has_activity = bool(dep or exc or ee or alloc)
        if has_activity or displayed < 0:
            # Active month (real entries) or genuinely negative: update balance.
            cumul = displayed
        # else: no entries, positive balance → neutral, keep cumul unchanged.
    return cumul


def show() -> None:
    mois, annee = _current_month_year()

    st.markdown(
        '<div class="page-header"><h1>📅 Vue Mensuelle</h1>'
        "<p>Charges fixes, épargne et dépenses variables du mois sélectionné.</p></div>",
        unsafe_allow_html=True,
    )

    # ── Month navigator ────────────────────────────────────────────────────
    nav_l, nav_c, nav_r = st.columns([1, 4, 1])
    with nav_l:
        if st.button("◀ Mois précédent"):
            if mois == 1:
                st.session_state["mois_selectionne"] = 12
                st.session_state["annee_selectionnee"] = annee - 1
            else:
                st.session_state["mois_selectionne"] = mois - 1
            st.rerun()
    with nav_c:
        mois_choisi = st.selectbox(
            "Mois",
            options=list(range(1, 13)),
            format_func=lambda m: MOIS[m - 1],
            index=mois - 1,
            label_visibility="collapsed",
        )
        if mois_choisi != mois:
            st.session_state["mois_selectionne"] = mois_choisi
            st.rerun()
    with nav_r:
        if st.button("Mois suivant ▶"):
            if mois == 12:
                st.session_state["mois_selectionne"] = 1
                st.session_state["annee_selectionnee"] = annee + 1
            else:
                st.session_state["mois_selectionne"] = mois + 1
            st.rerun()

    st.markdown(f"### {MOIS[mois - 1]} {annee}")

    # ── Load data ──────────────────────────────────────────────────────────
    params = db.get_parametres()
    charges = db.get_charges_fixes()
    produits = db.get_produits_epargne()
    categories = db.get_categories()
    bv_list = db.get_budgets_variables(mois, annee)
    budgets_defaut = db.get_budgets_defaut()
    # Augment bv_list with default budgets for categories not yet set this month
    _bv_set = {bv.categorie_id for bv in bv_list}
    for _cat in categories:
        if _cat.id not in _bv_set and budgets_defaut.get(_cat.id, 0.0) > 0:
            bv_list.append(BudgetVariable(
                id=0, mois=mois, annee=annee,
                categorie_id=_cat.id,
                montant_budgete=budgets_defaut[_cat.id],
            ))
    dep_list = db.get_depenses(mois, annee)
    exc_list = db.get_revenus_exceptionnels(mois, annee)
    ee_list = db.get_epargne_exceptionnelles(mois, annee)
    alloc_list = db.get_allocations_projet(mois, annee)
    prev_list = [p for p in db.get_previsionnel(annee) if p.mois_prevu == mois]
    total_exc = sum(r.montant for r in exc_list)

    solde_reporte = _calcul_solde_reporte(mois, annee, params, charges, produits, budgets_defaut)

    solde = calculs.calcul_solde_mensuel(
        salaire=params.salaire_net,
        revenus_exceptionnels=total_exc,
        charges_fixes=charges,
        produits_epargne=produits,
        budgets_variables=bv_list,
        depenses=dep_list,
        mois=mois,
        annee=annee,
        epargnes_exceptionnelles=ee_list,
        items_previsionnel=prev_list,
        solde_reporte=solde_reporte,
        allocations_projet=alloc_list,
    )


    col_left, col_right = st.columns(2)

    # ══ Left block — fixed charges ══════════════════════════════════════════
    with col_left:
        st.markdown('<div class="section-header">🔒 Charges fixes & solde</div>', unsafe_allow_html=True)

        st.markdown(f"""
| Poste | Montant |
|---|---:|
| 💰 Salaire net | **{params.salaire_net:,.0f} €** |
| 🎁 Revenus exceptionnels | {total_exc:,.0f} € |
| **Total revenus** | **{solde.total_revenus:,.0f} €** |
""")
        if charges:
            rows = "\n".join(
                f"| {cf.libelle} | -{cf.montant_mensuel:,.0f} € |"
                for cf in charges
            )
            st.markdown(f"""
| Charge | Montant mensuel |
|---|---:|
{rows}
| **Total charges fixes** | **-{solde.total_charges_fixes:,.0f} €** |
""")
        else:
            st.info("Aucune charge fixe configurée.")

        if produits:
            ep_rows = "\n".join(
                f"| {pe.produit} | -{pe.versement_mensuel:,.0f} €|"
                for pe in produits
            )
            st.markdown(f"""
| Épargne | Versement |
|---|---:|
{ep_rows}
| **Total épargne** | **-{solde.total_epargne:,.0f} €** |
""")

        if solde.total_epargne_exceptionnelle > 0:
            st.markdown(
                f"<div style='font-size:13px;color:#8E44AD;margin-top:4px'>"
                f"🎯 Épargne exceptionnelle : <strong>-{solde.total_epargne_exceptionnelle:,.0f} €</strong></div>",
                unsafe_allow_html=True,
            )

        if solde.total_variables_reel > 0:
            st.markdown(
                f"<div style='font-size:13px;color:#E67E22;margin-top:4px'>"
                f"🧾 Dépenses variables réelles : <strong>-{solde.total_variables_reel:,.0f} €</strong></div>",
                unsafe_allow_html=True,
            )

        if solde.total_allocations_projet > 0:
            st.markdown(
                f"<div style='font-size:13px;color:#2980B9;margin-top:4px'>"
                f"💡 Allocations projets : <strong>-{solde.total_allocations_projet:,.0f} €</strong></div>",
                unsafe_allow_html=True,
            )

        # Trois cartes KPI toujours affichées côte à côte
        kpi_cols = st.columns(3)
        solde_color = "#27AE60" if solde.solde_disponible >= 0 else "#E74C3C"
        budget_color = "#2980B9" if solde.budget_projete >= 0 else "#E74C3C"
        if solde.solde_reporte > 0:
            reporte_color, reporte_label = "#27AE60", "📈 SURPLUS REPORTÉ"
        elif solde.solde_reporte < 0:
            reporte_color, reporte_label = "#E74C3C", "⚠️ DÉFICIT REPORTÉ"
        else:
            reporte_color, reporte_label = "#7F8C8D", "↔ SOLDE REPORTÉ"
        with kpi_cols[0]:
            st.markdown(
                f"<div style='background:{solde_color};color:white;border-radius:10px;"
                f"padding:12px 10px;text-align:center;margin-top:12px'>"
                f"<div style='font-size:11px;font-weight:600;opacity:.9'>✦ SOLDE DISPONIBLE</div>"
                f"<div style='font-size:22px;font-weight:700'>{solde.solde_disponible:,.0f} €</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
        with kpi_cols[1]:
            st.markdown(
                f"<div style='background:{budget_color};color:white;border-radius:10px;"
                f"padding:12px 10px;text-align:center;margin-top:12px'>"
                f"<div style='font-size:11px;font-weight:600;opacity:.9'>📊 BUDGET PROJETÉ</div>"
                f"<div style='font-size:22px;font-weight:700'>{solde.budget_projete:,.0f} €</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
        with kpi_cols[2]:
            st.markdown(
                f"<div style='background:{reporte_color};color:white;border-radius:10px;"
                f"padding:12px 10px;text-align:center;margin-top:12px'>"
                f"<div style='font-size:11px;font-weight:600;opacity:.9'>{reporte_label}</div>"
                f"<div style='font-size:22px;font-weight:700'>{solde.solde_reporte:+,.0f} €</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

        # Deux cartes "mois seul" (hors report)
        solde_mois = solde.solde_disponible - solde.solde_reporte
        budget_mois = solde.budget_projete - solde.solde_reporte
        st.markdown(
            "<div style='font-size:11px;color:#95A5A6;text-align:center;"
            "margin-top:14px;margin-bottom:2px'>— Ce mois uniquement —</div>",
            unsafe_allow_html=True,
        )
        mois_cols = st.columns(2)
        sm_color = "#27AE60" if solde_mois >= 0 else "#E74C3C"
        bm_color = "#2980B9" if budget_mois >= 0 else "#E74C3C"
        with mois_cols[0]:
            st.markdown(
                f"<div style='background:{sm_color};color:white;border-radius:10px;"
                f"padding:12px 10px;text-align:center'>"
                f"<div style='font-size:11px;font-weight:600;opacity:.9'>📅 SOLDE MENSUEL</div>"
                f"<div style='font-size:22px;font-weight:700'>{solde_mois:,.0f} €</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
        with mois_cols[1]:
            st.markdown(
                f"<div style='background:{bm_color};color:white;border-radius:10px;"
                f"padding:12px 10px;text-align:center'>"
                f"<div style='font-size:11px;font-weight:600;opacity:.9'>🗓️ BUDGET MENSUEL PROJETÉ</div>"
                f"<div style='font-size:22px;font-weight:700'>{budget_mois:,.0f} €</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

        # ── Revenus exceptionnels ──────────────────────────────────────────
        st.markdown(
            '<div class="section-header" style="margin-top:20px">🎁 Revenus exceptionnels</div>',
            unsafe_allow_html=True,
        )
        with st.form("form_exc"):
            fc1, fc2 = st.columns([3, 2])
            with fc1:
                exc_lib = st.text_input("Libellé (prime, remb., …)")
            with fc2:
                exc_mt = st.number_input("Montant (€)", min_value=0.0, step=10.0)
            if st.form_submit_button("Ajouter"):
                if exc_lib and exc_mt > 0:
                    db.save_revenu_exceptionnel(RevenuExceptionnel(
                        id=0, mois=mois, annee=annee, libelle=exc_lib, montant=exc_mt
                    ))
                    st.rerun()
        for exc in exc_list:
            c1, c2 = st.columns([4, 1])
            c1.markdown(f"🎁 {exc.libelle} — **{exc.montant:,.0f} €**")
            if c2.button("🗑️", key=f"del_exc_{exc.id}"):
                db.delete_revenu_exceptionnel(exc.id)
                st.rerun()

        # ── Épargne exceptionnelle ─────────────────────────────────────────
        st.markdown(
            '<div class="section-header" style="margin-top:20px">🎯 Épargne exceptionnelle</div>',
            unsafe_allow_html=True,
        )
        produits_all = db.get_produits_epargne(actif_only=True)
        if not produits_all:
            st.info("Aucun produit d'épargne actif. Configurez-en dans les Paramètres.")
        else:
            produit_map = {pe.id: pe for pe in produits_all}
            with st.form("form_ee"):
                ee1, ee2 = st.columns([3, 2])
                with ee1:
                    ee_lib = st.text_input("Libellé (ex: versement PEA)")
                    ee_produit_id = st.selectbox(
                        "Produit d'épargne",
                        options=[pe.id for pe in produits_all],
                        format_func=lambda pid: produit_map[pid].produit,
                    )
                with ee2:
                    ee_mt = st.number_input("Montant (€)", min_value=0.0, step=50.0, key="ee_mt")
                if st.form_submit_button("Ajouter"):
                    if ee_lib and ee_mt > 0:
                        db.save_epargne_exceptionnelle(
                            EpargneExceptionnelle(
                                id=0,
                                mois=mois,
                                annee=annee,
                                produit_epargne_id=ee_produit_id,
                                libelle=ee_lib,
                                montant=ee_mt,
                            ),
                            delta=ee_mt,
                        )
                        st.rerun()
            for ee in ee_list:
                pe_nom = produit_map.get(ee.produit_epargne_id)
                pe_label = pe_nom.produit if pe_nom else f"#{ee.produit_epargne_id}"
                c1, c2 = st.columns([4, 1])
                c1.markdown(f"🎯 {ee.libelle} → {pe_label} — **{ee.montant:,.0f} €**")
                if c2.button("🗑️", key=f"del_ee_{ee.id}"):
                    db.delete_epargne_exceptionnelle(ee.id)
                    st.rerun()

    # ══ Right block — variable budget ═══════════════════════════════════════
    with col_right:
        st.markdown('<div class="section-header">📊 Dépenses variables</div>', unsafe_allow_html=True)

        bv_map = {bv.categorie_id: bv for bv in bv_list}
        reel_map: dict[int, float] = {}
        for d in dep_list:
            reel_map[d.categorie_id] = reel_map.get(d.categorie_id, 0.0) + d.montant

        if not categories:
            st.info("Aucune catégorie configurée dans les Paramètres.")
        else:
            for cat in categories:
                bv = bv_map.get(cat.id)
                current_budget = float(bv.montant_budgete) if bv else 0.0
                reel = reel_map.get(cat.id, 0.0)

                c1, c2 = st.columns([3, 2])
                with c1:
                    new_budget = st.number_input(
                        f"{cat.icone} {cat.nom}",
                        min_value=0.0,
                        value=current_budget,
                        step=10.0,
                        key=f"bv_{mois}_{annee}_{cat.id}",
                    )
                with c2:
                    st.markdown(
                        f"<div style='margin-top:28px;font-size:13px;color:#7F8C8D'>"
                        f"réel: {reel:,.0f} €</div>",
                        unsafe_allow_html=True,
                    )

                if new_budget != current_budget:
                    db.save_budget_variable(BudgetVariable(
                        id=bv.id if bv else 0,
                        mois=mois, annee=annee,
                        categorie_id=cat.id,
                        montant_budgete=new_budget,
                    ))

                if new_budget > 0 or reel > 0:
                    st.markdown(
                        budget_bar_html(cat.nom, reel, new_budget, cat.icone),
                        unsafe_allow_html=True,
                    )

            st.markdown("---")
            analyses = calculs.calcul_analyse_budget(categories, bv_list, dep_list)
            total_b = sum(a.budgete for a in analyses)
            total_r = sum(a.reel for a in analyses)
            st.markdown(
                f"**Total budgété :** {total_b:,.0f} € | "
                f"**Total réel :** {total_r:,.0f} € | "
                f"**Écart :** {total_r - total_b:+,.0f} €"
            )

        # ── Dépenses prévisionnelles du mois ──────────────────────────────
        if prev_list:
            st.markdown(
                '<div class="section-header" style="margin-top:20px">📦 Dépenses prévisionnelles</div>',
                unsafe_allow_html=True,
            )
            cat_map = {c.id: c for c in categories}
            for p in prev_list:
                montant_aff = p.montant_reel if p.montant_reel is not None else p.montant_estime
                cat_label = ""
                if p.categorie_id and p.categorie_id in cat_map:
                    c = cat_map[p.categorie_id]
                    cat_label = f" · {c.icone} {c.nom}"
                statut_color = {"Réalisé": "#27AE60", "À venir": "#2980B9", "Annulé": "#95A5A6"}.get(
                    p.statut, "#7F8C8D"
                )
                st.markdown(
                    f"<div style='border-left:4px solid {statut_color};"
                    f"padding:6px 10px;margin-bottom:6px;border-radius:0 6px 6px 0'>"
                    f"<strong>{p.libelle}</strong>{cat_label} — "
                    f"<span style='color:{statut_color}'>{montant_aff:,.0f} €</span> "
                    f"<span style='font-size:11px;color:#95A5A6'>({p.statut})</span></div>",
                    unsafe_allow_html=True,
                )
            st.caption(f"Total prévisionnel : **{solde.total_previsionnel:,.0f} €**")

        # ── Allocation du surplus ──────────────────────────────────────────
        if solde.solde_disponible > 0:
            projets = db.get_projets(actif_only=True)
            if projets:
                st.markdown(
                    '<div class="section-header" style="margin-top:20px">💡 Allouer le surplus</div>',
                    unsafe_allow_html=True,
                )
                st.caption(
                    f"Surplus disponible ce mois : **{solde.solde_disponible:,.0f} €**. "
                    "Vous pouvez en affecter une partie à vos projets."
                )
                allocs_existantes = {
                    a.projet_id: a for a in db.get_allocations_projet(mois, annee)
                }
                projet_map = {p.id: p for p in projets}
                with st.form("form_alloc"):
                    proj_id = st.selectbox(
                        "Projet",
                        options=[p.id for p in projets],
                        format_func=lambda pid: projet_map[pid].nom,
                    )
                    alloc_mt = st.number_input(
                        "Montant à allouer (€)",
                        min_value=0.0,
                        max_value=float(solde.solde_disponible),
                        step=50.0,
                    )
                    alloc_note = st.text_input("Note (optionnel)")
                    if st.form_submit_button("Allouer"):
                        if alloc_mt > 0:
                            existing = allocs_existantes.get(proj_id)
                            db.save_allocation_projet(AllocationProjet(
                                id=existing.id if existing else 0,
                                mois=mois,
                                annee=annee,
                                projet_id=proj_id,
                                montant=alloc_mt,
                                note=alloc_note,
                            ))
                            st.rerun()

                allocs = db.get_allocations_projet(mois, annee)
                for alloc in allocs:
                    proj = projet_map.get(alloc.projet_id)
                    nom = proj.nom if proj else f"#{alloc.projet_id}"
                    pct = min(100.0, proj.montant_alloue / proj.montant_cible * 100) if proj and proj.montant_cible > 0 else 0.0
                    c1, c2 = st.columns([4, 1])
                    c1.markdown(
                        f"💡 **{nom}** — {alloc.montant:,.0f} € alloués "
                        f"({proj.montant_alloue:,.0f}/{proj.montant_cible:,.0f} € · {pct:.0f}%)"
                        + (f" — _{alloc.note}_" if alloc.note else "")
                    )
                    if c2.button("🗑️", key=f"del_alloc_{alloc.id}"):
                        db.delete_allocation_projet(alloc.id)
                        st.rerun()
