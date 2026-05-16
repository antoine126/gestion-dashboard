"""Data models for the budget application.

Pydantic BaseModel  → external / persistence layer (Parquet I/O).
@dataclass          → internal computation results.
"""
from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Optional

from pydantic import BaseModel, Field


# ─── Pydantic models (persistence) ───────────────────────────────────────────

class User(BaseModel):
    """Application user account."""

    id: int = 0
    username: str = ""
    display_name: str = ""
    password_hash: str = ""
    created_at: str = Field(default_factory=lambda: datetime.datetime.now().isoformat())
    last_login: str = ""
    is_active: bool = True


class Parametres(BaseModel):
    """Global user configuration."""

    id: int = 1
    salaire_net: float = 0.0
    annee: int = datetime.date.today().year
    taux_besoins: float = 0.50
    taux_loisirs: float = 0.30
    taux_epargne: float = 0.20
    created_at: str = Field(default_factory=lambda: datetime.datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.datetime.now().isoformat())


class ChargeFix(BaseModel):
    """A fixed monthly charge (rent, subscription, loan, …)."""

    id: int = 0
    libelle: str = ""
    montant: float = 0.0
    frequence: str = "Mensuelle"
    categorie: str = ""
    actif: bool = True

    @property
    def montant_mensuel(self) -> float:
        """Return the monthly equivalent amount based on frequency."""
        if self.frequence == "Trimestrielle":
            return self.montant / 3
        if self.frequence == "Annuelle":
            return self.montant / 12
        return self.montant


class ProduitEpargne(BaseModel):
    """A savings product (Livret A, PEA, assurance-vie, …)."""

    id: int = 0
    produit: str = ""
    type_produit: str = "Livret"
    solde_actuel: float = 0.0
    versement_mensuel: float = 0.0
    taux_annuel: float = 0.0
    objectif: Optional[float] = None
    actif: bool = True


class CategorieDepense(BaseModel):
    """A variable expense category."""

    id: int = 0
    nom: str = ""
    icone: str = "📦"
    couleur: str = "#BDC3C7"
    ordre: int = 99


class BudgetVariable(BaseModel):
    """A monthly budget allocation per category."""

    id: int = 0
    mois: int = 1
    annee: int = datetime.date.today().year
    categorie_id: int = 0
    montant_budgete: float = 0.0


class Depense(BaseModel):
    """A single expense journal entry."""

    id: int = 0
    date: str = Field(default_factory=lambda: datetime.date.today().isoformat())
    libelle: str = ""
    categorie_id: int = 0
    montant: float = 0.0
    mode_paiement: str = "Carte bancaire"
    note: str = ""
    mois: int = datetime.date.today().month
    annee: int = datetime.date.today().year


class RevenuExceptionnel(BaseModel):
    """An exceptional revenue item for a given month."""

    id: int = 0
    mois: int = 1
    annee: int = datetime.date.today().year
    libelle: str = ""
    montant: float = 0.0


class PlanningDepense(BaseModel):
    """A planned large expense in the annual forecast."""

    id: int = 0
    annee: int = datetime.date.today().year
    libelle: str = ""
    mois_prevu: int = 1
    montant_estime: float = 0.0
    montant_reel: Optional[float] = None
    statut: str = "À venir"
    note: str = ""
    categorie_id: Optional[int] = None


class EpargneExceptionnelle(BaseModel):
    """A one-time savings contribution linked to a savings product for a given month."""

    id: int = 0
    mois: int = 1
    annee: int = datetime.date.today().year
    produit_epargne_id: int = 0
    libelle: str = ""
    montant: float = 0.0


class Projet(BaseModel):
    """A personal savings project with a target amount and deadline."""

    id: int = 0
    nom: str = ""
    description: str = ""
    montant_cible: float = 0.0
    date_souhaitee: str = ""
    montant_alloue: float = 0.0
    actif: bool = True


class AllocationProjet(BaseModel):
    """A monthly surplus allocation toward a personal project."""

    id: int = 0
    mois: int = 1
    annee: int = datetime.date.today().year
    projet_id: int = 0
    montant: float = 0.0
    note: str = ""


class BienImmobilier(BaseModel):
    """A real-estate asset (primary residence, rental, SCPI, …)."""

    id: int = 0
    nom: str = ""
    adresse: str = ""
    type_bien: str = "Résidence Principale"
    valeur_achat: float = 0.0
    valeur_actuelle: float = 0.0
    date_achat: str = ""
    capital_initial: float = 0.0
    capital_restant_du: float = 0.0
    mensualite_credit: float = 0.0
    taux_credit: float = 0.0
    duree_restante_mois: int = 0
    loyer_mensuel: float = 0.0
    charges_locataire: float = 0.0
    charges_proprietaire: float = 0.0
    taxe_fonciere: float = 0.0
    assurance_annuelle: float = 0.0
    frais_gestion: float = 0.0
    taux_vacance: float = 0.0
    actif: bool = True


# ─── Internal dataclasses (computation results) ──────────────────────────────

@dataclass
class Repartition503020:
    """Result of the 50/30/20 budget split calculation."""

    besoins: float
    loisirs: float
    epargne: float
    salaire: float
    taux_besoins: float
    taux_loisirs: float
    taux_epargne: float


@dataclass
class SoldeMensuel:
    """Computed monthly balance for one month."""

    mois: int
    annee: int
    total_revenus: float
    total_charges_fixes: float
    total_epargne: float
    total_variables_budgete: float
    total_variables_reel: float
    solde_disponible: float
    budget_projete: float
    # v1.1 additions — default to 0 for backward compatibility
    total_epargne_exceptionnelle: float = 0.0
    total_previsionnel: float = 0.0
    solde_reporte: float = 0.0          # positive = surplus, negative = deficit
    total_allocations_projet: float = 0.0


@dataclass
class KPIAnnuel:
    """Aggregated annual KPI values."""

    revenus_annuels: float
    charges_fixes_annuelles: float
    reste_apres_fixes_epargne: float
    variables_budgetees: float
    variables_reelles: float
    solde_mensuel_moyen: float
    epargne_mensuelle: float
    projection_epargne_annuelle: float
    total_epargne_cumulee: float


@dataclass
class AnalyseBudget:
    """Budget vs actual analysis for one category."""

    categorie_id: int
    categorie_nom: str
    categorie_icone: str
    categorie_couleur: str
    budgete: float
    reel: float
    ecart: float
    pourcentage_consomme: float


@dataclass
class CashflowImmo:
    """Monthly cashflow analysis for one real-estate asset."""

    bien_id: int
    loyer_percu: float
    mensualite_credit: float
    charges_proprietaire: float
    taxe_fonciere_mensuelle: float
    assurance_mensuelle: float
    frais_gestion: float
    provision_vacance: float
    cashflow_net_mensuel: float
    cashflow_net_annuel: float
    rentabilite_brute: float
    rentabilite_nette: float
