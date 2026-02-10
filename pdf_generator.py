#!/usr/bin/env python3
"""
PDF Generator v3.0 ULTIMATE - Rapport Complet Multimodal
Compatible avec app.py v13 et extractors v19

✅ Analyses complètes 15-20 pages
✅ Extraction robuste
✅ Recommandations automatiques  
✅ Analyses croisées multimodales DÉTAILLÉES
✅ Export professionnel prêt pour le patient
✅ Toutes les visualisations
"""

import os
import re
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image, KeepTogether, Flowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.graphics.shapes import Drawing, Rect, String, Circle, Line
from datetime import datetime

# LOGO
DEFAULT_LOGO = "/dna_logo.png"

def _safe_float(x):
    """Conversion sécurisée en float"""
    try:
        if x is None or str(x).strip() == '':
            return None
        val_str = str(x).strip().replace(',', '.').replace(' ', '')
        val_str = re.sub(r'[^\d\.\-]', '', val_str)
        return float(val_str) if val_str else None
    except:
        return None


def _parse_reference(ref_str):
    """Parse une référence type '0.70 — 1.05' ou '< 50' ou '> 10'"""
    if not ref_str or str(ref_str).strip() == '':
        return None, None, None
    
    ref = str(ref_str).strip()
    
    # Type 1: Plage
    match = re.search(r'(\d+\.?\d*)\s*[-—–]\s*(\d+\.?\d*)', ref)
    if match:
        min_val = _safe_float(match.group(1))
        max_val = _safe_float(match.group(2))
        return min_val, max_val, 'range'
    
    # Type 2: Limite supérieure
    match = re.search(r'[<≤]\s*(\d+\.?\d*)', ref)
    if match:
        max_val = _safe_float(match.group(1))
        return None, max_val, 'max'
    
    # Type 3: Limite inférieure
    match = re.search(r'[>≥]\s*(\d+\.?\d*)', ref)
    if match:
        min_val = _safe_float(match.group(1))
        return min_val, None, 'min'
    
    return None, None, None


def create_biomarker_visualization(name, value, unit, reference, status, width=480, height=70):
    """Crée une visualisation COMPLÈTE pour un biomarqueur avec barre de progression"""
    d = Drawing(width, height)
    
    # Couleur selon statut
    if status in ['Normal', 'normal']:
        color = colors.HexColor('#10b981')
        bg_color = colors.HexColor('#d1fae5')
    elif status in ['Élevé', 'Elevé', 'élevé', 'elevé', 'High', 'high']:
        color = colors.HexColor('#ef4444')
        bg_color = colors.HexColor('#fee2e2')
    elif status in ['Bas', 'bas', 'Low', 'low']:
        color = colors.HexColor('#f59e0b')
        bg_color = colors.HexColor('#fef3c7')
    else:
        color = colors.HexColor('#6b7280')
        bg_color = colors.HexColor('#f3f4f6')
    
    # Fond coloré
    d.add(Rect(0, 0, width, height, fillColor=bg_color, strokeColor=None))
    
    # Nom du biomarqueur
    d.add(String(10, height - 15, name[:60], 
                 fontSize=11, fillColor=colors.HexColor('#1f2937'), 
                 fontName='Helvetica-Bold'))
    
    # Valeur + Unité
    value_str = f"{value} {unit}" if value is not None else "N/A"
    d.add(String(10, height - 35, value_str, 
                 fontSize=12, fillColor=color, 
                 fontName='Helvetica-Bold'))
    
    # Statut badge
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
    
    # Barre de progression
    if ref_type == 'range' and min_val is not None and max_val is not None:
        bar_x, bar_y, bar_width, bar_height = 150, 8, 300, 10
        
        # Fond gris
        d.add(Rect(bar_x, bar_y, bar_width, bar_height, 
                   fillColor=colors.HexColor('#e5e7eb'), strokeColor=colors.HexColor('#d1d5db')))
        
        # Zone normale
        d.add(Rect(bar_x, bar_y, bar_width, bar_height, 
                   fillColor=colors.HexColor('#d1fae5'), strokeColor=None, fillOpacity=0.3))
        
        # Position du marqueur
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
        
        # Marqueur circulaire
        d.add(Circle(marker_x, bar_y + bar_height/2, 7, 
                     fillColor=color, strokeColor=colors.white, strokeWidth=2))
        
        # Indicateurs min/max
        d.add(String(bar_x - 5, bar_y - 2, str(min_val), 
                     fontSize=7, fillColor=colors.HexColor('#6b7280'), textAnchor='end'))
        d.add(String(bar_x + bar_width + 5, bar_y - 2, str(max_val), 
                     fontSize=7, fillColor=colors.HexColor('#6b7280')))
    
    elif ref_type == 'max' and max_val is not None:
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


