"""
ALGO-LIFE - Générateur de Rapports PDF CORRIGÉ
Version avec gestion robuste des données manquantes
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from datetime import datetime
from io import BytesIO
import matplotlib.pyplot as plt


class AlgoLifePDFGeneratorCorrected:
    """
    Générateur de rapports PDF professionnels avec analyses statistiques
    VERSION CORRIGÉE avec validation des données
    """
    
    # Couleurs du thème
    PRIMARY_COLOR = colors.HexColor('#2C3E50')
    SECONDARY_COLOR = colors.HexColor('#3498DB')
    ACCENT_COLOR = colors.HexColor('#E74C3C')
    SUCCESS_COLOR = colors.HexColor('#2ECC71')
    BACKGROUND_COLOR = colors.HexColor('#ECF0F1')
    
    def __init__(self, patient_name, analysis_results, chart_buffer=None):
        """
        Initialise le générateur de PDF
        
        Args:
            patient_name: Nom du patient
            analysis_results: Dictionnaire avec tous les résultats d'analyse
            chart_buffer: Buffer contenant les graphiques (BytesIO)
        """
        self.patient_name = patient_name or "Patient Inconnu"
        self.analysis_results = analysis_results or {}
        self.chart_buffer = chart_buffer
        self.buffer = BytesIO()
        self.styles = self._create_styles()
        
        # ✅ VALIDATION DES DONNÉES
        self._validate_data()
        
    def _validate_data(self):
        """Valide et complète les données si nécessaire"""
        print(f"\n🔍 Validation des données pour {self.patient_name}...")
        
        # Vérifier composite_indices
        if not self.analysis_results.get('composite_indices'):
            print("⚠️  Aucun indice composite trouvé!")
            self.analysis_results['composite_indices'] = {}
        else:
            n_indices = len(self.analysis_results['composite_indices'])
            print(f"✅ {n_indices} indices composites trouvés")
        
        # Vérifier statistical_model
        if not self.analysis_results.get('statistical_model'):
            print("⚠️  Aucun modèle statistique trouvé!")
            self.analysis_results['statistical_model'] = {'success': False}
        else:
            success = self.analysis_results['statistical_model'].get('success', False)
            print(f"{'✅' if success else '⚠️ '} Modèle statistique: {success}")
        
        # Vérifier recommendations
        if not self.analysis_results.get('recommendations'):
            print("⚠️  Aucune recommandation trouvée!")
            self.analysis_results['recommendations'] = []
        else:
            n_recs = len(self.analysis_results['recommendations'])
            print(f"✅ {n_recs} recommandations trouvées")
        
        # Vérifier patient_info
        if not self.analysis_results.get('patient_info'):
            self.analysis_results['patient_info'] = {}
            print("⚠️  Aucune info patient trouvée - utilisation de données par défaut")
    
    def _create_styles(self):
        """Crée les styles personnalisés"""
        styles = getSampleStyleSheet()
        
        styles.add(ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=self.PRIMARY_COLOR,
            spaceAfter=20,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        styles.add(ParagraphStyle(
            'CustomHeading1',
            parent=styles['Heading1'],
            fontSize=16,
            textColor=self.PRIMARY_COLOR,
            spaceAfter=12,
            spaceBefore=12,
            fontName='Helvetica-Bold',
            borderWidth=2,
            borderColor=self.SECONDARY_COLOR,
            borderPadding=5,
            backColor=self.BACKGROUND_COLOR
        ))
        
        styles.add(ParagraphStyle(
            'CustomHeading2',
            parent=styles['Heading2'],
            fontSize=13,
            textColor=self.SECONDARY_COLOR,
            spaceAfter=10,
            spaceBefore=10,
            fontName='Helvetica-Bold'
        ))
        
        styles.add(ParagraphStyle(
            'CustomBody',
            parent=styles['BodyText'],
            fontSize=10,
            textColor=colors.black,
            spaceAfter=8,
            alignment=TA_JUSTIFY,
            fontName='Helvetica'
        ))
        
        styles.add(ParagraphStyle(
            'Highlight',
            fontSize=11,
            textColor=colors.white,
            backColor=self.SECONDARY_COLOR,
            borderWidth=1,
            borderColor=self.PRIMARY_COLOR,
            borderPadding=8,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold',
            spaceAfter=10
        ))
        
        return styles
    
    def _create_header_footer(self, canvas_obj, doc):
        """Crée en-tête et pied de page"""
        canvas_obj.saveState()
        
        # En-tête
        canvas_obj.setFillColor(self.PRIMARY_COLOR)
        canvas_obj.rect(0, A4[1] - 2*cm, A4[0], 2*cm, fill=1, stroke=0)
        
        canvas_obj.setFillColor(colors.white)
        canvas_obj.setFont('Helvetica-Bold', 18)
        canvas_obj.drawString(2*cm, A4[1] - 1.3*cm, 'ALGO-LIFE')
        
        canvas_obj.setFont('Helvetica', 10)
        canvas_obj.drawString(2*cm, A4[1] - 1.7*cm, 'Analyse Bio-Fonctionnelle Avancée')
        
        # Date
        canvas_obj.setFont('Helvetica', 8)
        date_str = datetime.now().strftime('%d/%m/%Y')
        canvas_obj.drawRightString(A4[0] - 2*cm, A4[1] - 1.5*cm, f'Date: {date_str}')
        
        # Pied de page
        canvas_obj.setFillColor(self.PRIMARY_COLOR)
        canvas_obj.setFont('Helvetica', 8)
        page_num = canvas_obj.getPageNumber()
        canvas_obj.drawCentredString(A4[0]/2, 1.5*cm, f"Page {page_num}")
        
        canvas_obj.setFillColor(self.ACCENT_COLOR)
        canvas_obj.drawString(2*cm, 1*cm, '© ALGO-LIFE 2025 - Confidentiel')
        
        canvas_obj.restoreState()
    
    def generate_pdf(self):
        """
        Génère le rapport PDF complet
        """
        doc = SimpleDocTemplate(
            self.buffer,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=3*cm,
            bottomMargin=2.5*cm
        )
        
        story = []
        
        # PAGE 1 - Couverture
        story.extend(self._create_cover_page())
        story.append(PageBreak())
        
        # PAGE 2 - Indices Composites
        story.extend(self._create_composite_indices_page())
        story.append(PageBreak())
        
        # PAGE 3 - Analyse Statistique
        story.extend(self._create_statistical_analysis_page())
        story.append(PageBreak())
        
        # PAGE 4 - Visualisations
        if self.chart_buffer:
            story.extend(self._create_visualizations_page())
            story.append(PageBreak())
        
        # PAGE 5 - Recommandations
        story.extend(self._create_recommendations_page())
        
        # Construire le PDF
        doc.build(story, onFirstPage=self._create_header_footer, 
                 onLaterPages=self._create_header_footer)
        
        self.buffer.seek(0)
        return self.buffer
    
    def _create_cover_page(self):
        """Crée la page de couverture"""
        elements = []
        
        elements.append(Spacer(1, 2*cm))
        
        # Titre
        title = Paragraph("RAPPORT D'ANALYSE", self.styles['CustomTitle'])
        elements.append(title)
        
        subtitle = Paragraph(
            "Analyse Bio-Fonctionnelle Multi-Dimensionnelle",
            self.styles['CustomHeading2']
        )
        elements.append(subtitle)
        
        elements.append(Spacer(1, 1.5*cm))
        
        # Informations patient
        patient_info = self.analysis_results.get('patient_info', {})
        
        info_data = [
            ['Patient:', self.patient_name],
            ['Date d\'analyse:', datetime.now().strftime('%d/%m/%Y')],
            ['Type d\'analyse:', 'Statistique Multi-Dimensionnelle'],
        ]
        
        if patient_info.get('age'):
            info_data.append(['Âge:', f"{patient_info['age']} ans"])
        if patient_info.get('sexe'):
            info_data.append(['Sexe:', patient_info['sexe']])
        
        # Ajouter R² si disponible
        model_results = self.analysis_results.get('statistical_model', {})
        if model_results.get('success'):
            info_data.append(['Score prédictif (R²):', f"{model_results.get('r2_score', 0):.3f}"])
            info_data.append(['Variables analysées:', str(model_results.get('n_features', 'N/A'))])
        
        info_table = Table(info_data, colWidths=[7*cm, 8*cm])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), self.BACKGROUND_COLOR),
            ('BACKGROUND', (1, 0), (1, -1), colors.white),
            ('TEXTCOLOR', (0, 0), (-1, -1), self.PRIMARY_COLOR),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('GRID', (0, 0), (-1, -1), 1, self.PRIMARY_COLOR),
            ('LEFTPADDING', (0, 0), (-1, -1), 12),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(info_table)
        
        elements.append(Spacer(1, 2*cm))
        
        # Résumé exécutif
        elements.append(Paragraph("RÉSUMÉ EXÉCUTIF", self.styles['CustomHeading1']))
        
        summary_text = self._generate_executive_summary()
        if summary_text:
            elements.append(Paragraph(summary_text, self.styles['CustomBody']))
        else:
            elements.append(Paragraph(
                "<i>Analyse en cours - Résumé sera disponible après traitement complet des biomarqueurs</i>",
                self.styles['CustomBody']
            ))
        
        return elements
    
    def _generate_executive_summary(self):
        """Génère le résumé exécutif"""
        indices = self.analysis_results.get('composite_indices', {})
        
        if not indices:
            return ""
        
        summary_parts = []
        
        # Stress
        if 'stress' in indices:
            stress_score = indices['stress'].get('score', 0)
            stress_interp = indices['stress'].get('interpretation', 'Non disponible')
            summary_parts.append(
                f"<b>Stress:</b> Score {stress_score:.0f}/100 - {stress_interp}"
            )
        
        # Métabolisme
        if 'metabolic' in indices:
            metab_score = indices['metabolic'].get('score', 0)
            metab_interp = indices['metabolic'].get('interpretation', 'Non disponible')
            summary_parts.append(
                f"<b>Métabolisme:</b> Score {metab_score:.0f}/100 - {metab_interp}"
            )
        
        # Inflammation
        if 'inflammation' in indices:
            inflam_score = indices['inflammation'].get('score', 0)
            inflam_interp = indices['inflammation'].get('interpretation', 'Non disponible')
            summary_parts.append(
                f"<b>Inflammation:</b> Score {inflam_score:.0f}/100 - {inflam_interp}"
            )
        
        # Neurotransmetteurs
        if 'neurotransmitters' in indices:
            neuro_score = indices['neurotransmitters'].get('score', 0)
            neuro_interp = indices['neurotransmitters'].get('interpretation', 'Non disponible')
            summary_parts.append(
                f"<b>Neurotransmetteurs:</b> Score {neuro_score:.0f}/100 - {neuro_interp}"
            )
        
        if not summary_parts:
            return ""
        
        summary = "<br/><br/>".join(summary_parts)
        
        # Ajouter conclusion statistique
        model_results = self.analysis_results.get('statistical_model', {})
        if model_results.get('success'):
            r2 = model_results.get('r2_score', 0)
            summary += f"<br/><br/><b>Modèle prédictif:</b> R² = {r2:.3f}, "
            summary += f"expliquant {r2*100:.1f}% de la variance observée."
        
        return summary
    
    def _create_composite_indices_page(self):
        """Crée la page des indices composites"""
        elements = []
        
        elements.append(Paragraph("INDICES COMPOSITES", self.styles['CustomTitle']))
        elements.append(Spacer(1, 0.5*cm))
        
        indices = self.analysis_results.get('composite_indices', {})
        
        if not indices:
            elements.append(Paragraph(
                "<i>Aucun indice composite calculé. Veuillez vérifier que les biomarqueurs ont été correctement analysés.</i>",
                self.styles['CustomBody']
            ))
            return elements
        
        # Table des indices
        table_data = [['Indice', 'Score', 'Interprétation', 'Statut']]
        
        for key, result in indices.items():
            index_name = key.replace('_', ' ').title()
            score = result.get('score', 0)
            interpretation = result.get('interpretation', 'Non disponible')
            
            # Déterminer le statut
            if 'stress' in key or 'inflammation' in key:
                # Inverser pour ces indices (plus bas = mieux)
                if score < 30:
                    status = "✓ Optimal"
                elif score < 60:
                    status = "⚠ Surveillance"
                else:
                    status = "✗ Action requise"
            else:
                if score >= 70:
                    status = "✓ Optimal"
                elif score >= 50:
                    status = "⚠ Surveillance"
                else:
                    status = "✗ Action requise"
            
            table_data.append([
                index_name,
                f"{score:.0f}/100",
                interpretation,
                status
            ])
        
        indices_table = Table(table_data, colWidths=[3.5*cm, 2*cm, 6.5*cm, 3*cm])
        indices_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.PRIMARY_COLOR),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (2, -1), 'LEFT'),
            ('ALIGN', (3, 0), (3, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 1, self.PRIMARY_COLOR),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, self.BACKGROUND_COLOR]),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        elements.append(indices_table)
        elements.append(Spacer(1, 1*cm))
        
        # Détails pour chaque indice
        for key, result in indices.items():
            elements.append(Paragraph(
                key.replace('_', ' ').title(),
                self.styles['CustomHeading2']
            ))
            
            # Détails spécifiques
            details_text = ""
            
            if 'stress' in key:
                phase = result.get('phase', 'N/A')
                score = result.get('score', 0)
                interpretation = result.get('interpretation', 'N/A')
                details_text = f"<b>Phase identifiée:</b> {phase}<br/>"
                details_text += f"<b>Score:</b> {score:.0f}/100<br/>"
                details_text += f"<b>Interprétation:</b> {interpretation}"
            
            elif 'metabolic' in key:
                issues = result.get('issues', [])
                score = result.get('score', 0)
                risk_level = result.get('risk_level', 'N/A')
                details_text = f"<b>Score santé métabolique:</b> {score:.0f}/100<br/>"
                details_text += f"<b>Niveau de risque:</b> {risk_level}<br/>"
                if issues:
                    details_text += "<b>Points d'attention:</b><br/>"
                    for issue in issues:
                        details_text += f"• {issue}<br/>"
            
            elif 'inflammation' in key:
                sources = result.get('sources', [])
                score = result.get('score', 0)
                priority = result.get('priority', 'N/A')
                details_text = f"<b>Score inflammation:</b> {score:.0f}/100<br/>"
                details_text += f"<b>Priorité:</b> {priority}<br/>"
                if sources:
                    details_text += "<b>Sources d'inflammation:</b><br/>"
                    for source in sources:
                        details_text += f"• {source}<br/>"
            
            elif 'neurotransmitters' in key:
                score = result.get('score', 0)
                recommendation = result.get('recommendation', 'N/A')
                details_text = f"<b>Score équilibre:</b> {score:.0f}/100<br/>"
                details_text += f"<b>Recommandation:</b> {recommendation}"
            
            if details_text:
                elements.append(Paragraph(details_text, self.styles['CustomBody']))
            
            elements.append(Spacer(1, 0.5*cm))
        
        return elements
    
    def _create_statistical_analysis_page(self):
        """Crée la page d'analyse statistique"""
        elements = []
        
        elements.append(Paragraph("ANALYSE STATISTIQUE", self.styles['CustomTitle']))
        elements.append(Spacer(1, 0.5*cm))
        
        model_results = self.analysis_results.get('statistical_model', {})
        
        if not model_results.get('success'):
            elements.append(Paragraph(
                "Analyse statistique non disponible - Données insuffisantes",
                self.styles['CustomBody']
            ))
            return elements
        
        # Métriques du modèle
        elements.append(Paragraph("Performance du Modèle Prédictif", self.styles['CustomHeading1']))
        
        r2 = model_results.get('r2_score', 0)
        n_features = model_results.get('n_features', 'N/A')
        
        quality = 'excellente' if r2 > 0.7 else 'bonne' if r2 > 0.5 else 'modérée'
        
        metrics_text = f"""
        <b>R² (Coefficient de détermination):</b> {r2:.3f}<br/>
        <b>Interprétation:</b> Le modèle explique {r2*100:.1f}% de la variance,
        démontrant une {quality} capacité prédictive.<br/>
        <b>Variables analysées:</b> {n_features} paramètres biologiques
        """
        elements.append(Paragraph(metrics_text, self.styles['CustomBody']))
        
        elements.append(Spacer(1, 0.8*cm))
        
        # Top facteurs
        elements.append(Paragraph("Facteurs Principaux (par ordre d'impact)", self.styles['CustomHeading1']))
        
        coefficients = model_results.get('coefficients')
        if coefficients is not None and hasattr(coefficients, 'head'):
            top_factors = coefficients.head(5)
            
            factors_data = [['Rang', 'Facteur', 'Coefficient', 'Impact', 'Interprétation']]
            
            for i, (idx, row) in enumerate(top_factors.iterrows(), 1):
                factor_name = row.get('Feature', str(idx)).replace('_', ' ').title()
                coef = row.get('Coefficient', 0)
                
                if coef > 0:
                    impact = "Protecteur"
                    interpretation = "À maintenir/améliorer"
                else:
                    impact = "Délétère"
                    interpretation = "À corriger prioritairement"
                
                factors_data.append([
                    str(i),
                    factor_name,
                    f"{coef:+.3f}",
                    impact,
                    interpretation
                ])
            
            factors_table = Table(factors_data, colWidths=[1*cm, 4*cm, 2*cm, 2.5*cm, 5.5*cm])
            factors_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), self.SECONDARY_COLOR),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('ALIGN', (0, 0), (0, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 1, self.PRIMARY_COLOR),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, self.BACKGROUND_COLOR]),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
            ]))
            
            elements.append(factors_table)
        else:
            elements.append(Paragraph(
                "<i>Détail des coefficients non disponible</i>",
                self.styles['CustomBody']
            ))
        
        return elements
    
    def _create_visualizations_page(self):
        """Crée la page de visualisations"""
        elements = []
        
        elements.append(Paragraph("VISUALISATIONS GRAPHIQUES", self.styles['CustomTitle']))
        elements.append(Spacer(1, 0.5*cm))
        
        if self.chart_buffer:
            # Ajouter l'image des graphiques
            img = Image(self.chart_buffer, width=17*cm, height=10.5*cm)
            elements.append(img)
            
            elements.append(Spacer(1, 0.5*cm))
            
            # Légende
            legend_text = """
            <b>Interprétation des graphiques:</b><br/><br/>
            
            <b>Haut gauche - Impact des facteurs:</b> Les coefficients standardisés indiquent l'ampleur 
            et la direction de l'effet de chaque facteur. Les barres vertes représentent des effets 
            protecteurs, les rouges des effets délétères.<br/><br/>
            
            <b>Haut centre - Profil radar:</b> Visualisation globale des 4 axes de santé. Plus la surface 
            couverte est grande, meilleur est le profil global. Les écarts avec la zone optimale (ligne 
            bleue) identifient les axes à travailler prioritairement.<br/><br/>
            
            <b>Bas gauche - Profil cortisol:</b> Le rythme circadien du cortisol reflète l'adaptation au 
            stress. Un CAR effondré (<7.5) suggère un épuisement surrénalien nécessitant une intervention.<br/><br/>
            
            <b>Bas centre - Neurotransmetteurs:</b> L'équilibre des neurotransmetteurs influence l'humeur, 
            la motivation et le bien-être. La zone optimale se situe entre 40-70%.<br/><br/>
            
            <b>Bas droite - Distribution indices:</b> Vue d'ensemble de tous les indices composites. 
            Les barres vertes (>70%) indiquent des zones optimales, orange (50-70%) nécessitent une 
            surveillance, rouges (<50%) requièrent une intervention.
            """
            elements.append(Paragraph(legend_text, self.styles['CustomBody']))
        else:
            elements.append(Paragraph(
                "Visualisations non disponibles",
                self.styles['CustomBody']
            ))
        
        return elements
    
    def _create_recommendations_page(self):
        """Crée la page de recommandations"""
        elements = []
        
        elements.append(Paragraph("PLAN D'ACTION PERSONNALISÉ", self.styles['CustomTitle']))
        elements.append(Spacer(1, 0.5*cm))
        
        recommendations = self.analysis_results.get('recommendations', [])
        
        if not recommendations:
            elements.append(Paragraph(
                "Aucune recommandation spécifique - Profil optimal",
                self.styles['CustomBody']
            ))
            return elements
        
        # Introduction
        intro_text = """
        Les recommandations suivantes sont basées sur l'analyse statistique multi-dimensionnelle de vos 
        biomarqueurs. Elles sont hiérarchisées par ordre d'impact potentiel sur votre santé globale et 
        personnalisées selon votre profil biologique unique.
        """
        elements.append(Paragraph(intro_text, self.styles['CustomBody']))
        elements.append(Spacer(1, 0.5*cm))
        
        # Recommandations par priorité
        for i, rec in enumerate(recommendations[:5], 1):  # Top 5
            priority = rec.get('priority', 3)
            category = rec.get('category', 'Général')
            issue = rec.get('issue', 'Non spécifié')
            action = rec.get('action', 'Non spécifié')
            interventions = rec.get('interventions', [])
            impact = rec.get('expected_impact', 'Modéré')
            
            # Titre de la recommandation
            priority_label = "🔴 PRIORITÉ 1" if priority == 1 else "🟡 PRIORITÉ 2" if priority == 2 else "🟢 PRIORITÉ 3"
            
            elements.append(Paragraph(
                f"{priority_label} - {category}",
                self.styles['CustomHeading2']
            ))
            
            # Détails
            rec_text = f"<b>Constat:</b> {issue}<br/>"
            rec_text += f"<b>Objectif:</b> {action}<br/>"
            rec_text += f"<b>Impact attendu:</b> {impact}<br/><br/>"
            
            if interventions:
                rec_text += "<b>Interventions recommandées:</b><br/>"
                for intervention in interventions:
                    rec_text += f"  • {intervention}<br/>"
            
            elements.append(Paragraph(rec_text, self.styles['CustomBody']))
            elements.append(Spacer(1, 0.5*cm))
        
        # Conclusion
        elements.append(Spacer(1, 0.8*cm))
        elements.append(Paragraph("SUIVI ET RÉÉVALUATION", self.styles['CustomHeading1']))
        
        conclusion_text = """
        <b>Calendrier de suivi recommandé:</b><br/><br/>
        
        • <b>Court terme (1 mois):</b> Mise en place des interventions priorité 1, suivi des symptômes<br/>
        • <b>Moyen terme (3 mois):</b> Réévaluation des biomarqueurs clés, ajustement du protocole<br/>
        • <b>Long terme (6-12 mois):</b> Bilan complet avec nouvelle analyse statistique<br/><br/>
        
        <b>Indicateurs de succès:</b><br/>
        • Amélioration des indices composites (cible: >70%)<br/>
        • Normalisation des biomarqueurs hors norme<br/>
        • Amélioration subjective de la qualité de vie<br/>
        • Validation statistique des interventions (R² stable ou en hausse)
        """
        elements.append(Paragraph(conclusion_text, self.styles['CustomBody']))
        
        return elements


