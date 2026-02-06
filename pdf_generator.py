#!/usr/bin/env python3
"""
Générateur de rapports biologiques UNILABS - Design moderne v2
Améliorations: Logo ALGO-LIFE, microbiologie détaillée, tableaux de recommandations
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image, KeepTogether, Frame, PageTemplate
)
from reportlab.pdfgen import canvas
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Circle, Polygon
from reportlab.graphics import renderPDF
from datetime import datetime
from PIL import Image as PILImage
import io

# ============================================================================
# PALETTE DE COULEURS MODERNE
# ============================================================================
class ModernColors:
    # Couleurs principales - tons médicaux sophistiqués
    primary = colors.HexColor('#1a5490')      # Bleu médical profond
    secondary = colors.HexColor('#2d7ab9')    # Bleu clair
    accent = colors.HexColor('#00a8cc')       # Cyan moderne
    
    # États des biomarqueurs
    normal = colors.HexColor('#10b981')       # Vert émeraude
    warning = colors.HexColor('#f59e0b')      # Orange ambré
    critical = colors.HexColor('#ef4444')     # Rouge corail
    
    # Nuances de gris
    dark = colors.HexColor('#1f2937')         # Gris anthracite
    medium = colors.HexColor('#6b7280')       # Gris moyen
    light = colors.HexColor('#f3f4f6')        # Gris très clair
    background = colors.HexColor('#fafafa')   # Fond blanc cassé
    
    # Accents
    microbiome = colors.HexColor('#8b5cf6')   # Violet
    metabolic = colors.HexColor('#ec4899')    # Rose
    
    white = colors.white

# ============================================================================
# STYLES MODERNES
# ============================================================================
def get_modern_styles():
    """Définit les styles de paragraphe modernes"""
    styles = getSampleStyleSheet()
    
    # Titre principal
    styles.add(ParagraphStyle(
        name='ModernTitle',
        parent=styles['Title'],
        fontSize=28,
        textColor=ModernColors.primary,
        spaceAfter=8,
        spaceBefore=0,
        fontName='Helvetica-Bold',
        alignment=TA_LEFT,
        leading=32
    ))
    
    # Sous-titre
    styles.add(ParagraphStyle(
        name='ModernSubtitle',
        parent=styles['Normal'],
        fontSize=14,
        textColor=ModernColors.medium,
        spaceAfter=20,
        fontName='Helvetica',
        alignment=TA_LEFT
    ))
    
    # En-tête de section
    styles.add(ParagraphStyle(
        name='SectionHeader',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=ModernColors.primary,
        spaceAfter=12,
        spaceBefore=20,
        fontName='Helvetica-Bold',
        borderPadding=10,
        leftIndent=0
    ))
    
    # Sous-section
    styles.add(ParagraphStyle(
        name='SubsectionHeader',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=ModernColors.dark,
        spaceAfter=8,
        spaceBefore=12,
        fontName='Helvetica-Bold'
    ))
    
    # Corps de texte
    styles.add(ParagraphStyle(
        name='ModernBody',
        parent=styles['Normal'],
        fontSize=10,
        textColor=ModernColors.dark,
        alignment=TA_JUSTIFY,
        spaceAfter=6,
        leading=14,
        fontName='Helvetica'
    ))
    
    # Texte petit
    styles.add(ParagraphStyle(
        name='SmallText',
        parent=styles['Normal'],
        fontSize=8,
        textColor=ModernColors.medium,
        fontName='Helvetica'
    ))
    
    # Badge
    styles.add(ParagraphStyle(
        name='Badge',
        parent=styles['Normal'],
        fontSize=11,
        textColor=ModernColors.white,
        fontName='Helvetica-Bold',
        alignment=TA_CENTER
    ))
    
    return styles

# ============================================================================
# PIED DE PAGE MODERNE
# ============================================================================
def modern_footer(canvas, doc):
    """Pied de page épuré et professionnel"""
    canvas.saveState()
    
    # Ligne de séparation fine
    canvas.setStrokeColor(ModernColors.light)
    canvas.setLineWidth(0.5)
    canvas.line(2*cm, 2*cm, A4[0]-2*cm, 2*cm)
    
    # Informations de pied de page
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(ModernColors.medium)
    
    # Gauche - Confidentiel
    canvas.drawString(2*cm, 1.5*cm, 
                     "CONFIDENTIEL - Document médical")
    
    # Centre - Contact
    canvas.drawCentredString(A4[0]/2, 1.5*cm,
                            "Dr Thibault SUTTER, PhD")
    
    # Droite - Numéro de page
    canvas.drawRightString(A4[0]-2*cm, 1.5*cm,
                          f"Page {canvas.getPageNumber()} / 15")
    
    canvas.restoreState()

# ============================================================================
# CRÉATION DE LA PAGE DE GARDE
# ============================================================================
def create_cover_page(patient_data, logo_path=None):
    """Crée une page de garde moderne et élégante"""
    elements = []
    styles = get_modern_styles()
    
    # Espacement initial
    elements.append(Spacer(1, 1.5*cm))
    
    # Logo ADN
    if logo_path:
        try:
            # Ajouter le logo directement
            logo = Image(logo_path, width=4*cm, height=4*cm, kind='proportional')
            elements.append(logo)
        except Exception as e:
            print(f"Erreur lors du chargement du logo: {e}")
    
    elements.append(Spacer(1, 1*cm))
    
    # Titre principal
    title = Paragraph("Rapport d'Analyses Biologiques", styles['ModernTitle'])
    elements.append(title)
    
    # Sous-titre
    subtitle = Paragraph(
        "UNILABS - Analyse multimodale & recommandations personnalisées",
        styles['ModernSubtitle']
    )
    elements.append(subtitle)
    
    elements.append(Spacer(1, 2*cm))
    
    # Carte d'informations patient (design moderne)
    patient_info_data = [
        ['PATIENT', patient_data.get('nom', 'N/A')],
        ['SEXE', patient_data.get('sexe', 'N/A')],
        ['DATE DE NAISSANCE', patient_data.get('date_naissance', 'N/A')],
        ['DATE DU RAPPORT', datetime.now().strftime('%d/%m/%Y')]
    ]
    
    patient_table = Table(patient_info_data, colWidths=[5*cm, 10*cm])
    patient_table.setStyle(TableStyle([
        # Style général
        ('FONT', (0, 0), (-1, -1), 'Helvetica', 11),
        ('FONT', (0, 0), (0, -1), 'Helvetica-Bold', 10),
        ('TEXTCOLOR', (0, 0), (0, -1), ModernColors.medium),
        ('TEXTCOLOR', (1, 0), (1, -1), ModernColors.dark),
        
        # Bordures et fond
        ('BACKGROUND', (0, 0), (-1, -1), ModernColors.light),
        ('GRID', (0, 0), (-1, -1), 0, ModernColors.white),
        ('LINEABOVE', (0, 0), (-1, 0), 2, ModernColors.primary),
        
        # Espacement
        ('LEFTPADDING', (0, 0), (-1, -1), 15),
        ('RIGHTPADDING', (0, 0), (-1, -1), 15),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        
        # Alignement
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
    ]))
    
    elements.append(patient_table)
    elements.append(Spacer(1, 3*cm))
    
    # Badge de confidentialité moderne
    confid_text = Paragraph(
        "CONFIDENTIEL - Usage médical uniquement",
        styles['Badge']
    )
    
    confid_table = Table([[confid_text]], colWidths=[12*cm])
    confid_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), ModernColors.primary),
        ('TEXTCOLOR', (0, 0), (-1, -1), ModernColors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('ROUNDEDCORNERS', [8, 8, 8, 8]),
    ]))
    
    elements.append(confid_table)
    
    return elements

# ============================================================================
# RÉSUMÉ GLOBAL AVEC VISUALISATION MODERNE
# ============================================================================
def create_summary_section(biomarker_summary):
    """Crée le résumé global avec badges modernes inspirés du rapport"""
    elements = []
    styles = get_modern_styles()
    
    elements.append(PageBreak())
    elements.append(Spacer(1, 1*cm))
    
    # Titre de section
    title = Paragraph("Résumé global des biomarqueurs", styles['SectionHeader'])
    elements.append(title)
    elements.append(Spacer(1, 1*cm))
    
    # Récupération des valeurs
    normal_count = biomarker_summary.get('normaux', 0)
    warning_count = biomarker_summary.get('a_surveiller', 0)
    abnormal_count = biomarker_summary.get('anormaux', 0)
    
    # Création d'un drawing personnalisé pour les badges
    d = Drawing(500, 200)
    
    # Paramètres
    card_width = 140
    card_height = 160
    spacing = 20
    start_x = 10
    
    # Fonction helper pour créer une carte arrondie
    def create_card(x, y, width, height, color, count, label, bar_color):
        # Rectangle avec coins arrondis (simulé avec overlay)
        d.add(Rect(x, y, width, height, 
                  fillColor=colors.white,
                  strokeColor=color,
                  strokeWidth=2))
        
        # Barre latérale colorée
        d.add(Rect(x, y, 6, height,
                  fillColor=bar_color,
                  strokeColor=None))
        
        # Chiffre
        d.add(String(x + width/2, y + height - 60,
                    str(count),
                    fontSize=42,
                    fillColor=color,
                    textAnchor='middle',
                    fontName='Helvetica-Bold'))
        
        # Label
        d.add(String(x + width/2, y + 30,
                    label,
                    fontSize=11,
                    fillColor=ModernColors.medium,
                    textAnchor='middle',
                    fontName='Helvetica'))
    
    # Carte 1 - Normaux (vert)
    create_card(start_x, 20, card_width, card_height,
               ModernColors.normal, normal_count, 'Normaux',
               ModernColors.normal)
    
    # Carte 2 - À surveiller (orange)
    create_card(start_x + card_width + spacing, 20, card_width, card_height,
               ModernColors.warning, warning_count, 'À surveiller',
               ModernColors.warning)
    
    # Carte 3 - Anormaux (rouge)
    create_card(start_x + 2*(card_width + spacing), 20, card_width, card_height,
               ModernColors.critical, abnormal_count, 'Anormaux',
               ModernColors.critical)
    
    elements.append(d)
    elements.append(Spacer(1, 1.5*cm))
    
    return elements

# ============================================================================
# VISUALISATION DES BIOMARQUEURS
# ============================================================================
def create_biomarker_visualization(name, value, unit, min_val, max_val, status):
    """Crée une visualisation moderne pour un biomarqueur"""
    
    # Déterminer la couleur selon le statut
    if status == 'normal':
        color = ModernColors.normal
    elif status == 'warning':
        color = ModernColors.warning
    else:
        color = ModernColors.critical
    
    # Calcul de la position
    if min_val is not None and max_val is not None:
        range_span = max_val - min_val
        if range_span > 0:
            position = (value - min_val) / range_span
            position = max(0, min(1, position))  # Clamp entre 0 et 1
        else:
            position = 0.5
    else:
        position = 0.5
    
    # Création du graphique
    d = Drawing(400, 60)
    
    # Barre de fond (range normal)
    bar_y = 25
    bar_height = 8
    bar_width = 300
    bar_x = 50
    
    # Fond gris clair
    d.add(Rect(bar_x, bar_y, bar_width, bar_height,
              fillColor=ModernColors.light,
              strokeColor=None))
    
    # Zone normale (si définie)
    if min_val is not None and max_val is not None:
        d.add(Rect(bar_x, bar_y, bar_width, bar_height,
                  fillColor=colors.HexColor('#e8f5e9'),
                  strokeColor=None))
    
    # Marqueur de valeur
    marker_x = bar_x + (bar_width * position)
    d.add(Circle(marker_x, bar_y + bar_height/2, 6,
                fillColor=color,
                strokeColor=ModernColors.white,
                strokeWidth=2))
    
    # Textes
    d.add(String(bar_x - 5, bar_y + bar_height/2, 
                str(min_val) if min_val is not None else '',
                fontSize=8, fillColor=ModernColors.medium,
                textAnchor='end'))
    
    d.add(String(bar_x + bar_width + 5, bar_y + bar_height/2,
                str(max_val) if max_val is not None else '',
                fontSize=8, fillColor=ModernColors.medium,
                textAnchor='start'))
    
    # Nom du biomarqueur
    d.add(String(5, 45, name,
                fontSize=11, fillColor=ModernColors.dark,
                fontName='Helvetica-Bold', textAnchor='start'))
    
    # Valeur
    value_text = f"{value} {unit}"
    d.add(String(5, 5, value_text,
                fontSize=10, fillColor=color,
                fontName='Helvetica-Bold', textAnchor='start'))
    
    # Normes
    if min_val is not None and max_val is not None:
        norm_text = f"Normes: {min_val} — {max_val}"
        d.add(String(200, 5, norm_text,
                    fontSize=8, fillColor=ModernColors.medium,
                    textAnchor='start'))
    
    return d

# ============================================================================
# SECTION BIOMARQUEURS
# ============================================================================
def create_biomarkers_section(biomarkers):
    """Crée la section des biomarqueurs avec visualisations"""
    elements = []
    styles = get_modern_styles()
    
    elements.append(PageBreak())
    elements.append(Spacer(1, 1*cm))
    
    # Titre
    title = Paragraph("Biomarqueurs", styles['SectionHeader'])
    elements.append(title)
    elements.append(Spacer(1, 0.5*cm))
    
    # Grouper par catégorie
    categories = {}
    for bm in biomarkers:
        cat = bm.get('categorie', 'Autres')
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(bm)
    
    # Afficher par catégorie
    for cat_name, cat_biomarkers in categories.items():
        # Sous-titre de catégorie
        cat_title = Paragraph(cat_name, styles['SubsectionHeader'])
        elements.append(cat_title)
        elements.append(Spacer(1, 0.3*cm))
        
        # Chaque biomarqueur
        for bm in cat_biomarkers:
            viz = create_biomarker_visualization(
                name=bm['nom'],
                value=bm['valeur'],
                unit=bm['unite'],
                min_val=bm.get('min'),
                max_val=bm.get('max'),
                status=bm.get('statut', 'normal')
            )
            elements.append(viz)
            elements.append(Spacer(1, 0.5*cm))
    
    return elements

# ============================================================================
# SECTION MICROBIOTE AMÉLIORÉE
# ============================================================================
def create_microbiome_section(microbiome_data):
    """Crée la section microbiote avec toutes les souches"""
    elements = []
    styles = get_modern_styles()
    
    elements.append(PageBreak())
    elements.append(Spacer(1, 1*cm))
    
    # Titre
    title = Paragraph("Microbiote", styles['SectionHeader'])
    elements.append(title)
    elements.append(Spacer(1, 0.5*cm))
    
    # Indices globaux
    di_value = microbiome_data.get('indice_dysbiose', 'N/A')
    diversity = microbiome_data.get('diversite', 'N/A')
    
    indices_data = [
        ['Indice de dysbiose (DI)', str(di_value)],
        ['Diversité', diversity]
    ]
    
    indices_table = Table(indices_data, colWidths=[8*cm, 7*cm])
    indices_table.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), 'Helvetica', 10),
        ('FONT', (0, 0), (0, -1), 'Helvetica-Bold', 10),
        ('TEXTCOLOR', (0, 0), (-1, -1), ModernColors.dark),
        ('BACKGROUND', (0, 0), (-1, -1), ModernColors.light),
        ('GRID', (0, 0), (-1, -1), 0.5, ModernColors.white),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    
    elements.append(indices_table)
    elements.append(Spacer(1, 0.8*cm))
    
    # Groupes bactériens - Séparation normaux/anormaux
    if 'groupes_bacteriens' in microbiome_data:
        groups = microbiome_data['groupes_bacteriens']
        
        # Séparer les normaux et anormaux
        normal_groups = [g for g in groups if 'Normal' in g.get('statut', '')]
        abnormal_groups = [g for g in groups if 'Normal' not in g.get('statut', '')]
        
        # Section NORMAUX
        if normal_groups:
            normal_title = Paragraph("Souches normales", styles['SubsectionHeader'])
            elements.append(normal_title)
            elements.append(Spacer(1, 0.3*cm))
            
            # Tableau des groupes normaux
            normal_data = [['Groupe bactérien', 'Résultat', 'Statut']]
            
            for group in normal_groups:
                nom = group['nom']
                resultat = group['resultat']
                statut = '● Normal'
                
                normal_data.append([nom, resultat, statut])
            
            normal_table = Table(normal_data, colWidths=[9*cm, 4*cm, 2.5*cm])
            normal_table.setStyle(TableStyle([
                # En-tête
                ('BACKGROUND', (0, 0), (-1, 0), ModernColors.normal),
                ('TEXTCOLOR', (0, 0), (-1, 0), ModernColors.white),
                ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 9),
                
                # Corps
                ('FONT', (0, 1), (-1, -1), 'Helvetica', 8),
                ('TEXTCOLOR', (0, 1), (-1, -1), ModernColors.dark),
                ('BACKGROUND', (0, 1), (-1, -1), ModernColors.white),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [ModernColors.white, colors.HexColor('#f0fdf4')]),
                
                # Bordures
                ('GRID', (0, 0), (-1, -1), 0.5, ModernColors.medium),
                
                # Espacement
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                
                # Alignement
                ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            
            elements.append(normal_table)
            elements.append(Spacer(1, 0.8*cm))
        
        # Section ANORMAUX
        if abnormal_groups:
            abnormal_title = Paragraph("Souches à surveiller / anormales", styles['SubsectionHeader'])
            elements.append(abnormal_title)
            elements.append(Spacer(1, 0.3*cm))
            
            # Tableau des groupes anormaux
            abnormal_data = [['Groupe bactérien', 'Résultat', 'Statut']]
            
            for group in abnormal_groups:
                nom = group['nom']
                resultat = group['resultat']
                statut = group['statut']
                
                abnormal_data.append([nom, resultat, statut])
            
            abnormal_table = Table(abnormal_data, colWidths=[9*cm, 4*cm, 2.5*cm])
            abnormal_table.setStyle(TableStyle([
                # En-tête
                ('BACKGROUND', (0, 0), (-1, 0), ModernColors.critical),
                ('TEXTCOLOR', (0, 0), (-1, 0), ModernColors.white),
                ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 9),
                
                # Corps
                ('FONT', (0, 1), (-1, -1), 'Helvetica', 8),
                ('TEXTCOLOR', (0, 1), (-1, -1), ModernColors.dark),
                ('BACKGROUND', (0, 1), (-1, -1), ModernColors.white),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [ModernColors.white, colors.HexColor('#fef2f2')]),
                
                # Bordures
                ('GRID', (0, 0), (-1, -1), 0.5, ModernColors.medium),
                
                # Espacement
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                
                # Alignement
                ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            
            elements.append(abnormal_table)
    
    return elements

# ============================================================================
# RECOMMANDATIONS AVEC TABLEAUX JOLIS
# ============================================================================
def create_recommendations_section(recommendations):
    """Crée la section des recommandations avec tableaux élégants"""
    elements = []
    styles = get_modern_styles()
    
    elements.append(PageBreak())
    elements.append(Spacer(1, 1*cm))
    
    # Titre
    title = Paragraph("Recommandations personnalisées", styles['SectionHeader'])
    elements.append(title)
    elements.append(Spacer(1, 0.5*cm))
    
    # Biomarqueurs à surveiller - Tableau d'alerte
    if 'a_surveiller' in recommendations and recommendations['a_surveiller']:
        surveiller_title = Paragraph("À surveiller", styles['SubsectionHeader'])
        elements.append(surveiller_title)
        elements.append(Spacer(1, 0.3*cm))
        
        # Créer tableau
        alert_data = [['⚠️  Biomarqueur']]
        for item in recommendations['a_surveiller']:
            alert_data.append([item])
        
        alert_table = Table(alert_data, colWidths=[15*cm])
        alert_table.setStyle(TableStyle([
            # En-tête
            ('BACKGROUND', (0, 0), (-1, 0), ModernColors.warning),
            ('TEXTCOLOR', (0, 0), (-1, 0), ModernColors.white),
            ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 11),
            
            # Corps
            ('FONT', (0, 1), (-1, -1), 'Helvetica', 9),
            ('TEXTCOLOR', (0, 1), (-1, -1), ModernColors.dark),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#fffbeb'), ModernColors.white]),
            
            # Bordures
            ('GRID', (0, 0), (-1, -1), 0.5, ModernColors.warning),
            ('BOX', (0, 0), (-1, -1), 1.5, ModernColors.warning),
            
            # Espacement
            ('LEFTPADDING', (0, 0), (-1, -1), 12),
            ('RIGHTPADDING', (0, 0), (-1, -1), 12),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            
            # Alignement
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        elements.append(alert_table)
        elements.append(Spacer(1, 0.8*cm))
    
    # Catégories de recommandations avec icônes
    categories_config = {
        'micronutrition': {
            'title': '💊  Micronutrition',
            'key': 'micronutrition',
            'color': ModernColors.accent
        },
        'nutrition': {
            'title': '🥗  Nutrition',
            'key': 'nutrition',
            'color': ModernColors.normal
        },
        'hygiene_de_vie': {
            'title': '🏃  Hygiène de vie',
            'key': 'hygiene_de_vie',
            'color': ModernColors.microbiome
        }
    }
    
    for cat_config in categories_config.values():
        cat_key = cat_config['key']
        if cat_key in recommendations and recommendations[cat_key]:
            cat_title = Paragraph(cat_config['title'], styles['SubsectionHeader'])
            elements.append(cat_title)
            elements.append(Spacer(1, 0.3*cm))
            
            # Créer tableau de recommandations
            reco_data = [['Recommandation']]
            for item in recommendations[cat_key]:
                reco_data.append([item])
            
            reco_table = Table(reco_data, colWidths=[15*cm])
            reco_table.setStyle(TableStyle([
                # En-tête
                ('BACKGROUND', (0, 0), (-1, 0), cat_config['color']),
                ('TEXTCOLOR', (0, 0), (-1, 0), ModernColors.white),
                ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 10),
                
                # Corps
                ('FONT', (0, 1), (-1, -1), 'Helvetica', 9),
                ('TEXTCOLOR', (0, 1), (-1, -1), ModernColors.dark),
                ('BACKGROUND', (0, 1), (-1, -1), ModernColors.white),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [ModernColors.white, ModernColors.light]),
                
                # Bordures
                ('GRID', (0, 0), (-1, -1), 0.5, ModernColors.medium),
                ('BOX', (0, 0), (-1, -1), 1, cat_config['color']),
                
                # Espacement
                ('LEFTPADDING', (0, 0), (-1, -1), 12),
                ('RIGHTPADDING', (0, 0), (-1, -1), 12),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                
                # Alignement
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            
            elements.append(reco_table)
            elements.append(Spacer(1, 0.6*cm))
    
    return elements

# ============================================================================
# SUIVI ET EXAMENS COMPLÉMENTAIRES
# ============================================================================
def create_followup_section(followup_data):
    """Crée la section suivi"""
    elements = []
    styles = get_modern_styles()
    
    elements.append(PageBreak())
    elements.append(Spacer(1, 1*cm))
    
    # Examens complémentaires
    title = Paragraph("Examens complémentaires", styles['SectionHeader'])
    elements.append(title)
    elements.append(Spacer(1, 0.3*cm))
    
    if 'examens' in followup_data:
        for exam in followup_data['examens']:
            bullet = Paragraph(f"• {exam}", styles['ModernBody'])
            elements.append(bullet)
    
    elements.append(Spacer(1, 0.8*cm))
    
    # Suivi
    suivi_title = Paragraph("Suivi", styles['SectionHeader'])
    elements.append(suivi_title)
    elements.append(Spacer(1, 0.3*cm))
    
    if 'suivi' in followup_data:
        for item in followup_data['suivi']:
            bullet = Paragraph(f"• {item}", styles['ModernBody'])
            elements.append(bullet)
    
    return elements

# ============================================================================
# PAGE FINALE SIMPLIFIÉE
# ============================================================================
def create_final_page(logo_path=None):
    """Crée la page finale avec informations simplifiées"""
    elements = []
    styles = get_modern_styles()
    
    elements.append(PageBreak())
    elements.append(Spacer(1, 3*cm))
    
    # Logo ADN si disponible
    if logo_path:
        try:
            logo = Image(logo_path, width=4*cm, height=4*cm, kind='proportional')
            elements.append(logo)
        except Exception as e:
            print(f"Erreur lors du chargement du logo: {e}")
    
    elements.append(Spacer(1, 1*cm))
    
    # Informations simplifiées
    info_text = """
    <b>UNILABS © 2026</b><br/>
    Powered by Unilabs Group<br/><br/>
    <b>Dr Thibault SUTTER, PhD</b><br/>
    Biologiste spécialisé en biologie fonctionnelle<br/>
    Unilabs<br/><br/>
    ● Genève, Suisse
    """
    
    info_para = Paragraph(info_text, ParagraphStyle(
        name='FinalInfo',
        parent=styles['Normal'],
        fontSize=10,
        textColor=ModernColors.dark,
        alignment=TA_CENTER,
        leading=16
    ))
    
    elements.append(info_para)
    
    return elements

# ============================================================================
# GÉNÉRATEUR PRINCIPAL
# ============================================================================
def generate_modern_report(output_path, data, logo_path=None):
    """
    Génère un rapport médical moderne
    
    Args:
        output_path: Chemin du fichier PDF à créer
        data: Dictionnaire contenant toutes les données du rapport
        logo_path: Chemin vers le logo ALGO-LIFE
    """
    
    # Configuration du document
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2.5*cm,
        title="Rapport d'Analyses Biologiques UNILABS",
        author="Dr Thibault SUTTER, PhD"
    )
    
    # Liste des éléments du rapport
    story = []
    
    # 1. Page de garde
    story.extend(create_cover_page(data.get('patient', {}), logo_path))
    
    # 2. Résumé global
    story.extend(create_summary_section(data.get('resume', {})))
    
    # 3. Biomarqueurs
    story.extend(create_biomarkers_section(data.get('biomarqueurs', [])))
    
    # 4. Microbiote
    if 'microbiote' in data:
        story.extend(create_microbiome_section(data['microbiote']))
    
    # 5. Recommandations
    story.extend(create_recommendations_section(data.get('recommandations', {})))
    
    # 6. Suivi
    story.extend(create_followup_section(data.get('suivi', {})))
    
    # 7. Page finale
    story.extend(create_final_page(logo_path))
    
    # Construction du PDF avec pied de page
    doc.build(story, onFirstPage=modern_footer, onLaterPages=modern_footer)
    
    print(f"✓ Rapport généré avec succès : {output_path}")

# ============================================================================
# EXEMPLE D'UTILISATION
# ============================================================================
if __name__ == "__main__":
    # Données d'exemple complètes
    sample_data = {
        'patient': {
            'nom': 'SUTTER Thibault',
            'sexe': 'F',
            'date_naissance': '01/01/1980',
        },
        'resume': {
            'normaux': 8,
            'a_surveiller': 0,
            'anormaux': 4
        },
        'biomarqueurs': [
            {
                'nom': 'GLYCEMIE A JEUN',
                'valeur': 0.84,
                'unite': 'g/L',
                'min': 0.70,
                'max': 1.05,
                'statut': 'normal',
                'categorie': 'Métabolisme glucidique'
            },
            {
                'nom': 'FERRITINE',
                'valeur': 11.0,
                'unite': 'µg/L',
                'min': 15.0,
                'max': 150.0,
                'statut': 'abnormal',
                'categorie': 'Fer et minéraux'
            },
            {
                'nom': 'Hémoglobine',
                'valeur': 12.9,
                'unite': 'g/dL',
                'min': 11.5,
                'max': 16.0,
                'statut': 'normal',
                'categorie': 'Hématologie'
            },
            {
                'nom': 'GPX',
                'valeur': 171.0,
                'unite': 'U/g Hb',
                'min': 40.0,
                'max': 62.0,
                'statut': 'warning',
                'categorie': 'Stress oxydatif'
            },
            {
                'nom': 'Coenzyme Q10',
                'valeur': 506.0,
                'unite': 'µg/L',
                'min': 670.0,
                'max': 990.0,
                'statut': 'abnormal',
                'categorie': 'Mitochondries'
            },
            {
                'nom': 'Sélénium',
                'valeur': 82.0,
                'unite': 'µg/L',
                'min': 90.0,
                'max': 143.0,
                'statut': 'abnormal',
                'categorie': 'Oligo-éléments'
            }
        ],
        'microbiote': {
            'indice_dysbiose': 3,
            'diversite': 'as expected',
            'groupes_bacteriens': [
                {
                    'nom': 'A1. Prominent gut microbes represent the two most abundant bacteria',
                    'resultat': 'Expected',
                    'statut': '● Normal'
                },
                {
                    'nom': 'B1. Alistipes are bile-resistant bacteria',
                    'resultat': 'Expected',
                    'statut': '● Normal'
                },
                {
                    'nom': 'C1. Complex carbohydrate degraders',
                    'resultat': 'Expected',
                    'statut': '● Normal'
                },
                {
                    'nom': 'C2. Lactic acid bacteria and probiotics',
                    'resultat': 'Expected',
                    'statut': '● Normal'
                },
                {
                    'nom': 'D1. Gut epithelial integrity marker',
                    'resultat': 'Expected',
                    'statut': '● Normal'
                },
                {
                    'nom': 'D2. Major SCFA producers',
                    'resultat': 'Slightly deviating',
                    'statut': '● Normal'
                },
                {
                    'nom': 'E1. R. gnavus inflammation marker',
                    'resultat': 'Expected',
                    'statut': '● Normal'
                },
                {
                    'nom': 'E2. Potentially virulent B. fragilis',
                    'resultat': 'Expected',
                    'statut': '● Normal'
                },
                {
                    'nom': 'E5. Genital, respiratory, and skin bacteria',
                    'resultat': 'Slightly deviating',
                    'statut': '● Normal'
                }
            ]
        },
        'recommandations': {
            'a_surveiller': [
                'GPX: Élevé (171.0 U/g Hb)',
                'Glutathion total: Bas (1152.0 µmol/L)',
                'Coenzyme Q10: Bas (506.0 µg/L)',
                'Sélénium: Bas (82.0 µg/L)'
            ],
            'micronutrition': [
                'CoQ10 ubiquinol 200-400mg/j avec repas gras',
                'Sélénométhionine 200µg/j',
                'PQQ 20mg/j',
                'Carnitine 2g/j',
                'Vérifier dose sélénium supplémentée',
                'Éviter cumul multiples sources'
            ],
            'nutrition': [
                'Viandes organes (cœur, foie)',
                'Sardines, maquereaux',
                'Noix du Brésil 2-3/j (dose complète)',
                'Poissons, fruits de mer',
                'Œufs bio',
                'Épinards, brocoli'
            ],
            'hygiene_de_vie': [
                'CRUCIAL si statines (épuisent CoQ10)',
                'Support mitochondrial',
                'Support thyroïde et antioxydant',
                'Surveillance clinique si >400µg/j sélénium',
                'Symptômes toxicité: haleine ail, perte cheveux, ongles cassants'
            ]
        },
        'suivi': {
            'examens': [
                'Bilan de suivi recommandé dans 3 mois pour réévaluer les anomalies détectées',
                'Envisager test métabolites microbiens (SCFA) pour évaluation approfondie'
            ],
            'suivi': [
                'Suivi dans 3 mois recommandé : 4 paramètre(s) hors normes'
            ]
        }
    }
    
    # Générer le rapport avec le logo
    logo_path = '/home/claude/dna_logo.png'
    generate_modern_report('/home/claude/rapport_moderne_v2.pdf', sample_data, logo_path)
