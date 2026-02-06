#!/usr/bin/env python3
"""
Module d'export PDF pour UNILABS - Point d'entrée principal
Version: 2.0
Auteur: Dr Thibault SUTTER, PhD
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image, KeepTogether
)
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Circle
from PIL import Image as PILImage

# ============================================================================
# CONFIGURATION GLOBALE
# ============================================================================
class PDFConfig:
    """Configuration du générateur PDF"""
    VERSION = "2.0"
    AUTHOR = "Dr Thibault SUTTER, PhD"
    ORGANIZATION = "UNILABS"
    
    # Chemins par défaut
    DEFAULT_LOGO_PATH = "/home/claude/dna_logo.png"
    OUTPUT_DIR = "/mnt/user-data/outputs"
    
    # Palette de couleurs
    COLORS = {
        'primary': colors.HexColor('#1a5490'),
        'secondary': colors.HexColor('#2d7ab9'),
        'accent': colors.HexColor('#00a8cc'),
        'normal': colors.HexColor('#10b981'),
        'warning': colors.HexColor('#f59e0b'),
        'critical': colors.HexColor('#ef4444'),
        'dark': colors.HexColor('#1f2937'),
        'medium': colors.HexColor('#6b7280'),
        'light': colors.HexColor('#f3f4f6'),
        'background': colors.HexColor('#fafafa'),
        'microbiome': colors.HexColor('#8b5cf6'),
        'white': colors.white
    }

# ============================================================================
# STYLES
# ============================================================================
def get_styles():
    """Retourne les styles de paragraphe"""
    styles = getSampleStyleSheet()
    
    styles.add(ParagraphStyle(
        name='ModernTitle',
        parent=styles['Title'],
        fontSize=28,
        textColor=PDFConfig.COLORS['primary'],
        spaceAfter=8,
        fontName='Helvetica-Bold',
        alignment=TA_LEFT,
        leading=32
    ))
    
    styles.add(ParagraphStyle(
        name='ModernSubtitle',
        parent=styles['Normal'],
        fontSize=14,
        textColor=PDFConfig.COLORS['medium'],
        spaceAfter=20,
        fontName='Helvetica',
        alignment=TA_LEFT
    ))
    
    styles.add(ParagraphStyle(
        name='SectionHeader',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=PDFConfig.COLORS['primary'],
        spaceAfter=12,
        spaceBefore=20,
        fontName='Helvetica-Bold'
    ))
    
    styles.add(ParagraphStyle(
        name='SubsectionHeader',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=PDFConfig.COLORS['dark'],
        spaceAfter=8,
        spaceBefore=12,
        fontName='Helvetica-Bold'
    ))
    
    styles.add(ParagraphStyle(
        name='ModernBody',
        parent=styles['Normal'],
        fontSize=10,
        textColor=PDFConfig.COLORS['dark'],
        alignment=TA_JUSTIFY,
        spaceAfter=6,
        leading=14,
        fontName='Helvetica'
    ))
    
    styles.add(ParagraphStyle(
        name='Badge',
        parent=styles['Normal'],
        fontSize=11,
        textColor=PDFConfig.COLORS['white'],
        fontName='Helvetica-Bold',
        alignment=TA_CENTER
    ))
    
    return styles

# ============================================================================
# PIED DE PAGE
# ============================================================================
def modern_footer(canvas, doc):
    """Pied de page professionnel"""
    canvas.saveState()
    
    canvas.setStrokeColor(PDFConfig.COLORS['light'])
    canvas.setLineWidth(0.5)
    canvas.line(2*cm, 2*cm, A4[0]-2*cm, 2*cm)
    
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(PDFConfig.COLORS['medium'])
    
    canvas.drawString(2*cm, 1.5*cm, "CONFIDENTIEL - Document médical")
    canvas.drawCentredString(A4[0]/2, 1.5*cm, "Dr Thibault SUTTER, PhD")
    canvas.drawRightString(A4[0]-2*cm, 1.5*cm, f"Page {canvas.getPageNumber()}")
    
    canvas.restoreState()

# ============================================================================
# PAGE DE GARDE
# ============================================================================
def create_cover_page(patient_data, logo_path=None):
    """Crée la page de garde"""
    elements = []
    styles = get_styles()
    
    elements.append(Spacer(1, 1.5*cm))
    
    # Logo
    if logo_path and os.path.exists(logo_path):
        try:
            logo = Image(logo_path, width=4*cm, height=4*cm, kind='proportional')
            elements.append(logo)
        except Exception as e:
            print(f"⚠ Erreur logo: {e}")
    
    elements.append(Spacer(1, 1*cm))
    
    # Titre
    elements.append(Paragraph("Rapport d'Analyses Biologiques", styles['ModernTitle']))
    elements.append(Paragraph("UNILABS - Analyse multimodale & recommandations personnalisées", 
                             styles['ModernSubtitle']))
    elements.append(Spacer(1, 2*cm))
    
    # Informations patient
    patient_info = [
        ['PATIENT', patient_data.get('nom', 'N/A')],
        ['SEXE', patient_data.get('sexe', 'N/A')],
        ['DATE DE NAISSANCE', patient_data.get('date_naissance', 'N/A')],
        ['DATE DU RAPPORT', datetime.now().strftime('%d/%m/%Y')]
    ]
    
    table = Table(patient_info, colWidths=[5*cm, 10*cm])
    table.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), 'Helvetica', 11),
        ('FONT', (0, 0), (0, -1), 'Helvetica-Bold', 10),
        ('TEXTCOLOR', (0, 0), (0, -1), PDFConfig.COLORS['medium']),
        ('TEXTCOLOR', (1, 0), (1, -1), PDFConfig.COLORS['dark']),
        ('BACKGROUND', (0, 0), (-1, -1), PDFConfig.COLORS['light']),
        ('LINEABOVE', (0, 0), (-1, 0), 2, PDFConfig.COLORS['primary']),
        ('LEFTPADDING', (0, 0), (-1, -1), 15),
        ('RIGHTPADDING', (0, 0), (-1, -1), 15),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
    ]))
    
    elements.append(table)
    elements.append(Spacer(1, 3*cm))
    
    # Badge confidentiel
    confid = Paragraph("CONFIDENTIEL - Usage médical uniquement", styles['Badge'])
    confid_table = Table([[confid]], colWidths=[12*cm])
    confid_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), PDFConfig.COLORS['primary']),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))
    
    elements.append(confid_table)
    
    return elements

# ============================================================================
# RÉSUMÉ DES BIOMARQUEURS
# ============================================================================
def create_summary_section(summary_data):
    """Crée le résumé global avec cartes visuelles"""
    elements = []
    styles = get_styles()
    
    elements.append(PageBreak())
    elements.append(Spacer(1, 1*cm))
    elements.append(Paragraph("Résumé global des biomarqueurs", styles['SectionHeader']))
    elements.append(Spacer(1, 1*cm))
    
    normal = summary_data.get('normaux', 0)
    warning = summary_data.get('a_surveiller', 0)
    abnormal = summary_data.get('anormaux', 0)
    
    # Cartes visuelles
    d = Drawing(500, 200)
    card_width, card_height = 140, 160
    spacing, start_x = 20, 10
    
    def create_card(x, y, w, h, color, count, label, bar_color):
        d.add(Rect(x, y, w, h, fillColor=colors.white, 
                  strokeColor=color, strokeWidth=2))
        d.add(Rect(x, y, 6, h, fillColor=bar_color, strokeColor=None))
        d.add(String(x + w/2, y + h - 60, str(count), fontSize=42,
                    fillColor=color, textAnchor='middle', fontName='Helvetica-Bold'))
        d.add(String(x + w/2, y + 30, label, fontSize=11,
                    fillColor=PDFConfig.COLORS['medium'], textAnchor='middle'))
    
    create_card(start_x, 20, card_width, card_height,
               PDFConfig.COLORS['normal'], normal, 'Normaux', PDFConfig.COLORS['normal'])
    create_card(start_x + card_width + spacing, 20, card_width, card_height,
               PDFConfig.COLORS['warning'], warning, 'À surveiller', PDFConfig.COLORS['warning'])
    create_card(start_x + 2*(card_width + spacing), 20, card_width, card_height,
               PDFConfig.COLORS['critical'], abnormal, 'Anormaux', PDFConfig.COLORS['critical'])
    
    elements.append(d)
    elements.append(Spacer(1, 1.5*cm))
    
    return elements

# ============================================================================
# BIOMARQUEURS
# ============================================================================
def create_biomarker_viz(name, value, unit, min_val, max_val, status):
    """Visualisation d'un biomarqueur"""
    color = {
        'normal': PDFConfig.COLORS['normal'],
        'warning': PDFConfig.COLORS['warning'],
        'abnormal': PDFConfig.COLORS['critical']
    }.get(status, PDFConfig.COLORS['normal'])
    
    d = Drawing(400, 60)
    bar_y, bar_height, bar_width, bar_x = 25, 8, 300, 50
    
    # Barre de fond
    d.add(Rect(bar_x, bar_y, bar_width, bar_height,
              fillColor=colors.HexColor('#e8f5e9'), strokeColor=None))
    
    # Position du marqueur
    if min_val is not None and max_val is not None and max_val > min_val:
        position = max(0, min(1, (value - min_val) / (max_val - min_val)))
    else:
        position = 0.5
    
    # Marqueur
    marker_x = bar_x + (bar_width * position)
    d.add(Circle(marker_x, bar_y + bar_height/2, 6,
                fillColor=color, strokeColor=PDFConfig.COLORS['white'], strokeWidth=2))
    
    # Textes
    d.add(String(bar_x - 5, bar_y + bar_height/2, str(min_val) if min_val else '',
                fontSize=8, fillColor=PDFConfig.COLORS['medium'], textAnchor='end'))
    d.add(String(bar_x + bar_width + 5, bar_y + bar_height/2, str(max_val) if max_val else '',
                fontSize=8, fillColor=PDFConfig.COLORS['medium'], textAnchor='start'))
    d.add(String(5, 45, name, fontSize=11, fillColor=PDFConfig.COLORS['dark'],
                fontName='Helvetica-Bold', textAnchor='start'))
    d.add(String(5, 5, f"{value} {unit}", fontSize=10, fillColor=color,
                fontName='Helvetica-Bold', textAnchor='start'))
    
    if min_val is not None and max_val is not None:
        d.add(String(200, 5, f"Normes: {min_val} — {max_val}", fontSize=8,
                    fillColor=PDFConfig.COLORS['medium'], textAnchor='start'))
    
    return d

