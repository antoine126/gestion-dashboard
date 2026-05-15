# Gestion Dashboard — Budget Personnel

Application web de gestion budgétaire personnelle, construite avec Python et Streamlit. Elle remplace un fichier Excel par une interface interactive, des graphiques dynamiques et une persistance locale au format Parquet.

---

## Fonctionnalités

### Vue d'ensemble (Dashboard)
- KPIs annuels : revenus, charges fixes, épargne, solde moyen
- Évolution mensuelle des revenus, charges et solde (graphique linéaire)
- Comparaison répartition théorique 50/30/20 vs réelle (double camembert)

### Paramètres
- Salaire net mensuel et personnalisation des taux besoins / loisirs / épargne
- Gestion des charges fixes (loyer, abonnements, crédits…) avec fréquence mensuelle / trimestrielle / annuelle
- Gestion des produits d'épargne programmée (Livret A, PEA, assurance-vie…)
- Gestion des catégories de dépenses variables
- Gestion des projets personnels (voiture, vacances, travaux…) avec montant cible et date souhaitée

### Vue Mensuelle
- Tableau charges fixes + épargne + solde disponible
- Dépenses variables par catégorie avec barres de progression budget vs réel
- Revenus exceptionnels (prime, remboursement…)
- Épargne exceptionnelle : versement ponctuel sur un produit d'épargne, déduit du solde et crédité automatiquement sur le solde du produit
- Dépenses prévisionnelles du mois en cours (issues du module Prévisionnel)
- 5 cartes KPI colorées :
  - **SOLDE DISPONIBLE** (vert/rouge) — solde réel incluant le report cumulé
  - **BUDGET PROJETÉ** (bleu/rouge) — solde prévisionnel si le budget est respecté
  - **SURPLUS / DÉFICIT REPORTÉ** (vert/rouge/gris) — balance courante reportée des mois précédents, réinitialisée au 1er janvier
  - **SOLDE MENSUEL** (vert/rouge) — solde du mois courant uniquement, sans report
  - **BUDGET MENSUEL PROJETÉ** (bleu/rouge) — budget projeté du mois courant uniquement, sans report
- Allocation du surplus mensuel vers les projets personnels (visible uniquement si solde > 0)

### Journal des dépenses
- Saisie rapide : date, libellé, catégorie, montant, mode de paiement, note
- Tableau paginé et filtrable
- Export Excel (.xlsx)

### Épargne & Patrimoine
- Donut du patrimoine total par produit
- Simulateur d'intérêts composés avec projections glissantes
- Comparaison de scénarios (taux / versement / durée)
- Calculateur d'objectif : durée nécessaire pour atteindre un montant cible

### Immobilier
- Fiches biens : résidence principale, locatif, SCPI
- Waterfall du cashflow mensuel (loyer → charges → crédit → cashflow net)
- Rentabilité brute et nette calculées automatiquement

### Prévisionnel Annuel
- Tableau de planification des grosses dépenses avec catégorie associée
- Calendrier visuel des dépenses par mois
- Mensualité suggérée pour couvrir les dépenses à venir

### Analyses
- Heatmap des dépenses par catégorie × mois
- Détection automatique des mois anormaux
- Tendances des dépenses variables

---

## Stack technique

