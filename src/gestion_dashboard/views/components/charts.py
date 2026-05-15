"""Plotly chart builders for the budget application.

Every function returns a ``plotly.graph_objects.Figure`` that can be
passed directly to ``st.plotly_chart(fig, width="stretch")``.
"""
from __future__ import annotations

from typing import Dict, List, Optional

import plotly.graph_objects as go

from gestion_dashboard.models.budget import (
    AnalyseBudget,
    CashflowImmo,
    Repartition503020,
    SoldeMensuel,
)
from gestion_dashboard.models.enums import MOIS_COURT
from gestion_dashboard.styles.theme import CHART_PALETTE, COLORS

# ─── Shared layout defaults ───────────────────────────────────────────────────

_BASE = dict(
    font=dict(family="Inter, sans-serif", size=13, color=COLORS["text_primary"]),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(l=16, r=16, t=40, b=20),
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=-0.28,
        xanchor="center",
        x=0.5,
        font=dict(size=12),
    ),
    hoverlabel=dict(bgcolor="white", bordercolor="#ECF0F1", font_size=13),
)

_GRID = dict(
    xaxis=dict(gridcolor="#ECF0F1", showgrid=True, zeroline=False, linecolor="#ECF0F1"),
    yaxis=dict(gridcolor="#ECF0F1", showgrid=True, zeroline=False, linecolor="#ECF0F1"),
)


def _fig(**kwargs) -> go.Figure:
    """Return a Figure with the shared base layout applied."""
    layout = dict(**_BASE, **kwargs)
    return go.Figure(layout=go.Layout(**layout))


# ─── Chart functions ──────────────────────────────────────────────────────────

def chart_evolution_mensuelle(soldes: List[SoldeMensuel]) -> go.Figure:
    """
    Line chart — monthly budget vs actual evolution over 12 months.

    Parameters
    ----------
    soldes : List[SoldeMensuel]
        Monthly balance records, ordered by month.

    Returns
    -------
    go.Figure
    """
    labels = [MOIS_COURT[s.mois - 1] for s in soldes]
    fig = _fig(title="Évolution mensuelle", **_GRID)

    fig.add_trace(go.Scatter(
        x=labels,
        y=[s.total_variables_budgete for s in soldes],
        name="Budgété",
        line=dict(color=COLORS["primary"], dash="dot", width=2),
        mode="lines+markers",
        marker=dict(size=6),
        hovertemplate="%{y:,.0f} €<extra>Budgété</extra>",
    ))
    fig.add_trace(go.Scatter(
        x=labels,
        y=[s.total_variables_reel for s in soldes],
        name="Réel",
        line=dict(color=COLORS["secondary"], width=2.5),
        mode="lines+markers",
        marker=dict(size=6),
        hovertemplate="%{y:,.0f} €<extra>Réel</extra>",
    ))
    fig.add_trace(go.Scatter(
        x=labels,
        y=[s.solde_disponible for s in soldes],
        name="Solde disponible",
        line=dict(color=COLORS["positive"], width=2),
        mode="lines+markers",
        fill="tozeroy",
        fillcolor="rgba(39,174,96,0.07)",
        marker=dict(size=6),
        hovertemplate="%{y:,.0f} €<extra>Solde</extra>",
    ))
    return fig


def chart_double_piechart(
    repartition: Repartition503020,
    reel_dict: Dict[str, float],
) -> go.Figure:
    """
    Side-by-side pie charts: theoretical 50/30/20 vs actual spending.

    Parameters
    ----------
    repartition : Repartition503020
        Theoretical allocation.
    reel_dict : Dict[str, float]
        Actual amounts keyed by label.

    Returns
    -------
    go.Figure
    """
    fig = _fig(title="Budget Théorique (50/30/20) vs Budget Réel", showlegend=False)

    fig.add_trace(go.Pie(
        labels=["Besoins", "Loisirs & envies", "Épargne"],
        values=[repartition.besoins, repartition.loisirs, repartition.epargne],
        name="Théorique",
        domain=dict(x=[0, 0.46]),
        marker=dict(colors=[COLORS["primary"], COLORS["secondary"], COLORS["positive"]]),
        textinfo="label+percent",
        hovertemplate="%{label}: %{value:,.0f} €<extra>Théorique</extra>",
        title=dict(text="<b>Théorique</b>", font=dict(size=13, color=COLORS["text_primary"])),
    ))
    fig.add_trace(go.Pie(
        labels=list(reel_dict.keys()),
        values=list(reel_dict.values()),
        name="Réel",
        domain=dict(x=[0.54, 1.0]),
        marker=dict(colors=[COLORS["primary"], COLORS["secondary"], COLORS["positive"]]),
        textinfo="label+percent",
        hovertemplate="%{label}: %{value:,.0f} €<extra>Réel</extra>",
        title=dict(text="<b>Réel</b>", font=dict(size=13, color=COLORS["text_primary"])),
    ))
    return fig