def create_biomarkers_section(biomarkers):
    """Section des biomarqueurs"""
    elements = []
    styles = get_styles()
    
    elements.append(PageBreak())
    elements.append(Spacer(1, 1*cm))
    elements.append(Paragraph("Biomarqueurs", styles['SectionHeader']))
    elements.append(Spacer(1, 0.5*cm))
    
    # Grouper par catégorie
    categories = {}
    for bm in biomarkers:
        cat = bm.get('categorie', 'Autres')
        categories.setdefault(cat, []).append(bm)
    
    for cat_name, cat_biomarkers in categories.items():
        elements.append(Paragraph(cat_name, styles['SubsectionHeader']))
        elements.append(Spacer(1, 0.3*cm))
        
        for bm in cat_biomarkers:
            viz = create_biomarker_viz(
                bm['nom'], bm['valeur'], bm['unite'],
                bm.get('min'), bm.get('max'), bm.get('statut', 'normal')
            )
            elements.append(viz)
            elements.append(Spacer(1, 0.5*cm))
    
    return elements

# ============================================================================
# MICROBIOTE
# ============================================================================
def create_microbiome_section(microbiome_data):
    """Section microbiote"""
    elements = []
    styles = get_styles()
    
    elements.append(PageBreak())
    elements.append(Spacer(1, 1*cm))
    elements.append(Paragraph("Microbiote", styles['SectionHeader']))
    elements.append(Spacer(1, 0.5*cm))
    
    # Indices
    indices = [
        ['Indice de dysbiose (DI)', str(microbiome_data.get('indice_dysbiose', 'N/A'))],
        ['Diversité', microbiome_data.get('diversite', 'N/A')]
    ]
    
    table = Table(indices, colWidths=[8*cm, 7*cm])
    table.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), 'Helvetica', 10),
        ('FONT', (0, 0), (0, -1), 'Helvetica-Bold', 10),
        ('BACKGROUND', (0, 0), (-1, -1), PDFConfig.COLORS['light']),
        ('GRID', (0, 0), (-1, -1), 0.5, PDFConfig.COLORS['white']),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    
    elements.append(table)
    elements.append(Spacer(1, 0.8*cm))
    
    # Groupes bactériens
    if 'groupes_bacteriens' in microbiome_data:
        groups = microbiome_data['groupes_bacteriens']
        normal_groups = [g for g in groups if 'Normal' in g.get('statut', '')]
        abnormal_groups = [g for g in groups if 'Normal' not in g.get('statut', '')]
        
        # Normaux
        if normal_groups:
            elements.append(Paragraph("Souches normales", styles['SubsectionHeader']))
            elements.append(Spacer(1, 0.3*cm))
            
            data = [['Groupe bactérien', 'Résultat', 'Statut']]
            data.extend([[g['nom'], g['resultat'], '● Normal'] for g in normal_groups])
            
            table = Table(data, colWidths=[9*cm, 4*cm, 2.5*cm])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), PDFConfig.COLORS['normal']),
                ('TEXTCOLOR', (0, 0), (-1, 0), PDFConfig.COLORS['white']),
                ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 9),
                ('FONT', (0, 1), (-1, -1), 'Helvetica', 8),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), 
                 [PDFConfig.COLORS['white'], colors.HexColor('#f0fdf4')]),
                ('GRID', (0, 0), (-1, -1), 0.5, PDFConfig.COLORS['medium']),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ]))
            
            elements.append(table)
            elements.append(Spacer(1, 0.8*cm))
        
        # Anormaux
        if abnormal_groups:
            elements.append(Paragraph("Souches à surveiller / anormales", styles['SubsectionHeader']))
            elements.append(Spacer(1, 0.3*cm))
            
            data = [['Groupe bactérien', 'Résultat', 'Statut']]
            data.extend([[g['nom'], g['resultat'], g['statut']] for g in abnormal_groups])
            
            table = Table(data, colWidths=[9*cm, 4*cm, 2.5*cm])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), PDFConfig.COLORS['critical']),
                ('TEXTCOLOR', (0, 0), (-1, 0), PDFConfig.COLORS['white']),
                ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 9),
                ('FONT', (0, 1), (-1, -1), 'Helvetica', 8),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1),
                 [PDFConfig.COLORS['white'], colors.HexColor('#fef2f2')]),
                ('GRID', (0, 0), (-1, -1), 0.5, PDFConfig.COLORS['medium']),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ]))
            
            elements.append(table)
    
    return elements

