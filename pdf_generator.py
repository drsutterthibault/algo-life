"""
ALGO-LIFE - Générateur de Rapports PDF Multimodaux
Version Beta v1.0
Dr Thibault SUTTER - Biologiste spécialisé en biologie fonctionnelle

Génère des rapports PDF professionnels intégrant:
- Analyses biologiques (Synlab, MGD, etc.)
- Analyses microbiote (IDK GutMAP, etc.)
- Analyses croisées et corrélations
- Recommandations personnalisées
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, 
    PageBreak, Image, KeepTogether, ListFlowable, ListItem
)
from reportlab.graphics.shapes import Drawing, Rect, Line, Circle
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.linecharts import HorizontalLineChart
from reportlab.pdfgen import canvas
from datetime import datetime
import os
from typing import Dict, List, Any, Optional


class PDFGenerator:
    """Générateur de rapports PDF multimodaux pour ALGO-LIFE"""
    
    # Couleurs ALGO-LIFE
    COLOR_PRIMARY = colors.HexColor('#5B5FCF')  # Violet
    COLOR_SECONDARY = colors.HexColor('#8B7FCF')  # Violet clair
    COLOR_SUCCESS = colors.HexColor('#4CAF50')
    COLOR_WARNING = colors.HexColor('#FF9800')
    COLOR_DANGER = colors.HexColor('#F44336')
    COLOR_INFO = colors.HexColor('#2196F3')
    COLOR_GREY = colors.HexColor('#757575')
    COLOR_LIGHT_GREY = colors.HexColor('#E0E0E0')
    
    def __init__(self, output_path: str):
        """
        Initialise le générateur PDF
        
        Args:
            output_path: Chemin du fichier PDF à générer
        """
        self.output_path = output_path
        self.doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
        self.story = []
        self.width, self.height = A4
        
    def _setup_custom_styles(self):
        """Configure les styles personnalisés"""
        
        # Titre principal
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=self.COLOR_PRIMARY,
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        # Sous-titre
        self.styles.add(ParagraphStyle(
            name='CustomSubtitle',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=self.COLOR_GREY,
            spaceAfter=20,
            alignment=TA_CENTER,
            fontName='Helvetica'
        ))
        
        # Section
        self.styles.add(ParagraphStyle(
            name='SectionTitle',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=self.COLOR_PRIMARY,
            spaceAfter=15,
            spaceBefore=20,
            fontName='Helvetica-Bold',
            borderWidth=0,
            borderColor=self.COLOR_PRIMARY,
            borderPadding=5,
            backColor=colors.HexColor('#F5F5F5')
        ))
        
        # Sous-section
        self.styles.add(ParagraphStyle(
            name='SubsectionTitle',
            parent=self.styles['Heading3'],
            fontSize=13,
            textColor=self.COLOR_SECONDARY,
            spaceAfter=10,
            spaceBefore=15,
            fontName='Helvetica-Bold'
        ))
        
        # Corps de texte
        self.styles.add(ParagraphStyle(
            name='CustomBody',
            parent=self.styles['BodyText'],
            fontSize=10,
            alignment=TA_JUSTIFY,
            spaceAfter=10,
            leading=14
        ))
        
        # Recommandation
        self.styles.add(ParagraphStyle(
            name='Recommendation',
            parent=self.styles['BodyText'],
            fontSize=10,
            alignment=TA_LEFT,
            leftIndent=20,
            spaceAfter=8,
            textColor=colors.HexColor('#333333'),
            leading=14
        ))
        
        # Alerte
        self.styles.add(ParagraphStyle(
            name='Alert',
            parent=self.styles['BodyText'],
            fontSize=10,
            textColor=self.COLOR_DANGER,
            alignment=TA_LEFT,
            leftIndent=15,
            spaceAfter=10,
            fontName='Helvetica-Bold'
        ))
        
        # Info
        self.styles.add(ParagraphStyle(
            name='InfoBox',
            parent=self.styles['BodyText'],
            fontSize=9,
            textColor=self.COLOR_INFO,
            alignment=TA_LEFT,
            leftIndent=15,
            spaceAfter=10,
            backColor=colors.HexColor('#E3F2FD')
        ))
        
    def add_header(self, patient_data: Dict[str, Any]):
        """Ajoute l'en-tête du rapport"""
        
        # Logo et titre
        title = Paragraph(
            "🧬 ALGO-LIFE",
            self.styles['CustomTitle']
        )
        subtitle = Paragraph(
            "PLATEFORME MÉDECIN - Analyse Multimodale de Santé<br/>Beta v1.0",
            self.styles['CustomSubtitle']
        )
        
        self.story.append(title)
        self.story.append(subtitle)
        self.story.append(Spacer(1, 0.5*cm))
        
        # Informations patient
        patient_info = [
            ["<b>Informations Patient</b>", ""],
            ["Nom:", f"{patient_data.get('nom', 'N/A')} {patient_data.get('prenom', 'N/A')}"],
            ["Date de naissance:", patient_data.get('date_naissance', 'N/A')],
            ["Âge:", f"{patient_data.get('age', 'N/A')} ans"],
            ["Genre:", patient_data.get('genre', 'N/A')],
            ["Poids:", f"{patient_data.get('poids', 'N/A')} kg"],
            ["Taille:", f"{patient_data.get('taille', 'N/A')} cm"],
            ["IMC:", f"{patient_data.get('imc', 'N/A')} kg/m²"],
            ["Activité:", patient_data.get('activite', 'N/A')],
        ]
        
        # Date du rapport
        date_rapport = datetime.now().strftime("%d/%m/%Y")
        patient_info.append(["Date du rapport:", date_rapport])
        
        # Symptômes
        if 'symptomes' in patient_data and patient_data['symptomes']:
            symptomes_str = ", ".join(patient_data['symptomes'])
            patient_info.append(["Symptômes:", symptomes_str])
        
        table = Table(patient_info, colWidths=[4.5*cm, 12*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.COLOR_PRIMARY),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, self.COLOR_LIGHT_GREY),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F9F9F9')])
        ]))
        
        self.story.append(table)
        self.story.append(Spacer(1, 1*cm))
        
    def add_section(self, title: str, level: int = 1):
        """Ajoute un titre de section"""
        style = 'SectionTitle' if level == 1 else 'SubsectionTitle'
        self.story.append(Paragraph(title, self.styles[style]))
        
    def add_biology_section(self, bio_data: Dict[str, Any]):
        """Section analyse biologique"""
        
        self.add_section("📊 ANALYSE BIOLOGIQUE", level=1)
        
        # Résumé
        if 'resume' in bio_data:
            self.story.append(Paragraph(
                f"<b>Résumé:</b> {bio_data['resume']}",
                self.styles['CustomBody']
            ))
            self.story.append(Spacer(1, 0.3*cm))
        
        # Tableaux des biomarqueurs par catégorie
        if 'categories' in bio_data:
            for category, markers in bio_data['categories'].items():
                self.add_section(f"🔬 {category}", level=2)
                
                marker_data = [["Biomarqueur", "Valeur", "Unité", "Référence", "Statut"]]
                
                for marker in markers:
                    status = self._get_status_symbol(marker.get('statut', 'normal'))
                    marker_data.append([
                        marker.get('nom', 'N/A'),
                        str(marker.get('valeur', 'N/A')),
                        marker.get('unite', ''),
                        marker.get('reference', 'N/A'),
                        status
                    ])
                
                table = Table(marker_data, colWidths=[5*cm, 2.5*cm, 2*cm, 3*cm, 2*cm])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), self.COLOR_PRIMARY),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('ALIGN', (0, 1), (0, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 9),
                    ('FONTSIZE', (0, 1), (-1, -1), 8),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                    ('TOPPADDING', (0, 1), (-1, -1), 5),
                    ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
                    ('GRID', (0, 0), (-1, -1), 0.5, self.COLOR_LIGHT_GREY),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#FAFAFA')])
                ]))
                
                self.story.append(table)
                self.story.append(Spacer(1, 0.5*cm))
                
                # Interprétations
                if 'interpretations' in marker and marker['interpretations']:
                    for interp in marker['interpretations']:
                        self.story.append(Paragraph(
                            f"→ {interp}",
                            self.styles['Recommendation']
                        ))
                    self.story.append(Spacer(1, 0.3*cm))
        
    def add_microbiome_section(self, microbiome_data: Dict[str, Any]):
        """Section analyse microbiote"""
        
        self.add_section("🦠 ANALYSE MICROBIOTE", level=1)
        
        # Score de diversité
        if 'diversite' in microbiome_data:
            div_score = microbiome_data['diversite'].get('score', 0)
            div_status = self._get_diversity_status(div_score)
            
            self.story.append(Paragraph(
                f"<b>Score de Diversité:</b> {div_score}/100 - {div_status}",
                self.styles['CustomBody']
            ))
            self.story.append(Spacer(1, 0.3*cm))
        
        # Phyla dominants
        if 'phyla' in microbiome_data:
            self.add_section("Répartition des Phyla", level=2)
            
            phyla_data = [["Phylum", "Abondance (%)", "Statut"]]
            for phylum in microbiome_data['phyla']:
                status = self._get_status_symbol(phylum.get('statut', 'normal'))
                phyla_data.append([
                    phylum.get('nom', 'N/A'),
                    f"{phylum.get('abondance', 0):.1f}%",
                    status
                ])
            
            table = Table(phyla_data, colWidths=[6*cm, 4*cm, 4*cm])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), self.COLOR_SUCCESS),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('ALIGN', (0, 1), (0, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 0.5, self.COLOR_LIGHT_GREY),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F1F8F4')])
            ]))
            
            self.story.append(table)
            self.story.append(Spacer(1, 0.5*cm))
        
        # Espèces clés
        if 'especes_cles' in microbiome_data:
            self.add_section("Espèces Clés Identifiées", level=2)
            
            for espece in microbiome_data['especes_cles']:
                impact = espece.get('impact', 'neutre')
                icon = "✅" if impact == "positif" else "⚠️" if impact == "negatif" else "ℹ️"
                
                self.story.append(Paragraph(
                    f"{icon} <b>{espece.get('nom', 'N/A')}</b>: {espece.get('description', '')}",
                    self.styles['CustomBody']
                ))
                self.story.append(Spacer(1, 0.2*cm))
        
        # Fonctions métaboliques
        if 'fonctions_metaboliques' in microbiome_data:
            self.add_section("Capacités Métaboliques", level=2)
            
            for fonction in microbiome_data['fonctions_metaboliques']:
                self.story.append(Paragraph(
                    f"• <b>{fonction.get('nom', '')}:</b> {fonction.get('evaluation', '')}",
                    self.styles['CustomBody']
                ))
            self.story.append(Spacer(1, 0.3*cm))
    
    def add_cross_analysis_section(self, cross_data: Dict[str, Any]):
        """Section analyse croisée biologie × microbiote"""
        
        self.add_section("🔗 ANALYSE CROISÉE MULTIMODALE", level=1)
        
        self.story.append(Paragraph(
            "Cette section présente les corrélations identifiées entre vos analyses biologiques et votre profil microbiote, "
            "permettant une compréhension intégrée de votre santé.",
            self.styles['CustomBody']
        ))
        self.story.append(Spacer(1, 0.5*cm))
        
        # Corrélations majeures
        if 'correlations' in cross_data:
            self.add_section("Corrélations Identifiées", level=2)
            
            for i, corr in enumerate(cross_data['correlations'], 1):
                severity = corr.get('severite', 'faible')
                icon = "🔴" if severity == "elevee" else "🟡" if severity == "moyenne" else "🟢"
                
                self.story.append(Paragraph(
                    f"{icon} <b>Corrélation {i}:</b> {corr.get('titre', '')}",
                    self.styles['SubsectionTitle']
                ))
                
                self.story.append(Paragraph(
                    f"<b>Biomarqueur:</b> {corr.get('biomarqueur', 'N/A')} - "
                    f"<b>Microbiote:</b> {corr.get('microbiote_element', 'N/A')}",
                    self.styles['CustomBody']
                ))
                
                self.story.append(Paragraph(
                    f"<b>Interprétation:</b> {corr.get('interpretation', '')}",
                    self.styles['CustomBody']
                ))
                
                if 'mecanisme' in corr:
                    self.story.append(Paragraph(
                        f"<i>Mécanisme:</i> {corr.get('mecanisme', '')}",
                        self.styles['InfoBox']
                    ))
                
                self.story.append(Spacer(1, 0.4*cm))
        
        # Axes d'intervention prioritaires
        if 'axes_intervention' in cross_data:
            self.add_section("Axes d'Intervention Prioritaires", level=2)
            
            for i, axe in enumerate(cross_data['axes_intervention'], 1):
                self.story.append(Paragraph(
                    f"<b>{i}. {axe.get('titre', '')}</b>",
                    self.styles['SubsectionTitle']
                ))
                
                self.story.append(Paragraph(
                    axe.get('description', ''),
                    self.styles['CustomBody']
                ))
                
                if 'impact' in axe:
                    self.story.append(Paragraph(
                        f"<b>Impact attendu:</b> {axe.get('impact', '')}",
                        self.styles['Recommendation']
                    ))
                
                self.story.append(Spacer(1, 0.3*cm))
    
    def add_recommendations_section(self, recommendations: Dict[str, Any]):
        """Section recommandations personnalisées"""
        
        self.add_section("💡 RECOMMANDATIONS PERSONNALISÉES", level=1)
        
        # Priorités
        if 'priorites' in recommendations:
            self.add_section("Priorités d'Action", level=2)
            
            for i, priorite in enumerate(recommendations['priorites'], 1):
                self.story.append(Paragraph(
                    f"<b>Priorité {i} - {priorite.get('titre', '')}</b>",
                    self.styles['SubsectionTitle']
                ))
                
                self.story.append(Paragraph(
                    priorite.get('description', ''),
                    self.styles['CustomBody']
                ))
                self.story.append(Spacer(1, 0.3*cm))
        
        # Nutrition
        if 'nutrition' in recommendations:
            self.add_section("🥗 Nutrition et Alimentation", level=2)
            
            # Aliments à privilégier
            if 'privilegier' in recommendations['nutrition']:
                self.story.append(Paragraph(
                    "<b>À PRIVILÉGIER:</b>",
                    self.styles['SubsectionTitle']
                ))
                
                for item in recommendations['nutrition']['privilegier']:
                    self.story.append(Paragraph(
                        f"✓ <b>{item.get('nom', '')}</b>: {item.get('raison', '')}",
                        self.styles['Recommendation']
                    ))
                self.story.append(Spacer(1, 0.3*cm))
            
            # Aliments à limiter
            if 'limiter' in recommendations['nutrition']:
                self.story.append(Paragraph(
                    "<b>À LIMITER:</b>",
                    self.styles['SubsectionTitle']
                ))
                
                for item in recommendations['nutrition']['limiter']:
                    self.story.append(Paragraph(
                        f"✗ <b>{item.get('nom', '')}</b>: {item.get('raison', '')}",
                        self.styles['Alert']
                    ))
                self.story.append(Spacer(1, 0.3*cm))
        
        # Supplémentation
        if 'supplementation' in recommendations:
            self.add_section("💊 Supplémentation Suggérée", level=2)
            
            suppl_data = [["Supplément", "Dosage", "Fréquence", "Durée", "Objectif"]]
            
            for suppl in recommendations['supplementation']:
                suppl_data.append([
                    suppl.get('nom', 'N/A'),
                    suppl.get('dosage', 'N/A'),
                    suppl.get('frequence', 'N/A'),
                    suppl.get('duree', 'N/A'),
                    suppl.get('objectif', 'N/A')
                ])
            
            table = Table(suppl_data, colWidths=[3.5*cm, 2*cm, 2.5*cm, 2*cm, 5.5*cm])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), self.COLOR_INFO),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('ALIGN', (0, 1), (0, -1), 'LEFT'),
                ('ALIGN', (4, 1), (4, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, self.COLOR_LIGHT_GREY),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F0F7FF')])
            ]))
            
            self.story.append(table)
            self.story.append(Spacer(1, 0.3*cm))
            
            self.story.append(Paragraph(
                "<i>⚠️ Note: Ces suggestions sont basées sur votre profil multimodal. "
                "Consultez votre médecin avant toute nouvelle supplémentation.</i>",
                self.styles['InfoBox']
            ))
            self.story.append(Spacer(1, 0.5*cm))
        
        # Hygiène de vie
        if 'hygiene_vie' in recommendations:
            self.add_section("🏃 Hygiène de Vie", level=2)
            
            for categorie, conseils in recommendations['hygiene_vie'].items():
                self.story.append(Paragraph(
                    f"<b>{categorie.upper()}:</b>",
                    self.styles['SubsectionTitle']
                ))
                
                for conseil in conseils:
                    self.story.append(Paragraph(
                        f"→ {conseil}",
                        self.styles['Recommendation']
                    ))
                self.story.append(Spacer(1, 0.3*cm))
    
    def add_follow_up_section(self, follow_up: Dict[str, Any]):
        """Section suivi et contrôles"""
        
        self.add_section("📅 SUIVI ET CONTRÔLES", level=1)
        
        self.story.append(Paragraph(
            "Plan de suivi recommandé pour évaluer l'efficacité des interventions:",
            self.styles['CustomBody']
        ))
        self.story.append(Spacer(1, 0.3*cm))
        
        if 'controles' in follow_up:
            controle_data = [["Analyse", "Timing", "Biomarqueurs à Surveiller"]]
            
            for controle in follow_up['controles']:
                markers = ", ".join(controle.get('biomarqueurs', []))
                controle_data.append([
                    controle.get('type', 'N/A'),
                    controle.get('delai', 'N/A'),
                    markers
                ])
            
            table = Table(controle_data, colWidths=[4*cm, 3*cm, 8.5*cm])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), self.COLOR_SECONDARY),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 0.5, self.COLOR_LIGHT_GREY),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#FAF8FF')])
            ]))
            
            self.story.append(table)
            self.story.append(Spacer(1, 0.5*cm))
    
    def add_footer(self):
        """Ajoute le pied de page"""
        
        self.story.append(PageBreak())
        
        self.story.append(Spacer(1, 2*cm))
        
        footer_text = """
        <para alignment="center">
        <b>ALGO-LIFE © 2026</b><br/>
        Dr Thibault SUTTER, Dr en biologie spécialisé en biologie fonctionnelle<br/>
        Version Beta v1.0<br/><br/>
        
        <i>Ce rapport est généré par intelligence artificielle à partir d'analyses multimodales.<br/>
        Il ne remplace pas un avis médical professionnel.<br/>
        Pour toute question, consultez votre médecin traitant.</i><br/><br/>
        
        📧 Contact: contact@algo-life.com | 🌐 www.algo-life.com
        </para>
        """
        
        self.story.append(Paragraph(footer_text, self.styles['CustomBody']))
    
    def _get_status_symbol(self, status: str) -> str:
        """Retourne le symbole de statut"""
        status_map = {
            'normal': '✓ Normal',
            'bas': '↓ Bas',
            'haut': '↑ Haut',
            'critique_bas': '⚠️ Très bas',
            'critique_haut': '⚠️ Très haut',
            'attention': '⚡ Attention'
        }
        return status_map.get(status.lower(), '• N/A')
    
    def _get_diversity_status(self, score: float) -> str:
        """Évalue le statut de diversité"""
        if score >= 80:
            return "Excellente diversité"
        elif score >= 60:
            return "Bonne diversité"
        elif score >= 40:
            return "Diversité moyenne"
        else:
            return "Diversité faible"
    
    def generate(self, data: Dict[str, Any]):
        """
        Génère le rapport PDF complet
        
        Args:
            data: Dictionnaire contenant toutes les données du rapport
                - patient: informations patient
                - biologie: données biologiques
                - microbiote: données microbiome
                - cross_analysis: analyses croisées
                - recommendations: recommandations
                - follow_up: plan de suivi
        """
        
        # En-tête
        self.add_header(data.get('patient', {}))
        
        # Sections
        if 'biologie' in data:
            self.add_biology_section(data['biologie'])
            self.story.append(PageBreak())
        
        if 'microbiote' in data:
            self.add_microbiome_section(data['microbiote'])
            self.story.append(PageBreak())
        
        if 'cross_analysis' in data:
            self.add_cross_analysis_section(data['cross_analysis'])
            self.story.append(PageBreak())
        
        if 'recommendations' in data:
            self.add_recommendations_section(data['recommendations'])
            self.story.append(PageBreak())
        
        if 'follow_up' in data:
            self.add_follow_up_section(data['follow_up'])
        
        # Pied de page
        self.add_footer()
        
        # Construction du PDF
        self.doc.build(self.story)
        
        print(f"✅ Rapport PDF généré avec succès: {self.output_path}")
        return self.output_path