def compute_cross_analysis(biology_data, microbiome_data):
    """
    Génère des analyses croisées DÉTAILLÉES Biologie × Microbiome
    
    Returns:
        list: Liste de dict avec analyses croisées
    """
    if not biology_data or not microbiome_data:
        return []
    
    # Helper: Trouver un biomarqueur
    def get_biomarker(name_patterns):
        for bio in biology_data:
            bio_name = str(bio.get('Biomarqueur', '')).lower()
            for pattern in name_patterns:
                if pattern.lower() in bio_name:
                    return bio
        return None
    
    # Extraire données microbiome
    di = microbiome_data.get('dysbiosis_index')
    diversity = str(microbiome_data.get('diversity', '')).lower()
    bacteria_groups = microbiome_data.get('bacteria_groups', [])
    
    # Compter groupes anormaux
    deviating_groups = [g for g in bacteria_groups 
                       if 'deviating' in str(g.get('result') or g.get('abundance', '')).lower()]
    
    analyses = []
    
    # ===== ANALYSE 1: INFLAMMATION × DYSBIOSE =====
    crp = get_biomarker(['crp', 'c-reactive', 'proteine c'])
    if crp and crp.get('Statut') in ['Élevé', 'Elevé']:
        if di and di >= 3:
            analyses.append({
                'titre': '🔥 INFLAMMATION SYSTÉMIQUE + DYSBIOSE',
                'signal_bio': f"CRP élevée ({crp.get('Valeur')} {crp.get('Unité')})",
                'signal_micro': f"Dysbiose sévère (DI {di}/5)",
                'interpretation': (
                    "La présence simultanée d'une inflammation systémique (CRP élevée) et d'une dysbiose "
                    "intestinale suggère un lien bidirectionnel. Le déséquilibre du microbiote peut contribuer "
                    "à l'inflammation via la perméabilité intestinale et les lipopolysaccharides bactériens (LPS). "
                    "Inversement, l'inflammation peut altérer le microbiote."
                ),
                'recommandations': [
                    "Optimiser le microbiote (probiotiques, prébiotiques)",
                    "Réduire l'inflammation (oméga-3, curcumine)",
                    "Réparer la barrière intestinale (L-glutamine, zinc)",
                    "Identifier et éliminer les facteurs pro-inflammatoires"
                ],
                'priorite': 'HAUTE'
            })
    
    # ===== ANALYSE 2: CARENCES MARTIALES × MICROBIOTE =====
    ferritine = get_biomarker(['ferritin', 'ferritine'])
    hemoglobine = get_biomarker(['hemoglobin', 'hémoglobine', 'hb'])
    
    if (ferritine and ferritine.get('Statut') == 'Bas') or (hemoglobine and hemoglobine.get('Statut') == 'Bas'):
        if di and di >= 3:
            analyses.append({
                'titre': '⚠️ CARENCES MARTIALES + DYSBIOSE',
                'signal_bio': f"Ferritine/Hb basses ({ferritine.get('Valeur') if ferritine else 'N/A'} / {hemoglobine.get('Valeur') if hemoglobine else 'N/A'})",
                'signal_micro': f"Dysbiose (DI {di}/5)",
                'interpretation': (
                    "Les carences martiales associées à une dysbiose peuvent indiquer : "
                    "(1) Une malabsorption liée à l'inflammation intestinale, "
                    "(2) Une compétition bactérienne pour le fer, "
                    "(3) Des micro-saignements digestifs non détectés. "
                    "La dysbiose peut réduire l'absorption du fer héminique et non héminique."
                ),
                'recommandations': [
                    "Bilan digestif approfondi (coloscopie si indiqué)",
                    "Supplémentation fer bisglycinate (mieux toléré)",
                    "Restauration microbiote",
                    "Vitamine C pour améliorer absorption",
                    "Contrôle ferritine/CRP à 3 mois"
                ],
                'priorite': 'HAUTE'
            })
    
    # ===== ANALYSE 3: VITAMINE D × IMMUNITÉ × MICROBIOTE =====
    vitd = get_biomarker(['vitamin d', '25(oh)', '25-oh', 'vitamine d'])
    if vitd and vitd.get('Statut') == 'Bas':
        if di and di >= 3:
            analyses.append({
                'titre': '☀️ HYPOVITAMINOSE D + DYSBIOSE',
                'signal_bio': f"Vitamine D basse ({vitd.get('Valeur')} {vitd.get('Unité')})",
                'signal_micro': f"Dysbiose (DI {di}/5) + diversité {diversity}",
                'interpretation': (
                    "La vitamine D joue un rôle crucial dans l'immunité et la régulation du microbiote. "
                    "Son déficit associé à une dysbiose crée un cercle vicieux : "
                    "la vitamine D basse fragilise la barrière intestinale et l'immunité locale, "
                    "ce qui favorise la dysbiose. Inversement, la dysbiose peut réduire la conversion "
                    "de la vitamine D en sa forme active."
                ),
                'recommandations': [
                    "Supplémentation vitamine D3 (dose selon niveau actuel)",
                    "Exposition solaire régulière",
                    "Optimisation microbiote en parallèle",
                    "Magnésium et vitamine K2 (cofacteurs)",
                    "Contrôle à 2-3 mois"
                ],
                'priorite': 'MOYENNE'
            })
    
    # ===== ANALYSE 4: GLYCÉMIE × MICROBIOTE =====
    glycemie = get_biomarker(['glucose', 'glycemie', 'glycémie'])
    hba1c = get_biomarker(['hba1c', 'hémoglobine glyquée'])
    
    if (glycemie and glycemie.get('Statut') == 'Élevé') or (hba1c and hba1c.get('Statut') == 'Élevé'):
        if di and di >= 3:
            analyses.append({
                'titre': '🍬 DYSGLYCÉMIE + DYSBIOSE',
                'signal_bio': f"Glycémie/HbA1c élevée ({glycemie.get('Valeur') if glycemie else 'N/A'})",
                'signal_micro': f"Dysbiose (DI {di}/5)",
                'interpretation': (
                    "Le microbiote intestinal influence fortement la glycémie via : "
                    "(1) Production d'acides gras à chaîne courte (AGCC), "
                    "(2) Modulation de l'inflammation de bas grade, "
                    "(3) Régulation des hormones métaboliques (GLP-1, PYY). "
                    "La dysbiose peut contribuer à l'insulinorésistance et au diabète de type 2."
                ),
                'recommandations': [
                    "Régime pauvre en sucres rapides",
                    "Fibres prébiotiques (inuline, pectines)",
                    "Probiotiques spécifiques (Akkermansia)",
                    "Activité physique régulière",
                    "Restauration microbiote + suivi glycémie"
                ],
                'priorite': 'HAUTE'
            })
    
    # ===== ANALYSE 5: THYROÏDE × MICROBIOTE =====
    tsh = get_biomarker(['tsh'])
    t4 = get_biomarker(['t4', 'thyroxine'])
    
    if (tsh and tsh.get('Statut') in ['Élevé', 'Bas']) or (t4 and t4.get('Statut') in ['Élevé', 'Bas']):
        if di and di >= 3:
            analyses.append({
                'titre': '🦋 DYSFONCTION THYROÏDIENNE + DYSBIOSE',
                'signal_bio': f"TSH/T4 anormales ({tsh.get('Valeur') if tsh else 'N/A'})",
                'signal_micro': f"Dysbiose (DI {di}/5)",
                'interpretation': (
                    "Le microbiote influence la fonction thyroïdienne via : "
                    "(1) Conversion T4→T3 (désiodase intestinale), "
                    "(2) Absorption des nutriments essentiels (sélénium, zinc, iode), "
                    "(3) Modulation de l'inflammation qui peut affecter la thyroïde. "
                    "Une dysbiose peut donc impacter indirectement la fonction thyroïdienne."
                ),
                'recommandations': [
                    "Bilan thyroïdien complet (T3, anticorps)",
                    "Vérifier sélénium, zinc, iode",
                    "Optimisation microbiote",
                    "Éviter goitrogènes si hypothyroïdie",
                    "Suivi endocrinologique si besoin"
                ],
                'priorite': 'MOYENNE'
            })
    
    # ===== ANALYSE 6: DIVERSITÉ BACTÉRIENNE RÉDUITE =====
    if 'lower' in diversity or 'reduced' in diversity or 'below' in diversity:
        analyses.append({
            'titre': '🔬 DIVERSITÉ BACTÉRIENNE RÉDUITE',
            'signal_bio': "—",
            'signal_micro': f"Diversité {microbiome_data.get('diversity', 'N/A')}",
            'interpretation': (
                "Une diversité bactérienne réduite est associée à : "
                "une moindre résilience du microbiote face aux stress, "
                "une capacité métabolique diminuée, "
                "un risque accru de maladies inflammatoires et métaboliques. "
                "C'est un marqueur de fragilité du microbiote."
            ),
            'recommandations': [
                "Alimentation variée et riche en fibres",
                "Probiotiques multi-souches",
                "Prébiotiques diversifiés",
                "Réduire stress et antibiotiques",
                "Réévaluation microbiote à 6 mois"
            ],
            'priorite': 'MOYENNE'
        })
    
    # ===== ANALYSE 7: GROUPES BACTÉRIENS DÉVIANTS =====
    if len(deviating_groups) >= 3:
        group_names = ", ".join([g.get('category', '') for g in deviating_groups[:3]])
        analyses.append({
            'titre': '⚠️ MULTIPLES GROUPES BACTÉRIENS DÉVIANTS',
            'signal_bio': "—",
            'signal_micro': f"{len(deviating_groups)} groupes déviants ({group_names})",
            'interpretation': (
                "La présence de plusieurs groupes bactériens déviants simultanément indique "
                "un déséquilibre profond et multi-dimensionnel du microbiote. "
                "Cela nécessite une approche globale de restauration plutôt que ciblée."
            ),
            'recommandations': [
                "Approche holistique de restauration",
                "Éliminer facteurs perturbateurs",
                "Probiotiques + prébiotiques combinés",
                "Alimentation anti-inflammatoire",
                "Suivi rapproché (3 mois)"
            ],
            'priorite': 'HAUTE'
        })
    
    return analyses


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
    Génère le rapport PDF COMPLET et PROFESSIONNEL (15-20 pages)
    """
    
    if output_path is None:
        import tempfile
        output_path = os.path.join(tempfile.gettempdir(), 'rapport_unilabs_complet.pdf')
    
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
        fontSize=10,
        leading=14
    )
    
    # ==================== PAGE 1: PAGE DE GARDE ====================
    if os.path.exists(DEFAULT_LOGO):
        try:
            logo = Image(DEFAULT_LOGO, width=5*cm, height=5*cm, kind='proportional')
            story.append(logo)
            story.append(Spacer(1, 1*cm))
        except Exception as e:
            print(f"⚠ Logo non chargé: {e}")
    
    story.append(Paragraph("RAPPORT D'ANALYSES BIOLOGIQUES", title_style))
    story.append(Paragraph("Biologie Fonctionnelle & Microbiote", styles['Normal']))
    story.append(Spacer(1, 0.5*cm))
    
    story.append(Paragraph("<b>UNILABS</b> - Laboratoire Central de Suisse Romande", 
                          ParagraphStyle('Center', parent=styles['Normal'], alignment=TA_CENTER, fontSize=11)))
    story.append(Spacer(1, 2*cm))
    
    # Informations patient
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
    
    story.append(Paragraph(
        f"<i>Rapport généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}</i>",
        ParagraphStyle('ItalicCenter', parent=styles['Normal'], alignment=TA_CENTER, fontSize=9, textColor=colors.HexColor('#6b7280'))
    ))
    
    story.append(PageBreak())
    
    # ==================== PAGE 2: SOMMAIRE ====================
    story.append(Paragraph("📋 SOMMAIRE DU RAPPORT", subtitle_style))
    story.append(Spacer(1, 0.5*cm))
    
    sommaire_data = [
        ['SECTION', 'PAGE'],
        ['1. Résultats Biologie', '3'],
        ['2. Âge Biologique', '—' if not bio_age_result else '5'],
        ['3. Analyse Microbiote', '6'],
        ['4. Analyses Croisées Multimodales', '10'],
        ['5. Recommandations Personnalisées', '13'],
        ['6. Plan de Suivi', '—' if not follow_up else '17']
    ]
    
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
    
    # ==================== PAGE 3+: BIOMARQUEURS ====================
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
        
        # Tous les biomarqueurs avec visualisations
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
    
    # ==================== PAGE: ÂGE BIOLOGIQUE ====================
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
        
        interp = Paragraph(
            f"<i>Votre âge biologique est de <b>{bio_age:.1f} ans</b>, soit une différence de <b>{diff:+.1f} ans</b> "
            f"par rapport à votre âge chronologique. Probabilité de fragilité : <b>{prob:.1f}%</b> ({risk}).</i>",
            normal_justify
        )
        story.append(interp)
        story.append(PageBreak())
    
    # ==================== PAGE: MICROBIOME ====================
    if microbiome_data:
        story.append(Paragraph("🦠 ANALYSE MICROBIOTE", subtitle_style))
        story.append(Spacer(1, 0.5*cm))
        
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
        
        # Groupes bactériens
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
            
            # Détails groupes
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
        
        # Bactéries individuelles
        bacteria_individual = microbiome_data.get('bacteria_individual', [])
        
        if bacteria_individual:
            story.append(Paragraph("🔬 BACTÉRIES INDIVIDUELLES (48 SOUCHES)", subtitle_style))
            story.append(Spacer(1, 0.5*cm))
            
            normal = sum(1 for b in bacteria_individual if b.get('status') == 'Normal')
            abnormal = len(bacteria_individual) - normal
            
            story.append(Paragraph(
                f"<b>{len(bacteria_individual)} bactéries</b> analysées : "
                f"<font color='#10b981'>{normal} normales</font>, "
                f"<font color='#ef4444'>{abnormal} anormales</font>",
                normal_justify
            ))
            story.append(Spacer(1, 0.5*cm))
            
            # Bactéries anormales
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
            
            # Liste complète
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
        
        # Biomarqueurs selles
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
    
    # ==================== PAGE: ANALYSES CROISÉES MULTIMODALES ====================
    story.append(Paragraph("🔬 ANALYSES CROISÉES MULTIMODALES", subtitle_style))
    story.append(Spacer(1, 0.5*cm))
    
    story.append(Paragraph(
        "<i>Cette section présente les liens entre vos résultats biologiques et votre microbiote. "
        "Ces analyses croisées permettent d'identifier des patterns complexes et d'adapter les recommandations.</i>",
        normal_justify
    ))
    story.append(Spacer(1, 0.8*cm))
    
    # Générer analyses croisées automatiques
    cross_analyses = compute_cross_analysis(biology_data, microbiome_data)
    
    if cross_analyses:
        for idx, analysis in enumerate(cross_analyses, 1):
            # Encadré de l'analyse
            story.append(Paragraph(f"{idx}. {analysis['titre']}", heading3_style))
            story.append(Spacer(1, 0.3*cm))
            
            # Tableau des signaux
            signals_data = [
                ['Signal Biologie', analysis['signal_bio']],
                ['Signal Microbiote', analysis['signal_micro']]
            ]
            
            signals_table = Table(signals_data, colWidths=[5*cm, 11*cm])
            signals_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#e5e7eb')),
                ('FONT', (0,0), (0,-1), 'Helvetica-Bold', 10),
                ('FONT', (1,0), (1,-1), 'Helvetica', 10),
                ('GRID', (0,0), (-1,-1), 1, colors.grey),
                ('PADDING', (0,0), (-1,-1), 8),
                ('VALIGN', (0,0), (-1,-1), 'TOP')
            ]))
            
            story.append(signals_table)
            story.append(Spacer(1, 0.5*cm))
            
            # Interprétation
            story.append(Paragraph("<b>Interprétation:</b>", ParagraphStyle('BoldSmall', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10)))
            story.append(Spacer(1, 0.2*cm))
            story.append(Paragraph(analysis['interpretation'], normal_justify))
            story.append(Spacer(1, 0.5*cm))
            
            # Recommandations
            story.append(Paragraph("<b>Recommandations:</b>", ParagraphStyle('BoldSmall', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10)))
            story.append(Spacer(1, 0.2*cm))
            
            for reco in analysis['recommandations']:
                story.append(Paragraph(f"• {reco}", styles['Normal']))
                story.append(Spacer(1, 0.1*cm))
            
            # Badge priorité
            priorite = analysis.get('priorite', 'MOYENNE')
            if priorite == 'HAUTE':
                bg = colors.HexColor('#fee2e2')
                fg = colors.HexColor('#991b1b')
            elif priorite == 'MOYENNE':
                bg = colors.HexColor('#fff7ed')
                fg = colors.HexColor('#9a3412')
            else:
                bg = colors.HexColor('#f3f4f6')
                fg = colors.HexColor('#374151')
            
            story.append(Spacer(1, 0.3*cm))
            priority_table = Table([[f"PRIORITÉ: {priorite}"]], colWidths=[16*cm])
            priority_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), bg),
                ('TEXTCOLOR', (0,0), (-1,-1), fg),
                ('FONT', (0,0), (-1,-1), 'Helvetica-Bold', 10),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('PADDING', (0,0), (-1,-1), 8),
                ('BOX', (0,0), (-1,-1), 2, fg)
            ]))
            story.append(priority_table)
            
            story.append(Spacer(1, 1*cm))
        
        story.append(PageBreak())
    else:
        story.append(Paragraph(
            "<i>Aucune analyse croisée automatique n'a pu être générée avec les données disponibles. "
            "Cela peut indiquer que vos résultats sont globalement dans les normes ou que certaines données sont manquantes.</i>",
            normal_justify
        ))
        story.append(PageBreak())
    
    # ==================== PAGE: RECOMMANDATIONS ====================
    if recommendations:
        story.append(Paragraph("💊 RECOMMANDATIONS PERSONNALISÉES", subtitle_style))
        story.append(Spacer(1, 0.5*cm))
        
        def create_reco_section(title, items, bg_color, border_color, icon="•"):
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
        
        # Sections de recommandations
        story.extend(create_reco_section(
            "🔥 ACTIONS PRIORITAIRES",
            recommendations.get('Prioritaires', []),
            colors.HexColor('#fee2e2'),
            colors.HexColor('#ef4444'),
            "⚠️"
        ))
        
        story.extend(create_reco_section(
            "⚠️ À SURVEILLER",
            recommendations.get('À surveiller', []),
            colors.HexColor('#fff7ed'),
            colors.HexColor('#f59e0b'),
            "•"
        ))
        
        story.extend(create_reco_section(
            "🥗 NUTRITION & DIÉTÉTIQUE",
            recommendations.get('Nutrition', []),
            colors.HexColor('#f0fdf4'),
            colors.HexColor('#22c55e'),
            "•"
        ))
        
        story.extend(create_reco_section(
            "💊 MICRONUTRITION",
            recommendations.get('Micronutrition', []),
            colors.HexColor('#eff6ff'),
            colors.HexColor('#3b82f6'),
            "•"
        ))
        
        story.extend(create_reco_section(
            "🏃 HYGIÈNE DE VIE",
            recommendations.get('Hygiène de vie', []),
            colors.HexColor('#faf5ff'),
            colors.HexColor('#a855f7'),
            "•"
        ))
        
        story.extend(create_reco_section(
            "🔬 EXAMENS COMPLÉMENTAIRES",
            recommendations.get('Examens complémentaires', []),
            colors.HexColor('#f8f9fa'),
            colors.HexColor('#6b7280'),
            "•"
        ))
        
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
    
    # Stats
    file_size = os.path.getsize(output_path) / 1024
    print(f"✅ PDF généré avec succès: {output_path}")
    print(f"📄 Taille: {file_size:.1f} KB")
    print(f"📊 Sections: Biologie, Microbiote, Analyses croisées, Recommandations")
    print(f"🎯 Prêt pour le patient")
    
    return output_path


# Alias pour compatibilité
generate_report = generate_multimodal_report


if __name__ == "__main__":
    print("=" * 70)
    print("PDF Generator v3.0 ULTIMATE chargé")
    print("Compatible avec app.py v13 et extractors v19")
    print("=" * 70)
    print("✅ Rapport complet 15-20 pages")
    print("✅ Extraction robuste")
    print("✅ Recommandations automatiques")
    print("✅ Analyses croisées multimodales DÉTAILLÉES")
    print("✅ Export professionnel prêt pour le patient")
    print("=" * 70)
