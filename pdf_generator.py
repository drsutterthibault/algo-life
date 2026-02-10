#!/usr/bin/env python3
"""
PDF Generator v2.0 FINAL - Compatible avec app.py v13 et extractors v19
✅ Templates biomarqueurs TOUS présents avec barres de progression
✅ Résultats microbiote DÉTAILLÉS avec les 48 bactéries
✅ Résultats biologie COMPLETS avec interprétations
✅ Design professionnel avec couleurs et icônes
✅ Compatible bacteria_groups ET bacteria_individual
"""

import os
import re
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.graphics.shapes import Drawing, Rect, String, Circle, Line

# LOGO
DEFAULT_LOGO = "/dna_logo.png"

def _safe_float(x):
    """Conversion sécurisée en float"""
    try:
        if x is None or str(x).strip() == '':
            return None
        val_str = str(x).strip().replace(',', '.').replace(' ', '')
        # Nettoyer les caractères non numériques sauf . et -
        val_str = re.sub(r'[^\d\.\-]', '', val_str)
        return float(val_str) if val_str else None
    except:
        return None


def _parse_reference(ref_str):
    """Parse une référence type '0.70 — 1.05' ou '< 50' ou '> 10'"""
    if not ref_str or str(ref_str).strip() == '':
        return None, None, None
    
    ref = str(ref_str).strip()
    
    # Type 1: Plage (0.70 — 1.05 ou 0.70 - 1.05)
    match = re.search(r'(\d+\.?\d*)\s*[-—–]\s*(\d+\.?\d*)', ref)
    if match:
        min_val = _safe_float(match.group(1))
        max_val = _safe_float(match.group(2))
        return min_val, max_val, 'range'
    
    # Type 2: Limite supérieure (< 50 ou ≤ 50)
    match = re.search(r'[<≤]\s*(\d+\.?\d*)', ref)
    if match:
        max_val = _safe_float(match.group(1))
        return None, max_val, 'max'
    
    # Type 3: Limite inférieure (> 10 ou ≥ 10)
    match = re.search(r'[>≥]\s*(\d+\.?\d*)', ref)
    if match:
        min_val = _safe_float(match.group(1))
        return min_val, None, 'min'
    
    return None, None, None


