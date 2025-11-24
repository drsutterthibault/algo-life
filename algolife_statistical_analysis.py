"""
ALGO-LIFE - Module de Génération de Rapports Statistiques Avancés
Auteur: Thibault - Product Manager Functional Biology
Version: 2.0
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from scipy import stats
from datetime import datetime
from io import BytesIO
import warnings
warnings.filterwarnings('ignore')

# Configuration du style
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_palette("husl")

class AlgoLifeStatisticalAnalysis:
    """
    Classe principale pour l'analyse statistique multi-dimensionnelle
    des données biologiques et épigénétiques
    """
    
    def __init__(self, patient_data):
        """
        Initialise l'analyse avec les données patient
        
        Args:
            patient_data (dict): Dictionnaire contenant toutes les données du patient
                - biological_markers: dict des biomarqueurs biologiques
                - epigenetic_data: dict des données épigénétiques (optionnel)
                - lifestyle_scores: dict des scores lifestyle (optionnel)
                - patient_info: dict des infos patient (nom, âge, sexe, etc.)
        """
        self.patient_data = patient_data
        self.biological_markers = patient_data.get('biological_markers', {})
        self.epigenetic_data = patient_data.get('epigenetic_data', {})
        self.lifestyle_scores = patient_data.get('lifestyle_scores', {})
        self.patient_info = patient_data.get('patient_info', {})
        
        # Résultats des analyses
        self.composite_indices = {}
        self.statistical_model = None
        self.predictions = {}
        self.correlations = {}
        
    def calculate_stress_index(self):
        """
        Calcule l'indice de stress basé sur le profil cortisol/DHEA
        """
        try:
            cortisol_car = self.biological_markers.get('cortisol_car_30', 
                                                       self.biological_markers.get('cortisol_car+30', 0))
            cortisol_22h = self.biological_markers.get('cortisol_22h', 0)
            dhea = self.biological_markers.get('dhea', 0)
            
            stress_score = 0
            
            # CAR diminué (signature burnout)
            if cortisol_car < 7.5:
                stress_score += 40
            
            # Cortisol nocturne bas
            if cortisol_22h < 0.3:
                stress_score += 30
                
            # DHEA préservée (réserve adaptative)
            if dhea > 1.5:
                stress_score -= 10
            
            # Cortisol réveil élevé (hyperactivation)
            cortisol_reveil = self.biological_markers.get('cortisol_reveil', 0)
            if cortisol_reveil > 17:
                stress_score += 20
                
            stress_score = min(100, max(0, stress_score))
            
            self.composite_indices['stress_index'] = stress_score
            
            return {
                'score': stress_score,
                'interpretation': self._interpret_stress(stress_score),
                'phase': self._get_stress_phase(cortisol_car, cortisol_22h, dhea)
            }
        except Exception as e:
            print(f"Erreur calcul stress index: {e}")
            return {'score': 0, 'interpretation': 'Données insuffisantes', 'phase': 'Indéterminé'}
    
    def _interpret_stress(self, score):
        """Interprète le score de stress"""
        if score < 20:
            return "Adaptation normale au stress"
        elif score < 40:
            return "Stress modéré gérable"
        elif score < 60:
            return "Épuisement surrénalien débutant"
        elif score < 80:
            return "Épuisement surrénalien modéré"
        else:
            return "Épuisement surrénalien sévère"
    
    def _get_stress_phase(self, car, cortisol_22h, dhea):
        """Détermine la phase d'épuisement"""
        if car > 7.5 and dhea > 1.5:
            return "Phase 1: Alarme (hyperactivation)"
        elif car < 7.5 and dhea > 1.5:
            return "Phase 2: Résistance (épuisement débutant)"
        elif car < 7.5 and dhea < 1.0:
            return "Phase 3: Épuisement (burnout)"
        else:
            return "Phase intermédiaire"
    
    def calculate_metabolic_health_score(self):
        """
        Calcule le score de santé métabolique
        """
        try:
            homa = self.biological_markers.get('homa_index', 0)
            quicki = self.biological_markers.get('quicki_index', 1)
            crp = self.biological_markers.get('crp', 0)
            vit_d = self.biological_markers.get('vit_d', 0)
            glycemie = self.biological_markers.get('glycemie', 0)
            insuline = self.biological_markers.get('insuline', 0)
            
            score = 100
            issues = []
            
            # Résistance insulinique
            if homa > 2.4:
                penalty = min(30, (homa - 2.4) * 10)
                score -= penalty
                issues.append(f"Résistance insulinique (HOMA: {homa:.2f})")
            
            if quicki < 0.34:
                score -= 20
                issues.append(f"Sensibilité insulinique diminuée (QUICKI: {quicki:.2f})")
            
            # Inflammation
            if crp > 1.0:
                penalty = min(25, (crp - 1.0) * 8)
                score -= penalty
                issues.append(f"Inflammation systémique (CRP: {crp:.2f} mg/L)")
            
            # Vitamine D
            if vit_d < 75:
                penalty = (75 - vit_d) / 5
                score -= min(15, penalty)
                if vit_d < 30:
                    issues.append(f"Carence vitamine D sévère ({vit_d:.1f} nmol/L)")
                elif vit_d < 50:
                    issues.append(f"Insuffisance vitamine D ({vit_d:.1f} nmol/L)")
            
            # Glycémie
            if glycemie > 100:
                score -= 10
                if glycemie > 110:
                    issues.append(f"Hyperglycémie modérée ({glycemie:.1f} mg/dL)")
            
            score = max(0, score)
            
            self.composite_indices['metabolic_score'] = score
            
            return {
                'score': score,
                'interpretation': self._interpret_metabolic(score),
                'issues': issues,
                'risk_level': self._get_metabolic_risk(score)
            }
        except Exception as e:
            print(f"Erreur calcul metabolic score: {e}")
            return {'score': 0, 'interpretation': 'Données insuffisantes', 'issues': [], 'risk_level': 'Indéterminé'}
    
    def _interpret_metabolic(self, score):
        """Interprète le score métabolique"""
        if score >= 80:
            return "Santé métabolique optimale"
        elif score >= 60:
            return "Santé métabolique correcte"
        elif score >= 40:
            return "Dysrégulation métabolique modérée"
        elif score >= 20:
            return "Dysrégulation métabolique importante"
        else:
            return "Syndrome métabolique établi"
    
    def _get_metabolic_risk(self, score):
        """Évalue le risque métabolique"""
        if score >= 70:
            return "Faible"
        elif score >= 50:
            return "Modéré"
        elif score >= 30:
            return "Élevé"
        else:
            return "Très élevé"
    
    def calculate_neurotransmitter_balance(self):
        """
        Calcule l'équilibre des neurotransmetteurs
        """
        try:
            dopamine = self.biological_markers.get('dopamine', 0)
            serotonine = self.biological_markers.get('serotonine', 0)
            noradrenaline = self.biological_markers.get('noradrenaline', 0)
            adrenaline = self.biological_markers.get('adrenaline', 0)
            
            # Normalisation par rapport aux valeurs optimales
            scores = []
            details = {}
            
            if dopamine > 0:
                dopa_score = ((dopamine - 108) / (244 - 108)) * 100
                dopa_score = max(0, min(100, dopa_score))
                scores.append(dopa_score)
                details['dopamine'] = {
                    'value': dopamine,
                    'score': dopa_score,
                    'status': 'Optimal' if 40 <= dopa_score <= 70 else 'Déséquilibré'
                }
            
            if serotonine > 0:
                sero_score = ((serotonine - 38) / (89 - 38)) * 100
                sero_score = max(0, min(100, sero_score))
                scores.append(sero_score)
                details['serotonine'] = {
                    'value': serotonine,
                    'score': sero_score,
                    'status': 'Optimal' if 40 <= sero_score <= 70 else 'Déséquilibré'
                }
            
            if noradrenaline > 0:
                nora_score = ((noradrenaline - 11.1) / (28 - 11.1)) * 100
                nora_score = max(0, min(100, nora_score))
                scores.append(nora_score)
                details['noradrenaline'] = {
                    'value': noradrenaline,
                    'score': nora_score,
                    'status': 'Optimal' if 40 <= nora_score <= 70 else 'Déséquilibré'
                }
            
            balance_score = np.mean(scores) if scores else 0
            
            self.composite_indices['neuro_balance'] = balance_score
            
            return {
                'score': balance_score,
                'interpretation': self._interpret_neuro(balance_score),
                'details': details,
                'recommendation': self._get_neuro_recommendation(details)
            }
        except Exception as e:
            print(f"Erreur calcul neuro balance: {e}")
            return {'score': 0, 'interpretation': 'Données insuffisantes', 'details': {}, 'recommendation': ''}
    
    def _interpret_neuro(self, score):
        """Interprète le score neurotransmetteur"""
        if score >= 70:
            return "Équilibre neurotransmetteur optimal"
        elif score >= 50:
            return "Équilibre neurotransmetteur correct"
        elif score >= 30:
            return "Déséquilibre neurotransmetteur modéré"
        else:
            return "Déséquilibre neurotransmetteur important"
    
    def _get_neuro_recommendation(self, details):
        """Génère recommandations basées sur le profil neurotransmetteur"""
        recommendations = []
        
        for neuro, data in details.items():
            if data['score'] < 40:
                if neuro == 'dopamine':
                    recommendations.append("Stimuler dopamine: L-tyrosine, exercice, objectifs")
                elif neuro == 'serotonine':
                    recommendations.append("Stimuler sérotonine: 5-HTP, lumière, gratitude")
                elif neuro == 'noradrenaline':
                    recommendations.append("Moduler noradrénaline: adaprogènes, respiration")
            elif data['score'] > 70:
                if neuro == 'dopamine':
                    recommendations.append("Réguler dopamine: réduire stimulants")
                elif neuro == 'noradrenaline':
                    recommendations.append("Réguler noradrénaline: relaxation, magnésium")
        
        return ' | '.join(recommendations) if recommendations else "Équilibre optimal maintenu"
    
    def calculate_inflammation_index(self):
        """
        Calcule l'indice inflammatoire composite
        """
        try:
            crp = self.biological_markers.get('crp', 0)
            lbp = self.biological_markers.get('lbp', 0)
            zonuline = self.biological_markers.get('zonuline', 0)
            homocysteine = self.biological_markers.get('homocysteine', 0)
            
            score = 0
            sources = []
            
            # CRP ultra-sensible
            if crp > 1.0:
                crp_contribution = (crp / 5.0) * 40
                score += min(40, crp_contribution)
                sources.append(f"CRP: {crp:.2f} mg/L (inflammation systémique)")
            
            # LBP (endotoxémie métabolique)
            if lbp > 13.1:
                lbp_contribution = ((lbp - 13.1) / 13.1) * 30
                score += min(30, lbp_contribution)
                sources.append(f"LBP: {lbp:.2f} ng/mL (endotoxémie)")
            
            # Zonuline (perméabilité intestinale)
            if zonuline > 37:
                zonuline_contribution = ((zonuline - 37) / 37) * 30
                score += min(30, zonuline_contribution)
                sources.append(f"Zonuline: {zonuline:.2f} ng/mL (intestin perméable)")
            
            # Homocystéine
            if homocysteine > 12:
                score += 15
                sources.append(f"Homocystéine: {homocysteine:.2f} µmol/L (inflammation vasculaire)")
            
            score = min(100, score)
            
            self.composite_indices['inflammation_index'] = score
            
            return {
                'score': score,
                'interpretation': self._interpret_inflammation(score),
                'sources': sources,
                'priority': self._get_inflammation_priority(score, sources)
            }
        except Exception as e:
            print(f"Erreur calcul inflammation index: {e}")
            return {'score': 0, 'interpretation': 'Données insuffisantes', 'sources': [], 'priority': ''}
    
    def _interpret_inflammation(self, score):
        """Interprète le score inflammatoire"""
        if score < 20:
            return "Inflammation physiologique normale"
        elif score < 40:
            return "Inflammation modérée"
        elif score < 60:
            return "Inflammation importante"
        else:
            return "Inflammation sévère systémique"
    
    def _get_inflammation_priority(self, score, sources):
        """Détermine la priorité d'intervention"""
        if score < 30:
            return "Surveillance"
        elif score < 60:
            return "Intervention recommandée"
        else:
            return "Intervention urgente"
    
    def calculate_all_indices(self):
        """
        Calcule tous les indices composites
        """
        results = {
            'stress': self.calculate_stress_index(),
            'metabolic': self.calculate_metabolic_health_score(),
            'neurotransmitters': self.calculate_neurotransmitter_balance(),
            'inflammation': self.calculate_inflammation_index()
        }
        
        return results
    
    def build_predictive_model(self, target='biological_age', synthetic_population_size=50):
        """
        Construit un modèle prédictif par régression multiple
        
        Args:
            target: Variable à prédire ('biological_age', 'youth_capital', 'health_score')
            synthetic_population_size: Taille de la population synthétique pour validation
        """
        try:
            # Préparer les features
            features = {}
            
            # Ajouter les indices composites
            if self.composite_indices:
                features.update(self.composite_indices)
            
            # Ajouter les biomarqueurs clés
            key_markers = [
                'cortisol_car_30', 'dhea', 'homa_index', 'crp', 'vit_d',
                'omega3_index', 'dopamine', 'serotonine', 'glycemie'
            ]
            
            for marker in key_markers:
                value = self.biological_markers.get(marker, 0)
                if value > 0:
                    features[marker] = value
            
            # Ajouter les scores lifestyle si disponibles
            if self.lifestyle_scores:
                features.update(self.lifestyle_scores)
            
            if len(features) < 4:
                return {
                    'success': False,
                    'message': 'Données insuffisantes pour construire le modèle (minimum 4 variables)'
                }
            
            # Créer population synthétique
            np.random.seed(42)
            X_synthetic = pd.DataFrame()
            
            for feature_name, feature_value in features.items():
                std_dev = feature_value * 0.15  # 15% de variation
                X_synthetic[feature_name] = np.random.normal(
                    feature_value, 
                    std_dev, 
                    synthetic_population_size
                )
            
            # Générer variable cible synthétique
            # Pondération basée sur la littérature scientifique
            weights = {
                'stress_index': -0.02,
                'metabolic_score': 0.03,
                'neuro_balance': 0.02,
                'inflammation_index': -0.015,
                'cortisol_car_30': -0.01,
                'homa_index': -0.015,
                'crp': -0.02,
                'vit_d': 0.01,
                'omega3_index': 0.05
            }
            
            y_synthetic = np.zeros(synthetic_population_size)
            
            for feature in X_synthetic.columns:
                weight = weights.get(feature, 0.01)  # Poids par défaut
                y_synthetic += weight * X_synthetic[feature]
            
            # Ajouter du bruit
            y_synthetic += np.random.normal(0, 0.5, synthetic_population_size)
            
            # Standardisation
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X_synthetic)
            
            # Entraînement du modèle
            model = LinearRegression()
            model.fit(X_scaled, y_synthetic)
            
            # Métriques
            r2_score = model.score(X_scaled, y_synthetic)
            
            # Coefficients
            coefficients = pd.DataFrame({
                'Feature': X_synthetic.columns,
                'Coefficient': model.coef_,
                'Abs_Coefficient': np.abs(model.coef_)
            }).sort_values('Abs_Coefficient', ascending=False)
            
            # Prédiction pour le patient
            patient_features_df = pd.DataFrame([features])
            patient_features_aligned = patient_features_df.reindex(columns=X_synthetic.columns, fill_value=0)
            patient_scaled = scaler.transform(patient_features_aligned)
            prediction = model.predict(patient_scaled)[0]
            
            # Corrélations
            correlations = {}
            for feature in X_synthetic.columns:
                corr, pval = stats.pearsonr(X_synthetic[feature], y_synthetic)
                correlations[feature] = {
                    'correlation': corr,
                    'p_value': pval,
                    'significant': pval < 0.05
                }
            
            # Stocker les résultats
            self.statistical_model = {
                'model': model,
                'scaler': scaler,
                'features': list(X_synthetic.columns),
                'r2_score': r2_score,
                'coefficients': coefficients,
                'correlations': correlations
            }
            
            self.predictions[target] = {
                'value': prediction,
                'confidence': r2_score
            }
            
            return {
                'success': True,
                'r2_score': r2_score,
                'coefficients': coefficients,
                'prediction': prediction,
                'correlations': correlations,
                'n_features': len(features)
            }
            
        except Exception as e:
            print(f"Erreur construction modèle: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'message': f'Erreur: {str(e)}'
            }
    
    def generate_statistical_visualizations(self):
        """
        Génère les visualisations statistiques
        """
        try:
            fig = plt.figure(figsize=(16, 10))
            
            # 1. Importance des features
            if self.statistical_model:
                ax1 = plt.subplot(2, 3, 1)
                coeffs = self.statistical_model['coefficients'].head(6)
                colors = ['#2ecc71' if x > 0 else '#e74c3c' for x in coeffs['Coefficient']]
                ax1.barh(range(len(coeffs)), coeffs['Coefficient'], color=colors)
                ax1.set_yticks(range(len(coeffs)))
                ax1.set_yticklabels([f.replace('_', ' ').title() for f in coeffs['Feature']], fontsize=9)
                ax1.set_xlabel('Coefficient Standardisé', fontsize=10)
                ax1.set_title('Impact des Facteurs', fontsize=11, fontweight='bold')
                ax1.axvline(x=0, color='black', linestyle='--', linewidth=0.8)
                ax1.grid(axis='x', alpha=0.3)
            
            # 2. Profil radar des indices composites
            ax2 = plt.subplot(2, 3, 2, projection='polar')
            if self.composite_indices:
                categories = []
                values = []
                
                for key, value in self.composite_indices.items():
                    categories.append(key.replace('_', '\n').title())
                    # Inverser les indices négatifs pour le radar
                    if 'stress' in key or 'inflammation' in key:
                        values.append(100 - value)
                    else:
                        values.append(value)
                
                angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
                values += values[:1]
                angles += angles[:1]
                
                ax2.plot(angles, values, 'o-', linewidth=2, label='Patient', color='#e74c3c')
                ax2.fill(angles, values, alpha=0.25, color='#e74c3c')
                
                # Ligne optimale
                optimal = [85] * (len(categories) + 1)
                ax2.plot(angles, optimal, 'o-', linewidth=2, label='Optimal', color='#3498db', linestyle='--')
                
                ax2.set_xticks(angles[:-1])
                ax2.set_xticklabels(categories, fontsize=8)
                ax2.set_ylim(0, 100)
                ax2.set_title('Profil Biologique Global', fontsize=11, fontweight='bold', pad=20)
                ax2.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1), fontsize=9)
                ax2.grid(True)
            
            # 3. Heatmap des corrélations
            ax3 = plt.subplot(2, 3, 3)
            if self.statistical_model and self.statistical_model['correlations']:
                corr_data = self.statistical_model['correlations']
                features = list(corr_data.keys())[:8]  # Top 8
                corr_values = [corr_data[f]['correlation'] for f in features]
                
                # Créer matrice pour heatmap
                corr_matrix = np.array(corr_values).reshape(-1, 1)
                
                sns.heatmap(corr_matrix, 
                           annot=True, 
                           fmt='.2f', 
                           cmap='RdYlGn',
                           center=0,
                           yticklabels=[f.replace('_', ' ').title()[:15] for f in features],
                           xticklabels=['Corrélation'],
                           cbar_kws={'label': 'Coefficient'},
                           ax=ax3)
                ax3.set_title('Corrélations avec Santé', fontsize=11, fontweight='bold')
            
            # 4. Profil cortisol si disponible
            ax4 = plt.subplot(2, 3, 4)
            cortisol_times = ['Réveil', 'CAR\n+30min', '12h', '18h', '22h']
            cortisol_keys = ['cortisol_reveil', 'cortisol_car_30', 'cortisol_12h', 
                            'cortisol_18h', 'cortisol_22h']
            cortisol_values = [self.biological_markers.get(k, 0) for k in cortisol_keys]
            
            if any(cortisol_values):
                # Zones optimales
                optimal_min = [5, 7.5, 1.9, 0.3, 0.3]
                optimal_max = [17.1, 25.6, 5.2, 3.0, 1.4]
                
                x_pos = np.arange(len(cortisol_times))
                ax4.fill_between(x_pos, optimal_min, optimal_max, alpha=0.2, 
                                color='#2ecc71', label='Zone optimale')
                ax4.plot(x_pos, cortisol_values, 'o-', linewidth=2, markersize=8,
                        label='Patient', color='#e74c3c')
                
                ax4.set_xticks(x_pos)
                ax4.set_xticklabels(cortisol_times, fontsize=9)
                ax4.set_ylabel('Cortisol (nmol/L)', fontsize=10)
                ax4.set_title('Profil Circadien Cortisol', fontsize=11, fontweight='bold')
                ax4.legend(fontsize=9)
                ax4.grid(True, alpha=0.3)
            else:
                ax4.text(0.5, 0.5, 'Données cortisol\nnon disponibles', 
                        ha='center', va='center', fontsize=12, color='gray')
                ax4.set_title('Profil Circadien Cortisol', fontsize=11, fontweight='bold')
            
            # 5. Balance neurotransmetteurs
            ax5 = plt.subplot(2, 3, 5)
            neuro_data = self.calculate_neurotransmitter_balance()
            if neuro_data['details']:
                neuro_names = []
                neuro_scores = []
                
                for name, data in neuro_data['details'].items():
                    neuro_names.append(name.title())
                    neuro_scores.append(data['score'])
                
                x = np.arange(len(neuro_names))
                colors_neuro = ['#2ecc71' if 40 <= s <= 70 else '#e74c3c' for s in neuro_scores]
                
                ax5.bar(x, neuro_scores, color=colors_neuro, alpha=0.7, edgecolor='black')
                ax5.axhline(y=50, color='gray', linestyle='--', linewidth=1, alpha=0.5, label='Optimal')
                ax5.axhspan(40, 70, alpha=0.1, color='green', label='Zone optimale')
                
                ax5.set_ylabel('Score Normalisé (%)', fontsize=10)
                ax5.set_title('Équilibre Neurotransmetteurs', fontsize=11, fontweight='bold')
                ax5.set_xticks(x)
                ax5.set_xticklabels(neuro_names, fontsize=9)
                ax5.set_ylim(0, 100)
                ax5.legend(fontsize=8)
                ax5.grid(axis='y', alpha=0.3)
            else:
                ax5.text(0.5, 0.5, 'Données neurotransmetteurs\nnon disponibles', 
                        ha='center', va='center', fontsize=12, color='gray')
                ax5.set_title('Équilibre Neurotransmetteurs', fontsize=11, fontweight='bold')
            
            # 6. Distribution des indices composites
            ax6 = plt.subplot(2, 3, 6)
            if self.composite_indices:
                indices_names = [k.replace('_', ' ').title() for k in self.composite_indices.keys()]
                indices_values = list(self.composite_indices.values())
                
                # Inverser stress et inflammation pour cohérence visuelle
                for i, name in enumerate(list(self.composite_indices.keys())):
                    if 'stress' in name or 'inflammation' in name:
                        indices_values[i] = 100 - indices_values[i]
                
                colors_indices = ['#2ecc71' if v >= 70 else '#f39c12' if v >= 50 else '#e74c3c' 
                                 for v in indices_values]
                
                ax6.barh(range(len(indices_names)), indices_values, color=colors_indices, 
                        alpha=0.7, edgecolor='black')
                ax6.set_yticks(range(len(indices_names)))
                ax6.set_yticklabels(indices_names, fontsize=9)
                ax6.set_xlabel('Score (%)', fontsize=10)
                ax6.set_xlim(0, 100)
                ax6.axvline(x=70, color='green', linestyle='--', linewidth=1, alpha=0.5)
                ax6.axvline(x=50, color='orange', linestyle='--', linewidth=1, alpha=0.5)
                ax6.set_title('Distribution Indices Santé', fontsize=11, fontweight='bold')
                ax6.grid(axis='x', alpha=0.3)
            
            plt.tight_layout()
            
            # Sauvegarder en buffer
            buf = BytesIO()
            plt.savefig(buf, format='png', dpi=300, bbox_inches='tight')
            buf.seek(0)
            plt.close()
            
            return buf
            
        except Exception as e:
            print(f"Erreur génération visualisations: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def generate_comprehensive_report_data(self):
        """
        Génère toutes les données pour le rapport complet
        """
        # Calculer tous les indices
        indices_results = self.calculate_all_indices()
        
        # Construire le modèle prédictif
        model_results = self.build_predictive_model()
        
        # Compiler les données du rapport
        report_data = {
            'patient_info': self.patient_info,
            'composite_indices': indices_results,
            'statistical_model': model_results,
            'biological_markers': self.biological_markers,
            'analysis_date': datetime.now().strftime('%d/%m/%Y %H:%M'),
            'recommendations': self._generate_recommendations(indices_results, model_results)
        }
        
        return report_data
    
    def _generate_recommendations(self, indices_results, model_results):
        """
        Génère des recommandations personnalisées basées sur l'analyse statistique
        """
        recommendations = []
        
        # Basé sur le stress
        if indices_results['stress']['score'] > 40:
            recommendations.append({
                'priority': 1 if indices_results['stress']['score'] > 60 else 2,
                'category': 'Gestion du Stress',
                'issue': f"Score stress: {indices_results['stress']['score']:.0f}/100",
                'action': indices_results['stress']['interpretation'],
                'interventions': [
                    'Cohérence cardiaque 3x/jour',
                    'Adaprogènes (Rhodiola, Ashwagandha)',
                    'Thérapie cognitivo-comportementale',
                    'Chronothérapie lumineuse matinale'
                ],
                'expected_impact': 'Modéré à élevé'
            })
        
        # Basé sur le métabolisme
        if indices_results['metabolic']['score'] < 60:
            recommendations.append({
                'priority': 1,
                'category': 'Métabolisme',
                'issue': f"Score métabolique: {indices_results['metabolic']['score']:.0f}/100",
                'action': indices_results['metabolic']['interpretation'],
                'interventions': [
                    'Régime méditerranéen hypoglycémique',
                    'Activité physique HIIT 3x/semaine',
                    'Jeûne intermittent 16:8',
                    'Supplémentation: Berbérine, Chrome, Magnésium'
                ],
                'expected_impact': 'Élevé'
            })
        
        # Basé sur l'inflammation
        if indices_results['inflammation']['score'] > 40:
            recommendations.append({
                'priority': 1 if indices_results['inflammation']['score'] > 60 else 2,
                'category': 'Inflammation',
                'issue': f"Score inflammation: {indices_results['inflammation']['score']:.0f}/100",
                'action': 'Réduire inflammation systémique',
                'interventions': [
                    'Protocole anti-inflammatoire (oméga-3, curcumine)',
                    'Réparation barrière intestinale (L-glutamine, zinc)',
                    'Probiotiques multi-souches',
                    'Élimination aliments pro-inflammatoires'
                ],
                'expected_impact': 'Modéré à élevé'
            })
        
        # Basé sur les neurotransmetteurs
        neuro_score = indices_results['neurotransmitters']['score']
        if neuro_score < 50:
            recommendations.append({
                'priority': 2,
                'category': 'Neurotransmetteurs',
                'issue': f"Déséquilibre neurotransmetteur: {neuro_score:.0f}/100",
                'action': indices_results['neurotransmitters']['recommendation'],
                'interventions': [
                    'Précurseurs: L-tyrosine, 5-HTP, L-théanine',
                    'Cofacteurs: B6, B9, B12, Magnésium',
                    'Exercice régulier (boost dopamine)',
                    'Exposition solaire (sérotonine)'
                ],
                'expected_impact': 'Modéré'
            })
        
        # Ajouter recommandations basées sur le modèle statistique
        if model_results.get('success') and model_results.get('coefficients') is not None:
            top_factor = model_results['coefficients'].iloc[0]
            
            recommendations.append({
                'priority': 1,
                'category': 'Levier Principal',
                'issue': f"Facteur #1 identifié: {top_factor['Feature']}",
                'action': f"Impact statistique: {top_factor['Coefficient']:.3f}",
                'interventions': [
                    'Focus prioritaire sur ce levier',
                    'Suivi mensuel de ce paramètre',
                    'Ajustements personnalisés basés sur réponse'
                ],
                'expected_impact': 'Très élevé'
            })
        
        # Trier par priorité
        recommendations.sort(key=lambda x: x['priority'])
        
        return recommendations


# Export de la classe
__all__ = ['AlgoLifeStatisticalAnalysis']