# ============================================================================
# RECOMMANDATIONS
# ============================================================================
def create_recommendations_section(recommendations):
    """Section recommandations avec tableaux élégants"""
    elements = []
    styles = get_styles()
    
    elements.append(PageBreak())
    elements.append(Spacer(1, 1*cm))
    elements.append(Paragraph("Recommandations personnalisées", styles['SectionHeader']))
    elements.append(Spacer(1, 0.5*cm))
    
    # À surveiller
    if recommendations.get('a_surveiller'):
        elements.append(Paragraph("À surveiller", styles['SubsectionHeader']))
        elements.append(Spacer(1, 0.3*cm))
        
        data = [['⚠️  Biomarqueur']]
        data.extend([[item] for item in recommendations['a_surveiller']])
        
        table = Table(data, colWidths=[15*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), PDFConfig.COLORS['warning']),
            ('TEXTCOLOR', (0, 0), (-1, 0), PDFConfig.COLORS['white']),
            ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 11),
            ('FONT', (0, 1), (-1, -1), 'Helvetica', 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1),
             [colors.HexColor('#fffbeb'), PDFConfig.COLORS['white']]),
            ('GRID', (0, 0), (-1, -1), 0.5, PDFConfig.COLORS['warning']),
            ('BOX', (0, 0), (-1, -1), 1.5, PDFConfig.COLORS['warning']),
            ('LEFTPADDING', (0, 0), (-1, -1), 12),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 0.8*cm))
    
    # Catégories
    categories = {
        'micronutrition': ('💊  Micronutrition', PDFConfig.COLORS['accent']),
        'nutrition': ('🥗  Nutrition', PDFConfig.COLORS['normal']),
        'hygiene_de_vie': ('🏃  Hygiène de vie', PDFConfig.COLORS['microbiome'])
    }
    
    for key, (title, color) in categories.items():
        if recommendations.get(key):
            elements.append(Paragraph(title, styles['SubsectionHeader']))
            elements.append(Spacer(1, 0.3*cm))
            
            data = [['Recommandation']]
            data.extend([[item] for item in recommendations[key]])
            
            table = Table(data, colWidths=[15*cm])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), color),
                ('TEXTCOLOR', (0, 0), (-1, 0), PDFConfig.COLORS['white']),
                ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 10),
                ('FONT', (0, 1), (-1, -1), 'Helvetica', 9),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1),
                 [PDFConfig.COLORS['white'], PDFConfig.COLORS['light']]),
                ('GRID', (0, 0), (-1, -1), 0.5, PDFConfig.COLORS['medium']),
                ('BOX', (0, 0), (-1, -1), 1, color),
                ('LEFTPADDING', (0, 0), (-1, -1), 12),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ]))
            
            elements.append(table)
            elements.append(Spacer(1, 0.6*cm))
    
    return elements

