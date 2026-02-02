"""
ALGO-LIFE - Plateforme Multimodale d'Analyse de Santé Fonctionnelle
Version 4.1 - Janvier 2026 - EXTRACTION UNIVERSELLE + MICROBIOTE

Intégration multimodale:
- Biologie fonctionnelle (hormones, métabolisme, inflammation, microbiote)
- Épigénétique (âge biologique, méthylation, télomères)
- Imagerie DXA (composition corporelle, densité osseuse)
- Microbiote (analyse du microbiome intestinal)

Auteur: Dr Thibault SUTTER - Biologiste
Organisation: ALGO-LIFE / Espace Lab SA (Unilabs Group)
Email: contact@bilan-hormonal.com
"""

from __future__ import annotations

import re
import json
import importlib
from io import BytesIO
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import streamlit as st

# PDF extraction libs (optional)
try:
    import PyPDF2  # noqa: F401
    import pdfplumber  # noqa: F401
    PDF_AVAILABLE = True
except Exception:
    PDF_AVAILABLE = False

# Import modules ALGO-LIFE
from algolife_engine import AlgoLifeEngine
from algolife_statistical_analysis import AlgoLifeStatisticalAnalysis  # noqa: F401

# ✅ Universal extractor (required for "universal" mode)
try:
    from advanced_pdf_extractor_universal import UniversalPDFExtractor
    UNIVERSAL_EXTRACTOR_AVAILABLE = True
except Exception as e:
    UNIVERSAL_EXTRACTOR_AVAILABLE = False
    _UNIVERSAL_IMPORT_ERROR = str(e)

# ✅ PATCH: force reload module PDF (évite ancienne version / cache / doublon)
import algolife_pdf_generator as pdfgen
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
        "About": "ALGO-LIFE v4.1 - Plateforme d'analyse multimodale de santé",
    },
)

# ============================================================================
# STYLES CSS PROFESSIONNELS
# ============================================================================