| Composant | Technologie |
|---|---|
| Langage | Python 3.12.7 |
| Gestionnaire de packages | [UV](https://docs.astral.sh/uv/) |
| Interface | Streamlit ≥ 1.40 |
| Validation des données | Pydantic v2 |
| Persistance | Parquet (Pandas + PyArrow) |
| Graphiques | Plotly |
| Export Excel | openpyxl |

---

## Architecture

```
src/gestion_dashboard/
├── app.py                        # Point d'entrée Streamlit (st.navigation)
├── models/
│   ├── budget.py                 # Pydantic BaseModel (persistance) + @dataclass (calculs)
│   └── enums.py                  # Constantes : MOIS, catégories par défaut, etc.
├── controllers/
│   ├── database.py               # CRUD Parquet — une table par entité
│   ├── calculs.py                # Logique métier pure (50/30/20, KPIs, cashflow)
│   ├── epargne.py                # Projections intérêts composés
│   └── export.py                 # Export Excel (.xlsx)
├── styles/
│   └── theme.py                  # CSS global, palette COLORS, helpers HTML
├── views/
│   ├── components/
│   │   ├── kpi_card.py           # Carte KPI réutilisable
│   │   └── charts.py             # Graphiques Plotly partagés
│   └── pages/
│       ├── dashboard.py
│       ├── parametres.py
│       ├── mensuel.py
│       ├── journal.py
│       ├── epargne_page.py
│       ├── immobilier.py
│       ├── previsionnel.py
│       └── analyses.py
└── data/                         # Fichiers Parquet (créés automatiquement au premier lancement)
    ├── parametres.parquet
    ├── charges_fixes.parquet
    ├── epargne.parquet
    ├── categories.parquet
    ├── budgets_variables.parquet
    ├── journal_depenses.parquet
    ├── revenus_exceptionnels.parquet
    ├── previsionnel.parquet
    ├── biens_immobiliers.parquet
    ├── epargne_exceptionnelle.parquet
    ├── projets.parquet
    └── allocations_projet.parquet
```

Les données sont stockées localement dans `src/gestion_dashboard/data/`. Les fichiers Parquet sont créés automatiquement au premier lancement — aucune base de données externe n'est requise.

---

## Installation

### Prérequis

- Python 3.12.7+
- [UV](https://docs.astral.sh/uv/getting-started/installation/) installé

### Lancement

```bash
# Cloner le dépôt
git clone <url-du-repo>
cd gestion_dashboard

# Installer les dépendances et lancer
uv run gestion-dashboard
```

L'application s'ouvre automatiquement sur [http://localhost:8501](http://localhost:8501).

Alternatively, you can run Streamlit directly:

```bash
uv run python -m streamlit run src/gestion_dashboard/app.py
```

---

## Premiers pas

1. **Paramètres** — Renseignez votre salaire net mensuel et ajustez les taux 50/30/20 si nécessaire.
2. **Charges fixes** — Ajoutez vos charges récurrentes (loyer, abonnements, crédits).
3. **Épargne** — Configurez vos produits d'épargne et versements mensuels.
4. **Catégories** — Personnalisez les catégories de dépenses variables (ou conservez celles par défaut).
5. **Vue Mensuelle** — Saisissez vos budgets par catégorie et suivez vos dépenses réelles.
6. **Journal** — Enregistrez chaque dépense au fil du mois.

---

## Sauvegarde et restauration

Depuis la page **Prévisionnel**, un bouton permet d'exporter l'intégralité des données en JSON et de les restaurer ultérieurement. Les fichiers Parquet dans `data/` peuvent également être sauvegardés directement.

---

## Conventions de code

- Code et docstrings en **anglais**, format NumPy
- **Pydantic BaseModel** pour toutes les structures persistées (lecture/écriture Parquet)
- **@dataclass** pour les résultats de calcul internes (jamais sérialisés)
- CSS et styles isolés dans `styles/theme.py`
- Architecture **MVC** stricte : aucune logique métier dans les vues, aucun I/O dans les calculs

---

## Changelog

### v1.1
- **Épargne exceptionnelle** : versement ponctuel sur un produit d'épargne avec mise à jour automatique du solde du produit
- **Dépenses prévisionnelles** dans la Vue Mensuelle, avec association optionnelle à une catégorie de dépense variable
- **Projets personnels** : objectif, date cible, suivi de progression et allocation du surplus mensuel (réduit le solde disponible)
- **Solde reporté** (surplus ou déficit) : balance courante calculée mois par mois depuis janvier, réinitialisée au 1er janvier ; les mois sans activité sont neutres (ne gonflent pas le surplus)
- **5 cartes KPI** en Vue Mensuelle : 3 cartes incluant le report cumulé (Solde disponible, Budget projeté, Surplus/Déficit reporté) + 2 cartes mois courant uniquement (Solde mensuel, Budget mensuel projeté)

### v1.0
- Version initiale : Dashboard, Paramètres, Vue Mensuelle, Journal, Épargne, Immobilier, Prévisionnel, Analyses