# ============================================================================
# SUIVI
# ============================================================================
def create_followup_section(followup_data):
    """Section suivi"""
    elements = []
    styles = get_styles()
    
    elements.append(PageBreak())
    elements.append(Spacer(1, 1*cm))
    elements.append(Paragraph("Examens complémentaires", styles['SectionHeader']))
    elements.append(Spacer(1, 0.3*cm))
    
    if followup_data.get('examens'):
        for exam in followup_data['examens']:
            elements.append(Paragraph(f"• {exam}", styles['ModernBody']))
    
    elements.append(Spacer(1, 0.8*cm))
    elements.append(Paragraph("Suivi", styles['SectionHeader']))
    elements.append(Spacer(1, 0.3*cm))
    
    if followup_data.get('suivi'):
        for item in followup_data['suivi']:
            elements.append(Paragraph(f"• {item}", styles['ModernBody']))
    
    return elements

# ============================================================================
# PAGE FINALE
# ============================================================================
def create_final_page(logo_path=None):
    """Page finale"""
    elements = []
    styles = get_styles()
    
    elements.append(PageBreak())
    elements.append(Spacer(1, 3*cm))
    
    if logo_path and os.path.exists(logo_path):
        try:
            logo = Image(logo_path, width=4*cm, height=4*cm, kind='proportional')
            elements.append(logo)
        except:
            pass
    
    elements.append(Spacer(1, 1*cm))
    
    info = """
    <b>UNILABS © 2026</b><br/>
    Powered by Unilabs Group<br/><br/>
    <b>Dr Thibault SUTTER, PhD</b><br/>
    Biologiste spécialisé en biologie fonctionnelle<br/>
    Unilabs<br/><br/>
    ● Genève, Suisse
    """
    
    elements.append(Paragraph(info, ParagraphStyle(
        name='FinalInfo',
        parent=styles['Normal'],
        fontSize=10,
        textColor=PDFConfig.COLORS['dark'],
        alignment=TA_CENTER,
        leading=16
    )))
    
    return elements

