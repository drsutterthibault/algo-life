#!/usr/bin/env python3
"""
PDF Generator - COMPATIBLE AVEC RULES_ENGINE v10 + APP.PY v12
✅ Extraction correcte depuis consolidated_recommendations
✅ Templates bio conservés
✅ Tableaux microbiote complets
✅ Analyses croisées du rules_engine
✅ Détection automatique IA
"""

import os
import re
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.graphics.shapes import Drawing, Rect, String, Circle
from datetime import datetime

try:
    import streamlit as st
    STREAMLIT_AVAILABLE = True
except ImportError:
    STREAMLIT_AVAILABLE = False

DEFAULT_LOGO = "/dna_logo.png"

def _safe_float(x):
    try:
        if x is None or str(x).strip() == '':
            return None
        val_str = str(x).strip().replace(',', '.').replace(' ', '')
        val_str = re.sub(r'[^\d\.\-]', '', val_str)
        return float(val_str) if val_str else None
    except:
        return None

def _parse_reference(ref_str):
    if not ref_str or str(ref_str).strip() == '':
        return None, None, None
    
    ref = str(ref_str).strip()
    
    match = re.search(r'(\d+\.?\d*)\s*[-—–]\s*(\d+\.?\d*)', ref)
    if match:
        return _safe_float(match.group(1)), _safe_float(match.group(2)), 'range'
    
    match = re.search(r'[<≤]\s*(\d+\.?\d*)', ref)
    if match:
        return None, _safe_float(match.group(1)), 'max'
    
    match = re.search(r'[>≥]\s*(\d+\.?\d*)', ref)
    if match:
        return _safe_float(match.group(1)), None, 'min'
    
    return None, None, None

