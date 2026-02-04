"""
ALGO-LIFE / UNILABS - Générateur PDF Premium v2.0
✅ Design moderne et futuriste
✅ Biomarqueurs avec jauges visuelles colorées
✅ Logos professionnels
✅ Sections de recommandations dans des cadres stylisés
✅ Bug des valeurs par défaut corrigé
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Dict, Any, List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, 
    KeepTogether, Image as ReportLabImage, Frame, PageTemplate
)
from reportlab.pdfgen import canvas
from reportlab.graphics.shapes import Drawing, Rect, Circle, Line, String, Polygon
from reportlab.graphics import renderPDF


# =====================================================================
# COLORS & DESIGN CONSTANTS
# =====================================================================
PRIMARY_BLUE = colors.HexColor("#0066CC")  # UNILABS Blue
ACCENT_CYAN = colors.HexColor("#00BCD4")   # AlgoLife Cyan
DNA_PURPLE = colors.HexColor("#6A1B9A")    # DNA Purple
NORMAL_GREEN = colors.HexColor("#4CAF50")
WARNING_ORANGE = colors.HexColor("#FF9800")
CRITICAL_RED = colors.HexColor("#F44336")
GREY_DARK = colors.HexColor("#424242")
GREY_MEDIUM = colors.HexColor("#757575")
GREY_LIGHT = colors.HexColor("#EEEEEE")
WHITE = colors.white
BACKGROUND_LIGHT = colors.HexColor("#FAFAFA")


# =====================================================================
# HELPERS
# =====================================================================
def _safe_str(x: Any) -> str:
    """Convertit en string de manière sûre"""
    if x is None or x == "":
        return ""
    return str(x).strip()


def _safe_float(x: Any, default: float = 0.0) -> float:
    """Convertit en float de manière sûre"""
    if x is None or x == "":
        return default
    try:
        # Remplacer virgule par point si nécessaire
        if isinstance(x, str):
            x = x.replace(",", ".")
        return float(x)
    except Exception:
        return default


def _parse_reference(ref_str: str) -> tuple[float, float]:
    """
    Parse une référence au format 'min-max' ou 'min — max'
    Retourne (min, max) ou (0.0, 100.0) si impossible à parser
    """
    try:
        if not ref_str or ref_str == "Non spécifiées" or ref_str == "":
            return (0.0, 100.0)
        
        # Nettoyer et normaliser le format
        ref_str = str(ref_str).strip()
        ref_str = ref_str.replace(" — ", "-").replace("—", "-").replace(" - ", "-")
        
        parts = ref_str.split("-")
        
        if len(parts) == 2:
            min_val = _safe_float(parts[0].strip(), 0.0)
            max_val = _safe_float(parts[1].strip(), 100.0)
            
            # Vérifier que min < max
            if min_val >= max_val:
                return (0.0, 100.0)
            
            return (min_val, max_val)
        
        return (0.0, 100.0)
    except Exception:
        return (0.0, 100.0)



# =====================================================================
# NORMALISATION DES ENTREES (compatibilité app / extractors / excel)
# =====================================================================
def normalize_biology_data(biology_data: Any) -> List[Dict[str, Any]]:
    """Accepte plusieurs formats et retourne une liste de biomarqueurs au format attendu.

    Formats acceptés:
    - List[Dict] déjà au bon format: {"name","value","unit","reference","status","category"}
    - Dict[str, Dict]: {"Ferritine": {"value":..., "unit":..., "reference":..., "status":...}, ...}
    - List[Dict] au format app: {"biomarker"/"marqueur"/"name", "valeur"/"value", "unite"/"unit", "ref"/"reference", "statut"/"status", "category"/"categorie"}
    """
    if not biology_data:
        return []

    # 1) Dict mapping name -> fields
    if isinstance(biology_data, dict):
        out: List[Dict[str, Any]] = []
        for k, v in biology_data.items():
            if isinstance(v, dict):
                out.append({
                    "name": _safe_str(v.get("name", k)),
                    "value": v.get("value", v.get("valeur", v.get("result", ""))),
                    "unit": _safe_str(v.get("unit", v.get("unite", v.get("units", "")))),
                    "reference": _safe_str(v.get("reference", v.get("ref", v.get("norme", v.get("range", ""))))),
                    "status": _safe_str(v.get("status", v.get("statut", ""))),
                    "category": _safe_str(v.get("category", v.get("categorie", "Autres"))) or "Autres",
                })
        return out

    # 2) List of dicts
    if isinstance(biology_data, list):
        out: List[Dict[str, Any]] = []
        for item in biology_data:
            if not isinstance(item, dict):
                continue

            name = item.get("name") or item.get("biomarker") or item.get("marqueur") or item.get("parametre") or item.get("parameter")
            # Si c'est un dict extrait brut type {"Ferritine": {...}} dans une liste
            if name is None and len(item) == 1 and isinstance(next(iter(item.values())), dict):
                k = next(iter(item.keys()))
                v = next(iter(item.values()))
                out.append({
                    "name": _safe_str(v.get("name", k)),
                    "value": v.get("value", v.get("valeur", v.get("result", ""))),
                    "unit": _safe_str(v.get("unit", v.get("unite", v.get("units", "")))),
                    "reference": _safe_str(v.get("reference", v.get("ref", v.get("norme", v.get("range", ""))))),
                    "status": _safe_str(v.get("status", v.get("statut", ""))),
                    "category": _safe_str(v.get("category", v.get("categorie", "Autres"))) or "Autres",
                })
                continue

            out.append({
                "name": _safe_str(name),
                "value": item.get("value", item.get("valeur", item.get("result", ""))),
                "unit": _safe_str(item.get("unit", item.get("unite", item.get("units", "")))),
                "reference": _safe_str(item.get("reference", item.get("ref", item.get("norme", item.get("range", ""))))),
                "status": _safe_str(item.get("status", item.get("statut", ""))),
                "category": _safe_str(item.get("category", item.get("categorie", "Autres"))) or "Autres",
            })

        # Filtrer les entrées totalement vides
        out = [b for b in out if b.get("name")]
        return out

    return []


def create_dna_logo(width: float = 4*cm, height: float = 4*cm) -> Drawing:
    """
    Crée un logo ADN stylisé pour ALGO-LIFE
    """
    d = Drawing(width, height)
    
    # Hélice ADN simplifiée
    center_x = width / 2
    center_y = height / 2
    
    # Spirale gauche (bleu)
    for i in range(8):
        y = height * 0.1 + (i * height * 0.1)
        x_offset = 0.3 * cm * (1 if i % 2 == 0 else -1)
        
        circle = Circle(center_x + x_offset, y, 0.15*cm)
        circle.fillColor = PRIMARY_BLUE
        circle.strokeColor = PRIMARY_BLUE
        d.add(circle)
    
    # Spirale droite (cyan)
    for i in range(8):
        y = height * 0.1 + (i * height * 0.1)
        x_offset = 0.3 * cm * (-1 if i % 2 == 0 else 1)
        
        circle = Circle(center_x + x_offset, y, 0.15*cm)
        circle.fillColor = ACCENT_CYAN
        circle.strokeColor = ACCENT_CYAN
        d.add(circle)
    
    return d


def create_biomarker_gauge(biomarker: Dict[str, Any], width: float = 16*cm, height: float = 3.5*cm) -> Drawing:
    """
    Crée une jauge visuelle élégante et moderne pour un biomarqueur
    
    Args:
        biomarker: Dict avec keys: name, value, unit, reference, status
        width: Largeur du dessin
        height: Hauteur du dessin
    
    Returns:
        Drawing ReportLab
    """
    d = Drawing(width, height)
    
    # Récupération des données
    name = _safe_str(biomarker.get("name", ""))
    value = _safe_float(biomarker.get("value"), 0.0)
    unit = _safe_str(biomarker.get("unit", ""))
    reference = _safe_str(biomarker.get("reference", ""))
    status = _safe_str(biomarker.get("status", "Inconnu"))
    
    # Parse la référence
    min_ref, max_ref = _parse_reference(reference)
    
    # Configuration de la jauge
    gauge_width = width * 0.65
    gauge_height = 12
    gauge_x = width * 0.22
    gauge_y = height * 0.35
    
    # Couleur du statut
    if status == "Normal" or status == "normal":
        status_color = NORMAL_GREEN
    elif status == "Bas" or status == "bas":
        status_color = WARNING_ORANGE
    elif status == "Élevé" or status == "élevé" or status == "Elevé":
        status_color = CRITICAL_RED
    else:
        status_color = GREY_MEDIUM
    
    # ─────────────────────────────────────────────────────────────────
    # 1. Indicateur de statut (cercle coloré à gauche)
    # ─────────────────────────────────────────────────────────────────
    dot_x = width * 0.015
    dot_y = height * 0.65
    
    status_circle = Circle(dot_x, dot_y, 6)
    status_circle.fillColor = status_color
    status_circle.strokeColor = status_color
    d.add(status_circle)
    
    # ─────────────────────────────────────────────────────────────────
    # 2. Nom du biomarqueur
    # ─────────────────────────────────────────────────────────────────
    name_str = String(dot_x + 12, dot_y - 3, name[:60])  # Limiter à 60 caractères
    name_str.fontName = 'Helvetica-Bold'
    name_str.fontSize = 11
    name_str.fillColor = GREY_DARK
    d.add(name_str)
    
    # ─────────────────────────────────────────────────────────────────
    # 3. Barre de référence (fond gris)
    # ─────────────────────────────────────────────────────────────────
    bg_rect = Rect(gauge_x, gauge_y, gauge_width, gauge_height)
    bg_rect.fillColor = GREY_LIGHT
    bg_rect.strokeColor = colors.HexColor("#CCCCCC")
    bg_rect.strokeWidth = 0.5
    bg_rect.rx = 3  # Coins arrondis
    bg_rect.ry = 3
    d.add(bg_rect)
    
    # ─────────────────────────────────────────────────────────────────
    # 4. Zone normale (barre verte au centre)
    # ─────────────────────────────────────────────────────────────────
    # La zone normale représente 40-60% de la largeur totale
    normal_start_x = gauge_x + (gauge_width * 0.35)
    normal_width = gauge_width * 0.30
    
    normal_rect = Rect(normal_start_x, gauge_y + 1, normal_width, gauge_height - 2)
    normal_rect.fillColor = NORMAL_GREEN
    normal_rect.strokeColor = None
    normal_rect.fillOpacity = 0.3
    normal_rect.rx = 2
    normal_rect.ry = 2
    d.add(normal_rect)
    
    # ─────────────────────────────────────────────────────────────────
    # 5. Indicateur de position de la valeur du patient
    # ─────────────────────────────────────────────────────────────────
    
    # Calculer la position relative de la valeur
    if max_ref > min_ref and min_ref != max_ref:
        # Position relative entre min et max
        value_position_pct = (value - min_ref) / (max_ref - min_ref)
    else:
        value_position_pct = 0.5  # Centré par défaut
    
    # Limiter entre 0 et 1
    value_position_pct = max(0.0, min(1.0, value_position_pct))
    
    # Position X de l'indicateur
    indicator_x = gauge_x + (gauge_width * value_position_pct)
    
    # Triangle pointant vers le bas (indicateur)
    triangle_points = [
        indicator_x, gauge_y + gauge_height + 2,
        indicator_x - 5, gauge_y + gauge_height + 12,
        indicator_x + 5, gauge_y + gauge_height + 12
    ]
    
    triangle = Polygon(triangle_points)
    triangle.fillColor = status_color
    triangle.strokeColor = status_color
    d.add(triangle)
    
    # Ligne verticale de l'indicateur
    indicator_line = Line(indicator_x, gauge_y, indicator_x, gauge_y + gauge_height)
    indicator_line.strokeColor = status_color
    indicator_line.strokeWidth = 2
    d.add(indicator_line)
    
    # ─────────────────────────────────────────────────────────────────
    # 6. Labels des bornes de référence
    # ─────────────────────────────────────────────────────────────────
    
    # Borne min
    if min_ref != 0.0 or max_ref != 100.0:  # N'afficher que si les bornes sont définies
        min_label = String(gauge_x - 5, gauge_y + gauge_height / 2 - 3, f"{min_ref:.1f}")
        min_label.fontName = 'Helvetica'
        min_label.fontSize = 8
        min_label.fillColor = GREY_MEDIUM
        min_label.textAnchor = 'end'
        d.add(min_label)
        
        # Borne max
        max_label = String(gauge_x + gauge_width + 5, gauge_y + gauge_height / 2 - 3, f"{max_ref:.1f}")
        max_label.fontName = 'Helvetica'
        max_label.fontSize = 8
        max_label.fillColor = GREY_MEDIUM
        max_label.textAnchor = 'start'
        d.add(max_label)
    
    # ─────────────────────────────────────────────────────────────────
    # 7. Valeur du patient (grand texte à droite)
    # ─────────────────────────────────────────────────────────────────
    
    value_text = f"{value:.2f}" if value < 100 else f"{value:.1f}"
    if unit:
        value_text += f" {unit}"
    
    value_x = gauge_x + gauge_width + 0.8*cm
    value_label = String(value_x, gauge_y + gauge_height / 2 - 5, value_text)
    value_label.fontName = 'Helvetica-Bold'
    value_label.fontSize = 14
    value_label.fillColor = status_color
    value_label.textAnchor = 'start'
    d.add(value_label)
    
    # Label "Normes:" au-dessus de la jauge
    if min_ref != 0.0 or max_ref != 100.0:
        norms_label = String(gauge_x, gauge_y - 8, f"Normes : {min_ref:.1f} — {max_ref:.1f}")
        norms_label.fontName = 'Helvetica'
        norms_label.fontSize = 8
        norms_label.fillColor = GREY_MEDIUM
        d.add(norms_label)
    
    return d


def create_recommendation_box(title: str, items: List[str], color: colors.HexColor = PRIMARY_BLUE) -> Table:
    """
    Crée une boîte de recommandation stylisée
    
    Args:
        title: Titre de la section
        items: Liste des items à afficher
        color: Couleur de la bordure et du titre
    
    Returns:
        Table ReportLab formatée
    """
    from reportlab.lib.styles import getSampleStyleSheet
    
    styles = getSampleStyleSheet()
    
    # Style pour le titre
    title_style = ParagraphStyle(
        'RecoTitle',
        parent=styles['Normal'],
        fontSize=12,
        fontName='Helvetica-Bold',
        textColor=color,
        spaceAfter=5
    )
    
    # Style pour les items
    item_style = ParagraphStyle(
        'RecoItem',
        parent=styles['Normal'],
        fontSize=9,
        leading=13,
        leftIndent=10,
        bulletIndent=5
    )
    
    # Construire les données
    data = [[Paragraph(title, title_style)]]
    
    for item in items:
        data.append([Paragraph(f"• {item}", item_style)])
    
    # Créer la table
    table = Table(data, colWidths=[16*cm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#F5F5F5")),
        ('BOX', (0, 0), (-1, -1), 1.5, color),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (0, 0), 10),
        ('BOTTOMPADDING', (0, 0), (0, 0), 8),
        ('TOPPADDING', (0, 1), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    
    return table


# =====================================================================
# PDF HEADER/FOOTER
# =====================================================================
class NumberedCanvas(canvas.Canvas):
    """Canvas personnalisé avec en-têtes et pieds de page"""
    
    def __init__(self, *args, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_decorations(self, num_pages):
        """Dessine l'en-tête et le pied de page"""
        page_num = self._pageNumber
        
        # En-tête (pas sur la première page)
        if page_num > 1:
            self.saveState()
            self.setFont('Helvetica', 8)
            self.setFillColor(GREY_MEDIUM)
            
            # Ligne de séparation
            self.setStrokeColor(PRIMARY_BLUE)
            self.setLineWidth(1)
            self.line(2*cm, A4[1] - 1.5*cm, A4[0] - 2*cm, A4[1] - 1.5*cm)
            
            # Texte en-tête
            self.drawString(2*cm, A4[1] - 1.3*cm, "ALGO-LIFE | UNILABS Group")
            self.drawRightString(A4[0] - 2*cm, A4[1] - 1.3*cm, f"Page {page_num} / {num_pages}")
            
            self.restoreState()
        
        # Pied de page
        self.saveState()
        self.setFont('Helvetica', 7)
        self.setFillColor(GREY_MEDIUM)
        
        # Ligne de séparation
        self.setStrokeColor(GREY_LIGHT)
        self.setLineWidth(0.5)
        self.line(2*cm, 1.5*cm, A4[0] - 2*cm, 1.5*cm)
        
        # Texte pied de page
        self.drawString(2*cm, 1*cm, "CONFIDENTIEL - Document médical")
        self.drawRightString(A4[0] - 2*cm, 1*cm, f"Dr Thibault SUTTER, PhD | contact@algo-life.com")
        
        self.restoreState()


