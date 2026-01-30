"""
ALGO-LIFE PDF Generator - Version Premium v6.0 (HIGH-END TEMPLATE)
✅ Upgrade: jauges affichées pour biomarqueurs normaux + watch + anormaux
✅ Upgrade: template "âge biologique" très haut de gamme (hero card + ring gauge + timeline)
✅ Upgrade: meilleure mise en page (grille 2 colonnes, cards, séparateurs, typographie)
✅ Upgrade: palettes cohérentes + légendes + badges statut
✅ Robustesse: mapping clés, tri statut, pagination douce, jauges compactes

Auteur: Dr Thibault SUTTER
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
import re
import numpy as np
import matplotlib.pyplot as plt

# ============================================================
# OPTIONAL: High-end fonts (safe fallback to Helvetica)
# Put .ttf in your repo (e.g. assets/fonts/)
# ============================================================

def _try_register_fonts():
    """
    If you add these files in your project, you get a much more premium look:
      - assets/fonts/Inter-Regular.ttf
      - assets/fonts/Inter-SemiBold.ttf
      - assets/fonts/Inter-Bold.ttf
    Falls back silently to Helvetica if not found.
    """
    try:
        pdfmetrics.registerFont(TTFont("Inter", "assets/fonts/Inter-Regular.ttf"))
        pdfmetrics.registerFont(TTFont("Inter-SemiBold", "assets/fonts/Inter-SemiBold.ttf"))
        pdfmetrics.registerFont(TTFont("Inter-Bold", "assets/fonts/Inter-Bold.ttf"))
        return {
            "regular": "Inter",
            "semibold": "Inter-SemiBold",
            "bold": "Inter-Bold",
        }
    except Exception:
        return {
            "regular": "Helvetica",
            "semibold": "Helvetica-Bold",
            "bold": "Helvetica-Bold",
        }


# ============================================================
# THEME (High-end palette)
# ============================================================

THEME = {
    "primary": colors.HexColor("#111827"),     # near-black
    "muted": colors.HexColor("#6B7280"),
    "soft": colors.HexColor("#F3F4F6"),
    "card": colors.HexColor("#FFFFFF"),
    "border": colors.HexColor("#E5E7EB"),

    "accent": colors.HexColor("#4F46E5"),      # indigo
    "accent2": colors.HexColor("#7C3AED"),     # purple
    "good": colors.HexColor("#10B981"),        # emerald
    "warn": colors.HexColor("#F59E0B"),        # amber
    "bad": colors.HexColor("#EF4444"),         # red
    "info": colors.HexColor("#3B82F6"),        # blue

    "good_bg": colors.HexColor("#ECFDF5"),
    "warn_bg": colors.HexColor("#FFFBEB"),
    "bad_bg": colors.HexColor("#FEF2F2"),
    "info_bg": colors.HexColor("#EFF6FF"),
}

STATUS_BADGE = {
    "optimal": ("OPTIMAL", THEME["good"], THEME["good_bg"]),
    "normal": ("NORMAL", THEME["info"], THEME["info_bg"]),
    "low": ("BAS", THEME["warn"], THEME["warn_bg"]),
    "high": ("ÉLEVÉ", THEME["bad"], THEME["bad_bg"]),
    "unknown": ("N/A", THEME["muted"], THEME["soft"]),
}

# ============================================================
# BIOMARKER DATABASE - (Your original, unchanged)
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
                "normal_male": [30.0, 400.0],
                "normal_female": [15.0, 150.0],
                "optimal_male": [50.0, 150.0],
                "optimal_female": [30.0, 100.0],
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
            "homocysteine": {"unit": "µmol/L", "normal": [5.0, 15.0], "optimal": [5.0, 9.0], "category": "Cardiovasculaire"},
            "cortisol": {"unit": "µg/dL", "normal": [5.0, 25.0], "optimal": [10.0, 18.0], "category": "Hormones"},
            "testosterone": {
                "unit": "ng/mL",
                "normal_male": [3.0, 10.0],
                "optimal_male": [5.0, 8.0],
                "normal_female": [0.1, 0.7],
                "optimal_female": [0.3, 0.5],
                "category": "Hormones",
            },
        }

    def classify_biomarker(self, key, value, age=None, sexe=None):
        refs = self.get_reference_ranges()

        if key not in refs:
            return {"status": "unknown", "interpretation": "Référence non disponible pour ce biomarqueur", "icon": "❓"}

        ref = refs[key]
        try:
            val = float(value)
        except Exception:
            return {"status": "unknown", "interpretation": "Valeur non numérique / manquante", "icon": "❓"}

        # bounds
        if sexe == "Masculin" and "normal_male" in ref:
            normal = ref["normal_male"]
            optimal = ref.get("optimal_male", ref.get("optimal"))
        elif sexe == "Féminin" and "normal_female" in ref:
            normal = ref["normal_female"]
            optimal = ref.get("optimal_female", ref.get("optimal"))
        else:
            normal = ref.get("normal", [0, 100])
            optimal = ref.get("optimal")

        if optimal and len(optimal) == 2 and optimal[0] <= val <= optimal[1]:
            return {"status": "optimal", "interpretation": f"Valeur optimale ({val:.2f} {ref['unit']}).", "icon": "✅"}
        elif normal[0] <= val <= normal[1]:
            return {"status": "normal", "interpretation": f"Valeur dans les normes ({val:.2f} {ref['unit']}).", "icon": "✓"}
        elif val < normal[0]:
            deficit = normal[0] - val
            percent = (deficit / normal[0]) * 100 if normal[0] else 0
            return {"status": "low", "interpretation": f"Valeur basse ({val:.2f} {ref['unit']}). Déficit ~{percent:.0f}%.", "icon": "⚠️"}
        else:
            excess = val - normal[1]
            percent = (excess / normal[1]) * 100 if normal[1] else 0
            return {"status": "high", "interpretation": f"Valeur élevée ({val:.2f} {ref['unit']}). Excès ~{percent:.0f}%.", "icon": "⚠️"}


# ============================================================
# NORMALISATION INPUTS
# ============================================================

def normalize_patient(patient_data: dict) -> dict:
    if not isinstance(patient_data, dict):
        return {}
    if "patient_info" in patient_data and isinstance(patient_data["patient_info"], dict):
        return patient_data["patient_info"]
    return patient_data


def normalize_biomarkers(biomarker_results):
    if isinstance(biomarker_results, dict):
        return "dict", biomarker_results, []
    if isinstance(biomarker_results, list):
        cleaned = []
        for it in biomarker_results:
            if not isinstance(it, dict):
                continue
            cleaned.append({
                "key": it.get("key") or it.get("biomarker_key") or it.get("name") or "—",
                "name": it.get("name") or (it.get("key") or "—").replace("_", " ").title(),
                "value": it.get("value"),
                "unit": it.get("unit", ""),
                "flag": it.get("flag"),
                "range": it.get("range"),
                "category": it.get("category", "—"),
            })
        return "list", {}, cleaned
    return "unknown", {}, []


def safe_float(x, default=None):
    try:
        if x is None:
            return default
        return float(x)
    except Exception:
        return default


# ============================================================
# KEY MAPPING (PATCH)
# ============================================================

ALIASES = {
    "crp_us": "crp", "hs_crp": "crp", "hs-crp": "crp", "crp-us": "crp", "crp_hs": "crp", "crpus": "crp",
    "vit_d": "vitamine_d", "vitamin_d": "vitamine_d", "25ohd": "vitamine_d", "25-ohd": "vitamine_d", "25(oh)d": "vitamine_d",
    "b12": "vitamine_b12", "vit_b12": "vitamine_b12", "vitamineb12": "vitamine_b12",
    "insulin": "insuline", "insuline_jeun": "insuline", "insulin_fasting": "insuline",
    "homa": "homa_index", "homa_ir": "homa_index", "homair": "homa_index", "homa-IR": "homa_index",
    "quicki": "quicki_index",
    "ferritin": "ferritine",
    "zn": "zinc", "se": "selenium",
}


def canonical_key(raw_key: str) -> str:
    k = (raw_key or "").strip().lower()
    k = k.replace(" ", "_")
    return ALIASES.get(k, k)


# ============================================================
# MATPLOTLIB VISUALS (premium)
# ============================================================

def _mpl_clean(ax):
    ax.set_facecolor("white")
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)
    ax.grid(False)


def create_biomarker_gauge(
    biomarker_name, value, ref_min, ref_max,
    optimal_min=None, optimal_max=None, unit="",
    status="unknown"
):
    """
    Jauge horizontale premium (compact) - parfait pour inclure aussi les normaux.
    """
    v = safe_float(value, 0.0)
    rmin = safe_float(ref_min, 0.0)
    rmax = safe_float(ref_max, rmin + 1.0)
    if rmax <= rmin:
        rmax = rmin + 1.0

    total = rmax - rmin
    pos = (v - rmin) / total if total else 0.5
    pos = max(0, min(1, pos))

    fig, ax = plt.subplots(figsize=(8.2, 1.0))
    fig.patch.set_facecolor("white")

    # Track background
    ax.barh(0, 1, height=0.35, color="#EEF2FF", alpha=1.0, edgecolor="white")

    # Optimal zone
    if optimal_min is not None and optimal_max is not None:
        omin = safe_float(optimal_min, None)
        omax = safe_float(optimal_max, None)
        if omin is not None and omax is not None and omax > omin:
            start = max(0, (omin - rmin) / total)
            width = min(1 - start, (omax - omin) / total)
            ax.barh(0, width, left=start, height=0.35, color="#D1FAE5", alpha=1.0)

    # Marker color
    if status in ("optimal",):
        c = "#10B981"
    elif status in ("normal",):
        c = "#3B82F6"
    elif status in ("low",):
        c = "#F59E0B"
    elif status in ("high",):
        c = "#EF4444"
    else:
        c = "#6B7280"

    ax.plot([pos], [0], marker="o", markersize=10, color=c,
            markeredgecolor="white", markeredgewidth=2, zorder=10)

    # Texts
    ax.text(-0.02, 0, biomarker_name, va="center", ha="right",
            fontsize=9.5, fontweight="bold", color="#111827")
    ax.text(pos, 0.45, f"{v:.2f} {unit}".strip(), ha="center", va="bottom",
            fontsize=8.5, fontweight="bold", color=c)

    ax.text(0, -0.45, f"{rmin:.1f}", ha="center", va="top", fontsize=7.5, color="#6B7280")
    ax.text(1, -0.45, f"{rmax:.1f}", ha="center", va="top", fontsize=7.5, color="#6B7280")

    _mpl_clean(ax)
    ax.set_xlim(-0.15, 1.05)
    ax.set_ylim(-0.9, 0.9)

    buf = io.BytesIO()
    plt.tight_layout(pad=0.2)
    plt.savefig(buf, format="png", dpi=200, bbox_inches="tight", transparent=True)
    buf.seek(0)
    plt.close(fig)
    return buf


def create_bioage_hero_visual(bio_age, chrono_age):
    """
    Visuel "ultra premium" pour âge biologique:
      - ring gauge + delta
    """
    b = safe_float(bio_age, 50.0)
    c = safe_float(chrono_age, 50.0)
    delta = b - c

    # Map delta -> score ring 0..1 (younger = better)
    # delta -10 => 1.0 ; delta +10 => 0.0
    score = 1.0 - (delta + 10) / 20.0
    score = max(0.0, min(1.0, score))

    if delta <= -1:
        col = "#10B981"
        label = "Plus jeune que l'âge chronologique"
    elif delta <= 1:
        col = "#3B82F6"
        label = "En ligne avec l'âge chronologique"
    else:
        col = "#F59E0B"
        label = "Plus élevé que l'âge chronologique"

    fig = plt.figure(figsize=(8.5, 2.6))
    fig.patch.set_facecolor("white")

    # left: ring
    ax1 = fig.add_axes([0.02, 0.12, 0.33, 0.76])
    ax1.set_aspect("equal")
    ax1.axis("off")

    # ring background
    bg = plt.Circle((0, 0), 1.0, color="#F3F4F6")
    ax1.add_artist(bg)
    fg = plt.Circle((0, 0), 1.0, color="white")
    ax1.add_artist(fg)

    # progress arc via wedge
    theta = 360 * score
    wedge = plt.matplotlib.patches.Wedge((0, 0), 1.0, 90, 90 - theta, width=0.18, color=col)
    ax1.add_patch(wedge)

    ax1.text(0, 0.10, f"{b:.1f}", ha="center", va="center", fontsize=22, fontweight="bold", color="#111827")
    ax1.text(0, -0.22, "Âge bio", ha="center", va="center", fontsize=10, color="#6B7280")

    # right: numbers
    ax2 = fig.add_axes([0.40, 0.12, 0.58, 0.76])
    ax2.axis("off")

    ax2.text(0.00, 0.82, "Âge Biologique", fontsize=16, fontweight="bold", color="#111827")
    ax2.text(0.00, 0.58, f"Chronologique: {c:.1f} ans", fontsize=11, color="#6B7280")

    ax2.text(0.00, 0.34, "Delta:", fontsize=11, color="#6B7280")
    ax2.text(0.13, 0.34, f"{delta:+.1f} ans", fontsize=16, fontweight="bold", color=col)

    ax2.text(0.00, 0.10, label, fontsize=11, fontweight="semibold", color=col)

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=220, bbox_inches="tight", facecolor="white")
    buf.seek(0)
    plt.close(fig)
    return buf


def create_category_bars(category_scores: dict):
    fig, ax = plt.subplots(figsize=(8.0, 4.8))
    fig.patch.set_facecolor("white")

    cats = list(category_scores.keys())
    vals = [safe_float(category_scores[k], 0.0) for k in cats]

    cats = cats[::-1]
    vals = vals[::-1]

    cols = []
    for v in vals:
        if v >= 90:
            cols.append("#10B981")
        elif v >= 80:
            cols.append("#3B82F6")
        elif v >= 70:
            cols.append("#F59E0B")
        else:
            cols.append("#EF4444")

    y = np.arange(len(cats))
    ax.barh(y, vals, color=cols, alpha=0.92, edgecolor="white", linewidth=2)

    for yi, v in zip(y, vals):
        ax.text(v + 1.5, yi, f"{v:.1f}", va="center", fontsize=9, fontweight="bold", color="#111827")

    ax.set_yticks(y)
    ax.set_yticklabels([c.replace("_", " ").title() for c in cats], fontsize=9, color="#111827")
    ax.set_xlim(0, 105)
    ax.set_xlabel("Score (/100)", fontsize=10, fontweight="bold", color="#111827")
    ax.grid(axis="x", alpha=0.18, linestyle="--")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    buf = io.BytesIO()
    plt.tight_layout(pad=0.6)
    plt.savefig(buf, format="png", dpi=200, bbox_inches="tight", facecolor="white")
    buf.seek(0)
    plt.close(fig)
    return buf


# ============================================================
# REPORTLAB HELPERS (cards, badges, separators)
# ============================================================

def badge_paragraph(status: str, styles, font_map):
    s = (status or "unknown").lower()
    label, fg, bg = STATUS_BADGE.get(s, STATUS_BADGE["unknown"])
    # HTML-like inline background isn't fully supported; so we simulate a badge using a tiny table
    p = Paragraph(f"<b>{label}</b>", ParagraphStyle(
        "BadgeText", parent=styles["Normal"],
        fontName=font_map["bold"], fontSize=8,
        textColor=fg, alignment=TA_CENTER
    ))
    t = Table([[p]], colWidths=[22*mm], rowHeights=[6.5*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), bg),
        ("BOX", (0, 0), (0, 0), 0.6, fg),
        ("VALIGN", (0, 0), (0, 0), "MIDDLE"),
        ("ALIGN", (0, 0), (0, 0), "CENTER"),
        ("LEFTPADDING", (0, 0), (0, 0), 0),
        ("RIGHTPADDING", (0, 0), (0, 0), 0),
        ("TOPPADDING", (0, 0), (0, 0), 0),
        ("BOTTOMPADDING", (0, 0), (0, 0), 0),
    ]))
    return t


def section_title(text, style):
    return Paragraph(text, style)


def hr_line(width_mm=170, color=THEME["border"]):
    t = Table([[""]], colWidths=[width_mm*mm], rowHeights=[0.6*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), color),
    ]))
    return t


# ============================================================
# MAIN GENERATOR
# ============================================================

def generate_algolife_pdf_report(
    patient_data,
    biomarker_results,
    engine_results=None,
    chart_buffer=None,
    health_score=None,
    biological_age=None,
    nutritional_needs=None,
    recommendations=None,
    biomarker_db=None,
    max_gauges_abnormal=30,
    max_gauges_watch=25,
    max_gauges_normal=18,  # ✅ NEW: show gauges for normals too (cap)
):
    """
    High-end PDF report generator.
    """
    if biomarker_db is None:
        biomarker_db = BiomarkerDatabase()

    font_map = _try_register_fonts()

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=14*mm, bottomMargin=14*mm,
        leftMargin=18*mm, rightMargin=18*mm
    )

    styles = getSampleStyleSheet()

    # --- Global styles (premium typography) ---
    title_style = ParagraphStyle(
        "Title", parent=styles["Heading1"],
        fontName=font_map["bold"], fontSize=30,
        textColor=THEME["primary"], alignment=TA_CENTER,
        spaceAfter=3
    )
    subtitle_style = ParagraphStyle(
        "Subtitle", parent=styles["Normal"],
        fontName=font_map["regular"], fontSize=11.5,
        textColor=THEME["muted"], alignment=TA_CENTER,
        spaceAfter=14, leading=14
    )
    h2 = ParagraphStyle(
        "H2", parent=styles["Heading2"],
        fontName=font_map["bold"], fontSize=15.5,
        textColor=THEME["primary"],
        spaceBefore=12, spaceAfter=8
    )
    h3 = ParagraphStyle(
        "H3", parent=styles["Heading3"],
        fontName=font_map["semibold"], fontSize=12,
        textColor=THEME["primary"],
        spaceBefore=10, spaceAfter=6
    )
    small = ParagraphStyle(
        "Small", parent=styles["Normal"],
        fontName=font_map["regular"], fontSize=9,
        textColor=THEME["muted"], leading=12
    )
    body = ParagraphStyle(
        "Body", parent=styles["Normal"],
        fontName=font_map["regular"], fontSize=10,
        textColor=THEME["primary"], leading=14
    )
    interp_style = ParagraphStyle(
        "Interp", parent=styles["Normal"],
        fontName=font_map["regular"], fontSize=8.8,
        textColor=THEME["muted"], leading=12,
        leftIndent=6
    )

    # Normalize inputs
    patient_info = normalize_patient(patient_data)
    mode, biomarkers_dict, biomarkers_list = normalize_biomarkers(biomarker_results)

    story = []

    # ============================================================
    # COVER / HEADER
    # ============================================================

    story.append(Paragraph("ALGO-LIFE", title_style))
    story.append(Paragraph("Rapport Premium — Analyse Multimodale de Santé Fonctionnelle", subtitle_style))

    # Top meta row (date + id)
    meta_left = Paragraph(f"<b>Date du rapport</b><br/>{datetime.now().strftime('%d/%m/%Y')}", small)
    meta_right = Paragraph(f"<b>Version</b><br/>v6.0 Premium", small)
    meta = Table([[meta_left, meta_right]], colWidths=[85*mm, 85*mm])
    meta.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), THEME["soft"]),
        ("BOX", (0, 0), (-1, -1), 0.8, THEME["border"]),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(meta)
    story.append(Spacer(1, 10))

    # ============================================================
    # PATIENT CARD
    # ============================================================

    story.append(section_title("Informations Patient", h2))

    p_rows = [
        ["PATIENT", patient_info.get("nom", patient_info.get("name", "—"))],
        ["GENRE", patient_info.get("sexe", patient_info.get("sex", "—"))],
        ["ÂGE", f"{patient_info.get('age', '—')} ans"],
        ["TAILLE / POIDS", f"{patient_info.get('height', '—')} cm / {patient_info.get('weight', '—')} kg"],
        ["IMC", f"{patient_info.get('imc', '—')}" if patient_info.get("imc") else "—"],
        ["DATE PRÉLÈVEMENT", patient_info.get("prelevement_date", "—")],
    ]
    p_table = Table(p_rows, colWidths=[42*mm, 128*mm])
    p_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), THEME["card"]),
        ("BOX", (0, 0), (-1, -1), 0.8, THEME["border"]),
        ("LINEBEFORE", (1, 0), (1, -1), 0.8, THEME["border"]),
        ("FONTNAME", (0, 0), (0, -1), font_map["semibold"]),
        ("TEXTCOLOR", (0, 0), (0, -1), THEME["muted"]),
        ("FONTNAME", (1, 0), (1, -1), font_map["regular"]),
        ("TEXTCOLOR", (1, 0), (1, -1), THEME["primary"]),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(p_table)
    story.append(Spacer(1, 10))

    # ============================================================
    # BIO AGE HERO + HEALTH SCORE CARD
    # ============================================================

    story.append(section_title("Âge Biologique & Score Santé", h2))

    # left: bioage hero
    hero_img = None
    if biological_age:
        hero_img = create_bioage_hero_visual(
            biological_age.get("biological_age"),
            biological_age.get("chronological_age"),
        )

    # right: score card
    score_value = safe_float((health_score or {}).get("global_score"), None)
    grade = (health_score or {}).get("grade", "—")
    if score_value is None:
        score_value = 0.0

    if score_value >= 90:
        score_col = THEME["good"]
        score_bg = THEME["good_bg"]
    elif score_value >= 75:
        score_col = THEME["info"]
        score_bg = THEME["info_bg"]
    elif score_value >= 60:
        score_col = THEME["warn"]
        score_bg = THEME["warn_bg"]
    else:
        score_col = THEME["bad"]
        score_bg = THEME["bad_bg"]

    score_block = Table(
        [[
            Paragraph("Score Santé Global", ParagraphStyle(
                "ScoreLabel", parent=styles["Normal"],
                fontName=font_map["semibold"], fontSize=10,
                textColor=THEME["muted"]
            )),
        ],
         [
            Paragraph(f"<font color='{score_col.hexval()}'><b>{score_value:.1f}/100</b></font>",
                      ParagraphStyle("ScoreValue", parent=styles["Normal"],
                                     fontName=font_map["bold"], fontSize=22,
                                     textColor=score_col)),
         ],
         [
            Paragraph(f"Grade <b>{grade}</b>", ParagraphStyle(
                "ScoreGrade", parent=styles["Normal"],
                fontName=font_map["regular"], fontSize=10,
                textColor=THEME["primary"]
            )),
         ]],
        colWidths=[80*mm]
    )
    score_block.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), score_bg),
        ("BOX", (0, 0), (-1, -1), 0.8, score_col),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))

    # layout row
    row = []
    if hero_img is not None:
        row.append(Image(hero_img, width=92*mm, height=36*mm))
    else:
        row.append(Paragraph("Âge biologique non disponible.", small))
    row.append(score_block)

    row_table = Table([[row[0], row[1]]], colWidths=[92*mm, 78*mm])
    row_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(row_table)
    story.append(Spacer(1, 8))

    # Category bars
    if health_score and health_score.get("category_scores"):
        story.append(section_title("Scores par Catégorie", h3))
        bars = create_category_bars(health_score["category_scores"])
        story.append(Image(bars, width=168*mm, height=86*mm))

    story.append(PageBreak())

    # ============================================================
    # BIOMARKERS WITH GAUGES (✅ include NORMAL too)
    # ============================================================

    story.append(section_title("Biomarqueurs — Jauges & Statuts", h2))
    story.append(Paragraph(
        "Lecture visuelle: zone verte = optimale, barre bleue = normal, orange/rouge = hors normes.",
        small
    ))
    story.append(Spacer(1, 6))

    refs_db = biomarker_db.get_reference_ranges()

    normaux, watch, abnormal = [], [], []

    iterable = list(biomarkers_dict.items()) if mode == "dict" else [(it["key"], it["value"]) for it in biomarkers_list]

    for raw_key, value in iterable:
        if raw_key is None:
            continue
        key = canonical_key(str(raw_key))
        if key not in refs_db:
            continue

        cls = biomarker_db.classify_biomarker(key, value, patient_info.get("age"), patient_info.get("sexe"))
        stt = (cls.get("status") or "unknown").lower()
        ref = refs_db[key]

        item = {
            "key": key,
            "name": key.replace("_", " ").title(),
            "value": safe_float(value, None),
            "unit": ref.get("unit", ""),
            "classification": cls,
            "ref_data": ref
        }
        if item["value"] is None:
            continue

        if stt in ("optimal", "normal"):
            normaux.append(item)
        elif stt in ("low", "high"):
            abnormal.append(item)
        else:
            watch.append(item)

    # Summary mini-cards
    total = max(1, len(normaux) + len(watch) + len(abnormal))
    s_cards = Table([[
        Paragraph(f"<b>Normaux</b><br/>{len(normaux)}", body),
        Paragraph(f"<b>À surveiller</b><br/>{len(watch)}", body),
        Paragraph(f"<b>Anormaux</b><br/>{len(abnormal)}", body),
    ]], colWidths=[56*mm, 56*mm, 56*mm])
    s_cards.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), THEME["info_bg"]),
        ("BACKGROUND", (1, 0), (1, 0), THEME["warn_bg"]),
        ("BACKGROUND", (2, 0), (2, 0), THEME["bad_bg"]),
        ("BOX", (0, 0), (-1, -1), 0.8, THEME["border"]),
        ("INNERGRID", (0, 0), (-1, -1), 0.8, THEME["border"]),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(s_cards)
    story.append(Spacer(1, 8))
    story.append(hr_line())
    story.append(Spacer(1, 8))

    # limit display (soft)
    abnormal = abnormal[:max_gauges_abnormal] if isinstance(max_gauges_abnormal, int) else abnormal
    watch = watch[:max_gauges_watch] if isinstance(max_gauges_watch, int) else watch
    normaux = normaux[:max_gauges_normal] if isinstance(max_gauges_normal, int) else normaux  # ✅ NEW

    def _get_bounds(ref_data, sexe):
        # normal bounds
        if isinstance(ref_data.get("normal"), (list, tuple)) and len(ref_data["normal"]) == 2:
            rmin, rmax = ref_data["normal"]
        elif sexe == "Féminin" and isinstance(ref_data.get("normal_female"), (list, tuple)):
            rmin, rmax = ref_data["normal_female"]
        elif sexe == "Masculin" and isinstance(ref_data.get("normal_male"), (list, tuple)):
            rmin, rmax = ref_data.get("normal_male")[0], ref_data.get("normal_male")[1]
        else:
            rmin, rmax = 0, 100

        # optimal bounds
        omin, omax = None, None
        if isinstance(ref_data.get("optimal"), (list, tuple)) and len(ref_data["optimal"]) == 2:
            omin, omax = ref_data["optimal"]
        elif sexe == "Féminin" and isinstance(ref_data.get("optimal_female"), (list, tuple)):
            omin, omax = ref_data["optimal_female"]
        elif sexe == "Masculin" and isinstance(ref_data.get("optimal_male"), (list, tuple)):
            omin, omax = ref_data["optimal_male"]

        return rmin, rmax, omin, omax

    def render_section(title, items):
        if not items:
            return

        story.append(section_title(title, h3))
        story.append(Spacer(1, 2))

        for it in items:
            stt = (it["classification"].get("status") or "unknown").lower()
            ref_data = it["ref_data"]
            rmin, rmax, omin, omax = _get_bounds(ref_data, patient_info.get("sexe"))

            gauge = create_biomarker_gauge(
                it["name"], it["value"],
                rmin if rmin is not None else 0,
                rmax if rmax is not None else (it["value"] * 1.5 if it["value"] else 1.0),
                omin, omax, it["unit"],
                status=stt
            )

            left = Image(gauge, width=125*mm, height=18*mm)
            right = badge_paragraph(stt, styles, font_map)

            row = Table([[left, right]], colWidths=[132*mm, 30*mm])
            row.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]))

            story.append(KeepTogether([
                row,
                Paragraph(f"{it['classification'].get('icon','')} {it['classification'].get('interpretation','')}", interp_style),
                Spacer(1, 4),
                hr_line(width_mm=170, color=THEME["border"]),
                Spacer(1, 4),
            ]))

    # Order: abnormal -> watch -> normals (but normals still have gauges ✅)
    render_section("⚠️ Biomarqueurs Anormaux — Jauges", abnormal)
    render_section("⚡ Biomarqueurs À Surveiller — Jauges", watch)
    render_section("✅ Biomarqueurs Normaux — Jauges", normaux)

    story.append(PageBreak())

    # ============================================================
    # NUTRITION (same, but styled)
    # ============================================================

    if nutritional_needs:
        story.append(section_title("Besoins Nutritionnels", h2))
        story.append(Spacer(1, 6))

        nutri_data = [
            ["Métrique", "Valeur"],
            ["BMR", f"{safe_float(nutritional_needs.get('bmr'), 0):.0f} kcal/j"],
            ["DET", f"{safe_float(nutritional_needs.get('det'), 0):.0f} kcal/j"],
            ["Protéines", f"{safe_float(nutritional_needs.get('proteins_g'), 0):.0f} g/j"],
            ["Lipides", f"{safe_float(nutritional_needs.get('lipids_g'), 0):.0f} g/j"],
            ["Glucides", f"{safe_float(nutritional_needs.get('carbs_g'), 0):.0f} g/j"],
        ]
        t = Table(nutri_data, colWidths=[70*mm, 100*mm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), THEME["soft"]),
            ("TEXTCOLOR", (0, 0), (-1, 0), THEME["primary"]),
            ("FONTNAME", (0, 0), (-1, 0), font_map["bold"]),
            ("FONTNAME", (0, 1), (0, -1), font_map["semibold"]),
            ("BOX", (0, 0), (-1, -1), 0.8, THEME["border"]),
            ("INNERGRID", (0, 0), (-1, -1), 0.6, THEME["border"]),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(t)
        story.append(Spacer(1, 10))

    # ============================================================
    # RECOMMENDATIONS (styled)
    # ============================================================

    if recommendations:
        story.append(section_title("Recommandations Personnalisées", h2))
        story.append(Spacer(1, 6))

        recs = recommendations.get("recommendations", {}) if isinstance(recommendations, dict) else {}
        priorities = recommendations.get("priorities", []) if isinstance(recommendations, dict) else []

        if priorities:
            story.append(section_title("Priorités", h3))
            for i, p in enumerate(priorities[:6], 1):
                name = str(p.get("biomarker", "")).replace("_", " ").title()
                level = str(p.get("priority", "—"))
                c = THEME["bad"] if "élev" in level.lower() else THEME["warn"]
                story.append(Paragraph(f"{i}. <b>{name}</b> — <font color='{c.hexval()}'><b>{level}</b></font>", body))
            story.append(Spacer(1, 8))
            story.append(hr_line())
            story.append(Spacer(1, 8))

        def bullet_list(items, max_items=14):
            out = []
            for s in (items or [])[:max_items]:
                out.append(Paragraph(f"• {s}", body))
            return out

        if recs.get("supplements"):
            story.append(section_title("Micronutrition", h3))
            story.extend(bullet_list(recs.get("supplements"), 14))
            story.append(Spacer(1, 8))

        if recs.get("alimentation"):
            story.append(section_title("Alimentation", h3))
            story.extend(bullet_list(recs.get("alimentation"), 14))
            story.append(Spacer(1, 8))

        if recs.get("lifestyle"):
            story.append(section_title("Mode de vie", h3))
            story.extend(bullet_list(recs.get("lifestyle"), 14))
            story.append(Spacer(1, 8))

    # ============================================================
    # FOOTER (clean & premium)
    # ============================================================

    story.append(Spacer(1, 14))
    story.append(hr_line())
    story.append(Spacer(1, 6))

    footer = ParagraphStyle(
        "Footer", parent=styles["Normal"],
        fontName=font_map["regular"], fontSize=8.2,
        textColor=THEME["muted"], alignment=TA_CENTER, leading=11
    )
    story.append(Paragraph("<b>Rapport établi par Dr Thibault SUTTER — Biologiste</b>", footer))
    story.append(Paragraph("ALGO-LIFE | Plateforme Multimodale d'Analyse de Santé Fonctionnelle", footer))
    story.append(Paragraph("© 2026 — Document médical confidentiel", footer))

    # BUILD
    try:
        doc.build(story)
        buffer.seek(0)
        return buffer
    except Exception as e:
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        doc.build([Paragraph(f"ERREUR PDF: {str(e)}", styles["Normal"])])
        buffer.seek(0)
        return buffer


__all__ = ["generate_algolife_pdf_report", "BiomarkerDatabase"]

if __name__ == "__main__":
    print("✅ ALGO-LIFE PDF Generator v6.0 PREMIUM")
    print("🎨 High-end template (bio age hero + biomarker gauges including normals)")
