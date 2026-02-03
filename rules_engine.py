"""
UNILABS / ALGO-LIFE - Plateforme Multimodale COMPLÈTE
✅ Bug reco corrigé
✅ Date de naissance + âge biologique (bFRAil Score)
✅ Affichage PDF à côté du tableau
✅ Observations croisées complètes
"""

from __future__ import annotations

import os
import sys
import re
import tempfile
import base64
from datetime import datetime, date
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

import pandas as pd
import streamlit as st
import numpy as np

# ---------------------------------------------------------------------
# PATHS / IMPORTS
# ---------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from extractors import extract_synlab_biology, extract_idk_microbiome
from rules_engine import RulesEngine

try:
    from pdf_generator import generate_multimodal_report
    PDF_EXPORT_AVAILABLE = True
except Exception:
    PDF_EXPORT_AVAILABLE = False

RULES_EXCEL_PATH = os.path.join(BASE_DIR, "data", "Bases_regles_Synlab.xlsx")


# ---------------------------------------------------------------------
# BFRAIL SCORE - ÂGE BIOLOGIQUE
# ---------------------------------------------------------------------
@dataclass
class BiomarkerData:
    age: float
    sex: str
    crp: float
    hemoglobin: float
    vitamin_d: float
    albumin: Optional[float] = None


class BFrailScore:
    """Calcul âge biologique bFRAil Score"""
    
    def __init__(self):
        self.coefficients_full = {
            'intercept': -5.0,
            'age': 0.05,
            'sex_male': 0.3,
            'crp_6_10': 0.28,
            'crp_gt_10': 0.69,
            'albumin_ge_35': -0.14,
            'hemoglobin_ge_12': -0.15,
            'vit_d_lt_20': 0.25,
        }
        
        self.coefficients_modified = {
            'intercept': -4.5,
            'age': 0.055,
            'sex_male': 0.35,
            'crp_6_10': 0.32,
            'crp_gt_10': 0.75,
            'hemoglobin_ge_12': -0.18,
            'vit_d_lt_20': 0.28,
        }
    
    def calculate(self, data: BiomarkerData) -> Dict:
        has_albumin = data.albumin is not None
        coeffs = self.coefficients_full if has_albumin else self.coefficients_modified
        
        linear_score = coeffs['intercept']
        linear_score += coeffs['age'] * data.age
        if data.sex == 'M':
            linear_score += coeffs['sex_male']
        
        if data.crp < 6:
            pass
        elif 6 <= data.crp <= 10:
            linear_score += coeffs['crp_6_10']
        else:
            linear_score += coeffs['crp_gt_10']
        
        if has_albumin and data.albumin >= 35:
            linear_score += coeffs['albumin_ge_35']
        
        if data.hemoglobin >= 12:
            linear_score += coeffs['hemoglobin_ge_12']
        
        if data.vitamin_d < 20:
            linear_score += coeffs['vit_d_lt_20']
        elif 20 <= data.vitamin_d < 30:
            linear_score += 0.12
        
        probability = 1 / (1 + np.exp(-linear_score))
        
        # Estimer l'âge biologique
        bio_age = data.age + (probability - 0.3) * 20  # Ajustement basé sur la fragilité
        
        if probability < 0.3:
            risk_category = "Faible risque"
            color = "green"
        elif probability < 0.5:
            risk_category = "Risque modéré"
            color = "orange"
        else:
            risk_category = "Risque élevé"
            color = "red"
        
        return {
            'bfrail_score': round(linear_score, 2),
            'frailty_probability': round(probability * 100, 1),
            'bio_age': round(bio_age, 1),
            'risk_category': risk_category,
            'color': color,
            'has_albumin': has_albumin
        }


# ---------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------
def _file_to_temp_path(uploaded_file, suffix: str) -> str:
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.read())
        return tmp.name


def _safe_float(x) -> Optional[float]:
    try:
        if x is None:
            return None
        s = str(x).strip().replace(",", ".")
        s = re.sub(r"[^0-9\.\-\+eE]", "", s)
        return float(s) if s else None
    except Exception:
        return None