def chart_barres_groupees(soldes: List[SoldeMensuel]) -> go.Figure:
    """
    Grouped bar chart — budgeted vs actual by month.

    Parameters
    ----------
    soldes : List[SoldeMensuel]
        Monthly balances.

    Returns
    -------
    go.Figure
    """
    labels = [MOIS_COURT[s.mois - 1] for s in soldes]
    reels = [s.total_variables_reel for s in soldes]
    fig = _fig(barmode="group", title="Dépenses mensuelles — Budgété vs Réel", **_GRID)

    fig.add_trace(go.Bar(
        x=labels,
        y=[s.total_variables_budgete for s in soldes],
        name="Budgété",
        marker_color=COLORS["primary"],
        opacity=0.65,
    ))
    fig.add_trace(go.Bar(
        x=labels,
        y=reels,
        name="Réel",
        marker_color=COLORS["secondary"],
    ))
    if reels:
        avg = sum(reels) / len(reels)
        fig.add_hline(
            y=avg,
            line_dash="dot",
            line_color=COLORS["warning"],
            annotation_text=f"Moy. {avg:,.0f} €",
            annotation_font_color=COLORS["warning"],
        )
    return fig


def chart_heatmap(
    categories: List[str],
    mois_labels: List[str],
    matrix: List[List[float]],
) -> go.Figure:
    """
    Heatmap of spending intensity — categories × months.

    Parameters
    ----------
    categories : List[str]
        Row labels (category names).
    mois_labels : List[str]
        Column labels (month abbreviations).
    matrix : List[List[float]]
        2-D list [category][month] of amounts.

    Returns
    -------
    go.Figure
    """
    text = [[f"{v:,.0f} €" if v > 0 else "" for v in row] for row in matrix]
    fig = _fig(title="Heatmap des dépenses (€/mois × catégorie)")
    fig.update_layout(margin=dict(l=160, r=16, t=40, b=40))

    fig.add_trace(go.Heatmap(
        z=matrix,
        x=mois_labels,
        y=categories,
        colorscale=[[0, "#FFFFFF"], [0.3, "#FDEBD0"], [0.7, "#F39C12"], [1, "#E74C3C"]],
        showscale=True,
        hovertemplate="Mois: %{x}<br>Catégorie: %{y}<br>Montant: %{z:,.0f} €<extra></extra>",
        text=text,
        texttemplate="%{text}",
        textfont=dict(size=11),
    ))
    return fig


def chart_projection_epargne(
    years: List[int],
    projections: List[float],
    produit_nom: str,
    objectif: Optional[float] = None,
) -> go.Figure:
    """
    Line chart — compound-interest projection over time.

    Parameters
    ----------
    years : List[int]
        Year indices (e.g. [0, 1, 2, …, 30]).
    projections : List[float]
        Projected balance at each year.
    produit_nom : str
        Savings product name (used in the chart title).
    objectif : float, optional
        Target balance; rendered as a dashed horizontal line.

    Returns
    -------
    go.Figure
    """
    fig = _fig(
        title=f"Projection — {produit_nom}",
        xaxis_title="Années",
        yaxis_title="Montant (€)",
        **_GRID,
    )
    fig.add_trace(go.Scatter(
        x=years,
        y=projections,
        name=produit_nom,
        line=dict(color=COLORS["primary"], width=2.5),
        fill="tozeroy",
        fillcolor="rgba(91,79,190,0.08)",
        mode="lines+markers",
        marker=dict(size=5),
        hovertemplate="Année %{x}: %{y:,.0f} €<extra></extra>",
    ))
    if objectif:
        fig.add_hline(
            y=objectif,
            line_dash="dash",
            line_color=COLORS["positive"],
            annotation_text=f"Objectif: {objectif:,.0f} €",
            annotation_font_color=COLORS["positive"],
        )
    return fig


