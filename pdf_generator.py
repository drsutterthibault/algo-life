"""
ALGO-LIFE / UNILABS - Générateur PDF Premium v3.0
✅ Design premium haute qualité
✅ Logo ADN futuriste en haut de page
✅ Mise en page optimisée sans chevauchements
✅ Tableaux Microbiote détaillés
✅ Analyses Croisées (Biologie × Microbiote)
✅ Templates professionnels
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
from reportlab.graphics.shapes import Drawing, Rect, Circle, Line, String, Polygon, Path
from reportlab.graphics import renderPDF


# =====================================================================
# COLORS & DESIGN CONSTANTS - PREMIUM PALETTE
# =====================================================================
PRIMARY_BLUE = colors.HexColor("#0066CC")      # UNILABS Blue
ACCENT_CYAN = colors.HexColor("#00BCD4")       # AlgoLife Cyan
DNA_PURPLE = colors.HexColor("#6A1B9A")        # DNA Purple
DNA_PINK = colors.HexColor("#E91E63")          # DNA Accent
NORMAL_GREEN = colors.HexColor("#4CAF50")
WARNING_ORANGE = colors.HexColor("#FF9800")
CRITICAL_RED = colors.HexColor("#F44336")
GREY_DARK = colors.HexColor("#212121")
GREY_MEDIUM = colors.HexColor("#616161")
GREY_LIGHT = colors.HexColor("#E0E0E0")
WHITE = colors.white
BACKGROUND_LIGHT = colors.HexColor("#FAFAFA")
GRADIENT_BLUE_START = colors.HexColor("#1976D2")
GRADIENT_BLUE_END = colors.HexColor("#64B5F6")


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
        if isinstance(x, str):
            x = x.replace(",", ".")
        return float(x)
    except Exception:
        return default


def _parse_reference(ref_str: str) -> tuple[float, float]:
    """Parse une référence au format 'min-max' ou 'min — max'"""
    try:
        if not ref_str or ref_str == "Non spécifiées" or ref_str == "":
            return (0.0, 100.0)
        
        ref_str = str(ref_str).strip()
        ref_str = ref_str.replace(" — ", "-").replace("—", "-").replace(" - ", "-")
        parts = ref_str.split("-")
        
        if len(parts) == 2:
            min_val = _safe_float(parts[0].strip(), 0.0)
            max_val = _safe_float(parts[1].strip(), 100.0)
            
            if min_val >= max_val:
                return (0.0, 100.0)
            return (min_val, max_val)
        
        return (0.0, 100.0)
    except Exception:
        return (0.0, 100.0)


# =====================================================================
# NORMALISATION DES ENTREES
# =====================================================================
def normalize_biology_data(biology_data: Any) -> List[Dict[str, Any]]:
    """Normalise les biomarqueurs pour le générateur PDF"""
    if not biology_data:
        return []

    def _get(item: Dict[str, Any], *keys: str, default: Any = None) -> Any:
        for k in keys:
            if k in item:
                return item.get(k)
        return default

    # Dict mapping name -> fields
    if isinstance(biology_data, dict):
        for wrapper_key in ("biology_data", "biology", "biomarkers", "markers"):
            if wrapper_key in biology_data and isinstance(biology_data.get(wrapper_key), (list, dict)):
                return normalize_biology_data(biology_data.get(wrapper_key))

        out: List[Dict[str, Any]] = []
        for k, v in biology_data.items():
            if isinstance(v, dict):
                out.append({
                    "name": _safe_str(v.get("name", v.get("Biomarqueur", k))),
                    "value": v.get("value", v.get("Valeur", v.get("valeur", v.get("result", "")))),
                    "unit": _safe_str(v.get("unit", v.get("Unité", v.get("Unite", v.get("unite", v.get("units", "")))))),
                    "reference": _safe_str(v.get("reference", v.get("Référence", v.get("Reference", v.get("ref", v.get("norme", v.get("range", ""))))))),
                    "status": _safe_str(v.get("status", v.get("Statut", v.get("statut", "")))),
                    "category": _safe_str(v.get("category", v.get("Catégorie", v.get("Categorie", v.get("categorie", "Autres"))))) or "Autres",
                })
        return [b for b in out if b.get("name")]

    # List of dicts
    if isinstance(biology_data, list):
        out: List[Dict[str, Any]] = []
        for item in biology_data:
            if not isinstance(item, dict):
                continue

            # Cas dict encapsulé
            if len(item) == 1 and isinstance(next(iter(item.values())), dict) and not any(k in item for k in ("name","Biomarqueur","biomarker","marqueur")):
                k = next(iter(item.keys()))
                v = next(iter(item.values()))
                out.append({
                    "name": _safe_str(v.get("name", v.get("Biomarqueur", k))),
                    "value": v.get("value", v.get("Valeur", v.get("valeur", v.get("result", "")))),
                    "unit": _safe_str(v.get("unit", v.get("Unité", v.get("Unite", v.get("unite", v.get("units", "")))))),
                    "reference": _safe_str(v.get("reference", v.get("Référence", v.get("Reference", v.get("ref", v.get("norme", v.get("range", ""))))))),
                    "status": _safe_str(v.get("status", v.get("Statut", v.get("statut", "")))),
                    "category": _safe_str(v.get("category", v.get("Catégorie", v.get("Categorie", v.get("categorie", "Autres"))))) or "Autres",
                })
                continue

            name = (
                item.get("name")
                or item.get("biomarker") or item.get("marqueur")
                or item.get("Biomarqueur") or item.get("Marqueur")
                or item.get("parametre") or item.get("Paramètre") or item.get("Parametre")
                or item.get("parameter")
            )

            out.append({
                "name": _safe_str(name),
                "value": _get(item, "value", "valeur", "result", "Valeur", "Résultat", "Resultat", default=""),
                "unit": _safe_str(_get(item, "unit", "unite", "units", "Unité", "Unite", default="")),
                "reference": _safe_str(_get(item, "reference", "ref", "norme", "range", "Référence", "Reference", default="")),
                "status": _safe_str(_get(item, "status", "statut", "Statut", "flag", default="")),
                "category": _safe_str(_get(item, "category", "categorie", "Catégorie", "Categorie", default="Autres")) or "Autres",
            })

        return [b for b in out if b.get("name")]

    return []


# =====================================================================
# LOGO ADN FUTURISTE PREMIUM
# =====================================================================
def create_premium_dna_logo(width: float = 5*cm, height: float = 5*cm) -> Drawing:
    """
    Crée un logo ADN stylisé et futuriste de haute qualité
    Représente une double hélice avec effet 3D
    """
    d = Drawing(width, height)
    
    center_x = width / 2
    
    # ═══════════════════════════════════════════════════════════════
    # DOUBLE HÉLICE ADN avec courbes fluides
    # ═══════════════════════════════════════════════════════════════
    
    # Nombre de points pour l'hélice
    num_points = 24
    
    # Hélice gauche (Bleu gradient)
    for i in range(num_points):
        progress = i / num_points
        y = height * 0.05 + (progress * height * 0.9)
        
        # Oscillation sinusoïdale pour l'hélice
        import math
        x_offset = 0.6 * cm * math.sin(progress * 4 * math.pi)
        
        # Taille variable des cercles pour effet de profondeur
        circle_size = 0.10*cm + 0.05*cm * abs(math.sin(progress * 4 * math.pi))
        
        # Opacité variable
        opacity = 0.7 + 0.3 * abs(math.cos(progress * 4 * math.pi))
        
        circle = Circle(center_x + x_offset, y, circle_size)
        circle.fillColor = PRIMARY_BLUE
        circle.strokeColor = GRADIENT_BLUE_START
        circle.strokeWidth = 0.5
        circle.fillOpacity = opacity
        d.add(circle)
    
    # Hélice droite (Cyan/Rose accent)
    for i in range(num_points):
        progress = i / num_points
        y = height * 0.05 + (progress * height * 0.9)
        
        import math
        x_offset = -0.6 * cm * math.sin(progress * 4 * math.pi)
        circle_size = 0.10*cm + 0.05*cm * abs(math.sin(progress * 4 * math.pi))
        opacity = 0.7 + 0.3 * abs(math.cos(progress * 4 * math.pi))
        
        circle = Circle(center_x + x_offset, y, circle_size)
        
        # Alternance cyan/rose pour effet futuriste
        if i % 2 == 0:
            circle.fillColor = ACCENT_CYAN
            circle.strokeColor = colors.HexColor("#00ACC1")
        else:
            circle.fillColor = DNA_PINK
            circle.strokeColor = colors.HexColor("#D81B60")
        
        circle.strokeWidth = 0.5
        circle.fillOpacity = opacity
        d.add(circle)
    
    # Liaisons horizontales (ponts entre les hélices)
    for i in range(0, num_points, 3):
        progress = i / num_points
        y = height * 0.05 + (progress * height * 0.9)
        
        import math
        x1 = center_x + 0.6 * cm * math.sin(progress * 4 * math.pi)
        x2 = center_x - 0.6 * cm * math.sin(progress * 4 * math.pi)
        
        line = Line(x1, y, x2, y)
        line.strokeColor = DNA_PURPLE
        line.strokeWidth = 1
        line.strokeOpacity = 0.3
        d.add(line)
    
    # Cercle extérieur élégant
    outer_circle = Circle(center_x, height/2, height * 0.48)
    outer_circle.fillColor = None
    outer_circle.strokeColor = PRIMARY_BLUE
    outer_circle.strokeWidth = 2
    outer_circle.strokeOpacity = 0.3
    d.add(outer_circle)
    
    # Cercle intérieur pour profondeur
    inner_circle = Circle(center_x, height/2, height * 0.44)
    inner_circle.fillColor = None
    inner_circle.strokeColor = ACCENT_CYAN
    inner_circle.strokeWidth = 1
    inner_circle.strokeOpacity = 0.2
    d.add(inner_circle)
    
    return d


# =====================================================================
# JAUGE BIOMARQUEUR PREMIUM
# =====================================================================
def create_premium_biomarker_gauge(biomarker: Dict[str, Any], width: float = 17*cm, height: float = 4*cm) -> Drawing:
    """
    Crée une jauge visuelle premium pour un biomarqueur
    Design moderne avec gradients et ombres
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
    gauge_width = width * 0.58
    gauge_height = 16
    gauge_x = width * 0.25
    gauge_y = height * 0.40
    
    # Couleur du statut
    if status == "Normal" or status == "normal":
        status_color = NORMAL_GREEN
        status_bg = colors.HexColor("#E8F5E9")
    elif status.lower() in ["bas","faible","low"]:
        status_color = WARNING_ORANGE
        status_bg = colors.HexColor("#FFF3E0")
    elif status.lower() in ["élevé","elevé","haut","high"]:
        status_color = CRITICAL_RED
        status_bg = colors.HexColor("#FFEBEE")
    else:
        status_color = GREY_MEDIUM
        status_bg = GREY_LIGHT
    
    # ═══════════════════════════════════════════════════════════════
    # 1. Indicateur de statut (badge coloré à gauche)
    # ═══════════════════════════════════════════════════════════════
    dot_x = width * 0.018
    dot_y = height * 0.68
    
    # Badge avec bordure
    badge_bg = Circle(dot_x, dot_y, 9)
    badge_bg.fillColor = status_bg
    badge_bg.strokeColor = status_color
    badge_bg.strokeWidth = 2
    d.add(badge_bg)
    
    status_dot = Circle(dot_x, dot_y, 5)
    status_dot.fillColor = status_color
    status_dot.strokeColor = None
    d.add(status_dot)
    
    # ═══════════════════════════════════════════════════════════════
    # 2. Nom du biomarqueur (plus élégant)
    # ═══════════════════════════════════════════════════════════════
    name_str = String(dot_x + 18, dot_y - 4, name[:55])
    name_str.fontName = 'Helvetica-Bold'
    name_str.fontSize = 12
    name_str.fillColor = GREY_DARK
    d.add(name_str)
    
    # ═══════════════════════════════════════════════════════════════
    # 3. Barre de référence avec gradient subtil
    # ═══════════════════════════════════════════════════════════════
    
    # Ombre portée
    shadow_rect = Rect(gauge_x + 2, gauge_y - 2, gauge_width, gauge_height)
    shadow_rect.fillColor = colors.HexColor("#00000020")
    shadow_rect.strokeColor = None
    shadow_rect.rx = 4
    shadow_rect.ry = 4
    d.add(shadow_rect)
    
    # Fond de la jauge
    bg_rect = Rect(gauge_x, gauge_y, gauge_width, gauge_height)
    bg_rect.fillColor = BACKGROUND_LIGHT
    bg_rect.strokeColor = colors.HexColor("#BDBDBD")
    bg_rect.strokeWidth = 1
    bg_rect.rx = 4
    bg_rect.ry = 4
    d.add(bg_rect)
    
    # ═══════════════════════════════════════════════════════════════
    # 4. Zone normale (barre verte centrale)
    # ═══════════════════════════════════════════════════════════════
    normal_start_x = gauge_x + (gauge_width * 0.32)
    normal_width = gauge_width * 0.36
    
    normal_rect = Rect(normal_start_x, gauge_y + 2, normal_width, gauge_height - 4)
    normal_rect.fillColor = NORMAL_GREEN
    normal_rect.strokeColor = None
    normal_rect.fillOpacity = 0.25
    normal_rect.rx = 3
    normal_rect.ry = 3
    d.add(normal_rect)
    
    # ═══════════════════════════════════════════════════════════════
    # 5. Indicateur de position (design élégant)
    # ═══════════════════════════════════════════════════════════════
    
    if max_ref > min_ref and min_ref != max_ref:
        value_position_pct = (value - min_ref) / (max_ref - min_ref)
    else:
        value_position_pct = 0.5
    
    value_position_pct = max(0.0, min(1.0, value_position_pct))
    indicator_x = gauge_x + (gauge_width * value_position_pct)
    
    # Triangle moderne
    triangle_points = [
        indicator_x, gauge_y + gauge_height + 3,
        indicator_x - 6, gauge_y + gauge_height + 15,
        indicator_x + 6, gauge_y + gauge_height + 15
    ]
    
    triangle = Polygon(triangle_points)
    triangle.fillColor = status_color
    triangle.strokeColor = colors.HexColor("#FFFFFF")
    triangle.strokeWidth = 1.5
    d.add(triangle)
    
    # Ligne verticale élégante
    indicator_line = Line(indicator_x, gauge_y + 1, indicator_x, gauge_y + gauge_height - 1)
    indicator_line.strokeColor = status_color
    indicator_line.strokeWidth = 3
    indicator_line.strokeOpacity = 0.8
    d.add(indicator_line)
    
    # ═══════════════════════════════════════════════════════════════
    # 6. Labels des bornes
    # ═══════════════════════════════════════════════════════════════
    
    if min_ref != 0.0 or max_ref != 100.0:
        min_label = String(gauge_x - 8, gauge_y + gauge_height / 2 - 3, f"{min_ref:.1f}")
        min_label.fontName = 'Helvetica'
        min_label.fontSize = 9
        min_label.fillColor = GREY_MEDIUM
        min_label.textAnchor = 'end'
        d.add(min_label)
        
        max_label = String(gauge_x + gauge_width + 8, gauge_y + gauge_height / 2 - 3, f"{max_ref:.1f}")
        max_label.fontName = 'Helvetica'
        max_label.fontSize = 9
        max_label.fillColor = GREY_MEDIUM
        max_label.textAnchor = 'start'
        d.add(max_label)
    
    # ═══════════════════════════════════════════════════════════════
    # 7. Valeur du patient (affichage premium)
    # ═══════════════════════════════════════════════════════════════
    
    value_text = f"{value:.2f}" if value < 100 else f"{value:.1f}"
    if unit:
        value_text += f" {unit}"
    
    value_x = gauge_x + gauge_width + 1.2*cm
    value_label = String(value_x, gauge_y + gauge_height / 2 - 6, value_text)
    value_label.fontName = 'Helvetica-Bold'
    value_label.fontSize = 16
    value_label.fillColor = status_color
    value_label.textAnchor = 'start'
    d.add(value_label)
    
    # Label "Normes" discret
    if min_ref != 0.0 or max_ref != 100.0:
        norms_label = String(gauge_x, gauge_y - 10, f"Normes: {min_ref:.1f} — {max_ref:.1f}")
        norms_label.fontName = 'Helvetica'
        norms_label.fontSize = 8
        norms_label.fillColor = GREY_MEDIUM
        d.add(norms_label)
    
    return d


