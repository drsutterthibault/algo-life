"""
ALGO-LIFE - Générateur de Rapports PDF Premium
Design moderne, max 10 pages, graphiques avancés, stats croisées bio/imagerie/génétique
"""

import json
import os
import tempfile
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, 
    PageBreak, Image, KeepTogether, Frame, PageTemplate
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.pdfgen import canvas
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import Rectangle, Circle, Wedge
import numpy as np
import matplotlib
matplotlib.use('Agg')


class PremiumPDFReportGenerator:
    """
    Générateur de rapports PDF premium - Design moderne, max 10 pages
    """
    
    def __init__(self, json_file):
        """Initialise le générateur avec les données patient"""
        with open(json_file, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
        
        self.styles = getSampleStyleSheet()
        self._setup_premium_styles()
        self.chart_files = []  # Pour nettoyer les fichiers temporaires
        
    def _setup_premium_styles(self):
        """Configure les styles premium"""
        
        # Couleurs du thème
        self.PRIMARY = colors.HexColor('#1565C0')  # Bleu profond
        self.SECONDARY = colors.HexColor('#0277BD')
        self.ACCENT = colors.HexColor('#00838F')  # Teal
        self.WARNING = colors.HexColor('#F57C00')  # Orange
        self.DANGER = colors.HexColor('#C62828')  # Rouge
        self.SUCCESS = colors.HexColor('#2E7D32')  # Vert
        self.BG_LIGHT = colors.HexColor('#E3F2FD')
        self.BG_ACCENT = colors.HexColor('#FFF3E0')
        
        # Titre page de garde
        self.styles.add(ParagraphStyle(
            name='CoverTitle',
            parent=self.styles['Title'],
            fontSize=32,
            textColor=self.PRIMARY,
            spaceAfter=20,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        # Sous-titre page de garde
        self.styles.add(ParagraphStyle(
            name='CoverSubtitle',
            parent=self.styles['Normal'],
            fontSize=16,
            textColor=self.SECONDARY,
            spaceAfter=10,
            alignment=TA_CENTER,
            fontName='Helvetica'
        ))
        
        # Titre de section (H1)
        self.styles.add(ParagraphStyle(
            name='SectionTitle',
            parent=self.styles['Heading1'],
            fontSize=18,
            textColor=colors.white,
            spaceAfter=15,
            spaceBefore=20,
            fontName='Helvetica-Bold',
            backColor=self.PRIMARY,
            borderPadding=10,
            leftIndent=10
        ))
        
        # Sous-section (H2)
        self.styles.add(ParagraphStyle(
            name='SubSection',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=self.SECONDARY,
            spaceAfter=8,
            spaceBefore=12,
            fontName='Helvetica-Bold',
            leftIndent=5,
            borderWidth=0,
            borderPadding=0,
            # Ligne en dessous
            bulletIndent=0
        ))
        
        # Corps de texte
        self.styles.add(ParagraphStyle(
            name='BodyCompact',
            parent=self.styles['BodyText'],
            fontSize=9,
            alignment=TA_JUSTIFY,
            spaceAfter=4,
            leading=12
        ))
        
        # Alerte
        self.styles.add(ParagraphStyle(
            name='Alert',
            parent=self.styles['BodyText'],
            fontSize=9,
            textColor=self.DANGER,
            leftIndent=15,
            spaceAfter=6,
            leading=11,
            backColor=colors.HexColor('#FFEBEE'),
            borderWidth=2,
            borderColor=self.DANGER,
            borderPadding=6
        ))
        
        # Info box
        self.styles.add(ParagraphStyle(
            name='InfoBox',
            parent=self.styles['BodyText'],
            fontSize=9,
            textColor=self.PRIMARY,
            leftIndent=15,
            spaceAfter=6,
            leading=11,
            backColor=self.BG_LIGHT,
            borderWidth=1,
            borderColor=self.PRIMARY,
            borderPadding=6
        ))
        
        # Recommandation
        self.styles.add(ParagraphStyle(
            name='RecoTitle',
            parent=self.styles['Heading3'],
            fontSize=11,
            textColor=self.SUCCESS,
            spaceAfter=4,
            spaceBefore=6,
            fontName='Helvetica-Bold',
            leftIndent=10
        ))
        
        self.styles.add(ParagraphStyle(
            name='RecoBody',
            parent=self.styles['BodyText'],
            fontSize=8,
            leftIndent=20,
            spaceAfter=3,
            leading=10
        ))
    
    def _create_header_footer(self, canvas_obj, doc):
        """En-tête et pied de page moderne"""
        canvas_obj.saveState()
        
        # Bande bleue en haut
        canvas_obj.setFillColor(self.PRIMARY)
        canvas_obj.rect(0, A4[1] - 40, A4[0], 40, fill=True, stroke=False)
        
        # Texte en-tête
        canvas_obj.setFillColor(colors.white)
        canvas_obj.setFont('Helvetica-Bold', 14)
        canvas_obj.drawString(30, A4[1] - 25, "ALGO-LIFE")
        canvas_obj.setFont('Helvetica', 9)
        canvas_obj.drawString(30, A4[1] - 35, "Analyse Bio-Fonctionnelle Intégrée")
        
        # Patient info (si pas page de garde)
        if doc.page > 1:
            canvas_obj.setFont('Helvetica', 8)
            patient_info = self.data.get('patient_info', {})
            patient_text = f"{patient_info.get('nom', '')} - {patient_info.get('date_naissance', '')}"
            canvas_obj.drawRightString(A4[0] - 30, A4[1] - 25, patient_text)
        
        # Pied de page
        canvas_obj.setFillColor(colors.HexColor('#666666'))
        canvas_obj.setFont('Helvetica', 7)
        canvas_obj.drawString(30, 20, f"Généré le {datetime.now().strftime('%d/%m/%Y')}")
        canvas_obj.drawCentredString(A4[0] / 2, 20, "Confidentiel - Usage médical uniquement")
        canvas_obj.drawRightString(A4[0] - 30, 20, f"Page {doc.page}")
        
        canvas_obj.restoreState()
    
    def _create_cortisol_premium_chart(self):
        """Graphique cortisol premium avec zones colorées"""
        fig, ax = plt.subplots(figsize=(10, 4))
        
        # Données cortisol
        timepoints = ['Réveil', '+30min', '12h', '18h', '22h']
        patient_values = []
        norm_min = []
        norm_max = []
        
        for result in self.data.get('results', {}).get('hormonologie_salivaire', []):
            param = result.get('parametre', '').lower()
            if 'cortisol' in param and 'dhea' not in param:
                try:
                    val = float(result.get('resultat', 0))
                    patient_values.append(val)
                    
                    ref = result.get('valeurs_reference', '')
                    if '-' in ref:
                        parts = ref.split('-')
                        norm_min.append(float(parts[0].strip()))
                        norm_max.append(float(parts[1].strip().split()[0]))
                except:
                    continue
        
        if len(patient_values) >= 4:
            x = np.arange(len(patient_values))
            
            # Zone normale (vert clair)
            ax.fill_between(x, norm_min, norm_max, alpha=0.3, color='green', label='Zone normale')
            
            # Courbe patient
            ax.plot(x, patient_values, 'o-', color='#C62828', linewidth=3, 
                   markersize=10, label='Patient', markeredgecolor='white', markeredgewidth=2)
            
            # Annotations valeurs
            for i, (xi, yi) in enumerate(zip(x, patient_values)):
                ax.annotate(f'{yi:.1f}', xy=(xi, yi), xytext=(0, 10), 
                           textcoords='offset points', ha='center', fontsize=9, fontweight='bold')
            
            # Mise en forme
            ax.set_xticks(x)
            ax.set_xticklabels(timepoints[:len(patient_values)], fontsize=10)
            ax.set_ylabel('Cortisol (nmol/L)', fontsize=11, fontweight='bold')
            ax.set_title('Cycle Circadien du Cortisol', fontsize=13, fontweight='bold', pad=15)
            ax.legend(loc='upper right', fontsize=9)
            ax.grid(True, alpha=0.2)
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            
            chart_path = tempfile.mktemp(suffix='.png', prefix='cortisol_')
            plt.tight_layout()
            plt.savefig(chart_path, dpi=150, bbox_inches='tight', facecolor='white')
            plt.close()
            
            self.chart_files.append(chart_path)
            return chart_path
        
        return None
    
    def _create_omega_radar_chart(self):
        """Graphique radar des acides gras oméga"""
        fig, ax = plt.subplots(figsize=(7, 7), subplot_kw=dict(projection='polar'))
        
        # Paramètres à afficher
        categories = ['Index Ω3', 'EPA', 'DHA', 'Ratio Ω6/Ω3', 'AA/EPA']
        
        # Récupérer les valeurs
        fatty_acids = self.data.get('results', {}).get('acides_gras', [])
        
        values = []
        for fa in fatty_acids:
            param = fa.get('parametre', '')
            if 'index' in param.lower() and 'omega-3' in param.lower():
                # Normaliser sur 10 (cible: 8-10%)
                val = float(fa.get('resultat', 0))
                values.append((val / 10) * 100)  # En pourcentage de l'optimal
            elif 'epa' in param.lower() and 'c20:5' in param.lower():
                val = float(fa.get('resultat', 0))
                values.append((val / 2.3) * 100)  # Par rapport à max normal
            elif 'dha' in param.lower() and 'c22:6' in param.lower():
                val = float(fa.get('resultat', 0))
                values.append((val / 9.4) * 100)
        
        # Compléter avec des valeurs par défaut si besoin
        while len(values) < 5:
            values.append(50)
        
        values = values[:5]
        
        # Angles pour chaque axe
        angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
        values += values[:1]  # Fermer le polygone
        angles += angles[:1]
        
        # Tracer
        ax.plot(angles, values, 'o-', linewidth=2, color='#1565C0', markersize=8)
        ax.fill(angles, values, alpha=0.25, color='#1565C0')
        
        # Zone optimale (cercle à 100%)
        ax.plot(angles, [100] * len(angles), '--', linewidth=1, color='green', alpha=0.5)
        
        # Mise en forme
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories, fontsize=10)
        ax.set_ylim(0, 120)
        ax.set_yticks([50, 100])
        ax.set_yticklabels(['50%', '100%'], fontsize=8)
        ax.set_title('Profil Acides Gras Oméga\n(% de l\'optimal)', fontsize=12, fontweight='bold', pad=20)
        ax.grid(True)
        
        chart_path = tempfile.mktemp(suffix='.png', prefix='omega_radar_')
        plt.tight_layout()
        plt.savefig(chart_path, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        
        self.chart_files.append(chart_path)
        return chart_path
    
    def _create_neurotrans_bar_chart(self):
        """Graphique en barres des neurotransmetteurs avec zones normales"""
        neurotrans = self.data.get('results', {}).get('neurotransmetteurs', [])
        
        if not neurotrans:
            return None
        
        # Filtrer les neurotransmetteurs principaux
        main_neuro = ['dopamine', 'adrénaline', 'noradrénaline', 'sérotonine']
        data_to_plot = []
        
        for nt in neurotrans:
            param = nt.get('parametre', '').lower()
            for mn in main_neuro:
                if mn in param:
                    try:
                        val = float(nt.get('resultat', 0))
                        ref = nt.get('valeurs_reference', '')
                        
                        if '-' in ref:
                            parts = ref.split('-')
                            min_val = float(parts[0].strip())
                            max_val = float(parts[1].strip().split()[0])
                            
                            # Calculer le pourcentage par rapport à la zone normale
                            mid_val = (min_val + max_val) / 2
                            pct = (val / mid_val) * 100
                            
                            # Déterminer la couleur
                            if val < min_val:
                                color = '#F57C00'  # Orange
                            elif val > max_val:
                                color = '#F57C00'
                            else:
                                color = '#2E7D32'  # Vert
                            
                            data_to_plot.append({
                                'name': mn.capitalize(),
                                'value': pct,
                                'color': color,
                                'actual': val
                            })
                            break
                    except:
                        continue
        
        if not data_to_plot:
            return None
        
        # Créer le graphique
        fig, ax = plt.subplots(figsize=(10, 4))
        
        names = [d['name'] for d in data_to_plot]
        values = [d['value'] for d in data_to_plot]
        colors_list = [d['color'] for d in data_to_plot]
        
        bars = ax.barh(names, values, color=colors_list, edgecolor='white', linewidth=2)
        
        # Ligne à 100% (zone normale)
        ax.axvline(100, color='green', linestyle='--', linewidth=2, alpha=0.5, label='Valeur cible')
        
        # Zone normale (80-120%)
        ax.axvspan(80, 120, alpha=0.1, color='green')
        
        # Annotations
        for i, (bar, data) in enumerate(zip(bars, data_to_plot)):
            width = bar.get_width()
            ax.text(width + 5, bar.get_y() + bar.get_height()/2, 
                   f'{data["actual"]:.1f}', 
                   va='center', fontsize=9, fontweight='bold')
        
        ax.set_xlabel('% de la valeur moyenne normale', fontsize=10, fontweight='bold')
        ax.set_title('Profil Neurotransmetteurs', fontsize=12, fontweight='bold', pad=15)
        ax.set_xlim(0, max(values) * 1.2)
        ax.legend(loc='lower right', fontsize=8)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.grid(axis='x', alpha=0.2)
        
        chart_path = tempfile.mktemp(suffix='.png', prefix='neurotrans_')
        plt.tight_layout()
        plt.savefig(chart_path, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        
        self.chart_files.append(chart_path)
        return chart_path
    
    def _build_cover_page(self):
        """Page de garde moderne"""
        story = []
        
        # Espace en haut
        story.append(Spacer(1, 3*cm))
        
        # Titre principal
        story.append(Paragraph("RAPPORT D'ANALYSE", self.styles['CoverTitle']))
        story.append(Paragraph("BIO-FONCTIONNELLE INTÉGRÉE", self.styles['CoverTitle']))
        
        story.append(Spacer(1, 1*cm))
        
        # Sous-titre
        story.append(Paragraph("Analyse Multi-Dimensionnelle", self.styles['CoverSubtitle']))
        story.append(Paragraph("Hormonologie • Neurotransmetteurs • Acides Gras • Imagerie", 
                             self.styles['CoverSubtitle']))
        
        story.append(Spacer(1, 2*cm))
        
        # Info patient (box)
        patient_info = self.data.get('patient_info', {})
        
        patient_data = [
            ['PATIENT', f"{patient_info.get('nom', '')} {patient_info.get('prenom', '')}"],
            ['Date de naissance', patient_info.get('date_naissance', '')],
            ['Sexe', patient_info.get('sexe', '')],
            ['N° Dossier', patient_info.get('numero_dossier', '')],
            ['', ''],
            ['Date de prélèvement', patient_info.get('date_prelevement', '')],
            ['Médecin prescripteur', self.data.get('medecin_prescripteur', '')],
        ]
        
        patient_table = Table(patient_data, colWidths=[6*cm, 10*cm])
        patient_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), self.PRIMARY),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.white),
            ('BACKGROUND', (1, 0), (1, -1), self.BG_LIGHT),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 15),
            ('RIGHTPADDING', (0, 0), (-1, -1), 15),
            ('TOPPADDING', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1.5, self.PRIMARY),
        ]))
        
        story.append(patient_table)
        
        story.append(Spacer(1, 3*cm))
        
        # Footer page de garde
        footer_text = """
        <para align=center>
        <font size=10><b>ALGO-LIFE</b></font><br/>
        <font size=8>Laboratoire d'Analyses Bio-Fonctionnelles<br/>
        Fond des Més 5, Tour F - 1348 Louvain-la-Neuve, Belgique<br/>
        Tél: 010/87 09 70 | Email: [email protected]</font>
        </para>
        """
        
        story.append(Paragraph(footer_text, self.styles['BodyCompact']))
        
        story.append(PageBreak())
        
        return story
    
    def _build_executive_summary(self):
        """Résumé exécutif - PAGE 2"""
        story = []
        
        story.append(Paragraph("1. RÉSUMÉ EXÉCUTIF", self.styles['SectionTitle']))
        story.append(Spacer(1, 0.4*cm))
        
        # Synthèse clinique
        synth = self.data.get('interpretation', {}).get('synthese_clinique', '')
        if synth:
            story.append(Paragraph(synth, self.styles['BodyCompact']))
            story.append(Spacer(1, 0.3*cm))
        
        # Anomalies critiques (tableau compact)
        story.append(Paragraph("1.1 Anomalies Prioritaires", self.styles['SubSection']))
        story.append(Spacer(1, 0.2*cm))
        
        anomalies_data = [
            ['Biomarqueur', 'Valeur', 'Statut', 'Impact'],
        ]
        
        # Analyser les résultats pour détecter les anomalies
        for category in ['hormonologie_salivaire', 'neurotransmetteurs', 'acides_gras']:
            results = self.data.get('results', {}).get(category, [])
            for result in results[:3]:  # Top 3 par catégorie max
                interpretation = result.get('interpretation', '').lower()
                if any(word in interpretation for word in ['bas', 'élevé', 'critique', 'insuffisant']):
                    anomalies_data.append([
                        result.get('parametre', ''),
                        f"{result.get('resultat', '')} {result.get('unite', '')}",
                        result.get('interpretation', ''),
                        result.get('impact_clinique', '')[:50] + '...' if result.get('impact_clinique') else ''
                    ])
                    
                    if len(anomalies_data) >= 6:  # Max 5 anomalies
                        break
            
            if len(anomalies_data) >= 6:
                break
        
        if len(anomalies_data) > 1:
            anomalies_table = Table(anomalies_data, colWidths=[4*cm, 2.5*cm, 3*cm, 6.5*cm])
            anomalies_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), self.DANGER),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#FFF3E0')]),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            
            story.append(anomalies_table)
            story.append(Spacer(1, 0.4*cm))
        
        return story
    
    def _build_cortisol_section_compact(self):
        """Section cortisol compacte avec graphique"""
        story = []
        
        story.append(Paragraph("2. AXEHPA & CYCLE CIRCADIEN", self.styles['SectionTitle']))
        story.append(Spacer(1, 0.3*cm))
        
        # Graphique cortisol
        chart = self._create_cortisol_premium_chart()
        if chart:
            img = Image(chart, width=16*cm, height=6*cm)
            story.append(img)
            story.append(Spacer(1, 0.3*cm))
        
        # Interprétation concise
        interpretation = self.data.get('interpretation', {}).get('axe_hpa', '')
        if interpretation:
            story.append(Paragraph(interpretation, self.styles['InfoBox']))
            story.append(Spacer(1, 0.3*cm))
        
        return story
    
    def _build_neurotrans_section_compact(self):
        """Section neurotransmetteurs compacte"""
        story = []
        
        story.append(Paragraph("3. PROFIL NEUROTRANSMETTEURS", self.styles['SectionTitle']))
        story.append(Spacer(1, 0.3*cm))
        
        # Graphique
        chart = self._create_neurotrans_bar_chart()
        if chart:
            img = Image(chart, width=16*cm, height=6*cm)
            story.append(img)
            story.append(Spacer(1, 0.3*cm))
        
        # Interprétation
        interpretation = self.data.get('interpretation', {}).get('neurotransmetteurs', '')
        if interpretation:
            story.append(Paragraph(interpretation, self.styles['BodyCompact']))
            story.append(Spacer(1, 0.3*cm))
        
        return story
    
    def _build_fatty_acids_section_compact(self):
        """Section acides gras compacte"""
        story = []
        
        story.append(Paragraph("4. ACIDES GRAS & INFLAMMATION", self.styles['SectionTitle']))
        story.append(Spacer(1, 0.3*cm))
        
        # Graphique radar
        chart = self._create_omega_radar_chart()
        if chart:
            img = Image(chart, width=12*cm, height=12*cm)
            story.append(img)
            story.append(Spacer(1, 0.3*cm))
        
        # Points clés (compact)
        fatty_acids = self.data.get('results', {}).get('acides_gras', [])
        key_points = []
        
        for fa in fatty_acids:
            param = fa.get('parametre', '')
            if any(kw in param.lower() for kw in ['index omega-3', 'epa', 'dha', 'ratio']):
                key_points.append(f"• <b>{param}:</b> {fa.get('resultat', '')} {fa.get('unite', '')} - {fa.get('interpretation', '')}")
        
        if key_points:
            points_text = "<br/>".join(key_points[:5])  # Max 5 points
            story.append(Paragraph(points_text, self.styles['BodyCompact']))
            story.append(Spacer(1, 0.3*cm))
        
        story.append(PageBreak())
        
        return story
    
    def _build_cross_stats_section(self):
        """Section statistiques croisées bio + imagerie + génétique - PAGE 5-6"""
        story = []
        
        story.append(Paragraph("5. ANALYSE INTÉGRÉE MULTI-DIMENSIONNELLE", self.styles['SectionTitle']))
        story.append(Spacer(1, 0.3*cm))
        
        # Intro
        intro_text = """
        L'analyse intégrée permet de croiser les données biologiques (hormonologie, neurotransmetteurs, 
        acides gras), l'imagerie médicale (DXA, TBS) et les données épigénétiques pour identifier 
        des corrélations et établir un profil de santé global.
        """
        story.append(Paragraph(intro_text, self.styles['BodyCompact']))
        story.append(Spacer(1, 0.3*cm))
        
        # 5.1 Corrélations Bio-Imagerie
        story.append(Paragraph("5.1 Corrélations Biologie - Imagerie Osseuse", self.styles['SubSection']))
        story.append(Spacer(1, 0.2*cm))
        
        # Tableau de corrélations
        dxa_results = self.data.get('results', {}).get('dxa_densitometrie', {})
        
        if dxa_results:
            corr_data = [
                ['Paramètre DXA', 'Valeur', 'Biomarqueurs associés', 'Corrélation'],
            ]
            
            # DMO lombaire vs DHEA, Cortisol
            dmo_lombaire = dxa_results.get('rachis_lombaire', {})
            if dmo_lombaire:
                dmo_val = dmo_lombaire.get('dmo', '')
                tscore = dmo_lombaire.get('t_score', '')
                
                # Trouver DHEA et cortisol
                dhea_val = ''
                cortisol_am = ''
                
                for result in self.data.get('results', {}).get('hormonologie_salivaire', []):
                    if 'dhea' in result.get('parametre', '').lower():
                        dhea_val = f"{result.get('resultat', '')} {result.get('unite', '')}"
                    if 'cortisol' in result.get('parametre', '').lower() and 'car' in result.get('parametre', '').lower():
                        cortisol_am = f"{result.get('resultat', '')} {result.get('unite', '')}"
                
                corr_data.append([
                    f"DMO Lombaire\nT-score: {tscore}",
                    f"{dmo_val} g/cm²",
                    f"DHEA: {dhea_val}\nCortisol AM: {cortisol_am}",
                    "DHEA favorable pour DMO\nCortisol bas → risque osseux"
                ])
            
            # TBS vs inflammation (omega-3)
            tbs_val = dxa_results.get('tbs', {}).get('valeur', '')
            if tbs_val:
                # Trouver index omega-3
                omega3_index = ''
                for fa in self.data.get('results', {}).get('acides_gras', []):
                    if 'index' in fa.get('parametre', '').lower() and 'omega-3' in fa.get('parametre', '').lower():
                        omega3_index = f"{fa.get('resultat', '')} {fa.get('unite', '')}"
                        break
                
                corr_data.append([
                    "TBS (microarchitecture)",
                    f"{tbs_val}",
                    f"Index Ω3: {omega3_index}",
                    "Ω3 anti-inflammatoire\nprotège microarchitecture osseuse"
                ])
            
            if len(corr_data) > 1:
                corr_table = Table(corr_data, colWidths=[4*cm, 3*cm, 4.5*cm, 4.5*cm])
                corr_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), self.PRIMARY),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 9),
                    ('FONTSIZE', (0, 1), (-1, -1), 8),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, self.BG_LIGHT]),
                    ('LEFTPADDING', (0, 0), (-1, -1), 6),
                    ('TOPPADDING', (0, 0), (-1, -1), 8),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ]))
                
                story.append(corr_table)
                story.append(Spacer(1, 0.3*cm))
        
        # 5.2 Intégration Épigénétique
        story.append(Paragraph("5.2 Intégration Données Épigénétiques", self.styles['SubSection']))
        story.append(Spacer(1, 0.2*cm))
        
        epi_results = self.data.get('results', {}).get('epigenetique', {})
        
        if epi_results:
            age_bio = epi_results.get('age_biologique', '')
            age_chrono = epi_results.get('age_chronologique', '')
            
            if age_bio and age_chrono:
                delta_age = float(age_bio) - float(age_chrono)
                
                epi_text = f"""
                <b>Âge biologique:</b> {age_bio} ans (chronologique: {age_chrono} ans)<br/>
                <b>Delta:</b> {delta_age:+.1f} ans<br/><br/>
                
                <b>Facteurs épigénétiques modulables identifiés:</b><br/>
                • <b>Nutrition:</b> Déficit Ω3 → impact méthylation ADN → vieillissement accéléré<br/>
                • <b>Stress chronique:</b> Cortisol bas (épuisement) → télomères raccourcis<br/>
                • <b>Inflammation:</b> Ratio AA/EPA élevé → activation NF-κB → modifications épigénétiques<br/>
                • <b>Activité physique:</b> Niveau d'activité corrélé à expression génique anti-âge
                """
                
                story.append(Paragraph(epi_text, self.styles['InfoBox']))
                story.append(Spacer(1, 0.3*cm))
        
        # 5.3 Scores de risque intégrés
        story.append(Paragraph("5.3 Scores de Risque Intégrés", self.styles['SubSection']))
        story.append(Spacer(1, 0.2*cm))
        
        risk_data = [
            ['Domaine', 'Score', 'Facteurs contributifs', 'Action'],
        ]
        
        # Score cardiovasculaire
        cv_score = "Modéré"
        cv_factors = []
        
        # Vérifier omega-3
        for fa in self.data.get('results', {}).get('acides_gras', []):
            if 'index' in fa.get('parametre', '').lower() and 'omega-3' in fa.get('parametre', '').lower():
                if float(fa.get('resultat', 0)) < 7.5:
                    cv_factors.append("Index Ω3 bas")
        
        # Vérifier inflammation
        for fa in self.data.get('results', {}).get('acides_gras', []):
            if 'aa/epa' in fa.get('parametre', '').lower():
                if float(fa.get('resultat', 0)) > 10:
                    cv_factors.append("Inflammation élevée (AA/EPA)")
        
        risk_data.append([
            "Cardiovasculaire",
            cv_score,
            "\n".join(cv_factors) if cv_factors else "Profil favorable",
            "Supplémentation Ω3\nGestion inflammation"
        ])
        
        # Score neurocognitif
        neuro_score = "Faible"
        neuro_factors = []
        
        for nt in self.data.get('results', {}).get('neurotransmetteurs', []):
            param = nt.get('parametre', '').lower()
            if 'dopamine' in param:
                if nt.get('interpretation', '').lower() in ['bas', 'limite basse']:
                    neuro_factors.append("Dopamine basse")
            if 'adrénaline' in param:
                if nt.get('interpretation', '').lower() in ['bas', 'très bas']:
                    neuro_factors.append("Adrénaline très basse")
        
        risk_data.append([
            "Neurocognitif",
            "Modéré" if neuro_factors else "Faible",
            "\n".join(neuro_factors) if neuro_factors else "Profil équilibré",
            "Support catécholaminergique\nDHA cérébral"
        ])
        
        # Score osseux
        osteo_score = "Faible"
        if dxa_results:
            dmo_lomb = dxa_results.get('rachis_lombaire', {}).get('t_score', 0)
            try:
                if float(dmo_lomb) < -1:
                    osteo_score = "Modéré"
                if float(dmo_lomb) < -2.5:
                    osteo_score = "Élevé"
            except:
                pass
        
        risk_data.append([
            "Ostéoporose",
            osteo_score,
            f"T-score: {dmo_lomb}" if dxa_results else "Évaluation nécessaire",
            "Calcium, Vit D3, K2\nRésistance musculaire"
        ])
        
        risk_table = Table(risk_data, colWidths=[3.5*cm, 2.5*cm, 5*cm, 5*cm])
        risk_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.ACCENT),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, self.BG_ACCENT]),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        story.append(risk_table)
        story.append(Spacer(1, 0.3*cm))
        
        story.append(PageBreak())
        
        return story
    
    def _build_supplements_recommendations(self):
        """Recommandations compléments alimentaires structurées - PAGE 7-8"""
        story = []
        
        story.append(Paragraph("6. RECOMMANDATIONS COMPLÉMENTS ALIMENTAIRES", self.styles['SectionTitle']))
        story.append(Spacer(1, 0.3*cm))
        
        # Introduction
        intro_text = """
        Les recommandations suivantes sont personnalisées en fonction de votre profil bio-fonctionnel. 
        Les dosages et formes galéniques sont optimisés pour une biodisponibilité maximale.
        """
        story.append(Paragraph(intro_text, self.styles['BodyCompact']))
        story.append(Spacer(1, 0.3*cm))
        
        # 6.1 PRIORITÉ ABSOLUE
        story.append(Paragraph("6.1 PRIORITÉ ABSOLUE", self.styles['SubSection']))
        story.append(Spacer(1, 0.2*cm))
        
        priority_supps = []
        
        # Analyser les déficits pour déterminer les priorités
        recommendations = self.data.get('recommendations', {})
        lifestyle = recommendations.get('lifestyle_changes', [])
        
        # Omega-3 si déficit
        for fa in self.data.get('results', {}).get('acides_gras', []):
            if 'index' in fa.get('parametre', '').lower() and 'omega-3' in fa.get('parametre', '').lower():
                if float(fa.get('resultat', 0)) < 7.5:
                    priority_supps.append({
                        'nom': 'OMÉGA-3 EPA/DHA',
                        'dosage': '2-3g EPA+DHA combinés/jour',
                        'forme': 'Huile de poisson concentrée (forme triglycéride)',
                        'timing': 'Pendant les repas (matin et soir)',
                        'duree': '3-4 mois (phase d\'attaque), puis 1-1.5g/j à vie',
                        'objectif': 'Index Ω3 → 8-10% | Anti-inflammatoire | Neuroprotection',
                        'marques': 'EPAX®, Nordic Naturals, Nutrimuscle (TOTOX <10)'
                    })
        
        # Support surrénalien si cortisol CAR effondré
        for result in self.data.get('results', {}).get('hormonologie_salivaire', []):
            if 'car' in result.get('parametre', '').lower():
                interpretation = result.get('interpretation', '').lower()
                if 'effondré' in interpretation or 'critique' in interpretation or 'bas' in interpretation:
                    priority_supps.append({
                        'nom': 'RHODIOLA ROSEA',
                        'dosage': '300-400mg/jour (extrait standardisé 3% rosavine)',
                        'forme': 'Gélules ou comprimés',
                        'timing': 'Le matin à jeun',
                        'duree': '3 mois minimum',
                        'objectif': 'Restauration CAR | Énergie matinale | Adaptogène',
                        'marques': 'Nutrixeal, Supersmart, Solgar'
                    })
                    
                    priority_supps.append({
                        'nom': 'VITAMINE C',
                        'dosage': '1000-2000mg/jour',
                        'forme': 'Ascorbate de sodium ou Ester-C (mieux toléré)',
                        'timing': 'En 2-3 prises pendant la journée',
                        'duree': 'Continue',
                        'objectif': 'Cofacteur synthèse cortisol | Support surrénalien',
                        'marques': 'Acérola naturelle (Nutrixeal), Ester-C'
                    })
                    break
        
        # Afficher les suppléments prioritaires
        for supp in priority_supps[:3]:  # Max 3 priorités
            supp_text = f"""
            <b>{supp['nom']}</b><br/>
            • <b>Dosage:</b> {supp['dosage']}<br/>
            • <b>Forme:</b> {supp['forme']}<br/>
            • <b>Timing:</b> {supp['timing']}<br/>
            • <b>Durée:</b> {supp['duree']}<br/>
            • <b>Objectif:</b> {supp['objectif']}<br/>
            • <b>Marques recommandées:</b> {supp.get('marques', 'Qualité pharmaceutique')}
            """
            story.append(Paragraph(supp_text, self.styles['RecoBody']))
            story.append(Spacer(1, 0.3*cm))
        
        # 6.2 COFACTEURS ESSENTIELS
        story.append(Paragraph("6.2 COFACTEURS MÉTABOLIQUES", self.styles['SubSection']))
        story.append(Spacer(1, 0.2*cm))
        
        cofactors_data = [
            ['Cofacteur', 'Dosage', 'Timing', 'Rôle clé'],
            ['Magnésium\n(bisglycinate)', '300-400mg/j', 'Le soir', 'Désaturases AG | Système nerveux | Sommeil'],
            ['Zinc\n(bisglycinate)', '15-30mg/j', 'Le soir', 'Delta-5/6 désaturase | Immunité | Hormones'],
            ['Vitamine B6\n(P-5-P)', '25-50mg/j', 'Matin', 'Neurotransmetteurs | Désaturases'],
            ['Vitamine D3', '2000-4000 UI/j', 'Matin avec gras', 'Santé osseuse | Immunité | Hormones'],
            ['Vitamine K2\n(MK-7)', '100-200μg/j', 'Avec Vit D', 'Fixation calcium os | Santé cardiovasculaire'],
        ]
        
        cofactors_table = Table(cofactors_data, colWidths=[4*cm, 3*cm, 3*cm, 6*cm])
        cofactors_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.SUCCESS),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#E8F5E9')]),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        story.append(cofactors_table)
        story.append(Spacer(1, 0.3*cm))
        
        # 6.3 SUPPORT SPÉCIFIQUE (si neurotransmetteurs)
        story.append(Paragraph("6.3 SUPPORT NEUROTRANSMETTEURS (si nécessaire)", self.styles['SubSection']))
        story.append(Spacer(1, 0.2*cm))
        
        neuro_supps = []
        
        for nt in self.data.get('results', {}).get('neurotransmetteurs', []):
            param = nt.get('parametre', '').lower()
            interpretation = nt.get('interpretation', '').lower()
            
            if 'dopamine' in param and ('bas' in interpretation or 'limite' in interpretation):
                neuro_supps.append(
                    "• <b>L-Tyrosine:</b> 500-1000mg/j le matin à jeun → Précurseur dopamine, noradrénaline, adrénaline"
                )
            
            if 'sérotonine' in param and 'bas' in interpretation:
                neuro_supps.append(
                    "• <b>5-HTP:</b> 50-100mg/j le soir → Précurseur sérotonine (humeur, sommeil)"
                )
        
        if neuro_supps:
            neuro_text = "<br/>".join(neuro_supps)
            story.append(Paragraph(neuro_text, self.styles['RecoBody']))
        else:
            story.append(Paragraph("Profil neurotransmetteurs équilibré - Pas de supplémentation spécifique nécessaire", 
                                 self.styles['RecoBody']))
        
        story.append(Spacer(1, 0.3*cm))
        
        # Précautions
        precautions_text = """
        <b>⚠ PRÉCAUTIONS:</b><br/>
        • Toujours consulter votre médecin avant de débuter une supplémentation<br/>
        • Interactions possibles avec certains médicaments (anticoagulants, antidépresseurs)<br/>
        • Privilégier des compléments de qualité pharmaceutique (certification GMP, absence de contaminants)<br/>
        • Conserver au réfrigérateur (oméga-3 surtout) après ouverture<br/>
        • Réévaluation biologique recommandée à 3 mois
        """
        story.append(Paragraph(precautions_text, self.styles['Alert']))
        story.append(Spacer(1, 0.3*cm))
        
        story.append(PageBreak())
        
        return story
    
    def _build_lifestyle_recommendations(self):
        """Recommandations lifestyle - PAGE 9-10"""
        story = []
        
        story.append(Paragraph("7. PROTOCOLE LIFESTYLE & OPTIMISATION", self.styles['SectionTitle']))
        story.append(Spacer(1, 0.3*cm))
        
        # 7.1 Protocole Matinal
        story.append(Paragraph("7.1 Protocole Matinal (Optimisation CAR)", self.styles['SubSection']))
        story.append(Spacer(1, 0.2*cm))
        
        morning_protocol = """
        <b>🌅 Dans les 30 minutes suivant le réveil:</b><br/>
        1. <b>Exposition lumière naturelle:</b> 10-15 min dehors ou fenêtre ouverte (stimule cortisol naturel)<br/>
        2. <b>Hydratation:</b> 1 grand verre d'eau + pincée de sel (Himalaya/Guérande) → Électrolytes surrénaliens<br/>
        3. <b>Éviter caféine avant 10h:</b> Laisse le cortisol naturel monter (CAR)<br/>
        4. <b>Petit-déjeuner protéiné:</b> 20-30g protéines + bons lipides (œufs, saumon, avocat)<br/>
        5. <b>Mouvement doux:</b> 5-10 min étirements, yoga, marche<br/><br/>
        
        <b>Suppléments matinaux:</b> Rhodiola, Vitamine C, Vitamine D3, Oméga-3
        """
        story.append(Paragraph(morning_protocol, self.styles['InfoBox']))
        story.append(Spacer(1, 0.3*cm))
        
        # 7.2 Cohérence Cardiaque
        story.append(Paragraph("7.2 Cohérence Cardiaque (Méthode 365)", self.styles['SubSection']))
        story.append(Spacer(1, 0.2*cm))
        
        coherence_text = """
        <b>🫁 Technique 365:</b><br/>
        • <b>3</b> fois par jour<br/>
        • <b>6</b> respirations par minute (5 sec inspir / 5 sec expir)<br/>
        • Pendant <b>5</b> minutes<br/><br/>
        
        <b>Moments clés:</b> Matin (avant petit-déj), Midi (avant repas), 17h (fin de journée)<br/><br/>
        
        <b>Bénéfices:</b> Rééquilibrage système nerveux autonome | Réduction cortisol | ↑ HRV | 
        Normalisation catécholamines | Anti-stress
        """
        story.append(Paragraph(coherence_text, self.styles['BodyCompact']))
        story.append(Spacer(1, 0.3*cm))
        
        # 7.3 Nutrition Anti-Inflammatoire
        story.append(Paragraph("7.3 Nutrition Anti-Inflammatoire", self.styles['SubSection']))
        story.append(Spacer(1, 0.2*cm))
        
        nutrition_data = [
            ['À PRIVILÉGIER ✓', 'À LIMITER / ÉVITER ❌'],
            [
                '• Poissons gras 3x/sem (saumon, sardines, maquereaux)\n'
                '• Huiles: olive, lin (frigo), noix, avocat\n'
                '• Légumes colorés (épinards, brocoli, betterave)\n'
                '• Fruits rouges (myrtilles, framboises)\n'
                '• Graines: lin moulues, chia, courge\n'
                '• Noix, amandes\n'
                '• Protéines qualité: œufs, volaille bio\n'
                '• Épices: curcuma, gingembre, cannelle',
                
                '• Sucres raffinés et aliments IG élevé\n'
                '• Huiles oméga-6 (tournesol, maïs, soja)\n'
                '• Graisses trans (margarines, fritures)\n'
                '• Alcool (inhibe cortisol)\n'
                '• Caféine excessive (>1 café/j, après 14h)\n'
                '• Aliments ultra-transformés\n'
                '• Gluten/laitiers si sensibilité\n'
                '• Jeûne intermittent prolongé (stress surrénalien)'
            ]
        ]
        
        nutrition_table = Table(nutrition_data, colWidths=[8*cm, 8*cm])
        nutrition_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, 0), self.SUCCESS),
            ('BACKGROUND', (1, 0), (1, 0), self.DANGER),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ]))
        
        story.append(nutrition_table)
        story.append(Spacer(1, 0.3*cm))
        
        # 7.4 Activité Physique Adaptée
        story.append(Paragraph("7.4 Activité Physique Adaptée", self.styles['SubSection']))
        story.append(Spacer(1, 0.2*cm))
        
        exercise_text = """
        <b>⚠ IMPORTANT:</b> En cas d'épuisement surrénalien, éviter absolument les exercices intenses 
        (HIIT, CrossFit, course longue) qui aggraveraient l'épuisement.<br/><br/>
        
        <b>✓ ACTIVITÉS RECOMMANDÉES:</b><br/>
        • <b>Marche quotidienne:</b> 30-45 min, rythme modéré<br/>
        • <b>Yoga doux, Pilates:</b> 2-3x/semaine<br/>
        • <b>Natation douce:</b> Sans forcer<br/>
        • <b>Tai Chi, Qi Gong:</b> Équilibre système nerveux<br/>
        • <b>Musculation légère:</b> Charges modérées, récupération ample<br/><br/>
        
        <b>Principe:</b> Mouvement régulier SANS épuisement. Objectif: stimuler sans "casser" davantage.
        """
        story.append(Paragraph(exercise_text, self.styles['InfoBox']))
        story.append(Spacer(1, 0.3*cm))
        
        # 7.5 Optimisation Sommeil
        story.append(Paragraph("7.5 Optimisation du Sommeil", self.styles['SubSection']))
        story.append(Spacer(1, 0.2*cm))
        
        sleep_text = """
        • <b>Horaires réguliers:</b> Coucher/lever à heures fixes (même week-end)<br/>
        • <b>Température:</b> Chambre fraîche 18-19°C<br/>
        • <b>Lumière bleue:</b> Éviter écrans 2h avant coucher (ou lunettes anti-lumière bleue)<br/>
        • <b>Rituel apaisant:</b> Lecture, méditation, infusion (camomille, passiflore)<br/>
        • <b>Magnésium:</b> 300mg 30-60 min avant coucher<br/>
        • <b>Mélatonine:</b> 1-3mg si difficulté d'endormissement (avis médical)
        """
        story.append(Paragraph(sleep_text, self.styles['RecoBody']))
        story.append(Spacer(1, 0.3*cm))
        
        # 7.6 Suivi & Réévaluation
        story.append(Paragraph("7.6 Plan de Suivi", self.styles['SubSection']))
        story.append(Spacer(1, 0.2*cm))
        
        followup_data = [
            ['Échéance', 'Actions', 'Objectifs'],
            ['1 mois', 'Consultation médicale | Observance', 'Évaluation clinique, ajustements'],
            ['3 mois', 'Bilan biologique complet:\n• Cortisol salivaire 5 points\n• Neurotransmetteurs\n• Acides gras\n• DHEA', 
             '• CAR restaurée\n• Index Ω3 >8%\n• Amélioration neurotransmetteurs'],
            ['6 mois', 'Bilan d\'étape + DXA si osseux', 'Consolidation acquis, stratégie long terme'],
        ]
        
        followup_table = Table(followup_data, colWidths=[2.5*cm, 7*cm, 6.5*cm])
        followup_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.ACCENT),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, self.BG_ACCENT]),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        story.append(followup_table)
        story.append(Spacer(1, 0.5*cm))
        
        # Conclusion finale
        conclusion_text = """
        <b>CONCLUSION</b><br/><br/>
        
        L'analyse bio-fonctionnelle intégrée révèle des déséquilibres ciblés nécessitant une prise en charge 
        personnalisée. Le pronostic est excellent avec une mise en œuvre rigoureuse du protocole.<br/><br/>
        
        <b>Points clés:</b><br/>
        ✓ Support surrénalien prioritaire (adaptogènes, micronutriments)<br/>
        ✓ Correction déficit oméga-3 (2-3g EPA+DHA/j × 3-4 mois)<br/>
        ✓ Optimisation lifestyle (sommeil, stress, nutrition, activité adaptée)<br/>
        ✓ Suivi biologique à 3 mois pour ajustement<br/><br/>
        
        La prise en charge précoce permettra d'éviter l'évolution vers un épuisement complet 
        et ses conséquences à long terme sur la santé globale.
        """
        story.append(Paragraph(conclusion_text, self.styles['InfoBox']))
        story.append(Spacer(1, 0.5*cm))
        
        # Signature
        signature_text = """
        <para align=center>
        <b>Ce rapport constitue une interprétation fonctionnelle des biomarqueurs analysés.</b><br/>
        <b>Il ne remplace pas une consultation médicale complète.</b><br/><br/>
        
        <b>ALGO-LIFE - Laboratoire d'Analyses Bio-Fonctionnelles</b><br/>
        Fond des Més 5, Tour F - 1348 Louvain-la-Neuve, Belgique<br/>
        Tél: 010/87 09 70 | Email: [email protected]<br/>
        N° agrément: 8/25607/57/998
        </para>
        """
        story.append(Paragraph(signature_text, self.styles['BodyCompact']))
        
        return story
    
    def generate_premium_report(self, output_filename='rapport_premium.pdf'):
        """
        Génère le rapport PDF premium complet (max 10 pages)
        
        Returns:
            str: Chemin vers le fichier PDF généré
        """
        
        # Créer le document
        doc = SimpleDocTemplate(
            output_filename,
            pagesize=A4,
            rightMargin=20,
            leftMargin=20,
            topMargin=50,
            bottomMargin=35
        )
        
        # Construire le contenu
        story = []
        
        # Page de garde
        story.extend(self._build_cover_page())
        
        # Résumé exécutif
        story.extend(self._build_executive_summary())
        
        # Sections principales (compactes)
        story.extend(self._build_cortisol_section_compact())
        story.extend(self._build_neurotrans_section_compact())
        story.extend(self._build_fatty_acids_section_compact())
        
        # Analyse intégrée
        story.extend(self._build_cross_stats_section())
        
        # Recommandations
        story.extend(self._build_supplements_recommendations())
        story.extend(self._build_lifestyle_recommendations())
        
        # Générer le PDF
        doc.build(story, onFirstPage=self._create_header_footer, onLaterPages=self._create_header_footer)
        
        # Nettoyer les fichiers temporaires
        for chart_file in self.chart_files:
            try:
                if os.path.exists(chart_file):
                    os.unlink(chart_file)
            except:
                pass
        
        print(f"✅ Rapport premium généré: {output_filename}")
        
        return output_filename