st.markdown(
    """
<style>
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
    .stTabs [data-baseweb="tab-list"] { gap: 2rem; }
    .stTabs [data-baseweb="tab"] {
        height: 60px;
        padding: 1rem 2rem;
        font-weight: 600;
        font-size: 1.1rem;
    }
    .dataframe { border-radius: 10px; overflow: hidden; }
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
    def get_reference_ranges() -> Dict[str, Dict]:
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
                "optimal": (15, 50),
                "normal": (10, 60),
                "category": "Hormones",
                "lab_names": ["cortisol car+30", "cortisol 30min", "cortisol awakening response"],
            },
            "cortisol_12h": {
                "unit": "nmol/L",
                "optimal": (3, 12),
                "normal": (2, 15),
                "category": "Hormones",
                "lab_names": ["cortisol 12h", "cortisol midi", "cortisol noon"],
            },
            "cortisol_18h": {
                "unit": "nmol/L",
                "optimal": (1, 8),
                "normal": (0.5, 10),
                "category": "Hormones",
                "lab_names": ["cortisol 18h", "cortisol soir"],
            },
            "cortisol_22h": {
                "unit": "nmol/L",
                "optimal": (0.5, 5),
                "normal": (0.2, 8),
                "category": "Hormones",
                "lab_names": ["cortisol 22h", "cortisol coucher", "cortisol bedtime"],
            },
            "dhea": {
                "unit": "pg/mL",
                "optimal": (500, 2500),
                "normal": (200, 3500),
                "category": "Hormones",
                "lab_names": ["dhea", "dhea-s", "dehydroepiandrosterone"],
            },
            "melatonine": {
                "unit": "pg/mL",
                "optimal": (10, 50),
                "normal": (5, 80),
                "category": "Hormones",
                "lab_names": ["mélatonine", "melatonin"],
            },
            "testosterone": {
                "unit": "nmol/L",
                "optimal": (12, 35),
                "normal": (8, 40),
                "category": "Hormones",
                "lab_names": ["testostérone", "testosterone", "testo"],
            },
            # INFLAMMATION
            "crp": {
                "unit": "mg/L",
                "optimal": (0, 1),
                "normal": (0, 3),
                "category": "Inflammation",
                "lab_names": ["crp", "crp ultrasensible", "crp-us", "c-reactive protein"],
            },
            "homocysteine": {
                "unit": "µmol/L",
                "optimal": (5, 10),
                "normal": (5, 15),
                "category": "Inflammation",
                "lab_names": ["homocystéine", "homocysteine", "hcy"],
            },
            # MÉTABOLISME
            "glycemie": {
                "unit": "g/L",
                "optimal": (0.70, 1.00),
                "normal": (0.65, 1.10),
                "category": "Métabolisme",
                "lab_names": ["glycémie", "glucose", "glycémie à jeun"],
            },
            "insuline": {
                "unit": "mUI/L",
                "optimal": (2, 10),
                "normal": (2, 25),
                "category": "Métabolisme",
                "lab_names": ["insuline", "insulin"],
            },
            "hba1c": {
                "unit": "%",
                "optimal": (4.0, 5.6),
                "normal": (4.0, 6.0),
                "category": "Métabolisme",
                "lab_names": ["hba1c", "hemoglobine glyquée", "glycated hemoglobin"],
            },
            "cholesterol_total": {
                "unit": "g/L",
                "optimal": (1.50, 2.00),
                "normal": (1.50, 2.50),
                "category": "Métabolisme",
                "lab_names": ["cholestérol total", "total cholesterol"],
            },
            "hdl": {
                "unit": "g/L",
                "optimal": (0.50, 1.00),
                "normal": (0.40, 1.50),
                "category": "Métabolisme",
                "lab_names": ["hdl", "hdl cholesterol"],
            },
            "ldl": {
                "unit": "g/L",
                "optimal": (0.70, 1.30),
                "normal": (0.70, 1.60),
                "category": "Métabolisme",
                "lab_names": ["ldl", "ldl cholesterol"],
            },
            "triglycerides": {
                "unit": "g/L",
                "optimal": (0.50, 1.00),
                "normal": (0.50, 1.50),
                "category": "Métabolisme",
                "lab_names": ["triglycérides", "triglycerides", "tg"],
            },
            # MICRONUTRIMENTS
            "vitamine_d": {
                "unit": "ng/mL",
                "optimal": (40, 70),
                "normal": (30, 100),
                "category": "Micronutriments",
                "lab_names": ["vitamine d", "25oh vitamin d", "25-hydroxyvitamin d", "vitamine d3"],
            },
            "vitamine_b12": {
                "unit": "pg/mL",
                "optimal": (400, 900),
                "normal": (200, 1100),
                "category": "Micronutriments",
                "lab_names": ["vitamine b12", "vitamin b12", "cobalamine"],
            },
            "magnesium": {
                "unit": "mg/L",
                "optimal": (20, 26),
                "normal": (18, 30),
                "category": "Micronutriments",
                "lab_names": ["magnésium", "magnesium", "mg"],
            },
            "zinc": {
                "unit": "µg/dL",
                "optimal": (70, 120),
                "normal": (60, 150),
                "category": "Micronutriments",
                "lab_names": ["zinc", "zn"],
            },
            "selenium": {
                "unit": "µg/L",
                "optimal": (80, 120),
                "normal": (70, 150),
                "category": "Micronutriments",
                "lab_names": ["sélénium", "selenium", "se"],
            },
            "ferritine": {
                "unit": "ng/mL",
                "optimal": (50, 150),
                "normal": (30, 300),
                "category": "Micronutriments",
                "lab_names": ["ferritine", "ferritin"],
            },
            # PERMÉABILITÉ INTESTINALE
            "zonuline": {
                "unit": "ng/mL",
                "optimal": (0, 40),
                "normal": (0, 60),
                "category": "Perméabilité intestinale",
                "lab_names": ["zonuline", "zonulin"],
            },
            "lbp": {
                "unit": "µg/mL",
                "optimal": (0, 10),
                "normal": (0, 15),
                "category": "Perméabilité intestinale",
                "lab_names": ["lbp", "lipopolysaccharide binding protein"],
            },
            # THYROÏDE
            "tsh": {
                "unit": "mUI/L",
                "optimal": (1.0, 2.5),
                "normal": (0.5, 4.5),
                "category": "Thyroïde",
                "lab_names": ["tsh", "thyroid stimulating hormone"],
            },
            "t3_libre": {
                "unit": "pg/mL",
                "optimal": (3.0, 4.5),
                "normal": (2.3, 5.0),
                "category": "Thyroïde",
                "lab_names": ["t3 libre", "free t3", "ft3"],
            },
            "t4_libre": {
                "unit": "ng/dL",
                "optimal": (1.0, 1.5),
                "normal": (0.8, 1.8),
                "category": "Thyroïde",
                "lab_names": ["t4 libre", "free t4", "ft4"],
            },
        }

    @staticmethod
    def get_nutrition_recommendations() -> Dict[str, Dict]:
        """Recommandations nutritionnelles par biomarqueur"""
        return {
            "cortisol_reveil": {
                "high": ["Réduire stress", "Phosphatidylsérine 300mg", "Ashwagandha 600mg", "Rhodiola"],
                "low": ["Vitamine C 1000mg", "Réglisse DGL", "DHEA (si DHEA bas)", "Augmenter sel rose"],
            },
            "dhea": {
                "high": ["Réduire supplémentation DHEA", "Évaluer axe hormonal"],
                "low": ["DHEA 25-50mg matin", "Zinc 30mg", "Magnésium 400mg", "Réduire stress chronique"],
            },
            "crp": {
                "high": ["Omega-3 2000mg", "Curcumine 1000mg", "Diète anti-inflammatoire", "Éliminer gluten/laitages", "Probiotiques"],
                "low": ["RAS - Inflammation contrôlée"],
            },
            "vitamine_d": {
                "high": ["Réduire supplémentation", "Vérifier calcium"],
                "low": ["Vitamine D3 4000-10000 UI/j", "Exposition soleil 15min/j", "K2-MK7 200mcg"],
            },
            "glycemie": {
                "high": ["Réduire glucides rapides", "Berbérine 500mg x3", "Chrome picolinate 200mcg", "Cannelle 2g/j", "Activité physique"],
                "low": ["Augmenter féculents complexes", "Collations fréquentes", "Vérifier hypoglycémies"],
            },
            "insuline": {
                "high": ["Jeûne intermittent 16/8", "Réduire glucides", "Berbérine 500mg x3", "Inositol 2000mg", "Activité HIIT"],
                "low": ["Augmenter féculents", "Chrome", "Magnésium"],
            },
            "cholesterol_total": {
                "high": ["Omega-3 2000mg", "Fibres solubles 30g/j", "Ail noir 1200mg", "Réduire graisses saturées", "Levure riz rouge"],
                "low": ["Augmenter graisses saines", "Huile coco", "Œufs bio"],
            },
            "hdl": {
                "high": ["RAS - Bon HDL"],
                "low": ["Omega-3 2000mg", "Activité aérobie", "Augmenter graisses mono-insaturées", "Niacine 500mg"],
            },
            "ldl": {
                "high": ["Omega-3", "Fibres solubles", "Phytostérols", "Ail noir", "Réduire graisses saturées"],
                "low": ["Augmenter graisses saines", "RAS si pas trop bas"],
            },
            "triglycerides": {
                "high": ["Réduire glucides", "Omega-3 2000-4000mg", "Arrêter alcool", "Berbérine 500mg x3"],
                "low": ["RAS - Bon contrôle"],
            },
            "ferritine": {
                "high": ["Donner sang", "Curcumine", "Thé vert", "Réduire viande rouge", "Vérifier hémochromatose"],
                "low": ["Fer bisglycinate 30mg + Vitamine C", "Viande rouge 3x/sem", "Vérifier B12/folates"],
            },
            "vitamine_b12": {
                "high": ["Réduire supplémentation"],
                "low": ["B12 méthylcobalamine 1000mcg", "Viande rouge", "Œufs", "Vérifier facteur intrinsèque"],
            },
            "magnesium": {
                "high": ["Réduire supplémentation", "Vérifier fonction rénale"],
                "low": ["Magnésium bisglycinate 400mg", "Légumes verts", "Noix", "Chocolat noir 85%"],
            },
            "zinc": {
                "high": ["Réduire supplémentation", "Vérifier cuivre"],
                "low": ["Zinc bisglycinate 30mg", "Huîtres", "Viande rouge", "Graines courge"],
            },
            "zonuline": {
                "high": ["Probiotiques multi-souches", "L-glutamine 5g x2", "Éliminer gluten", "Collagène marin", "Curcumine"],
                "low": ["RAS - Bonne perméabilité"],
            },
            "tsh": {
                "high": ["Sélénium 200mcg", "Iode Lugol (si carence)", "Zinc 30mg", "Réduire goitrogènes", "Vérifier anticorps"],
                "low": ["Vérifier T3/T4", "Évaluer hyperthyroïdie", "Arrêter suppléments iode"],
            },
        }


class AdvancedPDFExtractor:
    """Wrapper pour UniversalPDFExtractor avec fallback"""

    @staticmethod
    def extract_text(pdf_file) -> str:
        if UNIVERSAL_EXTRACTOR_AVAILABLE:
            extractor = UniversalPDFExtractor(pdf_file)
            return extractor.extract_text()
        return ""

    @staticmethod
    def extract_biomarkers(text: str, debug: bool = False) -> Dict[str, float]:
        if UNIVERSAL_EXTRACTOR_AVAILABLE:
            extractor = UniversalPDFExtractor(None)
            return extractor.extract_biomarkers_universal(text, debug=debug)
        return {}

    @staticmethod
    def extract_patient_info(text: str) -> Dict[str, str]:
        if UNIVERSAL_EXTRACTOR_AVAILABLE:
            extractor = UniversalPDFExtractor(None)
            return extractor.extract_patient_info(text)
        return {}


class HealthScoreCalculator:
    """Calcul des scores de santé et âge biologique"""

    @staticmethod
    def calculate_health_score(biomarkers: Dict[str, float], age: int, sex: str) -> Dict:
        ref_ranges = BiomarkerDatabase.get_reference_ranges()
        total_score = 0
        max_score = 0
        category_scores = {}

        for marker, value in biomarkers.items():
            if marker in ref_ranges:
                ref = ref_ranges[marker]
                category = ref["category"]
                optimal = ref["optimal"]
                normal = ref["normal"]

                if optimal[0] <= value <= optimal[1]:
                    score = 100
                elif normal[0] <= value <= normal[1]:
                    if value < optimal[0]:
                        score = 70 + 30 * (value - normal[0]) / (optimal[0] - normal[0])
                    else:
                        score = 70 + 30 * (normal[1] - value) / (normal[1] - optimal[1])
                else:
                    if value < normal[0]:
                        score = max(0, 70 * value / normal[0])
                    else:
                        excess = value - normal[1]
                        range_width = normal[1] - normal[0]
                        score = max(0, 70 - 70 * excess / range_width)

                total_score += score
                max_score += 100

                if category not in category_scores:
                    category_scores[category] = {"score": 0, "count": 0}
                category_scores[category]["score"] += score
                category_scores[category]["count"] += 1

        global_score = round(total_score / max_score * 100, 1) if max_score > 0 else 0

        for cat in category_scores:
            category_scores[cat]["score"] = round(
                category_scores[cat]["score"] / category_scores[cat]["count"], 1
            )

        grade = "A+" if global_score >= 95 else "A" if global_score >= 90 else "B+" if global_score >= 85 else "B" if global_score >= 80 else "C+" if global_score >= 75 else "C" if global_score >= 70 else "D+" if global_score >= 65 else "D" if global_score >= 60 else "E"

        return {
            "global_score": global_score,
            "grade": grade,
            "category_scores": category_scores,
            "total_markers": len(biomarkers),
        }

    @staticmethod
    def calculate_biological_age(biomarkers: Dict[str, float], chronological_age: int, sex: str) -> Dict:
        ref_ranges = BiomarkerDatabase.get_reference_ranges()
        age_markers = ["crp", "cortisol_reveil", "dhea", "hba1c", "cholesterol_total", "vitamine_d"]

        aging_score = 0
        marker_count = 0

        for marker in age_markers:
            if marker in biomarkers and marker in ref_ranges:
                value = biomarkers[marker]
                optimal = ref_ranges[marker]["optimal"]

                if optimal[0] <= value <= optimal[1]:
                    deviation = 0
                elif value < optimal[0]:
                    deviation = (optimal[0] - value) / optimal[0]
                else:
                    deviation = (value - optimal[1]) / optimal[1]

                aging_score += deviation
                marker_count += 1

        if marker_count > 0:
            avg_deviation = aging_score / marker_count
            biological_age = round(chronological_age * (1 + avg_deviation * 0.3))
        else:
            biological_age = chronological_age

        delta = biological_age - chronological_age

        return {
            "biological_age": biological_age,
            "chronological_age": chronological_age,
            "delta": delta,
            "markers_used": marker_count,
        }

    @staticmethod
    def calculate_nutritional_needs(
        age: int, sex: str, weight: float, height: float, activity_level: str
    ) -> Dict:
        if sex == "Masculin":
            bmr = 10 * weight + 6.25 * height - 5 * age + 5
        else:
            bmr = 10 * weight + 6.25 * height - 5 * age - 161

        activity_multipliers = {
            "sedentary": 1.2,
            "light": 1.375,
            "moderate": 1.55,
            "active": 1.725,
            "very_active": 1.9,
        }

        det = bmr * activity_multipliers.get(activity_level, 1.55)

        proteins_g = weight * 1.6
        lipids_g = det * 0.30 / 9
        carbs_g = (det - proteins_g * 4 - lipids_g * 9) / 4

        return {
            "bmr": round(bmr, 0),
            "det": round(det, 0),
            "proteins_g": round(proteins_g, 0),
            "lipids_g": round(lipids_g, 0),
            "carbs_g": round(carbs_g, 0),
        }


class RecommendationEngine:
    """Génération de recommandations personnalisées"""

    @staticmethod
    def generate_personalized_recommendations(
        biomarkers: Dict[str, float],
        age: int,
        sex: str,
        health_score: Dict,
        biological_age_data: Dict,
    ) -> Dict:
        ref_ranges = BiomarkerDatabase.get_reference_ranges()
        nutrition_reco = BiomarkerDatabase.get_nutrition_recommendations()

        priorities = []
        supplements_set = set()
        alimentation_set = set()
        lifestyle_set = set()

        for marker, value in biomarkers.items():
            if marker not in ref_ranges:
                continue

            ref = ref_ranges[marker]
            optimal = ref["optimal"]
            normal = ref["normal"]

            status = "optimal"
            priority_level = "Normal"

            if value < normal[0]:
                status = "bas"
                priority_level = "Élevé" if value < optimal[0] * 0.7 else "Modéré"
            elif value > normal[1]:
                status = "élevé"
                priority_level = "Élevé" if value > optimal[1] * 1.3 else "Modéré"
            elif not (optimal[0] <= value <= optimal[1]):
                status = "à surveiller"
                priority_level = "Faible"

            if status != "optimal":
                priorities.append({
                    "biomarker": marker,
                    "value": value,
                    "status": status,
                    "priority": priority_level,
                })

                if marker in nutrition_reco:
                    reco_type = "high" if status == "élevé" else "low"
                    if reco_type in nutrition_reco[marker]:
                        for r in nutrition_reco[marker][reco_type]:
                            if "mg" in r or "UI" in r or "mcg" in r or "g/j" in r:
                                supplements_set.add(r)
                            elif any(food in r.lower() for food in ["réduire", "augmenter", "diète", "éliminer"]):
                                alimentation_set.add(r)
                            else:
                                lifestyle_set.add(r)

        priorities.sort(key=lambda x: {"Élevé": 3, "Modéré": 2, "Faible": 1}[x["priority"]], reverse=True)

        return {
            "priorities": priorities,
            "recommendations": {
                "supplements": sorted(list(supplements_set)),
                "alimentation": sorted(list(alimentation_set)),
                "lifestyle": sorted(list(lifestyle_set)),
            },
        }


# ============================================================================
# SESSION STATE
# ============================================================================

if "extracted_data" not in st.session_state:
    st.session_state.extracted_data = {
        "biological": {},
        "epigenetic": {},
        "imaging": {},
        "microbiome": {},  # ✅ AJOUT MICROBIOTE
        "patient_info": {},
    }

if "patient_data" not in st.session_state:
    st.session_state.patient_data = {
        "patient_info": {},
        "biological_markers": {},
        "epigenetic_data": {},
        "imaging_data": {},
        "microbiome_data": {},  # ✅ AJOUT MICROBIOTE
    }

if "analysis_complete" not in st.session_state:
    st.session_state.analysis_complete = False
if "health_score" not in st.session_state:
    st.session_state.health_score = None
if "biological_age" not in st.session_state:
    st.session_state.biological_age = None
if "recommendations" not in st.session_state:
    st.session_state.recommendations = None
if "nutritional_needs" not in st.session_state:
    st.session_state.nutritional_needs = None
if "engine_results" not in st.session_state:
    st.session_state.engine_results = None


# ============================================================================
# HEADER
# ============================================================================

st.markdown('<h1 class="main-title">🧬 ALGO-LIFE</h1>', unsafe_allow_html=True)
st.markdown(
    '<p class="sub-title">Plateforme Multimodale d\'Analyse de Santé Fonctionnelle</p>',
    unsafe_allow_html=True,
)

st.divider()


# ============================================================================
# SIDEBAR
# ============================================================================

with st.sidebar:
    st.header("📋 Informations Patient")

    if not UNIVERSAL_EXTRACTOR_AVAILABLE:
        st.error("❌ UniversalPDFExtractor indisponible (import failed).")
        st.code(_UNIVERSAL_IMPORT_ERROR, language="text")

    if st.button("🧹 Reset (cache + rerun)", use_container_width=True):
        try:
            st.cache_data.clear()
            st.cache_resource.clear()
        except Exception:
            pass
        st.session_state.analysis_complete = False
        st.session_state.health_score = None
        st.session_state.biological_age = None
        st.session_state.recommendations = None
        st.session_state.nutritional_needs = None
        st.session_state.engine_results = None
        st.rerun()

    default_name = st.session_state.extracted_data["patient_info"].get("nom", "Patient")
    default_age = int(st.session_state.extracted_data["patient_info"].get("age", 45))
    default_sex_index = 1 if st.session_state.extracted_data["patient_info"].get("sexe") == "Féminin" else 0

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

    imc = patient_weight / ((patient_height / 100) ** 2)
    st.metric("IMC", f"{imc:.1f}", help="Indice de Masse Corporelle")

    activity_level = st.selectbox(
        "Niveau d'activité",
        ["sedentary", "light", "moderate", "active", "very_active"],
        index=2,
        format_func=lambda x: {
            "sedentary": "Sédentaire",
            "light": "Léger",
            "moderate": "Modéré",
            "active": "Actif",
            "very_active": "Très actif",
        }[x],
        key="activity_input",
    )

    st.divider()

    default_date = datetime.now()
    if "prelevement_date" in st.session_state.extracted_data["patient_info"]:
        try:
            date_str = st.session_state.extracted_data["patient_info"]["prelevement_date"]
            default_date = datetime.strptime(date_str.replace(".", "/").replace("-", "/"), "%d/%m/%Y")
        except Exception:
            pass

    prelevement_date = st.date_input("Date du prélèvement", value=default_date, key="date_input")

    st.divider()

    if st.button("💾 Sauvegarder Informations", type="primary", use_container_width=True):
        st.session_state.patient_data["patient_info"] = {
            "nom": patient_name,
            "age": int(patient_age),
            "sexe": patient_sex,
            "height": float(patient_height),
            "weight": float(patient_weight),
            "imc": round(float(imc), 1),
            "activity_level": activity_level,
            "prelevement_date": prelevement_date.strftime("%Y-%m-%d"),
        }
        st.success("✅ Sauvegardé!")
        st.rerun()


# ============================================================================
# TABS
# ============================================================================

tab1, tab2, tab3, tab4 = st.tabs(["📤 Import & Extraction", "📊 Analyse & Scores", "📄 Rapport Professionnel", "ℹ️ Documentation"])


# ============================================================================
# TAB 1 - IMPORT
# ============================================================================

with tab1:
    st.header("📤 Import Automatique des Résultats PDF")

    st.markdown(
        """
<div class="alert-info">
<h4>🎯 Instructions d'Import</h4>
<p>Téléchargez vos fichiers PDF de résultats médicaux. Le système extraira automatiquement:</p>
<ul>
<li>✅ <strong>Biologie</strong>: Hormones, métabolisme, inflammation, antioxydants</li>
<li>✅ <strong>Épigénétique</strong>: Âge biologique, méthylation, télomères</li>
<li>✅ <strong>Imagerie</strong>: DXA, composition corporelle, densité osseuse</li>
<li>✅ <strong>Microbiote</strong>: Analyse du microbiome intestinal</li>
</ul>
<p><strong>Formats supportés:</strong> Tous les PDF médicaux standards (SYNLAB, LIMS, laboratoires européens)</p>
</div>
""",
        unsafe_allow_html=True,
    )

    st.divider()

    # ✅ MODIFICATION: 4 colonnes au lieu de 3
    col_upload1, col_upload2, col_upload3, col_upload4 = st.columns(4)

    # --- Biologie
    with col_upload1:
        st.subheader("🧪 PDF Biologie")
        bio_pdf = st.file_uploader(
            "Analyses biologiques",
            type=["pdf"],
            key="bio_pdf_upload",
            help="Hormones, métabolisme, inflammation...",
        )

        if bio_pdf:
            debug_bio = st.checkbox("🐛 Mode Debug", key="debug_bio_check")

            if st.button("🔍 Extraire", key="extract_bio_btn", use_container_width=True):
                if not UNIVERSAL_EXTRACTOR_AVAILABLE:
                    st.error("❌ UniversalPDFExtractor indisponible. Vérifie le fichier advanced_pdf_extractor_universal.py")
                else:
                    with st.spinner("Extraction en cours..."):
                        text = AdvancedPDFExtractor.extract_text(bio_pdf)
                        biomarkers = AdvancedPDFExtractor.extract_biomarkers(text, debug=debug_bio)
                        patient_info = AdvancedPDFExtractor.extract_patient_info(text)

                        if biomarkers:
                            st.session_state.extracted_data["biological"] = biomarkers
                            st.session_state.extracted_data["patient_info"].update(patient_info)
                            st.session_state.patient_data["biological_markers"].update(biomarkers)

                            st.success(f"✅ **{len(biomarkers)} biomarqueurs extraits!**")

                            known_db = BiomarkerDatabase.get_reference_ranges()
                            known_count = sum(1 for k in biomarkers.keys() if k in known_db)
                            new_count = len(biomarkers) - known_count

                            c1, c2, c3 = st.columns(3)
                            c1.metric("📊 Total Extrait", len(biomarkers))
                            c2.metric("⭐ Connus (avec ranges)", known_count)
                            c3.metric("🆕 Nouveaux Détectés", new_count)

                            if patient_info:
                                st.info(f"ℹ️ Informations patient extraites: {', '.join(patient_info.keys())}")

                            with st.expander("📋 Données extraites", expanded=True):
                                df_bio = (
                                    pd.DataFrame(
                                        [
                                            {
                                                "Biomarqueur": k.replace("_", " ").title(),
                                                "Valeur": v,
                                                "Type": "⭐ Connu" if k in known_db else "🆕 Nouveau",
                                            }
                                            for k, v in biomarkers.items()
                                        ]
                                    )
                                    .sort_values("Type", ascending=False)
                                )
                                st.dataframe(df_bio, use_container_width=True, hide_index=True)
                        else:
                            st.warning("⚠️ Aucune donnée extraite. Essayez le mode Debug.")

    # --- Epigénétique (simple regex)
    with col_upload2:
        st.subheader("🧬 PDF Épigénétique")
        epi_pdf = st.file_uploader(
            "Analyses épigénétiques",
            type=["pdf"],
            key="epi_pdf_upload",
            help="Âge biologique, méthylation, télomères...",
        )

        if epi_pdf:
            if st.button("🔍 Extraire", key="extract_epi_btn", use_container_width=True):
                if not UNIVERSAL_EXTRACTOR_AVAILABLE:
                    st.error("❌ UniversalPDFExtractor indisponible. (utilisé pour extraire le texte)")
                else:
                    with st.spinner("Extraction en cours..."):
                        text = AdvancedPDFExtractor.extract_text(epi_pdf)
                        epi_data: Dict[str, float] = {}

                        patterns_epi = {
                            "biological_age": r"[âa]ge\s+biologique[:\s]+(\d+\.?\d*)",
                            "telomere_length": r"t[ée]lom[èe]re.*?(\d+\.?\d*)",
                            "methylation_score": r"m[ée]thylation.*?(\d+\.?\d*)",
                        }

                        text_lower = text.lower()
                        for key, pattern in patterns_epi.items():
                            match = re.search(pattern, text_lower, re.IGNORECASE)
                            if match:
                                try:
                                    epi_data[key] = float(match.group(1))
                                except Exception:
                                    pass

                        if epi_data:
                            st.session_state.extracted_data["epigenetic"] = epi_data
                            st.session_state.patient_data["epigenetic_data"].update(epi_data)
                            st.success(f"✅ **{len(epi_data)} paramètres extraits!**")
                            with st.expander("📋 Données extraites"):
                                st.json(epi_data)
                        else:
                            st.warning("⚠️ Aucune donnée épigénétique trouvée.")

    # --- Imagerie (simple regex)
    with col_upload3:
        st.subheader("🏥 PDF Imagerie")
        img_pdf = st.file_uploader(
            "Analyses DXA",
            type=["pdf"],
            key="img_pdf_upload",
            help="Composition corporelle, densité osseuse...",
        )

        if img_pdf:
            if st.button("🔍 Extraire", key="extract_img_btn", use_container_width=True):
                if not UNIVERSAL_EXTRACTOR_AVAILABLE:
                    st.error("❌ UniversalPDFExtractor indisponible. (utilisé pour extraire le texte)")
                else:
                    with st.spinner("Extraction en cours..."):
                        text = AdvancedPDFExtractor.extract_text(img_pdf)

                        img_data: Dict[str, float] = {}
                        patterns_img = {
                            "body_fat_percentage": r"masse\s+grasse.*?(\d+\.?\d*)\s*%",
                            "lean_mass": r"masse\s+maigre.*?(\d+\.?\d*)",
                            "bone_density": r"densit[ée].*osseuse.*?(\d+\.?\d*)",
                            "visceral_fat": r"graisse\s+visc[ée]rale.*?(\d+\.?\d*)",
                        }

                        text_lower = text.lower()
                        for key, pattern in patterns_img.items():
                            match = re.search(pattern, text_lower, re.IGNORECASE)
                            if match:
                                try:
                                    img_data[key] = float(match.group(1))
                                except Exception:
                                    pass

                        if img_data:
                            st.session_state.extracted_data["imaging"] = img_data
                            st.session_state.patient_data["imaging_data"].update(img_data)
                            st.success(f"✅ **{len(img_data)} paramètres extraits!**")
                            with st.expander("📋 Données extraites"):
                                st.json(img_data)
                        else:
                            st.warning("⚠️ Aucune donnée d'imagerie trouvée.")

    # ✅ NOUVEAU: Colonne Microbiote
    with col_upload4:
        st.subheader("🦠 PDF Microbiote")
        microbiome_pdf = st.file_uploader(
            "Analyses du microbiote",
            type=["pdf"],
            key="microbiome_pdf_upload",
            help="Analyse du microbiome intestinal, diversité, pathogènes...",
        )

        if microbiome_pdf:
            if st.button("🔍 Extraire", key="extract_microbiome_btn", use_container_width=True):
                if not UNIVERSAL_EXTRACTOR_AVAILABLE:
                    st.error("❌ UniversalPDFExtractor indisponible. (utilisé pour extraire le texte)")
                else:
                    with st.spinner("Extraction en cours..."):
                        text = AdvancedPDFExtractor.extract_text(microbiome_pdf)

                        microbiome_data: Dict[str, float] = {}
                        
                        # Patterns pour extraire les données microbiote
                        patterns_microbiome = {
                            "shannon_index": r"shannon[:\s]+(\d+\.?\d*)",
                            "simpson_index": r"simpson[:\s]+(\d+\.?\d*)",
                            "firmicutes_bacteroidetes_ratio": r"f[\/]b.*?ratio[:\s]+(\d+\.?\d*)",
                            "dysbiosis_index": r"dysbiose.*?index[:\s]+(\d+\.?\d*)",
                            "lactobacillus": r"lactobacill.*?(\d+\.?\d*)",
                            "bifidobacterium": r"bifidobact.*?(\d+\.?\d*)",
                            "escherichia_coli": r"escherichia.*coli.*?(\d+\.?\d*)",
                            "akkermansia": r"akkermansia.*?(\d+\.?\d*)",
                            "faecalibacterium": r"faecalibacterium.*?(\d+\.?\d*)",
                        }

                        text_lower = text.lower()
                        for key, pattern in patterns_microbiome.items():
                            match = re.search(pattern, text_lower, re.IGNORECASE)
                            if match:
                                try:
                                    microbiome_data[key] = float(match.group(1))
                                except Exception:
                                    pass

                        if microbiome_data:
                            st.session_state.extracted_data["microbiome"] = microbiome_data
                            st.session_state.patient_data["microbiome_data"].update(microbiome_data)
                            st.success(f"✅ **{len(microbiome_data)} paramètres microbiote extraits!**")
                            with st.expander("📋 Données extraites"):
                                st.json(microbiome_data)
                        else:
                            st.warning("⚠️ Aucune donnée de microbiote trouvée.")

    st.divider()

    st.subheader("📊 Récapitulatif des Données Extraites")
    total_bio = len(st.session_state.extracted_data["biological"])
    total_epi = len(st.session_state.extracted_data["epigenetic"])
    total_img = len(st.session_state.extracted_data["imaging"])
    total_microbiome = len(st.session_state.extracted_data["microbiome"])  # ✅ AJOUT
    total = total_bio + total_epi + total_img + total_microbiome  # ✅ AJOUT

    # ✅ MODIFICATION: 5 colonnes au lieu de 4
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("🧪 Biomarqueurs Bio", total_bio)
    c2.metric("🧬 Paramètres Épi", total_epi)
    c3.metric("🏥 Données Imagerie", total_img)
    c4.metric("🦠 Données Microbiote", total_microbiome)  # ✅ NOUVEAU
    c5.metric("📈 Total", total)

    if total > 0:
        st.markdown(
            f"""
        <div class="alert-success">
        <h4>✅ {total} paramètres disponibles pour l'analyse!</h4>
        <p>Cliquez sur le bouton ci-dessous pour lancer l'analyse complète.</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

        if st.button("🚀 LANCER L'ANALYSE COMPLÈTE", type="primary", use_container_width=True, key="launch_full_analysis"):
            with st.spinner("🔬 Analyse en cours..."):
                try:
                    patient_info = st.session_state.patient_data["patient_info"]
                    biomarkers = st.session_state.patient_data["biological_markers"]

                    if not patient_info or not biomarkers:
                        st.error("❌ Veuillez d'abord enregistrer les informations patient et extraire les biomarqueurs.")
                    else:
                        biological_age_data = HealthScoreCalculator.calculate_biological_age(
                            biomarkers=biomarkers,
                            chronological_age=int(patient_info["age"]),
                            sex=str(patient_info["sexe"]),
                        )
                        st.session_state.biological_age = biological_age_data

                        health_score_data = HealthScoreCalculator.calculate_health_score(
                            biomarkers=biomarkers,
                            age=int(patient_info["age"]),
                            sex=str(patient_info["sexe"]),
                        )
                        st.session_state.health_score = health_score_data

                        nutritional_needs = HealthScoreCalculator.calculate_nutritional_needs(
                            age=int(patient_info["age"]),
                            sex=str(patient_info["sexe"]),
                            weight=float(patient_info["weight"]),
                            height=float(patient_info["height"]),
                            activity_level=str(patient_info.get("activity_level", "moderate")),
                        )
                        st.session_state.nutritional_needs = nutritional_needs

                        recommendations_data = RecommendationEngine.generate_personalized_recommendations(
                            biomarkers=biomarkers,
                            age=int(patient_info["age"]),
                            sex=str(patient_info["sexe"]),
                            health_score=health_score_data,
                            biological_age_data=biological_age_data,
                        )
                        st.session_state.recommendations = recommendations_data

                        # Engine (optional)
                        try:
                            engine = AlgoLifeEngine()
                            dxa_data = st.session_state.patient_data.get("imaging_data", {})

                            bio_data_engine = {
                                "hormones_salivaires": {
                                    "cortisol_reveil": biomarkers.get("cortisol_reveil"),
                                    "cortisol_reveil_30": biomarkers.get("cortisol_car_30"),
                                    "cortisol_12h": biomarkers.get("cortisol_12h"),
                                    "cortisol_18h": biomarkers.get("cortisol_18h"),
                                    "cortisol_22h": biomarkers.get("cortisol_22h"),
                                    "dhea": biomarkers.get("dhea"),
                                },
                                "inflammation": {"crp_us": biomarkers.get("crp")},
                                "metabolisme_glucidique": {
                                    "homa": biomarkers.get("homa_index"),
                                    "quicki": biomarkers.get("quicki_index"),
                                    "glycemie": biomarkers.get("glycemie"),
                                    "insuline": biomarkers.get("insuline"),
                                },
                                "permeabilite_intestinale": {"zonuline": biomarkers.get("zonuline"), "lbp": biomarkers.get("lbp")},
                                "micronutriments": {
                                    "vitamine_d": biomarkers.get("vitamine_d"),
                                    "vitamine_b12": biomarkers.get("vitamine_b12"),
                                    "magnesium": biomarkers.get("magnesium"),
                                },
                            }

                            engine_results = engine.analyze(
                                biological_data=bio_data_engine,
                                patient_age=int(patient_info["age"]),
                                patient_sex=str(patient_info["sexe"]),
                                dxa_data=dxa_data,
                            )
                            st.session_state.engine_results = engine_results
                        except Exception:
                            st.session_state.engine_results = None

                        st.session_state.analysis_complete = True
                        st.success("✅ Analyse complète terminée!")
                        st.balloons()
                        st.rerun()

                except Exception as e:
                    st.error(f"❌ Erreur lors de l'analyse: {str(e)}")
                    import traceback
                    with st.expander("Détails de l'erreur"):
                        st.code(traceback.format_exc())


# ============================================================================
# TAB 2 - ANALYSE
# ============================================================================

with tab2:
    st.header("📊 Analyse Complète & Scores de Santé")

    if not st.session_state.analysis_complete:
        st.info("📥 Veuillez d'abord effectuer une analyse complète depuis l'onglet 'Import & Extraction'")
    else:
        st.markdown(
            """
        <div class="alert-success">
        <h4>✅ Analyse Complète Disponible</h4>
        <p>Résultats détaillés ci-dessous.</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

        st.divider()

        health_score = st.session_state.health_score
        biological_age = st.session_state.biological_age

        col_main1, col_main2, col_main3 = st.columns(3)

        with col_main1:
            score = health_score["global_score"]
            grade = health_score["grade"]
            score_class = (
                "score-excellent"
                if score >= 90
                else "score-good"
                if score >= 75
                else "score-moderate"
                if score >= 60
                else "score-poor"
            )
            st.markdown(
                f"""
            <div class="metric-card">
            <h3>🎯 Score de Santé Global</h3>
            <div class="{score_class}">{score}/100</div>
            <p style="font-size:1.2rem; margin-top:0.5rem;">Grade: <strong>{grade}</strong></p>
            </div>
            """,
                unsafe_allow_html=True,
            )

        with col_main2:
            bio_age = biological_age["biological_age"]
            chrono_age = biological_age["chronological_age"]
            delta = biological_age["delta"]
            delta_sign = "+" if delta > 0 else ""
            delta_color = "#ef4444" if delta > 0 else "#10b981"
            st.markdown(
                f"""
            <div class="metric-card">
            <h3>🧬 Âge Biologique</h3>
            <div style="font-size:2.5rem; font-weight:700; color:#667eea;">{bio_age} ans</div>
            <p style="font-size:1.1rem; margin-top:0.5rem;">
            Âge chronologique: {chrono_age} ans<br>
            <span style="color:{delta_color}; font-weight:600;">Delta: {delta_sign}{delta} ans</span>
            </p>
            </div>
            """,
                unsafe_allow_html=True,
            )

        with col_main3:
            total_markers = health_score["total_markers"]
            st.markdown(
                f"""
            <div class="metric-card">
            <h3>📊 Biomarqueurs Analysés</h3>
            <div style="font-size:2.5rem; font-weight:700; color:#667eea;">{total_markers}</div>
            <p style="font-size:1.1rem; margin-top:0.5rem;">Marqueurs biologiques évalués</p>
            </div>
            """,
                unsafe_allow_html=True,
            )

        st.divider()

        st.subheader("📈 Scores par Catégorie")
        category_scores = health_score["category_scores"]

        if category_scores:
            cat_cols = st.columns(len(category_scores))
            for idx, (category, data) in enumerate(category_scores.items()):
                cat_score = data["score"]
                cat_count = data["count"]
                with cat_cols[idx]:
                    st.metric(
                        label=category,
                        value=f"{cat_score:.1f}/100",
                        help=f"{cat_count} biomarqueurs dans cette catégorie",
                    )
        else:
            st.info("Aucune donnée de catégorie disponible.")

        st.divider()

        st.subheader("🔬 Classification des Biomarqueurs")
        biomarkers_all = st.session_state.patient_data["biological_markers"]
        ref_ranges = BiomarkerDatabase.get_reference_ranges()

        classified = {
            "normaux": [],
            "a_surveiller": [],
            "anormaux": [],
            "non_references": [],
        }

        for marker, value in biomarkers_all.items():
            marker_display = marker.replace("_", " ").title()

            if marker not in ref_ranges:
                classified["non_references"].append({
                    "Biomarqueur": marker_display,
                    "Valeur": value,
                    "Statut": "Non référencé",
                })
                continue

            ref = ref_ranges[marker]
            optimal = ref["optimal"]
            normal = ref["normal"]
            unit = ref.get("unit", "")
            category = ref.get("category", "N/A")

            if optimal[0] <= value <= optimal[1]:
                status = "✅ Optimal"
                classified["normaux"].append({
                    "Biomarqueur": marker_display,
                    "Valeur": f"{value} {unit}",
                    "Optimal": f"{optimal[0]}-{optimal[1]} {unit}",
                    "Catégorie": category,
                    "Statut": status,
                })
            elif normal[0] <= value <= normal[1]:
                status = "⚡ À surveiller"
                classified["a_surveiller"].append({
                    "Biomarqueur": marker_display,
                    "Valeur": f"{value} {unit}",
                    "Normal": f"{normal[0]}-{normal[1]} {unit}",
                    "Optimal": f"{optimal[0]}-{optimal[1]} {unit}",
                    "Catégorie": category,
                    "Statut": status,
                })
            else:
                if value < normal[0]:
                    status = "⬇️ Trop bas"
                else:
                    status = "⬆️ Trop élevé"
                classified["anormaux"].append({
                    "Biomarqueur": marker_display,
                    "Valeur": f"{value} {unit}",
                    "Normal": f"{normal[0]}-{normal[1]} {unit}",
                    "Optimal": f"{optimal[0]}-{optimal[1]} {unit}",
                    "Catégorie": category,
                    "Statut": status,
                })

        with st.expander("✅ Biomarqueurs Normaux", expanded=False):
            if classified["normaux"]:
                st.dataframe(pd.DataFrame(classified["normaux"]), use_container_width=True, hide_index=True)
            else:
                st.info("Aucun biomarqueur normal.")

        with st.expander("⚡ Biomarqueurs À Surveiller", expanded=True):
            if classified["a_surveiller"]:
                st.dataframe(pd.DataFrame(classified["a_surveiller"]), use_container_width=True, hide_index=True)
            else:
                st.success("Aucun biomarqueur à surveiller.")

        with st.expander("⚠️ Biomarqueurs Anormaux", expanded=True):
            if classified["anormaux"]:
                st.dataframe(pd.DataFrame(classified["anormaux"]), use_container_width=True, hide_index=True)
            else:
                st.success("Aucun biomarqueur anormal.")

        with st.expander("❓ Biomarqueurs Non Référencés (nouveaux détectés)", expanded=False):
            if classified["non_references"]:
                st.info(
                    f"Ces {len(classified['non_references'])} biomarqueurs ont été extraits du PDF mais n'ont pas encore de plages de référence dans la base ALGO-LIFE."
                )
                st.dataframe(pd.DataFrame(classified["non_references"]), use_container_width=True, hide_index=True)
            else:
                st.success("Tous les biomarqueurs extraits sont référencés!")

        st.divider()

        st.subheader("🍽️ Besoins Nutritionnels Calculés")
        nutritional_needs = st.session_state.nutritional_needs

        n1, n2, n3, n4, n5 = st.columns(5)
        n1.metric("BMR", f"{nutritional_needs['bmr']:.0f} kcal", help="Métabolisme de base")
        n2.metric("DET", f"{nutritional_needs['det']:.0f} kcal", help="Dépense énergétique totale")
        n3.metric("Protéines", f"{nutritional_needs['proteins_g']:.0f} g", help="Besoin quotidien")
        n4.metric("Lipides", f"{nutritional_needs['lipids_g']:.0f} g", help="Besoin quotidien")
        n5.metric("Glucides", f"{nutritional_needs['carbs_g']:.0f} g", help="Besoin quotidien")

        st.divider()

        st.subheader("💡 Recommandations Personnalisées")
        recommendations = st.session_state.recommendations

        if recommendations and recommendations.get("priorities"):
            st.markdown("#### ⚠️ Priorités d'Action")
            for i, priority in enumerate(recommendations["priorities"][:5], 1):
                biomarker_name = priority["biomarker"].replace("_", " ").title()
                value = priority["value"]
                status = priority["status"]
                priority_level = priority["priority"]
                alert_class = "alert-danger" if priority_level == "Élevé" else "alert-warning"
                st.markdown(
                    f"""
                <div class="{alert_class}">
                    <strong>#{i} - {biomarker_name}</strong> ({priority_level})
                    <br>Valeur: {value} - Status: {status}
                </div>
                """,
                    unsafe_allow_html=True,
                )

        st.markdown("#### 📋 Recommandations Détaillées")
        tabs_reco = st.tabs(["💊 Suppléments", "🥗 Alimentation", "🏃 Lifestyle"])

        with tabs_reco[0]:
            supps = (recommendations or {}).get("recommendations", {}).get("supplements", [])
            if supps:
                for s in supps:
                    st.markdown(f"- {s}")
            else:
                st.info("Aucune supplémentation spécifique recommandée.")

        with tabs_reco[1]:
            alims = (recommendations or {}).get("recommendations", {}).get("alimentation", [])
            if alims:
                for a in alims:
                    st.markdown(f"- {a}")
            else:
                st.info("Aucune recommandation alimentaire spécifique.")

        with tabs_reco[2]:
            lifes = (recommendations or {}).get("recommendations", {}).get("lifestyle", [])
            if lifes:
                for l in lifes:
                    st.markdown(f"- {l}")
            else:
                st.info("Aucune recommandation lifestyle spécifique.")


# ============================================================================
# TAB 3 - PDF
# ============================================================================

with tab3:
    st.header("📄 Génération du Rapport Professionnel")

    if not st.session_state.analysis_complete:
        st.info("📥 Veuillez d'abord effectuer une analyse complète depuis l'onglet 'Import & Extraction'")
    else:
        st.markdown(
            """
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
        """,
            unsafe_allow_html=True,
        )

        if st.button("📥 GÉNÉRER LE RAPPORT PDF", type="primary", use_container_width=True, key="generate_pdf_btn"):
            with st.spinner("📄 Génération du rapport en cours..."):
                try:
                    pdf_buffer = generate_algolife_pdf_report(
                        patient_data=st.session_state.patient_data,
                        biomarker_results=st.session_state.patient_data["biological_markers"],
                        health_score=st.session_state.health_score,
                        biological_age=st.session_state.biological_age,
                        nutritional_needs=st.session_state.nutritional_needs,
                        recommendations=st.session_state.recommendations,
                        engine_results=st.session_state.engine_results,
                        chart_buffer=None,
                    )

                    st.success("✅ Rapport PDF généré avec succès!")

                    patient_name = st.session_state.patient_data["patient_info"].get("nom", "Patient")
                    filename = f"ALGO-LIFE_{patient_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf"

                    st.download_button(
                        label="📥 TÉLÉCHARGER LE RAPPORT PDF",
                        data=pdf_buffer.getvalue(),
                        file_name=filename,
                        mime="application/pdf",
                        type="primary",
                        use_container_width=True,
                    )
                    st.balloons()

                except Exception as e:
                    st.error(f"❌ Erreur lors de la génération du PDF: {str(e)}")
                    import traceback
                    with st.expander("Détails de l'erreur"):
                        st.code(traceback.format_exc())


# ============================================================================
# TAB 4 - DOC
# ============================================================================

with tab4:
    st.header("ℹ️ Documentation ALGO-LIFE")

    st.markdown(
        f"""
### 🎯 Vue d'Ensemble

**ALGO-LIFE** est une plateforme multimodale d'analyse de santé fonctionnelle qui intègre:
- **Biologie fonctionnelle**: Hormones, métabolisme, inflammation, neurotransmetteurs
- **Épigénétique**: Âge biologique, méthylation, télomères
- **Imagerie DXA**: Composition corporelle, densité osseuse
- **Microbiote**: Analyse du microbiome intestinal

### 📋 Workflow Complet

#### 1️⃣ Import des Données
- Téléchargez vos PDF de résultats médicaux
- Le système extrait automatiquement les biomarqueurs (MODE UNIVERSEL ✨)
- Complétez les informations patient
- Lancez l'analyse complète

#### 2️⃣ Analyse & Scores
- **Score Santé Global** (0-100) avec grade (A+ à D)
- **Âge Biologique** calculé (modèle fonctionnel)
- **Scores par Catégorie**
- **Classification**: Normaux / À surveiller / Anormaux / Non référencés
- **Besoins Nutritionnels**: BMR, DET, macronutriments

#### 3️⃣ Rapport Professionnel
- PDF complet, design pro
- Graphiques + recommandations
- Prêt consultation

### 📞 Support & Contact

**Développeur**: Dr Thibault SUTTER - Biologiste  
**Organisation**: ALGO-LIFE / Espace Lab SA (Unilabs Group)  
**Email**: contact@bilan-hormonal.com  
**Site**: https://bilan-hormonal.com  

**Version**: 4.1 - Janvier 2026 (Extraction Universelle + Microbiote)  
**Dernière mise à jour**: {datetime.now().strftime('%d/%m/%Y')}

### ⚖️ Disclaimer
ALGO-LIFE est un outil d'aide à la décision médicale. Les résultats et recommandations doivent être interprétés par un professionnel de santé qualifié. Ne remplace pas une consultation médicale.
"""
    )


# ============================================================================
# FOOTER
# ============================================================================

st.divider()
f1, f2, f3 = st.columns(3)
with f1:
    st.caption("© 2026 ALGO-LIFE")
    st.caption("Dr Thibault SUTTER - Biologiste")
with f2:
    st.caption("Espace Lab SA (Unilabs Group)")
    st.caption("Geneva, Switzerland")
with f3:
    st.caption("Version 4.1 - Janvier 2026")
    st.caption(f"Dernière exécution: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
