"""
ALGO-LIFE PDF Generator - Version Compatible v4.0
Compatible avec app_improved.py

Auteur: Dr Thibault SUTTER
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from io import BytesIO
from datetime import datetime


def generate_algolife_pdf_report(
    patient_data,
    biomarker_results,
    engine_results=None,
    chart_buffer=None,
    health_score=None,
    biological_age=None,
    nutritional_needs=None,
    recommendations=None
):
    """
    Génère un rapport PDF professionnel ALGO-LIFE v4.0
    
    Compatible avec les nouvelles structures de données
    """
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=20*mm,
        bottomMargin=20*mm,
        leftMargin=20*mm,
        rightMargin=20*mm
    )
    
    story = []
    styles = getSampleStyleSheet()
    
    # ===== STYLES PERSONNALISÉS =====
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=28,
        textColor=colors.HexColor('#667eea'),
        spaceAfter=10,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=14,
        textColor=colors.HexColor('#4A5568'),
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName='Helvetica'
    )
    
    heading2_style = ParagraphStyle(
        'CustomHeading2',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#2C3E50'),
        spaceAfter=12,
        spaceBefore=20,
        fontName='Helvetica-Bold'
    )
    
    heading3_style = ParagraphStyle(
        'CustomHeading3',
        parent=styles['Heading3'],
        fontSize=13,
        textColor=colors.HexColor('#34495E'),
        spaceAfter=8,
        spaceBefore=12,
        fontName='Helvetica-Bold'
    )
    
    # ===== PAGE 1: EN-TÊTE =====
    
    story.append(Paragraph("🧬 ALGO-LIFE", title_style))
    story.append(Paragraph(
        "Rapport d'Analyses Biologiques<br/>Analyse Multimodale de Santé",
        subtitle_style
    ))
    story.append(Spacer(1, 10))
    
    # ===== INFORMATIONS PATIENT =====
    
    patient_info = patient_data.get('patient_info', {})
    
    story.append(Paragraph("Informations Patient", heading2_style))
    
    patient_table_data = [
        ['PATIENT', patient_info.get('nom', '—')],
        ['GENRE', patient_info.get('sexe', '—')],
        ['ÂGE', f"{patient_info.get('age', '—')} ans"],
        ['DATE DE NAISSANCE', patient_info.get('date_naissance', '—')],
        ['IMC', f"{patient_info.get('imc', '—')}" if patient_info.get('imc') else '—'],
        ['DATE DU RAPPORT', datetime.now().strftime('%d/%m/%Y')]
    ]
    
    patient_table = Table(patient_table_data, colWidths=[70*mm, 90*mm])
    patient_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f3f4f6')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')
    ]))
    
    story.append(patient_table)
    story.append(Spacer(1, 20))
    
    # ===== CONTEXTE CLINIQUE =====
    
    story.append(Paragraph("Contexte Clinique", heading2_style))
    
    # Vérifier s'il y a des symptômes
    symptoms = patient_data.get('symptoms', [])
    if symptoms:
        for symptom in symptoms:
            story.append(Paragraph(f"• {symptom}", styles['Normal']))
    else:
        story.append(Paragraph("Aucun symptôme renseigné", styles['Normal']))
    
    story.append(Spacer(1, 20))
    
    # ===== SCORES PRINCIPAUX =====
    
    story.append(Paragraph("Âge Biologique & Score Santé", heading2_style))
    
    if biological_age and health_score:
        
        # Tableau des scores
        scores_data = [
            ['Métrique', 'Valeur', 'Interprétation'],
            ['Âge Biologique', 
             f"{biological_age['biological_age']} ans",
             biological_age['status']],
            ['Âge Chronologique', 
             f"{biological_age['chronological_age']} ans",
             '—'],
            ['Delta', 
             f"{biological_age['delta']:+.1f} ans ({biological_age['delta_percent']:+.1f}%)",
             ''],
            ['', '', ''],
            ['Score Santé Global', 
             f"{health_score['global_score']:.1f}/100",
             health_score['grade_label']],
            ['Grade', 
             health_score['grade'],
             '']
        ]
        
        scores_table = Table(scores_data, colWidths=[60*mm, 50*mm, 50*mm])
        scores_table.setStyle(TableStyle([
            # En-tête
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            # Âge biologique
            ('BACKGROUND', (0, 1), (-1, 3), colors.HexColor('#dbeafe')),
            # Séparateur
            ('BACKGROUND', (0, 4), (-1, 4), colors.white),
            ('LINEBELOW', (0, 4), (-1, 4), 0, colors.white),
            # Score santé
            ('BACKGROUND', (0, 5), (-1, 6), colors.HexColor('#d1fae5')),
            # Général
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')
        ]))
        
        story.append(scores_table)
        story.append(Spacer(1, 15))
        
        # Interprétation
        story.append(Paragraph(
            f"<i>{biological_age['interpretation']}</i>",
            styles['Normal']
        ))
        story.append(Spacer(1, 5))
        story.append(Paragraph(
            f"<i>{health_score['interpretation']}</i>",
            styles['Normal']
        ))
    
    else:
        story.append(Paragraph(
            "Les scores ne sont pas disponibles. Analyse incomplète.",
            styles['Normal']
        ))
    
    story.append(Spacer(1, 20))
    
    # ===== RÉSUMÉ BIOMARQUEURS =====
    
    story.append(Paragraph("Résumé Global des Biomarqueurs", heading2_style))
    
    # Classifier les biomarqueurs
    try:
        # Import local pour éviter les dépendances circulaires
        import sys
        import os
        
        # Essayer d'importer depuis le fichier amélioré
        try:
            from app_improved import BiomarkerDatabase
        except:
            # Fallback : classification simple
            BiomarkerDatabase = None
        
        if BiomarkerDatabase:
            normaux = []
            a_surveiller = []
            anormaux = []
            
            for biomarker_key, value in biomarker_results.items():
                classification = BiomarkerDatabase.classify_biomarker(
                    biomarker_key, value,
                    patient_info.get('age'),
                    patient_info.get('sexe')
                )
                
                if classification['status'] in ['optimal', 'normal']:
                    normaux.append((biomarker_key, value))
                elif classification['status'] in ['insufficient', 'low', 'elevated']:
                    a_surveiller.append((biomarker_key, value))
                else:
                    anormaux.append((biomarker_key, value))
            
            summary_data = [
                ['Catégorie', 'Nombre', 'Pourcentage'],
                ['✅ Normaux', str(len(normaux)), f"{len(normaux)/len(biomarker_results)*100:.0f}%"],
                ['⚡ À surveiller', str(len(a_surveiller)), f"{len(a_surveiller)/len(biomarker_results)*100:.0f}%"],
                ['⚠️ Anormaux', str(len(anormaux)), f"{len(anormaux)/len(biomarker_results)*100:.0f}%"]
            ]
        else:
            # Classification basique sans BiomarkerDatabase
            total = len(biomarker_results)
            summary_data = [
                ['Catégorie', 'Nombre', 'Pourcentage'],
                ['Total Biomarqueurs', str(total), '100%']
            ]
            normaux = []
            a_surveiller = []
            anormaux = []
    except Exception as e:
        summary_data = [
            ['Erreur', 'Classification non disponible', '—']
        ]
        normaux = []
        a_surveiller = []
        anormaux = []
    
    summary_table = Table(summary_data, colWidths=[60*mm, 50*mm, 50*mm])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')
    ]))
    
    story.append(summary_table)
    story.append(Spacer(1, 20))
    
    # ===== PAGE BREAK =====
    story.append(PageBreak())
    
    # ===== BIOMARQUEURS DÉTAILLÉS =====
    
    story.append(Paragraph("Biomarqueurs Détaillés", heading2_style))
    
    # Biomarqueurs anormaux
    if anormaux:
        story.append(Paragraph("⚠️ Biomarqueurs Anormaux (Action Requise)", heading3_style))
        
        anormaux_data = [['Biomarqueur', 'Valeur']]
        for bio, val in anormaux[:10]:  # Max 10
            anormaux_data.append([
                bio.replace('_', ' ').title(),
                f"{val:.2f}" if isinstance(val, float) else str(val)
            ])
        
        anormaux_table = Table(anormaux_data, colWidths=[100*mm, 60*mm])
        anormaux_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#fee2e2')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#991b1b')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
        ]))
        
        story.append(anormaux_table)
        story.append(Spacer(1, 15))
    
    # Biomarqueurs à surveiller
    if a_surveiller:
        story.append(Paragraph("⚡ Biomarqueurs À Surveiller", heading3_style))
        
        surveiller_data = [['Biomarqueur', 'Valeur']]
        for bio, val in a_surveiller[:10]:  # Max 10
            surveiller_data.append([
                bio.replace('_', ' ').title(),
                f"{val:.2f}" if isinstance(val, float) else str(val)
            ])
        
        surveiller_table = Table(surveiller_data, colWidths=[100*mm, 60*mm])
        surveiller_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#fef3c7')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#92400e')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
        ]))
        
        story.append(surveiller_table)
        story.append(Spacer(1, 15))
    
    # ===== BESOINS NUTRITIONNELS =====
    
    if nutritional_needs:
        story.append(Paragraph("Besoins Nutritionnels Calculés", heading2_style))
        
        nutri_data = [
            ['Métrique', 'Valeur'],
            ['Métabolisme de Base (BMR)', f"{nutritional_needs['bmr']:.0f} kcal/jour"],
            ['Dépense Énergétique Totale (DET)', f"{nutritional_needs['det']:.0f} kcal/jour"],
            ['Protéines', f"{nutritional_needs['proteins_g']:.0f} g/jour"],
            ['Lipides', f"{nutritional_needs['lipids_g']:.0f} g/jour"],
            ['Glucides', f"{nutritional_needs['carbs_g']:.0f} g/jour"]
        ]
        
        nutri_table = Table(nutri_data, colWidths=[100*mm, 60*mm])
        nutri_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BACKGROUND', (0, 1), (0, -1), colors.HexColor('#f3f4f6')),
            ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
        ]))
        
        story.append(nutri_table)
        story.append(Spacer(1, 20))
    
    # ===== PAGE BREAK =====
    story.append(PageBreak())
    
    # ===== RECOMMANDATIONS =====
    
    if recommendations:
        story.append(Paragraph("💡 Recommandations Personnalisées", heading2_style))
        
        recs = recommendations.get('recommendations', {})
        
        # Priorités
        priorities = recommendations.get('priorities', [])
        if priorities:
            story.append(Paragraph("⚠️ Priorités d'Action", heading3_style))
            
            for i, priority in enumerate(priorities[:5], 1):
                biomarker_name = priority['biomarker'].replace('_', ' ').title()
                value = priority['value']
                priority_level = priority['priority']
                
                story.append(Paragraph(
                    f"<b>{i}. {biomarker_name}</b> - Priorité: {priority_level}",
                    styles['Normal']
                ))
                story.append(Paragraph(
                    f"&nbsp;&nbsp;&nbsp;&nbsp;Valeur: {value}",
                    styles['Normal']
                ))
                story.append(Spacer(1, 5))
        
        story.append(Spacer(1, 15))
        
        # Suppléments
        if recs.get('supplements'):
            story.append(Paragraph("💊 Micronutrition Ciblée", heading3_style))
            for supp in recs['supplements'][:8]:  # Max 8
                story.append(Paragraph(f"• {supp}", styles['Normal']))
            story.append(Spacer(1, 12))
        
        # Alimentation
        if recs.get('alimentation'):
            story.append(Paragraph("🥗 Alimentation & Nutrition", heading3_style))
            for alim in recs['alimentation'][:8]:  # Max 8
                story.append(Paragraph(f"• {alim}", styles['Normal']))
            story.append(Spacer(1, 12))
        
        # Lifestyle
        if recs.get('lifestyle'):
            story.append(Paragraph("🏃 Optimisation du Mode de Vie", heading3_style))
            for life in recs['lifestyle'][:8]:  # Max 8
                story.append(Paragraph(f"• {life}", styles['Normal']))
    
    # ===== PLAN DE SUIVI =====
    
    story.append(Spacer(1, 30))
    story.append(Paragraph("Plan de Suivi Recommandé", heading2_style))
    
    story.append(Paragraph("<b>Prochain contrôle:</b> 3-6 mois", styles['Normal']))
    story.append(Spacer(1, 5))
    
    if anormaux:
        story.append(Paragraph("<b>Biomarqueurs à recontrôler:</b>", styles['Normal']))
        for bio, _ in anormaux[:5]:
            story.append(Paragraph(f"• {bio.replace('_', ' ').title()}", styles['Normal']))
    
    # ===== FOOTER =====
    
    story.append(Spacer(1, 50))
    
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.grey,
        alignment=TA_CENTER
    )
    
    story.append(Paragraph("_______________________________________________", footer_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph("Rapport établi par Dr Thibault SUTTER - Biologiste", footer_style))
    story.append(Paragraph("Product Manager Functional Biology, Espace Lab SA (Unilabs Group)", footer_style))
    story.append(Paragraph("ALGO-LIFE | Plateforme Multimodale d'Analyse de Santé", footer_style))
    story.append(Spacer(1, 5))
    story.append(Paragraph("© 2026 ALGO-LIFE - Document médical confidentiel", footer_style))
    story.append(Paragraph("contact@bilan-hormonal.com | https://bilan-hormonal.com", footer_style))
    
    # ===== BUILD PDF =====
    
    doc.build(story)
    buffer.seek(0)
    
    return buffer


# ===== FONCTION DE TEST =====

if __name__ == "__main__":
    # Test basique
    print("Module algolife_pdf_generator_compatible.py chargé avec succès!")
    print("Compatible avec app_improved.py v4.0")
