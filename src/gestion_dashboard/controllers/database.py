"""Parquet-based CRUD operations for the budget application.

Each entity type maps to a dedicated ``<name>.parquet`` file in a
user-specific sub-directory ``data/user_<id>/``.  Files are created on
first access with the correct schema and, where applicable, pre-populated
with sensible default values.

Multi-user isolation uses ``threading.local`` so that each Streamlit
session (one OS thread) has its own active data directory without
interfering with other concurrent sessions.  Call ``set_user_data_dir``
once per session at login; it must be re-called at the beginning of each
Streamlit rerun to ensure the thread-local value is current.
"""
from __future__ import annotations

import datetime
import json
import os
import threading
from typing import List, Optional

import pandas as pd

from gestion_dashboard.models.budget import (
    AllocationProjet,
    BienImmobilier,
    BudgetVariable,
    CategorieDepense,
    ChargeFix,
    Depense,
    EpargneExceptionnelle,
    Parametres,
    PlanningDepense,
    ProduitEpargne,
    Projet,
    RevenuExceptionnel,
)
from gestion_dashboard.models.enums import CATEGORIES_DEFAULT, PRODUITS_EPARGNE_DEFAULT

# Base data directory (shared root; user subdirs live inside)
_PKG_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(_PKG_ROOT, "data")

# Thread-local storage: each Streamlit session thread gets its own active dir
_tl = threading.local()


def set_user_data_dir(user_id: Optional[int]) -> None:
    """Point all DB operations for the current thread to *user_id*'s directory.

    Call this once after a user logs in and again at the top of every
    Streamlit rerun (``main()``), because Streamlit may assign the session
    to a different thread between reruns.

    Pass ``None`` to reset to the legacy shared directory (no-auth mode).
    """
    if user_id is None:
        _tl.data_dir = DATA_DIR
    else:
        d = os.path.join(DATA_DIR, f"user_{user_id}")
        os.makedirs(d, exist_ok=True)
        _tl.data_dir = d


def _active_dir() -> str:
    """Return the data directory for the current thread (session)."""
    return getattr(_tl, "data_dir", DATA_DIR)


# ─── Internal helpers ─────────────────────────────────────────────────────────

def _ensure_data_dir() -> None:
    os.makedirs(_active_dir(), exist_ok=True)


def _path(name: str) -> str:
    return os.path.join(_active_dir(), f"{name}.parquet")


def _load_df(name: str, empty_schema: dict) -> pd.DataFrame:
    """Load a Parquet file or return an empty DataFrame with ``empty_schema``."""
    p = _path(name)
    if os.path.exists(p):
        try:
            return pd.read_parquet(p)
        except Exception:
            pass
    return pd.DataFrame(empty_schema)


def _save_df(name: str, df: pd.DataFrame) -> None:
    _ensure_data_dir()
    df.to_parquet(_path(name), index=False)


def _next_id(df: pd.DataFrame) -> int:
    if df.empty or "id" not in df.columns:
        return 1
    return int(df["id"].max()) + 1


def _upsert(df: pd.DataFrame, row_dict: dict) -> pd.DataFrame:
    """Insert or update a row identified by its ``id``.

    Drops the existing row and re-appends to avoid Pandas dtype coercion
    issues (e.g. NaN being cast into int64 columns).
    """
    rid = row_dict["id"]
    if not df.empty and rid in df["id"].values:
        df = df[df["id"] != rid].reset_index(drop=True)
    df = pd.concat([df, pd.DataFrame([row_dict])], ignore_index=True)
    return df


# ─── Paramètres ───────────────────────────────────────────────────────────────

_PARAMS_SCHEMA = {
    "id": [], "salaire_net": [], "annee": [],
    "taux_besoins": [], "taux_loisirs": [], "taux_epargne": [],
    "created_at": [], "updated_at": [],
}


def get_parametres() -> Parametres:
    """Load global parameters; returns defaults if no file exists yet."""
    df = _load_df("parametres", _PARAMS_SCHEMA)
    if df.empty:
        return Parametres()
    row = df.iloc[0].to_dict()
    # Ensure numeric types survive Parquet round-trip
    for k in ("salaire_net", "taux_besoins", "taux_loisirs", "taux_epargne"):
        row[k] = float(row.get(k, 0) or 0)
    row["annee"] = int(row.get("annee", datetime.date.today().year) or datetime.date.today().year)
    return Parametres(**row)


