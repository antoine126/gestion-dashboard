"""PDF report generation using fpdf2 and Plotly/kaleido for chart images."""
from __future__ import annotations

import datetime
import io
import re
import struct
from typing import List, Optional, Tuple

from fpdf import FPDF, XPos, YPos

from gestion_dashboard.models.budget import (
    AnalyseBudget,
    CategorieDepense,
    KPIAnnuel,
    Parametres,
    Repartition503020,
    SoldeMensuel,
)
from gestion_dashboard.models.enums import MOIS, MOIS_COURT

# ─── Font path ────────────────────────────────────────────────────────────────

_FONT_PATH = "/Library/Fonts/Arial Unicode.ttf"

# ─── Colour palette (R, G, B) ────────────────────────────────────────────────

_C_PRIMARY   = (91,  79,  190)   # #5B4FBE
_C_SECONDARY = (0,   180, 166)   # #00B4A6
_C_POSITIVE  = (39,  174, 96)    # #27AE60
_C_NEGATIVE  = (231, 76,  60)    # #E74C3C
_C_WARNING   = (243, 156, 18)    # #F39C12
_C_TEXT      = (44,  62,  80)    # #2C3E50
_C_GRAY      = (127, 140, 141)   # #7F8C8D
_C_BG        = (248, 249, 250)   # #F8F9FA
_C_BORDER    = (236, 240, 241)   # #ECF0F1
_C_WHITE     = (255, 255, 255)
_C_PURPLE_LT = (237, 233, 255)   # light purple for totals row


def _hex_to_rgb(h: str) -> Tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _strip_emoji(text: str) -> str:
    """Remove emoji and non-BMP characters from text (core-font compatibility)."""
    return re.sub(r"[^\x00-\xFF€–—’“”]", "", text).strip()


def _png_size(data: bytes) -> Tuple[int, int]:
    """Return (width_px, height_px) from raw PNG bytes."""
    return struct.unpack(">II", data[16:24])


# ─── PDF class ────────────────────────────────────────────────────────────────