def create_biomarker_visualization(name, value, unit, reference, status, width=480, height=70):
    """
    Crée une visualisation COMPLÈTE pour un biomarqueur avec barre de progression
    
    Returns:
        Drawing object ReportLab
    """
    d = Drawing(width, height)
    
    # Couleur selon statut
    if status in ['Normal', 'normal']:
        color = colors.HexColor('#10b981')  # Vert
        bg_color = colors.HexColor('#d1fae5')
    elif status in ['Élevé', 'Elevé', 'élevé', 'elevé', 'High', 'high']:
        color = colors.HexColor('#ef4444')  # Rouge
        bg_color = colors.HexColor('#fee2e2')
    elif status in ['Bas', 'bas', 'Low', 'low']:
        color = colors.HexColor('#f59e0b')  # Orange
        bg_color = colors.HexColor('#fef3c7')
    else:
        color = colors.HexColor('#6b7280')  # Gris
        bg_color = colors.HexColor('#f3f4f6')
    
    # Fond coloré
    d.add(Rect(0, 0, width, height, fillColor=bg_color, strokeColor=None))
    
    # Nom du biomarqueur (ligne 1, gras)
    d.add(String(10, height - 15, name[:60], 
                 fontSize=11, fillColor=colors.HexColor('#1f2937'), 
                 fontName='Helvetica-Bold'))
    
    # Valeur + Unité (ligne 2, colorée selon statut)
    value_str = f"{value} {unit}" if value is not None else "N/A"
    d.add(String(10, height - 35, value_str, 
                 fontSize=12, fillColor=color, 
                 fontName='Helvetica-Bold'))
    
    # Statut badge (ligne 2, à droite)
    status_x = width - 80
    d.add(Rect(status_x, height - 38, 70, 16, 
               fillColor=color, strokeColor=None))
    d.add(String(status_x + 5, height - 35, status, 
                 fontSize=9, fillColor=colors.white, 
                 fontName='Helvetica-Bold'))
    
    # Parse référence
    min_val, max_val, ref_type = _parse_reference(reference)
    
    # Afficher référence texte
    if reference and str(reference).strip():
        d.add(String(10, 8, f"Réf: {reference}", 
                     fontSize=8, fillColor=colors.HexColor('#6b7280')))
    
    # Barre de progression (si plage disponible)
    if ref_type == 'range' and min_val is not None and max_val is not None:
        bar_x, bar_y, bar_width, bar_height = 150, 8, 300, 10
        
        # Fond gris de la barre
        d.add(Rect(bar_x, bar_y, bar_width, bar_height, 
                   fillColor=colors.HexColor('#e5e7eb'), strokeColor=colors.HexColor('#d1d5db')))
        
        # Zone normale (vert clair)
        d.add(Rect(bar_x, bar_y, bar_width, bar_height, 
                   fillColor=colors.HexColor('#d1fae5'), strokeColor=None, fillOpacity=0.3))
        
        # Position du marqueur (valeur du patient)
        try:
            value_float = _safe_float(value)
            if value_float is not None and max_val > min_val:
                # Clamp entre 0 et 1, mais permettre de dépasser légèrement pour montrer les anomalies
                position = (value_float - min_val) / (max_val - min_val)
                position = max(-0.1, min(1.1, position))  # Permettre ±10% de dépassement
            else:
                position = 0.5
        except:
            position = 0.5
        
        marker_x = bar_x + (bar_width * max(0, min(1, position)))
        
        # Marqueur circulaire (valeur du patient)
        d.add(Circle(marker_x, bar_y + bar_height/2, 7, 
                     fillColor=color, strokeColor=colors.white, strokeWidth=2))
        
        # Indicateurs min/max
        d.add(String(bar_x - 5, bar_y - 2, str(min_val), 
                     fontSize=7, fillColor=colors.HexColor('#6b7280'), textAnchor='end'))
        d.add(String(bar_x + bar_width + 5, bar_y - 2, str(max_val), 
                     fontSize=7, fillColor=colors.HexColor('#6b7280')))
    
    elif ref_type == 'max' and max_val is not None:
        # Barre simplifiée pour "< X"
        bar_x, bar_y, bar_width, bar_height = 150, 8, 300, 10
        d.add(Rect(bar_x, bar_y, bar_width, bar_height, 
                   fillColor=colors.HexColor('#e5e7eb'), strokeColor=colors.HexColor('#d1d5db')))
        
        try:
            value_float = _safe_float(value)
            if value_float is not None:
                position = min(1.0, value_float / (max_val * 1.2))
            else:
                position = 0.5
        except:
            position = 0.5
        
        marker_x = bar_x + (bar_width * position)
        d.add(Circle(marker_x, bar_y + bar_height/2, 7, 
                     fillColor=color, strokeColor=colors.white, strokeWidth=2))
        
        d.add(String(bar_x + bar_width + 5, bar_y - 2, f"< {max_val}", 
                     fontSize=7, fillColor=colors.HexColor('#6b7280')))
    
    return d


