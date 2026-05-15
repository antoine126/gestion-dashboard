"""Savings projection and financial planning calculations."""
from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np

from gestion_dashboard.models.budget import ProduitEpargne


def projection_interes_composes(
    solde_initial: float,
    versement_mensuel: float,
    taux_annuel: float,
    duree_annees: int,
) -> float:
    """
    Compound-interest projection (monthly compounding).

    Parameters
    ----------
    solde_initial : float
        Starting balance (€).
    versement_mensuel : float
        Fixed monthly contribution (€).
    taux_annuel : float
        Annual interest rate as a percentage (e.g. 5.0 for 5 %).
    duree_annees : int
        Projection horizon in years.

    Returns
    -------
    float
        Projected balance after ``duree_annees`` years.
    """
    r = taux_annuel / 100 / 12
    n = duree_annees * 12
    if r == 0:
        return solde_initial + versement_mensuel * n
    return float(
        solde_initial * (1 + r) ** n
        + versement_mensuel * ((1 + r) ** n - 1) / r
    )


def projection_serie(
    solde_initial: float,
    versement_mensuel: float,
    taux_annuel: float,
    horizons: Optional[List[int]] = None,
) -> Dict[int, float]:
    """
    Compute compound-interest projections for multiple time horizons.

    Parameters
    ----------
    solde_initial : float
        Starting balance (€).
    versement_mensuel : float
        Fixed monthly contribution (€).
    taux_annuel : float
        Annual interest rate as a percentage.
    horizons : List[int], optional
        Years to project (default: [1, 3, 5, 10, 20, 30]).

    Returns
    -------
    Dict[int, float]
        Mapping of horizon year → projected balance.
    """
    if horizons is None:
        horizons = [1, 3, 5, 10, 20, 30]
    return {
        h: projection_interes_composes(solde_initial, versement_mensuel, taux_annuel, h)
        for h in horizons
    }


def projection_annuelle_cumul(
    solde_initial: float,
    versement_mensuel: float,
    taux_annuel: float,
    duree_annees: int,
) -> List[float]:
    """
    Return year-by-year projected balances from year 0 to ``duree_annees``.

    Parameters
    ----------
    solde_initial : float
        Starting balance (€).
    versement_mensuel : float
        Fixed monthly contribution (€).
    taux_annuel : float
        Annual interest rate as a percentage.
    duree_annees : int
        Total projection horizon in years.

    Returns
    -------
    List[float]
        Projected balance at the end of each year (index 0 = year 0 = initial).
    """
    result = [solde_initial]
    for year in range(1, duree_annees + 1):
        result.append(
            projection_interes_composes(solde_initial, versement_mensuel, taux_annuel, year)
        )
    return result


def versement_necessaire_pour_objectif(
    objectif: float,
    solde_actuel: float,
    taux_annuel: float,
    duree_mois: int,
) -> float:
    """
    Compute the monthly contribution required to reach a savings target.

    Parameters
    ----------
    objectif : float
        Target balance (€).
    solde_actuel : float
        Current balance (€).
    taux_annuel : float
        Annual interest rate as a percentage.
    duree_mois : int
        Duration in months.

    Returns
    -------
    float
        Required monthly contribution (€), or 0.0 if target is already met.
    """
    r = taux_annuel / 100 / 12
    if r > 0:
        capital_futur = solde_actuel * (1 + r) ** duree_mois
    else:
        capital_futur = solde_actuel
    reste = objectif - capital_futur
    if reste <= 0:
        return 0.0
    if r == 0:
        return reste / duree_mois
    return float(reste / (((1 + r) ** duree_mois - 1) / r))


def calcul_patrimoine_financier(produits: List[ProduitEpargne]) -> Dict[str, float]:
    """
    Aggregate total portfolio balance by product type.

    Parameters
    ----------
    produits : List[ProduitEpargne]
        Active savings products.

    Returns
    -------
    Dict[str, float]
        Mapping of product type → total balance (€).
    """
    patrimoine: Dict[str, float] = {}
    for p in produits:
        patrimoine[p.type_produit] = patrimoine.get(p.type_produit, 0.0) + p.solde_actuel
    return patrimoine