# =====================================================================
# BOX RECOMMANDATIONS PREMIUM
# =====================================================================
def create_premium_recommendation_box(title: str, items: List[str], color: colors.HexColor = PRIMARY_BLUE) -> Table:
    """
    Crée une boîte de recommandation premium avec design moderne
    """
    from reportlab.lib.styles import getSampleStyleSheet
    
    styles = getSampleStyleSheet()
    
    # Style pour le titre
    title_style = ParagraphStyle(
        'RecoTitle',
        parent=styles['Normal'],
        fontSize=13,
        fontName='Helvetica-Bold',
        textColor=WHITE,
        spaceAfter=0
    )
    
    # Style pour les items
    item_style = ParagraphStyle(
        'RecoItem',
        parent=styles['Normal'],
        fontSize=10,
        leading=15,
        leftIndent=12,
        bulletIndent=6
    )
    
    # Construire les données
    data = [[Paragraph(title, title_style)]]
    
    for item in items:
        data.append([Paragraph(f"● {item}", item_style)])
    
    # Créer la table
    table = Table(data, colWidths=[17*cm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), color),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#FAFAFA")),
        ('BOX', (0, 0), (-1, -1), 2, color),
        ('LEFTPADDING', (0, 0), (-1, -1), 15),
        ('RIGHTPADDING', (0, 0), (-1, -1), 15),
        ('TOPPADDING', (0, 0), (0, 0), 12),
        ('BOTTOMPADDING', (0, 0), (0, 0), 12),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    
    return table