# ============================================================================
# GÉNÉRATEUR PRINCIPAL
# ============================================================================
def generate_report(output_path, data, logo_path=None):
    """
    Génère un rapport PDF complet
    
    Args:
        output_path (str): Chemin du PDF à créer
        data (dict): Données du rapport
        logo_path (str): Chemin du logo (optionnel)
    
    Returns:
        bool: True si succès, False sinon
    """
    try:
        # Utiliser le logo par défaut si non fourni
        if logo_path is None:
            logo_path = PDFConfig.DEFAULT_LOGO_PATH
        
        # Créer le document
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2.5*cm,
            title="Rapport d'Analyses Biologiques UNILABS",
            author=PDFConfig.AUTHOR
        )
        
        # Construire le contenu
        story = []
        story.extend(create_cover_page(data.get('patient', {}), logo_path))
        story.extend(create_summary_section(data.get('resume', {})))
        story.extend(create_biomarkers_section(data.get('biomarqueurs', [])))
        
        if 'microbiote' in data:
            story.extend(create_microbiome_section(data['microbiote']))
        
        story.extend(create_recommendations_section(data.get('recommandations', {})))
        story.extend(create_followup_section(data.get('suivi', {})))
        story.extend(create_final_page(logo_path))
        
        # Générer le PDF
        doc.build(story, onFirstPage=modern_footer, onLaterPages=modern_footer)
        
        print(f"✅ Rapport généré: {output_path}")
        return True
        
    except Exception as e:
        print(f"❌ Erreur génération PDF: {e}")
        import traceback
        traceback.print_exc()
        return False

# ============================================================================
# POINT D'ENTRÉE
# ============================================================================
if __name__ == "__main__":
    # Données de test
    test_data = {
        'patient': {
            'nom': 'SUTTER Thibault',
            'sexe': 'F',
            'date_naissance': '01/01/1980',
        },
        'resume': {'normaux': 8, 'a_surveiller': 0, 'anormaux': 4},
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
            }
        ],
        'microbiote': {
            'indice_dysbiose': 3,
            'diversite': 'as expected',
            'groupes_bacteriens': [
                {'nom': 'A1. Prominent gut microbes', 'resultat': 'Expected', 'statut': '● Normal'},
                {'nom': 'D2. Major SCFA producers', 'resultat': 'Slightly deviating', 'statut': '● Normal'}
            ]
        },
        'recommandations': {
            'a_surveiller': ['GPX: Élevé (171.0 U/g Hb)'],
            'micronutrition': ['CoQ10 ubiquinol 200-400mg/j'],
            'nutrition': ['Viandes organes (cœur, foie)'],
            'hygiene_de_vie': ['Support mitochondrial']
        },
        'suivi': {
            'examens': ['Bilan de suivi dans 3 mois'],
            'suivi': ['Suivi dans 3 mois recommandé']
        }
    }
    
    success = generate_report('/home/claude/test_rapport.pdf', test_data)
    sys.exit(0 if success else 1)