def save_parametres(p: Parametres) -> None:
    """Persist global parameters (single-row upsert)."""
    p.updated_at = datetime.datetime.now().isoformat()
    df = pd.DataFrame([p.model_dump()])
    _save_df("parametres", df)


# ─── Charges fixes ────────────────────────────────────────────────────────────

_CF_SCHEMA = {"id": [], "libelle": [], "montant": [], "frequence": [], "categorie": [], "actif": []}


def get_charges_fixes(actif_only: bool = True) -> List[ChargeFix]:
    df = _load_df("charges_fixes", _CF_SCHEMA)
    if actif_only and not df.empty:
        df = df[df["actif"].astype(bool)]
    return [ChargeFix(**r) for r in df.to_dict("records")]


def save_charge_fix(cf: ChargeFix) -> ChargeFix:
    df = _load_df("charges_fixes", _CF_SCHEMA)
    if cf.id == 0:
        cf.id = _next_id(df)
    df = _upsert(df, cf.model_dump())
    _save_df("charges_fixes", df)
    return cf


def delete_charge_fix(cid: int) -> None:
    df = _load_df("charges_fixes", _CF_SCHEMA)
    if not df.empty:
        df = df[df["id"] != cid]
    _save_df("charges_fixes", df)


# ─── Produits d'épargne ───────────────────────────────────────────────────────

_EP_SCHEMA = {
    "id": [], "produit": [], "type_produit": [],
    "solde_actuel": [], "versement_mensuel": [],
    "taux_annuel": [], "objectif": [], "actif": [],
}


def get_produits_epargne(actif_only: bool = True) -> List[ProduitEpargne]:
    df = _load_df("epargne", _EP_SCHEMA)
    if df.empty:
        rows = [ProduitEpargne(**d).model_dump() for d in PRODUITS_EPARGNE_DEFAULT]
        df = pd.DataFrame(rows)
        _save_df("epargne", df)
    if actif_only and not df.empty:
        df = df[df["actif"].astype(bool)]
    records = df.to_dict("records")
    for r in records:
        # None survives as NaN through Parquet
        if r.get("objectif") != r.get("objectif"):  # NaN check
            r["objectif"] = None
    return [ProduitEpargne(**r) for r in records]


def save_produit_epargne(pe: ProduitEpargne) -> ProduitEpargne:
    df = _load_df("epargne", _EP_SCHEMA)
    if pe.id == 0:
        pe.id = _next_id(df)
    df = _upsert(df, pe.model_dump())
    _save_df("epargne", df)
    return pe


def delete_produit_epargne(eid: int) -> None:
    df = _load_df("epargne", _EP_SCHEMA)
    if not df.empty:
        df = df[df["id"] != eid]
    _save_df("epargne", df)


# ─── Catégories ───────────────────────────────────────────────────────────────

_CAT_SCHEMA = {"id": [], "nom": [], "icone": [], "couleur": [], "ordre": []}


def get_categories() -> List[CategorieDepense]:
    df = _load_df("categories", _CAT_SCHEMA)
    if df.empty:
        rows = [CategorieDepense(**d).model_dump() for d in CATEGORIES_DEFAULT]
        df = pd.DataFrame(rows)
        _save_df("categories", df)
    return [CategorieDepense(**r) for r in df.sort_values("ordre").to_dict("records")]


def save_categorie(cat: CategorieDepense) -> CategorieDepense:
    df = _load_df("categories", _CAT_SCHEMA)
    if cat.id == 0:
        cat.id = _next_id(df)
    df = _upsert(df, cat.model_dump())
    _save_df("categories", df)
    return cat


def delete_categorie(cid: int) -> None:
    df = _load_df("categories", _CAT_SCHEMA)
    if not df.empty:
        df = df[df["id"] != cid]
    _save_df("categories", df)


# ─── Budgets variables ────────────────────────────────────────────────────────

_BV_SCHEMA = {"id": [], "mois": [], "annee": [], "categorie_id": [], "montant_budgete": []}


def get_budgets_variables(mois: int, annee: int) -> List[BudgetVariable]:
    df = _load_df("budgets_variables", _BV_SCHEMA)
    if not df.empty:
        df = df[(df["mois"] == mois) & (df["annee"] == annee)]
    return [BudgetVariable(**r) for r in df.to_dict("records")]


def get_all_budgets_variables(annee: int) -> List[BudgetVariable]:
    df = _load_df("budgets_variables", _BV_SCHEMA)
    if not df.empty:
        df = df[df["annee"] == annee]
    return [BudgetVariable(**r) for r in df.to_dict("records")]