# =====================================================================
# PDF HEADER/FOOTER
# =====================================================================
class NumberedCanvas(canvas.Canvas):
    """Canvas personnalisé avec en-têtes et pieds de page premium"""
    
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
        
        # En-tête premium (pas sur la première page)
        if page_num > 1:
            self.saveState()
            
            # Bande colorée subtile
            self.setFillColorRGB(0, 0.4, 0.8, alpha=0.08)
            self.rect(1.5*cm, A4[1] - 2*cm, A4[0] - 3*cm, 0.8*cm, fill=1, stroke=0)
            
            self.setFont('Helvetica-Bold', 9)
            self.setFillColor(PRIMARY_BLUE)
            self.drawString(2*cm, A4[1] - 1.5*cm, "ALGO-LIFE × UNILABS")
            
            self.setFont('Helvetica', 8)
            self.setFillColor(GREY_MEDIUM)
            self.drawRightString(A4[0] - 2*cm, A4[1] - 1.5*cm, f"Page {page_num} / {num_pages}")
            
            self.restoreState()
        
        # Pied de page premium
        self.saveState()
        
        # Ligne élégante
        self.setStrokeColor(GREY_LIGHT)
        self.setLineWidth(0.5)
        self.line(2*cm, 1.8*cm, A4[0] - 2*cm, 1.8*cm)
        
        self.setFont('Helvetica', 7)
        self.setFillColor(GREY_MEDIUM)
        self.drawString(2*cm, 1.2*cm, "CONFIDENTIEL - Document médical")
        self.drawRightString(A4[0] - 2*cm, 1.2*cm, "Dr Thibault SUTTER, PhD | contact@algo-life.com")
        
        self.restoreState()


