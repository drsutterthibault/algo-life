"""
Moteur de règles pour générer des recommandations personnalisées
basées sur les résultats biologiques et microbiote
"""

import pandas as pd
import numpy as np
import os
from typing import Dict, List, Optional, Union
from extractors import normalize_biomarker_name, determine_biomarker_status


class RulesEngine:
    """
    Moteur de règles pour l'analyse multimodale et la génération de recommandations
    """
    
    def __init__(self, rules_excel_path: str):
        """
        Initialise le moteur de règles avec le fichier Excel des règles
        
        Args:
            rules_excel_path: Chemin vers le fichier Excel contenant les règles
        """
        self.rules_excel_path = rules_excel_path
        self.rules_bio_base = None
        self.rules_bio_extended = None
        self.rules_bio_functional = None
        self.rules_microbiome = None
        self.rules_metabolites = None
        
        self._load_rules()
    
    def _load_rules(self):
        """Charge toutes les feuilles de règles depuis le fichier Excel"""
        try:
            # Vérifier que le fichier existe
            if not os.path.exists(self.rules_excel_path):
                raise FileNotFoundError(f"Le fichier {self.rules_excel_path} n'existe pas")
            
            print(f"📂 Tentative de chargement: {self.rules_excel_path}")
            print(f"📏 Taille du fichier: {os.path.getsize(self.rules_excel_path)} bytes")
            
            # Charger les règles biologiques
            print("⏳ Chargement BASE_40...")
            self.rules_bio_base = pd.read_excel(self.rules_excel_path, sheet_name='BASE_40', engine='openpyxl')
            print(f"✅ BASE_40 chargé: {len(self.rules_bio_base)} lignes")
            
            print("⏳ Chargement EXTENDED_92...")
            self.rules_bio_extended = pd.read_excel(self.rules_excel_path, sheet_name='EXTENDED_92', engine='openpyxl')
            print(f"✅ EXTENDED_92 chargé: {len(self.rules_bio_extended)} lignes")
            
            print("⏳ Chargement FONCTIONNEL_134...")
            self.rules_bio_functional = pd.read_excel(self.rules_excel_path, sheet_name='FONCTIONNEL_134', engine='openpyxl')
            print(f"✅ FONCTIONNEL_134 chargé: {len(self.rules_bio_functional)} lignes")
            
            print("⏳ Chargement Microbiote...")
            self.rules_microbiome = pd.read_excel(self.rules_excel_path, sheet_name='Microbiote', engine='openpyxl')
            print(f"✅ Microbiote chargé: {len(self.rules_microbiome)} lignes")
            
            print("⏳ Chargement Métabolites salivaire...")
            self.rules_metabolites = pd.read_excel(self.rules_excel_path, sheet_name='Métabolites salivaire', engine='openpyxl')
            print(f"✅ Métabolites chargé: {len(self.rules_metabolites)} lignes")
            
            print("✅ Toutes les règles chargées avec succès")
            
        except FileNotFoundError as e:
            print(f"❌ ERREUR: Fichier non trouvé - {str(e)}")
            raise
        except ValueError as e:
            print(f"❌ ERREUR: Feuille Excel introuvable - {str(e)}")
            print("📋 Feuilles disponibles dans le fichier:")
            try:
                xl_file = pd.ExcelFile(self.rules_excel_path, engine='openpyxl')
                for sheet in xl_file.sheet_names:
                    print(f"   - {sheet}")
            except:
                pass
            raise
        except Exception as e:
            print(f"❌ ERREUR DÉTAILLÉE lors du chargement: {type(e).__name__}: {str(e)}")
            import traceback
            print(traceback.format_exc())
            raise
    
    def _find_biomarker_rules(self, biomarker_name: str, gender: str = 'H') -> Optional[pd.Series]:
        """
        Trouve les règles correspondant à un biomarqueur
        
        Args:
            biomarker_name: Nom du biomarqueur
            gender: Genre du patient ('H' ou 'F')
            
        Returns:
            Série pandas avec les règles, ou None si non trouvé
        """
        normalized_name = normalize_biomarker_name(biomarker_name)
        
        # Chercher d'abord dans BASE_40
        for idx, row in self.rules_bio_base.iterrows():
            rule_name = normalize_biomarker_name(str(row['Biomarqueur']))
            if rule_name == normalized_name or normalized_name in rule_name:
                return row
        
        # Chercher dans EXTENDED_92
        for idx, row in self.rules_bio_extended.iterrows():
            rule_name = normalize_biomarker_name(str(row['Biomarqueur']))
            if rule_name == normalized_name or normalized_name in rule_name:
                return row
        
        # Chercher dans FONCTIONNEL_134
        for idx, row in self.rules_bio_functional.iterrows():
            rule_name = normalize_biomarker_name(str(row['Biomarqueur']))
            if rule_name == normalized_name or normalized_name in rule_name:
                return row
        
        return None
    
    def _get_microbiome_rules(self, group: str, severity: int) -> Optional[pd.Series]:
        """
        Trouve les règles correspondant à un groupe de bactéries et un niveau de sévérité
        
        Args:
            group: Nom du groupe bactérien
            severity: Niveau de gravité (1=léger, 2=modéré, 3=sévère)
            
        Returns:
            Série pandas avec les règles, ou None
        """
        # Normaliser le groupe
        normalized_group = group.upper().strip()
        
        # Chercher dans les règles microbiome
        for idx, row in self.rules_microbiome.iterrows():
            rule_group = str(row.get('Groupe', '')).upper().strip()
            rule_severity = row.get('Niveau_gravite', '')
            
            # Correspondance du groupe
            if normalized_group in rule_group or rule_group in normalized_group:
                # Vérifier la sévérité
                if (severity == 1 and '+1' in str(rule_severity)) or \
                   (severity == 2 and '+2' in str(rule_severity)) or \
                   (severity == 3 and '+3' in str(rule_severity)):
                    return row
        
        return None
    
    def generate_biology_interpretation(self, biomarker_data: pd.Series, patient_info: Dict) -> Dict:
        """
        Génère l'interprétation et les recommandations pour un biomarqueur
        
        Args:
            biomarker_data: Série avec les données du biomarqueur (Biomarqueur, Valeur, Unité, Référence)
            patient_info: Informations patient (genre, âge, etc.)
            
        Returns:
            Dictionnaire avec interprétation et recommandations
        """
        biomarker_name = biomarker_data['Biomarqueur']
        value = biomarker_data['Valeur']
        unit = biomarker_data.get('Unité', '')
        reference = biomarker_data.get('Référence', '')
        
        # Déterminer le statut
        status = determine_biomarker_status(value, reference, biomarker_name)
        
        # Trouver les règles
        gender = 'H' if patient_info.get('genre') == 'Homme' else 'F'
        rules = self._find_biomarker_rules(biomarker_name, gender)
        
        result = {
            'biomarker': biomarker_name,
            'value': value,
            'unit': unit,
            'reference': reference,
            'status': status,
            'interpretation': None,
            'nutrition_reco': None,
            'micronutrition_reco': None,
            'lifestyle_reco': None
        }
        
        if rules is not None:
            if status == 'Bas':
                result['interpretation'] = rules.get('BASSE - Interprétation', '')
                result['nutrition_reco'] = rules.get('BASSE - Nutrition', '')
                result['micronutrition_reco'] = rules.get('BASSE - Micronutrition', '')
                result['lifestyle_reco'] = rules.get('BASSE - Lifestyle', '')
            elif status == 'Élevé':
                result['interpretation'] = rules.get('HAUTE - Interprétation', '')
                result['nutrition_reco'] = rules.get('HAUTE - Nutrition', '')
                result['micronutrition_reco'] = rules.get('HAUTE - Micronutrition', '')
                result['lifestyle_reco'] = rules.get('HAUTE - Lifestyle', '')
        
        return result
    
    def generate_microbiome_interpretation(self, bacteria_data: Dict) -> Dict:
        """
        Génère l'interprétation pour un groupe bactérien
        
        Args:
            bacteria_data: Dict avec category, group, result
            
        Returns:
            Dictionnaire avec interprétation et recommandations
        """
        group = bacteria_data['group']
        result_status = bacteria_data['result']
        
        # Déterminer la sévérité basée sur le résultat
        if result_status == 'Expected':
            severity = 0  # Normal, pas de recommandations
        elif result_status == 'Slightly deviating':
            severity = 1  # Léger
        else:  # Deviating
            severity = 2  # Modéré à sévère
        
        result = {
            'category': bacteria_data['category'],
            'group': group,
            'result': result_status,
            'interpretation': None,
            'nutrition_reco': None,
            'supplementation_reco': None,
            'lifestyle_reco': None
        }
        
        # Si normal, pas de recommandations spécifiques
        if severity == 0:
            result['interpretation'] = "Niveau optimal - Continuer les bonnes pratiques actuelles"
            return result
        
        # Trouver les règles
        rules = self._get_microbiome_rules(group, severity)
        
        if rules is not None:
            result['interpretation'] = rules.get('Interpretation_clinique', '')
            result['nutrition_reco'] = rules.get('Recommandations_nutritionnelles', '')
            result['supplementation_reco'] = rules.get('Recommandations_supplementation', '')
            result['lifestyle_reco'] = rules.get('Recommandations_lifestyle', '')
        
        return result
    
    def generate_cross_analysis(self, biology_data: pd.DataFrame, microbiome_data: Dict) -> List[Dict]:
        """
        Génère une analyse croisée entre biologie et microbiome
        
        Args:
            biology_data: DataFrame avec les résultats biologiques
            microbiome_data: Dict avec les données du microbiome
            
        Returns:
            Liste de dict avec les analyses croisées
        """
        cross_analyses = []
        
        # Analyse 1: Inflammation (CRP + Microbiome pro-inflammatoire)
        crp_data = biology_data[biology_data['Biomarqueur'].str.contains('CRP', case=False, na=False)]
        
        if not crp_data.empty:
            crp_value = crp_data.iloc[0]['Valeur']
            
            # Chercher des bactéries pro-inflammatoires
            pro_inflammatory = [b for b in microbiome_data.get('bacteria', [])
                              if 'E.' in b.get('category', '') and b.get('result') != 'Expected']
            
            if crp_value > 3 and pro_inflammatory:
                cross_analyses.append({
                    'title': '🔥 Inflammation Systémique Détectée',
                    'description': f"""
                    **Corrélation biologie-microbiome:**
                    - CRP élevée: {crp_value} mg/L (>3)
                    - Microbiome pro-inflammatoire perturbé: {len(pro_inflammatory)} groupe(s) affecté(s)
                    
                    **Recommandations prioritaires:**
                    1. Régime anti-inflammatoire strict (élimination gluten/produits laitiers test 3 mois)
                    2. Omega-3 EPA 2-4g/j + Curcumine liposomale 1-2g/j
                    3. Probiotiques multi-souches ciblés pour restaurer l'équilibre
                    4. Gestion du stress et sommeil optimisé
                    """
                })
        
        # Analyse 2: Résistance à l'insuline + Dysbiose
        insulin_data = biology_data[biology_data['Biomarqueur'].str.contains('HOMA', case=False, na=False)]
        
        if not insulin_data.empty:
            homa_value = insulin_data.iloc[0]['Valeur']
            dysbiosis_index = microbiome_data.get('dysbiosis_index', 1)
            
            if homa_value > 2.4 and dysbiosis_index >= 3:
                cross_analyses.append({
                    'title': '⚡ Résistance à l\'Insuline + Dysbiose',
                    'description': f"""
                    **Corrélation métabolique:**
                    - HOMA-IR: {homa_value} (>2.4 = insulino-résistance)
                    - Dysbiosis Index: {dysbiosis_index}/5
                    
                    **Mécanisme:**
                    La dysbiose intestinale contribue à l'inflammation chronique de bas grade et à la résistance à l'insuline
                    via la production d'endotoxines (LPS) et la perturbation du métabolisme des acides gras à chaîne courte.
                    
                    **Recommandations intégrées:**
                    1. Jeûne intermittent 16:8 (fenêtre alimentaire 12h-20h)
                    2. Régime faible en glucides raffinés, riche en fibres prébiotiques
                    3. Berbérine 500mg 3x/j + Probiotiques haute dose (50-100 milliards UFC)
                    4. Exercice HIIT 3x/semaine + marche quotidienne
                    """
                })
        
        # Analyse 3: Statut antioxydant + SCFA producers
        glutathion_data = biology_data[biology_data['Biomarqueur'].str.contains('GLUTATHION', case=False, na=False)]
        
        if not glutathion_data.empty:
            glutathion_value = glutathion_data.iloc[0]['Valeur']
            
            # Chercher les producteurs de SCFA
            scfa_producers = [b for b in microbiome_data.get('bacteria', [])
                            if 'D2' in b.get('group', '')]
            
            if glutathion_value < 1200 and scfa_producers:
                scfa_status = scfa_producers[0].get('result', 'Expected') if scfa_producers else 'Expected'
                
                if scfa_status != 'Expected':
                    cross_analyses.append({
                        'title': '🛡️ Stress Oxydatif + Déficit en Producteurs de SCFA',
                        'description': f"""
                        **Corrélation fonctionnelle:**
                        - Glutathion total: {glutathion_value} µmol/L (<1200)
                        - Producteurs de SCFA (butyrate): {scfa_status}
                        
                        **Mécanisme:**
                        Les bactéries productrices de SCFA (notamment butyrate) sont essentielles pour:
                        - La production d'énergie des colonocytes
                        - La réduction du stress oxydatif intestinal
                        - La synthèse de glutathion par les cellules épithéliales
                        
                        **Recommandations synergiques:**
                        1. Fibres prébiotiques ciblées: Inuline 10g/j + Amidon résistant 20g/j
                        2. NAC 600mg 2x/j + Glutamine 10g/j + Vitamine C 2g/j
                        3. Probiotiques producteurs de butyrate: Faecalibacterium prausnitzii + Roseburia spp.
                        4. Polyphénols: Resvératrol 500mg/j + Curcumine 1g/j
                        """
                    })
        
        # Analyse 4: Ferritine basse + LBP élevé (perméabilité intestinale)
        ferritin_data = biology_data[biology_data['Biomarqueur'].str.contains('FERRITINE', case=False, na=False)]
        lbp_data = biology_data[biology_data['Biomarqueur'].str.contains('LBP', case=False, na=False)]
        
        if not ferritin_data.empty and not lbp_data.empty:
            ferritin_value = ferritin_data.iloc[0]['Valeur']
            lbp_value = lbp_data.iloc[0]['Valeur']
            
            if ferritin_value < 30 and lbp_value > 6.8:
                cross_analyses.append({
                    'title': '🔓 Carence en Fer + Hyperperméabilité Intestinale',
                    'description': f"""
                    **Corrélation digestive:**
                    - Ferritine: {ferritin_value} µg/L (<30)
                    - LBP: {lbp_value} mg/L (>6.8 = hyperperméabilité)
                    
                    **Mécanisme:**
                    L'hyperperméabilité intestinale ("leaky gut") altère l'absorption du fer et contribue
                    à l'inflammation systémique, aggravant la carence martiale.
                    
                    **Recommandations prioritaires:**
                    1. Réparer la barrière intestinale:
                       - L-Glutamine 15-20g/j (5g 3x/j à jeun)
                       - Zinc carnosine 75mg 2x/j
                       - Collagène hydrolysé 10g/j
                    2. Optimiser l'absorption du fer:
                       - Fer bisglycinate 60mg/j avec vitamine C 500mg
                       - À jeun ou 2h entre les repas
                    3. Restaurer le microbiome:
                       - Probiotiques Lactobacillus + Bifidobacterium 50 milliards UFC
                       - Fibres solubles douces (psyllium 5g/j)
                    4. Éliminer irritants: Gluten, produits laitiers, alcool, AINS
                    """
                })
        
        return cross_analyses
    
    def generate_recommendations(self, 
                                biology_data: Optional[pd.DataFrame] = None,
                                microbiome_data: Optional[Dict] = None,
                                patient_info: Optional[Dict] = None) -> Dict:
        """
        Génère toutes les recommandations basées sur les données disponibles
        
        Args:
            biology_data: DataFrame avec les résultats biologiques
            microbiome_data: Dict avec les données du microbiome
            patient_info: Dict avec les informations patient
            
        Returns:
            Dict avec toutes les interprétations et recommandations
        """
        recommendations = {
            'biology_interpretations': [],
            'microbiome_interpretations': [],
            'microbiome_summary': {},
            'cross_analysis': [],
            'priority_actions': []
        }
        
        # Traiter les données biologiques
        if biology_data is not None and not biology_data.empty:
            for idx, row in biology_data.iterrows():
                interp = self.generate_biology_interpretation(row, patient_info or {})
                recommendations['biology_interpretations'].append(interp)
        
        # Traiter les données microbiome
        if microbiome_data is not None:
            recommendations['microbiome_summary'] = {
                'dysbiosis_index': microbiome_data.get('dysbiosis_index'),
                'diversity': microbiome_data.get('diversity')
            }
            
            for bacteria in microbiome_data.get('bacteria', []):
                interp = self.generate_microbiome_interpretation(bacteria)
                recommendations['microbiome_interpretations'].append(interp)
        
        # Générer l'analyse croisée si les deux types de données sont disponibles
        if biology_data is not None and microbiome_data is not None:
            recommendations['cross_analysis'] = self.generate_cross_analysis(
                biology_data, microbiome_data
            )
        
        # Générer les actions prioritaires
        recommendations['priority_actions'] = self._generate_priority_actions(recommendations)
        
        return recommendations
    
    def _generate_priority_actions(self, recommendations: Dict) -> List[str]:
        """
        Génère une liste d'actions prioritaires basée sur toutes les recommandations
        
        Args:
            recommendations: Dict avec toutes les recommandations
            
        Returns:
            Liste de strings avec les actions prioritaires
        """
        actions = []
        
        # Prioriser les anomalies critiques en biologie
        critical_bio = [b for b in recommendations.get('biology_interpretations', [])
                       if b['status'] != 'Normal']
        
        if len(critical_bio) >= 5:
            actions.append("🚨 PRIORITÉ HAUTE: Consulter un médecin - Nombreuses anomalies biologiques détectées")
        
        # Prioriser la dysbiose sévère
        di = recommendations.get('microbiome_summary', {}).get('dysbiosis_index')
        if di and di >= 4:
            actions.append("🦠 PRIORITÉ HAUTE: Dysbiose sévère - Protocole de restauration du microbiome urgent")
        
        # Inflammation systémique
        inflammation = [a for a in recommendations.get('cross_analysis', [])
                       if 'Inflammation' in a.get('title', '')]
        if inflammation:
            actions.append("🔥 PRIORITÉ: Réduire l'inflammation - Régime anti-inflammatoire + supplémentation ciblée")
        
        # Hyperperméabilité intestinale
        permeability = [a for a in recommendations.get('cross_analysis', [])
                       if 'perméabilité' in a.get('title', '').lower()]
        if permeability:
            actions.append("🔓 PRIORITÉ: Réparer la barrière intestinale - L-Glutamine + Probiotiques")
        
        # Si peu d'actions, ajouter des recommandations générales
        if len(actions) < 2:
            actions.append("✅ Maintenir un mode de vie sain avec activité physique régulière")
            actions.append("🥗 Adopter une alimentation méditerranéenne riche en légumes et oméga-3")
        
        return actions