def save_budget_variable(bv: BudgetVariable) -> BudgetVariable:
    df = _load_df("budgets_variables", _BV_SCHEMA)
    # Upsert by (mois, annee, categorie_id)
    if not df.empty:
        mask = (
            (df["mois"] == bv.mois)
            & (df["annee"] == bv.annee)
            & (df["categorie_id"] == bv.categorie_id)
        )
        if mask.any():
            bv.id = int(df.loc[mask, "id"].iloc[0])
            df.loc[mask, "montant_budgete"] = bv.montant_budgete
            _save_df("budgets_variables", df)
            return bv
    if bv.id == 0:
        bv.id = _next_id(df)
    df = pd.concat([df, pd.DataFrame([bv.model_dump()])], ignore_index=True)
    _save_df("budgets_variables", df)
    return bv


# ─── Journal des dépenses ─────────────────────────────────────────────────────

_DEP_SCHEMA = {
    "id": [], "date": [], "libelle": [], "categorie_id": [],
    "montant": [], "mode_paiement": [], "note": [], "mois": [], "annee": [],
}


def get_depenses(mois: int, annee: int) -> List[Depense]:
    df = _load_df("journal_depenses", _DEP_SCHEMA)
    if not df.empty:
        df = df[(df["mois"] == mois) & (df["annee"] == annee)]
        df = df.sort_values("date", ascending=False)
    return [Depense(**r) for r in df.to_dict("records")]


def get_all_depenses(annee: int) -> List[Depense]:
    df = _load_df("journal_depenses", _DEP_SCHEMA)
    if not df.empty:
        df = df[df["annee"] == annee]
    return [Depense(**r) for r in df.to_dict("records")]


def save_depense(d: Depense) -> Depense:
    df = _load_df("journal_depenses", _DEP_SCHEMA)
    if d.id == 0:
        d.id = _next_id(df)
    df = _upsert(df, d.model_dump())
    _save_df("journal_depenses", df)
    return d


def delete_depense(did: int) -> None:
    df = _load_df("journal_depenses", _DEP_SCHEMA)
    if not df.empty:
        df = df[df["id"] != did]
    _save_df("journal_depenses", df)


# ─── Revenus exceptionnels ────────────────────────────────────────────────────

_RE_SCHEMA = {"id": [], "mois": [], "annee": [], "libelle": [], "montant": []}


def get_revenus_exceptionnels(mois: int, annee: int) -> List[RevenuExceptionnel]:
    df = _load_df("revenus_exceptionnels", _RE_SCHEMA)
    if not df.empty:
        df = df[(df["mois"] == mois) & (df["annee"] == annee)]
    return [RevenuExceptionnel(**r) for r in df.to_dict("records")]


def save_revenu_exceptionnel(re: RevenuExceptionnel) -> RevenuExceptionnel:
    df = _load_df("revenus_exceptionnels", _RE_SCHEMA)
    if re.id == 0:
        re.id = _next_id(df)
    df = _upsert(df, re.model_dump())
    _save_df("revenus_exceptionnels", df)
    return re


def delete_revenu_exceptionnel(rid: int) -> None:
    df = _load_df("revenus_exceptionnels", _RE_SCHEMA)
    if not df.empty:
        df = df[df["id"] != rid]
    _save_df("revenus_exceptionnels", df)


# ─── Prévisionnel annuel ──────────────────────────────────────────────────────

_PD_SCHEMA = {
    "id": [], "annee": [], "libelle": [], "mois_prevu": [],
    "montant_estime": [], "montant_reel": [], "statut": [], "note": [],
    "categorie_id": [],
}


def get_previsionnel(annee: int) -> List[PlanningDepense]:
    df = _load_df("previsionnel", _PD_SCHEMA)
    # backward compat: old Parquet files may not have categorie_id
    if "categorie_id" not in df.columns:
        df["categorie_id"] = None
    if not df.empty:
        df = df[df["annee"] == annee]
    records = df.to_dict("records")
    for r in records:
        if r.get("montant_reel") != r.get("montant_reel"):
            r["montant_reel"] = None
        if r.get("categorie_id") != r.get("categorie_id"):  # NaN check
            r["categorie_id"] = None
    return [PlanningDepense(**r) for r in records]


def save_planning_depense(pd_item: PlanningDepense) -> PlanningDepense:
    df = _load_df("previsionnel", _PD_SCHEMA)
    if pd_item.id == 0:
        pd_item.id = _next_id(df)
    df = _upsert(df, pd_item.model_dump())
    _save_df("previsionnel", df)
    return pd_item