def _normalize_reco_sections(reco_raw: Dict[str, Any]) -> Dict[str, List[str]]:
    """Normalise la sortie du RulesEngine vers des sections UI stables.

    Le RulesEngine renvoie typiquement:
      - biology_interpretations: [{biomarker, nutrition_reco, micronutrition_reco, lifestyle_reco, ...}]
      - microbiome_interpretations: [{group, nutrition_reco, supplementation_reco, lifestyle_reco, ...}]

    L'UI, elle, attend des listes:
      - Nutrition, Micronutrition, Lifestyle, Microbiome
    """
    if not isinstance(reco_raw, dict):
        return {"Nutrition": [], "Micronutrition": [], "Lifestyle": [], "Microbiome": []}

    nutrition: List[str] = []
    micronut: List[str] = []
    lifestyle: List[str] = []
    microbiome: List[str] = []

    # --- Biologie
    for item in (reco_raw.get("biology_interpretations") or []):
        if not isinstance(item, dict):
            continue
        biom = str(item.get("biomarker", "")).strip()
        prefix = f"[{biom}] " if biom else ""

        n = item.get("nutrition_reco")
        if n:
            nutrition.append(prefix + str(n).strip())

        m = item.get("micronutrition_reco")
        if m:
            micronut.append(prefix + str(m).strip())

        l = item.get("lifestyle_reco")
        if l:
            lifestyle.append(prefix + str(l).strip())

    # --- Microbiote
    for item in (reco_raw.get("microbiome_interpretations") or []):
        if not isinstance(item, dict):
            continue
        grp = str(item.get("group", "")).strip()
        prefix = f"[{grp}] " if grp else ""

        n = item.get("nutrition_reco")
        if n:
            nutrition.append(prefix + str(n).strip())
            microbiome.append(prefix + str(n).strip())

        s = item.get("supplementation_reco")
        if s:
            micronut.append(prefix + str(s).strip())
            microbiome.append(prefix + str(s).strip())

        l = item.get("lifestyle_reco")
        if l:
            lifestyle.append(prefix + str(l).strip())
            microbiome.append(prefix + str(l).strip())

    # dédoublonnage stable
    def _dedupe(seq: List[str]) -> List[str]:
        seen = set()
        out: List[str] = []
        for x in seq:
            k = str(x).strip()
            if not k or k in seen:
                continue
            seen.add(k)
            out.append(k)
        return out

    return {
        "Nutrition": _dedupe(nutrition),
        "Micronutrition": _dedupe(micronut),
        "Lifestyle": _dedupe(lifestyle),
        "Microbiome": _dedupe(microbiome),
    }


def _calc_age_from_birthdate(birthdate: date) -> int:
    """Calcule l'âge à partir de la date de naissance"""
    today = date.today()
    age = today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))
    return age


def _calc_bmi(weight_kg: Any, height_cm: Any) -> Optional[float]:
    w = _safe_float(weight_kg)
    h = _safe_float(height_cm)
    if w is None or h is None or h <= 0:
        return None
    hm = h / 100.0
    if hm <= 0:
        return None
    return w / (hm * hm)


def _dict_bio_to_dataframe(bio_dict: Dict[str, Any]) -> pd.DataFrame:
    rows = []
    for name, data in (bio_dict or {}).items():
        biomarker = str(name).strip()
        if not biomarker or biomarker.lower() == "nan":
            continue

        if isinstance(data, dict):
            val = data.get("value", data.get("Valeur", ""))
            unit = data.get("unit", data.get("Unité", ""))
            ref = data.get("reference", data.get("Référence", ""))
            status = data.get("status", data.get("Statut", "Normal"))
        else:
            val, unit, ref, status = data, "", "", "Normal"

        rows.append({
            "Biomarqueur": biomarker,
            "Valeur": val,
            "Unité": unit,
            "Référence": ref,
            "Statut": status,
            "Interprétation": ""
        })

    df = pd.DataFrame(rows)
    if not df.empty:
        df["Valeur"] = df["Valeur"].apply(_safe_float)
    return df


def _extract_biomarkers_for_bfrail(bio_df: pd.DataFrame) -> Dict[str, float]:
    """Extrait les biomarqueurs nécessaires au bFRAil Score"""
    markers = {}
    
    if bio_df.empty:
        return markers
    
    for _, row in bio_df.iterrows():
        name = str(row.get("Biomarqueur", "")).lower()
        val = _safe_float(row.get("Valeur"))
        
        if val is None:
            continue
        
        if "crp" in name and "ultrasensible" in name:
            markers['crp'] = val
        elif "hémoglobine" in name or "hemoglobin" in name:
            markers['hemoglobin'] = val
        elif "vitamine d" in name or "vitamin d" in name:
            markers['vitamin_d'] = val
        elif "albumine" in name or "albumin" in name:
            markers['albumin'] = val
    
    return markers


def _patient_to_rules_engine_format(patient_info: Dict[str, Any]) -> Dict[str, Any]:
    sex = (patient_info or {}).get("sex", "F")
    genre = "Homme" if sex == "H" else "Femme"
    antecedents = (patient_info or {}).get("antecedents", "")
    return {
        "nom": (patient_info or {}).get("name", ""),
        "age": (patient_info or {}).get("age", None),
        "genre": genre,
        "notes": antecedents,
    }