# Fonction helper pour générer rapidement un rapport
def generate_multimodal_report(
    patient_data: Dict[str, Any],
    biology_data: Dict[str, Any],
    microbiome_data: Dict[str, Any],
    cross_analysis: Dict[str, Any],
    recommendations: Dict[str, Any],
    follow_up: Dict[str, Any],
    output_path: str = "rapport_multimodal.pdf"
) -> str:
    """
    Fonction helper pour générer un rapport complet
    
    Returns:
        str: Chemin du fichier PDF généré
    """
    
    data = {
        'patient': patient_data,
        'biologie': biology_data,
        'microbiote': microbiome_data,
        'cross_analysis': cross_analysis,
        'recommendations': recommendations,
        'follow_up': follow_up
    }
    
    generator = PDFGenerator(output_path)
    return generator.generate(data)


if __name__ == "__main__":
    # Exemple d'utilisation avec données de test
    
    patient_example = {
        'nom': 'DUPONT',
        'prenom': 'Jean',
        'date_naissance': '03/10/1987',
        'age': 38,
        'genre': 'Homme',
        'poids': 73.0,
        'taille': 175.0,
        'imc': 23.8,
        'activite': 'Sédentaire (0-1h/semaine)',
        'symptomes': ['Fatigue chronique', 'Troubles digestifs']
    }
    
    biology_example = {
        'resume': 'Profil biologique montrant des signes de stress oxydatif et déséquilibre thyroïdien léger.',
        'categories': {
            'Thyroïde': [
                {
                    'nom': 'TSH',
                    'valeur': 3.8,
                    'unite': 'mUI/L',
                    'reference': '0.4-4.0',
                    'statut': 'haut',
                    'interpretations': [
                        'TSH en limite haute, suggère une légère hypothyroïdie subclinique',
                        'Vérifier T3/T4 libres pour confirmation'
                    ]
                }
            ],
            'Inflammation': [
                {
                    'nom': 'CRP',
                    'valeur': 5.2,
                    'unite': 'mg/L',
                    'reference': '<3.0',
                    'statut': 'haut',
                    'interpretations': [
                        'Inflammation chronique de bas grade détectée',
                        'Lien possible avec déséquilibre microbiote'
                    ]
                }
            ]
        }
    }
    
    microbiome_example = {
        'diversite': {
            'score': 65,
            'interpretation': 'Diversité modérée nécessitant amélioration'
        },
        'phyla': [
            {'nom': 'Firmicutes', 'abondance': 58.0, 'statut': 'normal'},
            {'nom': 'Bacteroidetes', 'abondance': 32.0, 'statut': 'normal'},
            {'nom': 'Proteobacteria', 'abondance': 8.0, 'statut': 'haut'},
            {'nom': 'Actinobacteria', 'abondance': 2.0, 'statut': 'bas'}
        ],
        'especes_cles': [
            {
                'nom': 'Akkermansia muciniphila',
                'description': 'Espèce protectrice de la barrière intestinale - abondance sous-optimale',
                'impact': 'negatif'
            },
            {
                'nom': 'Faecalibacterium prausnitzii',
                'description': 'Producteur majeur de butyrate - niveau satisfaisant',
                'impact': 'positif'
            }
        ],
        'fonctions_metaboliques': [
            {'nom': 'Production de SCFA', 'evaluation': 'Capacité modérée'},
            {'nom': 'Métabolisme des vitamines B', 'evaluation': 'Capacité réduite'},
            {'nom': 'Dégradation des fibres', 'evaluation': 'Capacité normale'}
        ]
    }
    
    cross_analysis_example = {
        'correlations': [
            {
                'titre': 'Inflammation et dysbiose',
                'biomarqueur': 'CRP élevée (5.2 mg/L)',
                'microbiote_element': 'Proteobacteria élevés (8%)',
                'interpretation': 'L\'excès de Proteobacteria pro-inflammatoires corrèle avec l\'élévation de la CRP',
                'mecanisme': 'Les lipopolysaccharides (LPS) bactériens stimulent la réponse inflammatoire systémique',
                'severite': 'moyenne'
            },
            {
                'titre': 'Fonction thyroïdienne et microbiote',
                'biomarqueur': 'TSH limite haute (3.8 mUI/L)',
                'microbiote_element': 'Faible diversité générale',
                'interpretation': 'La dysbiose peut affecter la conversion périphérique T4→T3',
                'mecanisme': 'Le microbiote influence le métabolisme des hormones thyroïdiennes via les déiodinases',
                'severite': 'faible'
            }
        ],
        'axes_intervention': [
            {
                'titre': 'Restauration barrière intestinale',
                'description': 'Renforcer l\'intégrité de la muqueuse intestinale pour réduire l\'inflammation systémique',
                'impact': 'Diminution attendue de la CRP et amélioration des symptômes digestifs'
            },
            {
                'titre': 'Optimisation thyroïdienne',
                'description': 'Support nutritionnel pour la fonction thyroïdienne (sélénium, zinc, iode)',
                'impact': 'Normalisation potentielle de la TSH et amélioration de l\'énergie'
            }
        ]
    }
    
    recommendations_example = {
        'priorites': [
            {
                'titre': 'Réduction de l\'inflammation',
                'description': 'Protocole anti-inflammatoire combinant alimentation, supplémentation et restauration du microbiote'
            }
        ],
        'nutrition': {
            'privilegier': [
                {'nom': 'Poissons gras (saumon, maquereau)', 'raison': 'Oméga-3 anti-inflammatoires et support thyroïdien'},
                {'nom': 'Légumes crucifères cuits', 'raison': 'Support détox et thyroïde (cuisson réduit goitrogènes)'},
                {'nom': 'Aliments fermentés', 'raison': 'Probiotiques naturels pour restaurer le microbiote'},
                {'nom': 'Fibres prébiotiques', 'raison': 'Nourriture pour bactéries bénéfiques'}
            ],
            'limiter': [
                {'nom': 'Sucres raffinés', 'raison': 'Favorisent l\'inflammation et la dysbiose'},
                {'nom': 'Gluten et produits laitiers', 'raison': 'Potentiellement pro-inflammatoires (test élimination 4 semaines)'},
                {'nom': 'Aliments ultra-transformés', 'raison': 'Additifs néfastes pour le microbiote'}
            ]
        },
        'supplementation': [
            {'nom': 'Oméga-3 EPA/DHA', 'dosage': '2-3g', 'frequence': '1x/jour', 'duree': '3 mois', 'objectif': 'Anti-inflammatoire'},
            {'nom': 'Probiotiques multi-souches', 'dosage': '20-50 milliards UFC', 'frequence': '1x/jour', 'duree': '3 mois', 'objectif': 'Restauration microbiote'},
            {'nom': 'L-Glutamine', 'dosage': '5g', 'frequence': '2x/jour', 'duree': '2 mois', 'objectif': 'Barrière intestinale'},
            {'nom': 'Sélénium', 'dosage': '100-200µg', 'frequence': '1x/jour', 'duree': '3 mois', 'objectif': 'Fonction thyroïdienne'},
            {'nom': 'Vitamine D3', 'dosage': '2000-4000 UI', 'frequence': '1x/jour', 'duree': 'Long terme', 'objectif': 'Immunité et inflammation'}
        ],
        'hygiene_vie': {
            'Activité physique': [
                'Marche quotidienne 30 minutes minimum',
                'Exercices de résistance 2-3x/semaine',
                'Éviter surmenage (stress oxydatif)'
            ],
            'Sommeil': [
                'Viser 7-8h par nuit',
                'Coucher avant 23h pour optimiser récupération',
                'Éviter écrans 1h avant coucher'
            ],
            'Gestion du stress': [
                'Techniques de respiration (cohérence cardiaque)',
                'Méditation ou yoga 10-15 min/jour',
                'Activités plaisir régulières'
            ]
        }
    }
    
    follow_up_example = {
        'controles': [
            {
                'type': 'Bilan biologique',
                'delai': '6-8 semaines',
                'biomarqueurs': ['TSH', 'T3 libre', 'T4 libre', 'CRP', 'Vitamine D']
            },
            {
                'type': 'Analyse microbiote',
                'delai': '3 mois',
                'biomarqueurs': ['Diversité', 'Ratio F/B', 'Akkermansia', 'Proteobacteria']
            },
            {
                'type': 'Bilan complet',
                'delai': '6 mois',
                'biomarqueurs': ['Panel hormonal', 'Stress oxydatif', 'Micronutriments']
            }
        ]
    }
    
    # Génération du rapport
    output = generate_multimodal_report(
        patient_data=patient_example,
        biology_data=biology_example,
        microbiome_data=microbiome_example,
        cross_analysis=cross_analysis_example,
        recommendations=recommendations_example,
        follow_up=follow_up_example,
        output_path="exemple_rapport_algo_life.pdf"
    )
    
    print(f"\n🎉 Rapport d'exemple généré: {output}")
