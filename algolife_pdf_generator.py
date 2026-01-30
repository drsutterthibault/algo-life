"""
ALGO-LIFE PDF Generator v7.2 ULTRA PREMIUM (LAYOUT+NORMAL+WATCH)
✅ Mise en page améliorée (header/footer, cards, sections)
✅ Ajout section "À surveiller" (dans la norme mais hors zone optimale)
✅ Templates complets: Anormaux / À surveiller / Normaux+Optimaux
✅ Robustesse biomarker_results: dict simple, dict structuré (value/unit/ref), liste
✅ Fix matplotlib alpha clamp + close safe
✅ ReportLab: couleurs hex HTML dans <font color="#RRGGBB">

Compatible avec app.py existant - Garde le nom generate_algolife_pdf_report()

Auteur: Dr Thibault SUTTER
Date: Janvier 2026
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
    PageBreak, Image, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from io import BytesIO
from datetime import datetime
import io
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyBboxPatch, Rectangle


# ============================================================
# THEME
# ============================================================

PREMIUM_THEME = {
    "deep_navy": colors.HexColor("#0A1628"),
    "slate": colors.HexColor("#1E293B"),
    "steel": colors.HexColor("#475569"),
    "mist": colors.HexColor("#94A3B8"),
    "cloud": colors.HexColor("#F8FAFC"),
    "pearl": colors.HexColor("#FFFFFF"),
    "silver": colors.HexColor("#E2E8F0"),
    "emerald": colors.HexColor("#059669"),
    "sapphire": colors.HexColor("#0284C7"),
    "gold": colors.HexColor("#F59E0B"),
    "ruby": colors.HexColor("#DC2626"),
    "emerald_subtle": colors.HexColor("#ECFDF5"),
    "sapphire_subtle": colors.HexColor("#F0F9FF"),
    "gold_subtle": colors.HexColor("#FFFBEB"),
    "ruby_subtle": colors.HexColor("#FEF2F2"),
    "shadow": colors.HexColor("#0B1220"),
}

STATUS_COLORS = {
    "optimal": (PREMIUM_THEME["emerald"], PREMIUM_THEME["emerald_subtle"]),
    "normal": (PREMIUM_THEME["sapphire"], PREMIUM_THEME["sapphire_subtle"]),
    "watch":  (PREMIUM_THEME["gold"], PREMIUM_THEME["gold_subtle"]),
    "low":    (PREMIUM_THEME["gold"], PREMIUM_THEME["gold_subtle"]),
    "high":   (PREMIUM_THEME["ruby"], PREMIUM_THEME["ruby_subtle"]),
    "unknown": (PREMIUM_THEME["steel"], PREMIUM_THEME["cloud"]),
}


# ============================================================
# UTILS
# ============================================================

def clamp01(x: float) -> float:
    try:
        x = float(x)
    except Exception:
        return 0.0
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x

def rl_color_to_hex(c) -> str:
    try:
        r = int(round(c.red * 255))
        g = int(round(c.green * 255))
        b = int(round(c.blue * 255))
        r = max(0, min(255, r))
        g = max(0, min(255, g))
        b = max(0, min(255, b))
        return f"#{r:02X}{g:02X}{b:02X}"
    except Exception:
        return "#0A1628"

def safe_float(x, default=None):
    try:
        return float(x) if x is not None else default
    except Exception:
        return default

def canonicalize_key(raw_key: str) -> str:
    k = (raw_key or "").strip().lower().replace(" ", "_")
    return ALIASES.get(k, k)

def now_str_fr() -> str:
    return datetime.now().strftime("%d/%m/%Y")

def _truncate(s: str, n: int = 34) -> str:
    s = (s or "").strip()
    if len(s) <= n:
        return s
    return s[: n - 1].rstrip() + "…"


# ============================================================
# FONTS
# ============================================================

def register_fonts():
    """
    Option: mets Inter dans /assets/fonts/
    - Inter-Regular.ttf
    - Inter-SemiBold.ttf
    - Inter-Bold.ttf
    """
    try:
        pdfmetrics.registerFont(TTFont("Inter", "assets/fonts/Inter-Regular.ttf"))
        pdfmetrics.registerFont(TTFont("InterSB", "assets/fonts/Inter-SemiBold.ttf"))
        pdfmetrics.registerFont(TTFont("InterB", "assets/fonts/Inter-Bold.ttf"))
        return {"regular": "Inter", "semibold": "InterSB", "bold": "InterB"}
    except Exception:
        return {"regular": "Helvetica", "semibold": "Helvetica-Bold", "bold": "Helvetica-Bold"}


# ============================================================
# BIOMARKER DATABASE (exemple minimal)
# ============================================================

class BiomarkerDatabase:
    def get_reference_ranges(self):
        return {
            "crp": {"unit": "mg/L", "normal": [0.0, 5.0], "optimal": [0.0, 1.0], "category": "Inflammation"},
            "insuline": {"unit": "mU/L", "normal": [3.0, 25.0], "optimal": [3.0, 8.0], "category": "Métabolisme"},
            "homa_index": {"unit": "", "normal": [0.0, 2.5], "optimal": [0.0, 1.0], "category": "Métabolisme"},
            "quicki_index": {"unit": "", "normal": [0.35, 0.45], "optimal": [0.38, 0.45], "category": "Métabolisme"},
            "ferritine": {
                "unit": "µg/L",
                "normal_male": [30.0, 400.0], "normal_female": [15.0, 150.0],
                "optimal_male": [50.0, 150.0], "optimal_female": [30.0, 100.0],
                "category": "Fer",
            },
            "zinc": {"unit": "µg/dL", "normal": [70.0, 150.0], "optimal": [90.0, 130.0], "category": "Micronutriments"},
            "selenium": {"unit": "µg/L", "normal": [70.0, 150.0], "optimal": [100.0, 140.0], "category": "Micronutriments"},
            "magnesium_erythrocytaire": {"unit": "mg/dL", "normal": [4.0, 6.0], "optimal": [5.0, 6.0], "category": "Micronutriments"},
            "glutathion_total": {"unit": "µmol/L", "normal": [900.0, 1750.0], "optimal": [1200.0, 1750.0], "category": "Antioxydants"},
            "coenzyme_q10": {"unit": "µg/L", "normal": [500.0, 1500.0], "optimal": [800.0, 1200.0], "category": "Antioxydants"},
            "gpx": {"unit": "U/g Hb", "normal": [27.5, 73.6], "optimal": [40.0, 65.0], "category": "Antioxydants"},
            "vitamine_d": {"unit": "ng/mL", "normal": [30.0, 100.0], "optimal": [50.0, 80.0], "category": "Vitamines"},
            "vitamine_b12": {"unit": "pg/mL", "normal": [200.0, 900.0], "optimal": [400.0, 700.0], "category": "Vitamines"},
        }

    def classify_biomarker(self, key, value, age=None, sexe=None):
        refs = self.get_reference_ranges()
        if key not in refs:
            return {"status": "unknown", "interpretation": "Référence non disponible"}

        ref = refs[key]
        try:
            val = float(value)
        except Exception:
            return {"status": "unknown", "interpretation": "Valeur invalide"}

        # normal/optimal sex-specific
        if sexe == "Masculin" and "normal_male" in ref:
            normal = ref["normal_male"]
            optimal = ref.get("optimal_male", ref.get("optimal"))
        elif sexe == "Féminin" and "normal_female" in ref:
            normal = ref["normal_female"]
            optimal = ref.get("optimal_female", ref.get("optimal"))
        else:
            normal = ref.get("normal", [0, 100])
            optimal = ref.get("optimal")

        unit = ref.get("unit", "")

        # Status "optimal"
        if optimal and len(optimal) == 2 and optimal[0] <= val <= optimal[1]:
            return {"status": "optimal", "interpretation": f"Valeur optimale ({val:.2f} {unit})"}

        # Status "normal" (dans la norme)
        if normal and len(normal) == 2 and normal[0] <= val <= normal[1]:
            return {"status": "normal", "interpretation": f"Valeur normale ({val:.2f} {unit})"}

        # low/high
        if val < normal[0]:
            deficit = ((normal[0] - val) / normal[0]) * 100 if normal[0] else 0
            return {"status": "low", "interpretation": f"Valeur basse ({val:.2f} {unit}). Déficit ~{deficit:.0f}%"}
        excess = ((val - normal[1]) / normal[1]) * 100 if normal[1] else 0
        return {"status": "high", "interpretation": f"Valeur élevée ({val:.2f} {unit}). Excès ~{excess:.0f}%"}


# ============================================================
# INPUT NORMALIZATION (robuste)
# ============================================================

def normalize_patient(patient_data):
    if not isinstance(patient_data, dict):
        return {}
    return patient_data.get("patient_info", patient_data)

def normalize_biomarkers(biomarker_results):
    """
    Supporte :
      1) dict simple: {"crp": 1.2, "zinc": 90}
      2) dict structuré: {"crp": {"value":1.2,"unit":"mg/L","ref_low":0,"ref_high":5}, ...}
      3) list: [{"key":"crp","value":1.2,"unit":"mg/L"}, ...]
    Retour:
      mode, dict_simple, list_items
    """
    # dict
    if isinstance(biomarker_results, dict):
        # détecte dict structuré
        structured = False
        for v in biomarker_results.values():
            if isinstance(v, dict) and ("value" in v or "unit" in v or "ref_low" in v or "ref_high" in v):
                structured = True
                break

        if not structured:
            return "dict_simple", biomarker_results, []

        # convert structuré -> liste
        cleaned = []
        for k, v in biomarker_results.items():
            if isinstance(v, dict):
                cleaned.append({
                    "key": k,
                    "name": v.get("name") or str(k).replace("_", " ").title(),
                    "value": v.get("value"),
                    "unit": v.get("unit", ""),
                    "ref_low": v.get("ref_low"),
                    "ref_high": v.get("ref_high"),
                    "ref_type": v.get("ref_type"),
                })
            else:
                cleaned.append({"key": k, "name": str(k).replace("_", " ").title(), "value": v, "unit": ""})
        return "list", {}, cleaned

    # list
    if isinstance(biomarker_results, list):
        cleaned = []
        for it in biomarker_results:
            if not isinstance(it, dict):
                continue
            cleaned.append({
                "key": it.get("key") or it.get("biomarker_key") or "—",
                "name": it.get("name") or (it.get("key") or "—").replace("_", " ").title(),
                "value": it.get("value"),
                "unit": it.get("unit", ""),
                "ref_low": it.get("ref_low"),
                "ref_high": it.get("ref_high"),
                "ref_type": it.get("ref_type"),
            })
        return "list", {}, cleaned

    return "unknown", {}, []


ALIASES = {
    "crp_us": "crp", "hs_crp": "crp", "insulin": "insuline",
    "homa": "homa_index", "quicki": "quicki_index",
    "ferritin": "ferritine", "zn": "zinc", "se": "selenium",
    "vit_d": "vitamine_d", "vitamin_d": "vitamine_d",
}


# ============================================================
# MATPLOTLIB VISUALS
# ============================================================

def create_bioage_ultra_premium(bio_age, chrono_age):
    """Visuel âge biologique ultra premium (alpha safe)"""
    b = safe_float(bio_age, 45.0)
    c = safe_float(chrono_age, 45.0)
    delta = b - c

    if delta <= -2:
        main_color = "#059669"
        bg_color = "#ECFDF5"
        label = "Âge biologique OPTIMAL"
        sublabel = "Plus jeune que l'âge chronologique"
    elif delta <= 2:
        main_color = "#0284C7"
        bg_color = "#F0F9FF"
        label = "Âge biologique ÉQUILIBRÉ"
        sublabel = "En ligne avec l'âge chronologique"
    else:
        main_color = "#F59E0B"
        bg_color = "#FFFBEB"
        label = "Âge biologique ÉLEVÉ"
        sublabel = "Nécessite attention"

    fig = plt.figure(figsize=(9.5, 4.2), facecolor="white")

    ax1 = fig.add_axes([0.02, 0.08, 0.42, 0.84])
    ax1.set_aspect("equal")
    ax1.axis("off")
    ax1.set_xlim(-1.4, 1.4)
    ax1.set_ylim(-1.4, 1.4)

    bg_circle = Circle((0, 0), 1.38, color=bg_color, alpha=0.3, zorder=1)
    ax1.add_patch(bg_circle)

    outer_ring = Circle((0, 0), 1.15, fill=False, edgecolor="#E2E8F0", linewidth=3, zorder=2)
    ax1.add_patch(outer_ring)

    for r in np.linspace(0.95, 1.05, 8):
        alpha_val = 0.15 + (1.05 - r) * 0.85 / 0.1
        alpha_val = clamp01(alpha_val)
        ring = Circle((0, 0), r, fill=False, edgecolor=main_color, linewidth=2.5, alpha=alpha_val, zorder=3)
        ax1.add_patch(ring)

    center = Circle((0, 0), 0.88, color="white", zorder=4)
    ax1.add_patch(center)

    ax1.text(0, 0.22, f"{b:.1f}", ha="center", va="center",
             fontsize=42, fontweight="bold", color=main_color, zorder=5)
    ax1.text(0, -0.18, "Âge biologique", ha="center", va="center",
             fontsize=11, color="#64748B", fontweight="600", zorder=5)
    ax1.text(0, -0.38, "(années)", ha="center", va="center",
             fontsize=9, color="#94A3B8", zorder=5)

    delta_x, delta_y = 0.75, 0.75
    delta_symbol = "▼" if delta < 0 else "▲" if delta > 0 else "●"
    ax1.text(delta_x, delta_y, delta_symbol, ha="center", va="center",
             fontsize=16, color=main_color, alpha=0.8, zorder=6)
    ax1.text(delta_x, delta_y - 0.18, f"{delta:+.1f}", ha="center", va="center",
             fontsize=9, fontweight="bold", color=main_color, zorder=6)

    ax2 = fig.add_axes([0.48, 0.08, 0.50, 0.84])
    ax2.axis("off")
    ax2.set_xlim(0, 1)
    ax2.set_ylim(0, 1)

    ax2.text(0.02, 0.88, label, fontsize=16, fontweight="bold",
             color="#0A1628", va="top")

    box = FancyBboxPatch(
        (0, 0.72), 0.96, 0.10,
        boxstyle="round,pad=0.01",
        edgecolor=main_color, facecolor=bg_color,
        linewidth=1.5, alpha=0.6
    )
    ax2.add_patch(box)
    ax2.text(0.48, 0.77, sublabel, fontsize=11, fontweight="600",
             color=main_color, ha="center", va="center")

    y_pos = 0.58
    ax2.text(0.02, y_pos, "Âge chronologique", fontsize=10, color="#64748B")
    ax2.text(0.98, y_pos, f"{c:.1f} ans", fontsize=12, fontweight="bold",
             color="#1E293B", ha="right")

    y_pos -= 0.14
    ax2.text(0.02, y_pos, "Âge biologique", fontsize=10, color="#64748B")
    ax2.text(0.98, y_pos, f"{b:.1f} ans", fontsize=12, fontweight="bold",
             color=main_color, ha="right")

    y_pos -= 0.14
    ax2.text(0.02, y_pos, "Différence", fontsize=10, color="#64748B")
    ax2.text(0.98, y_pos, f"{delta:+.1f} ans", fontsize=13, fontweight="bold",
             color=main_color, ha="right")

    y_pos -= 0.18
    timeline_y = y_pos
    ax2.plot([0.08, 0.92], [timeline_y, timeline_y], color="#CBD5E1",
             linewidth=3, solid_capstyle="round", zorder=1)

    chron_pos = 0.5
    bio_offset = (delta / 20.0) * 0.4
    bio_pos = np.clip(chron_pos + bio_offset, 0.08, 0.92)

    ax2.plot([chron_pos], [timeline_y], "o", markersize=9, color="#64748B",
             markeredgecolor="white", markeredgewidth=2, zorder=3)
    ax2.text(chron_pos, timeline_y - 0.06, f"{c:.0f}", ha="center",
             fontsize=8, color="#64748B", fontweight="600")

    ax2.plot([bio_pos], [timeline_y], "o", markersize=12, color=main_color,
             markeredgecolor="white", markeredgewidth=2.5, zorder=4)
    ax2.text(bio_pos, timeline_y + 0.06, f"{b:.0f}", ha="center",
             fontsize=9, color=main_color, fontweight="bold")

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=240, bbox_inches="tight",
                facecolor="white", edgecolor="none")
    buf.seek(0)
    plt.close(fig)
    return buf


def create_gauge_vertical_premium(name, value, ref_min, ref_max,
                                  opt_min=None, opt_max=None, unit="", status="normal"):
    """Jauge verticale premium (alpha safe)"""
    v = safe_float(value, 0.0)
    rmin = safe_float(ref_min, 0.0)
    rmax = safe_float(ref_max, rmin + 1.0)
    if rmax <= rmin:
        rmax = rmin + 1.0

    total = rmax - rmin
    pos_norm = np.clip((v - rmin) / total, 0, 1)

    if status == "optimal":
        main_col = "#059669"
    elif status == "normal":
        main_col = "#0284C7"
    elif status == "watch":
        main_col = "#F59E0B"
    elif status == "low":
        main_col = "#F59E0B"
    elif status == "high":
        main_col = "#DC2626"
    else:
        main_col = "#64748B"

    fig, ax = plt.subplots(figsize=(1.8, 3.55), facecolor="white")
    ax.set_xlim(-0.58, 0.58)
    ax.set_ylim(-0.12, 1.18)
    ax.axis("off")

    track_width = 0.18
    track = Rectangle(
        (-track_width / 2, 0), track_width, 1.0,
        facecolor="#F1F5F9", edgecolor="#E2E8F0",
        linewidth=1.5, zorder=1
    )
    ax.add_patch(track)

    # zone optimale
    if opt_min is not None and opt_max is not None:
        omin = safe_float(opt_min, None)
        omax = safe_float(opt_max, None)
        if omin is not None and omax is not None and omax > omin:
            opt_start = np.clip((omin - rmin) / total, 0, 1)
            opt_height = np.clip((omax - omin) / total, 0, 1 - opt_start)
            opt_zone = Rectangle(
                (-track_width / 2, opt_start), track_width, opt_height,
                facecolor="#D1FAE5", edgecolor="none",
                alpha=0.45, zorder=2
            )
            ax.add_patch(opt_zone)

    # segments
    n_segments = 26
    for i in range(int(pos_norm * n_segments)):
        seg_y = i / n_segments
        seg_h = 1.0 / n_segments
        alpha_val = clamp01(0.28 + (i / n_segments) * 0.72)
        seg = Rectangle(
            (-track_width / 2, seg_y), track_width, seg_h,
            facecolor=main_col, edgecolor="none",
            alpha=alpha_val, zorder=3
        )
        ax.add_patch(seg)

    marker = Circle((0, pos_norm), 0.12, facecolor=main_col,
                    edgecolor="white", linewidth=2.5, zorder=6)
    ax.add_patch(marker)

    pulse = Circle((0, pos_norm), 0.18, fill=False,
                   edgecolor=main_col, linewidth=2,
                   alpha=0.35, zorder=5)
    ax.add_patch(pulse)

    ax.text(0, 1.085, _truncate(name, 24), ha="center", va="bottom",
            fontsize=9, fontweight="bold", color="#0A1628")

    ax.text(0, pos_norm, f"{v:.1f}", ha="center", va="center",
            fontsize=8.6, fontweight="bold", color="white", zorder=7)

    if unit:
        ax.text(0.33, pos_norm, unit, ha="left", va="center",
                fontsize=7.4, color=main_col, fontweight="600")

    ax.text(-0.37, 0, f"{rmin:.0f}", ha="right", va="center",
            fontsize=7, color="#94A3B8")
    ax.text(-0.37, 1.0, f"{rmax:.0f}", ha="right", va="center",
            fontsize=7, color="#94A3B8")

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=220, bbox_inches="tight",
                facecolor="white", transparent=True)
    buf.seek(0)
    plt.close(fig)
    return buf


def create_category_bars_premium(category_scores):
    """Barres catégories premium"""
    fig, ax = plt.subplots(figsize=(9.0, 5.2), facecolor="white")

    cats = list(category_scores.keys())
    vals = [safe_float(category_scores[k], 0.0) for k in cats]
    cats = cats[::-1]
    vals = vals[::-1]
    y_pos = np.arange(len(cats))

    colors_list = []
    for v in vals:
        if v >= 90:
            colors_list.append("#059669")
        elif v >= 80:
            colors_list.append("#0284C7")
        elif v >= 70:
            colors_list.append("#F59E0B")
        else:
            colors_list.append("#DC2626")

    ax.barh(y_pos, vals, height=0.65, color=colors_list,
            edgecolor="white", linewidth=2.5, alpha=0.92)

    for yi, v, c in zip(y_pos, vals, colors_list):
        ax.text(v + 1.8, yi, f"{v:.1f}", va="center", ha="left",
                fontsize=10, fontweight="bold", color=c)

    ax.set_yticks(y_pos)
    ax.set_yticklabels([c.replace("_", " ").title() for c in cats],
                       fontsize=10, fontweight="600", color="#1E293B")

    ax.set_xlim(0, 108)
    ax.set_xlabel("Score (/100)", fontsize=11, fontweight="bold",
                  color="#0A1628", labelpad=10)

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#E2E8F0")
    ax.spines["bottom"].set_color("#E2E8F0")
    ax.grid(axis="x", alpha=0.12, linestyle="--", linewidth=1, color="#CBD5E1")
    ax.tick_params(colors="#64748B", labelsize=9)

    buf = io.BytesIO()
    plt.tight_layout(pad=0.8)
    plt.savefig(buf, format="png", dpi=220, bbox_inches="tight", facecolor="white")
    buf.seek(0)
    plt.close(fig)
    return buf


# ============================================================
# REPORTLAB UI
# ============================================================

def _make_styles(font_map):
    base = getSampleStyleSheet()

    styles = {}
    styles["title"] = ParagraphStyle(
        "AL_Title",
        fontName=font_map["bold"], fontSize=34,
        textColor=PREMIUM_THEME["deep_navy"],
        alignment=TA_CENTER, spaceAfter=4, leading=40
    )
    styles["subtitle"] = ParagraphStyle(
        "AL_Subtitle",
        fontName=font_map["regular"], fontSize=12,
        textColor=PREMIUM_THEME["steel"],
        alignment=TA_CENTER, spaceAfter=16, leading=16
    )
    styles["body"] = ParagraphStyle(
        "AL_Body",
        fontName=font_map["regular"], fontSize=10,
        textColor=PREMIUM_THEME["slate"],
        leading=15
    )
    styles["body_small"] = ParagraphStyle(
        "AL_BodySmall",
        fontName=font_map["regular"], fontSize=9,
        textColor=PREMIUM_THEME["steel"],
        leading=13
    )
    styles["micro"] = ParagraphStyle(
        "AL_Micro",
        fontName=font_map["regular"], fontSize=8.6,
        textColor=PREMIUM_THEME["mist"],
        leading=11.5
    )
    styles["kpi"] = ParagraphStyle(
        "AL_KPI",
        fontName=font_map["bold"], fontSize=18,
        textColor=PREMIUM_THEME["deep_navy"],
        alignment=TA_CENTER,
        leading=20
    )
    styles["kpi_label"] = ParagraphStyle(
        "AL_KPI_Label",
        fontName=font_map["semibold"], fontSize=9,
        textColor=PREMIUM_THEME["steel"],
        alignment=TA_CENTER,
        leading=11
    )
    styles["section"] = ParagraphStyle(
        "AL_Section",
        fontName=font_map["bold"],
        fontSize=16,
        textColor=PREMIUM_THEME["deep_navy"],
        spaceBefore=14,
        spaceAfter=10,
        leading=20
    )
    styles["section_small"] = ParagraphStyle(
        "AL_SectionSmall",
        fontName=font_map["bold"],
        fontSize=13,
        textColor=PREMIUM_THEME["deep_navy"],
        spaceBefore=10,
        spaceAfter=8,
        leading=16
    )
    return styles


def premium_section_title(text, styles, size=16):
    if size >= 16:
        return Paragraph(text, styles["section"])
    # clone léger
    st = ParagraphStyle(
        f"AL_Section_{size}_{abs(hash(text))}",
        parent=styles["section_small"],
        fontSize=size,
        leading=size * 1.25
    )
    return Paragraph(text, st)


def premium_card(content_rows, col_widths, bg=PREMIUM_THEME["pearl"], border=PREMIUM_THEME["silver"]):
    t = Table(content_rows, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("BOX", (0, 0), (-1, -1), 1.15, border),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return t


def divider_line(width_mm=170):
    t = Table([[""]], colWidths=[width_mm * mm], rowHeights=[0.55 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), PREMIUM_THEME["silver"]),
    ]))
    return t


def kpi_row(kpis, styles):
    """
    kpis: list of (label, value_str, status_key)
    """
    cells = []
    colw = []
    for label, val, stt in kpis:
        col, bg = STATUS_COLORS.get(stt, STATUS_COLORS["unknown"])
        cell = Table(
            [[Paragraph(val, styles["kpi"])],
             [Paragraph(label, styles["kpi_label"])]],
            colWidths=[42.0 * mm]
        )
        cell.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), bg),
            ("BOX", (0, 0), (-1, -1), 1.1, col),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        cells.append(cell)
        colw.append(43.0 * mm)

    row = Table([cells], colWidths=colw)
    row.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    return row


# ============================================================
# HEADER / FOOTER
# ============================================================

def _draw_header_footer(canvas, doc, font_map):
    canvas.saveState()

    # header line
    canvas.setStrokeColor(PREMIUM_THEME["silver"])
    canvas.setLineWidth(0.7)
    canvas.line(doc.leftMargin, A4[1] - doc.topMargin + 6*mm, A4[0] - doc.rightMargin, A4[1] - doc.topMargin + 6*mm)

    # header text
    canvas.setFillColor(PREMIUM_THEME["steel"])
    canvas.setFont(font_map["semibold"], 9)
    canvas.drawString(doc.leftMargin, A4[1] - doc.topMargin + 9*mm, "ALGO-LIFE — Rapport Premium")
    canvas.setFont(font_map["regular"], 8.5)
    canvas.drawRightString(A4[0] - doc.rightMargin, A4[1] - doc.topMargin + 9*mm, now_str_fr())

    # footer
    canvas.setStrokeColor(PREMIUM_THEME["silver"])
    canvas.setLineWidth(0.7)
    canvas.line(doc.leftMargin, doc.bottomMargin - 6*mm, A4[0] - doc.rightMargin, doc.bottomMargin - 6*mm)

    canvas.setFillColor(PREMIUM_THEME["mist"])
    canvas.setFont(font_map["regular"], 8.2)
    canvas.drawString(doc.leftMargin, doc.bottomMargin - 10*mm, "© 2026 — Document médical confidentiel")
    canvas.drawRightString(A4[0] - doc.rightMargin, doc.bottomMargin - 10*mm, f"Page {doc.page}")

    canvas.restoreState()


# ============================================================
# BIOMARKERS: bounds & watch logic
# ============================================================

def get_bounds(ref_data, sexe):
    # normal bounds
    if isinstance(ref_data.get("normal"), (list, tuple)):
        rmin, rmax = ref_data["normal"]
    elif sexe == "Masculin" and isinstance(ref_data.get("normal_male"), (list, tuple)):
        rmin, rmax = ref_data["normal_male"]
    elif sexe == "Féminin" and isinstance(ref_data.get("normal_female"), (list, tuple)):
        rmin, rmax = ref_data["normal_female"]
    else:
        rmin, rmax = 0, 100

    omin, omax = None, None
    if isinstance(ref_data.get("optimal"), (list, tuple)):
        omin, omax = ref_data["optimal"]
    elif sexe == "Masculin" and isinstance(ref_data.get("optimal_male"), (list, tuple)):
        omin, omax = ref_data["optimal_male"]
    elif sexe == "Féminin" and isinstance(ref_data.get("optimal_female"), (list, tuple)):
        omin, omax = ref_data["optimal_female"]

    return rmin, rmax, omin, omax


def compute_watch_status(classification_status: str, value: float, ref_data: dict, sexe: str) -> str:
    """
    Règle simple:
      - optimal -> optimal
      - low/high -> low/high
      - normal mais hors optimal -> watch
      - normal et dans optimal -> optimal (si DB l'a pas déjà classé)
    """
    stt = (classification_status or "unknown").lower()
    if stt in ("low", "high", "unknown"):
        return stt
    if stt == "optimal":
        return "optimal"

    # stt == "normal" -> check optimal zone
    rmin, rmax, omin, omax = get_bounds(ref_data, sexe)
    if omin is not None and omax is not None:
        if omin <= value <= omax:
            return "optimal"
        return "watch"
    # pas d'optimal => normal classique
    return "normal"


def biomarker_sort_key(item):
    # ordre: high/low -> watch -> normal -> optimal
    st = item.get("status_final", "unknown")
    order = {"high": 0, "low": 0, "watch": 1, "normal": 2, "optimal": 3, "unknown": 4}
    return (order.get(st, 9), item.get("name", ""))


def render_biomarker_grid(story, items, title, styles, font_map, sexe, max_items=24):
    if not items:
        return

    story.append(premium_section_title(title, styles, size=13))
    story.append(Spacer(1, 3.5 * mm))

    # 4 gauges per row
    items = items[:max_items]
    for i in range(0, len(items), 4):
        batch = items[i:i+4]
        cells = []

        for it in batch:
            ref_data = it["ref_data"]
            rmin, rmax, omin, omax = get_bounds(ref_data, sexe)

            gauge_img = create_gauge_vertical_premium(
                it["name"], it["value"],
                rmin, rmax, omin, omax,
                it["unit"], status=it["status_final"]
            )

            stt = it["status_final"]
            col, bg = STATUS_COLORS.get(stt, STATUS_COLORS["unknown"])
            col_hex = rl_color_to_hex(col)

            # mini caption card under the gauge
            caption = Paragraph(
                f"<b>{_truncate(it['name'], 26)}</b><br/>"
                f"<font color='{col_hex}'><b>{it['value']:.2f}</b></font> {it['unit']}<br/>"
                f"<font size=8 color='#64748B'>{it.get('interpretation','')}</font>",
                ParagraphStyle(
                    f"AL_Cap_{abs(hash(it['name']))}",
                    fontName=font_map["regular"],
                    fontSize=8.6,
                    leading=10.5,
                    textColor=PREMIUM_THEME["slate"],
                    alignment=TA_CENTER,
                )
            )

            block = Table(
                [[Image(gauge_img, width=40*mm, height=62*mm)],
                 [caption]],
                colWidths=[42.5*mm]
            )
            block.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), PREMIUM_THEME["pearl"]),
                ("BOX", (0, 0), (-1, -1), 1.0, PREMIUM_THEME["silver"]),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]))

            cells.append(KeepTogether([block]))

        while len(cells) < 4:
            cells.append(Spacer(1, 1))

        row = Table([cells], colWidths=[42.5*mm]*4)
        row.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ]))
        story.append(row)
        story.append(Spacer(1, 4.2 * mm))


# ============================================================
# MAIN GENERATOR - COMPAT APP.PY
# ============================================================

def generate_algolife_pdf_report(
    patient_data,
    biomarker_results,
    engine_results=None,   # legacy
    chart_buffer=None,     # legacy
    health_score=None,
    biological_age=None,
    nutritional_needs=None,
    recommendations=None,
    biomarker_db=None,
    max_gauges_abnormal=30,
    max_gauges_watch=25,
    max_gauges_normal=18,
):
    """
    ⭐ Générateur PDF ULTRA PREMIUM v7.2
    Compatible avec app.py existant
    """
    if biomarker_db is None:
        biomarker_db = BiomarkerDatabase()

    font_map = register_fonts()
    styles = _make_styles(font_map)

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        leftMargin=18 * mm,
        rightMargin=18 * mm
    )

    patient_info = normalize_patient(patient_data)
    sexe = patient_info.get("sexe", patient_info.get("sex", "—"))

    mode, biomarkers_dict, biomarkers_list = normalize_biomarkers(biomarker_results)

    story = []

    # ========================================================
    # COVER
    # ========================================================
    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph("ALGO-LIFE", styles["title"]))
    story.append(Paragraph(
        "Analyse Multimodale de Santé Fonctionnelle — Rapport Premium",
        styles["subtitle"]
    ))

    meta = [[
        Paragraph(f"<b>Date du rapport</b><br/>{now_str_fr()}", styles["micro"]),
        Paragraph("<b>Version</b><br/>v7.2 Premium", styles["micro"]),
        Paragraph("<b>Confidentialité</b><br/>Données médicales", styles["micro"]),
    ]]
    story.append(premium_card(meta, [55 * mm, 55 * mm, 55 * mm]))
    story.append(Spacer(1, 10 * mm))

    # ========================================================
    # PATIENT CARD
    # ========================================================
    story.append(premium_section_title("Informations Patient", styles, size=16))

    p_data = [
        [Paragraph("<b>PATIENT</b>", styles["micro"]),
         Paragraph(patient_info.get("nom", patient_info.get("name", "—")), styles["body"])],
        [Paragraph("<b>GENRE</b>", styles["micro"]),
         Paragraph(sexe, styles["body"])],
        [Paragraph("<b>ÂGE</b>", styles["micro"]),
         Paragraph(f"{patient_info.get('age', '—')} ans", styles["body"])],
        [Paragraph("<b>TAILLE / POIDS</b>", styles["micro"]),
         Paragraph(f"{patient_info.get('height', '—')} cm / {patient_info.get('weight', '—')} kg", styles["body"])],
        [Paragraph("<b>IMC</b>", styles["micro"]),
         Paragraph(f"{patient_info.get('imc', '—')}", styles["body"])],
        [Paragraph("<b>DATE PRÉLÈVEMENT</b>", styles["micro"]),
         Paragraph(patient_info.get("prelevement_date", "—"), styles["body"])],
    ]
    story.append(premium_card(p_data, [48 * mm, 122 * mm]))
    story.append(Spacer(1, 10 * mm))

    # ========================================================
    # BIO AGE + SCORE
    # ========================================================
    story.append(premium_section_title("Âge Biologique & Score Santé", styles, size=18))

    if biological_age:
        hero_img = create_bioage_ultra_premium(
            biological_age.get("biological_age"),
            biological_age.get("chronological_age")
        )
        story.append(Image(hero_img, width=170 * mm, height=75 * mm))

    story.append(Spacer(1, 8 * mm))

    score_val = safe_float((health_score or {}).get("global_score"), 0) or 0.0
    grade = (health_score or {}).get("grade", "—")

    if score_val >= 90:
        score_col = PREMIUM_THEME["emerald"]
        score_bg = PREMIUM_THEME["emerald_subtle"]
        score_stt = "optimal"
    elif score_val >= 75:
        score_col = PREMIUM_THEME["sapphire"]
        score_bg = PREMIUM_THEME["sapphire_subtle"]
        score_stt = "normal"
    else:
        score_col = PREMIUM_THEME["gold"]
        score_bg = PREMIUM_THEME["gold_subtle"]
        score_stt = "watch"

    score_hex = rl_color_to_hex(score_col)

    score_para = Paragraph(
        f"<b>Score Santé Global</b><br/>"
        f"<font size=28 color='{score_hex}'><b>{score_val:.1f}/100</b></font><br/>"
        f"<font size=12 color='#1E293B'>Grade <b>{grade}</b></font>",
        ParagraphStyle(
            "AL_Score",
            fontName=font_map["bold"],
            fontSize=12,
            leading=16,
            alignment=TA_CENTER,
            textColor=PREMIUM_THEME["deep_navy"],
        )
    )
    score_table = Table([[score_para]], colWidths=[170 * mm])
    score_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), score_bg),
        ("BOX", (0, 0), (0, 0), 1.25, score_col),
        ("LEFTPADDING", (0, 0), (0, 0), 12),
        ("RIGHTPADDING", (0, 0), (0, 0), 12),
        ("TOPPADDING", (0, 0), (0, 0), 12),
        ("BOTTOMPADDING", (0, 0), (0, 0), 12),
    ]))
    story.append(score_table)
    story.append(Spacer(1, 8 * mm))

    # KPI row
    story.append(kpi_row([
        ("Âge bio", f"{safe_float((biological_age or {}).get('biological_age'), 0):.1f} ans", score_stt),
        ("Âge chrono", f"{safe_float((biological_age or {}).get('chronological_age'), 0):.1f} ans", "normal"),
        ("Grade", str(grade), score_stt),
        ("Rapport", now_str_fr(), "normal"),
    ], styles))
    story.append(Spacer(1, 8 * mm))

    # Category chart
    if health_score and health_score.get("category_scores"):
        story.append(premium_section_title("Scores par Catégorie", styles, size=14))
        bars_img = create_category_bars_premium(health_score["category_scores"])
        story.append(Image(bars_img, width=170 * mm, height=98 * mm))

    story.append(PageBreak())

    # ========================================================
    # BIOMARKERS
    # ========================================================
    story.append(premium_section_title("Biomarqueurs — Analyse Détaillée", styles, size=18))
    story.append(Paragraph(
        "Jauges verticales avec zones optimales. Les biomarqueurs « à surveiller » sont dans la norme mais hors zone optimale.",
        styles["micro"]
    ))
    story.append(Spacer(1, 6 * mm))

    refs_db = biomarker_db.get_reference_ranges()

    abnormal = []
    watch = []
    normal = []
    optimal = []

    # iterable
    if mode == "dict_simple":
        iterable = [(k, v, None, None) for k, v in biomarkers_dict.items()]
    elif mode == "list":
        iterable = [(it.get("key"), it.get("value"), it.get("unit"), (it.get("ref_low"), it.get("ref_high"))) for it in biomarkers_list]
    else:
        iterable = []

    for raw_key, value, unit_from_input, ref_from_input in iterable:
        if raw_key is None:
            continue

        key = canonicalize_key(str(raw_key))
        if key not in refs_db:
            continue

        v = safe_float(value, None)
        if v is None:
            continue

        ref_data = refs_db[key]
        unit = ref_data.get("unit", "") or (unit_from_input or "")

        cls = biomarker_db.classify_biomarker(key, v, patient_info.get("age"), sexe)
        stt = (cls.get("status") or "unknown").lower()

        stt_final = compute_watch_status(stt, v, ref_data, sexe)

        item = {
            "key": key,
            "name": key.replace("_", " ").title(),
            "value": v,
            "unit": unit,
            "classification": cls,
            "interpretation": cls.get("interpretation", ""),
            "ref_data": ref_data,
            "status_final": stt_final,
        }

        if stt_final in ("low", "high"):
            abnormal.append(item)
        elif stt_final == "watch":
            watch.append(item)
        elif stt_final == "optimal":
            optimal.append(item)
        elif stt_final == "normal":
            normal.append(item)
        else:
            # unknown -> on le met en watch pour visibilité, sinon perdu
            watch.append(item)

    abnormal.sort(key=biomarker_sort_key)
    watch.sort(key=biomarker_sort_key)
    normal.sort(key=biomarker_sort_key)
    optimal.sort(key=biomarker_sort_key)

    # Summary KPI cards
    story.append(kpi_row([
        ("Anormaux", str(len(abnormal)), "high" if len(abnormal) else "normal"),
        ("À surveiller", str(len(watch)), "watch" if len(watch) else "normal"),
        ("Normaux", str(len(normal)), "normal"),
        ("Optimaux", str(len(optimal)), "optimal"),
    ], styles))
    story.append(Spacer(1, 6 * mm))
    story.append(divider_line())
    story.append(Spacer(1, 6 * mm))

    # Sections
    render_biomarker_grid(
        story, abnormal,
        "⚠️ Biomarqueurs Anormaux",
        styles, font_map, sexe,
        max_items=max_gauges_abnormal
    )
    render_biomarker_grid(
        story, watch,
        "👁️ Biomarqueurs À Surveiller",
        styles, font_map, sexe,
        max_items=max_gauges_watch
    )
    render_biomarker_grid(
        story, normal,
        "✅ Biomarqueurs Normaux",
        styles, font_map, sexe,
        max_items=max_gauges_normal
    )
    render_biomarker_grid(
        story, optimal,
        "⭐ Biomarqueurs Optimaux",
        styles, font_map, sexe,
        max_items=max_gauges_normal
    )

    story.append(PageBreak())

    # ========================================================
    # NUTRITION
    # ========================================================
    if nutritional_needs:
        story.append(premium_section_title("Besoins Nutritionnels", styles, size=16))

        nutri_data = [
            [Paragraph("<b>Métrique</b>", styles["micro"]), Paragraph("<b>Valeur</b>", styles["micro"])],
            [Paragraph("BMR", styles["body"]), Paragraph(f"{safe_float(nutritional_needs.get('bmr'), 0):.0f} kcal/j", styles["body"])],
            [Paragraph("DET", styles["body"]), Paragraph(f"{safe_float(nutritional_needs.get('det'), 0):.0f} kcal/j", styles["body"])],
            [Paragraph("Protéines", styles["body"]), Paragraph(f"{safe_float(nutritional_needs.get('proteins_g'), 0):.0f} g/j", styles["body"])],
            [Paragraph("Lipides", styles["body"]), Paragraph(f"{safe_float(nutritional_needs.get('lipids_g'), 0):.0f} g/j", styles["body"])],
            [Paragraph("Glucides", styles["body"]), Paragraph(f"{safe_float(nutritional_needs.get('carbs_g'), 0):.0f} g/j", styles["body"])],
        ]
        story.append(premium_card(nutri_data, [70 * mm, 100 * mm]))
        story.append(Spacer(1, 8 * mm))

    # ========================================================
    # RECOMMENDATIONS
    # ========================================================
    if recommendations:
        story.append(premium_section_title("Recommandations Personnalisées", styles, size=16))

        recs = recommendations.get("recommendations", {}) if isinstance(recommendations, dict) else {}
        priorities = recommendations.get("priorities", []) if isinstance(recommendations, dict) else []

        if priorities:
            story.append(Paragraph("<b>Priorités</b>", styles["body"]))
            for i, p in enumerate(priorities[:6], 1):
                story.append(Paragraph(
                    f"{i}. <b>{str(p.get('biomarker', '—')).replace('_', ' ').title()}</b> — {p.get('priority', '—')}",
                    styles["body"]
                ))
            story.append(Spacer(1, 5 * mm))

        if recs.get("supplements"):
            story.append(Paragraph("<b>Micronutrition</b>", styles["body"]))
            for s in recs["supplements"][:12]:
                story.append(Paragraph(f"• {s}", styles["body_small"]))
            story.append(Spacer(1, 5 * mm))

        if recs.get("alimentation"):
            story.append(Paragraph("<b>Alimentation</b>", styles["body"]))
            for a in recs["alimentation"][:12]:
                story.append(Paragraph(f"• {a}", styles["body_small"]))

    # ========================================================
    # FOOTER BLOCK (content)
    # ========================================================
    story.append(Spacer(1, 12 * mm))
    story.append(divider_line())
    story.append(Spacer(1, 6 * mm))

    footer_style = ParagraphStyle(
        "AL_FooterBlock",
        fontName=font_map["regular"],
        fontSize=8.5,
        textColor=PREMIUM_THEME["mist"],
        alignment=TA_CENTER,
        leading=12
    )
    story.append(Paragraph("<b>Rapport établi par Dr Thibault SUTTER — Biologiste</b>", footer_style))
    story.append(Paragraph("ALGO-LIFE | Plateforme Multimodale d'Analyse de Santé Fonctionnelle", footer_style))

    # ========================================================
    # BUILD
    # ========================================================
    try:
        doc.build(
            story,
            onFirstPage=lambda c, d: _draw_header_footer(c, d, font_map),
            onLaterPages=lambda c, d: _draw_header_footer(c, d, font_map),
        )
        buffer.seek(0)
        return buffer
    except Exception as e:
        # fallback minimal
        buffer = BytesIO()
        doc2 = SimpleDocTemplate(buffer, pagesize=A4)
        doc2.build([Paragraph(f"ERREUR: {str(e)}", getSampleStyleSheet()["Normal"])])
        buffer.seek(0)
        return buffer


__all__ = ["generate_algolife_pdf_report", "BiomarkerDatabase"]

if __name__ == "__main__":
    print("✅ ALGO-LIFE PDF Generator v7.2 ULTRA PREMIUM")
    print("🔧 Compatible app.py - Fonction: generate_algolife_pdf_report()")
