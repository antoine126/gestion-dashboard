"""Reference data constants for the budget application."""

MOIS = [
    "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
    "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre",
]

MOIS_COURT = ["Jan", "Fév", "Mar", "Avr", "Mai", "Jun",
               "Jul", "Aoû", "Sep", "Oct", "Nov", "Déc"]

CATEGORIES_DEFAULT = [
    {"id": 1, "nom": "Courses / Vie Quotidienne", "icone": "🛒", "couleur": "#27AE60", "ordre": 1},
    {"id": 2, "nom": "Restaurants / Sorties",     "icone": "🍽️", "couleur": "#E67E22", "ordre": 2},
    {"id": 3, "nom": "Loisirs / Hobbies",         "icone": "🎮", "couleur": "#9B59B6", "ordre": 3},
    {"id": 4, "nom": "Sport & Bien-être",          "icone": "🏋️", "couleur": "#1ABC9C", "ordre": 4},
    {"id": 5, "nom": "Transport / Carburant",      "icone": "🚗", "couleur": "#3498DB", "ordre": 5},
    {"id": 6, "nom": "Santé / Pharmacie",          "icone": "💊", "couleur": "#E74C3C", "ordre": 6},
    {"id": 7, "nom": "Achats divers",              "icone": "🛍️", "couleur": "#95A5A6", "ordre": 7},
    {"id": 8, "nom": "Autres dépenses",            "icone": "📦", "couleur": "#BDC3C7", "ordre": 8},
]

PRODUITS_EPARGNE_DEFAULT = [
    {"id": 1, "produit": "Livret A",  "type_produit": "Livret",       "solde_actuel": 0.0, "versement_mensuel": 0.0, "taux_annuel": 2.4,  "objectif": None, "actif": True},
    {"id": 2, "produit": "LDDS",      "type_produit": "Livret",       "solde_actuel": 0.0, "versement_mensuel": 0.0, "taux_annuel": 2.4,  "objectif": None, "actif": True},
    {"id": 3, "produit": "PEA",       "type_produit": "Actions",      "solde_actuel": 0.0, "versement_mensuel": 0.0, "taux_annuel": 7.0,  "objectif": None, "actif": True},
    {"id": 4, "produit": "PER",       "type_produit": "Retraite",     "solde_actuel": 0.0, "versement_mensuel": 0.0, "taux_annuel": 5.0,  "objectif": None, "actif": True},
    {"id": 5, "produit": "Assurance-vie", "type_produit": "Assurance-vie", "solde_actuel": 0.0, "versement_mensuel": 0.0, "taux_annuel": 3.5, "objectif": None, "actif": True},
]

MODES_PAIEMENT = [
    "Carte bancaire",
    "Virement bancaire",
    "Espèces",
    "Prélèvement automatique",
    "Chèque",
    "PayPal",
    "Virement instantané",
    "Autre",
]

STATUTS_PREVISIONNEL = ["À venir", "Payé", "En cours", "Annulé"]

TYPES_BIEN_IMMOBILIER = [
    "Résidence Principale",
    "Investissement Locatif",
    "Locatif meublé (LMNP)",
    "Locatif nu",
    "SCPI",
    "Crowdfunding immobilier",
    "Résidence secondaire",
]

TYPES_PRODUIT_EPARGNE = [
    "Livret", "Actions", "Assurance-vie", "Retraite",
    "Épargne logement", "Alternatif",
]

FREQUENCES_CHARGE = ["Mensuelle", "Trimestrielle", "Annuelle"]
