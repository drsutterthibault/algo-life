"""
ALGO-LIFE - Plateforme Multimodale d'Analyse de Santé Fonctionnelle
Version 4.1 - Janvier 2026 - EXTRACTION UNIVERSELLE

Intégration multimodale:
- Biologie fonctionnelle (hormones, métabolisme, inflammation, microbiote)
- Épigénétique (âge biologique, méthylation, télomères)
- Imagerie DXA (composition corporelle, densité osseuse)

Auteur: Dr Thibault SUTTER - Biologiste
Organisation: Laboratoire

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

# ✅ Microbiote Extractor (IDK GutMAP)
# ✅ Microbiome extractor (IDK GutMAP / PDF microbiote)
try:
    from microbiome_extractor_idk_gutmap import extract_microbiome_data  # type: ignore
    MICROBIOME_EXTRACTOR_AVAILABLE = True
except Exception as e:
    MICROBIOME_EXTRACTOR_AVAILABLE = False
    _MICROBIOME_IMPORT_ERROR = str(e)

    def extract_microbiome_data(*args, **kwargs):  # type: ignore
        """Fallback: returns empty dict if extractor module is unavailable."""
        return {}

# ----------------------------------------------------------------------------
# Fallback extractor (si advanced_pdf_extractor_universal absent sur Streamlit Cloud)
# ----------------------------------------------------------------------------
ADVANCED_UNIVERSAL_AVAILABLE = UNIVERSAL_EXTRACTOR_AVAILABLE

if not UNIVERSAL_EXTRACTOR_AVAILABLE:
    # NOTE: on garde l'app utilisable même si le module "advanced_pdf_extractor_universal.py"
    # n'est pas présent / pas importable sur Streamlit Cloud.
    if " _UNIVERSAL_IMPORT_ERROR" not in globals():
        _UNIVERSAL_IMPORT_ERROR = "unknown import error"

    class UniversalPDFExtractor:  # type: ignore
        """
        Fallback minimal compatible avec l'API utilisée dans app.py.
        - extract_text_from_pdf(pdf_file)
        - __init__(known_biomarkers=...)
        - extract_complete(text)
        - extract_microbiome_data(text)
        """
        def __init__(self, known_biomarkers: Dict[str, Dict] | None = None, *args, **kwargs):
            self.known_biomarkers = known_biomarkers or {}

        @staticmethod
        def extract_text_from_pdf(pdf_file) -> str:
            # pdf_file est un UploadedFile streamlit (BytesIO-like)
            data = pdf_file.read()
            # Important: remettre le curseur au début pour d'autres lectures
            try:
                pdf_file.seek(0)
            except Exception:
                pass

            text_out = ""

            if PDF_AVAILABLE:
                # 1) pdfplumber (meilleur sur tableaux)
                try:
                    import pdfplumber  # type: ignore
                    from io import BytesIO as _BytesIO
                    with pdfplumber.open(_BytesIO(data)) as pdf:
                        pages = []
                        for p in pdf.pages:
                            pages.append(p.extract_text() or "")
                        text_out = "\n".join(pages)
                    if text_out.strip():
                        return text_out
                except Exception:
                    pass

                # 2) PyPDF2 (fallback)
                try:
                    import PyPDF2  # type: ignore
                    from io import BytesIO as _BytesIO
                    reader = PyPDF2.PdfReader(_BytesIO(data))
                    pages = []
                    for page in reader.pages:
                        pages.append(page.extract_text() or "")
                    text_out = "\n".join(pages)
                    return text_out
                except Exception:
                    pass

            raise RuntimeError("Impossible d'extraire le texte: installe pdfplumber/PyPDF2 ou active l'extracteur universel.")

        def _parse_value_from_line(self, line: str) -> float | None:
            # Cherche un nombre (virgule ou point) éventuellement précédé de < ou >
            m = re.search(r'([<>]?\s*\d+(?:[\\.,]\\d+)?)', line)
            if not m:
                return None
            raw = m.group(1).replace(" ", "").replace(",", ".").replace("<", "").replace(">", "")
            try:
                return float(raw)
            except Exception:
                return None

        def extract_complete(self, text: str, debug: bool = False):
            """
            Retourne (known, all_biomarkers)
            Format attendu:
              known = {key: {"value": float, ...}, ...}
              all_biomarkers = idem (incluant nouveaux)
            Ici: extraction simple uniquement sur biomarqueurs connus.
            """
            known: Dict[str, Dict] = {}
            all_biomarkers: Dict[str, Dict] = {}

            lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
            # Accélération: text lower une fois
            for key, meta in self.known_biomarkers.items():
                lab_names = meta.get("lab_names", [])
                if not lab_names:
                    continue
                found_val = None
                for ln in lines:
                    lnl = ln.lower()
                    if any(name.lower() in lnl for name in lab_names):
                        val = self._parse_value_from_line(ln)
                        if val is not None:
                            found_val = val
                            break
                if found_val is not None:
                    known[key] = {"value": float(found_val)}
                    all_biomarkers[key] = {"value": float(found_val)}

            return known, all_biomarkers

        # Microbiote: non supporté en fallback (retourne dict vide)
        def extract_microbiome_data(self, text: str, debug: bool = False) -> Dict:
            return {}

    # On ré-active un "UNIVERSAL_EXTRACTOR_AVAILABLE" pour ne pas bloquer l'app
    UNIVERSAL_EXTRACTOR_AVAILABLE = True


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
        """Classifie un biomarqueur selon sa valeur (robuste + accepte non référencé)"""
        refs = BiomarkerDatabase.get_reference_ranges()

        if name not in refs:
            return {
                "status": "unknown",
                "interpretation": f"Biomarqueur détecté mais non référencé (valeur: {value})",
                "color": "gray",
                "icon": "❓",
                "value": value,
                "needs_reference": True,
            }

        ref = refs[name]

        # Gestion sexe-spécifique
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

        # Optimal
        if optimal[0] is not None and optimal[1] is not None and optimal[0] <= value <= optimal[1]:
            return {"status": "optimal", "interpretation": "Valeur optimale", "color": "green", "icon": "✅"}

        # Normal
        if normal[0] is not None and normal[1] is not None and normal[0] <= value <= normal[1]:
            return {"status": "normal", "interpretation": "Valeur normale", "color": "lightgreen", "icon": "✓"}

        # Seuils multiples
        if "elevated" in ref and ref["elevated"][0] is not None and value >= ref["elevated"][0]:
            if "high" in ref and ref["high"][0] is not None and value >= ref["high"][0]:
                return {"status": "high", "interpretation": "Valeur très élevée", "color": "red", "icon": "⚠️"}
            return {"status": "elevated", "interpretation": "Valeur modérément élevée", "color": "orange", "icon": "⚡"}

        if "deficiency" in ref and ref["deficiency"][1] is not None and value < ref["deficiency"][1]:
            return {"status": "deficient", "interpretation": "Carence", "color": "red", "icon": "⚠️"}

        if "insufficient" in ref and ref["insufficient"][0] is not None and ref["insufficient"][1] is not None:
            if ref["insufficient"][0] <= value < ref["insufficient"][1]:
                return {"status": "insufficient", "interpretation": "Insuffisance", "color": "orange", "icon": "⚡"}

        # Hors norme
        if normal[0] is not None and value < normal[0]:
            return {"status": "low", "interpretation": "Valeur basse", "color": "orange", "icon": "⬇️"}
        if normal[1] is not None and value > normal[1]:
            return {"status": "high", "interpretation": "Valeur élevée", "color": "red", "icon": "⬆️"}

        return {"status": "abnormal", "interpretation": "Valeur anormale", "color": "red", "icon": "❌"}


class AdvancedPDFExtractor:
    """Extracteur PDF universel (wrapper)"""

    @staticmethod
    def extract_text(pdf_file) -> str:
        if not UNIVERSAL_EXTRACTOR_AVAILABLE:
            raise RuntimeError(f"UniversalPDFExtractor indisponible: {_UNIVERSAL_IMPORT_ERROR}")
        return UniversalPDFExtractor.extract_text_from_pdf(pdf_file)

    @staticmethod
    def extract_biomarkers(text: str, debug: bool = False) -> Dict[str, float]:
        if not UNIVERSAL_EXTRACTOR_AVAILABLE:
            raise RuntimeError(f"UniversalPDFExtractor indisponible: {_UNIVERSAL_IMPORT_ERROR}")

        known_db = BiomarkerDatabase.get_reference_ranges()
        extractor = UniversalPDFExtractor(known_biomarkers=known_db)
        known, all_biomarkers = extractor.extract_complete(text, debug=debug)

        result: Dict[str, float] = {}
        for key, data in all_biomarkers.items():
            result[key] = data["value"]

        if debug:
            st.write(f"✅ EXTRACTION UNIVERSELLE: {len(result)} biomarqueurs")
            st.write(f"  - Connus (avec ranges): {len(known)}")
            st.write(f"  - Nouveaux détectés: {len(result) - len(known)}")

        return result

    @staticmethod
    def extract_patient_info(text: str) -> Dict:
        info: Dict[str, object] = {}
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
                    info["age"] = (datetime.now() - dob).days // 365
                except Exception:
                    pass
                break

        # Âge direct
        if "age" not in info:
            for pattern in [r"(\d{2})\s+ans", r"[âa]ge[:\s]+(\d{2})"]:
                match = re.search(pattern, text_lower)
                if match:
                    try:
                        info["age"] = int(match.group(1))
                    except Exception:
                        pass
                    break

        # Sexe
        for pattern in [r"sexe[:\s]+(m|f|h)", r"\((m|f|h)\)"]:
            match = re.search(pattern, text_lower)
            if match:
                sex_char = match.group(1).upper()
                info["sexe"] = "Masculin" if sex_char in ["M", "H"] else "Féminin"
                break

        # Date prélèvement
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
    """Calculateur avancé (âge biologique + score global + nutrition)"""

    @staticmethod
    def calculate_biological_age(biomarkers: Dict[str, float], chronological_age: int, sex: str) -> Dict:
        aging_factors = {
            "inflammation": 0,
            "oxidative_stress": 0,
            "metabolic_health": 0,
            "hormonal_balance": 0,
            "gut_health": 0,
            "cardiovascular": 0,
        }

        # Inflammation
        if "crp" in biomarkers and biomarkers["crp"] is not None:
            crp = float(biomarkers["crp"])
            if crp < 1:
                aging_factors["inflammation"] -= 2
            elif crp < 3:
                aging_factors["inflammation"] += 0
            elif crp < 10:
                aging_factors["inflammation"] += 3
            else:
                aging_factors["inflammation"] += 6

        if "homocysteine" in biomarkers and biomarkers["homocysteine"] is not None:
            hcy = float(biomarkers["homocysteine"])
            if hcy < 10:
                aging_factors["cardiovascular"] -= 1
            elif hcy < 15:
                aging_factors["cardiovascular"] += 0
            else:
                aging_factors["cardiovascular"] += 3

        # Oxydatif
        if "glutathion_total" in biomarkers and biomarkers["glutathion_total"] is not None:
            glut = float(biomarkers["glutathion_total"])
            if glut >= 1200:
                aging_factors["oxidative_stress"] -= 2
            elif glut >= 900:
                aging_factors["oxidative_stress"] += 0
            else:
                aging_factors["oxidative_stress"] += 3

        if "coenzyme_q10" in biomarkers and biomarkers["coenzyme_q10"] is not None:
            coq10 = float(biomarkers["coenzyme_q10"])
            aging_factors["oxidative_stress"] += (-1 if coq10 >= 670 else 2)

        # Métabolique
        if "homa_index" in biomarkers and biomarkers["homa_index"] is not None:
            homa = float(biomarkers["homa_index"])
            if homa < 1:
                aging_factors["metabolic_health"] -= 2
            elif homa < 2.4:
                aging_factors["metabolic_health"] += 0
            else:
                aging_factors["metabolic_health"] += 4

        if "glycemie" in biomarkers and biomarkers["glycemie"] is not None:
            gluc = float(biomarkers["glycemie"])
            if gluc < 0.95:
                aging_factors["metabolic_health"] -= 1
            elif gluc < 1.10:
                aging_factors["metabolic_health"] += 0
            else:
                aging_factors["metabolic_health"] += 3

        # Hormonal
        if "dhea" in biomarkers and biomarkers["dhea"] is not None:
            dhea = float(biomarkers["dhea"])
            optimal_dhea = 7 if sex == "Masculin" else 6
            ratio = dhea / optimal_dhea if optimal_dhea else 1
            if ratio >= 0.8:
                aging_factors["hormonal_balance"] -= 2
            elif ratio >= 0.5:
                aging_factors["hormonal_balance"] += 0
            else:
                aging_factors["hormonal_balance"] += 3

        # Intestin
        if "zonuline" in biomarkers and biomarkers["zonuline"] is not None:
            zon = float(biomarkers["zonuline"])
            if zon < 30:
                aging_factors["gut_health"] -= 1
            elif zon < 50:
                aging_factors["gut_health"] += 0
            else:
                aging_factors["gut_health"] += 3

        if "lbp" in biomarkers and biomarkers["lbp"] is not None:
            lbp = float(biomarkers["lbp"])
            aging_factors["gut_health"] += (-1 if lbp < 6.8 else 2)

        total_aging_score = sum(aging_factors.values())
        biological_age = chronological_age + (total_aging_score * 0.5)

        delta_age = biological_age - chronological_age
        delta_percent = (delta_age / chronological_age) * 100 if chronological_age else 0

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
            "biological_age": round(float(biological_age), 1),
            "chronological_age": int(chronological_age),
            "delta": round(float(delta_age), 1),
            "delta_percent": round(float(delta_percent), 1),
            "status": status,
            "interpretation": interpretation,
            "aging_factors": aging_factors,
        }

    @staticmethod
    def calculate_health_score(biomarkers: Dict[str, float], age: int, sex: str) -> Dict:
        category_scores = {
            "metabolism": 0,
            "inflammation": 0,
            "hormones": 0,
            "antioxidants": 0,
            "micronutrients": 0,
            "gut_health": 0,
            "cardiovascular": 0,
        }
        category_weights = {
            "metabolism": 20,
            "inflammation": 15,
            "hormones": 15,
            "antioxidants": 15,
            "micronutrients": 15,
            "gut_health": 10,
            "cardiovascular": 10,
        }

        # Métabolisme
        metab_score = 100
        if "homa_index" in biomarkers and biomarkers["homa_index"] is not None:
            homa = float(biomarkers["homa_index"])
            metab_score = 100 if homa < 1 else 80 if homa < 2.4 else 60 if homa < 4 else 30

        if "glycemie" in biomarkers and biomarkers["glycemie"] is not None:
            gluc = float(biomarkers["glycemie"])
            gluc_score = 100
            if gluc > 1.26:
                gluc_score = 30
            elif gluc > 1.10:
                gluc_score = 60
            elif gluc > 0.95:
                gluc_score = 80
            metab_score = (metab_score + gluc_score) / 2
        category_scores["metabolism"] = metab_score

        # Inflammation
        inflam_score = 100
        if "crp" in biomarkers and biomarkers["crp"] is not None:
            crp = float(biomarkers["crp"])
            inflam_score = 100 if crp < 1 else 85 if crp < 3 else 60 if crp < 10 else 30
        category_scores["inflammation"] = inflam_score

        # Hormones (cortisol + DHEA)
        hormone_score = 100
        cortisol_scores: List[float] = []
        for cort_key in ["cortisol_reveil", "cortisol_car_30", "cortisol_12h", "cortisol_18h", "cortisol_22h"]:
            if cort_key in biomarkers and biomarkers[cort_key] is not None:
                c = BiomarkerDatabase.classify_biomarker(cort_key, float(biomarkers[cort_key]), age, sex)
                cortisol_scores.append(100 if c["status"] == "optimal" else 80 if c["status"] == "normal" else 50)
        if cortisol_scores:
            hormone_score = float(np.mean(cortisol_scores))

        if "dhea" in biomarkers and biomarkers["dhea"] is not None:
            dhea_class = BiomarkerDatabase.classify_biomarker("dhea", float(biomarkers["dhea"]), age, sex)
            dhea_score = 100 if dhea_class["status"] == "optimal" else 80 if dhea_class["status"] == "normal" else 50
            hormone_score = (hormone_score + dhea_score) / 2
        category_scores["hormones"] = hormone_score

        # Antiox
        antiox_list: List[float] = []
        for k in ["glutathion_total", "coenzyme_q10", "gpx"]:
            if k in biomarkers and biomarkers[k] is not None:
                c = BiomarkerDatabase.classify_biomarker(k, float(biomarkers[k]), age, sex)
                antiox_list.append(100 if c["status"] == "optimal" else 80 if c["status"] == "normal" else 50)
        category_scores["antioxidants"] = float(np.mean(antiox_list)) if antiox_list else 100

        # Micro
        micro_list: List[float] = []
        for k in ["vit_d", "ferritine", "zinc", "selenium", "magnesium_erythrocytaire"]:
            if k in biomarkers and biomarkers[k] is not None:
                c = BiomarkerDatabase.classify_biomarker(k, float(biomarkers[k]), age, sex)
                if c["status"] in ["optimal", "normal"]:
                    micro_list.append(100)
                elif c["status"] in ["insufficient", "low", "elevated"]:
                    micro_list.append(60)
                else:
                    micro_list.append(30)
        category_scores["micronutrients"] = float(np.mean(micro_list)) if micro_list else 100

        # Gut
        gut_list: List[float] = []
        for k in ["zonuline", "lbp"]:
            if k in biomarkers and biomarkers[k] is not None:
                c = BiomarkerDatabase.classify_biomarker(k, float(biomarkers[k]), age, sex)
                gut_list.append(100 if c["status"] in ["optimal", "normal"] else 50)
        category_scores["gut_health"] = float(np.mean(gut_list)) if gut_list else 100

        # Cardio
        cardio_list: List[float] = []
        for k in ["homocysteine", "omega3_index", "aa_epa"]:
            if k in biomarkers and biomarkers[k] is not None:
                c = BiomarkerDatabase.classify_biomarker(k, float(biomarkers[k]), age, sex)
                cardio_list.append(100 if c["status"] in ["optimal", "normal"] else 50)
        category_scores["cardiovascular"] = float(np.mean(cardio_list)) if cardio_list else 100

        # Global pondéré
        total_score = 0.0
        total_weight = 0.0
        for category, score in category_scores.items():
            w = float(category_weights[category])
            total_score += float(score) * w
            total_weight += w
        global_score = (total_score / total_weight) if total_weight > 0 else 0

        if global_score >= 95:
            grade, grade_label = "A+", "Excellent"
        elif global_score >= 90:
            grade, grade_label = "A", "Très bon"
        elif global_score >= 85:
            grade, grade_label = "A-", "Très bon"
        elif global_score >= 80:
            grade, grade_label = "B+", "Bon"
        elif global_score >= 75:
            grade, grade_label = "B", "Bon"
        elif global_score >= 70:
            grade, grade_label = "B-", "Satisfaisant"
        elif global_score >= 65:
            grade, grade_label = "C+", "Moyen"
        elif global_score >= 60:
            grade, grade_label = "C", "Moyen"
        else:
            grade, grade_label = "D", "Faible"

        return {
            "global_score": round(float(global_score), 1),
            "grade": grade,
            "grade_label": grade_label,
            "category_scores": category_scores,
            "interpretation": (
                f"État de santé {grade_label.lower()}. "
                f"{'Continuez vos bonnes habitudes.' if global_score >= 90 else 'Améliorations possibles selon recommandations.'}"
            ),
        }

    @staticmethod
    def calculate_nutritional_needs(
        age: int,
        sex: str,
        weight: float,
        height: float,
        activity_level: str = "moderate",
    ) -> Dict:
        # Mifflin-St Jeor
        if sex == "Masculin":
            bmr = 10 * weight + 6.25 * height - 5 * age + 5
        else:
            bmr = 10 * weight + 6.25 * height - 5 * age - 161

        activity_factors = {
            "sedentary": 1.2,
            "light": 1.375,
            "moderate": 1.55,
            "active": 1.725,
            "very_active": 1.9,
        }
        det = bmr * activity_factors.get(activity_level, 1.55)

        proteins_g = weight * 1.8
        lipids_g = (det * 0.27) / 9

        proteins_kcal = proteins_g * 4
        lipids_kcal = lipids_g * 9
        carbs_kcal = det - proteins_kcal - lipids_kcal
        carbs_g = carbs_kcal / 4

        return {
            "bmr": round(float(bmr), 1),
            "det": round(float(det), 1),
            "proteins_g": round(float(proteins_g), 1),
            "lipids_g": round(float(lipids_g), 1),
            "carbs_g": round(float(carbs_g), 1),
            "activity_level": activity_level,
        }


class RecommendationEngine:
    """Moteur de recommandations personnalisées basé sur les biomarqueurs"""

    @staticmethod
    def generate_personalized_recommendations(
        biomarkers: Dict[str, float],
        age: int,
        sex: str,
        health_score: Dict,
        biological_age_data: Dict,
    ) -> Dict:
        recommendations = {
            "micronutrition": [],
            "alimentation": [],
            "lifestyle": [],
            "supplements": [],
        }
        priorities = []

        for biomarker_key, value in biomarkers.items():
            if value is None:
                continue

            classification = BiomarkerDatabase.classify_biomarker(biomarker_key, float(value), age, sex)

            if classification["status"] in ["abnormal", "deficient", "high", "elevated", "low"]:
                recs = RecommendationEngine._get_biomarker_recommendations(biomarker_key, float(value), classification)

                for rec_type, rec_list in recs.items():
                    recommendations[rec_type].extend(rec_list)

                priorities.append(
                    {
                        "biomarker": biomarker_key,
                        "value": float(value),
                        "status": classification["status"],
                        "priority": "Élevé" if classification["status"] in ["deficient", "high"] else "Moyen",
                    }
                )

        # Dedup
        for key in recommendations:
            recommendations[key] = list(dict.fromkeys(recommendations[key]))

        return {"recommendations": recommendations, "priorities": priorities}

    @staticmethod
    def _get_biomarker_recommendations(biomarker: str, value: float, classification: Dict) -> Dict:
        recs = {"micronutrition": [], "alimentation": [], "lifestyle": [], "supplements": []}

        if biomarker == "glutathion_total" and classification["status"] in ["low", "deficient"]:
            recs["supplements"] += [
                "N-acétyl-cystéine (NAC) : 600–1200 mg/jour",
                "Glycine : 2–3 g/jour (soir)",
                "Vitamine C : 500–1000 mg/jour",
            ]
            recs["alimentation"] += [
                "Privilégiez les protéines soufrées : ail, oignon, crucifères",
                "Consommez des œufs et du poulet (source de cystéine)",
            ]

        if biomarker == "coenzyme_q10" and classification["status"] in ["low", "deficient"]:
            recs["supplements"] += [
                "Coenzyme Q10 (ubiquinol) : 200 mg/jour avec repas gras",
                "PQQ : 10–20 mg/jour",
            ]
            recs["alimentation"] += ["Mangez des viandes d'organes : cœur, foie", "Intégrez sardines et maquereaux"]
            recs["lifestyle"].append("Si vous prenez des statines, la supplémentation en CoQ10 est essentielle")

        if biomarker == "selenium" and classification["status"] in ["low", "deficient"]:
            recs["supplements"].append("Sélénium (sélénométhionine) : 100–200 µg/jour")
            recs["alimentation"] += [
                "Consommez 2-3 noix du Brésil par jour",
                "Mangez des poissons et fruits de mer",
                "Consommez des abats et œufs bio",
            ]

        if biomarker == "ferritine":
            if classification["status"] == "deficient":
                recs["supplements"].append("Fer bisglycinate : 30 mg/jour (à jeun avec vitamine C)")
                recs["alimentation"] += ["Viandes rouges 2-3x/semaine", "Évitez thé/café pendant les repas"]
            elif value > 200:
                recs["lifestyle"].append("Envisagez des saignées thérapeutiques (suivi médical)")
                recs["alimentation"].append("Limitez les aliments enrichis en fer")

        if biomarker == "vit_d":
            if classification["status"] in ["deficient", "insufficient"]:
                dosage = 4000 if value < 20 else 2000
                recs["supplements"].append(f"Vitamine D3 : {dosage} UI/jour")
                recs["lifestyle"].append("Exposition solaire 15-20 min/jour (bras, jambes)")
            elif value > 100:
                recs["lifestyle"].append("Réduire la supplémentation en vitamine D")

        if biomarker == "crp" and value > 3:
            recs["supplements"] += ["Oméga-3 (EPA/DHA) : 2-3 g/jour", "Curcumine : 500-1000 mg/jour"]
            recs["alimentation"].append("Adoptez un régime anti-inflammatoire (méditerranéen)")
            recs["lifestyle"].append("Réduisez le stress chronique")

        if biomarker == "homa_index" and value > 2.4:
            recs["supplements"] += ["Berbérine : 500 mg 3x/jour", "Chrome picolinate : 200 µg/jour"]
            recs["alimentation"] += ["Adoptez un régime low-carb (<100g glucides/jour)", "Privilégiez l'index glycémique bas"]
            recs["lifestyle"] += ["Pratiquez le jeûne intermittent (16:8)", "Exercice de résistance 3x/semaine"]

        if biomarker == "zonuline" and value > 50:
            recs["supplements"] += [
                "L-glutamine : 5-10 g/jour",
                "Zinc carnosine : 75 mg 2x/jour",
                "Probiotiques multi-souches : 50 milliards UFC/jour",
            ]
            recs["alimentation"] += ["Évitez gluten et produits laitiers pendant 3 mois", "Bouillon d'os 2-3x/semaine"]

        if biomarker in ["cortisol_reveil", "cortisol_car_30"] and classification["status"] == "low":
            recs["supplements"] += ["Rhodiola rosea : 200-400 mg/jour", "Ashwagandha : 300-600 mg/jour"]
            recs["lifestyle"] += ["Optimisez votre sommeil (7-9h)", "Techniques de gestion du stress quotidiennes"]

        if biomarker == "dhea" and classification["status"] in ["low", "deficient"]:
            recs["supplements"].append("DHEA : 25-50 mg/jour (sous supervision médicale)")
            recs["lifestyle"].append("Exercice régulier (augmente DHEA naturellement)")

        if biomarker == "homocysteine" and value > 10:
            recs["supplements"] += [
                "Complexe vitamines B : B6 (50mg), B9 (800µg), B12 (1000µg)",
                "TMG (triméthylglycine) : 500-1000 mg/jour",
            ]
            recs["alimentation"].append("Légumes verts à feuilles quotidiennement")

        return recs


# ============================================================================
# SESSION STATE
# ============================================================================

def init_session_state() -> None:
    if "patient_data" not in st.session_state:
        st.session_state.patient_data = {
            "patient_info": {},
            "biological_markers": {},
            "epigenetic_data": {},
            "imaging_data": {},
            "microbiome_data": {},
        }
    if "extracted_data" not in st.session_state:
        st.session_state.extracted_data = {
            "biological": {},
            "epigenetic": {},
            "imaging": {},
            "microbiome": {},
            "patient_info": {},
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


init_session_state()


# ============================================================================
# HEADER
# ============================================================================

_, col_title = st.columns([1, 4])
with col_title:
    st.markdown('<h1 class="main-title">🧬 ALGO-LIFE</h1>', unsafe_allow_html=True)
    st.markdown(
        "<p class=\"sub-title\">Plateforme Multimodale d'Analyse de Santé Fonctionnelle</p>",
        unsafe_allow_html=True,
    )
st.markdown("---")


# ============================================================================
# SIDEBAR - INFORMATIONS PATIENT
# ============================================================================

with st.sidebar:
    st.header("👤 Informations Patient")

    # Debug pdf generator path
    st.caption("🧪 Debug PDF generator")
    st.code(getattr(pdfgen, "__file__", "unknown"), language="text")
    st.caption(f"PDFGEN LOADED: {datetime.now().strftime('%H:%M:%S')}")

    if not UNIVERSAL_EXTRACTOR_AVAILABLE:
        st.error("❌ UniversalPDFExtractor indisponible (import failed).")
        st.code(_UNIVERSAL_IMPORT_ERROR, language="text")

    if not MICROBIOME_EXTRACTOR_AVAILABLE:
        st.warning("⚠️ Microbiome extractor indisponible (import failed).")
        st.code(_MICROBIOME_IMPORT_ERROR, language="text")

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
<li>✅ <strong>Biologie</strong>: Hormones, métabolisme, inflammation, microbiote, antioxydants</li>
<li>✅ <strong>Épigénétique</strong>: Âge biologique, méthylation, télomères</li>
<li>✅ <strong>Imagerie</strong>: DXA, composition corporelle, densité osseuse</li>
</ul>
<p><strong>Formats supportés:</strong> Tous les PDF médicaux standards (SYNLAB, LIMS, laboratoires européens)</p>
</div>
""",
        unsafe_allow_html=True,
    )

    st.divider()

    col_upload1, col_upload2, col_upload3, col_upload4 = st.columns(4)

    # --- Biologie
    with col_upload1:
        st.subheader("🧪 PDF Biologie")
        bio_pdf = st.file_uploader(
            "Analyses biologiques",
            type=["pdf"],
            key="bio_pdf_upload",
            help="Hormones, métabolisme, inflammation, microbiote...",
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
        st.subheader("🏥 PDF Imagerie / DXA")
        imaging_pdf = st.file_uploader(
            "Imagerie (DXA, composition corporelle, densité osseuse)",
            type=["pdf"],
            key="imaging_pdf_upload",
            help="DXA, composition corporelle, densité osseuse... (module en cours d'intégration)",
        )

        if imaging_pdf:
            st.info("ℹ️ Module DXA en cours d'intégration dans cette version. Vous pouvez déjà importer la biologie, l'épigénétique et le microbiote.")

    # ✅ NOUVEAU: Colonne Microbiote AVEC EXTRACTION AVANCÉE
# --- Microbiote (IDK GutMAP)
with col_upload4:
    st.subheader("🦠 PDF Microbiote")
    microbiome_pdf = st.file_uploader(
        "Analyses du microbiote",
        type=["pdf"],
        key="microbiome_pdf_upload",
        help="Rapport IDK GutMAP (dysbiosis index, diversité, bactéries clés...)",
    )

    if microbiome_pdf:
        debug_micro = st.checkbox("🐛 Mode Debug", key="debug_micro_check")

        if st.button("🔍 Extraire", key="extract_microbiome_btn", use_container_width=True):
            if not MICROBIOME_EXTRACTOR_AVAILABLE:
                st.error("❌ Extracteur microbiote indisponible.")
                try:
                    st.code(_MICROBIOME_IMPORT_ERROR, language="text")
                except Exception:
                    pass
            else:
                with st.spinner("Extraction en cours..."):
                    microbiome_data = {}

                    try:
                        # 1) on récupère le texte via l'extracteur universel (déjà en place)
                        text = AdvancedPDFExtractor.extract_text(microbiome_pdf)

                        # 2) extraction structurée microbiote (IDK GutMAP)
                        microbiome_data = extract_microbiome_data(text, debug=debug_micro) or {}
                    except Exception as e:
                        st.error(f"❌ Erreur extraction microbiote: {e}")
                        import traceback
                        with st.expander("Détails de l'erreur microbiote"):
                            st.code(traceback.format_exc())

                    if microbiome_data:
                        st.session_state.extracted_data["microbiome"] = microbiome_data
                        st.session_state.patient_data.setdefault("microbiome_data", {})
                        st.session_state.patient_data["microbiome_data"].update(microbiome_data)

                        st.success(f"✅ **{len(microbiome_data)} paramètres microbiote extraits!**")

                        # Affichage rapide (quelques métriques si présentes)
                        m1, m2, m3, m4 = st.columns(4)

                        if "dysbiosis_index" in microbiome_data:
                            di = microbiome_data["dysbiosis_index"]
                            try:
                                di = float(di)
                            except Exception:
                                di = di
                            m1.metric("Dysbiosis Index", di)

                        if "diversity_shannon" in microbiome_data:
                            m2.metric("Diversité (Shannon)", microbiome_data["diversity_shannon"])

                        if "akkermansia_muciniphila" in microbiome_data:
                            m3.metric("Akkermansia", microbiome_data["akkermansia_muciniphila"])

                        if "faecalibacterium_prausnitzii" in microbiome_data:
                            m4.metric("Faecalibacterium", microbiome_data["faecalibacterium_prausnitzii"])

                        with st.expander("📋 Toutes les données microbiote", expanded=False):
                            # petit tri: indices d'abord
                            keys_first = [
                                "dysbiosis_index",
                                "diversity_shannon",
                                "firmicutes_bacteroidetes_ratio",
                            ]
                            ordered = {}
                            for k in keys_first:
                                if k in microbiome_data:
                                    ordered[k] = microbiome_data[k]
                            for k, v in microbiome_data.items():
                                if k not in ordered:
                                    ordered[k] = v
                            st.json(ordered)
                    else:
                        st.warning("⚠️ Aucune donnée de microbiote trouvée. Essayez le mode Debug.")
    st.divider()

    st.subheader("📊 Récapitulatif des Données Extraites")
    total_bio = len(st.session_state.extracted_data.get("biological", {}))
    total_epi = len(st.session_state.extracted_data.get("epigenetic", {}))
    total_img = len(st.session_state.extracted_data.get("imaging", {}))
    total_micro = len(st.session_state.extracted_data.get("microbiome", {}))
    total = total_bio + total_epi + total_img + total_micro

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("🧪 Biomarqueurs Bio", total_bio)
    c2.metric("🧬 Paramètres Épi", total_epi)
    c3.metric("🏥 Données Imagerie", total_img)
    c4.metric("🦠 Microbiote", total_micro)
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
                                    "vit_d": biomarkers.get("vit_d"),
                                    "selenium": biomarkers.get("selenium"),
                                    "zinc": biomarkers.get("zinc"),
                                    "ferritine": biomarkers.get("ferritine"),
                                },
                            }

                            epi_data_engine = {
                                "epigenetic_age": {
                                    "biological_age": st.session_state.extracted_data.get("epigenetic", {}).get("biological_age"),
                                    "chronological_age": patient_info["age"],
                                }
                            }

                            st.session_state.engine_results = engine.analyze(dxa_data, bio_data_engine, epi_data_engine)
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
# TAB 2 - ANALYSE
# ============================================================================