# ✅ FONCTION HELPER CORRIGÉE
def generate_algolife_pdf_report_corrected(patient_data, biomarker_results, engine_results, chart_buffer=None):
    """
    Fonction helper CORRIGÉE pour générer un rapport PDF depuis Streamlit
    
    Args:
        patient_data: Dictionnaire avec les données du patient (doit contenir 'nom')
        biomarker_results: Résultats des biomarqueurs (dict ou DataFrame)
        engine_results: Résultats du moteur d'analyse (doit contenir 'composite_indices', 'statistical_model', 'recommendations')
        chart_buffer: Buffer des graphiques (BytesIO) optionnel
    
    Returns:
        BytesIO: Buffer contenant le PDF
    """
    
    # ✅ VALIDATION STRICTE DES DONNÉES
    print("\n" + "="*80)
    print("GÉNÉRATION PDF ALGO-LIFE - VALIDATION DES DONNÉES")
    print("="*80)
    
    # Validation patient_data
    if not isinstance(patient_data, dict):
        print("❌ ERREUR: patient_data n'est pas un dictionnaire!")
        patient_data = {}
    
    patient_name = patient_data.get('nom', 'Patient Inconnu')
    print(f"✅ Patient: {patient_name}")
    
    # Validation engine_results
    if not isinstance(engine_results, dict):
        print("❌ ERREUR: engine_results n'est pas un dictionnaire!")
        engine_results = {}
    
    if not engine_results:
        print("⚠️  WARNING: engine_results est VIDE - Le rapport sera incomplet!")
    
    # Construire analysis_results à partir des données fournies
    analysis_results = {
        'patient_info': patient_data,
        'composite_indices': engine_results.get('composite_indices', {}),
        'statistical_model': engine_results.get('statistical_model', {}),
        'recommendations': engine_results.get('recommendations', [])
    }
    
    # Afficher résumé
    print(f"\nDonnées pour le PDF:")
    print(f"  - composite_indices: {len(analysis_results['composite_indices'])} indices")
    print(f"  - statistical_model success: {analysis_results['statistical_model'].get('success', False)}")
    print(f"  - recommendations: {len(analysis_results['recommendations'])} recommandations")
    print(f"  - chart_buffer: {'Présent' if chart_buffer else 'Absent'}")
    print("="*80 + "\n")
    
    # Créer et retourner le PDF
    generator = AlgoLifePDFGeneratorCorrected(patient_name, analysis_results, chart_buffer)
    return generator.generate_pdf()


__all__ = ['AlgoLifePDFGeneratorCorrected', 'generate_algolife_pdf_report_corrected']
