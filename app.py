"""
ALGO-LIFE - Plateforme Multimodale d'Analyse de Santé Fonctionnelle
Version 4.1 - Janvier 2026 - EXTRACTION UNIVERSELLE

Intégration multimodale:
- Biologie fonctionnelle (hormones, métabolisme, inflammation, microbiote)
- Épigénétique (âge biologique, méthylation, télomères)
- Imagerie DXA (composition corporelle, densité osseuse)

Auteur: Dr Thibault SUTTER - Biologiste
Organisation: ALGO-LIFE / Espace Lab SA (Unilabs Group)
Email: contact@bilan-hormonal.com
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, date
import re
from io import BytesIO
from typing import Dict, List, Optional, Tuple
import json

# ✅ PATCH: force reload module PDF (évite ancienne version / cache / doublon de fichier)
import importlib
import algolife_pdf_generator as pdfgen

# PDF extraction
try:
    import PyPDF2
    import pdfplumber
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

# Import modules ALGO-LIFE
from algolife_statistical_analysis import AlgoLifeStatisticalAnalysis
from algolife_engine import AlgoLifeEngine
from advanced_pdf_extractor_universal import UniversalPDFExtractor  # ✅ NOUVEAU

# ✅ PATCH: reload au runtime + alias fonction
pdfgen = importlib.reload(pdfgen)
generate_algolife_pdf_report = pdfgen.generate_algolife_pdf_report

# ============================================================================
# CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="ALGO-LIFE | Analyse Multimodale de Santé",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://bilan-hormonal.com',
        'Report a bug': "mailto:contact@bilan-hormonal.com",
        'About': "ALGO-LIFE v4.1 - Plateforme d'analyse multimodale de santé"
    }
)

# ============================================================================
# STYLES CSS PROFESSIONNELS
# ============================================================================

st.markdown("""
<style>
    /* Headers */
    .main-title {
        font-size: 3.5rem;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 0.5rem;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    .sub-title {
        font-size: 1.3rem;
        color: #4A5568;
        text-align: center;
        margin-bottom: 2rem;
        font-weight: 300;
    }
    
    /* Metric cards */
    .metric-card {
        background: linear-gradient(135deg, #667eea15 0%, #764ba215 100%);
        padding: 1.5rem;
        border-radius: 15px;
        border-left: 5px solid #667eea;
        box-shadow: 0 4px 6px rgba(0,0,0,0.07);
        margin: 1rem 0;
        transition: transform 0.2s;
    }
    
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 12px rgba(0,0,0,0.1);
    }
    
    /* Score badges */
    .score-excellent {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        color: white;
        padding: 0.5rem 1.5rem;
        border-radius: 25px;
        font-weight: 700;
        font-size: 1.8rem;
        display: inline-block;
        box-shadow: 0 4px 6px rgba(16, 185, 129, 0.3);
    }
    
    .score-good {
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
        color: white;
        padding: 0.5rem 1.5rem;
        border-radius: 25px;
        font-weight: 700;
        font-size: 1.8rem;
        display: inline-block;
        box-shadow: 0 4px 6px rgba(59, 130, 246, 0.3);
    }
    
    .score-moderate {
        background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
        color: white;
        padding: 0.5rem 1.5rem;
        border-radius: 25px;
        font-weight: 700;
        font-size: 1.8rem;
        display: inline-block;
        box-shadow: 0 4px 6px rgba(245, 158, 11, 0.3);
    }
    
    .score-poor {
        background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
        color: white;
        padding: 0.5rem 1.5rem;
        border-radius: 25px;
        font-weight: 700;
        font-size: 1.8rem;
        display: inline-block;
        box-shadow: 0 4px 6px rgba(239, 68, 68, 0.3);
    }
    
    /* Alert boxes */
    .alert-success {
        background-color: #d1fae5;
        border-left: 5px solid #10b981;
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    
    .alert-warning {
        background-color: #fef3c7;
        border-left: 5px solid #f59e0b;
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    
    .alert-danger {
        background-color: #fee2e2;
        border-left: 5px solid #ef4444;
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    
    .alert-info {
        background-color: #dbeafe;
        border-left: 5px solid #3b82f6;
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    
    /* Upload zone */
    .upload-zone {
        background: linear-gradient(135deg, #667eea10 0%, #764ba210 100%);
        border: 3px dashed #667eea;
        border-radius: 20px;
        padding: 3rem 2rem;
        text-align: center;
        margin: 2rem 0;
        transition: all 0.3s;
    }
    
    .upload-zone:hover {
        background: linear-gradient(135deg, #667eea20 0%, #764ba220 100%);
        border-color: #764ba2;
    }
    
    /* Buttons */
    .stButton>button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 0.75rem 2rem;
        font-weight: 600;
        font-size: 1rem;
        transition: all 0.3s;
        box-shadow: 0 4px 6px rgba(102, 126, 234, 0.3);
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(102, 126, 234, 0.4);
    }
    
    /* Biomarker status */
    .biomarker-normal {
        background-color: #d1fae5;
        padding: 0.5rem 1rem;
        border-radius: 8px;
        color: #065f46;
        font-weight: 600;
    }
    
    .biomarker-warning {
        background-color: #fef3c7;
        padding: 0.5rem 1rem;
        border-radius: 8px;
        color: #92400e;
        font-weight: 600;
    }
    
    .biomarker-abnormal {
        background-color: #fee2e2;
        padding: 0.5rem 1rem;
        border-radius: 8px;
        color: #991b1b;
        font-weight: 600;
    }
    
    /* Progress bars */
    .stProgress > div > div {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 60px;
        padding: 1rem 2rem;
        font-weight: 600;
        font-size: 1.1rem;
    }
    
    /* Data tables */
    .dataframe {
        border-radius: 10px;
        overflow: hidden;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# CLASSES PRINCIPALES
# ============================================================================

class BiomarkerDatabase:
    """Base de données complète des biomarqueurs avec normes et interprétations"""
    
    @staticmethod
    def get_reference_ranges():
        """Retourne les plages de référence pour tous les biomarqueurs"""
        return {
            # HORMONES
            'cortisol_reveil': {
                'unit': 'nmol/L',
                'optimal': (10, 38),
                'normal': (5, 50),
                'category': 'Hormones',
                'lab_names': ['cortisol réveil', 'cortisol salivaire réveil', 'cortisol awakening']
            },
            'cortisol_car_30': {
                'unit': 'nmol/L',
                'optimal': (20, 45),
                'normal': (10, 55),
                'category': 'Hormones',
                'lab_names': ['cortisol CAR (+30min)', 'cortisol réveil +30', 'cortisol +30min']
            },
            'cortisol_12h': {
                'unit': 'nmol/L',
                'optimal': (3, 10),
                'normal': (1.5, 15),
                'category': 'Hormones',
                'lab_names': ['cortisol 12h', 'cortisol midi']
            },
            'cortisol_18h': {
                'unit': 'nmol/L',
                'optimal': (1.5, 7.64),
                'normal': (1, 10),
                'category': 'Hormones',
                'lab_names': ['cortisol 18h', 'cortisol soir']
            },
            'cortisol_22h': {
                'unit': 'nmol/L',
                'optimal': (0.5, 3),
                'normal': (0.3, 5),
                'category': 'Hormones',
                'lab_names': ['cortisol 22h', 'cortisol nuit', 'cortisol coucher']
            },
            'dhea': {
                'unit': 'ng/mL',
                'optimal_male': (6, 10),
                'optimal_female': (4, 8),
                'normal_male': (3, 15),
                'normal_female': (2, 12),
                'category': 'Hormones',
                'lab_names': ['dhea', 'dhea salivaire', 'dehydroepiandrosterone']
            },
            
            # INFLAMMATION
            'crp': {
                'unit': 'mg/L',
                'optimal': (0, 1),
                'normal': (0, 3),
                'elevated': (3, 10),
                'high': (10, None),
                'category': 'Inflammation',
                'lab_names': ['crp ultrasensible', 'crp us', 'crp haute sensibilité', 'hs-crp']
            },
            
            # MÉTABOLISME GLUCIDIQUE
            'glycemie': {
                'unit': 'g/L',
                'optimal': (0.70, 0.95),
                'normal': (0.70, 1.10),
                'prediabetes': (1.10, 1.26),
                'diabetes': (1.26, None),
                'category': 'Métabolisme',
                'lab_names': ['glycémie à jeun', 'glycémie', 'glucose']
            },
            'insuline': {
                'unit': 'mUI/L',
                'optimal': (2, 7),
                'normal': (2, 25),
                'category': 'Métabolisme',
                'lab_names': ['insuline à jeun', 'insuline']
            },
            'homa_index': {
                'unit': '',
                'optimal': (0, 1),
                'normal': (0, 2.4),
                'insulin_resistance': (2.4, None),
                'category': 'Métabolisme',
                'lab_names': ['homa-ir', 'index homa', 'homa']
            },
            'quicki_index': {
                'unit': '',
                'optimal': (0.38, None),
                'insulin_sensitive': (0.35, None),
                'insulin_resistance': (None, 0.35),
                'category': 'Métabolisme',
                'lab_names': ['quicki', 'index quicki']
            },
            
            # MICRONUTRIMENTS
            'ferritine': {
                'unit': 'µg/L',
                'deficiency': (None, 15),
                'low': (15, 30),
                'optimal': (30, 100),
                'normal_female': (10, 291),
                'normal_male': (30, 400),
                'category': 'Micronutriments',
                'lab_names': ['ferritine']
            },
            'vit_d': {
                'unit': 'ng/mL',
                'deficiency': (None, 20),
                'insufficient': (20, 30),
                'optimal': (30, 60),
                'normal': (30, 100),
                'toxicity': (150, None),
                'category': 'Micronutriments',
                'lab_names': ['vitamine d', '25-oh vitamine d', '25-oh d', 'vitamin d']
            },
            'zinc': {
                'unit': 'µg/dL',
                'optimal': (88, 146),
                'normal': (70, 150),
                'category': 'Micronutriments',
                'lab_names': ['zinc']
            },
            'selenium': {
                'unit': 'µg/L',
                'optimal': (90, 143),
                'normal': (70, 150),
                'category': 'Micronutriments',
                'lab_names': ['sélénium', 'selenium']
            },
            'magnesium_erythrocytaire': {
                'unit': 'mg/dL',
                'optimal': (4.4, 5.8),
                'normal': (4.0, 6.0),
                'category': 'Micronutriments',
                'lab_names': ['magnésium érythrocytaire', 'mg érythrocytaire']
            },
            
            # ANTIOXYDANTS
            'glutathion_total': {
                'unit': 'µmol/L',
                'optimal': (1200, 1750),
                'normal': (900, 1800),
                'category': 'Antioxydants',
                'lab_names': ['glutathion total', 'glutathione']
            },
            'coenzyme_q10': {
                'unit': 'µg/L',
                'optimal': (670, 990),
                'normal': (500, 1000),
                'category': 'Antioxydants',
                'lab_names': ['coenzyme q10', 'coq10', 'ubiquinone']
            },
            'gpx': {
                'unit': 'U/g Hb',
                'optimal': (40, 62),
                'normal': (30, 70),
                'category': 'Antioxydants',
                'lab_names': ['glutathion peroxydase', 'gpx']
            },
            
            # PERMÉABILITÉ INTESTINALE
            'zonuline': {
                'unit': 'ng/mL',
                'optimal': (0, 30),
                'normal': (0, 50),
                'elevated': (50, 100),
                'high': (100, None),
                'category': 'Intestin',
                'lab_names': ['zonuline']
            },
            'lbp': {
                'unit': 'mg/L',
                'optimal': (0, 6.8),
                'normal': (2.3, 8.3),
                'category': 'Intestin',
                'lab_names': ['lbp', 'lps-binding protein', 'lipopolysaccharide binding protein']
            },
            
            # NEUROTRANSMETTEURS
            'dopamine': {
                'unit': 'µg/24h',
                'optimal': (150, 400),
                'normal': (100, 500),
                'category': 'Neurotransmetteurs',
                'lab_names': ['dopamine']
            },
            'serotonine': {
                'unit': 'µg/24h',
                'optimal': (100, 250),
                'normal': (50, 300),
                'category': 'Neurotransmetteurs',
                'lab_names': ['sérotonine', 'serotonine']
            },
            'noradrenaline': {
                'unit': 'µg/24h',
                'optimal': (15, 80),
                'normal': (10, 100),
                'category': 'Neurotransmetteurs',
                'lab_names': ['noradrénaline', 'noradrenaline', 'norepinephrine']
            },
            'adrenaline': {
                'unit': 'µg/24h',
                'optimal': (2, 20),
                'normal': (1, 25),
                'category': 'Neurotransmetteurs',
                'lab_names': ['adrénaline', 'adrenaline', 'epinephrine']
            },
            
            # CARDIOVASCULAIRE
            'homocysteine': {
                'unit': 'µmol/L',
                'optimal': (5, 10),
                'normal': (5, 15),
                'elevated': (15, 30),
                'high': (30, None),
                'category': 'Cardiovasculaire',
                'lab_names': ['homocystéine', 'homocysteine']
            },
            'omega3_index': {
                'unit': '%',
                'optimal': (8, None),
                'moderate': (6, 8),
                'low': (4, 6),
                'deficient': (None, 4),
                'category': 'Cardiovasculaire',
                'lab_names': ['index oméga-3', 'omega-3 index', 'index w3']
            },
            'aa_epa': {
                'unit': '',
                'optimal': (1, 3),
                'normal': (1, 5),
                'elevated': (5, 15),
                'high': (15, None),
                'category': 'Cardiovasculaire',
                'lab_names': ['rapport aa/epa', 'aa/epa ratio']
            },
        }
    
    @staticmethod
    def classify_biomarker(name: str, value: float, age: int = None, sex: str = None) -> Dict:
        """Classifie un biomarqueur selon sa valeur"""
        refs = BiomarkerDatabase.get_reference_ranges()
        
        if name not in refs:
            # ✅ AMÉLIORATION: Ne pas rejeter, retourner statut "non référencé"
            return {
                'status': 'unknown',
                'interpretation': f'Biomarqueur détecté mais non référencé (valeur: {value})',
                'color': 'gray',
                'icon': '❓',
                'value': value,
                'needs_reference': True
            }
        
        ref = refs[name]
        
        # Gestion sexe-spécifique (DHEA, Ferritine)
        if 'optimal_male' in ref and 'optimal_female' in ref:
            if sex == 'Masculin':
                optimal = ref['optimal_male']
                normal = ref.get('normal_male', optimal)
            else:
                optimal = ref['optimal_female']
                normal = ref.get('normal_female', optimal)
        else:
            optimal = ref.get('optimal', (None, None))
            normal = ref.get('normal', optimal)
        
        # Classification
        if optimal[0] is not None and optimal[1] is not None:
            if optimal[0] <= value <= optimal[1]:
                return {
                    'status': 'optimal',
                    'interpretation': 'Valeur optimale',
                    'color': 'green',
                    'icon': '✅'
                }
        
        if normal[0] is not None and normal[1] is not None:
            if normal[0] <= value <= normal[1]:
                return {
                    'status': 'normal',
                    'interpretation': 'Valeur normale',
                    'color': 'lightgreen',
                    'icon': '✓'
                }
        
        # Cas spéciaux avec seuils multiples
        if 'elevated' in ref:
            if ref['elevated'][0] <= value:
                if 'high' in ref and ref['high'][0] and value >= ref['high'][0]:
                    return {
                        'status': 'high',
                        'interpretation': 'Valeur très élevée',
                        'color': 'red',
                        'icon': '⚠️'
                    }
                return {
                    'status': 'elevated',
                    'interpretation': 'Valeur modérément élevée',
                    'color': 'orange',
                    'icon': '⚡'
                }
        
        if 'deficiency' in ref and ref['deficiency'][1] and value < ref['deficiency'][1]:
            return {
                'status': 'deficient',
                'interpretation': 'Carence',
                'color': 'red',
                'icon': '⚠️'
            }
        
        if 'insufficient' in ref:
            if ref['insufficient'][0] <= value < ref['insufficient'][1]:
                return {
                    'status': 'insufficient',
                    'interpretation': 'Insuffisance',
                    'color': 'orange',
                    'icon': '⚡'
                }
        
        # Hors normes par défaut
        if normal[0] and value < normal[0]:
            return {
                'status': 'low',
                'interpretation': 'Valeur basse',
                'color': 'orange',
                'icon': '⬇️'
            }
        elif normal[1] and value > normal[1]:
            return {
                'status': 'high',
                'interpretation': 'Valeur élevée',
                'color': 'red',
                'icon': '⬆️'
            }
        
        return {
            'status': 'abnormal',
            'interpretation': 'Valeur anormale',
            'color': 'red',
            'icon': '❌'
        }


class AdvancedPDFExtractor:
    """Extracteur PDF avec support universel (wrapper)"""
    
    @staticmethod
    def extract_text(pdf_file) -> str:
        """Extrait le texte du PDF avec fallback"""
        return UniversalPDFExtractor.extract_text_from_pdf(pdf_file)
    
    @staticmethod
    def extract_biomarkers(text: str, debug: bool = False) -> Dict[str, float]:
        """
        Extrait TOUS les biomarqueurs (mode universel)
        
        Returns:
            Dict[biomarker_key, value]
        """
        # Charger la DB des biomarqueurs connus
        known_db = BiomarkerDatabase.get_reference_ranges()
        
        # Créer extracteur universel
        extractor = UniversalPDFExtractor(known_biomarkers=known_db)
        
        # Extraction complète
        known, all_biomarkers = extractor.extract_complete(text, debug=debug)
        
        # Retourner format compatible (Dict[key, value])
        result = {}
        for key, data in all_biomarkers.items():
            result[key] = data['value']
        
        if debug:
            st.write(f"✅ EXTRACTION UNIVERSELLE: {len(result)} biomarqueurs")
            st.write(f"  - Connus (avec ranges): {len(known)}")
            st.write(f"  - Nouveaux détectés: {len(result) - len(known)}")
        
        return result
    
    @staticmethod
    def extract_patient_info(text: str) -> Dict:
        """Extrait les informations patient du PDF"""
        info = {}
        
        text_lower = text.lower()
        
        # Nom
        name_patterns = [
            r'nom[:\s]+([A-ZÀ-Ÿ\s-]+)',
            r'patient[:\s]+([A-ZÀ-Ÿ\s-]+)',
            r'nom d\'usage[:\s]+([A-ZÀ-Ÿ\s-]+)',
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                info['nom'] = match.group(1).strip()
                break
        
        # Date de naissance
        dob_patterns = [
            r'date de naissance[:\s]+(\d{2}[/.-]\d{2}[/.-]\d{4})',
            r'ddn[:\s]+(\d{2}[/.-]\d{2}[/.-]\d{4})',
            r'n[ée]e? le[:\s]+(\d{2}[/.-]\d{2}[/.-]\d{4})',
        ]
        
        for pattern in dob_patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                info['date_naissance'] = match.group(1)
                # Calculer l'âge
                try:
                    dob = datetime.strptime(match.group(1), '%d/%m/%Y')
                    age = (datetime.now() - dob).days // 365
                    info['age'] = age
                except:
                    pass
                break
        
        # Âge direct
        if 'age' not in info:
            age_patterns = [
                r'(\d{2})\s+ans',
                r'[âa]ge[:\s]+(\d{2})',
            ]
            
            for pattern in age_patterns:
                match = re.search(pattern, text_lower)
                if match:
                    info['age'] = int(match.group(1))
                    break
        
        # Sexe
        sex_patterns = [
            r'sexe[:\s]+(m|f|h)',
            r'\((m|f|h)\)',
        ]
        
        for pattern in sex_patterns:
            match = re.search(pattern, text_lower)
            if match:
                sex_char = match.group(1).upper()
                info['sexe'] = 'Masculin' if sex_char in ['M', 'H'] else 'Féminin'
                break
        
        # Date du prélèvement
        sample_patterns = [
            r'pr[ée]lev[ée] le[:\s]+(\d{2}[/.-]\d{2}[/.-]\d{4})',
            r'date du pr[ée]l[èe]vement[:\s]+(\d{2}[/.-]\d{2}[/.-]\d{4})',
        ]
        
        for pattern in sample_patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                info['prelevement_date'] = match.group(1)
                break
        
        return info


class HealthScoreCalculator:
    """Calculateur avancé de scores de santé et d'âge biologique"""
    
    @staticmethod
    def calculate_biological_age(
        biomarkers: Dict[str, float],
        chronological_age: int,
        sex: str
    ) -> Dict:
        """
        Calcule l'âge biologique selon l'algorithme Horvath modifié
        avec adaptation aux biomarqueurs fonctionnels
        """
        
        # Facteurs de vieillissement avec pondérations
        aging_factors = {
            'inflammation': 0,
            'oxidative_stress': 0,
            'metabolic_health': 0,
            'hormonal_balance': 0,
            'gut_health': 0,
            'cardiovascular': 0,
        }
        
        # Score inflammation (CRP, Homocystéine)
        if 'crp' in biomarkers:
            crp = biomarkers['crp']
            if crp < 1:
                aging_factors['inflammation'] -= 2  # Anti-âge
            elif crp < 3:
                aging_factors['inflammation'] += 0  # Neutre
            elif crp < 10:
                aging_factors['inflammation'] += 3  # Vieillissement
            else:
                aging_factors['inflammation'] += 6  # Fort vieillissement
        
        if 'homocysteine' in biomarkers:
            hcy = biomarkers['homocysteine']
            if hcy < 10:
                aging_factors['cardiovascular'] -= 1
            elif hcy < 15:
                aging_factors['cardiovascular'] += 0
            else:
                aging_factors['cardiovascular'] += 3
        
        # Score stress oxydatif
        if 'glutathion_total' in biomarkers:
            glut = biomarkers['glutathion_total']
            if glut >= 1200:
                aging_factors['oxidative_stress'] -= 2
            elif glut >= 900:
                aging_factors['oxidative_stress'] += 0
            else:
                aging_factors['oxidative_stress'] += 3
        
        if 'coenzyme_q10' in biomarkers:
            coq10 = biomarkers['coenzyme_q10']
            if coq10 >= 670:
                aging_factors['oxidative_stress'] -= 1
            else:
                aging_factors['oxidative_stress'] += 2
        
        # Score métabolique
        if 'homa_index' in biomarkers:
            homa = biomarkers['homa_index']
            if homa < 1:
                aging_factors['metabolic_health'] -= 2
            elif homa < 2.4:
                aging_factors['metabolic_health'] += 0
            else:
                aging_factors['metabolic_health'] += 4
        
        if 'glycemie' in biomarkers:
            gluc = biomarkers['glycemie']
            if gluc < 0.95:
                aging_factors['metabolic_health'] -= 1
            elif gluc < 1.10:
                aging_factors['metabolic_health'] += 0
            else:
                aging_factors['metabolic_health'] += 3
        
        # Score hormonal
        if 'dhea' in biomarkers:
            dhea = biomarkers['dhea']
            optimal_dhea = 7 if sex == 'Masculin' else 6
            
            ratio = dhea / optimal_dhea
            if ratio >= 0.8:
                aging_factors['hormonal_balance'] -= 2
            elif ratio >= 0.5:
                aging_factors['hormonal_balance'] += 0
            else:
                aging_factors['hormonal_balance'] += 3
        
        # Score intestinal
        if 'zonuline' in biomarkers:
            zon = biomarkers['zonuline']
            if zon < 30:
                aging_factors['gut_health'] -= 1
            elif zon < 50:
                aging_factors['gut_health'] += 0
            else:
                aging_factors['gut_health'] += 3
        
        if 'lbp' in biomarkers:
            lbp = biomarkers['lbp']
            if lbp < 6.8:
                aging_factors['gut_health'] -= 1
            else:
                aging_factors['gut_health'] += 2
        
        # Calcul âge biologique
        total_aging_score = sum(aging_factors.values())
        biological_age = chronological_age + (total_aging_score * 0.5)  # Facteur de conversion
        
        delta_age = biological_age - chronological_age
        delta_percent = (delta_age / chronological_age) * 100
        
        # Interprétation
        if delta_age < -3:
            status = "Excellent"
            interpretation = "Âge biologique significativement plus jeune que l'âge chronologique"
        elif delta_age < -1:
            status = "Très bon"
            interpretation = "Âge biologique légèrement plus jeune"
        elif delta_age <= 1:
            status = "Bon"
            interpretation = "Âge biologique en accord avec l'âge chronologique"
        elif delta_age <= 3:
            status = "Modéré"
            interpretation = "Âge biologique légèrement plus élevé"
        else:
            status = "Préoccupant"
            interpretation = "Âge biologique significativement plus élevé"
        
        return {
            'biological_age': round(biological_age, 1),
            'chronological_age': chronological_age,
            'delta': round(delta_age, 1),
            'delta_percent': round(delta_percent, 1),
            'status': status,
            'interpretation': interpretation,
            'aging_factors': aging_factors
        }
    
    @staticmethod
    def calculate_health_score(
        biomarkers: Dict[str, float],
        age: int,
        sex: str
    ) -> Dict:
        """
        Calcule un score de santé global sur 100
        Inspiré du rapport Mme X (Score: 97.8/100, Grade A+)
        """
        
        category_scores = {
            'metabolism': 0,
            'inflammation': 0,
            'hormones': 0,
            'antioxidants': 0,
            'micronutrients': 0,
            'gut_health': 0,
            'cardiovascular': 0,
        }
        
        category_weights = {
            'metabolism': 20,
            'inflammation': 15,
            'hormones': 15,
            'antioxidants': 15,
            'micronutrients': 15,
            'gut_health': 10,
            'cardiovascular': 10,
        }
        
        # Score pour chaque catégorie (0-100)
        
        # MÉTABOLISME
        metab_score = 100
        if 'homa_index' in biomarkers:
            homa = biomarkers['homa_index']
            if homa < 1:
                metab_score = 100
            elif homa < 2.4:
                metab_score = 80
            elif homa < 4:
                metab_score = 60
            else:
                metab_score = 30
        
        if 'glycemie' in biomarkers:
            gluc = biomarkers['glycemie']
            gluc_score = 100
            if gluc > 1.26:
                gluc_score = 30
            elif gluc > 1.10:
                gluc_score = 60
            elif gluc > 0.95:
                gluc_score = 80
            metab_score = (metab_score + gluc_score) / 2
        
        category_scores['metabolism'] = metab_score
        
        # INFLAMMATION
        inflam_score = 100
        if 'crp' in biomarkers:
            crp = biomarkers['crp']
            if crp < 1:
                inflam_score = 100
            elif crp < 3:
                inflam_score = 85
            elif crp < 10:
                inflam_score = 60
            else:
                inflam_score = 30
        
        category_scores['inflammation'] = inflam_score
        
        # HORMONES
        hormone_score = 100
        cortisol_scores = []
        for cort_key in ['cortisol_reveil', 'cortisol_car_30', 'cortisol_12h', 'cortisol_18h', 'cortisol_22h']:
            if cort_key in biomarkers:
                classification = BiomarkerDatabase.classify_biomarker(cort_key, biomarkers[cort_key], age, sex)
                if classification['status'] == 'optimal':
                    cortisol_scores.append(100)
                elif classification['status'] == 'normal':
                    cortisol_scores.append(80)
                else:
                    cortisol_scores.append(50)
        
        if cortisol_scores:
            hormone_score = np.mean(cortisol_scores)
        
        if 'dhea' in biomarkers:
            dhea_class = BiomarkerDatabase.classify_biomarker('dhea', biomarkers['dhea'], age, sex)
            dhea_score = 100 if dhea_class['status'] == 'optimal' else 80 if dhea_class['status'] == 'normal' else 50
            hormone_score = (hormone_score + dhea_score) / 2
        
        category_scores['hormones'] = hormone_score
        
        # ANTIOXYDANTS
        antiox_score = 100
        antiox_list = []
        
        for antiox_key in ['glutathion_total', 'coenzyme_q10', 'gpx']:
            if antiox_key in biomarkers:
                classification = BiomarkerDatabase.classify_biomarker(antiox_key, biomarkers[antiox_key], age, sex)
                if classification['status'] == 'optimal':
                    antiox_list.append(100)
                elif classification['status'] == 'normal':
                    antiox_list.append(80)
                else:
                    antiox_list.append(50)
        
        if antiox_list:
            antiox_score = np.mean(antiox_list)
        
        category_scores['antioxidants'] = antiox_score
        
        # MICRONUTRIMENTS
        micro_score = 100
        micro_list = []
        
        for micro_key in ['vit_d', 'ferritine', 'zinc', 'selenium', 'magnesium_erythrocytaire']:
            if micro_key in biomarkers:
                classification = BiomarkerDatabase.classify_biomarker(micro_key, biomarkers[micro_key], age, sex)
                if classification['status'] in ['optimal', 'normal']:
                    micro_list.append(100)
                elif classification['status'] in ['insufficient', 'low']:
                    micro_list.append(60)
                else:
                    micro_list.append(30)
        
        if micro_list:
            micro_score = np.mean(micro_list)
        
        category_scores['micronutrients'] = micro_score
        
        # SANTÉ INTESTINALE
        gut_score = 100
        gut_list = []
        
        for gut_key in ['zonuline', 'lbp']:
            if gut_key in biomarkers:
                classification = BiomarkerDatabase.classify_biomarker(gut_key, biomarkers[gut_key], age, sex)
                if classification['status'] in ['optimal', 'normal']:
                    gut_list.append(100)
                else:
                    gut_list.append(50)
        
        if gut_list:
            gut_score = np.mean(gut_list)
        
        category_scores['gut_health'] = gut_score
        
        # CARDIOVASCULAIRE
        cardio_score = 100
        cardio_list = []
        
        for cardio_key in ['homocysteine', 'omega3_index', 'aa_epa']:
            if cardio_key in biomarkers:
                classification = BiomarkerDatabase.classify_biomarker(cardio_key, biomarkers[cardio_key], age, sex)
                if classification['status'] in ['optimal', 'normal']:
                    cardio_list.append(100)
                else:
                    cardio_list.append(50)
        
        if cardio_list:
            cardio_score = np.mean(cardio_list)
        
        category_scores['cardiovascular'] = cardio_score
        
        # SCORE GLOBAL PONDÉRÉ
        total_score = 0
        total_weight = 0
        
        for category, score in category_scores.items():
            weight = category_weights[category]
            total_score += score * weight
            total_weight += weight
        
        global_score = total_score / total_weight if total_weight > 0 else 0
        
        # GRADE
        if global_score >= 95:
            grade = "A+"
            grade_label = "Excellent"
        elif global_score >= 90:
            grade = "A"
            grade_label = "Très bon"
        elif global_score >= 85:
            grade = "A-"
            grade_label = "Très bon"
        elif global_score >= 80:
            grade = "B+"
            grade_label = "Bon"
        elif global_score >= 75:
            grade = "B"
            grade_label = "Bon"
        elif global_score >= 70:
            grade = "B-"
            grade_label = "Satisfaisant"
        elif global_score >= 65:
            grade = "C+"
            grade_label = "Moyen"
        elif global_score >= 60:
            grade = "C"
            grade_label = "Moyen"
        else:
            grade = "D"
            grade_label = "Faible"
        
        return {
            'global_score': round(global_score, 1),
            'grade': grade,
            'grade_label': grade_label,
            'category_scores': category_scores,
            'interpretation': f"État de santé {grade_label.lower()}. {'Continuez vos bonnes habitudes.' if global_score >= 90 else 'Améliorations possibles selon recommandations.'}"
        }
    
    @staticmethod
    def calculate_nutritional_needs(
        age: int,
        sex: str,
        weight: float,
        height: float,
        activity_level: str = "moderate"
    ) -> Dict:
        """
        Calcule les besoins nutritionnels (BMR, DET, macros)
        Formules de Mifflin-St Jeor
        """
        
        # BMR (Basal Metabolic Rate)
        if sex == "Masculin":
            bmr = 10 * weight + 6.25 * height - 5 * age + 5
        else:
            bmr = 10 * weight + 6.25 * height - 5 * age - 161
        
        # Facteurs d'activité
        activity_factors = {
            "sedentary": 1.2,
            "light": 1.375,
            "moderate": 1.55,
            "active": 1.725,
            "very_active": 1.9
        }
        
        activity_factor = activity_factors.get(activity_level, 1.55)
        det = bmr * activity_factor
        
        proteins_g = weight * 1.8
        lipids_g = (det * 0.27) / 9
        
        proteins_kcal = proteins_g * 4
        lipids_kcal = lipids_g * 9
        carbs_kcal = det - proteins_kcal - lipids_kcal
        carbs_g = carbs_kcal / 4
        
        return {
            'bmr': round(bmr, 1),
            'det': round(det, 1),
            'proteins_g': round(proteins_g, 1),
            'lipids_g': round(lipids_g, 1),
            'carbs_g': round(carbs_g, 1),
            'activity_level': activity_level
        }


class RecommendationEngine:
    """Moteur de recommandations personnalisées basé sur les biomarqueurs"""
    
    @staticmethod
    def generate_personalized_recommendations(
        biomarkers: Dict[str, float],
        age: int,
        sex: str,
        health_score: Dict,
        biological_age_data: Dict
    ) -> Dict:
        recommendations = {
            'micronutrition': [],
            'alimentation': [],
            'lifestyle': [],
            'supplements': []
        }
        
        priorities = []
        
        for biomarker_key, value in biomarkers.items():
            classification = BiomarkerDatabase.classify_biomarker(biomarker_key, value, age, sex)
            
            if classification['status'] in ['abnormal', 'deficient', 'high', 'elevated', 'low']:
                recs = RecommendationEngine._get_biomarker_recommendations(biomarker_key, value, classification)
                
                for rec_type, rec_list in recs.items():
                    recommendations[rec_type].extend(rec_list)
                
                priorities.append({
                    'biomarker': biomarker_key,
                    'value': value,
                    'status': classification['status'],
                    'priority': 'Élevé' if classification['status'] in ['deficient', 'high'] else 'Moyen'
                })
        
        for key in recommendations:
            recommendations[key] = list(set(recommendations[key]))
        
        return {
            'recommendations': recommendations,
            'priorities': priorities
        }
    
    @staticmethod
    def _get_biomarker_recommendations(biomarker: str, value: float, classification: Dict) -> Dict:
        recs = {
            'micronutrition': [],
            'alimentation': [],
            'lifestyle': [],
            'supplements': []
        }
        
        if biomarker == 'glutathion_total' and classification['status'] in ['low', 'deficient']:
            recs['supplements'].append("N-acétyl-cystéine (NAC) : 600–1200 mg/jour")
            recs['supplements'].append("Glycine : 2–3 g/jour (soir)")
            recs['supplements'].append("Vitamine C : 500–1000 mg/jour")
            recs['alimentation'].append("Privilégiez les protéines soufrées : ail, oignon, crucifères")
            recs['alimentation'].append("Consommez des œufs et du poulet (source de cystéine)")
        
        if biomarker == 'coenzyme_q10' and classification['status'] in ['low', 'deficient']:
            recs['supplements'].append("Coenzyme Q10 (ubiquinol) : 200 mg/jour avec repas gras")
            recs['supplements'].append("PQQ : 10–20 mg/jour")
            recs['alimentation'].append("Mangez des viandes d'organes : cœur, foie")
            recs['alimentation'].append("Intégrez sardines et maquereaux")
            recs['lifestyle'].append("Si vous prenez des statines, la supplémentation en CoQ10 est essentielle")
        
        if biomarker == 'selenium' and classification['status'] in ['low', 'deficient']:
            recs['supplements'].append("Sélénium (sélénométhionine) : 100–200 µg/jour")
            recs['alimentation'].append("Consommez 2-3 noix du Brésil par jour")
            recs['alimentation'].append("Mangez des poissons et fruits de mer")
            recs['alimentation'].append("Consommez des abats et œufs bio")
        
        if biomarker == 'ferritine':
            if classification['status'] == 'deficient':
                recs['supplements'].append("Fer bisglycinate : 30 mg/jour (à jeun avec vitamine C)")
                recs['alimentation'].append("Viandes rouges 2-3x/semaine")
                recs['alimentation'].append("Évitez thé/café pendant les repas")
            elif value > 200:
                recs['lifestyle'].append("Envisagez des saignées thérapeutiques (suivi médical)")
                recs['alimentation'].append("Limitez les aliments enrichis en fer")
        
        if biomarker == 'vit_d':
            if classification['status'] in ['deficient', 'insufficient']:
                dosage = 4000 if value < 20 else 2000
                recs['supplements'].append(f"Vitamine D3 : {dosage} UI/jour")
                recs['lifestyle'].append("Exposition solaire 15-20 min/jour (bras, jambes)")
            elif value > 100:
                recs['lifestyle'].append("Réduire la supplémentation en vitamine D")
        
        if biomarker == 'crp' and value > 3:
            recs['supplements'].append("Oméga-3 (EPA/DHA) : 2-3 g/jour")
            recs['supplements'].append("Curcumine : 500-1000 mg/jour")
            recs['alimentation'].append("Adoptez un régime anti-inflammatoire (méditerranéen)")
            recs['lifestyle'].append("Réduisez le stress chronique")
        
        if biomarker == 'homa_index' and value > 2.4:
            recs['supplements'].append("Berbérine : 500 mg 3x/jour")
            recs['supplements'].append("Chrome picolinate : 200 µg/jour")
            recs['alimentation'].append("Adoptez un régime low-carb (<100g glucides/jour)")
            recs['alimentation'].append("Privilégiez l'index glycémique bas")
            recs['lifestyle'].append("Pratiquez le jeûne intermittent (16:8)")
            recs['lifestyle'].append("Exercice de résistance 3x/semaine")
        
        if biomarker == 'zonuline' and value > 50:
            recs['supplements'].append("L-glutamine : 5-10 g/jour")
            recs['supplements'].append("Zinc carnosine : 75 mg 2x/jour")
            recs['supplements'].append("Probiotiques multi-souches : 50 milliards UFC/jour")
            recs['alimentation'].append("Évitez gluten et produits laitiers pendant 3 mois")
            recs['alimentation'].append("Bouillon d'os 2-3x/semaine")
        
        if biomarker in ['cortisol_reveil', 'cortisol_car_30'] and classification['status'] == 'low':
            recs['supplements'].append("Rhodiola rosea : 200-400 mg/jour")
            recs['supplements'].append("Ashwagandha : 300-600 mg/jour")
            recs['lifestyle'].append("Optimisez votre sommeil (7-9h)")
            recs['lifestyle'].append("Techniques de gestion du stress quotidiennes")
        
        if biomarker == 'dhea' and classification['status'] in ['low', 'deficient']:
            recs['supplements'].append("DHEA : 25-50 mg/jour (sous supervision médicale)")
            recs['lifestyle'].append("Exercice régulier (augmente DHEA naturellement)")
        
        if biomarker == 'homocysteine' and value > 10:
            recs['supplements'].append("Complexe vitamines B : B6 (50mg), B9 (800µg), B12 (1000µg)")
            recs['supplements'].append("TMG (triméthylglycine) : 500-1000 mg/jour")
            recs['alimentation'].append("Légumes verts à feuilles quotidiennement")
        
        return recs


# ============================================================================
# SESSION STATE
# ============================================================================

def init_session_state():
    """Initialise toutes les variables de session"""
    
    if 'patient_data' not in st.session_state:
        st.session_state.patient_data = {
            'patient_info': {},
            'biological_markers': {},
            'epigenetic_data': {},
            'imaging_data': {}
        }
    
    if 'extracted_data' not in st.session_state:
        st.session_state.extracted_data = {
            'biological': {},
            'epigenetic': {},
            'imaging': {},
            'patient_info': {}
        }
    
    if 'analysis_complete' not in st.session_state:
        st.session_state.analysis_complete = False
    
    if 'analysis_results' not in st.session_state:
        st.session_state.analysis_results = None
    
    if 'health_score' not in st.session_state:
        st.session_state.health_score = None
    
    if 'biological_age' not in st.session_state:
        st.session_state.biological_age = None
    
    if 'recommendations' not in st.session_state:
        st.session_state.recommendations = None

    if 'nutritional_needs' not in st.session_state:
        st.session_state.nutritional_needs = None

    if 'engine_results' not in st.session_state:
        st.session_state.engine_results = None

init_session_state()


# ============================================================================
# HEADER
# ============================================================================

col_logo, col_title = st.columns([1, 4])

with col_title:
    st.markdown('<h1 class="main-title">🧬 ALGO-LIFE</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">Plateforme Multimodale d\'Analyse de Santé Fonctionnelle</p>', unsafe_allow_html=True)

st.markdown("---")

# ============================================================================
# SIDEBAR - INFORMATIONS PATIENT
# ============================================================================

with st.sidebar:
    st.header("👤 Informations Patient")

    # ✅ PATCH DEBUG: afficher le fichier réellement chargé
    st.caption("🧪 Debug PDF generator")
    st.code(getattr(pdfgen, "__file__", "unknown"), language="text")
    st.caption(f"PDFGEN LOADED: {datetime.now().strftime('%H:%M:%S')}")

    # ✅ PATCH: bouton reset cache + rerun
    if st.button("🧹 Reset (cache + rerun)", use_container_width=True):
        try:
            st.cache_data.clear()
            st.cache_resource.clear()
        except Exception:
            pass
        st.rerun()
    
    # Auto-fill from extracted data if available
    default_name = st.session_state.extracted_data['patient_info'].get('nom', 'Patient')
    default_age = st.session_state.extracted_data['patient_info'].get('age', 45)
    default_sex_index = 1 if st.session_state.extracted_data['patient_info'].get('sexe') == 'Féminin' else 0
    
    patient_name = st.text_input("Nom complet", value=default_name, key="patient_name_input")
    
    col_age, col_sex = st.columns(2)
    with col_age:
        patient_age = st.number_input("Âge", min_value=18, max_value=120, value=default_age, key="age_input")
    with col_sex:
        patient_sex = st.selectbox("Sexe", ["Masculin", "Féminin"], index=default_sex_index, key="sex_input")
    
    col_height, col_weight = st.columns(2)
    with col_height:
        patient_height = st.number_input("Taille (cm)", min_value=100, max_value=250, value=170, key="height_input")
    with col_weight:
        patient_weight = st.number_input("Poids (kg)", min_value=30.0, max_value=200.0, value=70.0, step=0.1, key="weight_input")
    
    # IMC
    imc = patient_weight / ((patient_height / 100) ** 2)
    st.metric("IMC", f"{imc:.1f}", help="Indice de Masse Corporelle")
    
    # Niveau d'activité
    activity_level = st.selectbox(
        "Niveau d'activité",
        ["sedentary", "light", "moderate", "active", "very_active"],
        index=2,
        format_func=lambda x: {
            "sedentary": "Sédentaire",
            "light": "Léger",
            "moderate": "Modéré",
            "active": "Actif",
            "very_active": "Très actif"
        }[x],
        key="activity_input"
    )
    
    st.divider()
    
    # Date prélèvement
    default_date = datetime.now()
    if 'prelevement_date' in st.session_state.extracted_data['patient_info']:
        try:
            date_str = st.session_state.extracted_data['patient_info']['prelevement_date']
            default_date = datetime.strptime(date_str, '%d/%m/%Y')
        except:
            pass
    
    prelevement_date = st.date_input("Date du prélèvement", value=default_date, key="date_input")
    
    st.divider()
    
    if st.button("💾 Sauvegarder Informations", type="primary", use_container_width=True):
        st.session_state.patient_data['patient_info'] = {
            'nom': patient_name,
            'age': patient_age,
            'sexe': patient_sex,
            'height': patient_height,
            'weight': patient_weight,
            'imc': round(imc, 1),
            'activity_level': activity_level,
            'prelevement_date': prelevement_date.strftime('%Y-%m-%d')
        }
        st.success("✅ Sauvegardé!")
        st.rerun()


# ============================================================================
# TABS PRINCIPAUX
# ============================================================================

tab1, tab2, tab3, tab4 = st.tabs([
    "📤 Import & Extraction",
    "📊 Analyse & Scores",
    "📄 Rapport Professionnel",
    "ℹ️ Documentation"
])

# ============================================================================
# TAB 1 - IMPORT PDF
# ============================================================================

with tab1:
    st.header("📤 Import Automatique des Résultats PDF")
    
    st.markdown("""
    <div class="alert-info">
    <h4>🎯 Instructions d'Import</h4>
    <p>Téléchargez vos fichiers PDF de résultats médicaux. Le système extraira automatiquement:</p>
    <ul>
        <li>✅ <strong>Biologie</strong>: Hormones, métabolisme, inflammation, microbiote, antioxydants</li>
        <li>✅ <strong>Épigénétique</strong>: Âge biologique, méthylation, télomères</li>
        <li>✅ <strong>Imagerie</strong>: DXA, composition corporelle, densité osseuse</li>
    </ul>
    <p><strong>Formats supportés:</strong> Tous les PDF médicaux standards (SYNLAB, LIMS, laboratoires européens)</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    
    # Upload files
    col_upload1, col_upload2, col_upload3 = st.columns(3)
    
    with col_upload1:
        st.subheader("🧪 PDF Biologie")
        bio_pdf = st.file_uploader(
            "Analyses biologiques",
            type=['pdf'],
            key='bio_pdf_upload',
            help="Hormones, métabolisme, inflammation, microbiote..."
        )
        
        if bio_pdf:
            debug_bio = st.checkbox("🐛 Mode Debug", key="debug_bio_check")
            
            if st.button("🔍 Extraire", key="extract_bio_btn", use_container_width=True):
                with st.spinner("Extraction en cours..."):
                    text = AdvancedPDFExtractor.extract_text(bio_pdf)
                    biomarkers = AdvancedPDFExtractor.extract_biomarkers(text, debug=debug_bio)
                    patient_info = AdvancedPDFExtractor.extract_patient_info(text)
                    
                    if biomarkers:
                        st.session_state.extracted_data['biological'] = biomarkers
                        st.session_state.extracted_data['patient_info'].update(patient_info)
                        st.session_state.patient_data['biological_markers'].update(biomarkers)
                        
                        st.success(f"✅ **{len(biomarkers)} biomarqueurs extraits!**")
                        
                        # ✅ AMÉLIORATION: Afficher statistiques
                        known_db = BiomarkerDatabase.get_reference_ranges()
                        known_count = sum(1 for k in biomarkers.keys() if k in known_db)
                        new_count = len(biomarkers) - known_count
                        
                        col_stat1, col_stat2, col_stat3 = st.columns(3)
                        with col_stat1:
                            st.metric("📊 Total Extrait", len(biomarkers))
                        with col_stat2:
                            st.metric("⭐ Connus (avec ranges)", known_count)
                        with col_stat3:
                            st.metric("🆕 Nouveaux Détectés", new_count)
                        
                        if patient_info:
                            st.info(f"ℹ️ Informations patient extraites: {', '.join(patient_info.keys())}")
                        
                        # Afficher preview avec marqueur connu/nouveau
                        with st.expander("📋 Données extraites", expanded=True):
                            df_bio = pd.DataFrame([
                                {
                                    'Biomarqueur': k.replace('_', ' ').title(),
                                    'Valeur': v,
                                    'Type': '⭐ Connu' if k in known_db else '🆕 Nouveau'
                                }
                                for k, v in biomarkers.items()
                            ]).sort_values('Type', ascending=False)
                            st.dataframe(df_bio, use_container_width=True, hide_index=True)
                    else:
                        st.warning("⚠️ Aucune donnée extraite. Essayez le mode Debug.")
    
    with col_upload2:
        st.subheader("🧬 PDF Épigénétique")
        epi_pdf = st.file_uploader(
            "Analyses épigénétiques",
            type=['pdf'],
            key='epi_pdf_upload',
            help="Âge biologique, méthylation, télomères..."
        )
        
        if epi_pdf:
            if st.button("🔍 Extraire", key="extract_epi_btn", use_container_width=True):
                with st.spinner("Extraction en cours..."):
                    text = AdvancedPDFExtractor.extract_text(epi_pdf)
                    
                    epi_data = {}
                    patterns_epi = {
                        'biological_age': r'[âa]ge\s+biologique[:\s]+(\d+\.?\d*)',
                        'telomere_length': r't[ée]lom[èe]re.*?(\d+\.?\d*)',
                        'methylation_score': r'm[ée]thylation.*?(\d+\.?\d*)',
                    }
                    
                    text_lower = text.lower()
                    for key, pattern in patterns_epi.items():
                        match = re.search(pattern, text_lower, re.IGNORECASE)
                        if match:
                            try:
                                value = float(match.group(1))
                                epi_data[key] = value
                            except:
                                pass
                    
                    if epi_data:
                        st.session_state.extracted_data['epigenetic'] = epi_data
                        st.session_state.patient_data['epigenetic_data'].update(epi_data)
                        
                        st.success(f"✅ **{len(epi_data)} paramètres extraits!**")
                        
                        with st.expander("📋 Données extraites"):
                            st.json(epi_data)
                    else:
                        st.warning("⚠️ Aucune donnée épigénétique trouvée.")
    
    with col_upload3:
        st.subheader("🏥 PDF Imagerie")
        img_pdf = st.file_uploader(
            "Analyses DXA",
            type=['pdf'],
            key='img_pdf_upload',
            help="Composition corporelle, densité osseuse..."
        )
        
        if img_pdf:
            if st.button("🔍 Extraire", key="extract_img_btn", use_container_width=True):
                with st.spinner("Extraction en cours..."):
                    text = AdvancedPDFExtractor.extract_text(img_pdf)
                    
                    img_data = {}
                    patterns_img = {
                        'body_fat_percentage': r'masse\s+grasse.*?(\d+\.?\d*)\s*%',
                        'lean_mass': r'masse\s+maigre.*?(\d+\.?\d*)',
                        'bone_density': r'densit[ée].*osseuse.*?(\d+\.?\d*)',
                        'visceral_fat': r'graisse\s+visc[ée]rale.*?(\d+\.?\d*)',
                    }
                    
                    text_lower = text.lower()
                    for key, pattern in patterns_img.items():
                        match = re.search(pattern, text_lower, re.IGNORECASE)
                        if match:
                            try:
                                value = float(match.group(1))
                                img_data[key] = value
                            except:
                                pass
                    
                    if img_data:
                        st.session_state.extracted_data['imaging'] = img_data
                        st.session_state.patient_data['imaging_data'].update(img_data)
                        
                        st.success(f"✅ **{len(img_data)} paramètres extraits!**")
                        
                        with st.expander("📋 Données extraites"):
                            st.json(img_data)
                    else:
                        st.warning("⚠️ Aucune donnée d'imagerie trouvée.")
    
    st.divider()
    
    # Récapitulatif
    st.subheader("📊 Récapitulatif des Données Extraites")
    
    total_bio = len(st.session_state.extracted_data['biological'])
    total_epi = len(st.session_state.extracted_data['epigenetic'])
    total_img = len(st.session_state.extracted_data['imaging'])
    total = total_bio + total_epi + total_img
    
    col_sum1, col_sum2, col_sum3, col_sum4 = st.columns(4)
    with col_sum1:
        st.metric("🧪 Biomarqueurs Bio", total_bio)
    with col_sum2:
        st.metric("🧬 Paramètres Épi", total_epi)
    with col_sum3:
        st.metric("🏥 Données Imagerie", total_img)
    with col_sum4:
        st.metric("📈 Total", total)
    
    if total > 0:
        st.markdown(f"""
        <div class="alert-success">
        <h4>✅ {total} paramètres disponibles pour l'analyse!</h4>
        <p>Cliquez sur le bouton ci-dessous pour lancer l'analyse complète.</p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("🚀 LANCER L'ANALYSE COMPLÈTE", type="primary", use_container_width=True, key="launch_full_analysis"):
            with st.spinner("🔬 Analyse en cours... Cela peut prendre quelques secondes."):
                try:
                    patient_info = st.session_state.patient_data['patient_info']
                    biomarkers = st.session_state.patient_data['biological_markers']
                    
                    if not patient_info or not biomarkers:
                        st.error("❌ Veuillez d'abord enregistrer les informations patient et extraire les biomarqueurs.")
                    else:
                        biological_age_data = HealthScoreCalculator.calculate_biological_age(
                            biomarkers=biomarkers,
                            chronological_age=patient_info['age'],
                            sex=patient_info['sexe']
                        )
                        st.session_state.biological_age = biological_age_data
                        
                        health_score_data = HealthScoreCalculator.calculate_health_score(
                            biomarkers=biomarkers,
                            age=patient_info['age'],
                            sex=patient_info['sexe']
                        )
                        st.session_state.health_score = health_score_data
                        
                        nutritional_needs = HealthScoreCalculator.calculate_nutritional_needs(
                            age=patient_info['age'],
                            sex=patient_info['sexe'],
                            weight=patient_info['weight'],
                            height=patient_info['height'],
                            activity_level=patient_info.get('activity_level', 'moderate')
                        )
                        st.session_state.nutritional_needs = nutritional_needs
                        
                        recommendations_data = RecommendationEngine.generate_personalized_recommendations(
                            biomarkers=biomarkers,
                            age=patient_info['age'],
                            sex=patient_info['sexe'],
                            health_score=health_score_data,
                            biological_age_data=biological_age_data
                        )
                        st.session_state.recommendations = recommendations_data
                        
                        try:
                            engine = AlgoLifeEngine()
                            dxa_data = st.session_state.patient_data.get('imaging_data', {})
                            
                            bio_data_engine = {
                                'hormones_salivaires': {
                                    'cortisol_reveil': biomarkers.get('cortisol_reveil'),
                                    'cortisol_reveil_30': biomarkers.get('cortisol_car_30'),
                                    'cortisol_12h': biomarkers.get('cortisol_12h'),
                                    'cortisol_18h': biomarkers.get('cortisol_18h'),
                                    'cortisol_22h': biomarkers.get('cortisol_22h'),
                                    'dhea': biomarkers.get('dhea')
                                },
                                'inflammation': {
                                    'crp_us': biomarkers.get('crp')
                                },
                                'metabolisme_glucidique': {
                                    'homa': biomarkers.get('homa_index'),
                                    'quicki': biomarkers.get('quicki_index'),
                                    'glycemie': biomarkers.get('glycemie'),
                                    'insuline': biomarkers.get('insuline')
                                },
                                'permeabilite_intestinale': {
                                    'zonuline': biomarkers.get('zonuline'),
                                    'lbp': biomarkers.get('lbp')
                                },
                                'micronutriments': {
                                    'vit_d': biomarkers.get('vit_d'),
                                    'selenium': biomarkers.get('selenium'),
                                    'zinc': biomarkers.get('zinc'),
                                    'ferritine': biomarkers.get('ferritine')
                                }
                            }
                            
                            epi_data_engine = {
                                'epigenetic_age': {
                                    'biological_age': biomarkers.get('biological_age'),
                                    'chronological_age': patient_info['age']
                                }
                            }
                            
                            engine_results = engine.analyze(dxa_data, bio_data_engine, epi_data_engine)
                            st.session_state.engine_results = engine_results
                        except Exception as e:
                            st.warning(f"⚠️ AlgoLifeEngine non disponible: {e}")
                            st.session_state.engine_results = None
                        
                        st.session_state.analysis_complete = True
                        
                        st.success("✅ Analyse complète terminée!")
                        st.balloons()
                        st.info("👉 Consultez l'onglet 'Analyse & Scores' pour voir les résultats détaillés.")
                
                except Exception as e:
                    st.error(f"❌ Erreur lors de l'analyse: {str(e)}")
                    import traceback
                    with st.expander("Détails de l'erreur"):
                        st.code(traceback.format_exc())
    else:
        st.info("📥 Importez au moins un fichier PDF pour commencer.")


# ============================================================================
# TAB 2 - ANALYSE & SCORES
# ============================================================================

with tab2:
    st.header("📊 Analyse Complète & Scores de Santé")
    
    if not st.session_state.analysis_complete:
        st.info("📥 Veuillez d'abord importer des données et lancer l'analyse depuis l'onglet 'Import & Extraction'")
    else:
        st.subheader("🎯 Scores Principaux")
        
        health_score = st.session_state.health_score
        biological_age = st.session_state.biological_age
        
        col_score1, col_score2 = st.columns(2)
        
        with col_score1:
            st.markdown("### Score Santé")
            score = health_score['global_score']
            grade = health_score['grade']
            grade_label = health_score['grade_label']
            
            if score >= 95:
                score_class = "score-excellent"
            elif score >= 80:
                score_class = "score-good"
            elif score >= 60:
                score_class = "score-moderate"
            else:
                score_class = "score-poor"
            
            st.markdown(f"""
            <div class="metric-card" style="text-align: center;">
                <span class="{score_class}">{score}/100</span>
                <h3 style="margin-top: 1rem;">Grade: {grade}</h3>
                <p style="font-size: 1.1rem; color: #4A5568;">{grade_label}</p>
                <p style="margin-top: 1rem;">{health_score['interpretation']}</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col_score2:
            st.markdown("### Âge Biologique")
            bio_age = biological_age['biological_age']
            chrono_age = biological_age['chronological_age']
            delta = biological_age['delta']
            
            if delta < -1:
                color = "#10b981"
                icon = "⬇️"
            elif delta <= 1:
                color = "#3b82f6"
                icon = "↔️"
            else:
                color = "#f59e0b"
                icon = "⬆️"
            
            st.markdown(f"""
            <div class="metric-card" style="text-align: center;">
                <h2 style="color: {color}; font-size: 3rem; margin: 0;">{bio_age} ans</h2>
                <p style="font-size: 1.2rem; color: #4A5568; margin: 0.5rem 0;">
                    Chronologique: {chrono_age} ans
                </p>
                <p style="font-size: 1.5rem; color: {color}; font-weight: 600;">
                    {icon} Delta: {delta:+.1f} ans ({biological_age['delta_percent']:+.1f}%)
                </p>
                <p style="margin-top: 1rem; font-style: italic;">
                    {biological_age['interpretation']}
                </p>
            </div>
            """, unsafe_allow_html=True)
        
        st.divider()
        
        st.subheader("📈 Scores par Catégorie")
        category_scores = health_score['category_scores']
        
        df_categories = pd.DataFrame([
            {
                'Catégorie': cat.replace('_', ' ').title(),
                'Score': round(score, 1),
                'Status': 'Excellent' if score >= 90 else 'Bon' if score >= 75 else 'Moyen' if score >= 60 else 'Faible'
            }
            for cat, score in category_scores.items()
        ]).sort_values('Score', ascending=False)
        
        st.dataframe(df_categories, use_container_width=True, hide_index=True)
        
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(10, 6))
        categories = [cat.replace('_', ' ').title() for cat in category_scores.keys()]
        scores_list = list(category_scores.values())
        colors = ['#10b981' if s >= 90 else '#3b82f6' if s >= 75 else '#f59e0b' if s >= 60 else '#ef4444' for s in scores_list]
        ax.barh(categories, scores_list, color=colors)
        ax.set_xlabel('Score (/100)', fontsize=12, fontweight='bold')
        ax.set_title('Scores par Catégorie', fontsize=14, fontweight='bold')
        ax.set_xlim(0, 100)
        ax.grid(axis='x', alpha=0.3)
        plt.tight_layout()
        st.pyplot(fig)
        
        st.divider()
        
        st.subheader("🔬 Classification des Biomarqueurs")
        
        biomarkers = st.session_state.patient_data['biological_markers']
        patient_info = st.session_state.patient_data['patient_info']
        
        classified = {
            'normaux': [], 
            'a_surveiller': [], 
            'anormaux': [],
            'non_references': []  # ✅ NOUVEAU
        }
        
        for biomarker_key, value in biomarkers.items():
            classification = BiomarkerDatabase.classify_biomarker(
                biomarker_key,
                value,
                patient_info.get('age'),
                patient_info.get('sexe')
            )
            
            refs = BiomarkerDatabase.get_reference_ranges()
            bio_info = refs.get(biomarker_key, {})
            
            item = {
                'Biomarqueur': biomarker_key.replace('_', ' ').title(),
                'Valeur': value,
                'Unité': bio_info.get('unit', ''),
                'Status': classification.get('status', 'unknown'),
                'Interprétation': classification.get('interpretation', ''),
                'Icon': classification.get('icon', '')
            }
            
            if classification.get('status') in ['optimal', 'normal']:
                classified['normaux'].append(item)
            elif classification.get('status') in ['insufficient', 'low', 'elevated']:
                classified['a_surveiller'].append(item)
            elif classification.get('status') in ['deficient', 'high', 'abnormal']:
                classified['anormaux'].append(item)
            else:
                classified['non_references'].append(item)  # ✅ NOUVEAU
        
        col_class1, col_class2, col_class3, col_class4 = st.columns(4)
        with col_class1:
            st.metric("✅ Normaux", len(classified['normaux']), delta=None)
        with col_class2:
            st.metric("⚡ À surveiller", len(classified['a_surveiller']), delta=None)
        with col_class3:
            st.metric("⚠️ Anormaux", len(classified['anormaux']), delta=None)
        with col_class4:
            st.metric("❓ Non référencés", len(classified['non_references']), delta=None)
        
        with st.expander("✅ Biomarqueurs Normaux", expanded=False):
            if classified['normaux']:
                st.dataframe(pd.DataFrame(classified['normaux']), use_container_width=True, hide_index=True)
            else:
                st.info("Aucun biomarqueur normal.")
        
        with st.expander("⚡ Biomarqueurs À Surveiller", expanded=True):
            if classified['a_surveiller']:
                st.dataframe(pd.DataFrame(classified['a_surveiller']), use_container_width=True, hide_index=True)
            else:
                st.success("Aucun biomarqueur à surveiller.")
        
        with st.expander("⚠️ Biomarqueurs Anormaux", expanded=True):
            if classified['anormaux']:
                st.dataframe(pd.DataFrame(classified['anormaux']), use_container_width=True, hide_index=True)
            else:
                st.success("Aucun biomarqueur anormal.")
        
        # ✅ NOUVEAU: Expander pour biomarqueurs non référencés
        with st.expander("❓ Biomarqueurs Non Référencés (nouveaux détectés)", expanded=False):
            if classified['non_references']:
                st.info(f"""
                Ces {len(classified['non_references'])} biomarqueurs ont été extraits du PDF mais 
                n'ont pas encore de plages de référence dans la base ALGO-LIFE.
                
                👉 Vous pouvez les visualiser ci-dessous et les ajouter à la base si pertinents.
                """)
                st.dataframe(
                    pd.DataFrame(classified['non_references']), 
                    use_container_width=True, 
                    hide_index=True
                )
            else:
                st.success("Tous les biomarqueurs extraits sont référencés!")
        
        st.divider()
        
        st.subheader("🍽️ Besoins Nutritionnels Calculés")
        nutritional_needs = st.session_state.nutritional_needs
        
        col_nut1, col_nut2, col_nut3, col_nut4, col_nut5 = st.columns(5)
        with col_nut1:
            st.metric("BMR", f"{nutritional_needs['bmr']:.0f} kcal", help="Métabolisme de base")
        with col_nut2:
            st.metric("DET", f"{nutritional_needs['det']:.0f} kcal", help="Dépense énergétique totale")
        with col_nut3:
            st.metric("Protéines", f"{nutritional_needs['proteins_g']:.0f} g", help="Besoin quotidien")
        with col_nut4:
            st.metric("Lipides", f"{nutritional_needs['lipids_g']:.0f} g", help="Besoin quotidien")
        with col_nut5:
            st.metric("Glucides", f"{nutritional_needs['carbs_g']:.0f} g", help="Besoin quotidien")
        
        st.divider()
        
        st.subheader("💡 Recommandations Personnalisées")
        recommendations = st.session_state.recommendations
        
        if recommendations and recommendations.get('priorities'):
            st.markdown("#### ⚠️ Priorités d'Action")
            for i, priority in enumerate(recommendations['priorities'][:5], 1):
                biomarker_name = priority['biomarker'].replace('_', ' ').title()
                value = priority['value']
                status = priority['status']
                priority_level = priority['priority']
                alert_class = "alert-danger" if priority_level == "Élevé" else "alert-warning"
                
                st.markdown(f"""
                <div class="{alert_class}">
                    <strong>#{i} - {biomarker_name}</strong> ({priority_level})
                    <br>Valeur: {value} - Status: {status}
                </div>
                """, unsafe_allow_html=True)
        
        st.markdown("#### 📋 Recommandations Détaillées")
        tabs_reco = st.tabs(["💊 Suppléments", "🥗 Alimentation", "🏃 Lifestyle"])
        
        with tabs_reco[0]:
            supps = (recommendations or {}).get('recommendations', {}).get('supplements', [])
            if supps:
                for supplement in supps:
                    st.markdown(f"- {supplement}")
            else:
                st.info("Aucune supplémentation spécifique recommandée.")
        
        with tabs_reco[1]:
            alims = (recommendations or {}).get('recommendations', {}).get('alimentation', [])
            if alims:
                for aliment in alims:
                    st.markdown(f"- {aliment}")
            else:
                st.info("Aucune recommandation alimentaire spécifique.")
        
        with tabs_reco[2]:
            lifes = (recommendations or {}).get('recommendations', {}).get('lifestyle', [])
            if lifes:
                for lifestyle in lifes:
                    st.markdown(f"- {lifestyle}")
            else:
                st.info("Aucune recommandation lifestyle spécifique.")


# ============================================================================
# TAB 3 - RAPPORT PDF
# ============================================================================

with tab3:
    st.header("📄 Génération du Rapport Professionnel")
    
    if not st.session_state.analysis_complete:
        st.info("📥 Veuillez d'abord effectuer une analyse complète depuis l'onglet 'Import & Extraction'")
    else:
        st.markdown("""
        <div class="alert-success">
        <h4>✅ Rapport Prêt à Générer</h4>
        <p>Le rapport PDF comprendra:</p>
        <ul>
            <li>✅ Informations patient</li>
            <li>✅ Scores de santé et âge biologique</li>
            <li>✅ Classification complète des biomarqueurs</li>
            <li>✅ Besoins nutritionnels calculés</li>
            <li>✅ Recommandations personnalisées multi-niveaux</li>
            <li>✅ Graphiques et visualisations</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("📥 GÉNÉRER LE RAPPORT PDF", type="primary", use_container_width=True, key="generate_pdf_btn"):
            with st.spinner("📄 Génération du rapport en cours... Cela peut prendre quelques secondes."):
                try:
                    pdf_buffer = generate_algolife_pdf_report(
                        patient_data=st.session_state.patient_data,
                        biomarker_results=st.session_state.patient_data["biological_markers"],
                        health_score=st.session_state.health_score,
                        biological_age=st.session_state.biological_age,
                        nutritional_needs=st.session_state.nutritional_needs,
                        recommendations=st.session_state.recommendations,
                        engine_results=st.session_state.engine_results,
                        chart_buffer=None
                    )

                    st.success("✅ Rapport PDF généré avec succès!")
                    
                    patient_name = st.session_state.patient_data['patient_info'].get('nom', 'Patient')
                    filename = f"ALGO-LIFE_{patient_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf"
                    
                    st.download_button(
                        label="📥 TÉLÉCHARGER LE RAPPORT PDF",
                        data=pdf_buffer.getvalue(),
                        file_name=filename,
                        mime="application/pdf",
                        type="primary",
                        use_container_width=True
                    )
                    
                    st.balloons()
                    
                except Exception as e:
                    st.error(f"❌ Erreur lors de la génération du PDF: {str(e)}")
                    import traceback
                    with st.expander("Détails de l'erreur"):
                        st.code(traceback.format_exc())


# ============================================================================
# TAB 4 - DOCUMENTATION
# ============================================================================

with tab4:
    st.header("ℹ️ Documentation ALGO-LIFE")
    
    st.markdown(f"""
    ### 🎯 Vue d'Ensemble
    
    **ALGO-LIFE** est une plateforme multimodale d'analyse de santé fonctionnelle qui intègre:
    
    - **Biologie fonctionnelle**: Hormones, métabolisme, inflammation, neurotransmetteurs, microbiote
    - **Épigénétique**: Âge biologique, méthylation, télomères
    - **Imagerie DXA**: Composition corporelle, densité osseuse
    
    ### 📋 Workflow Complet
    
    #### 1️⃣ Import des Données
    - Téléchargez vos PDF de résultats médicaux
    - Le système extrait automatiquement les biomarqueurs (MODE UNIVERSEL ✨)
    - Complétez les informations patient
    - Lancez l'analyse complète
    
    #### 2️⃣ Analyse & Scores
    - **Score Santé Global** (0-100) avec grade (A+ à D)
    - **Âge Biologique** calculé selon algorithme Horvath modifié
    - **Scores par Catégorie**: Métabolisme, Inflammation, Hormones, etc.
    - **Classification des Biomarqueurs**: Normaux / À surveiller / Anormaux / Non référencés
    - **Besoins Nutritionnels**: BMR, DET, macronutriments
    
    #### 3️⃣ Recommandations
    - **Micronutrition ciblée** selon déficits identifiés
    - **Conseils alimentaires** personnalisés
    - **Optimisation lifestyle**
    - **Protocoles de supplémentation** avec dosages
    
    #### 4️⃣ Rapport Professionnel
    - Génération d'un rapport PDF complet
    - Design professionnel et lisible
    - Graphiques et visualisations
    - Prêt pour consultation patient
    
    ### 📞 Support & Contact
    
    **Développeur**: Dr Thibault SUTTER - Biologiste  
    **Organisation**: ALGO-LIFE / Espace Lab SA (Unilabs Group)  
    **Email**: contact@bilan-hormonal.com  
    **Site**: https://bilan-hormonal.com  
    
    **Version**: 4.1 - Janvier 2026 (Extraction Universelle)  
    **Dernière mise à jour**: {datetime.now().strftime('%d/%m/%Y')}
    
    ### ⚖️ Disclaimer
    
    ALGO-LIFE est un outil d'aide à la décision médicale. Les résultats et recommandations doivent être 
    interprétés par un professionnel de santé qualifié. Ne remplace pas une consultation médicale.
    """)

# ============================================================================
# FOOTER
# ============================================================================

st.divider()

col_footer1, col_footer2, col_footer3 = st.columns(3)

with col_footer1:
    st.caption("© 2026 ALGO-LIFE")
    st.caption("Dr Thibault SUTTER - Biologiste")

with col_footer2:
    st.caption("Espace Lab SA (Unilabs Group)")
    st.caption("Geneva, Switzerland")

with col_footer3:
    st.caption("Version 4.1 - Janvier 2026")
    st.caption(f"Dernière exécution: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
