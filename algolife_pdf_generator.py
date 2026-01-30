"""
ALGO-LIFE PDF Generator - Version Professionnelle v5.0
Design haut de gamme avec toutes les jauges visibles

Auteur: Dr Thibault SUTTER
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph,
    Spacer, PageBreak, Image
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_CENTER
from io import BytesIO
from datetime import datetime
import io
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle


# ============================================================
# NORMALISATION INPUTS (IMPORTANT)
# ============================================================

def normalize_patient(patient_data: dict) -> dict:
    """
    Accepte:
    - patient_data = {"nom":..., "sexe":..., ...}
    - ou patient_data = {"patient_info": {...}}
    Retourne toujours patient_info dict.
    """
    if not isinstance(patient_data, dict):
        return {}
    if "patient_info" in patient_data and isinstance(patient_data["patient_info"], dict):
        return patient_data["patient_info"]
    return patient_data


def normalize_biomarkers(biomarker_results):
    """
    Accepte:
    - dict: {"crp": 1.2, "hba1c": 5.4, ...}
    - list: [{"key":..., "value":..., "name":..., "unit":..., "flag":...}, ...]
    Retour:
    - mode = "dict" ou "list"
    - dict_data / list_data
    """
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
# VISUALS (MATPLOTLIB -> PNG BUFFERS)
# ============================================================

def create_biomarker_gauge(biomarker_name, value, ref_min, ref_max,
                           optimal_min=None, optimal_max=None, unit=""):
    """
    Jauge horizontale type 'Mme X'
    Retourne: BytesIO PNG
    """
    v = safe_float(value, 0.0)
    rmin = safe_float(ref_min, 0.0)
    rmax = safe_float(ref_max, rmin + 1.0)
    if rmax <= rmin:
        rmax = rmin + 1.0

    fig, ax = plt.subplots(figsize=(8, 1.2))

    total_range = rmax - rmin
    value_pos = (v - rmin) / total_range if total_range > 0 else 0.5
    value_pos = max(0, min(1, value_pos))

    color_normal = '#d1fae5'
    color_optimal = '#10b981'

    ax.barh(0, 1, height=0.4, color=color_normal, alpha=0.25)

    # Zone optimale
    if optimal_min is not None and optimal_max is not None:
        omin = safe_float(optimal_min, None)
        omax = safe_float(optimal_max, None)
        if omin is not None and omax is not None and omax > omin:
            opt_start = (omin - rmin) / total_range
            opt_width = (omax - omin) / total_range
            opt_start = max(0, min(1, opt_start))
            opt_width = max(0, min(1 - opt_start, opt_width))
            ax.barh(0, opt_width, left=opt_start, height=0.4, color=color_optimal, alpha=0.55)

    # Marker color logic
    marker_color = '#ef4444'
    if rmin <= v <= rmax:
        marker_color = '#22c55e'
    if optimal_min is not None and optimal_max is not None:
        omin = safe_float(optimal_min, None)
        omax = safe_float(optimal_max, None)
        if omin is not None and omax is not None and omin <= v <= omax:
            marker_color = '#10b981'

    ax.plot([value_pos], [0], marker='v', markersize=15, color=marker_color,
            markeredgecolor='white', markeredgewidth=2, zorder=10)

    ax.text(-0.02, 0, str(biomarker_name), va='center', ha='right', fontsize=10, fontweight='bold')
    ax.text(value_pos, 0.6, f"{v:.2f} {unit}".strip(), ha='center', va='bottom',
            fontsize=9, fontweight='bold', color=marker_color)

    ax.text(0, -0.6, f"{rmin:.1f}", ha='center', va='top', fontsize=8, color='gray')
    ax.text(1, -0.6, f"{rmax:.1f}", ha='center', va='top', fontsize=8, color='gray')

    if optimal_min is not None and optimal_max is not None:
        omin = safe_float(optimal_min, None)
        omax = safe_float(optimal_max, None)
        if omin is not None and omax is not None and omax > omin:
            opt_start_pos = (omin - rmin) / total_range
            opt_end_pos = (omax - rmin) / total_range
            ax.text(opt_start_pos, -0.9, f"Opt: {omin:.1f}", ha='center', va='top',
                    fontsize=7, color='green', style='italic')
            ax.text(opt_end_pos, -0.9, f"{omax:.1f}", ha='center', va='top',
                    fontsize=7, color='green', style='italic')

    ax.set_xlim(-0.15, 1.05)
    ax.set_ylim(-1.2, 1)
    ax.axis('off')

    buf = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', transparent=True)
    buf.seek(0)
    plt.close(fig)

    return buf


def create_biological_age_visual(biological_age, chronological_age, delta, delta_percent):
    """
    Visualisation élégante de l'âge biologique - Design haut de gamme
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 3.5))
    fig.patch.set_facecolor('white')
    
    bio_age = safe_float(biological_age, 50)
    chrono_age = safe_float(chronological_age, 50)
    delta_val = safe_float(delta, 0)
    
    # ===== GRAPHIQUE 1: Comparaison des âges =====
    ages = ['Chronologique', 'Biologique']
    values = [chrono_age, bio_age]
    
    bar_colors = ['#3b82f6', '#10b981' if delta_val <= 0 else '#f59e0b']
    
    bars = ax1.bar(ages, values, color=bar_colors, alpha=0.85, 
                   edgecolor='white', linewidth=3, width=0.6)
    
    for bar, val in zip(bars, values):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2, height + 1,
                f'{val:.1f}\nans', ha='center', va='bottom',
                fontsize=13, fontweight='bold', color=bar.get_facecolor())
    
    if abs(delta_val) > 0:
        y_middle = (bio_age + chrono_age) / 2
        ax1.plot([0, 1], [y_middle, y_middle], 'k--', alpha=0.3, linewidth=1)
    
    ax1.set_ylim(0, max(values) * 1.3)
    ax1.set_ylabel('Âge (années)', fontsize=11, fontweight='bold')
    ax1.set_title('Comparaison des Âges', fontsize=12, fontweight='bold', pad=15)
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)
    ax1.grid(axis='y', alpha=0.2, linestyle='--')
    
    # ===== GRAPHIQUE 2: Delta et pourcentage =====
    delta_color = '#10b981' if delta_val <= 0 else '#f59e0b'
    delta_text = 'Rajeunissement' if delta_val < 0 else ('Vieillissement' if delta_val > 0 else 'Équilibre')
    
    ax2.text(0.5, 0.65, f"{delta_val:+.1f}", ha='center', va='center',
            fontsize=48, fontweight='bold', color=delta_color,
            transform=ax2.transAxes)
    
    ax2.text(0.5, 0.42, 'ans', ha='center', va='center',
            fontsize=16, color='#6b7280',
            transform=ax2.transAxes)
    
    ax2.text(0.5, 0.25, f"({delta_percent:+.1f}%)", ha='center', va='center',
            fontsize=18, fontweight='bold', color=delta_color,
            transform=ax2.transAxes)
    
    ax2.text(0.5, 0.08, delta_text, ha='center', va='center',
            fontsize=13, fontweight='600', color=delta_color,
            style='italic', transform=ax2.transAxes)
    
    rect = Rectangle((0.05, 0.05), 0.9, 0.9, linewidth=3,
                     edgecolor=delta_color, facecolor='none',
                     transform=ax2.transAxes, alpha=0.6)
    ax2.add_patch(rect)
    
    ax2.set_xlim(0, 1)
    ax2.set_ylim(0, 1)
    ax2.axis('off')
    ax2.set_title('Delta Biologique', fontsize=12, fontweight='bold', pad=15)
    
    plt.tight_layout()
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight',
                transparent=False, facecolor='white')
    buf.seek(0)
    plt.close(fig)
    return buf