def create_biomarker_visualization(name, value, unit, reference, status, width=480, height=70):
    d = Drawing(width, height)
    
    if status in ['Normal', 'normal']:
        color, bg_color = colors.HexColor('#10b981'), colors.HexColor('#d1fae5')
    elif status in ['Élevé', 'Elevé', 'élevé', 'elevé', 'High', 'high']:
        color, bg_color = colors.HexColor('#ef4444'), colors.HexColor('#fee2e2')
    elif status in ['Bas', 'bas', 'Low', 'low']:
        color, bg_color = colors.HexColor('#f59e0b'), colors.HexColor('#fef3c7')
    else:
        color, bg_color = colors.HexColor('#6b7280'), colors.HexColor('#f3f4f6')
    
    d.add(Rect(0, 0, width, height, fillColor=bg_color, strokeColor=None))
    d.add(String(10, height - 15, name[:60], fontSize=11, fillColor=colors.HexColor('#1f2937'), fontName='Helvetica-Bold'))
    
    value_str = f"{value} {unit}" if value is not None else "N/A"
    d.add(String(10, height - 35, value_str, fontSize=12, fillColor=color, fontName='Helvetica-Bold'))
    
    status_x = width - 80
    d.add(Rect(status_x, height - 38, 70, 16, fillColor=color, strokeColor=None))
    d.add(String(status_x + 5, height - 35, status, fontSize=9, fillColor=colors.white, fontName='Helvetica-Bold'))
    
    if reference and str(reference).strip():
        d.add(String(10, 8, f"Réf: {reference}", fontSize=8, fillColor=colors.HexColor('#6b7280')))
    
    min_val, max_val, ref_type = _parse_reference(reference)
    
    if ref_type == 'range' and min_val is not None and max_val is not None:
        bar_x, bar_y, bar_width, bar_height = 150, 8, 300, 10
        d.add(Rect(bar_x, bar_y, bar_width, bar_height, fillColor=colors.HexColor('#e5e7eb'), strokeColor=colors.HexColor('#d1d5db')))
        d.add(Rect(bar_x, bar_y, bar_width, bar_height, fillColor=colors.HexColor('#d1fae5'), strokeColor=None, fillOpacity=0.3))
        
        try:
            value_float = _safe_float(value)
            if value_float is not None and max_val > min_val:
                position = (value_float - min_val) / (max_val - min_val)
                position = max(-0.1, min(1.1, position))
            else:
                position = 0.5
        except:
            position = 0.5
        
        marker_x = bar_x + (bar_width * max(0, min(1, position)))
        d.add(Circle(marker_x, bar_y + bar_height/2, 7, fillColor=color, strokeColor=colors.white, strokeWidth=2))
        d.add(String(bar_x - 5, bar_y - 2, str(min_val), fontSize=7, fillColor=colors.HexColor('#6b7280'), textAnchor='end'))
        d.add(String(bar_x + bar_width + 5, bar_y - 2, str(max_val), fontSize=7, fillColor=colors.HexColor('#6b7280')))
    
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
    Génère le rapport PDF - COMPATIBLE RULES_ENGINE v10
    
    Parameters:
    - recommendations: Dict retourné par rules_engine.generate_consolidated_recommendations()
                      Structure attendue: {"Prioritaires": [...], "À surveiller": [...], ...}
    - cross_analysis: Liste retournée par rules_engine (dans consolidated["cross_analysis"])
    """
    
    # Détection automatique IA
    ai_enrichment = None
    if STREAMLIT_AVAILABLE and hasattr(st, 'session_state'):
        if st.session_state.get('ai_enrichment_active') and st.session_state.get('ai_enrichment_output'):
            ai_enrichment = st.session_state.ai_enrichment_output
    
    if output_path is None:
        import tempfile
        output_path = os.path.join(tempfile.gettempdir(), 'rapport_unilabs.pdf')
    
    doc = SimpleDocTemplate(output_path, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm, topMargin=2*cm, bottomMargin=2.5*cm)
    
    story = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=26, textColor=colors.HexColor('#1a5490'), spaceAfter=20, alignment=TA_CENTER, fontName='Helvetica-Bold')
    subtitle_style = ParagraphStyle('Subtitle', parent=styles['Heading2'], fontSize=18, textColor=colors.HexColor('#1a5490'), spaceAfter=15, spaceBefore=10, fontName='Helvetica-Bold')
    heading3_style = ParagraphStyle('Heading3Custom', parent=styles['Heading3'], fontSize=14, textColor=colors.HexColor('#1f2937'), spaceAfter=10, spaceBefore=8, fontName='Helvetica-Bold')
    normal_justify = ParagraphStyle('NormalJustify', parent=styles['Normal'], alignment=TA_JUSTIFY, fontSize=10, leading=14)
    
    # PAGE DE GARDE
    if os.path.exists(DEFAULT_LOGO):
        try:
            logo = Image(DEFAULT_LOGO, width=5*cm, height=5*cm, kind='proportional')
            story.append(logo)
            story.append(Spacer(1, 1*cm))
        except:
            pass
    
    story.append(Paragraph("RAPPORT D'ANALYSES BIOLOGIQUES", title_style))
    story.append(Paragraph("Biologie Fonctionnelle & Microbiote", styles['Normal']))
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph("<b>UNILABS</b> - Laboratoire Central de Suisse Romande", ParagraphStyle('Center', parent=styles['Normal'], alignment=TA_CENTER, fontSize=11)))
    story.append(Spacer(1, 2*cm))
    
    # Info patient
    patient_table_data = [
        ['PATIENT', patient_data.get('name', 'N/A')],
        ['SEXE', patient_data.get('sex', 'N/A')],
        ['DATE DE NAISSANCE', str(patient_data.get('birthdate', 'N/A'))],
        ['ÂGE', f"{patient_data.get('age', 'N/A')} ans"],
    ]
    
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
    story.append(Paragraph(f"<i>Rapport généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}</i>", ParagraphStyle('ItalicCenter', parent=styles['Normal'], alignment=TA_CENTER, fontSize=9, textColor=colors.HexColor('#6b7280'))))
    story.append(PageBreak())
    
    # SOMMAIRE
    story.append(Paragraph("📋 SOMMAIRE DU RAPPORT", subtitle_style))
    story.append(Spacer(1, 0.5*cm))
    
    sommaire_data = [
        ['SECTION', 'PAGE'],
        ['1. Résultats Biologie', '3'],
        ['2. Âge Biologique', '—' if not bio_age_result else '5'],
        ['3. Analyse Microbiote', '6'],
        ['4. Analyses Croisées Multimodales', '10'],
        ['5. Recommandations (Système de Règles)', '12'],
    ]
    
    if ai_enrichment:
        sommaire_data.append(['6. Recommandations IA Enrichies', '15'])
        sommaire_data.append(['7. Plan de Suivi', '17'])
    else:
        sommaire_data.append(['6. Plan de Suivi', '15'])
    
    sommaire_table = Table(sommaire_data, colWidths=[13*cm, 3*cm])
    sommaire_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1a5490')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONT', (0,0), (-1,0), 'Helvetica-Bold', 11),
        ('FONT', (0,1), (-1,-1), 'Helvetica', 10),
        ('GRID', (0,0), (-1,-1), 1, colors.grey),
        ('ALIGN', (1,0), (1,-1), 'CENTER'),
        ('PADDING', (0,0), (-1,-1), 10),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8f9fa')])
    ]))
    
    story.append(sommaire_table)
    story.append(PageBreak())
    
    # BIOMARQUEURS
    if biology_data:
        story.append(Paragraph("🧪 RÉSULTATS BIOLOGIE", subtitle_style))
        story.append(Spacer(1, 0.5*cm))
        
        total = len(biology_data)
        normaux = sum(1 for b in biology_data if b.get('Statut') in ['Normal', 'normal'])
        eleves = sum(1 for b in biology_data if b.get('Statut') in ['Élevé', 'Elevé', 'élevé', 'elevé'])
        bas = sum(1 for b in biology_data if b.get('Statut') in ['Bas', 'bas'])
        
        summary_table_data = [
            ['📊 RÉSUMÉ', ''],
            ['Total biomarqueurs analysés', str(total)],
            ['✅ Normaux', str(normaux)],
            ['⬆️ Élevés', str(eleves)],
            ['⬇️ Bas', str(bas)],
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
        
        story.append(Paragraph("DÉTAILS DES BIOMARQUEURS", heading3_style))
        story.append(Spacer(1, 0.5*cm))
        
        for bio in biology_data:
            name = str(bio.get('Biomarqueur', 'N/A'))
            value = bio.get('Valeur')
            unit = str(bio.get('Unité', ''))
            status = bio.get('Statut', 'Normal')
            reference = bio.get('Référence', '')
            
            viz = create_biomarker_visualization(name, value, unit, reference, status)
            story.append(viz)
            story.append(Spacer(1, 0.3*cm))
        
        story.append(PageBreak())
    
    # ÂGE BIOLOGIQUE
    if bio_age_result:
        story.append(Paragraph("🧬 ÂGE BIOLOGIQUE (bFRAil Score)", subtitle_style))
        story.append(Spacer(1, 0.5*cm))
        
        bio_age = bio_age_result.get('bio_age', 0)
        chrono_age = patient_data.get('age', 0)
        diff = bio_age - chrono_age
        prob = bio_age_result.get('frailty_probability', 0)
        risk = bio_age_result.get('risk_category', 'N/A')
        
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
        story.append(Paragraph(f"<i>Votre âge biologique est de <b>{bio_age:.1f} ans</b>, soit une différence de <b>{diff:+.1f} ans</b> par rapport à votre âge chronologique. Probabilité de fragilité : <b>{prob:.1f}%</b> ({risk}).</i>", normal_justify))
        story.append(PageBreak())
    
    # MICROBIOME
    if microbiome_data:
        story.append(Paragraph("🦠 ANALYSE MICROBIOTE", subtitle_style))
        story.append(Spacer(1, 0.5*cm))
        
        di = microbiome_data.get('dysbiosis_index')
        diversity = microbiome_data.get('diversity', 'N/A')
        
        microbiome_summary_data = [
            ['📊 VUE D\'ENSEMBLE', ''],
            ['Indice de dysbiose (DI)', f"{di}/5" if di is not None else 'N/A'],
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
        
        bacteria_groups = microbiome_data.get('bacteria_groups', [])
        
        if bacteria_groups:
            story.append(Paragraph("GROUPES BACTÉRIENS ANALYSÉS", heading3_style))
            story.append(Spacer(1, 0.3*cm))
            
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
            
            story.append(Paragraph("TABLEAU COMPLET DES GROUPES:", heading3_style))
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
    
    # ANALYSES CROISÉES
    if cross_analysis:
        story.append(Paragraph("🔬 ANALYSES CROISÉES MULTIMODALES", subtitle_style))
        story.append(Spacer(1, 0.5*cm))
        
        story.append(Paragraph("<i>Cette section présente les analyses croisées générées par le système de règles expert.</i>", normal_justify))
        story.append(Spacer(1, 0.8*cm))
        
        for idx, analysis in enumerate(cross_analysis, 1):
            titre = analysis.get('title') or analysis.get('titre', 'Analyse croisée')
            story.append(Paragraph(f"{idx}. {titre}", heading3_style))
            story.append(Spacer(1, 0.3*cm))
            
            description = analysis.get('description', '')
            if description:
                desc_box = Table([[description]], colWidths=[15.5*cm])
                desc_box.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f9fafb')),
                    ('FONT', (0,0), (-1,-1), 'Helvetica', 10),
                    ('PADDING', (0,0), (-1,-1), 12),
                    ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#d1d5db')),
                    ('VALIGN', (0,0), (-1,-1), 'TOP')
                ]))
                story.append(desc_box)
                story.append(Spacer(1, 0.5*cm))
            
            reco_list = analysis.get('recommendations', [])
            if reco_list:
                story.append(Paragraph("<b>💊 Recommandations associées:</b>", ParagraphStyle('BoldSmall', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10)))
                story.append(Spacer(1, 0.2*cm))
                
                reco_items = [[f"• {reco}"] for reco in reco_list]
                reco_table = Table(reco_items, colWidths=[15.5*cm])
                reco_table.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,-1), colors.white),
                    ('FONT', (0,0), (-1,-1), 'Helvetica', 9),
                    ('LEFTPADDING', (0,0), (-1,-1), 20),
                    ('TOPPADDING', (0,0), (-1,-1), 6),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                    ('LINEBELOW', (0,0), (-1,-2), 0.25, colors.HexColor('#e5e7eb')),
                    ('VALIGN', (0,0), (-1,-1), 'TOP')
                ]))
                story.append(reco_table)
            
            severity = analysis.get('severity', 'info')
            if severity == 'critical':
                bg, fg, text = colors.HexColor('#fee2e2'), colors.HexColor('#991b1b'), '⚠️ CRITIQUE'
            elif severity == 'warning':
                bg, fg, text = colors.HexColor('#fff7ed'), colors.HexColor('#9a3412'), '⚠️ ATTENTION'
            else:
                bg, fg, text = colors.HexColor('#eff6ff'), colors.HexColor('#1e40af'), 'ℹ️ INFO'
            
            story.append(Spacer(1, 0.3*cm))
            severity_table = Table([[f"NIVEAU: {text}"]], colWidths=[16*cm])
            severity_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), bg),
                ('TEXTCOLOR', (0,0), (-1,-1), fg),
                ('FONT', (0,0), (-1,-1), 'Helvetica-Bold', 10),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('PADDING', (0,0), (-1,-1), 8),
                ('BOX', (0,0), (-1,-1), 2, fg)
            ]))
            story.append(severity_table)
            story.append(Spacer(1, 1*cm))
        
        story.append(PageBreak())
    
    # RECOMMANDATIONS SYSTÈME
    # CRITICAL: recommendations est un DICT pas une liste
    if recommendations and isinstance(recommendations, dict):
        story.append(Paragraph("💊 RECOMMANDATIONS PERSONNALISÉES", subtitle_style))
        story.append(Paragraph("(Générées par le Système de Règles)", ParagraphStyle('Subtitle2', parent=styles['Normal'], fontSize=12, textColor=colors.HexColor('#6b7280'), alignment=TA_CENTER)))
        story.append(Spacer(1, 0.5*cm))
        
        def create_reco_section(title, items, bg_color, border_color, icon="•"):
            if not items or not isinstance(items, list):
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
                ('TOPPADDING', (0,0), (-1,-1), 10),
                ('BOTTOMPADDING', (0,0), (-1,-1), 10),
                ('BOX', (0,0), (-1,-1), 2, border_color),
                ('LINEBELOW', (0,0), (-1,-2), 0.5, colors.HexColor('#e5e7eb')),
                ('VALIGN', (0,0), (-1,-1), 'TOP')
            ]))
            
            elements.append(reco_table)
            elements.append(Spacer(1, 0.8*cm))
            
            return elements
        
        story.extend(create_reco_section("🔥 ACTIONS PRIORITAIRES", recommendations.get('Prioritaires', []), colors.HexColor('#fee2e2'), colors.HexColor('#ef4444'), "⚠️"))
        story.extend(create_reco_section("⚠️ À SURVEILLER", recommendations.get('À surveiller', []), colors.HexColor('#fff7ed'), colors.HexColor('#f59e0b'), "•"))
        story.extend(create_reco_section("🥗 NUTRITION & DIÉTÉTIQUE", recommendations.get('Nutrition', []), colors.HexColor('#f0fdf4'), colors.HexColor('#22c55e'), "•"))
        story.extend(create_reco_section("💊 MICRONUTRITION", recommendations.get('Micronutrition', []), colors.HexColor('#eff6ff'), colors.HexColor('#3b82f6'), "•"))
        story.extend(create_reco_section("🏃 HYGIÈNE DE VIE", recommendations.get('Hygiène de vie', []), colors.HexColor('#faf5ff'), colors.HexColor('#a855f7'), "•"))
        story.extend(create_reco_section("🔬 EXAMENS COMPLÉMENTAIRES", recommendations.get('Examens complémentaires', []), colors.HexColor('#f8f9fa'), colors.HexColor('#6b7280'), "•"))
        story.extend(create_reco_section("📅 PLAN DE SUIVI", recommendations.get('Suivi', []), colors.HexColor('#f8f9fa'), colors.HexColor('#6b7280'), "•"))
        
        story.append(PageBreak())
    
    # RECOMMANDATIONS IA (SI DÉTECTÉ)
    if ai_enrichment:
        story.append(Paragraph("🤖 RECOMMANDATIONS IA ENRICHIES", subtitle_style))
        story.append(Paragraph("(Personnalisées par Intelligence Artificielle)", ParagraphStyle('Subtitle2', parent=styles['Normal'], fontSize=12, textColor=colors.HexColor('#6b7280'), alignment=TA_CENTER)))
        story.append(Spacer(1, 0.5*cm))
        
        synthese = ai_enrichment.get('synthese_enrichie', '')
        if synthese:
            synthese_box = Table([[synthese]], colWidths=[15.5*cm])
            synthese_box.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#eff6ff')),
                ('FONT', (0,0), (-1,-1), 'Helvetica', 10),
                ('PADDING', (0,0), (-1,-1), 15),
                ('BOX', (0,0), (-1,-1), 2, colors.HexColor('#3b82f6')),
                ('VALIGN', (0,0), (-1,-1), 'TOP')
            ]))
            story.append(Paragraph("📋 SYNTHÈSE PERSONNALISÉE", heading3_style))
            story.append(Spacer(1, 0.2*cm))
            story.append(synthese_box)
            story.append(Spacer(1, 0.8*cm))
        
        contexte = ai_enrichment.get('contexte_applique', '')
        if contexte:
            story.append(Paragraph(f"<i>🎯 Personnalisation : {contexte}</i>", ParagraphStyle('ItalicSmall', parent=styles['Normal'], fontSize=9, textColor=colors.HexColor('#6b7280'))))
            story.append(Spacer(1, 0.5*cm))
        
        nutrition_ia = ai_enrichment.get('nutrition_enrichie', [])
        if nutrition_ia:
            story.append(Paragraph("🥗 NUTRITION PERSONNALISÉE (IA)", heading3_style))
            story.append(Spacer(1, 0.3*cm))
            
            nutrition_data = [[f"{i}. {item}"] for i, item in enumerate(nutrition_ia, 1)]
            nutrition_table = Table(nutrition_data, colWidths=[15.5*cm])
            nutrition_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f0fdf4')),
                ('FONT', (0,0), (-1,-1), 'Helvetica', 10),
                ('PADDING', (0,0), (-1,-1), 12),
                ('BOX', (0,0), (-1,-1), 2, colors.HexColor('#22c55e')),
                ('LINEBELOW', (0,0), (-1,-2), 0.5, colors.HexColor('#d1fae5')),
                ('VALIGN', (0,0), (-1,-1), 'TOP')
            ]))
            story.append(nutrition_table)
            story.append(Spacer(1, 1*cm))
        
        micronutrition_ia = ai_enrichment.get('micronutrition_enrichie', [])
        if micronutrition_ia:
            story.append(Paragraph("💊 MICRONUTRITION EXPERTE (IA)", heading3_style))
            story.append(Spacer(1, 0.3*cm))
            
            micronutrition_data = [[f"{i}. {item}"] for i, item in enumerate(micronutrition_ia, 1)]
            micronutrition_table = Table(micronutrition_data, colWidths=[15.5*cm])
            micronutrition_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#eff6ff')),
                ('FONT', (0,0), (-1,-1), 'Helvetica', 10),
                ('PADDING', (0,0), (-1,-1), 12),
                ('BOX', (0,0), (-1,-1), 2, colors.HexColor('#3b82f6')),
                ('LINEBELOW', (0,0), (-1,-2), 0.5, colors.HexColor('#dbeafe')),
                ('VALIGN', (0,0), (-1,-1), 'TOP')
            ]))
            story.append(micronutrition_table)
            story.append(Spacer(1, 1*cm))
        
        story.append(PageBreak())
    
    # PLAN DE SUIVI
    if follow_up:
        story.append(Paragraph("📅 PLAN DE SUIVI", subtitle_style))
        story.append(Spacer(1, 0.5*cm))
        
        next_date = follow_up.get('next_date')
        plan = follow_up.get('plan', '')
        objectives = follow_up.get('objectives', '')
        
        if next_date:
            story.append(Paragraph(f"<b>Date du prochain contrôle :</b> {next_date}", styles['Normal']))
            story.append(Spacer(1, 0.5*cm))
        
        if plan:
            story.append(Paragraph("<b>Plan détaillé :</b>", heading3_style))
            story.append(Spacer(1, 0.2*cm))
            story.append(Paragraph(plan, normal_justify))
            story.append(Spacer(1, 0.5*cm))
        
        if objectives:
            story.append(Paragraph("<b>Objectifs mesurables :</b>", heading3_style))
            story.append(Spacer(1, 0.2*cm))
            story.append(Paragraph(objectives, normal_justify))
        
        story.append(PageBreak())
    
    # PAGE FINALE
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
    <i><font size=8 color='#6b7280'>Ce rapport est généré par analyse multimodale (système de règles + IA).<br/>
    Il ne remplace pas un avis médical personnalisé.</font></i>
    </para>
    """
    
    story.append(Paragraph(contact_text, styles['Normal']))
    
    doc.build(story)
    
    file_size = os.path.getsize(output_path) / 1024
    print(f"✅ PDF généré: {output_path}")
    print(f"📄 Taille: {file_size:.1f} KB")
    
    # Debug recommandations
    if recommendations:
        total_reco = sum(len(v) if isinstance(v, list) else 0 for v in recommendations.values())
        print(f"📋 Recommandations incluses: {total_reco}")
    
    if ai_enrichment:
        print("🤖 IA détectée et incluse")
    
    return output_path

# Alias
generate_report = generate_multimodal_report

if __name__ == "__main__":
    print("=" * 70)
    print("PDF Generator - COMPATIBLE RULES_ENGINE v10 + APP.PY v12")
    print("=" * 70)
    print("✅ Extraction correcte depuis consolidated_recommendations")
    print("✅ Templates bio conservés")
    print("✅ Tableaux microbiote complets")
    print("✅ Analyses croisées du rules_engine")
    print("✅ Détection automatique IA")
    print("=" * 70)