class _BudgetPDF(FPDF):
    """Custom FPDF subclass with branded layout helpers."""

    _MARGIN_LEFT  = 15
    _MARGIN_RIGHT = 15
    _MARGIN_TOP   = 18
    _MARGIN_BOT   = 18
    _USABLE_W     = 210 - _MARGIN_LEFT - _MARGIN_RIGHT  # 180 mm

    def __init__(self, annee: int, today_str: str) -> None:
        super().__init__(orientation="P", unit="mm", format="A4")
        self.alias_nb_pages()
        self.set_margins(self._MARGIN_LEFT, self._MARGIN_TOP, self._MARGIN_RIGHT)
        self.set_auto_page_break(auto=True, margin=self._MARGIN_BOT)
        self._annee = annee
        self._today = today_str
        self.add_font("AU", fname=_FONT_PATH)
        self.add_font("AU", style="B", fname=_FONT_PATH)

    # ── Header / Footer ──────────────────────────────────────────────────────

    def footer(self) -> None:
        self.set_y(-14)
        self.set_font("AU", size=8)
        self.set_text_color(*_C_GRAY)
        self.cell(
            0, 8,
            f"Budget Personnel — Rapport {self._annee} — {self._today}"
            f" — Page {self.page_no()} / {{nb}}",
            align="C",
        )

    # ── Typography helpers ───────────────────────────────────────────────────

    def h1(self, text: str) -> None:
        """Section heading with primary-colour underline."""
        self.set_font("AU", style="B", size=14)
        self.set_text_color(*_C_PRIMARY)
        self.cell(0, 8, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        x, y = self.get_x(), self.get_y()
        self.set_draw_color(*_C_PRIMARY)
        self.set_line_width(0.5)
        self.line(x, y, x + self._USABLE_W, y)
        self.ln(4)
        self.set_text_color(*_C_TEXT)
        self.set_line_width(0.2)

    def h2(self, text: str) -> None:
        """Sub-section heading."""
        self.ln(2)
        self.set_font("AU", style="B", size=11)
        self.set_text_color(*_C_TEXT)
        self.cell(0, 7, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        x, y = self.get_x(), self.get_y()
        self.set_draw_color(*_C_BORDER)
        self.line(x, y, x + self._USABLE_W, y)
        self.ln(3)

    def body(self, text: str, size: int = 10) -> None:
        self.set_font("AU", size=size)
        self.set_text_color(*_C_TEXT)
        self.multi_cell(0, 5, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # ── KPI card ─────────────────────────────────────────────────────────────

    def _kpi_card(
        self,
        x: float, y: float, w: float, h: float,
        label: str, value: float,
        delta: Optional[float] = None,
    ) -> None:
        # card background
        self.set_fill_color(*_C_BG)
        self.set_draw_color(*_C_BORDER)
        self.set_line_width(0.2)
        self.rect(x, y, w, h, style="FD")
        # label
        self.set_font("AU", size=7)
        self.set_text_color(*_C_GRAY)
        self.set_xy(x + 2, y + 3)
        self.cell(w - 4, 4, label.upper(), align="C")
        # value
        self.set_font("AU", style="B", size=11)
        self.set_text_color(*_C_TEXT)
        self.set_xy(x + 2, y + 8)
        self.cell(w - 4, 6, f"{value:,.0f} €", align="C")
        # delta
        if delta is not None:
            self.set_font("AU", size=8)
            color = _C_POSITIVE if delta >= 0 else _C_NEGATIVE
            sign = "+" if delta >= 0 else ""
            self.set_text_color(*color)
            self.set_xy(x + 2, y + 15)
            self.cell(w - 4, 4, f"{sign}{delta:,.0f} € vs budget", align="C")
        self.set_text_color(*_C_TEXT)

    def kpi_grid(
        self,
        items: List[tuple],
        cols: int = 3,
        card_h: float = 24,
    ) -> None:
        """
        Draw a row of KPI cards.

        Parameters
        ----------
        items : list of (label, value) or (label, value, delta)
        """
        gap = 3.0
        card_w = (self._USABLE_W - gap * (cols - 1)) / cols
        y0 = self.get_y()
        n_rows = (len(items) + cols - 1) // cols
        for i, item in enumerate(items):
            label  = item[0]
            value  = item[1]
            delta  = item[2] if len(item) > 2 else None
            row    = i // cols
            col    = i % cols
            x      = self._MARGIN_LEFT + col * (card_w + gap)
            y      = y0 + row * (card_h + gap)
            self._kpi_card(x, y, card_w, card_h, label, value, delta)
        self.set_y(y0 + n_rows * (card_h + gap) + 2)

    # ── Colour KPI (monthly) ─────────────────────────────────────────────────

    def _color_kpi(
        self,
        x: float, y: float, w: float, h: float,
        label: str, value: float, bg: Tuple[int, int, int],
    ) -> None:
        self.set_fill_color(*bg)
        self.set_draw_color(*bg)
        self.set_line_width(0)
        self.rect(x, y, w, h, style="F")
        self.set_text_color(*_C_WHITE)
        self.set_font("AU", size=7)
        self.set_xy(x + 1, y + 2)
        self.cell(w - 2, 4, label, align="C")
        self.set_font("AU", style="B", size=11)
        self.set_xy(x + 1, y + 7)
        self.cell(w - 2, 5, f"{value:,.0f} €", align="C")
        self.set_text_color(*_C_TEXT)
        self.set_line_width(0.2)

    def color_kpi_grid(self, items: List[tuple], cols: int = 4, card_h: float = 20) -> None:
        """Draw coloured KPI cards. items = list of (label, value, bg_color_tuple)."""
        gap = 2.5
        card_w = (self._USABLE_W - gap * (cols - 1)) / cols
        y0 = self.get_y()
        n_rows = (len(items) + cols - 1) // cols
        for i, (label, value, bg) in enumerate(items):
            row = i // cols
            col = i % cols
            x   = self._MARGIN_LEFT + col * (card_w + gap)
            y   = y0 + row * (card_h + gap)
            self._color_kpi(x, y, card_w, card_h, label, value, bg)
        self.set_y(y0 + n_rows * (card_h + gap) + 3)

    # ── Chart image ──────────────────────────────────────────────────────────

    def add_chart(self, png_bytes: bytes, max_w: float = 180) -> None:
        """Embed a PNG chart at full usable width."""
        w_px, h_px = _png_size(png_bytes)
        img_w = min(max_w, self._USABLE_W)
        img_h = img_w * h_px / w_px
        if self.get_y() + img_h > self.page_break_trigger:
            self.add_page()
        buf = io.BytesIO(png_bytes)
        self.image(buf, x=self._MARGIN_LEFT, w=img_w, h=img_h, type="PNG")
        self.ln(4)

    # ── Table ────────────────────────────────────────────────────────────────

    def table(
        self,
        headers: List[str],
        col_widths: List[float],
        rows: List[List],
        col_aligns: Optional[List[str]] = None,
        total_row: Optional[List] = None,
    ) -> None:
        """Render a simple data table with alternating row fill."""
        aligns = col_aligns or ["L"] * len(headers)
        row_h = 6.0

        # Header
        self.set_fill_color(*_C_PRIMARY)
        self.set_text_color(*_C_WHITE)
        self.set_font("AU", style="B", size=9)
        for h, w, a in zip(headers, col_widths, aligns):
            self.cell(w, row_h + 1, h, border=0, fill=True, align=a)
        self.ln()

        # Data rows
        for idx, row in enumerate(rows):
            fill = idx % 2 == 0
            if fill:
                self.set_fill_color(*_C_BG)
            self.set_font("AU", size=8.5)
            for val, w, a in zip(row, col_widths, aligns):
                # Detect colored value via tuple sentinel
                if isinstance(val, tuple) and len(val) == 2:
                    txt, color = val
                    self.set_text_color(*color)
                    self.cell(w, row_h, str(txt), border=0, fill=fill, align=a)
                    self.set_text_color(*_C_TEXT)
                else:
                    self.set_text_color(*_C_TEXT)
                    self.cell(w, row_h, str(val), border=0, fill=fill, align=a)
            self.ln()

        # Total / footer row
        if total_row is not None:
            self.set_fill_color(*_C_PURPLE_LT)
            self.set_font("AU", style="B", size=9)
            self.set_draw_color(*_C_PRIMARY)
            self.set_line_width(0.4)
            for val, w, a in zip(total_row, col_widths, aligns):
                if isinstance(val, tuple):
                    txt, color = val
                    self.set_text_color(*color)
                    self.cell(w, row_h + 1, str(txt), border="T", fill=True, align=a)
                    self.set_text_color(*_C_TEXT)
                else:
                    self.set_text_color(*_C_TEXT)
                    self.cell(w, row_h + 1, str(val), border="T", fill=True, align=a)
            self.ln()
            self.set_line_width(0.2)

        self.ln(2)

    # ── Info box ─────────────────────────────────────────────────────────────

    def info_box(self, text: str, bg: Tuple[int, int, int] = (235, 245, 251)) -> None:
        x, y = self.get_x(), self.get_y()
        self.set_fill_color(*bg)
        self.set_draw_color(*_C_PRIMARY)
        self.set_line_width(0.6)
        self.line(x, y, x, y + 12)
        self.set_line_width(0)
        self.rect(x + 0.5, y, self._USABLE_W - 0.5, 12, style="F")
        self.set_font("AU", size=9)
        self.set_text_color(26, 82, 118)
        self.set_xy(x + 4, y + 2)
        self.multi_cell(self._USABLE_W - 5, 5, text)
        self.set_line_width(0.2)
        self.set_y(y + 14)
        self.set_text_color(*_C_TEXT)


# ─── Chart generation ─────────────────────────────────────────────────────────

def _make_png(fig, width: int = 860, height: int = 320) -> Optional[bytes]:
    """Convert a Plotly figure to PNG bytes via kaleido. Returns None on failure."""
    try:
        import plotly.io as pio
        return pio.to_image(fig, format="png", width=width, height=height, scale=2)
    except Exception:
        return None


# ─── Main export function ─────────────────────────────────────────────────────

def generate_rapport_pdf(
    annee: int,
    parametres: Parametres,
    kpis: KPIAnnuel,
    soldes: List[SoldeMensuel],
    analyses: List[AnalyseBudget],
    repartition: Optional[Repartition503020],
    categories: Optional[List[CategorieDepense]] = None,
    heatmap_matrix: Optional[List[List[float]]] = None,
    include_mensuel: bool = True,
    include_heatmap: bool = True,
) -> bytes:
    """
    Generate a full annual budget PDF report.

    Parameters
    ----------
    annee : int
        Report year.
    parametres : Parametres
        User settings (salary, rates).
    kpis : KPIAnnuel
        Annual KPIs.
    soldes : List[SoldeMensuel]
        Monthly balances (12 items).
    analyses : List[AnalyseBudget]
        Annual budget analysis per category.
    repartition : Repartition503020, optional
        50/30/20 theoretical split.
    categories : List[CategorieDepense], optional
        Category list for heatmap labels.
    heatmap_matrix : List[List[float]], optional
        2-D spending matrix [category][month].
    include_mensuel : bool
        Include the 12-month summary section.
    include_heatmap : bool
        Include the spending heatmap section.

    Returns
    -------
    bytes
        PDF content ready for download.
    """
    from gestion_dashboard.views.components import charts

    today = datetime.date.today().strftime("%d/%m/%Y")
    pdf = _BudgetPDF(annee=annee, today_str=today)

    # ── Page 1: Cover ────────────────────────────────────────────────────────
    pdf.add_page()

    # Gradient-like header stripe
    pdf.set_fill_color(*_C_PRIMARY)
    pdf.rect(0, 0, 210, 8, style="F")
    pdf.set_fill_color(*_C_SECONDARY)
    pdf.rect(105, 0, 105, 8, style="F")

    pdf.set_y(70)
    pdf.set_font("AU", style="B", size=28)
    pdf.set_text_color(*_C_PRIMARY)
    pdf.cell(0, 12, f"Rapport Financier {annee}", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_font("AU", size=14)
    pdf.set_text_color(*_C_GRAY)
    pdf.cell(0, 8, "Budget Personnel — Tableau de bord consolidé", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.ln(20)
    pdf.set_draw_color(*_C_BORDER)
    pdf.set_line_width(0.3)
    pdf.line(40, pdf.get_y(), 170, pdf.get_y())
    pdf.ln(8)

    pdf.set_font("AU", size=11)
    pdf.set_text_color(*_C_TEXT)
    meta_lines = [
        f"Salaire net mensuel : {parametres.salaire_net:,.0f} €",
        (
            f"Répartition théorique : {parametres.taux_besoins*100:.0f}% besoins / "
            f"{parametres.taux_loisirs*100:.0f}% loisirs / "
            f"{parametres.taux_epargne*100:.0f}% épargne"
        ),
        f"Généré le {today}",
    ]
    for line in meta_lines:
        pdf.cell(0, 7, line, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # ── Page 2: Dashboard Annuel ─────────────────────────────────────────────
    pdf.add_page()
    pdf.h1("Dashboard Annuel")

    ecart_var = kpis.variables_reelles - kpis.variables_budgetees
    pdf.kpi_grid([
        ("Revenus annuels",       kpis.revenus_annuels),
        ("Charges fixes",         kpis.charges_fixes_annuelles),
        ("Solde moy./mois",       kpis.solde_mensuel_moyen),
        ("Var. budgétées",        kpis.variables_budgetees),
        ("Var. réelles",          kpis.variables_reelles, ecart_var),
        ("Projection épargne/an", kpis.projection_epargne_annuelle),
    ], cols=3, card_h=24)

    pdf.h2("Évolution mensuelle — Budgété / Réel / Solde")
    png = _make_png(charts.chart_evolution_mensuelle(soldes), 860, 300)
    if png:
        pdf.add_chart(png)
    else:
        pdf.body("(graphique indisponible)")

    pdf.h2("Dépenses mensuelles — Budgété vs Réel")
    png = _make_png(charts.chart_barres_groupees(soldes), 860, 270)
    if png:
        pdf.add_chart(png)
    else:
        pdf.body("(graphique indisponible)")

    # ── Page 3: 50/30/20 + Synthèse catégories ──────────────────────────────
    pdf.add_page()

    if repartition is not None:
        pdf.h1("Budget Théorique (50/30/20) vs Réel")
        reel_dict = {
            "Besoins réels":  kpis.charges_fixes_annuelles,
            "Loisirs réels":  kpis.variables_reelles,
            "Épargne réelle": kpis.epargne_mensuelle * 12,
        }
        png = _make_png(charts.chart_double_piechart(repartition, reel_dict), 860, 360)
        if png:
            pdf.add_chart(png)
        else:
            pdf.body("(graphique indisponible)")
        pdf.ln(2)

    pdf.h1("Synthèse Annuelle par Catégorie")
    if analyses:
        total_b = sum(a.budgete for a in analyses)
        total_r = sum(a.reel for a in analyses)
        total_e = total_r - total_b

        rows = []
        for a in analyses:
            ecart_cls = _C_NEGATIVE if a.ecart > 0 else (_C_POSITIVE if a.ecart < 0 else _C_TEXT)
            rows.append([
                _strip_emoji(f"{a.categorie_icone} {a.categorie_nom}"),
                f"{a.budgete:,.0f} €",
                f"{a.reel:,.0f} €",
                (f"{a.ecart:+,.0f} €", ecart_cls),
                f"{a.pourcentage_consomme:.1f}%",
            ])

        total_ecart_cls = _C_NEGATIVE if total_e > 0 else _C_POSITIVE
        pdf.table(
            headers=["Catégorie", "Budgété", "Réel", "Écart", "% Consommé"],
            col_widths=[80, 28, 28, 28, 16],
            rows=rows,
            col_aligns=["L", "R", "R", "R", "R"],
            total_row=[
                "Total",
                f"{total_b:,.0f} €",
                f"{total_r:,.0f} €",
                (f"{total_e:+,.0f} €", total_ecart_cls),
                "—",
            ],
        )

        # Pie chart: spending by category
        png = _make_png(charts.chart_categories_piechart(analyses, show_reel=True), 860, 340)
        if png:
            pdf.h2("Répartition des dépenses réelles par catégorie")
            pdf.add_chart(png)
    else:
        pdf.info_box("Aucune catégorie configurée.")

    # ── Page 4: Suivi mensuel ────────────────────────────────────────────────
    if include_mensuel:
        pdf.add_page()
        pdf.h1("Suivi Mensuel")

        active = [s for s in soldes if s.total_revenus > 0 or s.total_variables_reel > 0]
        if active:
            # Colour cards for each active month (solde disponible)
            color_items = []
            for s in active:
                bg = _C_POSITIVE if s.solde_disponible >= 0 else _C_NEGATIVE
                color_items.append((MOIS[s.mois - 1], s.solde_disponible, bg))
            pdf.color_kpi_grid(color_items, cols=4, card_h=20)

            pdf.h2("Récapitulatif par mois")
            rows = []
            for s in soldes:
                if s.total_revenus == 0 and s.total_variables_reel == 0:
                    continue
                s_cls = _C_POSITIVE if s.solde_disponible >= 0 else _C_NEGATIVE
                rows.append([
                    MOIS[s.mois - 1],
                    f"{s.total_revenus:,.0f} €",
                    f"{s.total_charges_fixes:,.0f} €",
                    f"{s.total_epargne:,.0f} €",
                    f"{s.total_variables_budgete:,.0f} €",
                    f"{s.total_variables_reel:,.0f} €",
                    (f"{s.solde_disponible:,.0f} €", s_cls),
                ])
            pdf.table(
                headers=["Mois", "Revenus", "Charges", "Épargne", "Var. budg.", "Var. réel", "Solde"],
                col_widths=[28, 26, 26, 24, 24, 24, 28],
                rows=rows,
                col_aligns=["L", "R", "R", "R", "R", "R", "R"],
            )
        else:
            pdf.info_box("Aucune donnée mensuelle disponible pour cette année.")

    # ── Page 5: Analyses ─────────────────────────────────────────────────────
    if include_heatmap and categories and heatmap_matrix:
        pdf.add_page()
        pdf.h1("Analyses Comparatives")

        cat_labels = [_strip_emoji(f"{c.icone} {c.nom}") for c in categories]
        height_px = max(320, 28 * len(categories) + 80)
        png = _make_png(
            charts.chart_heatmap(cat_labels, MOIS_COURT, heatmap_matrix),
            860, height_px,
        )
        if png:
            pdf.h2("Heatmap des dépenses (€/mois × catégorie)")
            pdf.add_chart(png)
        else:
            pdf.body("(graphique indisponible)")

        # Trends piechart (cumulative year)
        if repartition is not None:
            try:
                n_mois = sum(1 for s in soldes if s.total_revenus > 0) or 1
                from gestion_dashboard.models.budget import Repartition503020
                rep_scaled = Repartition503020(
                    besoins=repartition.besoins * n_mois,
                    loisirs=repartition.loisirs * n_mois,
                    epargne=repartition.epargne * n_mois,
                    salaire=repartition.salaire * n_mois,
                    taux_besoins=repartition.taux_besoins,
                    taux_loisirs=repartition.taux_loisirs,
                    taux_epargne=repartition.taux_epargne,
                )
                reel_dict_year = {
                    "Besoins réels":  sum(s.total_charges_fixes for s in soldes),
                    "Loisirs réels":  sum(s.total_variables_reel for s in soldes),
                    "Épargne réelle": sum(s.total_epargne for s in soldes),
                }
                png = _make_png(charts.chart_double_piechart(rep_scaled, reel_dict_year), 860, 360)
                if png:
                    pdf.h2("Répartition cumulée vs théorique (année en cours)")
                    pdf.add_chart(png)
            except Exception:
                pass

    return bytes(pdf.output())