# =====================================================================
# PDF GENERATOR
# =====================================================================
def generate_unilabs_report(
    patient_data: Dict[str, Any],
    biology_data: List[Dict[str, Any]],
    microbiome_data: Optional[Dict[str, Any]] = None,
    recommendations: Optional[Dict[str, List[str]]] = None,
    cross_analysis: Optional[List[Dict[str, Any]]] = None,
    follow_up: Optional[Dict[str, Any]] = None,
    bio_age_result: Optional[Dict[str, Any]] = None,
    output_path: str = "rapport_unilabs.pdf"
) -> str:
    """
    Génère un rapport PDF UNILABS/ALGO-LIFE avec design moderne
    
    Args:
        patient_data: Dict avec name, age, sex, birth_date, report_date, clinical_context
        biology_data: Liste de dicts avec name, value, unit, reference, status, category
        microbiome_data: Données microbiome (optionnel)
        recommendations: Dict avec sections (Nutrition, Micronutrition, etc.)
        cross_analysis: Analyses croisées (optionnel)
        follow_up: Plan de suivi (optionnel)
        bio_age_result: Résultat âge biologique (optionnel)
        output_path: Chemin de sortie
    
    Returns:
        Chemin du fichier généré
    """
    
    # Configuration document avec canvas personnalisé
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2.5*cm,
        bottomMargin=2*cm
    )
    
    # Styles
    styles = getSampleStyleSheet()
    
    style_title = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=32,
        textColor=PRIMARY_BLUE,
        spaceAfter=10,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    style_subtitle = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=14,
        textColor=GREY_MEDIUM,
        alignment=TA_CENTER,
        fontName='Helvetica',
        spaceAfter=20
    )
    
    style_section = ParagraphStyle(
        'SectionTitle',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=PRIMARY_BLUE,
        spaceBefore=20,
        spaceAfter=12,
        fontName='Helvetica-Bold',
        borderWidth=0,
        borderPadding=8,
        leftIndent=0
    )
    
    style_subsection = ParagraphStyle(
        'Subsection',
        parent=styles['Heading3'],
        fontSize=13,
        textColor=ACCENT_CYAN,
        spaceBefore=15,
        spaceAfter=8,
        fontName='Helvetica-Bold'
    )
    
    style_body = ParagraphStyle(
        'BodyText',
        parent=styles['BodyText'],
        fontSize=10,
        leading=14,
        alignment=TA_JUSTIFY
    )
    
    style_body_left = ParagraphStyle(
        'BodyTextLeft',
        parent=style_body,
        alignment=TA_LEFT
    )
    
    story = []
    # ─────────────────────────────────────────────────────────────────
    # NORMALISATION (évite biomarqueurs vides / 0.00 quand les clés diffèrent)
    # ─────────────────────────────────────────────────────────────────
    biology_data = normalize_biology_data(biology_data)

    
    # ═════════════════════════════════════════════════════════════════
    # PAGE DE GARDE
    # ═════════════════════════════════════════════════════════════════
    
    # Logo DNA
    logo = create_dna_logo(width=6*cm, height=6*cm)
    story.append(logo)
    story.append(Spacer(1, 1*cm))
    
    # Titres
    story.append(Paragraph("Rapport d'Analyses Biologiques", style_title))
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(
        '<font color="#0066CC"><b>UNILABS</b></font> <font color="#00BCD4">× ALGO-LIFE</font>',
        ParagraphStyle('BrandTitle', parent=style_title, fontSize=24, spaceAfter=5)
    ))
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph("Analyse complète et recommandations personnalisées", style_subtitle))
    story.append(Spacer(1, 2*cm))
    
    # Informations patient dans un cadre
    patient_name = _safe_str(patient_data.get("name", ""))
    patient_sex = _safe_str(patient_data.get("sex", ""))
    patient_birth = _safe_str(patient_data.get("birth_date", ""))
    report_date = _safe_str(patient_data.get("report_date", datetime.now().strftime("%d/%m/%Y")))
    
    patient_info_data = [
        [Paragraph("<b>PATIENT</b>", style_body), Paragraph(patient_name, style_body)],
        [Paragraph("<b>GENRE</b>", style_body), Paragraph(patient_sex, style_body)],
        [Paragraph("<b>DATE DE NAISSANCE</b>", style_body), Paragraph(patient_birth, style_body)],
        [Paragraph("<b>DATE DU RAPPORT</b>", style_body), Paragraph(report_date, style_body)],
    ]
    
    patient_table = Table(patient_info_data, colWidths=[6*cm, 10*cm])
    patient_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), BACKGROUND_LIGHT),
        ('BOX', (0, 0), (-1, -1), 1.5, PRIMARY_BLUE),
        ('LINEBELOW', (0, 0), (-1, 0), 0.5, GREY_LIGHT),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('LEFTPADDING', (0, 0), (-1, -1), 15),
        ('RIGHTPADDING', (0, 0), (-1, -1), 15),
    ]))
    
    story.append(patient_table)
    story.append(Spacer(1, 1.5*cm))
    
    # Contexte clinique
    clinical_context = _safe_str(patient_data.get("clinical_context", ""))
    if clinical_context:
        story.append(Paragraph("Contexte clinique", style_subsection))
        story.append(Paragraph(f"• {clinical_context}", style_body_left))
        story.append(Spacer(1, 1*cm))
    
    # Âge biologique
    if bio_age_result:
        bio_age = _safe_float(bio_age_result.get("biological_age"), 0)
        chrono_age = _safe_float(bio_age_result.get("chronological_age"), 0)
        delta = _safe_float(bio_age_result.get("delta"), 0)
        
        story.append(Paragraph("Âge Biologique", style_subsection))
        
        age_data = [
            [Paragraph("<b>Âge Biologique</b>", style_body), 
             Paragraph(f'<font size="18" color="#0066CC"><b>{bio_age:.1f} ans</b></font>', style_body)],
            [Paragraph("Chronologique :", style_body), Paragraph(f"{chrono_age:.1f} ans", style_body)],
            [Paragraph("Delta :", style_body), 
             Paragraph(f'<font color="{"#4CAF50" if delta < 0 else "#F44336"}">{delta:+.1f} ans ({delta/chrono_age*100:+.1f}%)</font>', style_body)],
        ]
        
        age_table = Table(age_data, colWidths=[7*cm, 9*cm])
        age_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#E3F2FD")),
            ('BOX', (0, 0), (-1, -1), 1, ACCENT_CYAN),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('LEFTPADDING', (0, 0), (-1, -1), 15),
        ]))
        
        story.append(age_table)
        story.append(Spacer(1, 0.5*cm))
        
        interpretation = bio_age_result.get("interpretation", "")
        if interpretation:
            story.append(Paragraph(interpretation, style_body_left))
    
    story.append(Spacer(1, 1*cm))
    story.append(Paragraph(
        "<b>CONFIDENTIEL - Usage médical uniquement</b>",
        ParagraphStyle('Conf', parent=style_body, fontSize=9, alignment=TA_CENTER, textColor=CRITICAL_RED)
    ))
    
    story.append(PageBreak())
    
    # ═════════════════════════════════════════════════════════════════
    # RÉSUMÉ GLOBAL DES BIOMARQUEURS
    # ═════════════════════════════════════════════════════════════════
    
    if biology_data and len(biology_data) > 0:
        story.append(Paragraph("Résumé global des biomarqueurs", style_section))
        story.append(Spacer(1, 0.5*cm))
        
        # Compter les statuts
        normal_count = len([b for b in biology_data if _safe_str(b.get("status", "")).lower() == "normal"])
        to_watch_count = len([b for b in biology_data if _safe_str(b.get("status", "")).lower() in ["à surveiller", "a surveiller", "inconnu", "unknown"]])
        abnormal_count = len([b for b in biology_data if _safe_str(b.get("status", "")).lower() in ["bas", "élevé", "elevé", "anormal"]])
        
        # Créer des cercles colorés avec les chiffres
        summary_drawing = Drawing(16*cm, 3*cm)
        
        # Cercle Normaux (vert)
        circle1 = Circle(2*cm, 1.5*cm, 1*cm)
        circle1.fillColor = NORMAL_GREEN
        circle1.strokeColor = NORMAL_GREEN
        circle1.strokeWidth = 3
        summary_drawing.add(circle1)
        
        label1_count = String(2*cm, 1.5*cm, str(normal_count))
        label1_count.fontName = 'Helvetica-Bold'
        label1_count.fontSize = 24
        label1_count.fillColor = WHITE
        label1_count.textAnchor = 'middle'
        summary_drawing.add(label1_count)
        
        label1_text = String(2*cm, 0.3*cm, "Normaux")
        label1_text.fontName = 'Helvetica'
        label1_text.fontSize = 11
        label1_text.fillColor = GREY_DARK
        label1_text.textAnchor = 'middle'
        summary_drawing.add(label1_text)
        
        # Cercle À surveiller (orange)
        circle2 = Circle(8*cm, 1.5*cm, 1*cm)
        circle2.fillColor = WARNING_ORANGE
        circle2.strokeColor = WARNING_ORANGE
        circle2.strokeWidth = 3
        summary_drawing.add(circle2)
        
        label2_count = String(8*cm, 1.5*cm, str(to_watch_count))
        label2_count.fontName = 'Helvetica-Bold'
        label2_count.fontSize = 24
        label2_count.fillColor = WHITE
        label2_count.textAnchor = 'middle'
        summary_drawing.add(label2_count)
        
        label2_text = String(8*cm, 0.3*cm, "À surveiller")
        label2_text.fontName = 'Helvetica'
        label2_text.fontSize = 11
        label2_text.fillColor = GREY_DARK
        label2_text.textAnchor = 'middle'
        summary_drawing.add(label2_text)
        
        # Cercle Anormaux (rouge)
        circle3 = Circle(14*cm, 1.5*cm, 1*cm)
        circle3.fillColor = CRITICAL_RED
        circle3.strokeColor = CRITICAL_RED
        circle3.strokeWidth = 3
        summary_drawing.add(circle3)
        
        label3_count = String(14*cm, 1.5*cm, str(abnormal_count))
        label3_count.fontName = 'Helvetica-Bold'
        label3_count.fontSize = 24
        label3_count.fillColor = WHITE
        label3_count.textAnchor = 'middle'
        summary_drawing.add(label3_count)
        
        label3_text = String(14*cm, 0.3*cm, "Anormaux")
        label3_text.fontName = 'Helvetica'
        label3_text.fontSize = 11
        label3_text.fillColor = GREY_DARK
        label3_text.textAnchor = 'middle'
        summary_drawing.add(label3_text)
        
        story.append(summary_drawing)
        story.append(Spacer(1, 1.5*cm))
    
    # ═════════════════════════════════════════════════════════════════
    # BIOMARQUEURS PAR CATÉGORIE
    # ═════════════════════════════════════════════════════════════════
    
    if biology_data and len(biology_data) > 0:
        story.append(PageBreak())
        story.append(Paragraph("Biomarqueurs", style_section))
        story.append(Spacer(1, 0.5*cm))
        
        # Grouper par catégorie
        categories = {}
        for biomarker in biology_data:
            category = _safe_str(biomarker.get("category", "Autres"))
            if not category:
                category = "Autres"
            
            if category not in categories:
                categories[category] = []
            
            categories[category].append(biomarker)
        
        # Afficher chaque catégorie
        for category, biomarkers in categories.items():
            story.append(Paragraph(category, style_subsection))
            story.append(Spacer(1, 0.3*cm))
            
            for i, biomarker in enumerate(biomarkers):
                # Créer la jauge
                gauge = create_biomarker_gauge(biomarker)
                story.append(gauge)
                story.append(Spacer(1, 1*cm))
                
                # Saut de page tous les 6 biomarqueurs (au lieu de 7)
                if (i + 1) % 6 == 0 and i < len(biomarkers) - 1:
                    story.append(PageBreak())
            
            story.append(Spacer(1, 0.5*cm))
        
        story.append(PageBreak())
    
    
    # ═════════════════════════════════════════════════════════════════
    # MICROBIOTE (TABLEAUX SOUS LA BIOLOGIE)
    # ═════════════════════════════════════════════════════════════════
    if microbiome_data:
        story.append(Paragraph("Microbiote", style_section))
        story.append(Spacer(1, 0.5*cm))

        di = microbiome_data.get("dysbiosis_index")
        diversity = _safe_str(microbiome_data.get("diversity", ""))
        div_metrics = microbiome_data.get("diversity_metrics") or {}

        summary_rows = [
            [Paragraph("<b>Indice de dysbiose (DI)</b>", style_body), Paragraph(_safe_str(di), style_body)],
            [Paragraph("<b>Diversité</b>", style_body), Paragraph(diversity or "Non disponible", style_body)],
        ]
        if isinstance(div_metrics, dict) and div_metrics:
            sh = div_metrics.get("shannon")
            si = div_metrics.get("simpson")
            if sh is not None:
                summary_rows.append([Paragraph("Shannon", style_body), Paragraph(_safe_str(sh), style_body)])
            if si is not None:
                summary_rows.append([Paragraph("Simpson", style_body), Paragraph(_safe_str(si), style_body)])

        micro_table = Table(summary_rows, colWidths=[7*cm, 9*cm])
        micro_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F3F7FF")),
            ('BOX', (0, 0), (-1, -1), 1.2, ACCENT_CYAN),
            ('INNERGRID', (0, 0), (-1, -1), 0.25, GREY_LIGHT),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(micro_table)
        story.append(Spacer(1, 0.8*cm))

        # Groupes (résumé)
        groups = microbiome_data.get("bacteria_groups") or []
        if isinstance(groups, list) and groups:
            story.append(Paragraph("Résumé par groupes", style_subsection))
            gdata = [[Paragraph("<b>Groupe</b>", style_body), Paragraph("<b>Résultat</b>", style_body)]]
            for g in groups[:18]:
                gname = _safe_str(g.get("group", g.get("category", "")))
                gres = _safe_str(g.get("result", ""))
                gdata.append([Paragraph(gname, style_body_left), Paragraph(gres, style_body_left)])
            gtab = Table(gdata, colWidths=[12*cm, 4*cm])
            gtab.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#E0F7FA")),
                ('BOX', (0, 0), (-1, -1), 1.0, ACCENT_CYAN),
                ('INNERGRID', (0, 0), (-1, -1), 0.25, GREY_LIGHT),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            story.append(gtab)
            story.append(Spacer(1, 0.8*cm))

        # Bactéries individuelles (top)
        indiv = microbiome_data.get("bacteria_individual") or []
        if isinstance(indiv, list) and indiv:
            story.append(Paragraph("Bactéries individuelles (extrait)", style_subsection))
            idata = [[Paragraph("<b>ID</b>", style_body), Paragraph("<b>Bactérie</b>", style_body), Paragraph("<b>Cat.</b>", style_body)]]
            for b in indiv[:30]:
                idata.append([
                    Paragraph(_safe_str(b.get("id", "")), style_body_left),
                    Paragraph(_safe_str(b.get("name", "")), style_body_left),
                    Paragraph(_safe_str(b.get("category", "")), style_body_left),
                ])
            itab = Table(idata, colWidths=[1.5*cm, 12.5*cm, 2*cm])
            itab.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#F5F5F5")),
                ('BOX', (0, 0), (-1, -1), 1.0, PRIMARY_BLUE),
                ('INNERGRID', (0, 0), (-1, -1), 0.25, GREY_LIGHT),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            story.append(itab)

        story.append(PageBreak())