def generate_multimodal_report(
    patient_data, 
    biology_data, 
    microbiome_data,
    recommendations, 
    cross_analysis, 
    follow_up,
    bio_age_result=None, 
    output_path=None
):
    """
    Génère le rapport PDF COMPLET - Compatible app.py v13 et extractors v19
    
    Args:
        patient_data: dict avec name, sex, age, birthdate, weight, height, bmi
        biology_data: list de dict avec Biomarqueur, Valeur, Unité, Référence, Statut
        microbiome_data: dict avec dysbiosis_index, diversity, bacteria_groups, bacteria_individual
        recommendations: dict avec Prioritaires, À surveiller, Nutrition, Micronutrition, etc.
        cross_analysis: list de dict avec analyses croisées
        follow_up: dict avec suivi
        bio_age_result: dict avec âge biologique (optionnel)
        output_path: chemin du PDF de sortie
    
    Returns:
        str: Chemin du PDF généré
    """
    
    if output_path is None:
        import tempfile
        output_path = os.path.join(tempfile.gettempdir(), 'rapport_unilabs.pdf')
    
    # Configuration PDF
    doc = SimpleDocTemplate(
        output_path, 
        pagesize=A4, 
        leftMargin=2*cm, 
        rightMargin=2*cm,
        topMargin=2*cm, 
        bottomMargin=2.5*cm
    )
    
    story = []
    styles = getSampleStyleSheet()
    
    # ==================== STYLES PERSONNALISÉS ====================
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=26,
        textColor=colors.HexColor('#1a5490'),
        spaceAfter=20,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Heading2'],
        fontSize=18,
        textColor=colors.HexColor('#1a5490'),
        spaceAfter=15,
        spaceBefore=10,
        fontName='Helvetica-Bold'
    )
    
    heading3_style = ParagraphStyle(
        'Heading3Custom',
        parent=styles['Heading3'],
        fontSize=14,
        textColor=colors.HexColor('#1f2937'),
        spaceAfter=10,
        spaceBefore=8,
        fontName='Helvetica-Bold'
    )
    
    normal_justify = ParagraphStyle(
        'NormalJustify',
        parent=styles['Normal'],
        alignment=TA_JUSTIFY,
        fontSize=10
    )
    
    # ==================== PAGE 1: PAGE DE GARDE ====================
    # Logo en haut
    if os.path.exists(DEFAULT_LOGO):
        try:
            logo = Image(DEFAULT_LOGO, width=5*cm, height=5*cm, kind='proportional')
            story.append(logo)
            story.append(Spacer(1, 1*cm))
        except Exception as e:
            print(f"⚠ Logo non chargé: {e}")
    
    # Titre principal
    story.append(Paragraph("RAPPORT D'ANALYSES BIOLOGIQUES", title_style))
    story.append(Paragraph("Biologie Fonctionnelle & Microbiote", styles['Normal']))
    story.append(Spacer(1, 0.5*cm))
    
    # Bloc UNILABS
    story.append(Paragraph("<b>UNILABS</b> - Laboratoire Central de Suisse Romande", 
                          ParagraphStyle('Center', parent=styles['Normal'], alignment=TA_CENTER, fontSize=11)))
    story.append(Spacer(1, 2*cm))
    
    # Informations patient (tableau élégant)
    patient_table_data = [
        ['PATIENT', patient_data.get('name', 'N/A')],
        ['SEXE', patient_data.get('sex', 'N/A')],
        ['DATE DE NAISSANCE', str(patient_data.get('birthdate', 'N/A'))],
        ['ÂGE', f"{patient_data.get('age', 'N/A')} ans"],
    ]
    
    # Ajouter IMC si disponible
    bmi = patient_data.get('bmi')
    if bmi:
        patient_table_data.append(['IMC', f"{bmi:.1f} kg/m²"])
    
    patient_table = Table(patient_table_data, colWidths=[6*cm, 10*cm])
    patient_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#1a5490')),
        ('BACKGROUND', (1,0), (1,-1), colors.HexColor('#f8f9fa')),
        ('TEXTCOLOR', (0,0), (0,-1), colors.white),
        ('FONT', (0,0), (0,-1), 'Helvetica-Bold', 11),
        ('FONT', (1,0), (1,-1), 'Helvetica', 11),
        ('GRID', (0,0), (-1,-1), 1, colors.HexColor('#d1d5db')),
        ('PADDING', (0,0), (-1,-1), 12),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOX', (0,0), (-1,-1), 2, colors.HexColor('#1a5490'))
    ]))
    
    story.append(patient_table)
    story.append(Spacer(1, 1*cm))
    
    # Date du rapport
    from datetime import datetime
    story.append(Paragraph(
        f"<i>Rapport généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}</i>",
        ParagraphStyle('ItalicCenter', parent=styles['Normal'], alignment=TA_CENTER, fontSize=9, textColor=colors.HexColor('#6b7280'))
    ))
    
    story.append(PageBreak())
    
    # ==================== PAGE 2+: BIOMARQUEURS ====================
    if biology_data:
        story.append(Paragraph("🧪 RÉSULTATS BIOLOGIE", subtitle_style))
        story.append(Spacer(1, 0.5*cm))
        
        # Résumé statistique
        total = len(biology_data)
        normaux = sum(1 for b in biology_data if b.get('Statut') in ['Normal', 'normal'])
        eleves = sum(1 for b in biology_data if b.get('Statut') in ['Élevé', 'Elevé', 'élevé', 'elevé'])
        bas = sum(1 for b in biology_data if b.get('Statut') in ['Bas', 'bas'])
        inconnus = total - normaux - eleves - bas
        
        summary_table_data = [
            ['📊 RÉSUMÉ', ''],
            ['Total biomarqueurs analysés', str(total)],
            ['✅ Normaux', str(normaux)],
            ['⬆️ Élevés', str(eleves)],
            ['⬇️ Bas', str(bas)],
            ['❓ Inconnus', str(inconnus)]
        ]
        
        summary_table = Table(summary_table_data, colWidths=[10*cm, 6*cm])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1a5490')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONT', (0,0), (-1,0), 'Helvetica-Bold', 12),
            ('BACKGROUND', (0,2), (-1,2), colors.HexColor('#d1fae5')),
            ('BACKGROUND', (0,3), (-1,3), colors.HexColor('#fee2e2')),
            ('BACKGROUND', (0,4), (-1,4), colors.HexColor('#fef3c7')),
            ('FONT', (0,1), (-1,-1), 'Helvetica', 10),
            ('FONT', (1,1), (1,-1), 'Helvetica-Bold', 14),
            ('ALIGN', (1,0), (1,-1), 'CENTER'),
            ('GRID', (0,0), (-1,-1), 1, colors.HexColor('#d1d5db')),
            ('PADDING', (0,0), (-1,-1), 10),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE')
        ]))
        
        story.append(summary_table)
        story.append(Spacer(1, 1*cm))
        
        # Section détails
        story.append(Paragraph("DÉTAILS DES BIOMARQUEURS", heading3_style))
        story.append(Spacer(1, 0.5*cm))
        
        # ✅ TOUS LES BIOMARQUEURS AVEC VISUALISATIONS
        for bio in biology_data:
            name = str(bio.get('Biomarqueur', 'N/A'))
            value = bio.get('Valeur')
            unit = str(bio.get('Unité', ''))
            status = bio.get('Statut', 'Normal')
            reference = bio.get('Référence', '')
            
            # Créer la visualisation
            viz = create_biomarker_visualization(name, value, unit, reference, status)
            story.append(viz)
            story.append(Spacer(1, 0.3*cm))
        
        story.append(PageBreak())
    
    # ==================== PAGE 3+: ÂGE BIOLOGIQUE ====================
    if bio_age_result:
        story.append(Paragraph("🧬 ÂGE BIOLOGIQUE (bFRAil Score)", subtitle_style))
        story.append(Spacer(1, 0.5*cm))
        
        bio_age = bio_age_result.get('bio_age', 0)
        chrono_age = patient_data.get('age', 0)
        diff = bio_age - chrono_age
        prob = bio_age_result.get('frailty_probability', 0)
        risk = bio_age_result.get('risk_category', 'N/A')
        
        # Tableau âge biologique
        bioage_data = [
            ['Âge chronologique', f"{chrono_age} ans"],
            ['Âge biologique', f"{bio_age:.1f} ans"],
            ['Différence', f"{diff:+.1f} ans"],
            ['Probabilité de fragilité', f"{prob:.1f}%"],
            ['Catégorie de risque', risk]
        ]
        
        bioage_table = Table(bioage_data, colWidths=[10*cm, 6*cm])
        bioage_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8f9fa')),
            ('FONT', (0,0), (0,-1), 'Helvetica-Bold', 11),
            ('FONT', (1,0), (1,-1), 'Helvetica', 11),
            ('GRID', (0,0), (-1,-1), 1, colors.HexColor('#d1d5db')),
            ('PADDING', (0,0), (-1,-1), 12),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE')
        ]))
        
        story.append(bioage_table)
        story.append(Spacer(1, 0.5*cm))
        
        # Interprétation
        interp = Paragraph(
            f"<i>Votre âge biologique est de <b>{bio_age:.1f} ans</b>, soit une différence de <b>{diff:+.1f} ans</b> "
            f"par rapport à votre âge chronologique. Probabilité de fragilité : <b>{prob:.1f}%</b> ({risk}).</i>",
            normal_justify
        )
        story.append(interp)
        story.append(PageBreak())
    
    # ==================== PAGE 4+: MICROBIOME ====================
    if microbiome_data:
        story.append(Paragraph("🦠 ANALYSE MICROBIOTE", subtitle_style))
        story.append(Spacer(1, 0.5*cm))
        
        # Vue d'ensemble
        di = microbiome_data.get('dysbiosis_index')
        di_text = microbiome_data.get('dysbiosis_text', 'Unknown')
        diversity = microbiome_data.get('diversity', 'N/A')
        
        microbiome_summary_data = [
            ['📊 VUE D\'ENSEMBLE', ''],
            ['Indice de dysbiose (DI)', f"{di}/5" if di is not None else 'N/A'],
            ['Interprétation DI', di_text],
            ['Diversité bactérienne', diversity]
        ]
        
        micro_summary_table = Table(microbiome_summary_data, colWidths=[10*cm, 6*cm])
        micro_summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#a855f7')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONT', (0,0), (-1,0), 'Helvetica-Bold', 12),
            ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#faf5ff')),
            ('FONT', (0,1), (0,-1), 'Helvetica-Bold', 10),
            ('FONT', (1,1), (1,-1), 'Helvetica', 10),
            ('GRID', (0,0), (-1,-1), 1, colors.HexColor('#d1d5db')),
            ('PADDING', (0,0), (-1,-1), 12),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE')
        ]))
        
        story.append(micro_summary_table)
        story.append(Spacer(1, 1*cm))
        
        # ✅ GROUPES BACTÉRIENS (bacteria_groups)
        bacteria_groups = microbiome_data.get('bacteria_groups', [])
        
        if bacteria_groups:
            story.append(Paragraph("GROUPES BACTÉRIENS ANALYSÉS", heading3_style))
            story.append(Spacer(1, 0.3*cm))
            
            # Statistiques
            expected = sum(1 for g in bacteria_groups if 'expected' in str(g.get('result') or g.get('abundance', '')).lower())
            slightly = sum(1 for g in bacteria_groups if 'slightly' in str(g.get('result') or g.get('abundance', '')).lower())
            deviating = sum(1 for g in bacteria_groups if 'deviating' in str(g.get('result') or g.get('abundance', '')).lower() and 'slightly' not in str(g.get('result') or g.get('abundance', '')).lower())
            
            stats_data = [
                ['✅ Attendus (Expected)', str(expected)],
                ['⚠️ Légèrement déviants', str(slightly)],
                ['🔴 Déviants', str(deviating)]
            ]
            
            stats_table = Table(stats_data, colWidths=[10*cm, 6*cm])
            stats_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (0,0), colors.HexColor('#d1fae5')),
                ('BACKGROUND', (0,1), (0,1), colors.HexColor('#fff7ed')),
                ('BACKGROUND', (0,2), (0,2), colors.HexColor('#fee2e2')),
                ('FONT', (0,0), (-1,-1), 'Helvetica-Bold', 11),
                ('ALIGN', (1,0), (1,-1), 'CENTER'),
                ('GRID', (0,0), (-1,-1), 1, colors.grey),
                ('PADDING', (0,0), (-1,-1), 10)
            ]))
            
            story.append(stats_table)
            story.append(Spacer(1, 0.8*cm))
            
            # Détails des groupes
            story.append(Paragraph("Détails par groupe:", heading3_style))
            story.append(Spacer(1, 0.3*cm))
            
            groups_data = [['Catégorie', 'Nom du groupe', 'Résultat']]
            
            for grp in bacteria_groups:
                category = grp.get('category', 'N/A')
                name = grp.get('name', grp.get('group', 'N/A'))[:60]
                result = grp.get('result') or grp.get('abundance', 'N/A')
                groups_data.append([category, name, result])
            
            groups_table = Table(groups_data, colWidths=[2*cm, 10*cm, 4*cm])
            groups_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#a855f7')),
                ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                ('FONT', (0,0), (-1,0), 'Helvetica-Bold', 10),
                ('FONT', (0,1), (-1,-1), 'Helvetica', 9),
                ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#faf5ff')]),
                ('ALIGN', (0,0), (0,-1), 'CENTER'),
                ('ALIGN', (2,0), (2,-1), 'CENTER'),
                ('PADDING', (0,0), (-1,-1), 8),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE')
            ]))
            
            story.append(groups_table)
            story.append(PageBreak())
        
        # ✅ BACTÉRIES INDIVIDUELLES (bacteria_individual)
        bacteria_individual = microbiome_data.get('bacteria_individual', [])
        
        if bacteria_individual:
            story.append(Paragraph("🔬 BACTÉRIES INDIVIDUELLES (48 SOUCHES)", subtitle_style))
            story.append(Spacer(1, 0.5*cm))
            
            # Stats
            normal = sum(1 for b in bacteria_individual if b.get('status') == 'Normal')
            abnormal = len(bacteria_individual) - normal
            
            story.append(Paragraph(
                f"<b>{len(bacteria_individual)} bactéries</b> analysées : "
                f"<font color='#10b981'>{normal} normales</font>, "
                f"<font color='#ef4444'>{abnormal} anormales</font>",
                normal_justify
            ))
            story.append(Spacer(1, 0.5*cm))
            
            # Tableau des bactéries anormales
            abnormal_bacteria = [b for b in bacteria_individual if b.get('status') != 'Normal']
            
            if abnormal_bacteria:
                story.append(Paragraph(f"⚠️ BACTÉRIES ANORMALES À SURVEILLER ({len(abnormal_bacteria)})", heading3_style))
                story.append(Spacer(1, 0.3*cm))
                
                abnormal_data = [['ID', 'Nom', 'Catégorie', 'Niveau', 'Statut']]
                
                for b in abnormal_bacteria:
                    abnormal_data.append([
                        b.get('id', '')[:5],
                        b.get('name', 'N/A')[:45],
                        b.get('category', '')[:5],
                        str(b.get('abundance_level', 0)),
                        b.get('status', '')[:20]
                    ])
                
                abnormal_table = Table(abnormal_data, colWidths=[1.5*cm, 8*cm, 2*cm, 2*cm, 3*cm])
                abnormal_table.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#ef4444')),
                    ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                    ('FONT', (0,0), (-1,0), 'Helvetica-Bold', 9),
                    ('FONT', (0,1), (-1,-1), 'Helvetica', 8),
                    ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                    ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#fee2e2')]),
                    ('ALIGN', (0,0), (0,-1), 'CENTER'),
                    ('ALIGN', (2,0), (-1,-1), 'CENTER'),
                    ('PADDING', (0,0), (-1,-1), 6),
                    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                    ('FONTSIZE', (0,1), (-1,-1), 7)
                ]))
                
                story.append(abnormal_table)
                story.append(Spacer(1, 0.5*cm))
            
            # Tableau TOUTES les bactéries (version compacte)
            story.append(Paragraph("LISTE COMPLÈTE DES 48 BACTÉRIES", heading3_style))
            story.append(Spacer(1, 0.3*cm))
            
            all_bacteria_data = [['ID', 'Nom', 'Cat', 'Niv', 'Statut']]
            
            for b in bacteria_individual:
                all_bacteria_data.append([
                    b.get('id', '')[:5],
                    b.get('name', 'N/A')[:40],
                    b.get('category', '')[:4],
                    str(b.get('abundance_level', 0)),
                    b.get('status', '')[:15]
                ])
            
            all_bacteria_table = Table(all_bacteria_data, colWidths=[1.2*cm, 9*cm, 1.5*cm, 1.5*cm, 3.3*cm])
            all_bacteria_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#6b7280')),
                ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                ('FONT', (0,0), (-1,0), 'Helvetica-Bold', 8),
                ('FONT', (0,1), (-1,-1), 'Helvetica', 7),
                ('GRID', (0,0), (-1,-1), 0.25, colors.lightgrey),
                ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f9fafb')]),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('PADDING', (0,0), (-1,-1), 4),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('FONTSIZE', (0,1), (-1,-1), 6)
            ]))
            
            story.append(all_bacteria_table)
            story.append(PageBreak())
        
        # Biomarqueurs de selles (si présents)
        stool_biomarkers = microbiome_data.get('stool_biomarkers', {})
        
        if stool_biomarkers:
            story.append(Paragraph("💊 BIOMARQUEURS DES SELLES", heading3_style))
            story.append(Spacer(1, 0.5*cm))
            
            for name, data in stool_biomarkers.items():
                value = data.get('value')
                unit = data.get('unit', '')
                reference = data.get('reference', '')
                status = data.get('status', 'Normal')
                
                viz = create_biomarker_visualization(name, value, unit, reference, status)
                story.append(viz)
                story.append(Spacer(1, 0.3*cm))
            
            story.append(PageBreak())
    
    # ==================== PAGE: RECOMMANDATIONS ====================
    if recommendations:
        story.append(Paragraph("💊 RECOMMANDATIONS PERSONNALISÉES", subtitle_style))
        story.append(Spacer(1, 0.5*cm))
        
        def create_reco_section(title, items, bg_color, border_color, icon="•"):
            """Crée une section de recommandations stylée"""
            if not items:
                return []
            
            elements = []
            elements.append(Paragraph(title, heading3_style))
            elements.append(Spacer(1, 0.2*cm))
            
            reco_data = [[f"{icon} {item}"] for item in items]
            reco_table = Table(reco_data, colWidths=[15.5*cm])
            reco_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), bg_color),
                ('FONT', (0,0), (-1,-1), 'Helvetica', 10),
                ('LEFTPADDING', (0,0), (-1,-1), 15),
                ('RIGHTPADDING', (0,0), (-1,-1), 15),
                ('TOPPADDING', (0,0), (-1,-1), 10),
                ('BOTTOMPADDING', (0,0), (-1,-1), 10),
                ('BOX', (0,0), (-1,-1), 2, border_color),
                ('LINEBELOW', (0,0), (-1,-2), 0.5, colors.HexColor('#e5e7eb')),
                ('VALIGN', (0,0), (-1,-1), 'TOP')
            ]))
            
            elements.append(reco_table)
            elements.append(Spacer(1, 0.8*cm))
            
            return elements
        
        # 🔥 Prioritaires
        story.extend(create_reco_section(
            "🔥 ACTIONS PRIORITAIRES",
            recommendations.get('Prioritaires', []),
            colors.HexColor('#fee2e2'),
            colors.HexColor('#ef4444'),
            "⚠️"
        ))
        
        # ⚠️ À surveiller
        story.extend(create_reco_section(
            "⚠️ À SURVEILLER",
            recommendations.get('À surveiller', []),
            colors.HexColor('#fff7ed'),
            colors.HexColor('#f59e0b'),
            "•"
        ))
        
        # 🥗 Nutrition
        story.extend(create_reco_section(
            "🥗 NUTRITION & DIÉTÉTIQUE",
            recommendations.get('Nutrition', []),
            colors.HexColor('#f0fdf4'),
            colors.HexColor('#22c55e'),
            "•"
        ))
        
        # 💊 Micronutrition
        story.extend(create_reco_section(
            "💊 MICRONUTRITION",
            recommendations.get('Micronutrition', []),
            colors.HexColor('#eff6ff'),
            colors.HexColor('#3b82f6'),
            "•"
        ))
        
        # 🏃 Hygiène de vie
        story.extend(create_reco_section(
            "🏃 HYGIÈNE DE VIE",
            recommendations.get('Hygiène de vie', []),
            colors.HexColor('#faf5ff'),
            colors.HexColor('#a855f7'),
            "•"
        ))
        
        # 🔬 Examens complémentaires
        story.extend(create_reco_section(
            "🔬 EXAMENS COMPLÉMENTAIRES",
            recommendations.get('Examens complémentaires', []),
            colors.HexColor('#f8f9fa'),
            colors.HexColor('#6b7280'),
            "•"
        ))
        
        # 📅 Suivi
        story.extend(create_reco_section(
            "📅 PLAN DE SUIVI",
            recommendations.get('Suivi', []),
            colors.HexColor('#f8f9fa'),
            colors.HexColor('#6b7280'),
            "•"
        ))
        
        story.append(PageBreak())
    
    # ==================== PAGE FINALE: CONTACT ====================
    story.append(Spacer(1, 3*cm))
    
    if os.path.exists(DEFAULT_LOGO):
        try:
            logo = Image(DEFAULT_LOGO, width=4*cm, height=4*cm, kind='proportional')
            story.append(logo)
        except:
            pass
    
    story.append(Spacer(1, 1*cm))
    
    contact_text = """
    <para align=center>
    <b><font size=14 color='#1a5490'>UNILABS © 2026</font></b><br/>
    <font size=11>Powered by Unilabs Group</font><br/><br/>
    <b><font size=12>Dr Thibault SUTTER, PhD</font></b><br/>
    <font size=10>Biologiste spécialisé en biologie fonctionnelle</font><br/>
    <font size=10>Product Manager - Functional Biology</font><br/>
    <font size=10>Espace Lab SA (Unilabs Group)</font><br/><br/>
    <font size=9>📍 Geneva, Switzerland</font><br/>
    <font size=9>🌐 bilan-hormonal.com | ALGO-LIFE</font><br/><br/>
    <i><font size=8 color='#6b7280'>Ce rapport est généré par analyse multimodale basée sur un système de règles.<br/>
    Il ne remplace pas un avis médical personnalisé.</font></i>
    </para>
    """
    
    story.append(Paragraph(contact_text, styles['Normal']))
    
    # ==================== GÉNÉRATION PDF ====================
    doc.build(story)
    print(f"✅ PDF généré avec succès: {output_path}")
    print(f"📄 Taille: {os.path.getsize(output_path) / 1024:.1f} KB")
    
    return output_path


# Alias pour compatibilité
generate_report = generate_multimodal_report


if __name__ == "__main__":
    print("=" * 70)
    print("PDF Generator v2.0 FINAL chargé")
    print("Compatible avec app.py v13 et extractors v19")
    print("=" * 70)
    print("✅ Templates biomarqueurs complets avec barres de progression")
    print("✅ Support bacteria_groups ET bacteria_individual")
    print("✅ Visualisations des 48 bactéries")
    print("✅ Design professionnel avec couleurs")
    print("=" * 70)