def chart_waterfall_cashflow(cf: CashflowImmo, bien_nom: str) -> go.Figure:
    """
    Waterfall chart — monthly cashflow breakdown for a rental property.

    Parameters
    ----------
    cf : CashflowImmo
        Cashflow data.
    bien_nom : str
        Property name used in the chart title.

    Returns
    -------
    go.Figure
    """
    items = [
        ("Loyer perçu",         cf.loyer_percu,              "relative"),
        ("Mensualité crédit",   -cf.mensualite_credit,        "relative"),
        ("Charges propriétaire",-cf.charges_proprietaire,     "relative"),
        ("Taxe foncière",       -cf.taxe_fonciere_mensuelle,  "relative"),
        ("Assurance",           -cf.assurance_mensuelle,      "relative"),
        ("Frais de gestion",    -cf.frais_gestion,            "relative"),
        ("Cashflow net",         cf.cashflow_net_mensuel,     "total"),
    ]
    labels, values, measures = zip(*[(i[0], i[1], i[2]) for i in items])

    fig = _fig(title=f"Cashflow mensuel — {bien_nom}", **_GRID)
    fig.add_trace(go.Waterfall(
        measure=list(measures),
        x=list(labels),
        y=list(values),
        connector=dict(line=dict(color="#ECF0F1", width=1)),
        increasing=dict(marker=dict(color=COLORS["positive"])),
        decreasing=dict(marker=dict(color=COLORS["negative"])),
        totals=dict(marker=dict(color=COLORS["primary"])),
        text=[f"{v:+,.0f} €" for v in values],
        textposition="outside",
        hovertemplate="%{x}: %{y:+,.0f} €<extra></extra>",
    ))
    fig.update_layout(yaxis_title="€/mois")
    return fig


def chart_donut_epargne(
    labels: List[str],
    values: List[float],
) -> go.Figure:
    """
    Donut chart — savings distribution by product type.

    Parameters
    ----------
    labels : List[str]
        Product type names.
    values : List[float]
        Balances for each type.

    Returns
    -------
    go.Figure
    """
    total = sum(values)
    fig = _fig(title="Répartition du patrimoine financier")
    fig.add_trace(go.Pie(
        labels=labels,
        values=values,
        hole=0.45,
        marker=dict(colors=CHART_PALETTE[: len(labels)]),
        textinfo="label+percent",
        hovertemplate="%{label}: %{value:,.0f} €<extra></extra>",
    ))
    fig.add_annotation(
        text=f"<b>{total:,.0f} €</b>",
        x=0.5, y=0.5,
        font=dict(size=15, color=COLORS["text_primary"]),
        showarrow=False,
    )
    return fig


def chart_categories_piechart(
    analyses: List[AnalyseBudget],
    show_reel: bool = True,
) -> go.Figure:
    """
    Pie chart — spending by category (actual or budgeted).

    Parameters
    ----------
    analyses : List[AnalyseBudget]
        Budget analysis rows.
    show_reel : bool
        When ``True`` show actual amounts; when ``False`` show budgeted amounts.

    Returns
    -------
    go.Figure
    """
    key = "reel" if show_reel else "budgete"
    filtered = [(a, getattr(a, key)) for a in analyses if getattr(a, key) > 0]
    if not filtered:
        return _fig(title="Aucune dépense")
    labels = [f"{a.categorie_icone} {a.categorie_nom}" for a, _ in filtered]
    values = [v for _, v in filtered]
    colors = [a.categorie_couleur for a, _ in filtered]

    title = "Dépenses réelles par catégorie" if show_reel else "Budget par catégorie"
    fig = _fig(title=title, showlegend=False)
    fig.add_trace(go.Pie(
        labels=labels,
        values=values,
        marker=dict(colors=colors),
        textinfo="label+percent",
        hovertemplate="%{label}: %{value:,.0f} € (%{percent})<extra></extra>",
    ))
    return fig


def chart_previsionnel_timeline(
    items: list,
    mois_labels: List[str],
) -> go.Figure:
    """
    Horizontal bar chart — annual forecast timeline by month.

    Parameters
    ----------
    items : list
        List of PlanningDepense objects.
    mois_labels : List[str]
        Month name labels for the x-axis.

    Returns
    -------
    go.Figure
    """
    color_map = {
        "À venir": COLORS["primary"],
        "Payé": COLORS["positive"],
        "En cours": COLORS["warning"],
        "Annulé": "#BDC3C7",
    }
    fig = _fig(title="Calendrier des dépenses prévisionnelles", **_GRID)

    for i, item in enumerate(items):
        color = color_map.get(item.statut, COLORS["primary"])
        mois_nom = mois_labels[item.mois_prevu - 1] if 1 <= item.mois_prevu <= 12 else "?"
        montant = item.montant_reel if item.montant_reel else item.montant_estime
        fig.add_trace(go.Bar(
            x=[montant],
            y=[f"{mois_nom} — {item.libelle[:20]}"],
            orientation="h",
            marker_color=color,
            text=f"{montant:,.0f} €",
            textposition="outside",
            hovertemplate=f"{item.libelle}<br>Montant: {montant:,.0f} €<br>Statut: {item.statut}<extra></extra>",
            showlegend=False,
            name=item.statut,
        ))

    fig.update_layout(
        xaxis_title="Montant (€)",
        barmode="overlay",
        height=max(200, 40 * len(items) + 80),
    )
    return fig