# Fonction utilitaire
def generate_premium_pdf_report(
    patient_data=None,
    json_file=None,
    output_path=None,
    output_filename=None
):
    """
    Génère un rapport PDF premium
    
    Args:
        patient_data (dict, optional): Données patient en dict
        json_file (str, optional): Chemin vers JSON
        output_path (str, optional): Chemin de sortie
        output_filename (str, optional): Nom du fichier
        
    Returns:
        str: Chemin vers le PDF généré
    """
    
    # Déterminer le fichier JSON
    temp_json_file = None
    
    if patient_data:
        temp_json_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8')
        json.dump(patient_data, temp_json_file, ensure_ascii=False, indent=2)
        temp_json_file.close()
        json_source = temp_json_file.name
    elif json_file:
        json_source = json_file
    else:
        raise ValueError("Fournir patient_data ou json_file")
    
    # Nom de fichier de sortie
    if output_path:
        output_file = output_path
    elif output_filename:
        output_file = output_filename
    else:
        output_file = 'rapport_premium.pdf'
    
    try:
        generator = PremiumPDFReportGenerator(json_source)
        result = generator.generate_premium_report(output_file)
        return result
        
    finally:
        if temp_json_file and os.path.exists(temp_json_file.name):
            try:
                os.unlink(temp_json_file.name)
            except:
                pass


if __name__ == "__main__":
    if os.path.exists('patient_data.json'):
        generate_premium_pdf_report(json_file='patient_data.json', output_filename='test_premium.pdf')
        print("✅ Test génération terminé")
    else:
        print("⚠️ Fichier patient_data.json non trouvé")
        # Alias pour compatibilité avec l'ancien code
def generate_pdf_report(patient_data=None, json_file=None, dxa_pdf_path=None, 
                       epigenetic_pdf_path=None, output_path=None, output_filename=None):
    """Fonction legacy - redirige vers generate_premium_pdf_report"""
    return generate_premium_pdf_report(
        patient_data=patient_data,
        json_file=json_file,
        output_path=output_path,
        output_filename=output_filename
    )
