"""Business logic and financial calculations.

All functions are pure (no I/O) and operate on the domain models defined in
``gestion_dashboard.models.budget``.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from gestion_dashboard.models.budget import (
    AllocationProjet,
    AnalyseBudget,
    BienImmobilier,
    BudgetVariable,
    CashflowImmo,
    CategorieDepense,
    ChargeFix,
    Depense,
    EpargneExceptionnelle,
    KPIAnnuel,
    Parametres,
    PlanningDepense,
    ProduitEpargne,
    Repartition503020,
    SoldeMensuel,
)


def calcul_repartition_503020(
    salaire: float,
    taux_besoins: float = 0.50,
    taux_loisirs: float = 0.30,
    taux_epargne: float = 0.20,
) -> Repartition503020:
    """
    Compute the 50/30/20 budget allocation.

    Parameters
    ----------
    salaire : float
        Monthly net salary.
    taux_besoins, taux_loisirs, taux_epargne : float
        Allocation ratios (must sum to 1.0 for a coherent plan).

    Returns
    -------
    Repartition503020
        Computed allocations in euros.
    """
    return Repartition503020(
        besoins=salaire * taux_besoins,
        loisirs=salaire * taux_loisirs,
        epargne=salaire * taux_epargne,
        salaire=salaire,
        taux_besoins=taux_besoins,
        taux_loisirs=taux_loisirs,
        taux_epargne=taux_epargne,
    )


def calcul_solde_mensuel(
    salaire: float,
    revenus_exceptionnels: float,
    charges_fixes: List[ChargeFix],
    produits_epargne: List[ProduitEpargne],
    budgets_variables: List[BudgetVariable],
    depenses: List[Depense],
    mois: int,
    annee: int,
    epargnes_exceptionnelles: Optional[List[EpargneExceptionnelle]] = None,
    items_previsionnel: Optional[List[PlanningDepense]] = None,
    solde_reporte: float = 0.0,
    allocations_projet: Optional[List[AllocationProjet]] = None,
) -> SoldeMensuel:
    """
    Compute the monthly balance.

    Parameters
    ----------
    salaire : float
        Monthly net salary.
    revenus_exceptionnels : float
        Sum of exceptional revenues for the month.
    charges_fixes : List[ChargeFix]
        Active fixed charges.
    produits_epargne : List[ProduitEpargne]
        Active savings products.
    budgets_variables : List[BudgetVariable]
        Variable budgets for the month.
    depenses : List[Depense]
        Actual expenses for the month.
    mois : int
        Month number (1–12).
    annee : int
        Year.
    epargnes_exceptionnelles : List[EpargneExceptionnelle], optional
        One-time savings contributions for this month.
    items_previsionnel : List[PlanningDepense], optional
        Planned large expenses due this month (estimated amounts used).
    solde_reporte : float
        Running balance carried forward from prior months (positive = surplus,
        negative = deficit). Resets to 0 on 1 January each year.
    allocations_projet : List[AllocationProjet], optional
        Surplus amounts allocated to personal projects this month.

    Returns
    -------
    SoldeMensuel
        Computed monthly balance.
    """
    total_revenus = salaire + revenus_exceptionnels
    total_charges = sum(cf.montant_mensuel for cf in charges_fixes)
    total_epargne = sum(pe.versement_mensuel for pe in produits_epargne)
    total_budget = sum(bv.montant_budgete for bv in budgets_variables)
    total_reel = sum(d.montant for d in depenses)

    total_ee = sum(ee.montant for ee in (epargnes_exceptionnelles or []))
    total_prev = sum(
        (p.montant_reel if p.montant_reel is not None else p.montant_estime)
        for p in (items_previsionnel or [])
    )
    total_alloc = sum(a.montant for a in (allocations_projet or []))

    # Envelope available before variable spending (fixed costs + savings deducted)
    solde_avant_variables = total_revenus - total_charges - total_epargne - total_ee

    # True remaining balance: deduct actual spending, project allocations and carried deficit
    solde_disponible = solde_avant_variables - total_reel - total_alloc + solde_reporte

    return SoldeMensuel(
        mois=mois,
        annee=annee,
        total_revenus=total_revenus,
        total_charges_fixes=total_charges,
        total_epargne=total_epargne,
        total_variables_budgete=total_budget,
        total_variables_reel=total_reel,
        solde_disponible=solde_disponible,
        budget_projete=solde_avant_variables + solde_reporte - total_budget - total_alloc,
        total_epargne_exceptionnelle=total_ee,
        total_previsionnel=total_prev,
        solde_reporte=solde_reporte,
        total_allocations_projet=total_alloc,
    )


def calcul_kpis_annuels(
    parametres: Parametres,
    soldes_mensuels: List[SoldeMensuel],
    produits_epargne: List[ProduitEpargne],
) -> KPIAnnuel:
    """
    Aggregate annual KPIs from monthly balances.

    Parameters
    ----------
    parametres : Parametres
        Global configuration (unused today; kept for future ratio comparisons).
    soldes_mensuels : List[SoldeMensuel]
        List of monthly balances (up to 12 items).
    produits_epargne : List[ProduitEpargne]
        Active savings products.

    Returns
    -------
    KPIAnnuel
        Computed annual KPIs.
    """
    n = len(soldes_mensuels) or 1
    revenus = sum(s.total_revenus for s in soldes_mensuels)
    charges = sum(s.total_charges_fixes for s in soldes_mensuels)
    epargne_m = sum(pe.versement_mensuel for pe in produits_epargne)
    reste = revenus - charges - epargne_m * n
    variables_budget = sum(s.total_variables_budgete for s in soldes_mensuels)
    variables_reel = sum(s.total_variables_reel for s in soldes_mensuels)
    solde_moyen = sum(s.solde_disponible for s in soldes_mensuels) / n
    total_cumule = sum(pe.solde_actuel for pe in produits_epargne)

    return KPIAnnuel(
        revenus_annuels=revenus,
        charges_fixes_annuelles=charges,
        reste_apres_fixes_epargne=reste,
        variables_budgetees=variables_budget,
        variables_reelles=variables_reel,
        solde_mensuel_moyen=solde_moyen,
        epargne_mensuelle=epargne_m,
        projection_epargne_annuelle=epargne_m * 12,
        total_epargne_cumulee=total_cumule,
    )


def calcul_analyse_budget(
    categories: List[CategorieDepense],
    budgets_variables: List[BudgetVariable],
    depenses: List[Depense],
) -> List[AnalyseBudget]:
    """
    Compare budget vs actual spending per category.

    Parameters
    ----------
    categories : List[CategorieDepense]
        All expense categories.
    budgets_variables : List[BudgetVariable]
        Budgeted amounts per category.
    depenses : List[Depense]
        Actual expenses.

    Returns
    -------
    List[AnalyseBudget]
        One analysis row per category.
    """
    budget_map: Dict[int, float] = {bv.categorie_id: bv.montant_budgete for bv in budgets_variables}
    reel_map: Dict[int, float] = {}
    for d in depenses:
        reel_map[d.categorie_id] = reel_map.get(d.categorie_id, 0.0) + d.montant

    analyses: List[AnalyseBudget] = []
    for cat in categories:
        budgete = budget_map.get(cat.id, 0.0)
        reel = reel_map.get(cat.id, 0.0)
        ecart = reel - budgete
        if budgete > 0:
            pct = reel / budgete * 100
        elif reel > 0:
            pct = 100.0
        else:
            pct = 0.0
        analyses.append(
            AnalyseBudget(
                categorie_id=cat.id,
                categorie_nom=cat.nom,
                categorie_icone=cat.icone,
                categorie_couleur=cat.couleur,
                budgete=budgete,
                reel=reel,
                ecart=ecart,
                pourcentage_consomme=pct,
            )
        )
    return analyses


def calcul_cashflow_immobilier(bien: BienImmobilier) -> CashflowImmo:
    """
    Compute the monthly cashflow for a rental property.

    Parameters
    ----------
    bien : BienImmobilier
        Real-estate asset data.

    Returns
    -------
    CashflowImmo
        Detailed monthly cashflow breakdown.
    """
    loyer = bien.loyer_mensuel
    vacance = loyer * (bien.taux_vacance / 100)
    loyer_net = loyer - vacance
    taxe_m = bien.taxe_fonciere / 12
    assurance_m = bien.assurance_annuelle / 12
    cashflow = (
        loyer_net
        - bien.mensualite_credit
        - bien.charges_proprietaire
        - taxe_m
        - assurance_m
        - bien.frais_gestion
    )
    valeur = bien.valeur_actuelle or bien.valeur_achat
    rentabilite_brute = (loyer * 12 / valeur * 100) if valeur > 0 else 0.0
    charges_annuelles = (
        bien.charges_proprietaire * 12
        + bien.taxe_fonciere
        + bien.assurance_annuelle
        + bien.frais_gestion * 12
        + vacance * 12
    )
    rentabilite_nette = ((loyer * 12 - charges_annuelles) / valeur * 100) if valeur > 0 else 0.0

    return CashflowImmo(
        bien_id=bien.id,
        loyer_percu=loyer_net,
        mensualite_credit=bien.mensualite_credit,
        charges_proprietaire=bien.charges_proprietaire,
        taxe_fonciere_mensuelle=taxe_m,
        assurance_mensuelle=assurance_m,
        frais_gestion=bien.frais_gestion,
        provision_vacance=vacance,
        cashflow_net_mensuel=cashflow,
        cashflow_net_annuel=cashflow * 12,
        rentabilite_brute=rentabilite_brute,
        rentabilite_nette=rentabilite_nette,
    )


def reel_par_envelope(
    repartition: Repartition503020,
    total_charges: float,
    total_epargne: float,
    total_variables: float,
) -> Dict[str, float]:
    """
    Map actual spending into the 50/30/20 envelopes.

    Returns a dict suitable for pie-chart comparison with the theoretical split.

    Parameters
    ----------
    repartition : Repartition503020
        Theoretical allocation.
    total_charges : float
        Sum of fixed charges (mapped to «Besoins»).
    total_epargne : float
        Sum of savings contributions (mapped to «Épargne»).
    total_variables : float
        Sum of variable spending (mapped to «Loisirs & Besoins»).

    Returns
    -------
    Dict[str, float]
        Keys: "Besoins réels", "Loisirs & envies réels", "Épargne réelle".
    """
    return {
        "Besoins réels": total_charges,
        "Loisirs & envies réels": total_variables,
        "Épargne réelle": total_epargne,
    }