# =====================================================================
# PDF GENERATOR PREMIUM
# =====================================================================
def generate_unilabs_report(
    patient_data: Dict[str, Any],
    biology_data: List[Dict[str, Any]],
    microbiome_data: Optional[Dict[str, Any]] = None,
    recommendations: Optional[Dict[str, List[str]]] = None,
    cross_analysis: Optional[List[Dict[str, Any]]] = None,
    follow_up: Optional[Dict[str, Any]] = None,
    bio_age_result: Optional[Dict[str, Any]] = None,
    output_path: str = "rapport_unilabs_premium.pdf"
) -> str:
    """
    Génère un rapport PDF UNILABS/ALGO-LIFE avec design PREMIUM
    """
    
    # Configuration document
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2.8*cm,
        bottomMargin=2.5*cm
    )
    
    # Styles
    styles = getSampleStyleSheet()
    
    style_title = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=34,
        textColor=PRIMARY_BLUE,
        spaceAfter=8,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    style_subtitle = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=15,
        textColor=GREY_MEDIUM,
        alignment=TA_CENTER,
        fontName='Helvetica',
        spaceAfter=15
    )
    
    style_section = ParagraphStyle(
        'SectionTitle',
        parent=styles['Heading2'],
        fontSize=18,
        textColor=PRIMARY_BLUE,
        spaceBefore=25,
        spaceAfter=15,
        fontName='Helvetica-Bold',
        borderWidth=0,
        borderPadding=0,
        leftIndent=0
    )
    
    style_subsection = ParagraphStyle(
        'Subsection',
        parent=styles['Heading3'],
        fontSize=14,
        textColor=ACCENT_CYAN,
        spaceBefore=18,
        spaceAfter=10,
        fontName='Helvetica-Bold'
    )
    
    style_body = ParagraphStyle(
        'BodyText',
        parent=styles['BodyText'],
        fontSize=10,
        leading=15,
        alignment=TA_JUSTIFY
    )
    
    style_body_left = ParagraphStyle(
        'BodyTextLeft',
        parent=style_body,
        alignment=TA_LEFT
    )
    
    story = []
    
    # ═════════════════════════════════════════════════════════════════
    # NORMALISATION
    # ═════════════════════════════════════════════════════════════════
    biology_data = normalize_biology_data(biology_data)
    if not biology_data:
        biology_data = []
    
    # ═════════════════════════════════════════════════════════════════
    # PAGE DE GARDE PREMIUM
    # ═════════════════════════════════════════════════════════════════
    
    # Logo DNA Premium en haut
    logo = create_premium_dna_logo(width=6*cm, height=6*cm)
    story.append(logo)
    story.append(Spacer(1, 0.8*cm))
    
    # Titres élégants
    story.append(Paragraph("Rapport d'Analyses Biologiques", style_title))
    story.append(Spacer(1, 0.4*cm))
    story.append(Paragraph(
        '<font color="#0066CC"><b>UNILABS</b></font> <font color="#00BCD4">× ALGO-LIFE</font>',
        ParagraphStyle('BrandTitle', parent=style_title, fontSize=26, spaceAfter=0)
    ))
    story.append(Spacer(1, 0.6*cm))
    story.append(Paragraph("Analyse multimodale & recommandations personnalisées", style_subtitle))
    story.append(Spacer(1, 2.2*cm))
    
    # Informations patient dans un cadre premium
    patient_name = _safe_str(patient_data.get("name", ""))
    patient_sex = _safe_str(patient_data.get("sex", ""))
    patient_birth = _safe_str(patient_data.get("birth_date", ""))
    report_date = _safe_str(patient_data.get("report_date", datetime.now().strftime("%d/%m/%Y")))
    
    patient_info_data = [
        [Paragraph("<b>PATIENT</b>", style_body), Paragraph(patient_name, style_body)],
        [Paragraph("<b>SEXE</b>", style_body), Paragraph(patient_sex, style_body)],
        [Paragraph("<b>DATE DE NAISSANCE</b>", style_body), Paragraph(patient_birth, style_body)],
        [Paragraph("<b>DATE DU RAPPORT</b>", style_body), Paragraph(report_date, style_body)],
    ]
    
    patient_table = Table(patient_info_data, colWidths=[6.5*cm, 10*cm])
    patient_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F5F9FF")),
        ('BOX', (0, 0), (-1, -1), 2, PRIMARY_BLUE),
        ('LINEBELOW', (0, 0), (-1, -1), 0.5, GREY_LIGHT),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 14),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 14),
        ('LEFTPADDING', (0, 0), (-1, -1), 18),
        ('RIGHTPADDING', (0, 0), (-1, -1), 18),
    ]))
    
    story.append(patient_table)
    story.append(Spacer(1, 1.8*cm))
    
    # Contexte clinique
    clinical_context = _safe_str(patient_data.get("clinical_context", ""))
    if clinical_context:
        story.append(Paragraph("Contexte clinique", style_subsection))
        story.append(Paragraph(f"● {clinical_context}", style_body_left))
        story.append(Spacer(1, 1.2*cm))
    
    # Âge biologique
    if bio_age_result:
        bio_age = _safe_float(bio_age_result.get("biological_age"), 0)
        chrono_age = _safe_float(bio_age_result.get("chronological_age"), 0)
        delta = _safe_float(bio_age_result.get("delta"), 0)
        
        story.append(Paragraph("Âge Biologique", style_subsection))
        
        age_data = [
            [Paragraph("<b>Âge Biologique</b>", style_body), 
             Paragraph(f'<font size="20" color="#0066CC"><b>{bio_age:.1f} ans</b></font>', style_body)],
            [Paragraph("Chronologique :", style_body), Paragraph(f"{chrono_age:.1f} ans", style_body)],
            [Paragraph("Delta :", style_body), 
             Paragraph(f'<font color="{"#4CAF50" if delta < 0 else "#F44336"}">{delta:+.1f} ans ({delta/chrono_age*100:+.1f}%)</font>', style_body)],
        ]
        
        age_table = Table(age_data, colWidths=[7.5*cm, 9*cm])
        age_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#E1F5FE")),
            ('BOX', (0, 0), (-1, -1), 1.5, ACCENT_CYAN),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('LEFTPADDING', (0, 0), (-1, -1), 18),
        ]))
        
        story.append(age_table)
        story.append(Spacer(1, 0.6*cm))
        
        interpretation = bio_age_result.get("interpretation", "")
        if interpretation:
            story.append(Paragraph(interpretation, style_body_left))
    
    story.append(Spacer(1, 1.5*cm))
    story.append(Paragraph(
        "<b>CONFIDENTIEL - Usage médical uniquement</b>",
        ParagraphStyle('Conf', parent=style_body, fontSize=9, alignment=TA_CENTER, textColor=CRITICAL_RED)
    ))
    
    story.append(PageBreak())
    
    # ═════════════════════════════════════════════════════════════════
    # RÉSUMÉ GLOBAL DES BIOMARQUEURS
    # ═════════════════════════════════════════════════════════════════
    
    if not biology_data:
        story.append(Paragraph("Résumé global des biomarqueurs", style_section))
        story.append(Paragraph("Aucun biomarqueur exploitable n'a été reçu.", style_body_left))
        story.append(Spacer(1, 1*cm))
    else:
        story.append(Paragraph("Résumé global des biomarqueurs", style_section))
        story.append(Spacer(1, 0.6*cm))
        
        # Compter les statuts
        normal_count = len([b for b in biology_data if _safe_str(b.get("status", "")).lower() == "normal"])
        to_watch_count = len([b for b in biology_data if _safe_str(b.get("status", "")).lower() in ["à surveiller","a surveiller","surveiller","borderline","limite","inconnu","unknown"]])
        abnormal_count = len([b for b in biology_data if _safe_str(b.get("status", "")).lower() in ["bas","faible","low","élevé","elevé","haut","high","anormal","abnormal"]])
        
        # Cercles colorés premium
        summary_drawing = Drawing(17*cm, 3.5*cm)
        
        # Cercle Normaux (vert)
        circle1_shadow = Circle(2.2*cm, 1.6*cm, 1.1*cm)
        circle1_shadow.fillColor = colors.HexColor("#00000015")
        circle1_shadow.strokeColor = None
        summary_drawing.add(circle1_shadow)
        
        circle1 = Circle(2*cm, 1.7*cm, 1.1*cm)
        circle1.fillColor = NORMAL_GREEN
        circle1.strokeColor = colors.HexColor("#FFFFFF")
        circle1.strokeWidth = 3
        summary_drawing.add(circle1)
        
        label1_count = String(2*cm, 1.7*cm, str(normal_count))
        label1_count.fontName = 'Helvetica-Bold'
        label1_count.fontSize = 28
        label1_count.fillColor = WHITE
        label1_count.textAnchor = 'middle'
        summary_drawing.add(label1_count)
        
        label1_text = String(2*cm, 0.3*cm, "Normaux")
        label1_text.fontName = 'Helvetica-Bold'
        label1_text.fontSize = 12
        label1_text.fillColor = GREY_DARK
        label1_text.textAnchor = 'middle'
        summary_drawing.add(label1_text)
        
        # Cercle À surveiller (orange)
        circle2_shadow = Circle(8.7*cm, 1.6*cm, 1.1*cm)
        circle2_shadow.fillColor = colors.HexColor("#00000015")
        circle2_shadow.strokeColor = None
        summary_drawing.add(circle2_shadow)
        
        circle2 = Circle(8.5*cm, 1.7*cm, 1.1*cm)
        circle2.fillColor = WARNING_ORANGE
        circle2.strokeColor = colors.HexColor("#FFFFFF")
        circle2.strokeWidth = 3
        summary_drawing.add(circle2)
        
        label2_count = String(8.5*cm, 1.7*cm, str(to_watch_count))
        label2_count.fontName = 'Helvetica-Bold'
        label2_count.fontSize = 28
        label2_count.fillColor = WHITE
        label2_count.textAnchor = 'middle'
        summary_drawing.add(label2_count)
        
        label2_text = String(8.5*cm, 0.3*cm, "À surveiller")
        label2_text.fontName = 'Helvetica-Bold'
        label2_text.fontSize = 12
        label2_text.fillColor = GREY_DARK
        label2_text.textAnchor = 'middle'
        summary_drawing.add(label2_text)
        
        # Cercle Anormaux (rouge)
        circle3_shadow = Circle(15.2*cm, 1.6*cm, 1.1*cm)
        circle3_shadow.fillColor = colors.HexColor("#00000015")
        circle3_shadow.strokeColor = None
        summary_drawing.add(circle3_shadow)
        
        circle3 = Circle(15*cm, 1.7*cm, 1.1*cm)
        circle3.fillColor = CRITICAL_RED
        circle3.strokeColor = colors.HexColor("#FFFFFF")
        circle3.strokeWidth = 3
        summary_drawing.add(circle3)
        
        label3_count = String(15*cm, 1.7*cm, str(abnormal_count))
        label3_count.fontName = 'Helvetica-Bold'
        label3_count.fontSize = 28
        label3_count.fillColor = WHITE
        label3_count.textAnchor = 'middle'
        summary_drawing.add(label3_count)
        
        label3_text = String(15*cm, 0.3*cm, "Anormaux")
        label3_text.fontName = 'Helvetica-Bold'
        label3_text.fontSize = 12
        label3_text.fillColor = GREY_DARK
        label3_text.textAnchor = 'middle'
        summary_drawing.add(label3_text)
        
        story.append(summary_drawing)
        story.append(Spacer(1, 2*cm))
    
    # ═════════════════════════════════════════════════════════════════
    # BIOMARQUEURS PAR CATÉGORIE (AVEC JAUGES PREMIUM)
    # ═════════════════════════════════════════════════════════════════
    
    if biology_data and len(biology_data) > 0:
        story.append(PageBreak())
        story.append(Paragraph("Biomarqueurs", style_section))
        story.append(Spacer(1, 0.8*cm))
        
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
            story.append(Spacer(1, 0.5*cm))
            
            for i, biomarker in enumerate(biomarkers):
                # Créer la jauge premium
                gauge = create_premium_biomarker_gauge(biomarker)
                story.append(gauge)
                story.append(Spacer(1, 1.2*cm))
                
                # Saut de page tous les 5 biomarqueurs (éviter chevauchement)
                if (i + 1) % 5 == 0 and i < len(biomarkers) - 1:
                    story.append(PageBreak())
                    story.append(Paragraph(f"{category} (suite)", style_subsection))
                    story.append(Spacer(1, 0.5*cm))
            
            story.append(Spacer(1, 0.8*cm))
        
        story.append(PageBreak())
    
    # ═════════════════════════════════════════════════════════════════
    # MICROBIOTE (TABLEAUX DÉTAILLÉS APRÈS BIOLOGIE)
    # ═════════════════════════════════════════════════════════════════
    
    if microbiome_data:
        story.append(Paragraph("Microbiote", style_section))
        story.append(Spacer(1, 0.8*cm))
        
        # ─────────────────────────────────────────────────────────────
        # 1. Tableau résumé principal
        # ─────────────────────────────────────────────────────────────
        
        di = microbiome_data.get("dysbiosis_index")
        diversity = _safe_str(microbiome_data.get("diversity", ""))
        div_metrics = microbiome_data.get("diversity_metrics") or {}
        
        summary_rows = [
            [Paragraph("<b>Indice de dysbiose (DI)</b>", style_body), 
             Paragraph(f'<font size="13" color="#0066CC"><b>{_safe_str(di)}</b></font>', style_body)],
            [Paragraph("<b>Diversité</b>", style_body), 
             Paragraph(diversity or "Non disponible", style_body)],
        ]
        
        if isinstance(div_metrics, dict) and div_metrics:
            sh = div_metrics.get("shannon")
            si = div_metrics.get("simpson")
            if sh is not None:
                summary_rows.append([
                    Paragraph("Shannon (H')", style_body), 
                    Paragraph(f"{_safe_str(sh)}", style_body)
                ])
            if si is not None:
                summary_rows.append([
                    Paragraph("Simpson (D)", style_body), 
                    Paragraph(f"{_safe_str(si)}", style_body)
                ])
        
        micro_summary_table = Table(summary_rows, colWidths=[8*cm, 9*cm])
        micro_summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F0F8FF")),
            ('BOX', (0, 0), (-1, -1), 2, ACCENT_CYAN),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#B3E5FC")),
            ('LEFTPADDING', (0, 0), (-1, -1), 15),
            ('RIGHTPADDING', (0, 0), (-1, -1), 15),
            ('TOPPADDING', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ]))
        story.append(micro_summary_table)
        story.append(Spacer(1, 1.2*cm))
        
        # ─────────────────────────────────────────────────────────────
        # 2. Tableau détaillé des groupes bactériens
        # ─────────────────────────────────────────────────────────────
        
        groups = microbiome_data.get("bacteria_groups") or []
        if isinstance(groups, list) and groups:
            story.append(Paragraph("Groupes bactériens détaillés", style_subsection))
            story.append(Spacer(1, 0.5*cm))
            
            # Header du tableau
            gdata = [[
                Paragraph("<b>Groupe bactérien</b>", style_body), 
                Paragraph("<b>Résultat</b>", style_body),
                Paragraph("<b>Statut</b>", style_body)
            ]]
            
            for g in groups[:25]:  # Limiter à 25 groupes pour éviter débordement
                gname = _safe_str(g.get("group", g.get("category", "")))
                gres = _safe_str(g.get("result", ""))
                gstatus = _safe_str(g.get("status", "Normal"))
                
                # Colorer le statut
                if gstatus.lower() in ["bas", "faible", "low"]:
                    status_html = f'<font color="#FF9800">● {gstatus}</font>'
                elif gstatus.lower() in ["élevé", "elevé", "haut", "high"]:
                    status_html = f'<font color="#F44336">● {gstatus}</font>'
                else:
                    status_html = f'<font color="#4CAF50">● {gstatus}</font>'
                
                gdata.append([
                    Paragraph(gname, style_body_left), 
                    Paragraph(gres, style_body_left),
                    Paragraph(status_html, style_body_left)
                ])
            
            gtab = Table(gdata, colWidths=[9*cm, 5*cm, 3*cm])
            gtab.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), ACCENT_CYAN),
                ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#FAFAFA")),
                ('BOX', (0, 0), (-1, -1), 1.5, ACCENT_CYAN),
                ('INNERGRID', (0, 0), (-1, -1), 0.5, GREY_LIGHT),
                ('LEFTPADDING', (0, 0), (-1, -1), 10),
                ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                ('TOPPADDING', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, colors.HexColor("#F5F5F5")]),
            ]))
            story.append(gtab)
            story.append(Spacer(1, 1*cm))
        
        # ─────────────────────────────────────────────────────────────
        # 3. Recommandations microbiote (si présentes)
        # ─────────────────────────────────────────────────────────────
        
        micro_reco = microbiome_data.get("recommendations", [])
        if isinstance(micro_reco, list) and micro_reco:
            story.append(Paragraph("Recommandations microbiote", style_subsection))
            story.append(Spacer(1, 0.4*cm))
            
            reco_box = create_premium_recommendation_box(
                "Interventions suggérées",
                micro_reco[:8],  # Limiter à 8 recommandations
                DNA_PURPLE
            )
            story.append(reco_box)
            story.append(Spacer(1, 1*cm))
        
        story.append(PageBreak())
    
    # ═════════════════════════════════════════════════════════════════
    # ANALYSES CROISÉES (BIOLOGIE × MICROBIOTE) - NOUVELLE SECTION
    # ═════════════════════════════════════════════════════════════════
    
    if cross_analysis or (biology_data and microbiome_data):
        story.append(Paragraph("Analyses Croisées", style_section))
        story.append(Spacer(1, 0.6*cm))
        
        story.append(Paragraph(
            "Corrélations identifiées entre biomarqueurs biologiques et microbiote",
            ParagraphStyle('Intro', parent=style_body, fontSize=11, textColor=GREY_DARK, spaceAfter=15)
        ))
        
        # Si cross_analysis est fourni, l'utiliser
        if cross_analysis and isinstance(cross_analysis, list):
            for i, analysis in enumerate(cross_analysis, 1):
                title = _safe_str(analysis.get("title", f"Analyse {i}"))
                findings = analysis.get("findings", [])
                implications = _safe_str(analysis.get("implications", ""))
                
                # Boîte d'analyse croisée
                cross_data = [[Paragraph(f"<b>{title}</b>", style_subsection)]]
                
                if isinstance(findings, list):
                    for finding in findings:
                        cross_data.append([Paragraph(f"• {_safe_str(finding)}", style_body_left)])
                
                if implications:
                    cross_data.append([Paragraph(f"<b>Implications:</b> {implications}", 
                                                ParagraphStyle('Implication', parent=style_body_left, 
                                                             textColor=DNA_PURPLE, fontSize=10))])
                
                cross_table = Table(cross_data, colWidths=[17*cm])
                cross_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#F3E5F5")),
                    ('BACKGROUND', (0, 1), (-1, -1), WHITE),
                    ('BOX', (0, 0), (-1, -1), 1.5, DNA_PURPLE),
                    ('LEFTPADDING', (0, 0), (-1, -1), 15),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 15),
                    ('TOPPADDING', (0, 0), (-1, -1), 12),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ]))
                story.append(cross_table)
                story.append(Spacer(1, 0.8*cm))
        
        # Sinon, générer des exemples par défaut si données disponibles
        else:
            # Exemple 1: Inflammation + Dysbiose
            if biology_data and microbiome_data:
                crp_markers = [b for b in biology_data if "crp" in _safe_str(b.get("name", "")).lower() or "protéine c" in _safe_str(b.get("name", "")).lower()]
                di = microbiome_data.get("dysbiosis_index")
                
                if crp_markers or di:
                    cross_data = [[Paragraph("<b>Inflammation systémique × Dysbiose</b>", style_subsection)]]
                    
                    if crp_markers:
                        crp_value = _safe_float(crp_markers[0].get("value"), 0)
                        cross_data.append([Paragraph(
                            f"• CRP: {crp_value} {_safe_str(crp_markers[0].get('unit', ''))} - Marqueur inflammatoire",
                            style_body_left
                        )])
                    
                    if di:
                        cross_data.append([Paragraph(
                            f"• Indice de dysbiose: {_safe_str(di)} - Déséquilibre du microbiote",
                            style_body_left
                        )])
                    
                    cross_data.append([Paragraph(
                        "<b>Implications:</b> La dysbiose peut aggraver l'inflammation systémique via la production "
                        "d'endotoxines (LPS) et la perméabilité intestinale accrue. Une restauration de l'équilibre "
                        "microbien pourrait contribuer à réduire l'inflammation.",
                        ParagraphStyle('Implication', parent=style_body_left, textColor=DNA_PURPLE, fontSize=10)
                    )])
                    
                    cross_table = Table(cross_data, colWidths=[17*cm])
                    cross_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#F3E5F5")),
                        ('BACKGROUND', (0, 1), (-1, -1), WHITE),
                        ('BOX', (0, 0), (-1, -1), 1.5, DNA_PURPLE),
                        ('LEFTPADDING', (0, 0), (-1, -1), 15),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 15),
                        ('TOPPADDING', (0, 0), (-1, -1), 12),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ]))
                    story.append(cross_table)
                    story.append(Spacer(1, 0.8*cm))
            
            # Exemple 2: Fer bas + Flore appauvrie
            if biology_data and microbiome_data:
                fer_markers = [b for b in biology_data if "fer" in _safe_str(b.get("name", "")).lower()]
                diversity = _safe_str(microbiome_data.get("diversity", ""))
                
                if fer_markers or diversity:
                    cross_data = [[Paragraph("<b>Statut martial × Diversité microbienne</b>", style_subsection)]]
                    
                    if fer_markers:
                        fer_value = _safe_float(fer_markers[0].get("value"), 0)
                        cross_data.append([Paragraph(
                            f"• Fer sérique: {fer_value} {_safe_str(fer_markers[0].get('unit', ''))} - Statut martial",
                            style_body_left
                        )])
                    
                    if diversity:
                        cross_data.append([Paragraph(
                            f"• Diversité microbienne: {diversity} - Richesse du microbiote",
                            style_body_left
                        )])
                    
                    cross_data.append([Paragraph(
                        "<b>Implications:</b> Une diversité microbienne réduite peut altérer l'absorption et le métabolisme "
                        "du fer. Certaines bactéries probiotiques (Lactobacillus, Bifidobacterium) peuvent améliorer "
                        "la biodisponibilité du fer non-héminique.",
                        ParagraphStyle('Implication', parent=style_body_left, textColor=DNA_PURPLE, fontSize=10)
                    )])
                    
                    cross_table = Table(cross_data, colWidths=[17*cm])
                    cross_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#F3E5F5")),
                        ('BACKGROUND', (0, 1), (-1, -1), WHITE),
                        ('BOX', (0, 0), (-1, -1), 1.5, DNA_PURPLE),
                        ('LEFTPADDING', (0, 0), (-1, -1), 15),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 15),
                        ('TOPPADDING', (0, 0), (-1, -1), 12),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ]))
                    story.append(cross_table)
                    story.append(Spacer(1, 0.8*cm))
            
            # Exemple 3: LDL oxydé + Déséquilibre Gram–
            if biology_data and microbiome_data:
                ldl_markers = [b for b in biology_data if "ldl" in _safe_str(b.get("name", "")).lower()]
                groups = microbiome_data.get("bacteria_groups") or []
                gram_neg = [g for g in groups if "gram" in _safe_str(g.get("group", "")).lower() and "neg" in _safe_str(g.get("group", "")).lower()]
                
                if ldl_markers or gram_neg:
                    cross_data = [[Paragraph("<b>Profil lipidique × Bactéries Gram–</b>", style_subsection)]]
                    
                    if ldl_markers:
                        ldl_value = _safe_float(ldl_markers[0].get("value"), 0)
                        cross_data.append([Paragraph(
                            f"• LDL Cholestérol: {ldl_value} {_safe_str(ldl_markers[0].get('unit', ''))} - Lipides athérogènes",
                            style_body_left
                        )])
                    
                    if gram_neg:
                        cross_data.append([Paragraph(
                            f"• Bactéries Gram négatif: {_safe_str(gram_neg[0].get('result', ''))} - Production de LPS",
                            style_body_left
                        )])
                    
                    cross_data.append([Paragraph(
                        "<b>Implications:</b> Les lipopolysaccharides (LPS) des bactéries Gram– peuvent favoriser "
                        "l'oxydation du LDL et l'inflammation vasculaire. Un déséquilibre en faveur des Gram– augmente "
                        "le risque cardiovasculaire via l'endotoxémie métabolique.",
                        ParagraphStyle('Implication', parent=style_body_left, textColor=DNA_PURPLE, fontSize=10)
                    )])
                    
                    cross_table = Table(cross_data, colWidths=[17*cm])
                    cross_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#F3E5F5")),
                        ('BACKGROUND', (0, 1), (-1, -1), WHITE),
                        ('BOX', (0, 0), (-1, -1), 1.5, DNA_PURPLE),
                        ('LEFTPADDING', (0, 0), (-1, -1), 15),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 15),
                        ('TOPPADDING', (0, 0), (-1, -1), 12),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ]))
                    story.append(cross_table)
                    story.append(Spacer(1, 0.8*cm))
        
        story.append(PageBreak())
    
    # ═════════════════════════════════════════════════════════════════
    # RECOMMANDATIONS
    # ═════════════════════════════════════════════════════════════════
    
    if recommendations:
        story.append(Paragraph("Recommandations personnalisées", style_section))
        story.append(Spacer(1, 0.8*cm))
        
        # Ordre de priorité des sections
        priority_order = [
            ("À surveiller", CRITICAL_RED),
            ("Micronutrition", DNA_PURPLE),
            ("Nutrition", NORMAL_GREEN),
            ("Supplémentation", ACCENT_CYAN),
            ("Mode de vie", PRIMARY_BLUE),
        ]
        
        # Afficher d'abord les sections prioritaires
        for section_name, color in priority_order:
            if section_name in recommendations:
                items = recommendations[section_name]
                if isinstance(items, list) and items:
                    box = create_premium_recommendation_box(section_name, items, color)
                    story.append(box)
                    story.append(Spacer(1, 0.8*cm))
        
        # Puis les autres sections
        for section, items in recommendations.items():
            if section not in [name for name, _ in priority_order]:
                if isinstance(items, list) and items:
                    box = create_premium_recommendation_box(section, items, PRIMARY_BLUE)
                    story.append(box)
                    story.append(Spacer(1, 0.8*cm))
        
        story.append(PageBreak())
    
    # ═════════════════════════════════════════════════════════════════
    # PLAN DE SUIVI
    # ═════════════════════════════════════════════════════════════════
    
    if follow_up:
        story.append(Paragraph("Plan de suivi", style_section))
        story.append(Spacer(1, 0.8*cm))
        
        # Date du prochain bilan
        next_date = _safe_str(follow_up.get("next_date", ""))
        if next_date:
            story.append(Paragraph(
                f'<font color="#0066CC">■</font> <b>Prochain bilan</b>',
                style_subsection
            ))
            story.append(Paragraph(f"Date recommandée : {next_date}", style_body_left))
            story.append(Spacer(1, 0.6*cm))
        
        # Analyses à recontrôler
        next_tests = follow_up.get("next_tests", [])
        if isinstance(next_tests, list) and next_tests:
            story.append(Paragraph(
                f'<font color="#00BCD4">■</font> <b>Analyses à recontrôler</b>',
                style_subsection
            ))
            for test in next_tests:
                story.append(Paragraph(f"• {_safe_str(test)}", style_body_left))
            story.append(Spacer(1, 0.6*cm))
        
        # Objectifs mesurables
        objectives = _safe_str(follow_up.get("objectives", ""))
        if objectives:
            story.append(Paragraph(
                f'<font color="#4CAF50">■</font> <b>Objectifs mesurables</b>',
                style_subsection
            ))
            story.append(Paragraph(objectives, style_body_left))
            story.append(Spacer(1, 0.6*cm))
        
        # Observations
        observations = _safe_str(follow_up.get("observations", ""))
        if observations:
            story.append(Paragraph(
                f'<font color="#FF9800">■</font> <b>Observations</b>',
                style_subsection
            ))
            story.append(Paragraph(observations, style_body_left))
    
    # ═════════════════════════════════════════════════════════════════
    # FOOTER FINAL PREMIUM
    # ═════════════════════════════════════════════════════════════════
    
    story.append(PageBreak())
    story.append(Spacer(1, 3.5*cm))
    
    footer_style = ParagraphStyle(
        'FooterFinal',
        parent=styles['Normal'],
        fontSize=9,
        alignment=TA_CENTER,
        textColor=GREY_MEDIUM,
        leading=14
    )
    
    story.append(Paragraph('<font color="#0066CC"><b>ALGO-LIFE © 2026</b></font>', footer_style))
    story.append(Paragraph("Powered by UNILABS Group", footer_style))
    story.append(Spacer(1, 0.6*cm))
    story.append(Paragraph("Dr Thibault SUTTER, PhD", footer_style))
    story.append(Paragraph("Biologiste spécialisé en biologie fonctionnelle", footer_style))
    story.append(Paragraph("15+ années d'expertise en médecine fonctionnelle", footer_style))
    story.append(Spacer(1, 1.2*cm))
    story.append(Paragraph(
        "Ce rapport est généré automatiquement par analyse multimodale IA.<br/>"
        "Il ne remplace pas un avis médical personnalisé.",
        footer_style
    ))
    story.append(Spacer(1, 0.7*cm))
    story.append(Paragraph("■ contact@algo-life.com | ■ www.algo-life.com", footer_style))
    story.append(Paragraph("■ Genève, Suisse", footer_style))
    
    # Build PDF avec le canvas premium
    doc.build(story, canvasmaker=NumberedCanvas)
    
    return output_path


