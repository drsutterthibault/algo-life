#!/usr/bin/env python3
"""
PDF Generator COMPATIBLE avec app.py v11.0
Structure: microbiome_data contient 'bacteria' directement
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
from reportlab.lib.enums import TA_CENTER

# LOGO
DEFAULT_LOGO = "/dna_logo.png"

def _safe_float(x):
    try:
        if x is None or str(x).strip() == '':
            return None
        return float(str(x).strip().replace(',', '.').replace(' ', ''))
    except:
        return None

def generate_multimodal_report(
    patient_data, biology_data, microbiome_data,
    recommendations, cross_analysis, follow_up,
    bio_age_result=None, output_path=None
):
    """
    Génère le rapport PDF - Compatible app.py v11.0
    
    microbiome_data structure attendue:
    {
        'dysbiosis_index': 3,
        'diversity': 'as expected',
        'bacteria': [  # ← IMPORTANT : 'bacteria' pas 'bacteria_groups'
            {
                'category': 'A1',
                'group': 'Prominent gut microbes...',
                'result': 'Expected',
                'status': '● Normal'  # ← peut aussi être 'abundance'
            }
        ]
    }
    """
    
    if output_path is None:
        import tempfile
        output_path = os.path.join(tempfile.gettempdir(), 'rapport.pdf')
    
    # PDF
    doc = SimpleDocTemplate(output_path, pagesize=A4, 
                           leftMargin=2*cm, rightMargin=2*cm,
                           topMargin=2*cm, bottomMargin=2.5*cm)
    
    story = []
    styles = getSampleStyleSheet()
    
    # Styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1a5490'),
        spaceAfter=20,
        alignment=TA_CENTER
    )
    
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#1a5490'),
        spaceAfter=12
    )
    
    # ==================== PAGE 1: GARDE ====================
    # LOGO
    if os.path.exists(DEFAULT_LOGO):
        try:
            logo = Image(DEFAULT_LOGO, width=4*cm, height=4*cm, kind='proportional')
            story.append(logo)
            story.append(Spacer(1, 1*cm))
            print("✓ Logo ajouté à la page de garde")
        except Exception as e:
            print(f"⚠ Erreur logo: {e}")
    
    # Titre
    story.append(Paragraph("Rapport d'Analyses Biologiques", title_style))
    story.append(Paragraph("UNILABS - Biologie Fonctionnelle", styles['Normal']))
    story.append(Spacer(1, 2*cm))
    
    # Patient
    patient_table = Table([
        ['PATIENT', patient_data.get('name', 'N/A')],
        ['SEXE', patient_data.get('sex', 'N/A')],
        ['DATE NAISSANCE', str(patient_data.get('birthdate', 'N/A'))]
    ], colWidths=[5*cm, 10*cm])
    
    patient_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f3f4f6')),
        ('FONT', (0,0), (0,-1), 'Helvetica-Bold', 10),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('PADDING', (0,0), (-1,-1), 10)
    ]))
    
    story.append(patient_table)
    story.append(PageBreak())
    
    # ==================== PAGE 2: BIOMARQUEURS ====================
    if biology_data:
        story.append(Paragraph("Biomarqueurs", subtitle_style))
        story.append(Spacer(1, 0.5*cm))
        
        # Résumé
        normaux = sum(1 for b in biology_data if b.get('Statut') == 'Normal')
        anormaux = sum(1 for b in biology_data if b.get('Statut') in ['Élevé', 'Bas'])
        
        summary_table = Table([
            ['✅ Normaux', str(normaux)],
            ['⚠ Anormaux', str(anormaux)]
        ], colWidths=[8*cm, 4*cm])
        
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (0,0), colors.HexColor('#d1fae5')),
            ('BACKGROUND', (0,1), (0,1), colors.HexColor('#fee2e2')),
            ('FONT', (0,0), (-1,-1), 'Helvetica-Bold', 14),
            ('ALIGN', (1,0), (1,-1), 'CENTER'),
            ('PADDING', (0,0), (-1,-1), 15),
            ('GRID', (0,0), (-1,-1), 1, colors.grey)
        ]))
        
        story.append(summary_table)
        story.append(Spacer(1, 1*cm))
        
        # Liste biomarqueurs (premiers 15)
        for bio in biology_data[:15]:
            txt = f"{bio.get('Biomarqueur')}: {bio.get('Valeur')} {bio.get('Unité')} ({bio.get('Statut')})"
            story.append(Paragraph(txt, styles['Normal']))
            story.append(Spacer(1, 0.2*cm))
        
        story.append(PageBreak())
    
    # ==================== PAGE 3: MICROBIOTE ====================
    # ✅ IMPORTANT : Détecter 'bacteria' directement (structure app.py)
    bacteria_list = None
    
    if microbiome_data:
        # Essayer différentes clés possibles
        if 'bacteria' in microbiome_data and isinstance(microbiome_data['bacteria'], list):
            bacteria_list = microbiome_data['bacteria']
            print(f"✓ Microbiome trouvé : {len(bacteria_list)} bactéries dans 'bacteria'")
        elif 'bacteria_groups' in microbiome_data and isinstance(microbiome_data['bacteria_groups'], list):
            bacteria_list = microbiome_data['bacteria_groups']
            print(f"✓ Microbiome trouvé : {len(bacteria_list)} bactéries dans 'bacteria_groups'")
    
    if bacteria_list:
        story.append(Paragraph("Analyse Microbiote", subtitle_style))
        story.append(Spacer(1, 0.5*cm))
        
        # Indices
        di = microbiome_data.get('dysbiosis_index', 'N/A')
        div = microbiome_data.get('diversity', 'N/A')
        
        indices_table = Table([
            ['Indice de dysbiose (DI)', str(di)],
            ['Diversité', str(div)]
        ], colWidths=[8*cm, 7*cm])
        
        indices_table.setStyle(TableStyle([
            ('FONT', (0,0), (0,-1), 'Helvetica-Bold', 10),
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f3f4f6')),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('PADDING', (0,0), (-1,-1), 10)
        ]))
        
        story.append(indices_table)
        story.append(Spacer(1, 0.8*cm))
        
        # Séparer normaux et anormaux
        # ✅ Chercher dans 'status' OU 'result' car structure peut varier
        normal_bact = []
        abnormal_bact = []
        
        for b in bacteria_list:
            # Récupérer le statut (peut être 'status' ou dedans 'result')
            status = b.get('status', '')
            result = b.get('result', '')
            
            # Normaliser pour détecter
            is_normal = ('● Normal' in status) or ('Normal' in status) or (result == 'Expected')
            
            if is_normal:
                normal_bact.append(b)
            else:
                abnormal_bact.append(b)
        
        print(f"✓ Répartition : {len(normal_bact)} normaux, {len(abnormal_bact)} anormaux")
        
        # ===== TABLEAU RÉCAPITULATIF =====
        story.append(Paragraph("RÉCAPITULATIF DES SOUCHES", styles['Heading3']))
        story.append(Spacer(1, 0.3*cm))
        
        recap_data = [
            ['Type de souches', 'Nombre', 'État'],
            ['Souches normales', str(len(normal_bact)), '✓ Bon'],
            ['Souches anormales / à surveiller', str(len(abnormal_bact)), '⚠ Attention' if abnormal_bact else '✓ Bon']
        ]
        
        recap_table = Table(recap_data, colWidths=[8*cm, 3*cm, 4*cm])
        recap_table.setStyle(TableStyle([
            # En-tête bleu
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1a5490')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONT', (0,0), (-1,0), 'Helvetica-Bold', 12),
            # Ligne normales
            ('BACKGROUND', (0,1), (0,1), colors.HexColor('#d1fae5')),
            ('TEXTCOLOR', (0,1), (0,1), colors.HexColor('#059669')),
            # Ligne anormales
            ('BACKGROUND', (0,2), (0,2), colors.HexColor('#fee2e2') if abnormal_bact else colors.HexColor('#d1fae5')),
            ('TEXTCOLOR', (0,2), (0,2), colors.red if abnormal_bact else colors.HexColor('#059669')),
            # Style général
            ('FONT', (0,1), (-1,-1), 'Helvetica', 11),
            ('FONT', (1,1), (-1,-1), 'Helvetica-Bold', 14),
            ('GRID', (0,0), (-1,-1), 1.5, colors.grey),
            ('ALIGN', (1,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('PADDING', (0,0), (-1,-1), 12),
            ('BOX', (0,0), (-1,-1), 2, colors.HexColor('#1a5490'))
        ]))
        
        story.append(recap_table)
        story.append(Spacer(1, 1*cm))
        
        print("✓ Tableau récapitulatif microbiote ajouté")
        
        # ===== DÉTAILS NORMAUX =====
        if normal_bact:
            story.append(Paragraph(f"Souches normales ({len(normal_bact)})", styles['Heading3']))
            story.append(Spacer(1, 0.3*cm))
            
            normal_data = [['Groupe bactérien', 'Résultat', 'Statut']]
            for b in normal_bact[:20]:  # Max 20
                group_name = b.get('group', b.get('category', 'N/A'))
                result = b.get('result', 'Expected')
                normal_data.append([
                    group_name[:80],  # Tronquer
                    result,
                    '● Normal'
                ])
            
            normal_table = Table(normal_data, colWidths=[10*cm, 3*cm, 2.5*cm])
            normal_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.green),
                ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                ('FONT', (0,0), (-1,0), 'Helvetica-Bold', 10),
                ('FONT', (0,1), (-1,-1), 'Helvetica', 8),
                ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f0fdf4')]),
                ('ALIGN', (1,0), (-1,-1), 'CENTER'),
                ('PADDING', (0,0), (-1,-1), 8),
                ('BOX', (0,0), (-1,-1), 1.5, colors.green)
            ]))
            
            story.append(normal_table)
            story.append(Spacer(1, 1*cm))
            print(f"✓ Tableau détails normaux ajouté ({len(normal_bact)} souches)")
        
        # ===== DÉTAILS ANORMAUX =====
        if abnormal_bact:
            story.append(Paragraph(f"Souches anormales / à surveiller ({len(abnormal_bact)})", styles['Heading3']))
            story.append(Spacer(1, 0.3*cm))
            
            abnormal_data = [['Groupe bactérien', 'Résultat', 'Statut']]
            for b in abnormal_bact:
                group_name = b.get('group', b.get('category', 'N/A'))
                result = b.get('result', 'Deviating')
                status = b.get('status', '⚠ Anormal')
                abnormal_data.append([
                    group_name[:80],
                    result,
                    status[:20]
                ])
            
            abnormal_table = Table(abnormal_data, colWidths=[10*cm, 3*cm, 2.5*cm])
            abnormal_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.red),
                ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                ('FONT', (0,0), (-1,0), 'Helvetica-Bold', 10),
                ('FONT', (0,1), (-1,-1), 'Helvetica', 8),
                ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#fee2e2')]),
                ('ALIGN', (1,0), (-1,-1), 'CENTER'),
                ('PADDING', (0,0), (-1,-1), 8),
                ('BOX', (0,0), (-1,-1), 1.5, colors.red)
            ]))
            
            story.append(abnormal_table)
            print(f"✓ Tableau détails anormaux ajouté ({len(abnormal_bact)} souches)")
        
        story.append(PageBreak())
    
    # ==================== PAGE 4: RECOMMANDATIONS ====================
    if recommendations:
        story.append(Paragraph("Recommandations", subtitle_style))
        story.append(Spacer(1, 0.5*cm))
        
        for key, items in recommendations.items():
            if items and isinstance(items, list):
                story.append(Paragraph(key.upper(), styles['Heading3']))
                for item in items[:5]:  # Max 5 par catégorie
                    story.append(Paragraph(f"• {item}", styles['Normal']))
                    story.append(Spacer(1, 0.2*cm))
                story.append(Spacer(1, 0.5*cm))
        
        story.append(PageBreak())
    
    # ==================== DERNIÈRE PAGE: LOGO ====================
    story.append(Spacer(1, 3*cm))
    
    if os.path.exists(DEFAULT_LOGO):
        try:
            logo = Image(DEFAULT_LOGO, width=4*cm, height=4*cm, kind='proportional')
            story.append(logo)
            print("✓ Logo ajouté à la page finale")
        except:
            pass
    
    story.append(Spacer(1, 1*cm))
    
    contact = """
    <para align=center>
    <b>UNILABS © 2026</b><br/>
    Powered by Unilabs Group<br/><br/>
    <b>Dr Thibault SUTTER, PhD</b><br/>
    Biologiste spécialisé en biologie fonctionnelle<br/>
    Unilabs<br/><br/>
    ● Genève, Suisse
    </para>
    """
    
    story.append(Paragraph(contact, styles['Normal']))
    
    # GÉNÉRER
    doc.build(story)
    print(f"✅ PDF généré: {output_path}")
    return output_path

# Alias
generate_report = generate_multimodal_report

if __name__ == "__main__":
    print("Module PDF chargé - Compatible app.py v11.0")
    print("Structure microbiome: {'bacteria': [...]}")
