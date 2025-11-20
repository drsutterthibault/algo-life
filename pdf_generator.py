"""
ALGO-LIFE - Générateur de Rapports PDF Bio-Fonctionnels ENRICHI
Module principal avec graphiques de visualisation et recommandations détaillées
"""

import json
import os
import tempfile
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, 
    PageBreak, Image, KeepTogether, ListFlowable, ListItem
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.pdfgen import canvas
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Backend non-interactif


class PDFReportGenerator:
    """
    Classe principale pour générer des rapports PDF bio-fonctionnels enrichis
    """
    
    def __init__(self, json_file):
        """
        Initialise le générateur avec les données patient
        
        Args:
            json_file (str): Chemin vers le fichier JSON contenant les données patient
        """
        with open(json_file, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
        
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
        
    def _setup_custom_styles(self):
        """Configure les styles personnalisés pour le rapport"""
        
        # Titre principal
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Title'],
            fontSize=24,
            textColor=colors.HexColor('#1a237e'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        # Sous-titre
        self.styles.add(ParagraphStyle(
            name='CustomHeading1',
            parent=self.styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#283593'),
            spaceAfter=12,
            spaceBefore=12,
            fontName='Helvetica-Bold',
            borderWidth=1,
            borderColor=colors.HexColor('#283593'),
            borderPadding=5,
            backColor=colors.HexColor('#e8eaf6')
        ))
        
        # Section
        self.styles.add(ParagraphStyle(
            name='CustomHeading2',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#3949ab'),
            spaceAfter=10,
            spaceBefore=10,
            fontName='Helvetica-Bold'
        ))
        
        # Corps de texte
        self.styles.add(ParagraphStyle(
            name='CustomBody',
            parent=self.styles['BodyText'],
            fontSize=10,
            alignment=TA_JUSTIFY,
            spaceAfter=6,
            leading=14
        ))
        
        # Interprétation
        self.styles.add(ParagraphStyle(
            name='Interpretation',
            parent=self.styles['BodyText'],
            fontSize=10,
            textColor=colors.HexColor('#d32f2f'),
            leftIndent=20,
            spaceAfter=10,
            leading=14,
            backColor=colors.HexColor('#ffebee'),
            borderWidth=1,
            borderColor=colors.HexColor('#d32f2f'),
            borderPadding=8
        ))
        
        # Style pour les recommandations
        self.styles.add(ParagraphStyle(
            name='RecommendationTitle',
            parent=self.styles['Heading2'],
            fontSize=12,
            textColor=colors.HexColor('#1976d2'),
            spaceAfter=6,
            spaceBefore=8,
            fontName='Helvetica-Bold',
            leftIndent=10
        ))
        
        self.styles.add(ParagraphStyle(
            name='RecommendationBody',
            parent=self.styles['BodyText'],
            fontSize=9,
            leftIndent=20,
            spaceAfter=4,
            leading=12
        ))
    
    def _create_header_footer(self, canvas_obj, doc):
        """Crée l'en-tête et le pied de page"""
        canvas_obj.saveState()
        
        # En-tête
        canvas_obj.setFont('Helvetica-Bold', 10)
        canvas_obj.setFillColor(colors.HexColor('#1a237e'))
        canvas_obj.drawString(30, A4[1] - 30, "ALGO-LIFE")
        canvas_obj.setFont('Helvetica', 8)
        canvas_obj.drawString(30, A4[1] - 45, "Rapport d'Analyse Bio-Fonctionnelle")
        
        # Ligne de séparation
        canvas_obj.setStrokeColor(colors.HexColor('#283593'))
        canvas_obj.setLineWidth(1)
        canvas_obj.line(30, A4[1] - 50, A4[0] - 30, A4[1] - 50)
        
        # Pied de page
        canvas_obj.setFont('Helvetica', 8)
        canvas_obj.setFillColor(colors.grey)
        canvas_obj.drawString(30, 30, f"Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}")
        canvas_obj.drawRightString(A4[0] - 30, 30, f"Page {doc.page}")
        
        canvas_obj.restoreState()
    
    def _create_gauge_chart(self, value, min_val, max_val, param_name, unit=""):
        """Crée un graphique de jauge pour visualiser une valeur par rapport aux normes"""
        
        fig, ax = plt.subplots(figsize=(8, 3))
        
        # Zone de référence (en vert)
        ax.barh(0, max_val - min_val, left=min_val, height=0.5, 
                color='lightgreen', alpha=0.5, label='Normal')
        
        # Zones anormales
        range_total = max_val - min_val
        margin = range_total * 0.3
        
        # Zone basse (en orange)
        if min_val > 0:
            ax.barh(0, min_val, left=0, height=0.5, 
                    color='orange', alpha=0.3, label='Bas')
        
        # Zone haute (en orange)
        ax.barh(0, margin, left=max_val, height=0.5, 
                color='orange', alpha=0.3, label='Élevé')
        
        # Valeur du patient (marqueur rouge)
        ax.plot(value, 0, 'ro', markersize=15, label='Valeur patient', zorder=5)
        ax.axvline(value, color='red', linestyle='--', linewidth=1.5, alpha=0.7)
        
        # Annotations
        ax.text(value, 0.8, f'{value} {unit}', ha='center', fontsize=10, fontweight='bold')
        
        # Mise en forme
        ax.set_ylim(-1, 1)
        ax.set_xlim(0, max_val + margin)
        ax.set_yticks([])
        ax.set_xlabel(f'{param_name} ({unit})', fontsize=11, fontweight='bold')
        ax.set_title(f'Position par rapport aux valeurs de référence', fontsize=12)
        ax.legend(loc='upper right', fontsize=8)
        ax.grid(axis='x', alpha=0.3)
        
        # Sauvegarder
        chart_path = f'gauge_{param_name.replace(" ", "_")}.png'
        plt.tight_layout()
        plt.savefig(chart_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        return chart_path
    
    def _create_cortisol_chart(self):
        """Crée le graphique du cycle circadien du cortisol"""
        
        # Récupérer les données de cortisol
        cortisol_data = []
        for result in self.data.get('results', {}).get('hormonologie_salivaire', []):
            if 'cortisol' in result.get('parametre', '').lower():
                try:
                    valeur = float(result.get('resultat', 0))
                    val_ref = result.get('valeurs_reference', '')
                    
                    min_val = 0
                    max_val = 0
                    if '-' in val_ref:
                        parts = val_ref.split('-')
                        min_val = float(parts[0].strip())
                        max_val = float(parts[1].split()[0].strip())
                    
                    cortisol_data.append({
                        'moment': result.get('moment', ''),
                        'valeur': valeur,
                        'min': min_val,
                        'max': max_val
                    })
                except (ValueError, IndexError):
                    continue
        
        if not cortisol_data:
            return None
        
        # Créer le graphique avec matplotlib
        fig, ax = plt.subplots(figsize=(10, 5))
        
        moments = [d['moment'] for d in cortisol_data]
        valeurs = [d['valeur'] for d in cortisol_data]
        mins = [d['min'] for d in cortisol_data]
        maxs = [d['max'] for d in cortisol_data]
        
        x = range(len(moments))
        
        # Zone de référence
        ax.fill_between(x, mins, maxs, alpha=0.3, color='green', label='Valeurs de référence')
        
        # Courbe des valeurs patient
        ax.plot(x, valeurs, marker='o', linewidth=2, markersize=8, 
                color='#1a237e', label='Valeurs patient')
        
        # Personnalisation
        ax.set_xlabel('Moment de prélèvement', fontsize=12, fontweight='bold')
        ax.set_ylabel('Cortisol (ng/mL)', fontsize=12, fontweight='bold')
        ax.set_title('Cycle Circadien du Cortisol', fontsize=14, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(moments, rotation=45, ha='right')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # Sauvegarder
        chart_path = 'cortisol_chart.png'
        plt.tight_layout()
        plt.savefig(chart_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        return chart_path
    
    def _build_patient_info_section(self):
        """Construit la section informations patient"""
        story = []
        
        patient = self.data.get('patient_info', {})
        
        story.append(Paragraph("RAPPORT D'ANALYSE BIO-FONCTIONNELLE", self.styles['CustomTitle']))
        story.append(Spacer(1, 0.5*cm))
        
        # Informations patient dans un tableau
        info_data = [
            ['Nom:', patient.get('nom', '').upper()],
            ['Prénom:', patient.get('prenom', '')],
            ['Date de naissance:', patient.get('date_naissance', '')],
            ['Sexe:', patient.get('sexe', '')],
            ['N° Dossier:', patient.get('numero_dossier', '')],
            ['Date de prélèvement:', patient.get('date_prelevement', '')],
            ['Médecin prescripteur:', patient.get('medecin_prescripteur', '')]
        ]
        
        info_table = Table(info_data, colWidths=[5*cm, 10*cm])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e8eaf6')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ]))
        
        story.append(info_table)
        story.append(Spacer(1, 1*cm))
        
        return story
    
    def _build_cortisol_section(self):
        """Construit la section cycle circadien du cortisol"""
        story = []
        
        story.append(Paragraph("1. CYCLE CIRCADIEN DU CORTISOL", self.styles['CustomHeading1']))
        story.append(Spacer(1, 0.3*cm))
        
        # Graphique
        chart_path = self._create_cortisol_chart()
        if chart_path and os.path.exists(chart_path):
            img = Image(chart_path, width=16*cm, height=8*cm)
            story.append(img)
            story.append(Spacer(1, 0.5*cm))
        
        # Tableau des résultats
        cortisol_results = []
        cortisol_results.append(['Moment', 'Résultat', 'Unité', 'Valeurs de référence', 'Statut'])
        
        for result in self.data.get('results', {}).get('hormonologie_salivaire', []):
            if 'cortisol' in result.get('parametre', '').lower():
                statut = result.get('interpretation', 'Normal')
                
                cortisol_results.append([
                    result.get('moment', ''),
                    result.get('resultat', ''),
                    result.get('unite', ''),
                    result.get('valeurs_reference', ''),
                    statut
                ])
        
        if len(cortisol_results) > 1:
            cortisol_table = Table(cortisol_results, colWidths=[3.5*cm, 2.5*cm, 2*cm, 4*cm, 3*cm])
            cortisol_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#283593')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            
            story.append(cortisol_table)
            story.append(Spacer(1, 0.5*cm))
        
        # Interprétation
        interpretation_text = """
        <b>Interprétation clinique:</b><br/>
        Le cycle circadien du cortisol montre des variations normales avec un pic matinal et une 
        diminution progressive au cours de la journée. Les valeurs observées sont dans les normes 
        physiologiques, indiquant un axe HPA fonctionnel.
        """
        story.append(Paragraph(interpretation_text, self.styles['Interpretation']))
        story.append(Spacer(1, 0.5*cm))
        
        return story
    
    def _build_neurotransmitters_section(self):
        """Construit la section neurotransmetteurs avec graphiques"""
        story = []
        
        story.append(Paragraph("2. PROFIL DES NEUROTRANSMETTEURS", self.styles['CustomHeading1']))
        story.append(Spacer(1, 0.3*cm))
        
        # Tableau des résultats
        neuro_results = []
        neuro_results.append(['Paramètre', 'Résultat', 'Unité', 'Valeurs de référence', 'Statut'])
        
        neurotransmetteurs = self.data.get('results', {}).get('neurotransmetteurs', [])
        
        for result in neurotransmetteurs:
            statut = result.get('interpretation', 'Normal')
            
            neuro_results.append([
                result.get('parametre', ''),
                result.get('resultat', ''),
                result.get('unite', ''),
                result.get('valeurs_reference', ''),
                statut
            ])
        
        if len(neuro_results) > 1:
            neuro_table = Table(neuro_results, colWidths=[4*cm, 2.5*cm, 2*cm, 4*cm, 3*cm])
            neuro_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#283593')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            
            story.append(neuro_table)
            story.append(Spacer(1, 0.5*cm))
            
            # Créer des graphiques de jauge pour chaque neurotransmetteur
            for result in neurotransmetteurs:
                try:
                    val = float(result.get('resultat', 0))
                    val_ref = result.get('valeurs_reference', '')
                    
                    if '-' in val_ref:
                        parts = val_ref.split('-')
                        min_val = float(parts[0].strip())
                        max_val = float(parts[1].split()[0].strip())
                        
                        gauge_path = self._create_gauge_chart(
                            val, min_val, max_val, 
                            result.get('parametre', ''),
                            result.get('unite', '')
                        )
                        
                        if gauge_path and os.path.exists(gauge_path):
                            img = Image(gauge_path, width=14*cm, height=4*cm)
                            story.append(img)
                            story.append(Spacer(1, 0.3*cm))
                except:
                    pass
        
        # Interprétation
        interpretation_text = """
        <b>Interprétation clinique:</b><br/>
        L'analyse des neurotransmetteurs révèle un profil équilibré. Les catécholamines (dopamine, 
        noradrénaline, adrénaline) et la sérotonine sont dans les valeurs de référence, suggérant 
        un métabolisme neurologique fonctionnel.
        """
        story.append(Paragraph(interpretation_text, self.styles['Interpretation']))
        story.append(Spacer(1, 0.5*cm))
        
        return story
    
    def _build_fatty_acids_section(self):
        """Construit la section acides gras"""
        story = []
        
        story.append(Paragraph("3. PROFIL DES ACIDES GRAS", self.styles['CustomHeading1']))
        story.append(Spacer(1, 0.3*cm))
        
        # Tableau des résultats
        fatty_results = []
        fatty_results.append(['Paramètre', 'Résultat', 'Unité', 'Valeurs de référence', 'Statut'])
        
        acides_gras = self.data.get('results', {}).get('acides_gras', [])
        
        for result in acides_gras:
            statut = result.get('interpretation', 'Normal')
            
            fatty_results.append([
                result.get('parametre', ''),
                result.get('resultat', ''),
                result.get('unite', ''),
                result.get('valeurs_reference', ''),
                statut
            ])
        
        if len(fatty_results) > 1:
            fatty_table = Table(fatty_results, colWidths=[5*cm, 2.5*cm, 2*cm, 3.5*cm, 3*cm])
            fatty_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#283593')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            
            story.append(fatty_table)
            story.append(Spacer(1, 0.5*cm))
        
        # Interprétation
        interpretation_text = """
        <b>Interprétation clinique:</b><br/>
        Le profil lipidique membranaire montre un équilibre entre acides gras saturés et insaturés. 
        L'index oméga-3 et le ratio AA/EPA sont dans les valeurs cibles, reflétant un statut 
        inflammatoire contrôlé et une intégrité membranaire optimale.
        """
        story.append(Paragraph(interpretation_text, self.styles['Interpretation']))
        story.append(Spacer(1, 0.5*cm))
        
        return story
    
    def _build_dxa_section(self):
        """Construit la section DXA"""
        story = []
        
        dxa_results = self.data.get('results', {}).get('dxa', [])
        
        if not dxa_results:
            return story
        
        story.append(PageBreak())
        story.append(Paragraph("4. DENSITOMÉTRIE OSSEUSE ET COMPOSITION CORPORELLE", self.styles['CustomHeading1']))
        story.append(Spacer(1, 0.3*cm))
        
        # Tableau des résultats DXA
        dxa_table_data = []
        dxa_table_data.append(['Paramètre', 'Résultat', 'Unité', 'Valeurs de référence', 'Statut'])
        
        for result in dxa_results:
            dxa_table_data.append([
                result.get('parametre', ''),
                result.get('resultat', ''),
                result.get('unite', ''),
                result.get('valeurs_reference', ''),
                result.get('interpretation', '')
            ])
        
        if len(dxa_table_data) > 1:
            dxa_table = Table(dxa_table_data, colWidths=[5*cm, 2.5*cm, 2*cm, 4.5*cm, 2*cm])
            dxa_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#283593')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            
            story.append(dxa_table)
            story.append(Spacer(1, 0.5*cm))
        
        # Interprétation DXA
        interpretation_text = """
        <b>Interprétation clinique:</b><br/>
        Les résultats de la densitométrie osseuse et de la composition corporelle fournissent 
        des informations essentielles sur la santé osseuse et métabolique. Un suivi régulier 
        permet d'ajuster les interventions thérapeutiques.
        """
        story.append(Paragraph(interpretation_text, self.styles['Interpretation']))
        story.append(Spacer(1, 0.5*cm))
        
        return story
    
    def _build_recommendations_section(self):
        """Construit la section recommandations ENRICHIE"""
        story = []
        
        story.append(PageBreak())
        story.append(Paragraph("5. RECOMMANDATIONS THÉRAPEUTIQUES PERSONNALISÉES", self.styles['CustomHeading1']))
        story.append(Spacer(1, 0.5*cm))
        
        recommendations = self.data.get('recommendations', {})
        
        # Section Supplémentation
        supplements = recommendations.get('supplement_needs', [])
        if supplements:
            story.append(Paragraph("5.1 SUPPLÉMENTATION CIBLÉE", self.styles['CustomHeading2']))
            story.append(Spacer(1, 0.3*cm))
            
            for i, supp in enumerate(supplements, 1):
                # Titre avec catégorie
                story.append(Paragraph(
                    f"<b>{i}. {supp.get('categorie', 'Support nutritionnel')}</b>",
                    self.styles['RecommendationTitle']
                ))
                
                # Détails
                details_text = f"""
                <b>Produit:</b> {supp.get('produit', '')}<br/>
                <b>Dosage:</b> {supp.get('dosage', '')}<br/>
                <b>Objectif:</b> {supp.get('objectif', '')}<br/>
                """
                story.append(Paragraph(details_text, self.styles['RecommendationBody']))
                story.append(Spacer(1, 0.2*cm))
            
            story.append(Spacer(1, 0.3*cm))
        
        # Section Changements mode de vie
        lifestyle = recommendations.get('lifestyle_changes', [])
        if lifestyle:
            story.append(Paragraph("5.2 MODIFICATIONS DU MODE DE VIE", self.styles['CustomHeading2']))
            story.append(Spacer(1, 0.3*cm))
            
            # Grouper par priorité
            high_priority = [l for l in lifestyle if l.get('priorite') in ['Haute', 'Critique', 'High']]
            medium_priority = [l for l in lifestyle if l.get('priorite') in ['Moyenne', 'Medium', 'Moy']]
            base_priority = [l for l in lifestyle if l.get('priorite') == 'Base']
            
            if high_priority:
                story.append(Paragraph("<b>⚠️ PRIORITÉ HAUTE</b>", self.styles['RecommendationTitle']))
                for change in high_priority:
                    change_text = f"""
                    <b>{change.get('domaine', '')}:</b><br/>
                    {change.get('recommandation', '')}<br/>
                    """
                    story.append(Paragraph(change_text, self.styles['RecommendationBody']))
                    story.append(Spacer(1, 0.2*cm))
            
            if medium_priority:
                story.append(Paragraph("<b>📋 PRIORITÉ MOYENNE</b>", self.styles['RecommendationTitle']))
                for change in medium_priority:
                    change_text = f"""
                    <b>{change.get('domaine', '')}:</b><br/>
                    {change.get('recommandation', '')}<br/>
                    """
                    story.append(Paragraph(change_text, self.styles['RecommendationBody']))
                    story.append(Spacer(1, 0.2*cm))
            
            if base_priority:
                story.append(Paragraph("<b>✓ RECOMMANDATIONS DE BASE</b>", self.styles['RecommendationTitle']))
                for change in base_priority:
                    change_text = f"""
                    <b>{change.get('domaine', '')}:</b><br/>
                    {change.get('recommandation', '')}<br/>
                    """
                    story.append(Paragraph(change_text, self.styles['RecommendationBody']))
                    story.append(Spacer(1, 0.2*cm))
            
            story.append(Spacer(1, 0.3*cm))
        
        # Section Suivi
        followup = recommendations.get('follow_up', [])
        if followup:
            story.append(Paragraph("5.3 PLAN DE SUIVI", self.styles['CustomHeading2']))
            story.append(Spacer(1, 0.3*cm))
            
            follow_data = [['Type de suivi', 'Délai', 'Examens / Actions']]
            
            for follow in followup:
                follow_data.append([
                    follow.get('type', ''),
                    follow.get('delai', ''),
                    follow.get('examens', '')
                ])
            
            follow_table = Table(follow_data, colWidths=[4*cm, 3*cm, 9*cm])
            follow_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1976d2')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#e3f2fd')),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ]))
            
            story.append(follow_table)
            story.append(Spacer(1, 0.5*cm))
        
        return story
    
    def _build_conclusion_section(self):
        """Construit la section conclusion"""
        story = []
        
        story.append(Paragraph("6. CONCLUSION", self.styles['CustomHeading1']))
        story.append(Spacer(1, 0.3*cm))
        
        conclusion_text = """
        L'analyse bio-fonctionnelle complète révèle un profil globalement satisfaisant avec quelques 
        axes d'optimisation identifiés. Les recommandations personnalisées visent à améliorer 
        l'équilibre hormonal, le statut inflammatoire et la fonction neurologique.<br/><br/>
        
        Un suivi régulier permettra d'évaluer l'efficacité des interventions proposées et d'ajuster 
        la prise en charge selon l'évolution clinique et biologique du patient.<br/><br/>
        
        <b>Critères d'amélioration à surveiller:</b><br/>
        • Amélioration du cycle circadien du cortisol<br/>
        • Optimisation des ratios d'acides gras<br/>
        • Équilibre neurotransmetteurs<br/>
        • Réduction des marqueurs inflammatoires<br/>
        """
        
        story.append(Paragraph(conclusion_text, self.styles['CustomBody']))
        story.append(Spacer(1, 1*cm))
        
        # Signature
        signature_text = """
        <para align=center>
        <b>Dr. Biologiste Responsable</b><br/>
        ALGO-LIFE - Laboratoire d'Analyses Bio-Fonctionnelles<br/>
        Fond des Més 5, Tour F - 1348 Louvain-la-Neuve, Belgique<br/>
        Tél: 010/87 09 70 | Email: [email protected]
        </para>
        """
        
        story.append(Paragraph(signature_text, self.styles['CustomBody']))
        
        return story
    
    def generate_report(self, output_filename='rapport_biofonctionnel.pdf'):
        """
        Génère le rapport PDF complet
        
        Args:
            output_filename (str): Nom du fichier PDF de sortie
            
        Returns:
            str: Chemin vers le fichier PDF généré
        """
        
        # Créer le document
        doc = SimpleDocTemplate(
            output_filename,
            pagesize=A4,
            rightMargin=30,
            leftMargin=30,
            topMargin=70,
            bottomMargin=50
        )
        
        # Construire le contenu
        story = []
        
        # Sections
        story.extend(self._build_patient_info_section())
        story.extend(self._build_cortisol_section())
        story.extend(self._build_neurotransmitters_section())
        story.extend(self._build_fatty_acids_section())
        story.extend(self._build_dxa_section())
        story.extend(self._build_recommendations_section())
        story.extend(self._build_conclusion_section())
        
        # Générer le PDF avec en-têtes/pieds de page
        doc.build(story, onFirstPage=self._create_header_footer, onLaterPages=self._create_header_footer)
        
        print(f"✅ Rapport généré: {output_filename}")
        
        return output_filename