def _build_pdf_payload() -> Dict[str, Any]:
    patient = st.session_state.patient_info or {}

    patient_data = {
        "name": patient.get("name", ""),
        "age": patient.get("age", ""),
        "sex": patient.get("sex", ""),
        "weight_kg": patient.get("weight_kg", None),
        "height_cm": patient.get("height_cm", None),
        "bmi": patient.get("bmi", None),
        "birthdate": str(patient.get("birthdate", "")),
        "bio_age": patient.get("bio_age", None),
        "antecedents": patient.get("antecedents", ""),
    }

    biology_data = st.session_state.biology_data or {}
    microbiome_data = st.session_state.microbiome_data or {}

    recos = st.session_state.recommendations or {}
    
    cross_analysis = {
        "cross_analysis": st.session_state.get("cross_analysis_observations", []),
        "priority_actions": st.session_state.get("cross_analysis_actions", []),
    }

    recommendations = {
        "raw": recos,
        "edited": st.session_state.edited_recommendations or {},
    }

    follow_up = _build_follow_up_dict(st.session_state.follow_up)

    return {
        "patient_data": patient_data,
        "biology_data": biology_data,
        "microbiome_data": microbiome_data,
        "cross_analysis": cross_analysis,
        "recommendations": recommendations,
        "follow_up": follow_up,
    }


def _build_follow_up_dict(session_follow: Dict[str, Any]) -> Dict[str, Any]:
    if not session_follow:
        return {}

    nxt = session_follow.get("next_tests", [])
    if isinstance(nxt, list):
        next_tests_txt = ", ".join([str(x).strip() for x in nxt if str(x).strip()])
    else:
        next_tests_txt = str(nxt or "").strip()

    return {
        "next_date": str(session_follow.get("next_date", "")),
        "next_tests": next_tests_txt,
        "plan": session_follow.get("plan", ""),
        "clinician_notes": session_follow.get("clinician_notes", ""),
    }


def _get_rules_engine() -> Optional[RulesEngine]:
    if not os.path.exists(RULES_EXCEL_PATH):
        return None

    if "rules_engine" not in st.session_state:
        st.session_state["rules_engine"] = RulesEngine(RULES_EXCEL_PATH)

    return st.session_state["rules_engine"]


def _generate_cross_analysis(biology_df: pd.DataFrame, microbiome_data: Dict[str, Any]) -> Dict[str, List]:
    """Génère l'analyse croisée biologie+microbiote"""
    observations = []
    actions = []
    
    if biology_df is None or biology_df.empty:
        return {"observations": observations, "actions": actions}
    
    abnormal_markers = biology_df[biology_df["Statut"].str.contains("Élevé|Bas|Critique", case=False, na=False)]
    
    dysbiosis_index = microbiome_data.get("dysbiosis_index", 0) if microbiome_data else 0
    
    for _, row in abnormal_markers.head(3).iterrows():
        marker = row["Biomarqueur"]
        status = row["Statut"]
        
        if "Glucose" in marker and "Élevé" in status:
            observations.append(f"Glucose {status.lower()} - Impact sur équilibre microbiote")
            if dysbiosis_index > 2:
                observations.append("Corrélation hyperglycémie et dysbiose intestinale")
                actions.append({
                    "text": "Optimiser équilibre glycémique et soutenir microbiote",
                    "priority": "high"
                })
        
        elif "Cholestérol" in marker or "LDL" in marker:
            observations.append(f"{marker} {status.lower()} - Inflammation systémique possible")
            actions.append({
                "text": "Optimiser profil lipidique via nutrition et oméga-3",
                "priority": "medium"
            })
        
        elif "Vitamine D" in marker and "Bas" in status:
            observations.append("Déficit vitamine D - Impact sur immunité et barrière intestinale")
            actions.append({
                "text": "Corriger déficit vitamine D (4000 UI/jour, 3 mois)",
                "priority": "high"
            })
        
        elif "Ferritine" in marker and "Bas" in status:
            observations.append("Ferritine basse - Peut affecter énergie et absorption intestinale")
            actions.append({
                "text": "Évaluer causes du déficit en fer et supplémenter",
                "priority": "medium"
            })
    
    if dysbiosis_index >= 4:
        observations.append(f"Dysbiose sévère (index {dysbiosis_index}/5)")
        actions.append({
            "text": "Protocole intensif rééquilibrage microbiote (probiotiques + prébiotiques)",
            "priority": "high"
        })
    elif dysbiosis_index >= 3:
        observations.append(f"Dysbiose modérée (index {dysbiosis_index}/5)")
        actions.append({
            "text": "Soutenir microbiote par alimentation riche en fibres et probiotiques",
            "priority": "medium"
        })
    
    bacteria = microbiome_data.get("bacteria", []) if microbiome_data else []
    deviating = [b for b in bacteria if "deviating" in b.get("result", "").lower()]
    
    if len(deviating) > 3:
        observations.append(f"{len(deviating)} groupes bactériens déviants - Déséquilibre microbien")
    
    butyrate_producers = [b for b in bacteria if "butyrate" in b.get("group", "").lower()]
    if any("deviating" in b.get("result", "").lower() for b in butyrate_producers):
        observations.append("Producteurs de butyrate déviants - Impact sur santé intestinale")
        actions.append({
            "text": "Augmenter fibres prébiotiques (inuline 5g/jour)",
            "priority": "high"
        })
    
    if not observations:
        observations.append("Profil global équilibré - Maintenir bonnes pratiques")
        actions.append({
            "text": "Poursuivre alimentation variée et équilibrée",
            "priority": "low"
        })
    
    return {"observations": observations, "actions": actions}