# ═════════════════════════════════════════════════════════════════
    # RECOMMANDATIONS PERSONNALISÉES
    # ═════════════════════════════════════════════════════════════════
    
    if recommendations:
        story.append(Paragraph("■ RECOMMANDATIONS PERSONNALISÉES", style_section))
        story.append(Spacer(1, 0.5*cm))
        
        story.append(Paragraph(
            "Ces recommandations sont générées automatiquement par ALGO-LIFE sur la base de votre profil "
            "multimodal (biologie + microbiote). Elles visent à optimiser votre santé selon une approche de biologie fonctionnelle.",
            style_body
        ))
        story.append(Spacer(1, 0.3*cm))
        
        # Avertissement
        warning_style = ParagraphStyle(
            'Warning',
            parent=style_body,
            backColor=colors.HexColor("#FFF3E0"),
            borderColor=WARNING_ORANGE,
            borderWidth=1.5,
            borderPadding=12,
            fontSize=10
        )
        story.append(Paragraph(
            "<b>⚠️ Important:</b> Ces suggestions ne remplacent pas un avis médical. "
            "Consultez votre médecin avant toute nouvelle supplémentation.",
            warning_style
        ))
        story.append(Spacer(1, 0.8*cm))
        
        # Sections de recommandations avec codes couleur
        sections_config = [
            ("Prioritaires", "🔥", CRITICAL_RED),
            ("À surveiller", "⚠️", WARNING_ORANGE),
            ("Nutrition", "🥗", NORMAL_GREEN),
            ("Micronutrition", "💊", ACCENT_CYAN),
            ("Hygiène de vie", "🏃", PRIMARY_BLUE),
            ("Examens complémentaires", "🔬", DNA_PURPLE),
            ("Suivi", "📅", GREY_DARK)
        ]
        
        for section_name, icon, color in sections_config:
            items = recommendations.get(section_name, [])
            if not items:
                continue
            
            # Créer la boîte de recommandation
            reco_box = create_recommendation_box(f"{icon} {section_name}", items, color)
            story.append(reco_box)
            story.append(Spacer(1, 0.7*cm))
        
        story.append(PageBreak())
    
    # ═════════════════════════════════════════════════════════════════
    # PLAN DE SUIVI
    # ═════════════════════════════════════════════════════════════════
    
    if follow_up:
        story.append(Paragraph("Plan de suivi recommandé", style_section))
        story.append(Spacer(1, 0.5*cm))
        
        # Prochain contrôle
        next_date = _safe_str(follow_up.get("next_date", ""))
        if next_date:
            story.append(Paragraph(
                f'<font color="#0066CC">■</font> <b>Prochain contrôle</b>',
                style_subsection
            ))
            story.append(Paragraph(next_date, style_body_left))
            story.append(Spacer(1, 0.5*cm))
        
        # Biomarqueurs à recontrôler
        next_tests = follow_up.get("next_tests", [])
        if next_tests:
            story.append(Paragraph(
                f'<font color="#0066CC">■</font> <b>Biomarqueurs à recontrôler</b>',
                style_subsection
            ))
            
            for test in next_tests:
                story.append(Paragraph(f"• {test}", style_body_left))
            
            story.append(Spacer(1, 0.5*cm))
        
        # Objectifs mesurables
        objectives = _safe_str(follow_up.get("objectives", ""))
        if objectives:
            story.append(Paragraph(
                f'<font color="#4CAF50">■</font> <b>Objectifs mesurables</b>',
                style_subsection
            ))
            story.append(Paragraph(objectives, style_body_left))
            story.append(Spacer(1, 0.5*cm))
        
        # Observations
        observations = _safe_str(follow_up.get("observations", ""))
        if observations:
            story.append(Paragraph(
                f'<font color="#FF9800">■</font> <b>Observations</b>',
                style_subsection
            ))
            story.append(Paragraph(observations, style_body_left))
    
    # ═════════════════════════════════════════════════════════════════
    # FOOTER FINAL
    # ═════════════════════════════════════════════════════════════════
    
    story.append(PageBreak())
    story.append(Spacer(1, 3*cm))
    
    footer_style = ParagraphStyle(
        'FooterFinal',
        parent=styles['Normal'],
        fontSize=9,
        alignment=TA_CENTER,
        textColor=GREY_MEDIUM
    )
    
    story.append(Paragraph('<font color="#0066CC"><b>ALGO-LIFE © 2026</b></font>', footer_style))
    story.append(Paragraph("Powered by UNILABS Group", footer_style))
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph("Dr Thibault SUTTER, PhD", footer_style))
    story.append(Paragraph("Biologiste spécialisé en biologie fonctionnelle", footer_style))
    story.append(Paragraph("15+ années d'expertise en médecine fonctionnelle", footer_style))
    story.append(Spacer(1, 1*cm))
    story.append(Paragraph(
        "Ce rapport est généré automatiquement par analyse multimodale IA.<br/>"
        "Il ne remplace pas un avis médical personnalisé.",
        footer_style
    ))
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph("■ contact@algo-life.com | ■ www.algo-life.com", footer_style))
    story.append(Paragraph("■ Genève, Suisse", footer_style))
    
    # Build PDF avec le canvas personnalisé
    doc.build(story, canvasmaker=NumberedCanvas)
    
    return output_path