with tab2:
    st.header("📊 Analyse Complète & Scores de Santé")

    if not st.session_state.analysis_complete:
        st.info("📥 Veuillez d'abord importer des données et lancer l'analyse depuis l'onglet 'Import & Extraction'")
    else:
        health_score = st.session_state.health_score
        biological_age = st.session_state.biological_age

        st.subheader("🎯 Scores Principaux")
        col_score1, col_score2 = st.columns(2)

        with col_score1:
            st.markdown("### Score Santé")
            score = float(health_score["global_score"])
            grade = health_score["grade"]
            grade_label = health_score["grade_label"]

            if score >= 95:
                score_class = "score-excellent"
            elif score >= 80:
                score_class = "score-good"
            elif score >= 60:
                score_class = "score-moderate"
            else:
                score_class = "score-poor"

            st.markdown(
                f"""
            <div class="metric-card" style="text-align: center;">
                <span class="{score_class}">{score}/100</span>
                <h3 style="margin-top: 1rem;">Grade: {grade}</h3>
                <p style="font-size: 1.1rem; color: #4A5568;">{grade_label}</p>
                <p style="margin-top: 1rem;">{health_score['interpretation']}</p>
            </div>
            """,
                unsafe_allow_html=True,
            )

        with col_score2:
            st.markdown("### Âge Biologique")
            bio_age = float(biological_age["biological_age"])
            chrono_age = int(biological_age["chronological_age"])
            delta = float(biological_age["delta"])

            if delta < -1:
                color = "#10b981"
                icon = "⬇️"
            elif delta <= 1:
                color = "#3b82f6"
                icon = "↔️"
            else:
                color = "#f59e0b"
                icon = "⬆️"

            st.markdown(
                f"""
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
            """,
                unsafe_allow_html=True,
            )

        st.divider()

        st.subheader("📈 Scores par Catégorie")
        category_scores = health_score["category_scores"]

        df_categories = (
            pd.DataFrame(
                [
                    {
                        "Catégorie": cat.replace("_", " ").title(),
                        "Score": round(float(sc), 1),
                        "Status": "Excellent" if sc >= 90 else "Bon" if sc >= 75 else "Moyen" if sc >= 60 else "Faible",
                    }
                    for cat, sc in category_scores.items()
                ]
            )
            .sort_values("Score", ascending=False)
        )
        st.dataframe(df_categories, use_container_width=True, hide_index=True)

        st.divider()

        st.subheader("🔬 Classification des Biomarqueurs")

        biomarkers = st.session_state.patient_data["biological_markers"]
        patient_info = st.session_state.patient_data["patient_info"]

        classified = {"normaux": [], "a_surveiller": [], "anormaux": [], "non_references": []}
        refs = BiomarkerDatabase.get_reference_ranges()

        for biomarker_key, value in biomarkers.items():
            if value is None:
                continue
            classification = BiomarkerDatabase.classify_biomarker(biomarker_key, float(value), patient_info.get("age"), patient_info.get("sexe"))

            bio_info = refs.get(biomarker_key, {})
            item = {
                "Biomarqueur": biomarker_key.replace("_", " ").title(),
                "Valeur": float(value),
                "Unité": bio_info.get("unit", ""),
                "Status": classification.get("status", "unknown"),
                "Interprétation": classification.get("interpretation", ""),
                "Icon": classification.get("icon", ""),
            }

            if classification.get("status") in ["optimal", "normal"]:
                classified["normaux"].append(item)
            elif classification.get("status") in ["insufficient", "low", "elevated"]:
                classified["a_surveiller"].append(item)
            elif classification.get("status") in ["deficient", "high", "abnormal"]:
                classified["anormaux"].append(item)
            else:
                classified["non_references"].append(item)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("✅ Normaux", len(classified["normaux"]))
        c2.metric("⚡ À surveiller", len(classified["a_surveiller"]))
        c3.metric("⚠️ Anormaux", len(classified["anormaux"]))
        c4.metric("❓ Non référencés", len(classified["non_references"]))

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

**Version**: 4.1 - Janvier 2026 (Extraction Universelle)  
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