def delete_planning_depense(pid: int) -> None:
    df = _load_df("previsionnel", _PD_SCHEMA)
    if not df.empty:
        df = df[df["id"] != pid]
    _save_df("previsionnel", df)


# ─── Biens immobiliers ────────────────────────────────────────────────────────

_BI_SCHEMA = {
    "id": [], "nom": [], "adresse": [], "type_bien": [],
    "valeur_achat": [], "valeur_actuelle": [], "date_achat": [],
    "capital_initial": [], "capital_restant_du": [], "mensualite_credit": [],
    "taux_credit": [], "duree_restante_mois": [], "loyer_mensuel": [],
    "charges_locataire": [], "charges_proprietaire": [], "taxe_fonciere": [],
    "assurance_annuelle": [], "frais_gestion": [], "taux_vacance": [], "actif": [],
}


def get_biens_immobiliers(actif_only: bool = True) -> List[BienImmobilier]:
    df = _load_df("biens_immobiliers", _BI_SCHEMA)
    if actif_only and not df.empty:
        df = df[df["actif"].astype(bool)]
    return [BienImmobilier(**r) for r in df.to_dict("records")]


def save_bien_immobilier(bi: BienImmobilier) -> BienImmobilier:
    df = _load_df("biens_immobiliers", _BI_SCHEMA)
    if bi.id == 0:
        bi.id = _next_id(df)
    df = _upsert(df, bi.model_dump())
    _save_df("biens_immobiliers", df)
    return bi


def delete_bien_immobilier(bid: int) -> None:
    df = _load_df("biens_immobiliers", _BI_SCHEMA)
    if not df.empty:
        df = df[df["id"] != bid]
    _save_df("biens_immobiliers", df)


# ─── Épargne exceptionnelle ───────────────────────────────────────────────────

_EE_SCHEMA = {
    "id": [], "mois": [], "annee": [],
    "produit_epargne_id": [], "libelle": [], "montant": [],
}


def get_epargne_exceptionnelles(mois: int, annee: int) -> List[EpargneExceptionnelle]:
    df = _load_df("epargne_exceptionnelle", _EE_SCHEMA)
    if not df.empty:
        df = df[(df["mois"] == mois) & (df["annee"] == annee)]
    return [EpargneExceptionnelle(**r) for r in df.to_dict("records")]


def save_epargne_exceptionnelle(ee: EpargneExceptionnelle, delta: float = 0.0) -> EpargneExceptionnelle:
    """Persist an exceptional saving and adjust the linked product's balance.

    Parameters
    ----------
    ee : EpargneExceptionnelle
        The record to save (id==0 means new).
    delta : float
        Net amount to add to `ProduitEpargne.solde_actuel` (positive on
        insert, negative on edit if the amount changed).
    """
    df = _load_df("epargne_exceptionnelle", _EE_SCHEMA)
    if ee.id == 0:
        ee.id = _next_id(df)
    df = _upsert(df, ee.model_dump())
    _save_df("epargne_exceptionnelle", df)

    # Side effect: update linked savings product balance
    if delta != 0.0 and ee.produit_epargne_id:
        pe_df = _load_df("epargne", _EP_SCHEMA)
        mask = pe_df["id"] == ee.produit_epargne_id
        if mask.any():
            pe_df.loc[mask, "solde_actuel"] = pe_df.loc[mask, "solde_actuel"].astype(float) + delta
            _save_df("epargne", pe_df)

    return ee


def delete_epargne_exceptionnelle(eid: int) -> None:
    df = _load_df("epargne_exceptionnelle", _EE_SCHEMA)
    if df.empty:
        return
    row = df[df["id"] == eid]
    if row.empty:
        return
    montant = float(row.iloc[0]["montant"])
    produit_id = int(row.iloc[0]["produit_epargne_id"])
    df = df[df["id"] != eid]
    _save_df("epargne_exceptionnelle", df)

    # Reverse the balance increment
    if produit_id:
        pe_df = _load_df("epargne", _EP_SCHEMA)
        mask = pe_df["id"] == produit_id
        if mask.any():
            pe_df.loc[mask, "solde_actuel"] = pe_df.loc[mask, "solde_actuel"].astype(float) - montant
            _save_df("epargne", pe_df)


# ─── Projets ──────────────────────────────────────────────────────────────────