def generate_multimodal_report(*args, **kwargs) -> str:
    """Point d'entrée unique (compatibilité maximale)"""
    
    # Appel avec payload dict unique
    if len(args) == 1 and isinstance(args[0], dict) and not kwargs:
        payload = args[0]

        patient_data = payload.get("patient_data") or payload.get("patient") or {}
        biology_data = payload.get("biology_data") or payload.get("biology") or []
        microbiome_data = payload.get("microbiome_data") or payload.get("microbiome") or payload.get("microbiote") or None
        recommendations = payload.get("recommendations") or payload.get("reco") or None
        cross_analysis = payload.get("cross_analysis") or payload.get("cross") or None
        follow_up = payload.get("follow_up") or payload.get("suivi") or None
        bio_age_result = payload.get("bio_age_result") or payload.get("bio_age") or None
        output_path = payload.get("output_path") or payload.get("output") or "rapport_algo_life_premium.pdf"

        return generate_unilabs_report(
            patient_data=patient_data,
            biology_data=biology_data,
            microbiome_data=microbiome_data,
            recommendations=recommendations,
            cross_analysis=cross_analysis,
            follow_up=follow_up,
            bio_age_result=bio_age_result,
            output_path=output_path,
        )

    # Appel "ancien style" (kwargs)
    return generate_unilabs_report(
        patient_data=kwargs.get("patient_data", args[0] if len(args) > 0 else {}),
        biology_data=kwargs.get("biology_data", args[1] if len(args) > 1 else []),
        microbiome_data=kwargs.get("microbiome_data", args[2] if len(args) > 2 else None),
        recommendations=kwargs.get("recommendations", args[3] if len(args) > 3 else None),
        cross_analysis=kwargs.get("cross_analysis", args[4] if len(args) > 4 else None),
        follow_up=kwargs.get("follow_up", args[5] if len(args) > 5 else None),
        bio_age_result=kwargs.get("bio_age_result", kwargs.get("bio_age", None)),
        output_path=kwargs.get("output_path", "rapport_algo_life_premium.pdf"),
    )