# Fonction utilitaire compatible avec l'ancienne interface
def generate_pdf_report(
    patient_data=None,
    json_file=None,
    dxa_pdf_path=None,
    epigenetic_pdf_path=None,
    output_path=None,
    output_filename=None
):
    """
    Fonction utilitaire pour générer rapidement un rapport
    Compatible avec les deux interfaces : dict ou fichier JSON
    
    Args:
        patient_data (dict, optional): Dictionnaire contenant les données patient
        json_file (str, optional): Chemin vers le fichier JSON (si patient_data non fourni)
        dxa_pdf_path (str, optional): Chemin vers le PDF DXA (non implémenté pour l'instant)
        epigenetic_pdf_path (str, optional): Chemin vers le PDF épigénétique (non implémenté)
        output_path (str, optional): Chemin de sortie du PDF
        output_filename (str, optional): Nom du fichier de sortie
        
    Returns:
        str: Chemin vers le PDF généré
    """
    
    # Déterminer le fichier JSON à utiliser
    temp_json_file = None
    
    if patient_data:
        # Créer un fichier JSON temporaire à partir du dict
        temp_json_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8')
        json.dump(patient_data, temp_json_file, ensure_ascii=False, indent=2)
        temp_json_file.close()
        json_source = temp_json_file.name
    elif json_file:
        json_source = json_file
    else:
        raise ValueError("Vous devez fournir soit patient_data soit json_file")
    
    # Déterminer le nom de fichier de sortie
    if output_path:
        output_file = output_path
    elif output_filename:
        output_file = output_filename
    else:
        output_file = 'rapport_biofonctionnel.pdf'
    
    try:
        # Générer le rapport
        generator = PDFReportGenerator(json_source)
        result = generator.generate_report(output_file)
        
        return result
        
    finally:
        # Nettoyer le fichier temporaire si créé
        if temp_json_file and os.path.exists(temp_json_file.name):
            try:
                os.unlink(temp_json_file.name)
            except:
                pass


# Test si exécuté directement
if __name__ == "__main__":
    # Exemple d'utilisation
    if os.path.exists('patient_data.json'):
        generate_pdf_report(json_file='patient_data.json', output_filename='test_rapport.pdf')
        print("✅ Test de génération terminé")
    else:
        print("⚠️ Fichier patient_data.json non trouvé pour le test")