def _display_pdf_viewer(pdf_path: str, height: int = 600):
    """Affiche un PDF dans Streamlit"""
    with open(pdf_path, "rb") as f:
        base64_pdf = base64.b64encode(f.read()).decode('utf-8')
    
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="{height}" type="application/pdf"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True)


# ---------------------------------------------------------------------
# STREAMLIT PAGE CONFIG
# ---------------------------------------------------------------------
st.set_page_config(
    page_title="UNILABS - ALGO-LIFE",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
.main-header {
    background: linear-gradient(135deg, #0B2E4A 0%, #1F6AA5 100%);
    padding: 1.2rem 1.3rem;
    border-radius: 14px;
    color: white;
    margin-bottom: 0.9rem;
}
.main-header h1 { margin: 0; font-size: 2.0rem; }
.main-header .sub { opacity: 0.95; margin-top: 0.35rem; font-size: 0.98rem; }

.patient-strip {
    background: #f6f8fb;
    padding: 0.85rem 1rem;
    border-radius: 10px;
    border-left: 5px solid #1F6AA5;
    margin-bottom: 1.1rem;
}

.biomarker-card {
    background: white;
    border: 1px solid #e0e0e0;
    border-radius: 12px;
    padding: 1rem;
    margin-bottom: 1rem;
    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

.status-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    margin-right: 10px;
}

.status-normal { background-color: #4CAF50; }
.status-bas { background-color: #FF9800; }
.status-eleve { background-color: #F44336; }

.section-divider {
    border-top: 2px solid #1F6AA5;
    margin: 2rem 0 1rem 0;
    padding-top: 1rem;
}
</style>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------
# SESSION STATE INIT
# ---------------------------------------------------------------------
if "patient_info" not in st.session_state:
    st.session_state.patient_info = {}

if "biology_data" not in st.session_state:
    st.session_state.biology_data = {}

if "biology_df" not in st.session_state:
    st.session_state.biology_df = pd.DataFrame()

if "microbiome_data" not in st.session_state:
    st.session_state.microbiome_data = {}

if "recommendations" not in st.session_state:
    st.session_state.recommendations = {}

if "edited_recommendations" not in st.session_state:
    st.session_state.edited_recommendations = {}

if "follow_up" not in st.session_state:
    st.session_state.follow_up = {}

if "data_extracted" not in st.session_state:
    st.session_state.data_extracted = False

if "cross_analysis_observations" not in st.session_state:
    st.session_state.cross_analysis_observations = []

if "cross_analysis_actions" not in st.session_state:
    st.session_state.cross_analysis_actions = []

if "bio_pdf_path" not in st.session_state:
    st.session_state.bio_pdf_path = None

if "micro_pdf_path" not in st.session_state:
    st.session_state.micro_pdf_path = None

# ---------------------------------------------------------------------
# HEADER
# ---------------------------------------------------------------------
st.markdown(
    """
<div class="main-header">
    <h1>🧬 UNILABS / ALGO-LIFE</h1>
    <div class="sub">Plateforme d'Analyse Multimodale - Biologie Fonctionnelle & Microbiote</div>
</div>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------
# SIDEBAR - PATIENT INFO
# ---------------------------------------------------------------------
with st.sidebar:
    st.header("👤 Informations Patient")

    patient_name = st.text_input(
        "Nom complet",
        value=st.session_state.patient_info.get("name", ""),
        key="patient_name",
    )

    # Date de naissance
    patient_birthdate = st.date_input(
        "Date de naissance",
        value=st.session_state.patient_info.get("birthdate") or date(1980, 1, 1),
        min_value=date(1920, 1, 1),
        max_value=date.today(),
        key="patient_birthdate",
    )

    # Calculer l'âge automatiquement
    patient_age = _calc_age_from_birthdate(patient_birthdate)
    st.metric("Âge calculé", f"{patient_age} ans")

    patient_sex = st.selectbox(
        "Sexe",
        ["F", "H"],
        index=0 if st.session_state.patient_info.get("sex", "F") == "F" else 1,
        key="patient_sex",
    )

    col_weight, col_height = st.columns(2)
    with col_weight:
        patient_weight = st.number_input(
            "Poids (kg)",
            min_value=0.0,
            max_value=300.0,
            value=float(st.session_state.patient_info.get("weight_kg", 0) or 0),
            step=0.1,
            key="patient_weight",
        )
    with col_height:
        patient_height = st.number_input(
            "Taille (cm)",
            min_value=0.0,
            max_value=250.0,
            value=float(st.session_state.patient_info.get("height_cm", 0) or 0),
            step=0.1,
            key="patient_height",
        )

    patient_bmi = _calc_bmi(patient_weight, patient_height)
    if patient_bmi:
        st.metric("IMC", f"{patient_bmi:.1f}")

    # Calcul âge biologique (si biomarqueurs disponibles)
    bio_age = None
    if not st.session_state.biology_df.empty and patient_age >= 50:
        markers = _extract_biomarkers_for_bfrail(st.session_state.biology_df)
        if 'crp' in markers and 'hemoglobin' in markers and 'vitamin_d' in markers:
            try:
                bfrail_data = BiomarkerData(
                    age=float(patient_age),
                    sex=patient_sex,
                    crp=markers['crp'],
                    hemoglobin=markers['hemoglobin'],
                    vitamin_d=markers['vitamin_d'],
                    albumin=markers.get('albumin')
                )
                bfrail_result = BFrailScore().calculate(bfrail_data)
                bio_age = bfrail_result['bio_age']
                
                st.markdown("---")
                st.markdown("### 🧬 Âge Biologique (bFRAil)")
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Âge chronologique", f"{patient_age} ans")
                with col2:
                    delta = bio_age - patient_age
                    st.metric("Âge biologique", f"{bio_age:.1f} ans", delta=f"{delta:+.1f} ans")
                
                st.caption(f"Risque: {bfrail_result['risk_category']} ({bfrail_result['frailty_probability']}%)")
            except Exception as e:
                st.warning(f"Impossible de calculer l'âge biologique: {e}")

    patient_antecedents = st.text_area(
        "Antécédents médicaux",
        value=st.session_state.patient_info.get("antecedents", ""),
        height=100,
        key="patient_antecedents",
    )

    if st.button("💾 Enregistrer les infos patient", type="primary"):
        st.session_state.patient_info = {
            "name": patient_name,
            "birthdate": patient_birthdate,
            "age": patient_age,
            "sex": patient_sex,
            "weight_kg": patient_weight if patient_weight > 0 else None,
            "height_cm": patient_height if patient_height > 0 else None,
            "bmi": patient_bmi,
            "bio_age": bio_age,
            "antecedents": patient_antecedents,
        }
        st.success("✅ Informations enregistrées")
        st.rerun()

# Patient strip
patient = st.session_state.patient_info
if patient.get("name"):
    patient_display = f"<b>{patient['name']}</b>"
    if patient.get("birthdate"):
        patient_display += f" • Né(e) le {patient['birthdate'].strftime('%d/%m/%Y')}"
    if patient.get("age"):
        patient_display += f" • {patient['age']} ans"
    if patient.get("bio_age"):
        patient_display += f" • Âge bio: {patient['bio_age']:.1f} ans"
    if patient.get("sex"):
        patient_display += f" • {patient['sex']}"
    if patient.get("bmi"):
        patient_display += f" • IMC: {patient['bmi']:.1f}"

    st.markdown(
        f'<div class="patient-strip">👤 {patient_display}</div>',
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------
# TABS
# ---------------------------------------------------------------------
tabs = st.tabs([
    "📊 Import & Données",
    "💡 Interprétation",
    "🔄 Analyse Croisée",
    "📅 Suivi",
    "📄 Export PDF"
])

# ═════════════════════════════════════════════════════════════════════
# TAB 0: IMPORT & DONNÉES
# ═════════════════════════════════════════════════════════════════════
with tabs[0]:
    st.subheader("📊 Import & Données extraites")

    col_bio_upload, col_micro_upload = st.columns(2)

    # BIOLOGIE
    with col_bio_upload:
        st.markdown("### 🔬 Biologie")
        bio_file = st.file_uploader(
            "PDF Biologie (Synlab/Unilabs)",
            type=["pdf"],
            key="bio_upload",
        )

        if bio_file and st.button("🔍 Extraire Biologie", key="extract_bio"):
            with st.spinner("Extraction en cours..."):
                tmp_path = _file_to_temp_path(bio_file, ".pdf")
                try:
                    bio_data = extract_synlab_biology(tmp_path)
                    st.session_state.biology_data = bio_data
                    st.session_state.biology_df = _dict_bio_to_dataframe(bio_data)
                    st.session_state.bio_pdf_path = tmp_path
                    st.session_state.data_extracted = True
                    st.success(f"✅ {len(bio_data)} biomarqueurs extraits")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Erreur: {e}")
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)

    # MICROBIOTE
    with col_micro_upload:
        st.markdown("### 🦠 Microbiote")
        micro_file = st.file_uploader(
            "PDF Microbiote (IDK GutMAP)",
            type=["pdf"],
            key="micro_upload",
        )

        if micro_file and st.button("🔍 Extraire Microbiote", key="extract_micro"):
            with st.spinner("Extraction en cours..."):
                tmp_path = _file_to_temp_path(micro_file, ".pdf")
                try:
                    micro_data = extract_idk_microbiome(tmp_path)
                    st.session_state.microbiome_data = micro_data
                    st.session_state.micro_pdf_path = tmp_path
                    st.session_state.data_extracted = True
                    bacteria_count = len(micro_data.get("bacteria", []))
                    st.success(f"✅ Microbiote extrait ({bacteria_count} groupes)")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Erreur: {e}")
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)

    # AFFICHAGE DONNÉES + PDF
    if st.session_state.data_extracted:
        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
        
        # BIOLOGIE
        if not st.session_state.biology_df.empty:
            st.markdown("### 🔬 Données Biologie")
            
            col_pdf_bio, col_table_bio = st.columns([1, 1])
            
            with col_pdf_bio:
                st.markdown("**📄 PDF Source**")
                if st.session_state.bio_pdf_path and os.path.exists(st.session_state.bio_pdf_path):
                    _display_pdf_viewer(st.session_state.bio_pdf_path, height=500)
                else:
                    st.info("PDF non disponible")
            
            with col_table_bio:
                st.markdown("**📊 Valeurs Extraites**")
                edited_bio_df = st.data_editor(
                    st.session_state.biology_df,
                    use_container_width=True,
                    hide_index=False,
                    height=500,
                    column_config={
                        "Biomarqueur": st.column_config.TextColumn("Biomarqueur", width="medium"),
                        "Valeur": st.column_config.NumberColumn("Valeur", format="%.2f"),
                        "Unité": st.column_config.TextColumn("Unité", width="small"),
                        "Référence": st.column_config.TextColumn("Référence", width="medium"),
                        "Statut": st.column_config.TextColumn("Statut", width="small"),
                        "Interprétation": st.column_config.TextColumn("Interprétation", width="large"),
                    },
                    key="bio_editor"
                )
                st.session_state.biology_df = edited_bio_df
                st.caption(f"📊 {len(edited_bio_df)} biomarqueurs")
        
        # MICROBIOTE
        if st.session_state.microbiome_data and st.session_state.microbiome_data.get("bacteria"):
            st.markdown("### 🦠 Données Microbiote")
            
            col_pdf_micro, col_table_micro = st.columns([1, 1])
            
            with col_pdf_micro:
                st.markdown("**📄 PDF Source**")
                if st.session_state.micro_pdf_path and os.path.exists(st.session_state.micro_pdf_path):
                    _display_pdf_viewer(st.session_state.micro_pdf_path, height=500)
                else:
                    st.info("PDF non disponible")
            
            with col_table_micro:
                st.markdown("**📊 Valeurs Extraites**")
                micro_data = st.session_state.microbiome_data
                bacteria_list = micro_data.get("bacteria", [])
                
                bacteria_df = pd.DataFrame([
                    {
                        "Catégorie": b.get("category", ""),
                        "Élément": b.get("group", ""),
                        "Statut": b.get("result", ""),
                        "Interprétation": ""
                    }
                    for b in bacteria_list
                ])
                
                dysbiosis = micro_data.get("dysbiosis_index", "N/A")
                diversity = micro_data.get("diversity", "N/A")
                st.caption(f"ℹ️ dysbiosis={dysbiosis}, diversity={diversity}")
                
                edited_micro_df = st.data_editor(
                    bacteria_df,
                    use_container_width=True,
                    hide_index=False,
                    height=450,
                    column_config={
                        "Catégorie": st.column_config.TextColumn("category", width="small"),
                        "Élément": st.column_config.TextColumn("Description", width="large"),
                        "Statut": st.column_config.TextColumn("result", width="medium"),
                        "Interprétation": st.column_config.TextColumn("Interprétation", width="large"),
                    },
                    key="micro_editor"
                )
                
                if "edited_microbiome_df" not in st.session_state:
                    st.session_state.edited_microbiome_df = edited_micro_df
                else:
                    st.session_state.edited_microbiome_df = edited_micro_df
                
                st.caption(f"🦠 {len(bacteria_list)} groupes bactériens")

# ═════════════════════════════════════════════════════════════════════
# TAB 1: INTERPRÉTATION (RECOMMANDATIONS)
# ═════════════════════════════════════════════════════════════════════
with tabs[1]:
    st.subheader("💡 Interprétation & Recommandations")

    if not st.session_state.data_extracted:
        st.warning("⚠️ Veuillez d'abord extraire les données")
    else:
        if st.button("🤖 Générer l'interprétation automatique", type="primary"):
            engine = _get_rules_engine()
            if not engine:
                st.error(f"❌ Fichier de règles introuvable: {RULES_EXCEL_PATH}")
            else:
                with st.spinner("Génération..."):
                    try:
                        patient_fmt = _patient_to_rules_engine_format(st.session_state.patient_info)
                        bio_df = st.session_state.biology_df
                        micro_data = st.session_state.microbiome_data

                        # ✅ RulesEngine attend une LISTE de dicts (orient="records"), pas un DataFrame
biology_list = []
if isinstance(bio_df, pd.DataFrame) and not bio_df.empty:
    biology_list = bio_df.to_dict(orient="records")

reco = engine.generate_recommendations(
    biology_data=biology_list,
    microbiome_data=micro_data,
    patient_info=patient_fmt,
)
                        
                        st.session_state.recommendations = reco
                        st.success("✅ Interprétation générée")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Erreur: {e}")
                        import traceback
                        st.code(traceback.format_exc())

        # AFFICHAGE DES RECOMMANDATIONS
        if st.session_state.recommendations:
            reco_raw = st.session_state.recommendations
            reco = _normalize_reco_sections(reco_raw)

            with st.expander("🛠️ Debug recos (si vide)"):
                                st.write("Clés reco_raw :", list(reco_raw.keys()) if isinstance(reco_raw, dict) else type(reco_raw))
                st.json(reco_raw)


            # Nutrition
            nutrition_items = reco.get("Nutrition", [])
            if nutrition_items:
                st.markdown("### 🥗 Nutrition")
                for i, item in enumerate(nutrition_items):
                    st.markdown(f"**{i+1}.** {item}")
                st.markdown("---")

            # Micronutrition
            micronut_items = reco.get("Micronutrition", [])
            if micronut_items:
                st.markdown("### 💊 Micronutrition")
                for i, item in enumerate(micronut_items):
                    st.markdown(f"**{i+1}.** {item}")
                st.markdown("---")

            # Microbiome
            microbiome_items = reco.get("Microbiome", [])
            if microbiome_items:
                st.markdown("### 🦠 Microbiome")
                for i, item in enumerate(microbiome_items):
                    st.markdown(f"**{i+1}.** {item}")
                st.markdown("---")

            # Lifestyle
            lifestyle_items = reco.get("Lifestyle", [])
            if lifestyle_items:
                st.markdown("### 🏃 Lifestyle")
                for i, item in enumerate(lifestyle_items):
                    st.markdown(f"**{i+1}.** {item}")
                st.markdown("---")

            # Supplementation
            suppl_items = reco.get("Supplementation", [])
            if suppl_items:
                st.markdown("### 📋 Protocole de Supplémentation")
                suppl_df = pd.DataFrame(suppl_items)
                st.dataframe(suppl_df, use_container_width=True)

# ═════════════════════════════════════════════════════════════════════
# TAB 2: ANALYSE CROISÉE
# ═════════════════════════════════════════════════════════════════════
with tabs[2]:
    st.subheader("🔄 Analyse Croisée Multimodale")

    if not st.session_state.data_extracted:
        st.warning("⚠️ Veuillez d'abord extraire les données")
    else:
        if st.button("🤖 Générer l'analyse croisée", type="primary"):
            with st.spinner("Analyse en cours..."):
                bio_df = st.session_state.biology_df
                micro_data = st.session_state.microbiome_data
                
                cross_analysis = _generate_cross_analysis(bio_df, micro_data)
                
                st.session_state.cross_analysis_observations = cross_analysis["observations"]
                st.session_state.cross_analysis_actions = cross_analysis["actions"]
                
                st.success("✅ Analyse croisée générée")
                st.rerun()
        
        # Observations
        st.markdown("### 🔍 Observations Croisées")
        observations_text = "\n".join(st.session_state.cross_analysis_observations)
        edited_observations = st.text_area(
            "Observations (une par ligne)",
            value=observations_text,
            height=200,
            help="Modifiez, ajoutez ou supprimez des observations"
        )
        
        if edited_observations != observations_text:
            st.session_state.cross_analysis_observations = [
                line.strip() for line in edited_observations.split("\n") if line.strip()
            ]
        
        # Actions prioritaires
        st.markdown("### ⚡ Actions Prioritaires")
        for i, action in enumerate(st.session_state.cross_analysis_actions):
            col1, col2, col3 = st.columns([3, 1, 1])
            
            with col1:
                if isinstance(action, dict):
                    action_text = action.get("text", "")
                    priority = action.get("priority", "medium")
                else:
                    action_text = str(action)
                    priority = "medium"
                
                new_text = st.text_input(
                    f"Action {i+1}",
                    value=action_text,
                    key=f"action_{i}_text"
                )
            
            with col2:
                new_priority = st.selectbox(
                    "Priorité",
                    ["high", "medium", "low"],
                    index=["high", "medium", "low"].index(priority),
                    key=f"action_{i}_priority"
                )
            
            with col3:
                if st.button("🗑️", key=f"delete_action_{i}"):
                    st.session_state.cross_analysis_actions.pop(i)
                    st.rerun()
            
            st.session_state.cross_analysis_actions[i] = {
                "text": new_text,
                "priority": new_priority
            }
        
        if st.button("➕ Ajouter une action"):
            st.session_state.cross_analysis_actions.append({
                "text": "Nouvelle action",
                "priority": "medium"
            })
            st.rerun()

# ═════════════════════════════════════════════════════════════════════
# TAB 3: SUIVI
# ═════════════════════════════════════════════════════════════════════
with tabs[3]:
    st.subheader("📅 Plan de Suivi")

    next_date = st.date_input(
        "Date du prochain contrôle",
        value=st.session_state.follow_up.get("next_date") or date.today(),
        key="follow_date",
    )

    prev_tests = st.session_state.follow_up.get("next_tests", [])
    if isinstance(prev_tests, str):
        prev_tests = [x.strip() for x in prev_tests.split(",") if x.strip()]

    engine = _get_rules_engine()
    if engine:
        all_biomarkers = engine.list_all_biomarkers()
        next_tests_list = st.multiselect(
            "Analyses à recontrôler",
            options=all_biomarkers,
            default=prev_tests,
            key="follow_tests",
        )
    else:
        st.warning("Règles non chargées")
        next_tests_list = prev_tests

    manual_add = st.text_input(
        "Ajouter un biomarqueur (manuel)",
        value="",
        placeholder="Ex: LBP, DAO, Homocystéine…",
        key="follow_manual_add",
    )
    if manual_add.strip():
        if manual_add.strip() not in next_tests_list:
            next_tests_list = next_tests_list + [manual_add.strip()]

    plan = st.text_area(
        "Plan de suivi",
        value=st.session_state.follow_up.get("plan", ""),
        key="follow_plan",
        height=120,
    )

    clinician_notes = st.text_area(
        "Notes internes",
        value=st.session_state.follow_up.get("clinician_notes", ""),
        key="follow_notes",
        height=90,
    )

    if st.button("💾 Enregistrer le suivi"):
        st.session_state.follow_up = {
            "next_date": next_date,
            "next_tests": next_tests_list,
            "plan": plan,
            "clinician_notes": clinician_notes,
        }
        st.success("✅ Suivi enregistré")

# ═════════════════════════════════════════════════════════════════════
# TAB 4: EXPORT PDF
# ═════════════════════════════════════════════════════════════════════
with tabs[4]:
    st.subheader("📄 Export PDF")
    
    if not PDF_EXPORT_AVAILABLE:
        st.error("❌ Export PDF indisponible")
    else:
        if not st.session_state.data_extracted:
            st.warning("Générez d'abord une analyse")
        else:
            pdf_filename = st.text_input(
                "Nom du fichier PDF",
                value=f"UNILABS_rapport_{(patient.get('name','patient')).replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf",
            )

            if st.button("📄 Générer le PDF", type="primary"):
                payload = _build_pdf_payload()
                out_path = os.path.join(tempfile.gettempdir(), pdf_filename)

                try:
                    pdf_path = generate_multimodal_report(
                        patient_data=payload["patient_data"],
                        biology_data=payload["biology_data"],
                        microbiome_data=payload["microbiome_data"],
                        cross_analysis=payload["cross_analysis"],
                        recommendations=payload["recommendations"],
                        follow_up=payload["follow_up"],
                        output_path=out_path,
                    )

                    with open(pdf_path, "rb") as f:
                        st.download_button(
                            "⬇️ Télécharger le PDF",
                            data=f.read(),
                            file_name=pdf_filename,
                            mime="application/pdf",
                        )
                    st.success("✅ PDF généré")
                except Exception as e:
                    st.error(f"❌ Erreur: {e}")
                    import traceback
                    st.code(traceback.format_exc())
