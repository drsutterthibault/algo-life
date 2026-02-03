"""
ALGO-LIFE / UNILABS - Générateur PDF Simplifié v11.0
✅ Structure claire et cohérente avec l'UI
✅ Recommandations segmentées comme dans l'interface
✅ Support multimodal (Bio + Microbiote + Cross-analysis)
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Dict, Any, List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)


# =====================================================================
# COLORS
# =====================================================================
PRIMARY = colors.HexColor("#0A4D8C")
ACCENT = colors.HexColor("#00ACC1")
NORMAL = colors.HexColor("#4CAF50")
WARNING = colors.HexColor("#FF9800")
CRITICAL = colors.HexColor("#F44336")
GREY = colors.HexColor("#757575")
LIGHT_GREY = colors.HexColor("#F5F5F5")


# =====================================================================
# HELPERS
# =====================================================================
def _safe_str(x: Any) -> str:
    return "" if x is None else str(x)


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        return float(x)
    except Exception:
        return default


# =====================================================================
# PDF GENERATOR
# =====================================================================
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
    Génère un rapport PDF multimodal
    
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
    
    # Configuration document
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )
    
    # Styles
    styles = getSampleStyleSheet()
    
    style_title = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=PRIMARY,
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    style_section = ParagraphStyle(
        'SectionTitle',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=PRIMARY,
        spaceBefore=20,
        spaceAfter=10,
        borderWidth=0,
        borderColor=PRIMARY,
        borderPadding=5
    )
    
    style_subsection = ParagraphStyle(
        'Subsection',
        parent=styles['Heading3'],
        fontSize=13,
        textColor=ACCENT,
        spaceBefore=15,
        spaceAfter=8
    )
    
    style_body = ParagraphStyle(
        'BodyText',
        parent=styles['BodyText'],
        fontSize=10,
        leading=14,
        alignment=TA_JUSTIFY
    )
    
    story = []
    
    # ═════════════════════════════════════════════════════════════════
    # PAGE DE GARDE
    # ═════════════════════════════════════════════════════════════════
    story.append(Spacer(1, 2*cm))
    story.append(Paragraph("UNILABS", style_title))
    story.append(Paragraph("ALGO-LIFE", style_title))
    story.append(Spacer(1, 1*cm))
    story.append(Paragraph(
        "Analyse Multimodale de Biologie Fonctionnelle",
        ParagraphStyle('Subtitle', parent=styles['Normal'], fontSize=14, alignment=TA_CENTER, textColor=GREY)
    ))
    story.append(Spacer(1, 3*cm))
    
    # Informations patient
    patient_info = [
        ["Nom:", _safe_str(patient_data.get("name", ""))],
        ["Âge:", f"{patient_data.get('age', '')} ans"],
        ["Sexe:", _safe_str(patient_data.get("sex", ""))],
        ["Date du rapport:", datetime.now().strftime("%d/%m/%Y")]
    ]
    
    patient_table = Table(patient_info, colWidths=[5*cm, 10*cm])
    patient_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    
    story.append(patient_table)
    story.append(Spacer(1, 1*cm))
    story.append(Paragraph(
        "Dr Thibault SUTTER, PhD<br/>Biologiste spécialisé en biologie fonctionnelle<br/>UNILABS Group",
        ParagraphStyle('Footer', parent=styles['Normal'], fontSize=9, alignment=TA_CENTER, textColor=GREY)
    ))
    story.append(Spacer(1, 1*cm))
    story.append(Paragraph(
        "<b>CONFIDENTIEL - Usage médical uniquement</b>",
        ParagraphStyle('Confidential', parent=styles['Normal'], fontSize=10, alignment=TA_CENTER, textColor=CRITICAL)
    ))
    
    story.append(PageBreak())
    
    # ═════════════════════════════════════════════════════════════════
    # BIOLOGIE
    # ═════════════════════════════════════════════════════════════════
    if biology_data:
        story.append(Paragraph("■ ANALYSE BIOLOGIQUE", style_section))
        story.append(Spacer(1, 0.5*cm))
        
        story.append(Paragraph(
            "Cette section présente l'analyse détaillée de vos biomarqueurs biologiques. "
            "Chaque paramètre est évalué par rapport à ses valeurs de référence optimales.",
            style_body
        ))
        story.append(Spacer(1, 0.5*cm))
        
        # Statistiques
        normal_count = len([b for b in biology_data if b.get("status") == "Normal"])
        low_count = len([b for b in biology_data if b.get("status") == "Bas"])
        high_count = len([b for b in biology_data if b.get("status") == "Élevé"])
        
        stats_data = [
            ["Normaux", "Bas", "Élevés", "Total"],
            [str(normal_count), str(low_count), str(high_count), str(len(biology_data))]
        ]
        
        stats_table = Table(stats_data, colWidths=[4*cm, 4*cm, 4*cm, 4*cm])
        stats_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, GREY),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        story.append(stats_table)
        story.append(Spacer(1, 0.5*cm))
        
        # Tableau des anomalies prioritaires
        anomalies = [b for b in biology_data if b.get("status") in ["Bas", "Élevé"]]
        
        if anomalies:
            story.append(Paragraph("Biomarqueurs Anormaux", style_subsection))
            
            bio_table_data = [
                [Paragraph("<b>Biomarqueur</b>", style_body),
                 Paragraph("<b>Valeur</b>", style_body),
                 Paragraph("<b>Unité</b>", style_body),
                 Paragraph("<b>Référence</b>", style_body),
                 Paragraph("<b>Statut</b>", style_body)]
            ]
            
            for bio in anomalies[:15]:  # Limiter à 15 pour la place
                status_color = CRITICAL if bio.get("status") == "Élevé" else WARNING
                bio_table_data.append([
                    Paragraph(_safe_str(bio.get("biomarker")), style_body),
                    Paragraph(_safe_str(bio.get("value")), style_body),
                    Paragraph(_safe_str(bio.get("unit")), style_body),
                    Paragraph(_safe_str(bio.get("reference")), style_body),
                    Paragraph(f'<font color="{status_color.hexval()}">{bio.get("status")}</font>', style_body)
                ])
            
            bio_table = Table(bio_table_data, colWidths=[5*cm, 2*cm, 2*cm, 3.5*cm, 2.5*cm])
            bio_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('GRID', (0, 0), (-1, -1), 0.5, GREY),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, LIGHT_GREY]),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            
            story.append(bio_table)
        
        story.append(PageBreak())
    
    # ═════════════════════════════════════════════════════════════════
    # MICROBIOME
    # ═════════════════════════════════════════════════════════════════
    if microbiome_data:
        story.append(Paragraph("■ ANALYSE DU MICROBIOTE INTESTINAL", style_section))
        story.append(Spacer(1, 0.5*cm))
        
        story.append(Paragraph(
            "Cette section présente l'analyse de votre microbiote intestinal (GutMAP). "
            "L'équilibre de votre flore intestinale est un facteur clé de votre santé globale.",
            style_body
        ))
        story.append(Spacer(1, 0.5*cm))
        
        # Scores globaux
        di = microbiome_data.get("dysbiosis_index")
        diversity = microbiome_data.get("diversity")
        
        if di or diversity:
            story.append(Paragraph("Scores Globaux", style_subsection))
            
            scores_data = []
            if di:
                scores_data.append(["Indice de Dysbiose", f"{di}/5", "(1=Normal, 5=Sévère)"])
            if diversity:
                scores_data.append(["Diversité Bactérienne", diversity, ""])
            
            scores_table = Table(scores_data, colWidths=[6*cm, 4*cm, 6*cm])
            scores_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ]))
            
            story.append(scores_table)
            story.append(Spacer(1, 0.5*cm))
        
        # Groupes bactériens
        bacteria = microbiome_data.get("bacteria", [])
        if bacteria:
            story.append(Paragraph("Groupes Bactériens Analysés", style_subsection))
            
            bact_data = [
                [Paragraph("<b>Catégorie</b>", style_body),
                 Paragraph("<b>Groupe</b>", style_body),
                 Paragraph("<b>Résultat</b>", style_body)]
            ]
            
            for b in bacteria:
                result = b.get("result", "")
                result_icon = "✓" if result == "Expected" else "■" if "Slightly" in result else "●"
                result_color = NORMAL if result == "Expected" else WARNING if "Slightly" in result else CRITICAL
                
                bact_data.append([
                    Paragraph(_safe_str(b.get("category")), style_body),
                    Paragraph(_safe_str(b.get("group"))[:80], style_body),  # Tronquer si trop long
                    Paragraph(f'<font color="{result_color.hexval()}">{result_icon} {result}</font>', style_body)
                ])
            
            bact_table = Table(bact_data, colWidths=[2*cm, 10*cm, 4*cm])
            bact_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('GRID', (0, 0), (-1, -1), 0.5, GREY),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, LIGHT_GREY]),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            
            story.append(bact_table)
        
        story.append(PageBreak())
    
    # ═════════════════════════════════════════════════════════════════
    # ANALYSES CROISÉES
    # ═════════════════════════════════════════════════════════════════
    if cross_analysis:
        story.append(Paragraph("■ ANALYSE CROISÉE MULTIMODALE", style_section))
        story.append(Spacer(1, 0.5*cm))
        
        story.append(Paragraph(
            "Cette section présente les corrélations identifiées entre vos données biologiques et votre microbiote, "
            "permettant une approche intégrée et personnalisée de votre santé.",
            style_body
        ))
        story.append(Spacer(1, 0.5*cm))
        
        for ca in cross_analysis:
            story.append(Paragraph(ca.get("title", ""), style_subsection))
            story.append(Paragraph(ca.get("description", ""), style_body))
            
            ca_reco = ca.get("recommendations", [])
            if ca_reco:
                for reco in ca_reco:
                    story.append(Paragraph(f"• {reco}", style_body))
            
            story.append(Spacer(1, 0.3*cm))
        
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
        
        warning_style = ParagraphStyle(
            'Warning',
            parent=style_body,
            backColor=colors.HexColor("#FFF3E0"),
            borderColor=WARNING,
            borderWidth=1,
            borderPadding=10
        )
        story.append(Paragraph(
            "<b>⚠️ Important:</b> Ces suggestions ne remplacent pas un avis médical. "
            "Consultez votre médecin avant toute nouvelle supplémentation.",
            warning_style
        ))
        story.append(Spacer(1, 0.5*cm))
        
        # Sections de recommandations
        sections = [
            ("Prioritaires", "🔥"),
            ("À surveiller", "⚠️"),
            ("Nutrition", "🥗"),
            ("Micronutrition", "💊"),
            ("Hygiène de vie", "🏃"),
            ("Examens complémentaires", "🔬"),
            ("Suivi", "📅")
        ]
        
        for section_name, icon in sections:
            items = recommendations.get(section_name, [])
            if not items:
                continue
            
            story.append(Paragraph(f"{icon} <b>{section_name}</b>", style_subsection))
            story.append(Spacer(1, 0.2*cm))
            
            for item in items:
                story.append(Paragraph(f"• {item}", style_body))
                story.append(Spacer(1, 0.1*cm))
            
            story.append(Spacer(1, 0.3*cm))
    
    # ═════════════════════════════════════════════════════════════════
    # PLAN DE SUIVI
    # ═════════════════════════════════════════════════════════════════
    if follow_up:
        story.append(PageBreak())
        story.append(Paragraph("■ PLAN DE SUIVI RECOMMANDÉ", style_section))
        story.append(Spacer(1, 0.5*cm))
        
        next_date = follow_up.get("next_date")
        if next_date:
            story.append(Paragraph(f"<b>Prochain contrôle:</b> {next_date}", style_body))
            story.append(Spacer(1, 0.3*cm))
        
        next_tests = follow_up.get("next_tests", [])
        if next_tests:
            story.append(Paragraph("<b>Biomarqueurs à recontrôler:</b>", style_body))
            for test in next_tests:
                story.append(Paragraph(f"• {test}", style_body))
            story.append(Spacer(1, 0.3*cm))
        
        objectives = follow_up.get("objectives", "")
        if objectives:
            story.append(Paragraph("<b>Objectifs mesurables:</b>", style_body))
            story.append(Paragraph(objectives, style_body))
    
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
        textColor=GREY
    )
    
    story.append(Paragraph("ALGO-LIFE © 2026", footer_style))
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
    
    # Build PDF
    doc.build(story)
    
    return output_path
