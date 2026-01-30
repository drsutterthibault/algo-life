"""
ALGO-LIFE PDF Generator v7.0 ULTRA PREMIUM
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
from matplotlib.patches import Circle, Wedge, FancyBboxPatch


# ============================================================
# PALETTE ULTRA PREMIUM
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
}

STATUS_COLORS = {
    "optimal": (PREMIUM_THEME["emerald"], PREMIUM_THEME["emerald_subtle"]),
    "normal": (PREMIUM_THEME["sapphire"], PREMIUM_THEME["sapphire_subtle"]),
    "low": (PREMIUM_THEME["gold"], PREMIUM_THEME["gold_subtle"]),
    "high": (PREMIUM_THEME["ruby"], PREMIUM_THEME["ruby_subtle"]),
}


# ============================================================
# FONTS
# ============================================================

def register_fonts():
    try:
        pdfmetrics.registerFont(TTFont("Inter", "assets/fonts/Inter-Regular.ttf"))
        pdfmetrics.registerFont(TTFont("InterSB", "assets/fonts/Inter-SemiBold.ttf"))
        pdfmetrics.registerFont(TTFont("InterB", "assets/fonts/Inter-Bold.ttf"))
        return {"regular": "Inter", "semibold": "InterSB", "bold": "InterB"}
    except:
        return {"regular": "Helvetica", "semibold": "Helvetica-Bold", "bold": "Helvetica-Bold"}


# ============================================================
# BIOMARKER DATABASE
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
        except:
            return {"status": "unknown", "interpretation": "Valeur invalide"}
        
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
            return {"status": "optimal", "interpretation": f"Valeur optimale ({val:.2f} {ref['unit']})"}
        elif normal[0] <= val <= normal[1]:
            return {"status": "normal", "interpretation": f"Valeur normale ({val:.2f} {ref['unit']})"}
        elif val < normal[0]:
            deficit = ((normal[0] - val) / normal[0]) * 100 if normal[0] else 0
            return {"status": "low", "interpretation": f"Valeur basse ({val:.2f} {ref['unit']}). Déficit ~{deficit:.0f}%"}
        else:
            excess = ((val - normal[1]) / normal[1]) * 100 if normal[1] else 0
            return {"status": "high", "interpretation": f"Valeur élevée ({val:.2f} {ref['unit']}). Excès ~{excess:.0f}%"}


# ============================================================
# HELPERS
# ============================================================

def safe_float(x, default=None):
    try:
        return float(x) if x is not None else default
    except:
        return default

def normalize_patient(patient_data):
    if not isinstance(patient_data, dict):
        return {}
    return patient_data.get("patient_info", patient_data)

def normalize_biomarkers(biomarker_results):
    if isinstance(biomarker_results, dict):
        return "dict", biomarker_results, []
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
            })
        return "list", {}, cleaned
    return "unknown", {}, []

ALIASES = {
    "crp_us": "crp", "hs_crp": "crp", "insulin": "insuline",
    "homa": "homa_index", "quicki": "quicki_index",
    "ferritin": "ferritine", "zn": "zinc", "se": "selenium",
}

def canonical_key(raw_key):
    k = (raw_key or "").strip().lower().replace(" ", "_")
    return ALIASES.get(k, k)


# ============================================================
# VISUALISATIONS ULTRA PREMIUM
# ============================================================

def create_bioage_ultra_premium(bio_age, chrono_age):
    """Visuel âge biologique ultra premium"""
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
    
    fig = plt.figure(figsize=(9.5, 4.2), facecolor='white')
    
    # Cercle gauche
    ax1 = fig.add_axes([0.02, 0.08, 0.42, 0.84])
    ax1.set_aspect('equal')
    ax1.axis('off')
    ax1.set_xlim(-1.4, 1.4)
    ax1.set_ylim(-1.4, 1.4)
    
    bg_circle = Circle((0, 0), 1.38, color=bg_color, alpha=0.3, zorder=1)
    ax1.add_patch(bg_circle)
    
    outer_ring = Circle((0, 0), 1.15, fill=False, edgecolor='#E2E8F0', linewidth=3, zorder=2)
    ax1.add_patch(outer_ring)
    
    for r in np.linspace(0.95, 1.05, 8):
        alpha_val = 0.15 + (1.05 - r) * 0.85 / 0.1
        ring = Circle((0, 0), r, fill=False, edgecolor=main_color, 
                     linewidth=2.5, alpha=alpha_val, zorder=3)
        ax1.add_patch(ring)
    
    center = Circle((0, 0), 0.88, color='white', zorder=4)
    ax1.add_patch(center)
    
    ax1.text(0, 0.22, f"{b:.1f}", ha='center', va='center',
             fontsize=42, fontweight='bold', color=main_color, zorder=5)
    ax1.text(0, -0.18, "Âge biologique", ha='center', va='center',
             fontsize=11, color='#64748B', fontweight='600', zorder=5)
    ax1.text(0, -0.38, "(années)", ha='center', va='center',
             fontsize=9, color='#94A3B8', zorder=5)
    
    delta_x, delta_y = 0.75, 0.75
    delta_symbol = "▼" if delta < 0 else "▲" if delta > 0 else "●"
    ax1.text(delta_x, delta_y, delta_symbol, ha='center', va='center',
             fontsize=16, color=main_color, alpha=0.8, zorder=6)
    ax1.text(delta_x, delta_y - 0.18, f"{delta:+.1f}", ha='center', va='center',
             fontsize=9, fontweight='bold', color=main_color, zorder=6)
    
    # Info droite
    ax2 = fig.add_axes([0.48, 0.08, 0.50, 0.84])
    ax2.axis('off')
    ax2.set_xlim(0, 1)
    ax2.set_ylim(0, 1)
    
    ax2.text(0.02, 0.88, label, fontsize=16, fontweight='bold',
             color='#0A1628', va='top')
    
    box = FancyBboxPatch((0, 0.72), 0.96, 0.10, boxstyle="round,pad=0.01",
                         edgecolor=main_color, facecolor=bg_color, 
                         linewidth=1.5, alpha=0.6)
    ax2.add_patch(box)
    ax2.text(0.48, 0.77, sublabel, fontsize=11, fontweight='600',
             color=main_color, ha='center', va='center')
    
    y_pos = 0.58
    ax2.text(0.02, y_pos, "Âge chronologique", fontsize=10, color='#64748B')
    ax2.text(0.98, y_pos, f"{c:.1f} ans", fontsize=12, fontweight='bold',
             color='#1E293B', ha='right')
    
    y_pos -= 0.14
    ax2.text(0.02, y_pos, "Âge biologique", fontsize=10, color='#64748B')
    ax2.text(0.98, y_pos, f"{b:.1f} ans", fontsize=12, fontweight='bold',
             color=main_color, ha='right')
    
    y_pos -= 0.14
    ax2.text(0.02, y_pos, "Différence", fontsize=10, color='#64748B')
    ax2.text(0.98, y_pos, f"{delta:+.1f} ans", fontsize=13, fontweight='bold',
             color=main_color, ha='right')
    
    # Timeline
    y_pos -= 0.18
    timeline_y = y_pos
    
    ax2.plot([0.08, 0.92], [timeline_y, timeline_y], color='#CBD5E1', 
             linewidth=3, solid_capstyle='round', zorder=1)
    
    chron_pos = 0.5
    bio_offset = (delta / 20.0) * 0.4
    bio_pos = np.clip(chron_pos + bio_offset, 0.08, 0.92)
    
    ax2.plot([chron_pos], [timeline_y], 'o', markersize=9, color='#64748B',
             markeredgecolor='white', markeredgewidth=2, zorder=3)
    ax2.text(chron_pos, timeline_y - 0.06, f"{c:.0f}", ha='center',
             fontsize=8, color='#64748B', fontweight='600')
    
    ax2.plot([bio_pos], [timeline_y], 'o', markersize=12, color=main_color,
             markeredgecolor='white', markeredgewidth=2.5, zorder=4)
    ax2.text(bio_pos, timeline_y + 0.06, f"{b:.0f}", ha='center',
             fontsize=9, color=main_color, fontweight='bold')
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=240, bbox_inches='tight', 
                facecolor='white', edgecolor='none')
    buf.seek(0)
    plt.close(fig)
    return buf


def create_gauge_vertical_premium(name, value, ref_min, ref_max, 
                                   opt_min=None, opt_max=None, unit="", status="normal"):
    """Jauge verticale premium"""
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
    elif status == "low":
        main_col = "#F59E0B"
    elif status == "high":
        main_col = "#DC2626"
    else:
        main_col = "#64748B"
    
    fig, ax = plt.subplots(figsize=(1.8, 3.5), facecolor='white')
    ax.set_xlim(-0.55, 0.55)
    ax.set_ylim(-0.1, 1.15)
    ax.axis('off')
    
    track_width = 0.18
    from matplotlib.patches import Rectangle
    track = Rectangle((-track_width/2, 0), track_width, 1.0,
                      facecolor='#F1F5F9', edgecolor='#E2E8F0',
                      linewidth=1.5, zorder=1)
    ax.add_patch(track)
    
    if opt_min is not None and opt_max is not None:
        omin = safe_float(opt_min, None)
        omax = safe_float(opt_max, None)
        if omin is not None and omax is not None and omax > omin:
            opt_start = np.clip((omin - rmin) / total, 0, 1)
            opt_height = np.clip((omax - omin) / total, 0, 1 - opt_start)
            opt_zone = Rectangle((-track_width/2, opt_start), track_width, opt_height,
                                facecolor='#D1FAE5', edgecolor='none',
                                alpha=0.5, zorder=2)
            ax.add_patch(opt_zone)
    
    n_segments = 25
    for i in range(int(pos_norm * n_segments)):
        seg_y = i / n_segments
        seg_h = 1.0 / n_segments
        alpha_val = 0.3 + (i / n_segments) * 0.7
        seg = Rectangle((-track_width/2, seg_y), track_width, seg_h,
                       facecolor=main_col, edgecolor='none',
                       alpha=alpha_val, zorder=3)
        ax.add_patch(seg)
    
    marker = Circle((0, pos_norm), 0.12, facecolor=main_col,
                   edgecolor='white', linewidth=2.5, zorder=5)
    ax.add_patch(marker)
    
    pulse = Circle((0, pos_norm), 0.18, fill=False,
                  edgecolor=main_col, linewidth=2, alpha=0.4, zorder=4)
    ax.add_patch(pulse)
    
    ax.text(0, 1.08, name, ha='center', va='bottom',
            fontsize=9, fontweight='bold', color='#0A1628')
    
    ax.text(0, pos_norm, f"{v:.1f}", ha='center', va='center',
            fontsize=8.5, fontweight='bold', color='white', zorder=6)
    
    ax.text(0.32, pos_norm, unit, ha='left', va='center',
            fontsize=7.5, color=main_col, fontweight='600')
    
    ax.text(-0.35, 0, f"{rmin:.0f}", ha='right', va='center',
            fontsize=7, color='#94A3B8')
    ax.text(-0.35, 1.0, f"{rmax:.0f}", ha='right', va='center',
            fontsize=7, color='#94A3B8')
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=200, bbox_inches='tight',
                facecolor='white', transparent=True)
    buf.seek(0)
    plt.close(fig)
    return buf


def create_category_bars_premium(category_scores):
    """Barres catégories premium"""
    fig, ax = plt.subplots(figsize=(9.0, 5.2), facecolor='white')
    
    cats = list(category_scores.keys())
    vals = [safe_float(category_scores[k], 0.0) for k in cats]
    
    cats = cats[::-1]
    vals = vals[::-1]
    
    y_pos = np.arange(len(cats))
    
    colors_list = []
    for v in vals:
        if v >= 90:
            colors_list.append('#059669')
        elif v >= 80:
            colors_list.append('#0284C7')
        elif v >= 70:
            colors_list.append('#F59E0B')
        else:
            colors_list.append('#DC2626')
    
    ax.barh(y_pos, vals, height=0.65, color=colors_list,
            edgecolor='white', linewidth=2.5, alpha=0.92)
    
    for i, (yi, v, c) in enumerate(zip(y_pos, vals, colors_list)):
        ax.text(v + 1.8, yi, f"{v:.1f}", va='center', ha='left',
                fontsize=10, fontweight='bold', color=c)
    
    ax.set_yticks(y_pos)
    ax.set_yticklabels([c.replace("_", " ").title() for c in cats],
                       fontsize=10, fontweight='600', color='#1E293B')
    
    ax.set_xlim(0, 108)
    ax.set_xlabel("Score (/100)", fontsize=11, fontweight='bold',
                  color='#0A1628', labelpad=10)
    
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#E2E8F0')
    ax.spines['bottom'].set_color('#E2E8F0')
    
    ax.grid(axis='x', alpha=0.12, linestyle='--', linewidth=1, color='#CBD5E1')
    ax.tick_params(colors='#64748B', labelsize=9)
    
    buf = io.BytesIO()
    plt.tight_layout(pad=0.8)
    plt.savefig(buf, format='png', dpi=220, bbox_inches='tight', facecolor='white')
    buf.seek(0)
    plt.close(fig)
    return buf


# ============================================================
# REPORTLAB HELPERS
# ============================================================

def premium_section_title(text, font_map, size=16):
    style = ParagraphStyle(
        "PremiumTitle",
        fontName=font_map["bold"],
        fontSize=size,
        textColor=PREMIUM_THEME["deep_navy"],
        spaceBefore=14,
        spaceAfter=10,
        leading=size * 1.3
    )
    return Paragraph(text, style)


def premium_card(content_rows, col_widths):
    t = Table(content_rows, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PREMIUM_THEME["pearl"]),
        ("BOX", (0, 0), (-1, -1), 1.2, PREMIUM_THEME["silver"]),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return t


def divider_line(width=170):
    t = Table([[""]], colWidths=[width*mm], rowHeights=[0.5*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), PREMIUM_THEME["silver"]),
    ]))
    return t


# ============================================================
# MAIN GENERATOR - NOM COMPATIBLE APP.PY ⭐
# ============================================================

def generate_algolife_pdf_report(
    patient_data,
    biomarker_results,
    engine_results=None,  # Paramètre legacy ignoré
    chart_buffer=None,     # Paramètre legacy ignoré
    health_score=None,
    biological_age=None,
    nutritional_needs=None,
    recommendations=None,
    biomarker_db=None,
    max_gauges_abnormal=30,    # Paramètres legacy ignorés
    max_gauges_watch=25,
    max_gauges_normal=18,
):
    """
    ⭐ Générateur PDF ULTRA PREMIUM v7.0
    Compatible avec app.py existant
    """
    if biomarker_db is None:
        biomarker_db = BiomarkerDatabase()
    
    font_map = register_fonts()
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=16*mm, bottomMargin=16*mm,
        leftMargin=20*mm, rightMargin=20*mm
    )
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        "Title", fontName=font_map["bold"], fontSize=34,
        textColor=PREMIUM_THEME["deep_navy"],
        alignment=TA_CENTER, spaceAfter=4, leading=40
    )
    
    subtitle_style = ParagraphStyle(
        "Subtitle", fontName=font_map["regular"], fontSize=12,
        textColor=PREMIUM_THEME["steel"],
        alignment=TA_CENTER, spaceAfter=16, leading=16
    )
    
    body_style = ParagraphStyle(
        "Body", fontName=font_map["regular"], fontSize=10,
        textColor=PREMIUM_THEME["slate"], leading=15
    )
    
    small_style = ParagraphStyle(
        "Small", fontName=font_map["regular"], fontSize=9,
        textColor=PREMIUM_THEME["mist"], leading=12
    )
    
    patient_info = normalize_patient(patient_data)
    mode, biomarkers_dict, biomarkers_list = normalize_biomarkers(biomarker_results)
    
    story = []
    
    # === COVER ===
    story.append(Spacer(1, 6*mm))
    story.append(Paragraph("ALGO-LIFE", title_style))
    story.append(Paragraph(
        "Analyse Multimodale de Santé Fonctionnelle — Rapport Premium",
        subtitle_style
    ))
    
    meta_data = [[
        Paragraph(f"<b>Date du rapport</b><br/>{datetime.now().strftime('%d/%m/%Y')}", small_style),
        Paragraph(f"<b>Version</b><br/>v7.0 Premium", small_style)
    ]]
    story.append(premium_card(meta_data, [85*mm, 85*mm]))
    story.append(Spacer(1, 12*mm))
    
    # === PATIENT ===
    story.append(premium_section_title("Informations Patient", font_map))
    
    p_data = [
        [Paragraph("<b>PATIENT</b>", small_style), 
         Paragraph(patient_info.get("nom", patient_info.get("name", "—")), body_style)],
        [Paragraph("<b>GENRE</b>", small_style),
         Paragraph(patient_info.get("sexe", patient_info.get("sex", "—")), body_style)],
        [Paragraph("<b>ÂGE</b>", small_style),
         Paragraph(f"{patient_info.get('age', '—')} ans", body_style)],
        [Paragraph("<b>TAILLE / POIDS</b>", small_style),
         Paragraph(f"{patient_info.get('height', '—')} cm / {patient_info.get('weight', '—')} kg", body_style)],
        [Paragraph("<b>IMC</b>", small_style),
         Paragraph(f"{patient_info.get('imc', '—')}", body_style)],
        [Paragraph("<b>DATE PRÉLÈVEMENT</b>", small_style),
         Paragraph(patient_info.get("prelevement_date", "—"), body_style)],
    ]
    
    story.append(premium_card(p_data, [45*mm, 125*mm]))
    story.append(Spacer(1, 12*mm))
    
    # === BIO AGE ===
    story.append(premium_section_title("Âge Biologique & Score Santé", font_map, size=18))
    
    if biological_age:
        hero_img = create_bioage_ultra_premium(
            biological_age.get("biological_age"),
            biological_age.get("chronological_age")
        )
        story.append(Image(hero_img, width=170*mm, height=75*mm))
    
    story.append(Spacer(1, 10*mm))
    
    # Score
    score_val = safe_float((health_score or {}).get("global_score"), 0)
    grade = (health_score or {}).get("grade", "—")
    
    if score_val >= 90:
        score_col = PREMIUM_THEME["emerald"]
        score_bg = PREMIUM_THEME["emerald_subtle"]
    elif score_val >= 75:
        score_col = PREMIUM_THEME["sapphire"]
        score_bg = PREMIUM_THEME["sapphire_subtle"]
    else:
        score_col = PREMIUM_THEME["gold"]
        score_bg = PREMIUM_THEME["gold_subtle"]
    
    score_data = [[
        Paragraph(f"<b>Score Santé Global</b><br/>"
                 f"<font size=26 color='{score_col.hexval()}'><b>{score_val:.1f}/100</b></font><br/>"
                 f"<font size=12>Grade <b>{grade}</b></font>",
                 ParagraphStyle("Score", alignment=TA_CENTER, fontName=font_map["bold"]))
    ]]
    
    score_table = Table(score_data, colWidths=[170*mm])
    score_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), score_bg),
        ("BOX", (0, 0), (0, 0), 1.2, score_col),
        ("LEFTPADDING", (0, 0), (0, 0), 12),
        ("RIGHTPADDING", (0, 0), (0, 0), 12),
        ("TOPPADDING", (0, 0), (0, 0), 12),
        ("BOTTOMPADDING", (0, 0), (0, 0), 12),
    ]))
    story.append(score_table)
    story.append(Spacer(1, 10*mm))
    
    # Catégories
    if health_score and health_score.get("category_scores"):
        story.append(premium_section_title("Scores par Catégorie", font_map, size=14))
        bars_img = create_category_bars_premium(health_score["category_scores"])
        story.append(Image(bars_img, width=170*mm, height=98*mm))
    
    story.append(PageBreak())
    
    # === BIOMARQUEURS ===
    story.append(premium_section_title("Biomarqueurs — Analyse Détaillée", font_map, size=18))
    story.append(Paragraph(
        "Jauges verticales sophistiquées avec zones optimales",
        small_style
    ))
    story.append(Spacer(1, 8*mm))
    
    refs_db = biomarker_db.get_reference_ranges()
    normaux, abnormal = [], []
    
    iterable = list(biomarkers_dict.items()) if mode == "dict" else [(it["key"], it["value"]) for it in biomarkers_list]
    
    for raw_key, value in iterable:
        if raw_key is None:
            continue
        key = canonical_key(str(raw_key))
        if key not in refs_db:
            continue
        
        cls = biomarker_db.classify_biomarker(key, value, 
                                              patient_info.get("age"),
                                              patient_info.get("sexe"))
        stt = cls.get("status", "unknown").lower()
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
        else:
            abnormal.append(item)
    
    summary_data = [[
        Paragraph(f"<b>Normaux</b><br/>{len(normaux)}", body_style),
        Paragraph(f"<b>Anormaux</b><br/>{len(abnormal)}", body_style),
    ]]
    story.append(premium_card(summary_data, [85*mm, 85*mm]))
    story.append(Spacer(1, 8*mm))
    story.append(divider_line())
    story.append(Spacer(1, 8*mm))
    
    def get_bounds(ref_data, sexe):
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
    
    def render_biomarkers(items, section_title):
        if not items:
            return
        
        story.append(premium_section_title(section_title, font_map, size=13,))
        story.append(Spacer(1, 4*mm))
        
        for i in range(0, len(items), 4):
            batch = items[i:i+4]
            gauges = []
            
            for it in batch:
                stt = it["classification"].get("status", "normal").lower()
                ref_data = it["ref_data"]
                rmin, rmax, omin, omax = get_bounds(ref_data, patient_info.get("sexe"))
                
                gauge_img = create_gauge_vertical_premium(
                    it["name"], it["value"],
                    rmin, rmax, omin, omax,
                    it["unit"], status=stt
                )
                gauges.append(Image(gauge_img, width=40*mm, height=62*mm))
            
            while len(gauges) < 4:
                gauges.append(Paragraph("", body_style))
            
            gauge_row = Table([gauges], colWidths=[42.5*mm]*4)
            gauge_row.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ]))
            story.append(gauge_row)
            story.append(Spacer(1, 4*mm))
    
    render_biomarkers(abnormal[:20], "⚠️ Biomarqueurs Anormaux")
    render_biomarkers(normaux[:20], "✅ Biomarqueurs Normaux")
    
    story.append(PageBreak())
    
    # === NUTRITION ===
    if nutritional_needs:
        story.append(premium_section_title("Besoins Nutritionnels", font_map))
        
        nutri_data = [
            [Paragraph("<b>Métrique</b>", small_style),
             Paragraph("<b>Valeur</b>", small_style)],
            [Paragraph("BMR", body_style),
             Paragraph(f"{safe_float(nutritional_needs.get('bmr'), 0):.0f} kcal/j", body_style)],
            [Paragraph("DET", body_style),
             Paragraph(f"{safe_float(nutritional_needs.get('det'), 0):.0f} kcal/j", body_style)],
            [Paragraph("Protéines", body_style),
             Paragraph(f"{safe_float(nutritional_needs.get('proteins_g'), 0):.0f} g/j", body_style)],
            [Paragraph("Lipides", body_style),
             Paragraph(f"{safe_float(nutritional_needs.get('lipids_g'), 0):.0f} g/j", body_style)],
            [Paragraph("Glucides", body_style),
             Paragraph(f"{safe_float(nutritional_needs.get('carbs_g'), 0):.0f} g/j", body_style)],
        ]
        
        story.append(premium_card(nutri_data, [70*mm, 100*mm]))
        story.append(Spacer(1, 10*mm))
    
    # === RECOMMANDATIONS ===
    if recommendations:
        story.append(premium_section_title("Recommandations Personnalisées", font_map))
        
        recs = recommendations.get("recommendations", {}) if isinstance(recommendations, dict) else {}
        priorities = recommendations.get("priorities", []) if isinstance(recommendations, dict) else []
        
        if priorities:
            story.append(Paragraph("<b>Priorités</b>", body_style))
            for i, p in enumerate(priorities[:5], 1):
                story.append(Paragraph(
                    f"{i}. <b>{p.get('biomarker', '—').replace('_', ' ').title()}</b> — {p.get('priority', '—')}",
                    body_style
                ))
            story.append(Spacer(1, 6*mm))
        
        if recs.get("supplements"):
            story.append(Paragraph("<b>Micronutrition</b>", body_style))
            for s in recs["supplements"][:10]:
                story.append(Paragraph(f"• {s}", body_style))
            story.append(Spacer(1, 6*mm))
        
        if recs.get("alimentation"):
            story.append(Paragraph("<b>Alimentation</b>", body_style))
            for a in recs["alimentation"][:10]:
                story.append(Paragraph(f"• {a}", body_style))
    
    # === FOOTER ===
    story.append(Spacer(1, 15*mm))
    story.append(divider_line())
    story.append(Spacer(1, 8*mm))
    
    footer_style = ParagraphStyle(
        "Footer", fontName=font_map["regular"], fontSize=8.5,
        textColor=PREMIUM_THEME["mist"],
        alignment=TA_CENTER, leading=12
    )
    
    story.append(Paragraph(
        "<b>Rapport établi par Dr Thibault SUTTER — Biologiste</b>",
        footer_style
    ))
    story.append(Paragraph(
        "ALGO-LIFE | Plateforme Multimodale d'Analyse de Santé Fonctionnelle",
        footer_style
    ))
    story.append(Paragraph("© 2026 — Document médical confidentiel", footer_style))
    
    try:
        doc.build(story)
        buffer.seek(0)
        return buffer
    except Exception as e:
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        doc.build([Paragraph(f"ERREUR: {str(e)}", styles["Normal"])])
        buffer.seek(0)
        return buffer


__all__ = ["generate_algolife_pdf_report", "BiomarkerDatabase"]

if __name__ == "__main__":
    print("✅ ALGO-LIFE PDF Generator v7.0 ULTRA PREMIUM")
    print("🔧 Compatible app.py - Fonction: generate_algolife_pdf_report()")