def generate_multimodal_report(
    patient_data: Dict[str, Any],
    biology_data: List[Dict[str, Any]],
    microbiome_data: Dict[str, Any],
    recommendations: Dict[str, List[str]],
    cross_analysis: List[Dict[str, Any]],
    follow_up: Dict[str, Any],
    bio_age_result: Optional[Dict[str, Any]] = None,
    output_path: str = "rapport_algo_life.pdf"
) -> str:
    """
    Fonction wrapper pour compatibilité avec l'ancien code
    Génère un rapport PDF multimodal avec templates visuels
    
    Args:
        patient_data: Informations patient
        biology_data: Liste des biomarqueurs
        microbiome_data: Données microbiome
        recommendations: Dict avec clés Prioritaires, Nutrition, Micronutrition, etc.
        cross_analysis: Analyses croisées
        follow_up: Plan de suivi
        bio_age_result: Résultat âge biologique (optionnel)
        output_path: Chemin de sortie
    
    Returns:
        Chemin du fichier généré
    """
    # Appeler la fonction principale avec les nouveaux paramètres
    return generate_unilabs_report(
        patient_data=patient_data,
        biology_data=biology_data,
        microbiome_data=microbiome_data,
        recommendations=recommendations,
        cross_analysis=cross_analysis,
        follow_up=follow_up,
        bio_age_result=bio_age_result,
        output_path=output_path
    )


