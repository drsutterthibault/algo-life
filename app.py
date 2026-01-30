"""
ALGO-LIFE - Plateforme Multimodale d'Analyse de Santé Fonctionnelle
Version 4.1.1 - Janvier 2026 - EXTRACTION UNIVERSELLE (PATCH)

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
        "Get Help": "https://bilan-hormonal.com",
        "Report a bug": "mailto:contact@bilan-hormonal.com",
        "About": "ALGO-LIFE v4.1.1 - Plateforme d'analyse multimodale de santé",
    },
)

# ============================================================================
# STYLES CSS PROFESSIONNELS
# ============================================================================

st.markdown(
    """
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
""",
    unsafe_allow_html=True,
)

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
            "cortisol_reveil": {
                "unit": "nmol/L",
                "optimal": (10, 38),
                "normal": (5, 50),
                "category": "Hormones",
                "lab_names": ["cortisol réveil", "cortisol salivaire réveil", "cortisol awakening"],
            },
            "cortisol_car_30": {
                "unit": "nmol/L",
                "optimal": (20, 45),
                "normal": (10, 55),
                "category": "Hormones",
                "lab_names": ["cortisol CAR (+30min)", "cortisol réveil +30", "cortisol +30min"],
            },
            "cortisol_12h": {
                "unit": "nmol/L",
                "optimal": (3, 10),
                "normal": (1.5, 15),
                "category": "Hormones",
                "lab_names": ["cortisol 12h", "cortisol midi"],
            },
            "cortisol_18h": {
                "unit": "nmol/L",
                "optimal": (1.5, 7.64),
                "normal": (1, 10),
                "category": "Hormones",
                "lab_names": ["cortisol 18h", "cortisol soir"],
            },
            "cortisol_22h": {
                "unit": "nmol/L",
                "optimal": (0.5, 3),
                "normal": (0.3, 5),
                "category": "Hormones",
                "lab_names": ["cortisol 22h", "cortisol nuit", "cortisol coucher"],
            },
            "dhea": {
                "unit": "ng/mL",
                "optimal_male": (6, 10),
                "optimal_female": (4, 8),
                "normal_male": (3, 15),
                "normal_female": (2, 12),
                "category": "Hormones",
                "lab_names": ["dhea", "dhea salivaire", "dehydroepiandrosterone"],
            },
            # INFLAMMATION
            "crp": {
                "unit": "mg/L",
                "optimal": (0, 1),
                "normal": (0, 3),
                "elevated": (3, 10),
                "high": (10, None),
                "category": "Inflammation",
                "lab_names": ["crp ultrasensible", "crp us", "crp haute sensibilité", "hs-crp"],
            },
            # MÉTABOLISME GLUCIDIQUE
            "glycemie": {
                "unit": "g/L",
                "optimal": (0.70, 0.95),
                "normal": (0.70, 1.10),
                "prediabetes": (1.10, 1.26),
                "diabetes": (1.26, None),
                "category": "Métabolisme",
                "lab_names": ["glycémie à jeun", "glycémie", "glucose"],
            },
            "insuline": {
                "unit": "mUI/L",
                "optimal": (2, 7),
                "normal": (2, 25),
                "category": "Métabolisme",
                "lab_names": ["insuline à jeun", "insuline"],
            },
            "homa_index": {
                "unit": "",
                "optimal": (0, 1),
                "normal": (0, 2.4),
                "insulin_resistance": (2.4, None),
                "category": "Métabolisme",
                "lab_names": ["homa-ir", "index homa", "homa"],
            },
            "quicki_index": {
                "unit": "",
                "optimal": (0.38, None),
                "insulin_sensitive": (0.35, None),
                "insulin_resistance": (None, 0.35),
                "category": "Métabolisme",
                "lab_names": ["quicki", "index quicki"],
            },
            # MICRONUTRIMENTS
            "ferritine": {
                "unit": "µg/L",
                "deficiency": (None, 15),
                "low": (15, 30),
                "optimal": (30, 100),
                "normal_female": (10, 291),
                "normal_male": (30, 400),
                "category": "Micronutriments",
                "lab_names": ["ferritine"],
            },
            "vit_d": {
                "unit": "ng/mL",
                "deficiency": (None, 20),
                "insufficient": (20, 30),
                "optimal": (30, 60),
                "normal": (30, 100),
                "toxicity": (150, None),
                "category": "Micronutriments",
                "lab_names": ["vitamine d", "25-oh vitamine d", "25-oh d", "vitamin d"],
            },
            "zinc": {
                "unit": "µg/dL",
                "optimal": (88, 146),
                "normal": (70, 150),
                "category": "Micronutriments",
                "lab_names": ["zinc"],
            },
            "selenium": {
                "unit": "µg/L",
                "optimal": (90, 143),
                "normal": (70, 150),
                "category": "Micronutriments",
                "lab_names": ["sélénium", "selenium"],
            },
            "magnesium_erythrocytaire": {
                "unit": "mg/dL",
                "optimal": (4.4, 5.8),
                "normal": (4.0, 6.0),
                "category": "Micronutriments",
                "lab_names": ["magnésium érythrocytaire", "mg érythrocytaire"],
            },
            # ANTIOXYDANTS
            "glutathion_total": {
                "unit": "µmol/L",
                "optimal": (1200, 1750),
                "normal": (900, 1800),
                "category": "Antioxydants",
                "lab_names": ["glutathion total", "glutathione"],
            },
            "coenzyme_q10": {
                "unit": "µg/L",
                "optimal": (670, 990),
                "normal": (500, 1000),
                "category": "Antioxydants",
                "lab_names": ["coenzyme q10", "coq10", "ubiquinone"],
            },
            "gpx": {
                "unit": "U/g Hb",
                "optimal": (40, 62),
                "normal": (30, 70),
                "category": "Antioxydants",
                "lab_names": ["glutathion peroxydase", "gpx"],
            },
            # PERMÉABILITÉ INTESTINALE
            "zonuline": {
                "unit": "ng/mL",
                "optimal": (0, 30),
                "normal": (0, 50),
                "elevated": (50, 100),
                "high": (100, None),
                "category": "Intestin",
                "lab_names": ["zonuline"],
            },
            "lbp": {
                "unit": "mg/L",
                "optimal": (0, 6.8),
                "normal": (2.3, 8.3),
                "category": "Intestin",
                "lab_names": ["lbp", "lps-binding protein", "lipopolysaccharide binding protein"],
            },
            # NEUROTRANSMETTEURS
            "dopamine": {
                "unit": "µg/24h",
                "optimal": (150, 400),
                "normal": (100, 500),
                "category": "Neurotransmetteurs",
                "lab_names": ["dopamine"],
            },
            "serotonine": {
                "unit": "µg/24h",
                "optimal": (100, 250),
                "normal": (50, 300),
                "category": "Neurotransmetteurs",
                "lab_names": ["sérotonine", "serotonine"],
            },
            "noradrenaline": {
                "unit": "µg/24h",
                "optimal": (15, 80),
                "normal": (10, 100),
                "category": "Neurotransmetteurs",
                "lab_names": ["noradrénaline", "noradrenaline", "norepinephrine"],
            },
            "adrenaline": {
                "unit": "µg/24h",
                "optimal": (2, 20),
                "normal": (1, 25),
                "category": "Neurotransmetteurs",
                "lab_names": ["adrénaline", "adrenaline", "epinephrine"],
            },
            # CARDIOVASCULAIRE
            "homocysteine": {
                "unit": "µmol/L",
                "optimal": (5, 10),
                "normal": (5, 15),
                "elevated": (15, 30),
                "high": (30, None),
                "category": "Cardiovasculaire",
                "lab_names": ["homocystéine", "homocysteine"],
            },
            "omega3_index": {
                "unit": "%",
                "optimal": (8, None),
                "moderate": (6, 8),
                "low": (4, 6),
                "deficient": (None, 4),
                "category": "Cardiovasculaire",
                "lab_names": ["index oméga-3", "omega-3 index", "index w3"],
            },
            "aa_epa": {
                "unit": "",
                "optimal": (1, 3),
                "normal": (1, 5),
                "elevated": (5, 15),
                "high": (15, None),
                "category": "Cardiovasculaire",
                "lab_names": ["rapport aa/epa", "aa/epa ratio"],
            },
        }

    @staticmethod
    def classify_biomarker(name: str, value: float, age: int = None, sex: str = None) -> Dict:
        """Classifie un biomarqueur selon sa valeur"""
        refs = BiomarkerDatabase.get_reference_ranges()

        if name not in refs:
            # ✅ AMÉLIORATION: Ne pas rejeter, retourner statut "non référencé"
            return {
                "status": "unknown",
                "interpretation": f"Biomarqueur détecté mais non référencé (valeur: {value})",
                "color": "gray",
                "icon": "❓",
                "value": value,
                "needs_reference": True,
            }

        ref = refs[name]

        # Gestion sexe-spécifique (DHEA, Ferritine)
        if "optimal_male" in ref and "optimal_female" in ref:
            if sex == "Masculin":
                optimal = ref["optimal_male"]
                normal = ref.get("normal_male", optimal)
            else:
                optimal = ref["optimal_female"]
                normal = ref.get("normal_female", optimal)
        else:
            optimal = ref.get("optimal", (None, None))
            normal = ref.get("normal", optimal)

        # Classification
        if optimal[0] is not None and optimal[1] is not None:
            if optimal[0] <= value <= optimal[1]:
                return {"status": "optimal", "interpretation": "Valeur optimale", "color": "green", "icon": "✅"}

        if normal[0] is not None and normal[1] is not None:
            if normal[0] <= value <= normal[1]:
                return {"status": "normal", "interpretation": "Valeur normale", "color": "lightgreen", "icon": "✓"}

        # Cas spéciaux avec seuils multiples
        if "elevated" in ref:
            if ref["elevated"][0] <= value:
                if "high" in ref and ref["high"][0] and value >= ref["high"][0]:
                    return {"status": "high", "interpretation": "Valeur très élevée", "color": "red", "icon": "⚠️"}
                return {"status": "elevated", "interpretation": "Valeur modérément élevée", "color": "orange", "icon": "⚡"}

        if "deficiency" in ref and ref["deficiency"][1] and value < ref["deficiency"][1]:
            return {"status": "deficient", "interpretation": "Carence", "color": "red", "icon": "⚠️"}

        if "insufficient" in ref:
            if ref["insufficient"][0] <= value < ref["insufficient"][1]:
                return {"status": "insufficient", "interpretation": "Insuffisance", "color": "orange", "icon": "⚡"}

        # Hors normes par défaut
        if normal[0] is not None and value < normal[0]:
            return {"status": "low", "interpretation": "Valeur basse", "color": "orange", "icon": "⬇️"}
        elif normal[1] is not None and value > normal[1]:
            return {"status": "high", "interpretation": "Valeur élevée", "color": "red", "icon": "⬆️"}

        return {"status": "abnormal", "interpretation": "Valeur anormale", "color": "red", "icon": "❌"}


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
        known_db = BiomarkerDatabase.get_reference_ranges()
        extractor = UniversalPDFExtractor(known_biomarkers=known_db)

        known, all_biomarkers = extractor.extract_complete(text, debug=debug)

        result = {}
        for key, data in all_biomarkers.items():
            result[key] = data["value"]

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
            r"nom[:\s]+([A-ZÀ-Ÿ\s-]+)",
            r"patient[:\s]+([A-ZÀ-Ÿ\s-]+)",
            r"nom d\'usage[:\s]+([A-ZÀ-Ÿ\s-]+)",
        ]
        for pattern in name_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                info["nom"] = match.group(1).strip()
                break

        # Date de naissance
        dob_patterns = [
            r"date de naissance[:\s]+(\d{2}[/.-]\d{2}[/.-]\d{4})",
            r"ddn[:\s]+(\d{2}[/.-]\d{2}[/.-]\d{4})",
            r"n[ée]e? le[:\s]+(\d{2}[/.-]\d{2}[/.-]\d{4})",
        ]
        for pattern in dob_patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                info["date_naissance"] = match.group(1)
                try:
                    dob = datetime.strptime(match.group(1).replace(".", "/").replace("-", "/"), "%d/%m/%Y")
                    age = (datetime.now() - dob).days // 365
                    info["age"] = age
                except Exception:
                    pass
                break

        # Âge direct
        if "age" not in info:
            age_patterns = [r"(\d{2})\s+ans", r"[âa]ge[:\s]+(\d{2})"]
            for pattern in age_patterns:
                match = re.search(pattern, text_lower)
                if match:
                    try:
                        info["age"] = int(match.group(1))
                    except Exception:
                        pass
                    break

        # Sexe
        sex_patterns = [r"sexe[:\s]+(m|f|h)", r"\((m|f|h)\)"]
        for pattern in sex_patterns:
            match = re.search(pattern, text_lower)
            if match:
                sex_char = match.group(1).upper()
                info["sexe"] = "Masculin" if sex_char in ["M", "H"] else "Féminin"
                break

        # Date du prélèvement
        sample_patterns = [
            r"pr[ée]lev[ée] le[:\s]+(\d{2}[/.-]\d{2}[/.-]\d{4})",
            r"date du pr[ée]l[èe]vement[:\s]+(\d{2}[/.-]\d{2}[/.-]\d{4})",
        ]
        for pattern in sample_patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                info["prelevement_date"] = match.group(1)
                break

        return info


class HealthScoreCalculator:
    """Calculateur avancé de scores de santé et d'âge biologique"""

    @staticmethod
