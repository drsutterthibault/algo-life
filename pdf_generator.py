"""
ALGO-LIFE - Générateur de Rapports PDF Multimodaux ULTRA-AMÉLIORÉ
Version Beta v1.0 - AVEC JAUGES VISUELLES
Dr Thibault SUTTER - Biologiste spécialisé en biologie fonctionnelle
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, 
    PageBreak, Image, KeepTogether, ListFlowable, Flowable
)
from reportlab.graphics.shapes import Drawing, Rect, Line, Circle, String
from reportlab.graphics.charts.barcharts import VerticalBarChart, HorizontalBarChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.widgets.markers import makeMarker
from datetime import datetime
import os
from typing import Dict, List, Any, Optional


class BiomarkerGauge(Flowable):
    """Jauge visuelle pour afficher un biomarqueur avec sa position par rapport aux valeurs de référence"""
    
    def __init__(self, name: str, value: float, ref_min: float, ref_max: float, unit: str = "", 
                 width: float = 15*cm, height: float = 1.5*cm):
        Flowable.__init__(self)
        self.name = name
        self.value = value
        self.ref_min = ref_min
        self.ref_max = ref_max
        self.unit = unit
        self.width = width
        self.height = height
        
    def draw(self):
        # Définir les couleurs
        COLOR_LOW = colors.HexColor('#FF9800')  # Orange
        COLOR_NORMAL = colors.HexColor('#4CAF50')  # Vert
        COLOR_HIGH = colors.HexColor('#F44336')  # Rouge
        COLOR_BG = colors.HexColor('#E0E0E0')  # Gris clair
        
        # Dimensions de la jauge
        gauge_width = self.width - 3*cm
        gauge_height = 0.8*cm
        gauge_x = 2.5*cm
        gauge_y = 0.3*cm
        
        # Nom du biomarqueur
        self.canv.setFont('Helvetica-Bold', 10)
        self.canv.drawString(0, gauge_y + 0.3*cm, self.name)
        
        # Calculer la position de la valeur sur la jauge
        # Étendre la plage pour inclure des valeurs hors normes
        display_min = self.ref_min * 0.5
        display_max = self.ref_max * 1.5
        range_width = display_max - display_min
        
        # Position de la zone normale
        normal_start = (self.ref_min - display_min) / range_width * gauge_width
        normal_width = (self.ref_max - self.ref_min) / range_width * gauge_width
        
        # Position de la valeur
        if self.value < display_min:
            value_pos = 0
        elif self.value > display_max:
            value_pos = gauge_width
        else:
            value_pos = (self.value - display_min) / range_width * gauge_width
        
        # Dessiner le fond de la jauge (zones colorées)
        # Zone basse (orange)
        self.canv.setFillColor(COLOR_LOW)
        self.canv.setStrokeColor(COLOR_LOW)
        self.canv.rect(gauge_x, gauge_y, normal_start, gauge_height, fill=1, stroke=0)
        
        # Zone normale (vert)
        self.canv.setFillColor(COLOR_NORMAL)
        self.canv.setStrokeColor(COLOR_NORMAL)
        self.canv.rect(gauge_x + normal_start, gauge_y, normal_width, gauge_height, fill=1, stroke=0)
        
        # Zone haute (rouge)
        self.canv.setFillColor(COLOR_HIGH)
        self.canv.setStrokeColor(COLOR_HIGH)
        high_start = normal_start + normal_width
        high_width = gauge_width - high_start
        self.canv.rect(gauge_x + high_start, gauge_y, high_width, gauge_height, fill=1, stroke=0)
        
        # Bordure de la jauge
        self.canv.setStrokeColor(colors.HexColor('#757575'))
        self.canv.setLineWidth(1)
        self.canv.rect(gauge_x, gauge_y, gauge_width, gauge_height, fill=0, stroke=1)
        
        # Marqueur de la valeur (triangle inversé)
        marker_x = gauge_x + value_pos
        marker_y = gauge_y + gauge_height
        
        self.canv.setFillColor(colors.HexColor('#1976D2'))  # Bleu foncé
        self.canv.setStrokeColor(colors.HexColor('#1976D2'))
        
        # Triangle
        path = self.canv.beginPath()
        path.moveTo(marker_x, marker_y + 0.3*cm)
        path.lineTo(marker_x - 0.15*cm, marker_y)
        path.lineTo(marker_x + 0.15*cm, marker_y)
        path.close()
        self.canv.drawPath(path, fill=1, stroke=1)
        
        # Ligne verticale du marqueur
        self.canv.setLineWidth(2)
        self.canv.line(marker_x, marker_y, marker_x, gauge_y)
        
        # Afficher la valeur et l'unité
        self.canv.setFont('Helvetica-Bold', 11)
        self.canv.setFillColor(colors.HexColor('#1976D2'))
        value_text = f"{self.value} {self.unit}"
        self.canv.drawString(marker_x - 0.7*cm, marker_y + 0.4*cm, value_text)
        
        # Afficher les valeurs de référence
        self.canv.setFont('Helvetica', 8)
        self.canv.setFillColor(colors.HexColor('#757575'))
        
        # Min
        self.canv.drawString(gauge_x, gauge_y - 0.3*cm, f"{self.ref_min}")
        # Max
        max_text = f"{self.ref_max}"
        self.canv.drawRightString(gauge_x + gauge_width, gauge_y - 0.3*cm, max_text)
        # Label "Référence"
        self.canv.drawCentredString(gauge_x + gauge_width/2, gauge_y - 0.3*cm, f"Référence: {self.ref_min}-{self.ref_max} {self.unit}")


class ScoreCircle(Flowable):
    """Cercle de score pour afficher un pourcentage (ex: diversité microbiote)"""
    
    def __init__(self, score: float, title: str, width: float = 4*cm, height: float = 4*cm):
        Flowable.__init__(self)
        self.score = score
        self.title = title
        self.width = width
        self.height = height
        
    def draw(self):
        # Centre du cercle
        cx = self.width / 2
        cy = self.height / 2 - 0.3*cm
        radius = 1.2*cm
        
        # Couleur selon le score
        if self.score >= 80:
            color = colors.HexColor('#4CAF50')
        elif self.score >= 60:
            color = colors.HexColor('#FF9800')
        else:
            color = colors.HexColor('#F44336')
        
        # Fond gris
        self.canv.setFillColor(colors.HexColor('#E0E0E0'))
        self.canv.setStrokeColor(colors.HexColor('#E0E0E0'))
        self.canv.circle(cx, cy, radius, fill=1, stroke=0)
        
        # Arc de progression
        self.canv.setFillColor(color)
        self.canv.setStrokeColor(color)
        self.canv.setLineWidth(8)
        
        # Dessiner l'arc (approximation avec wedge)
        angle = (self.score / 100) * 360
        path = self.canv.beginPath()
        path.moveTo(cx, cy)
        path.arcTo(cx - radius, cy - radius, cx + radius, cy + radius, 90, angle)
        path.close()
        self.canv.drawPath(path, fill=1, stroke=0)
        
        # Cercle intérieur blanc
        self.canv.setFillColor(colors.white)
        self.canv.circle(cx, cy, radius - 0.25*cm, fill=1, stroke=0)
        
        # Score au centre
        self.canv.setFont('Helvetica-Bold', 20)
        self.canv.setFillColor(color)
        score_text = f"{int(self.score)}"
        self.canv.drawCentredString(cx, cy - 0.2*cm, score_text)
        
        self.canv.setFont('Helvetica', 9)
        self.canv.drawCentredString(cx, cy - 0.5*cm, "/100")
        
        # Titre en dessous
        self.canv.setFont('Helvetica-Bold', 10)
        self.canv.setFillColor(colors.HexColor('#333333'))
        self.canv.drawCentredString(cx, cy - radius - 0.5*cm, self.title)


class PDFGenerator:
    """Générateur de rapports PDF multimodaux ultra-amélioré pour ALGO-LIFE"""
    
    # Couleurs ALGO-LIFE
    COLOR_PRIMARY = colors.HexColor('#5B5FCF')
    COLOR_SECONDARY = colors.HexColor('#8B7FCF')
    COLOR_SUCCESS = colors.HexColor('#4CAF50')
    COLOR_WARNING = colors.HexColor('#FF9800')
    COLOR_DANGER = colors.HexColor('#F44336')
    COLOR_INFO = colors.HexColor('#2196F3')
    COLOR_GREY = colors.HexColor('#757575')
    COLOR_LIGHT_GREY = colors.HexColor('#E0E0E0')
    
    def __init__(self, output_path: str):
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
        
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=self.COLOR_PRIMARY,
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        self.styles.add(ParagraphStyle(
            name='CustomSubtitle',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=self.COLOR_GREY,
            spaceAfter=20,
            alignment=TA_CENTER,
            fontName='Helvetica'
        ))
        
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
        
        self.styles.add(ParagraphStyle(
            name='SubsectionTitle',
            parent=self.styles['Heading3'],
            fontSize=13,
            textColor=self.COLOR_SECONDARY,
            spaceAfter=10,
            spaceBefore=15,
            fontName='Helvetica-Bold'
        ))
        
        self.styles.add(ParagraphStyle(
            name='CustomBody',
            parent=self.styles['BodyText'],
            fontSize=10,
            alignment=TA_JUSTIFY,
            spaceAfter=10,
            leading=14
        ))
        
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
        
        title = Paragraph("🧬 ALGO-LIFE", self.styles['CustomTitle'])
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
            ["IMC:", f"{patient_data.get('imc', 'N/A'):.1f} kg/m²"],
            ["Activité:", patient_data.get('activite', 'N/A')],
        ]
        
        date_rapport = datetime.now().strftime("%d/%m/%Y")
        patient_info.append(["Date du rapport:", date_rapport])
        
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
        
    def _parse_reference_range(self, reference: str) -> tuple:
        """Parse la plage de référence"""
        try:
            if '-' in reference:
                parts = reference.split('-')
                return float(parts[0]), float(parts[1])
            elif '<' in reference:
                max_val = float(reference.replace('<', '').strip())
                return 0, max_val
            elif '>' in reference:
                min_val = float(reference.replace('>', '').strip())
                return min_val, min_val * 2
            else:
                val = float(reference)
                return val * 0.8, val * 1.2
        except:
            return 0, 100
    
    def add_biology_section(self, bio_data: Dict[str, Any]):
        """Section analyse biologique AVEC JAUGES VISUELLES"""
        
        self.add_section("📊 ANALYSE BIOLOGIQUE", level=1)
        
        if 'resume' in bio_data:
            self.story.append(Paragraph(
                f"<b>Résumé:</b> {bio_data['resume']}",
                self.styles['CustomBody']
            ))
            self.story.append(Spacer(1, 0.5*cm))
        
        if 'categories' in bio_data:
            for category, markers in bio_data['categories'].items():
                self.add_section(f"🔬 {category}", level=2)
                
                for marker in markers:
                    # Extraire les valeurs min/max de référence
                    ref_str = marker.get('reference', '0-100')
                    ref_min, ref_max = self._parse_reference_range(ref_str)
                    
                    value = marker.get('valeur', 0)
                    if isinstance(value, str):
                        try:
                            value = float(value)
                        except:
                            value = 0
                    
                    # Ajouter la jauge
                    gauge = BiomarkerGauge(
                        name=marker.get('nom', 'N/A'),
                        value=value,
                        ref_min=ref_min,
                        ref_max=ref_max,
                        unit=marker.get('unite', ''),
                        width=16*cm,
                        height=1.8*cm
                    )
                    self.story.append(gauge)
                    self.story.append(Spacer(1, 0.3*cm))
                    
                    # Interprétations
                    if marker.get('interpretations'):
                        for interp in marker['interpretations']:
                            if interp:  # Vérifier que l'interprétation n'est pas vide
                                self.story.append(Paragraph(
                                    f"→ {interp}",
                                    self.styles['Recommendation']
                                ))
                        self.story.append(Spacer(1, 0.5*cm))
    
    def add_microbiome_section(self, microbiome_data: Dict[str, Any]):
        """Section analyse microbiote"""
        
        self.add_section("🦠 ANALYSE MICROBIOTE", level=1)
        
        # Score de diversité avec cercle visuel
        if 'diversite' in microbiome_data:
            div_score = microbiome_data['diversite'].get('score', 0)
            
            score_circle = ScoreCircle(
                score=div_score,
                title="Score de Diversité",
                width=5*cm,
                height=5*cm
            )
            
            self.story.append(score_circle)
            self.story.append(Spacer(1, 0.5*cm))
            
            interp = microbiome_data['diversite'].get('interpretation', '')
            if interp:
                self.story.append(Paragraph(
                    f"<b>Interprétation:</b> {interp}",
                    self.styles['CustomBody']
                ))
                self.story.append(Spacer(1, 0.5*cm))
        
        # Phyla dominants
        if 'phyla' in microbiome_data and microbiome_data['phyla']:
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
        if 'especes_cles' in microbiome_data and microbiome_data['especes_cles']:
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
        if 'fonctions_metaboliques' in microbiome_data and microbiome_data['fonctions_metaboliques']:
            self.add_section("Capacités Métaboliques", level=2)
            
            for fonction in microbiome_data['fonctions_metaboliques']:
                self.story.append(Paragraph(
                    f"• <b>{fonction.get('nom', '')}:</b> {fonction.get('evaluation', '')}",
                    self.styles['CustomBody']
                ))
            self.story.append(Spacer(1, 0.3*cm))
    
    def add_cross_analysis_section(self, cross_data: Dict[str, Any]):
        """Section analyse croisée biologie × microbiote AMÉLIORÉE"""
        
        self.add_section("🔗 ANALYSE CROISÉE MULTIMODALE", level=1)
        
        self.story.append(Paragraph(
            "Cette section présente les corrélations identifiées entre vos analyses biologiques et votre profil microbiote, "
            "permettant une compréhension intégrée de votre santé métabolique.",
            self.styles['CustomBody']
        ))
        self.story.append(Spacer(1, 0.5*cm))
        
        # Corrélations majeures
        if 'correlations' in cross_data and cross_data['correlations']:
            self.add_section("🔍 Corrélations Identifiées", level=2)
            
            for i, corr in enumerate(cross_data['correlations'], 1):
                severity = corr.get('severite', 'faible')
                icon = "🔴" if severity == "elevee" else "🟡" if severity == "moyenne" else "🟢"
                
                # Encadré pour chaque corrélation
                corr_title = Paragraph(
                    f"{icon} <b>Corrélation {i}:</b> {corr.get('titre', '')}",
                    self.styles['SubsectionTitle']
                )
                self.story.append(corr_title)
                
                # Tableau détaillé
                corr_data = [
                    ["Biomarqueur", corr.get('biomarqueur', 'N/A')],
                    ["Élément microbiote", corr.get('microbiote_element', 'N/A')],
                    ["Interprétation", corr.get('interpretation', '')],
                ]
                
                if corr.get('mecanisme'):
                    corr_data.append(["Mécanisme", corr.get('mecanisme', '')])
                
                table = Table(corr_data, colWidths=[4*cm, 12*cm])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F5F5F5')),
                    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('GRID', (0, 0), (-1, -1), 0.5, self.COLOR_LIGHT_GREY),
                    ('TOPPADDING', (0, 0), (-1, -1), 8),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ]))
                
                self.story.append(table)
                self.story.append(Spacer(1, 0.5*cm))
        
        # Axes d'intervention prioritaires
        if 'axes_intervention' in cross_data and cross_data['axes_intervention']:
            self.add_section("🎯 Axes d'Intervention Prioritaires", level=2)
            
            for i, axe in enumerate(cross_data['axes_intervention'], 1):
                self.story.append(Paragraph(
                    f"<b>{i}. {axe.get('titre', '')}</b>",
                    self.styles['SubsectionTitle']
                ))
                
                self.story.append(Paragraph(
                    axe.get('description', ''),
                    self.styles['CustomBody']
                ))
                
                if axe.get('impact'):
                    self.story.append(Paragraph(
                        f"<b>Impact attendu:</b> {axe.get('impact', '')}",
                        self.styles['Recommendation']
                    ))
                
                self.story.append(Spacer(1, 0.3*cm))
    
    def add_recommendations_section(self, recommendations: Dict[str, Any]):
        """Section recommandations personnalisées"""
        
        self.add_section("💡 RECOMMANDATIONS PERSONNALISÉES", level=1)
        
        # Priorités
        if 'priorites' in recommendations and recommendations['priorites']:
            self.add_section("🎯 Priorités d'Action", level=2)
            
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
            
            if 'privilegier' in recommendations['nutrition'] and recommendations['nutrition']['privilegier']:
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
            
            if 'limiter' in recommendations['nutrition'] and recommendations['nutrition']['limiter']:
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
        if 'supplementation' in recommendations and recommendations['supplementation']:
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
        if 'hygiene_vie' in recommendations and recommendations['hygiene_vie']:
            self.add_section("🏃 Hygiène de Vie", level=2)
            
            for categorie, conseils in recommendations['hygiene_vie'].items():
                if conseils:  # Vérifier que la liste n'est pas vide
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
        
        if 'controles' in follow_up and follow_up['controles']:
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
        return status_map.get(status.lower() if status else 'normal', '• N/A')
    
    def generate(self, data: Dict[str, Any]):
        """Génère le rapport PDF complet"""
        
        # En-tête
        self.add_header(data.get('patient', {}))
        
        # Sections
        if 'biologie' in data and data['biologie']:
            self.add_biology_section(data['biologie'])
            self.story.append(PageBreak())
        
        if 'microbiote' in data and data['microbiote']:
            self.add_microbiome_section(data['microbiote'])
            self.story.append(PageBreak())
        
        if 'cross_analysis' in data and data['cross_analysis']:
            self.add_cross_analysis_section(data['cross_analysis'])
            self.story.append(PageBreak())
        
        if 'recommendations' in data and data['recommendations']:
            self.add_recommendations_section(data['recommendations'])
            self.story.append(PageBreak())
        
        if 'follow_up' in data and data['follow_up']:
            self.add_follow_up_section(data['follow_up'])
        
        # Pied de page
        self.add_footer()
        
        # Construction du PDF
        self.doc.build(self.story)
        
        print(f"✅ Rapport PDF généré avec succès: {self.output_path}")
        return self.output_path


def generate_multimodal_report(
    patient_data: Dict[str, Any],
    biology_data: Dict[str, Any],
    microbiome_data: Dict[str, Any],
    cross_analysis: Dict[str, Any],
    recommendations: Dict[str, Any],
    follow_up: Dict[str, Any],
    output_path: str = "rapport_multimodal.pdf"
) -> str:
    """Fonction helper pour générer un rapport complet"""
    
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
    print("PDF Generator chargé avec succès - Version ultra-améliorée avec jauges visuelles!")