# =====================================================================
# EXEMPLE D'UTILISATION
# =====================================================================
if __name__ == "__main__":
    # Données de test
    patient_data = {
        "name": "Isabelle FISCHER",
        "sex": "F",
        "birth_date": "20/10/1961",
        "report_date": "16/12/2025",
        "clinical_context": "Fatigue chronique"
    }
    
    biology_data = [
        {
            "name": "Hémoglobine",
            "value": 14.1,
            "unit": "g/dL",
            "reference": "12.0-16.0",
            "status": "Normal",
            "category": "Hematologie"
        },
        {
            "name": "Cholestérol total",
            "value": 2.47,
            "unit": "g/L",
            "reference": "1.8-1.9",
            "status": "Élevé",
            "category": "Bilan Lipidique"
        },
        {
            "name": "LDL Cholestérol",
            "value": 1.75,
            "unit": "g/L",
            "reference": "1.0-1.3",
            "status": "Élevé",
            "category": "Bilan Lipidique"
        },
        {
            "name": "Vitamine D (25-OH totale D2+D3)",
            "value": 43.7,
            "unit": "ng/mL",
            "reference": "30.0-60.0",
            "status": "Normal",
            "category": "Vitamines"
        },
    ]
    
    recommendations = {
        "À surveiller": [
            "Cholestérol total: Élevé (2.47 g/L)",
            "LDL Cholestérol: Élevé (1.75 g/L)"
        ],
        "Nutrition": [
            "Privilégiez un régime de type méditerranéen riche en polyphénols",
            "Consommez 3-4 portions de poissons gras par semaine",
            "Limitez les viandes rouges à 1-2 fois par semaine"
        ],
        "Micronutrition": [
            "Oméga-3 EPA/DHA (ratio 2:1) : 2000 mg/jour",
            "Berbérine : 500 mg, 2 fois par jour"
        ]
    }
    
    follow_up = {
        "next_date": "2026-02-16",
        "next_tests": ["Cholestérol total", "LDL Cholestérol", "Homocystéine"],
        "objectives": "Réduire le LDL Cholestérol à moins de 1.00 g/L"
    }
    
    bio_age_result = {
        "biological_age": 64.0,
        "chronological_age": 64.2,
        "delta": -0.2,
        "interpretation": "Bon - Âge en accord avec âge chronologique"
    }
    
    # Générer le PDF
    output = generate_unilabs_report(
        patient_data=patient_data,
        biology_data=biology_data,
        recommendations=recommendations,
        follow_up=follow_up,
        bio_age_result=bio_age_result,
        output_path="/tmp/test_rapport_unilabs.pdf"
    )
    
    print(f"✅ Rapport généré : {output}")