_PROJ_SCHEMA = {
    "id": [], "nom": [], "description": [],
    "montant_cible": [], "date_souhaitee": [],
    "montant_alloue": [], "actif": [],
}


def get_projets(actif_only: bool = True) -> List[Projet]:
    df = _load_df("projets", _PROJ_SCHEMA)
    if actif_only and not df.empty:
        df = df[df["actif"].astype(bool)]
    return [Projet(**r) for r in df.to_dict("records")]


def save_projet(proj: Projet) -> Projet:
    df = _load_df("projets", _PROJ_SCHEMA)
    if proj.id == 0:
        proj.id = _next_id(df)
    df = _upsert(df, proj.model_dump())
    _save_df("projets", df)
    return proj


def delete_projet(pid: int) -> None:
    df = _load_df("projets", _PROJ_SCHEMA)
    if not df.empty:
        df = df[df["id"] != pid]
    _save_df("projets", df)


# ─── Allocations de projets ───────────────────────────────────────────────────

_ALLOC_SCHEMA = {
    "id": [], "mois": [], "annee": [],
    "projet_id": [], "montant": [], "note": [],
}


def get_allocations_projet(mois: int, annee: int) -> List[AllocationProjet]:
    df = _load_df("allocations_projet", _ALLOC_SCHEMA)
    if not df.empty:
        df = df[(df["mois"] == mois) & (df["annee"] == annee)]
    return [AllocationProjet(**r) for r in df.to_dict("records")]


def get_all_allocations_projet(annee: int) -> List[AllocationProjet]:
    df = _load_df("allocations_projet", _ALLOC_SCHEMA)
    if not df.empty:
        df = df[df["annee"] == annee]
    return [AllocationProjet(**r) for r in df.to_dict("records")]


def save_allocation_projet(alloc: AllocationProjet) -> AllocationProjet:
    """Persist an allocation and increment the project's montant_alloue."""
    df = _load_df("allocations_projet", _ALLOC_SCHEMA)

    # Compute delta vs existing record (for edit vs insert)
    old_montant = 0.0
    if not df.empty and alloc.id != 0:
        existing = df[df["id"] == alloc.id]
        if not existing.empty:
            old_montant = float(existing.iloc[0]["montant"])

    if alloc.id == 0:
        alloc.id = _next_id(df)
    df = _upsert(df, alloc.model_dump())
    _save_df("allocations_projet", df)

    delta = alloc.montant - old_montant
    if delta != 0.0 and alloc.projet_id:
        proj_df = _load_df("projets", _PROJ_SCHEMA)
        mask = proj_df["id"] == alloc.projet_id
        if mask.any():
            proj_df.loc[mask, "montant_alloue"] = (
                proj_df.loc[mask, "montant_alloue"].astype(float) + delta
            )
            _save_df("projets", proj_df)

    return alloc


def delete_allocation_projet(aid: int) -> None:
    df = _load_df("allocations_projet", _ALLOC_SCHEMA)
    if df.empty:
        return
    row = df[df["id"] == aid]
    if row.empty:
        return
    montant = float(row.iloc[0]["montant"])
    projet_id = int(row.iloc[0]["projet_id"])
    df = df[df["id"] != aid]
    _save_df("allocations_projet", df)

    if projet_id:
        proj_df = _load_df("projets", _PROJ_SCHEMA)
        mask = proj_df["id"] == projet_id
        if mask.any():
            proj_df.loc[mask, "montant_alloue"] = (
                proj_df.loc[mask, "montant_alloue"].astype(float) - montant
            )
            _save_df("projets", proj_df)


# ─── Import / Export JSON ─────────────────────────────────────────────────────

_ALL_TABLES = [
    "parametres", "charges_fixes", "epargne", "categories",
    "budgets_variables", "journal_depenses", "revenus_exceptionnels",
    "previsionnel", "biens_immobiliers",
    "epargne_exceptionnelle", "projets", "allocations_projet",
]


def export_to_json() -> str:
    """Serialize all data tables to a JSON string."""
    data: dict = {}
    for name in _ALL_TABLES:
        p = _path(name)
        data[name] = pd.read_parquet(p).to_dict("records") if os.path.exists(p) else []
    return json.dumps(data, ensure_ascii=False, indent=2, default=str)


def import_from_json(json_str: str) -> None:
    """Restore all data tables from a JSON string."""
    data = json.loads(json_str)
    for name, records in data.items():
        if records:
            _save_df(name, pd.DataFrame(records))