# =====================================================================
# EXEMPLE D'UTILISATION
# =====================================================================
if __name__ == "__main__":
    # Données de test complètes
    patient_data = {
        "name": "Isabelle FISCHER",
        "sex": "F",
        "birth_date": "20/10/1961",
        "report_date": "04/02/2026",
        "clinical_context": "Fatigue chronique, troubles digestifs"
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
            "name": "Ferritine",
            "value": 28,
            "unit": "ng/mL",
            "reference": "30-200",
            "status": "Bas",
            "category": "Metabolisme Fer"
        },
        {
            "name": "CRP (Protéine C-réactive)",
            "value": 8.2,
            "unit": "mg/L",
            "reference": "0-5",
            "status": "Élevé",
            "category": "Inflammation"
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
    
    microbiome_data = {
        "dysbiosis_index": 3.2,
        "diversity": "Réduite",
        "diversity_metrics": {
            "shannon": 2.1,
            "simpson": 0.65
        },
        "bacteria_groups": [
            {"group": "Firmicutes", "result": "45%", "status": "Normal"},
            {"group": "Bacteroidetes", "result": "30%", "status": "Bas"},
            {"group": "Actinobacteria", "result": "15%", "status": "Normal"},
            {"group": "Proteobacteria (Gram–)", "result": "8%", "status": "Élevé"},
            {"group": "Lactobacillus spp.", "result": "2.5%", "status": "Bas"},
            {"group": "Bifidobacterium spp.", "result": "3.1%", "status": "Bas"},
        ],
        "recommendations": [
            "Probiotiques multi-souches (10 milliards UFC/jour)",
            "Prébiotiques: inuline, FOS",
            "Fibres alimentaires: 30g/jour minimum",
            "Polyphénols: baies, thé vert"
        ]
    }
    
    recommendations = {
        "À surveiller": [
            "Ferritine basse: Risque d'anémie ferriprive",
            "CRP élevée: Inflammation systémique",
            "Cholestérol total et LDL élevés"
        ],
        "Nutrition": [
            "Régime méditerranéen riche en polyphénols",
            "Poissons gras 3-4×/semaine (oméga-3)",
            "Viandes rouges limitées à 1-2×/semaine",
            "Légumes verts à chaque repas (fer non-héminique)"
        ],
        "Micronutrition": [
            "Fer bisglycinate: 30 mg/jour (à jeun)",
            "Oméga-3 EPA/DHA (2:1): 2000 mg/jour",
            "Berbérine: 500 mg, 2×/jour",
            "Curcumine biodisponible: 1000 mg/jour"
        ]
    }
    
    cross_analysis = [
        {
            "title": "Inflammation chronique × Dysbiose",
            "findings": [
                "CRP élevée à 8.2 mg/L (inflammation systémique)",
                "Indice de dysbiose à 3.2 (déséquilibre modéré)",
                "Proteobactéries Gram– élevées (8%)"
            ],
            "implications": "Les endotoxines (LPS) des bactéries Gram– peuvent franchir "
                          "la barrière intestinale et stimuler la production de cytokines pro-inflammatoires, "
                          "aggravant l'inflammation systémique mesurée par la CRP."
        },
        {
            "title": "Statut martial déficient × Diversité microbienne réduite",
            "findings": [
                "Ferritine basse à 28 ng/mL",
                "Diversité Shannon réduite (2.1)",
                "Lactobacillus et Bifidobacterium diminués"
            ],
            "implications": "Une diversité microbienne réduite altère l'absorption du fer. "
                          "Les probiotiques (Lactobacillus, Bifidobacterium) peuvent améliorer "
                          "la biodisponibilité du fer non-héminique via acidification du milieu intestinal."
        }
    ]
    
    follow_up = {
        "next_date": "04/05/2026",
        "next_tests": [
            "Ferritine", 
            "CRP", 
            "Cholestérol total et LDL", 
            "Hémoglobine",
            "Analyse microbiote (si possible)"
        ],
        "objectives": "Normaliser la ferritine (>50 ng/mL), "
                     "réduire la CRP (<5 mg/L), "
                     "LDL <1.00 g/L",
        "observations": "Évaluer la tolérance digestive des suppléments de fer. "
                       "Surveiller les symptômes de fatigue."
    }
    
    bio_age_result = {
        "biological_age": 64.0,
        "chronological_age": 64.2,
        "delta": -0.2,
        "interpretation": "Bon - Âge biologique en accord avec âge chronologique"
    }
    
    # Générer le PDF PREMIUM
    output = generate_unilabs_report(
        patient_data=patient_data,
        biology_data=biology_data,
        microbiome_data=microbiome_data,
        recommendations=recommendations,
        cross_analysis=cross_analysis,
        follow_up=follow_up,
        bio_age_result=bio_age_result,
        output_path="/tmp/rapport_unilabs_premium.pdf"
    )
    
    print(f"✅ Rapport PREMIUM généré : {output}")