def create_category_bars(category_scores: dict):
    fig, ax = plt.subplots(figsize=(8, 5))
    categories = list(category_scores.keys())
    scores = [safe_float(category_scores[k], 0.0) for k in categories]

    categories.reverse()
    scores.reverse()

    colors_list = []
    for score in scores:
        if score >= 90:
            colors_list.append('#10b981')
        elif score >= 80:
            colors_list.append('#3b82f6')
        elif score >= 70:
            colors_list.append('#f59e0b')
        else:
            colors_list.append('#ef4444')

    y_pos = np.arange(len(categories))
    bars = ax.barh(y_pos, scores, color=colors_list, alpha=0.85, edgecolor='white', linewidth=2)

    for bar, score in zip(bars, scores):
        ax.text(score + 2, bar.get_y() + bar.get_height()/2,
                f'{score:.1f}', va='center', fontsize=10, fontweight='bold')

    ax.set_yticks(y_pos)
    ax.set_yticklabels([cat.replace('_', ' ').title() for cat in categories], fontsize=10)
    ax.set_xlabel('Score (/100)', fontsize=11, fontweight='bold')
    ax.set_xlim(0, 105)
    ax.set_title('Scores par Catégorie', fontsize=13, fontweight='bold', pad=15)
    ax.grid(axis='x', alpha=0.3, linestyle='--')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    buf.seek(0)
    plt.close(fig)
    return buf


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
    max_gauges_abnormal=None,
    max_gauges_watch=None
):
    """
    Génère un rapport PDF professionnel ALGO-LIFE v5.0
    - patient_data: dict (ou dict contenant patient_info)
    - biomarker_results: dict OU list[dict]
    - biomarker_db: objet optionnel ayant:
        - get_reference_ranges() -> dict
        - classify_biomarker(key, value, age, sexe) -> dict {status, interpretation, icon}
    - TOUTES LES JAUGES AFFICHÉES (pas de limite max_gauges)
    """
    engine_results = engine_results or {}

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=15*mm,
        bottomMargin=15*mm,
        leftMargin=20*mm,
        rightMargin=20*mm
    )
    story = []
    styles = getSampleStyleSheet()

    # ===== STYLES PERSONNALISÉS =====
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=32,
        textColor=colors.HexColor('#667eea'),
        spaceAfter=5,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )

    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=13,
        textColor=colors.HexColor('#4A5568'),
        spaceAfter=25,
        alignment=TA_CENTER,
        fontName='Helvetica'
    )

    heading2_style = ParagraphStyle(
        'CustomHeading2',
        parent=styles['Heading2'],
        fontSize=18,
        textColor=colors.HexColor('#2C3E50'),
        spaceAfter=10,
        spaceBefore=15,
        fontName='Helvetica-Bold',
        borderWidth=1,
        borderColor=colors.HexColor('#667eea'),
        borderPadding=8,
        backColor=colors.HexColor('#f8f9fa')
    )

    heading3_style = ParagraphStyle(
        'CustomHeading3',
        parent=styles['Heading3'],
        fontSize=14,
        textColor=colors.HexColor('#34495E'),
        spaceAfter=8,
        spaceBefore=10,
        fontName='Helvetica-Bold'
    )

    warning_style = ParagraphStyle(
        'Warning',
        parent=styles['Normal'],
        fontSize=11,
        textColor=colors.HexColor('#d97706'),
        backColor=colors.HexColor('#fef3c7'),
        borderWidth=1,
        borderColor=colors.HexColor('#f59e0b'),
        borderPadding=10,
        spaceAfter=10
    )

    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.grey,
        alignment=TA_CENTER,
        spaceAfter=3
    )

    interp_style = ParagraphStyle(
        'Interpretation',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#6b7280'),
        leftIndent=10,
        spaceAfter=10
    )

    # ===== NORMALISATION =====
    patient_info = normalize_patient(patient_data)
    mode, biomarkers_dict, biomarkers_list = normalize_biomarkers(biomarker_results)

    # ===== EN-TÊTE =====
    story.append(Paragraph("🧬 ALGO-LIFE", title_style))
    story.append(Paragraph(
        "Rapport d'Analyses Biologiques<br/>Analyse Multimodale de Santé Fonctionnelle",
        subtitle_style
    ))
    story.append(Spacer(1, 5))

    # ===== INFORMATIONS PATIENT =====
    story.append(Paragraph("Informations Patient", heading2_style))
    story.append(Spacer(1, 5))

    patient_table_data = [
        ['', ''],
        ['PATIENT', patient_info.get('nom', patient_info.get('name', '—'))],
        ['GENRE', patient_info.get('sexe', patient_info.get('sex', '—'))],
        ['ÂGE', f"{patient_info.get('age', '—')} ans"],
        ['TAILLE / POIDS', f"{patient_info.get('height', '—')} cm / {patient_info.get('weight', '—')} kg"],
        ['IMC', f"{patient_info.get('imc', '—')}" if patient_info.get('imc') else '—'],
        ['DATE PRÉLÈVEMENT', patient_info.get('prelevement_date', '—')],
        ['DATE DU RAPPORT', datetime.now().strftime('%d/%m/%Y')],
    ]

    patient_table = Table(patient_table_data, colWidths=[70*mm, 100*mm])
    patient_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 1), (0, -1), colors.HexColor('#667eea')),
        ('TEXTCOLOR', (0, 1), (0, -1), colors.white),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 1), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 1), (-1, -1), 1, colors.HexColor('#e5e7eb')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (1, 1), (1, -1), [colors.white, colors.HexColor('#f9fafb')])
    ]))
    story.append(patient_table)
    story.append(Spacer(1, 20))

    # ===== SCORES PRINCIPAUX =====
    story.append(Paragraph("Âge Biologique & Score Santé", heading2_style))
    story.append(Spacer(1, 10))

    if biological_age and health_score:
        # Visualisation âge biologique (design haut de gamme)
        age_visual_buf = create_biological_age_visual(
            biological_age.get('biological_age'),
            biological_age.get('chronological_age'),
            biological_age.get('delta'),
            biological_age.get('delta_percent')
        )
        story.append(Image(age_visual_buf, width=170*mm, height=60*mm))
        story.append(Spacer(1, 15))

        delta = safe_float(biological_age.get('delta'), 0.0)
        delta_percent = safe_float(biological_age.get('delta_percent'), 0.0)
        delta_color = 'green' if delta <= 0 else 'orange'

        info_data = [
            ['Âge Biologique', f"<font size=16><b>{biological_age.get('biological_age', '—')} ans</b></font>"],
            ['Âge Chronologique', f"{biological_age.get('chronological_age', '—')} ans"],
            ['Delta', f"<font color='{delta_color}'><b>{delta:+.1f} ans ({delta_percent:+.1f}%)</b></font>"],
            ['Status', biological_age.get('status', '—')],
            ['', ''],
            ['Interprétation', biological_age.get('interpretation', '—')],
        ]

        info_table = Table(info_data, colWidths=[50*mm, 100*mm])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -2), colors.HexColor('#f3f4f6')),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, 4), 0.5, colors.HexColor('#e5e7eb')),
            ('SPAN', (0, 5), (1, 5)),
            ('VALIGN', (0, 0), (-1, -1), 'TOP')
        ]))
        story.append(info_table)
        story.append(Spacer(1, 15))

        # Score de santé global
        score_value = safe_float(health_score.get('global_score', 0), 0)
        score_color = 'green' if score_value >= 80 else ('orange' if score_value >= 60 else 'red')

        score_data = [
            ['Score Santé Global', f"<font size=20 color='{score_color}'><b>{score_value:.1f}/100</b></font>"],
            ['Grade', f"<font size=14 color='{score_color}'><b>{health_score.get('grade', '—')}</b></font>"],
        ]

        score_table = Table(score_data, colWidths=[60*mm, 110*mm])
        score_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#667eea')),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.white),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('TOPPADDING', (0, 0), (-1, -1), 15),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb')),
        ]))
        story.append(score_table)
        story.append(Spacer(1, 15))

        if health_score.get('category_scores'):
            story.append(Paragraph("Scores par Catégorie de Santé", heading3_style))
            category_bars_buf = create_category_bars(health_score['category_scores'])
            story.append(Image(category_bars_buf, width=160*mm, height=100*mm))
    else:
        story.append(Paragraph(
            "⚠️ <b>Les scores ne sont pas disponibles.</b><br/>"
            "L'analyse est incomplète. Vérifie extraction biomarqueurs + calculs.",
            warning_style
        ))

    story.append(Spacer(1, 10))
    story.append(PageBreak())

    # ===== BIOMARQUEURS AVEC CLASSIFICATION =====
    story.append(Paragraph("Résultats Détaillés des Biomarqueurs", heading2_style))
    story.append(Spacer(1, 10))

    normaux, a_surveiller, anormaux = [], [], []

    # Classification si biomarker_db dispo
    if biomarker_db is not None:
        try:
            refs_db = biomarker_db.get_reference_ranges()

            if mode == "dict":
                iterable = list(biomarkers_dict.items())
            else:
                iterable = [(it["key"], it["value"]) for it in biomarkers_list]

            for biomarker_key, value in iterable:
                if biomarker_key not in refs_db:
                    continue

                classification = biomarker_db.classify_biomarker(
                    biomarker_key, value,
                    patient_info.get('age'),
                    patient_info.get('sexe')
                )
                ref_data = refs_db[biomarker_key]

                item = {
                    'key': biomarker_key,
                    'name': str(biomarker_key).replace('_', ' ').title(),
                    'value': safe_float(value, value),
                    'unit': ref_data.get('unit', ''),
                    'classification': classification,
                    'ref_data': ref_data
                }

                st = (classification.get('status') or '').lower()
                if st in ('optimal', 'normal', 'ok'):
                    normaux.append(item)
                elif st in ('insufficient', 'low', 'elevated', 'watch', 'surveiller', 'monitor'):
                    a_surveiller.append(item)
                else:
                    anormaux.append(item)

        except Exception as e:
            story.append(Paragraph(
                f"⚠️ Classification BiomarkerDatabase indisponible.<br/>Erreur: {str(e)}",
                styles['Normal']
            ))
            biomarker_db = None

    # Si pas de DB : fallback tableau brut
    if biomarker_db is None:
        if mode == "dict":
            bio_data = [['Biomarqueur', 'Valeur']]
            for key, value in biomarkers_dict.items():
                bio_data.append([str(key).replace('_', ' ').title(), f"{safe_float(value, value)}"])
        else:
            bio_data = [['Catégorie', 'Biomarqueur', 'Valeur', 'Normes', 'Statut']]
            for it in biomarkers_list:
                bio_data.append([
                    it.get("category", "—"),
                    it.get("name", "—"),
                    str(it.get("value", "—")),
                    str(it.get("range", "—")),
                    str(it.get("flag", "—")),
                ])

        bio_table = Table(bio_data, colWidths=[90*mm, 70*mm] if mode == "dict" else [40*mm, 60*mm, 30*mm, 30*mm, 20*mm])
        bio_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')])
        ]))
        story.append(bio_table)
    else:
        total = max(1, (len(normaux) + len(a_surveiller) + len(anormaux)))
        summary_data = [
            ['Catégorie', 'Nombre', '%'],
            ['✅ Normaux', str(len(normaux)), f"{len(normaux)/total*100:.0f}%"],
            ['⚡ À surveiller', str(len(a_surveiller)), f"{len(a_surveiller)/total*100:.0f}%"],
            ['⚠️ Anormaux', str(len(anormaux)), f"{len(anormaux)/total*100:.0f}%"]
        ]
        summary_table = Table(summary_data, colWidths=[80*mm, 40*mm, 40*mm])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#d1fae5')),
            ('BACKGROUND', (0, 2), (-1, 2), colors.HexColor('#fef3c7')),
            ('BACKGROUND', (0, 3), (-1, 3), colors.HexColor('#fee2e2')),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.white),
            ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold')
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 15))

        # JAUGES ANORMAUX - TOUTES AFFICHÉES
        if anormaux:
            story.append(Paragraph("⚠️ Biomarqueurs Anormaux - Analyse Détaillée", heading3_style))
            story.append(Spacer(1, 5))

            for item in anormaux:
                ref_data = item['ref_data']

                ref_min, ref_max = 0, 100
                if isinstance(ref_data.get('normal'), (list, tuple)) and len(ref_data['normal']) == 2:
                    ref_min, ref_max = ref_data['normal']
                elif patient_info.get('sexe') == 'Féminin' and isinstance(ref_data.get('normal_female'), (list, tuple)):
                    ref_min, ref_max = ref_data['normal_female']
                elif patient_info.get('sexe') == 'Masculin' and isinstance(ref_data.get('normal_male'), (list, tuple)):
                    ref_min, ref_max = ref_data['normal_male']

                opt_min, opt_max = None, None
                if isinstance(ref_data.get('optimal'), (list, tuple)) and len(ref_data['optimal']) == 2:
                    opt_min, opt_max = ref_data['optimal']
                elif patient_info.get('sexe') == 'Féminin' and isinstance(ref_data.get('optimal_female'), (list, tuple)):
                    opt_min, opt_max = ref_data['optimal_female']
                elif patient_info.get('sexe') == 'Masculin' and isinstance(ref_data.get('optimal_male'), (list, tuple)):
                    opt_min, opt_max = ref_data['optimal_male']

                if ref_min is None:
                    ref_min = 0
                if ref_max is None:
                    v = safe_float(item['value'], 1.0)
                    ref_max = v * 1.5 if v else 1.0

                gauge_buf = create_biomarker_gauge(
                    item['name'], safe_float(item['value'], 0.0),
                    ref_min, ref_max,
                    opt_min, opt_max,
                    item['unit']
                )
                story.append(Image(gauge_buf, width=150*mm, height=25*mm))
                story.append(Paragraph(
                    f"<i>{item['classification'].get('icon','')} {item['classification'].get('interpretation','')}</i>",
                    interp_style
                ))

        # JAUGES A SURVEILLER - TOUTES AFFICHÉES
        if a_surveiller:
            story.append(Spacer(1, 10))
            story.append(Paragraph("⚡ Biomarqueurs À Surveiller", heading3_style))
            story.append(Spacer(1, 5))

            for item in a_surveiller:
                ref_data = item['ref_data']

                ref_min, ref_max = 0, 100
                if isinstance(ref_data.get('normal'), (list, tuple)) and len(ref_data['normal']) == 2:
                    ref_min, ref_max = ref_data['normal']
                elif patient_info.get('sexe') == 'Féminin' and isinstance(ref_data.get('normal_female'), (list, tuple)):
                    ref_min, ref_max = ref_data['normal_female']
                elif patient_info.get('sexe') == 'Masculin' and isinstance(ref_data.get('normal_male'), (list, tuple)):
                    ref_min, ref_max = ref_data['normal_male']

                opt_min, opt_max = None, None
                if isinstance(ref_data.get('optimal'), (list, tuple)) and len(ref_data['optimal']) == 2:
                    opt_min, opt_max = ref_data['optimal']
                elif patient_info.get('sexe') == 'Féminin' and isinstance(ref_data.get('optimal_female'), (list, tuple)):
                    opt_min, opt_max = ref_data['optimal_female']
                elif patient_info.get('sexe') == 'Masculin' and isinstance(ref_data.get('optimal_male'), (list, tuple)):
                    opt_min, opt_max = ref_data['optimal_male']

                if ref_min is None:
                    ref_min = 0
                if ref_max is None:
                    v = safe_float(item['value'], 1.0)
                    ref_max = v * 1.5 if v else 1.0

                gauge_buf = create_biomarker_gauge(
                    item['name'], safe_float(item['value'], 0.0),
                    ref_min, ref_max,
                    opt_min, opt_max,
                    item['unit']
                )
                story.append(Image(gauge_buf, width=150*mm, height=25*mm))
                story.append(Paragraph(
                    f"<i>{item['classification'].get('icon','')} {item['classification'].get('interpretation','')}</i>",
                    interp_style
                ))

        # Tableau compact normaux
        if normaux:
            story.append(Spacer(1, 10))
            story.append(Paragraph("✅ Biomarqueurs Normaux", heading3_style))
            story.append(Spacer(1, 5))

            normaux_data = [['Biomarqueur', 'Valeur', 'Unité', 'Status']]
            for item in normaux:
                v = safe_float(item['value'], item['value'])
                normaux_data.append([
                    item['name'],
                    f"{v:.2f}" if isinstance(v, (int, float)) else str(v),
                    item['unit'],
                    f"{item['classification'].get('icon','')} {str(item['classification'].get('status','')).title()}"
                ])

            normaux_table = Table(normaux_data, colWidths=[70*mm, 30*mm, 25*mm, 35*mm])
            normaux_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#d1fae5')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#065f46')),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (1, 1), (2, -1), 'CENTER'),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')])
            ]))
            story.append(normaux_table)

    story.append(Spacer(1, 15))
    story.append(PageBreak())

    # ===== BESOINS NUTRITIONNELS =====
    if nutritional_needs:
        story.append(Paragraph("Besoins Nutritionnels Calculés", heading2_style))
        story.append(Spacer(1, 10))

        nutri_data = [
            ['Métrique', 'Valeur', 'Description'],
            ['Métabolisme de Base (BMR)', f"{safe_float(nutritional_needs.get('bmr'), 0):.0f} kcal/jour", 'Énergie au repos'],
            ['Dépense Énergétique Totale (DET)', f"{safe_float(nutritional_needs.get('det'), 0):.0f} kcal/jour", 'Besoin calorique journalier'],
            ['Protéines', f"{safe_float(nutritional_needs.get('proteins_g'), 0):.0f} g/jour", 'Objectif protéines'],
            ['Lipides', f"{safe_float(nutritional_needs.get('lipids_g'), 0):.0f} g/jour", 'Objectif lipides'],
            ['Glucides', f"{safe_float(nutritional_needs.get('carbs_g'), 0):.0f} g/jour", 'Objectif glucides'],
        ]
        nutri_table = Table(nutri_data, colWidths=[70*mm, 50*mm, 40*mm])
        nutri_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.white),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')]),
        ]))
        story.append(nutri_table)
        story.append(Spacer(1, 15))

    # ===== RECOMMANDATIONS =====
    if recommendations:
        story.append(Paragraph("💡 Recommandations Personnalisées", heading2_style))
        story.append(Spacer(1, 10))

        recs = recommendations.get('recommendations', {}) if isinstance(recommendations, dict) else {}
        priorities = recommendations.get('priorities', []) if isinstance(recommendations, dict) else []

        if priorities:
            story.append(Paragraph("⚠️ Priorités d'Action Immédiate", heading3_style))
            for i, priority in enumerate(priorities[:5], 1):
                biomarker_name = str(priority.get('biomarker', '')).replace('_', ' ').title()
                priority_level = str(priority.get('priority', '—'))
                priority_color = '#ef4444' if 'élev' in priority_level.lower() else '#f59e0b'
                story.append(Paragraph(
                    f"<b>{i}.</b> <font color='{priority_color}'><b>{biomarker_name}</b></font> "
                    f"- Priorité: <b>{priority_level}</b>",
                    styles['Normal']
                ))
            story.append(Spacer(1, 12))

        if recs.get('supplements'):
            story.append(Paragraph("💊 Micronutrition Ciblée", heading3_style))
            for supp in recs['supplements'][:12]:
                story.append(Paragraph(f"• {supp}", styles['Normal']))
            story.append(Spacer(1, 10))

        if recs.get('alimentation'):
            story.append(Paragraph("🥗 Alimentation & Nutrition", heading3_style))
            for alim in recs['alimentation'][:12]:
                story.append(Paragraph(f"• {alim}", styles['Normal']))
            story.append(Spacer(1, 10))

        if recs.get('lifestyle'):
            story.append(Paragraph("🏃 Optimisation du Mode de Vie", heading3_style))
            for life in recs['lifestyle'][:12]:
                story.append(Paragraph(f"• {life}", styles['Normal']))

    # ===== PLAN DE SUIVI =====
    story.append(Spacer(1, 20))
    story.append(Paragraph("Plan de Suivi Recommandé", heading2_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph("<b>Prochain contrôle:</b> 3-6 mois selon évolution", styles['Normal']))
    story.append(Spacer(1, 5))

    if biomarker_db is not None and anormaux:
        story.append(Paragraph("<b>Biomarqueurs à recontrôler en priorité:</b>", styles['Normal']))
        for item in anormaux[:5]:
            story.append(Paragraph(f"• {item['name']}", styles['Normal']))

    # ===== FOOTER =====
    story.append(Spacer(1, 30))
    story.append(Paragraph("_" * 100, footer_style))
    story.append(Spacer(1, 8))
    story.append(Paragraph("<b>Rapport établi par Dr Thibault SUTTER - Biologiste</b>", footer_style))
    story.append(Paragraph("Product Manager Functional Biology, Espace Lab SA (Unilabs Group)", footer_style))
    story.append(Paragraph("ALGO-LIFE | Plateforme Multimodale d'Analyse de Santé Fonctionnelle", footer_style))
    story.append(Spacer(1, 5))
    story.append(Paragraph("© 2026 ALGO-LIFE - Document médical confidentiel", footer_style))

    # ===== BUILD PDF =====
    try:
        doc.build(story)
        buffer.seek(0)
        return buffer
    except Exception as e:
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        story = [
            Paragraph("ALGO-LIFE - Erreur de Génération", title_style),
            Spacer(1, 20),
            Paragraph(f"Une erreur s'est produite: {str(e)}", styles['Normal'])
        ]
        doc.build(story)
        buffer.seek(0)
        return buffer


__all__ = ["generate_algolife_pdf_report"]


if __name__ == "__main__":
    print("✅ Module algolife_pdf_generator v5.0 chargé!")
    print("✨ Améliorations:")
    print("   - Design haut de gamme pour âge biologique")
    print("   - TOUTES les jauges affichées (pas de limite)")
    print("   - Visualisations élégantes")
