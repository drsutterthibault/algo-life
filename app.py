"""
UNILABS Plateforme Multimodale v12.0 - VERSION FINALE
✅ VÉRITABLE MULTIMODALITÉ : Bio + Microbiote + Analyses croisées dans l'interprétation
✅ IA À VALEUR AJOUTÉE : Recommandations précises nutrition/micronutrition basées sur bilans
✅ IA enrichit les règles (ne les remplace pas) avec conseils actionnables
"""

from __future__ import annotations

import os
import sys
import re
import tempfile
from datetime import datetime, date
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

import pandas as pd
import streamlit as st
import numpy as np

# =====================================================================
# IA - ENRICHISSEMENT INTELLIGENT DES RECOMMANDATIONS
# =====================================================================
import json as _json

_DEFAULT_OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

def _clean_api_key(raw: str) -> str:
    k = (raw or "").strip().strip('"').strip("'").strip()
    return k

def _get_openai_api_key() -> str:
    k = os.getenv("OPENAI_API_KEY", "")
    if k:
        return _clean_api_key(k)
    
    try:
        if hasattr(st, "secrets") and "OPENAI_API_KEY" in st.secrets:
            return _clean_api_key(str(st.secrets["OPENAI_API_KEY"]))
    except Exception:
        pass
    
    return ""

_AI_ENRICHMENT_PROMPT = """Tu es un expert en biologie fonctionnelle, nutrition et micronutrition avec 20 ans d'expérience.

🎯 TA MISSION :
Tu reçois des recommandations générées par un système de règles expert. 
TON RÔLE : les ENRICHIR avec 8-15 recommandations NOUVELLES ultra-précises et actionnables.

📋 FOCUS ABSOLU :
1. NUTRITION : Aliments spécifiques, quantités, fréquences, timing, mode de cuisson
2. MICRONUTRITION : Formes biodisponibles, dosages suggérés (non prescriptifs), synergies, timing de prise

❌ INTERDICTIONS :
- Aucun diagnostic médical
- Aucune posologie définitive (utilise "généralement conseillé", "souvent suggéré autour de")
- Aucune invention de données absentes du bilan
- Aucun conseil dangereux

✅ CE QUE TU DOIS FAIRE :
- Analyser les biomarqueurs (valeurs, statuts, références)
- Analyser le microbiote (DI, diversité, groupes déviants)
- Analyser les signaux croisés bio × micro
- Contextualiser selon âge, sexe, IMC, antécédents
- Générer 8-15 recommandations NOUVELLES précises et actionnables

📊 FORMAT DE SORTIE (JSON STRICT) :
{
  "synthese_enrichie": "2-4 lignes résumant l'approche personnalisée",
  "nutrition_enrichie": [
    "5-8 recommandations nutrition PRÉCISES (aliments, quantités, timing, mode préparation)"
  ],
  "micronutrition_enrichie": [
    "5-8 recommandations micronutrition PRÉCISES (formes, dosages suggérés, synergies, timing)"
  ],
  "contexte_applique": "Comment tu as personnalisé selon profil patient"
}

EXEMPLES DE PRÉCISION ATTENDUE :
❌ Mauvais : "Consommer des oméga-3"
✅ Bon : "Consommer 2-3 portions/semaine de petits poissons gras (sardines, maquereaux, anchois) riches en EPA/DHA, privilégier cuisson vapeur ou papillote pour préserver les acides gras"

❌ Mauvais : "Prendre de la vitamine D"
✅ Bon : "Vitamine D3 (cholécalciférol) généralement conseillée autour de 2000-4000 UI/jour selon déficit, en association avec vitamine K2-MK7 (100-200 µg) pour synergie calcique, à prendre pendant repas contenant lipides pour optimiser absorption"""


def _build_enrichment_payload(
    patient_info: Dict,
    bio_df: pd.DataFrame,
    microbiome_data: Dict,
    cross_analysis: List[Dict],
    existing_reco: Dict
) -> str:
    """Construit un prompt riche pour l'IA"""
    
    # Résumé patient
    bmi_value = patient_info.get('bmi')
    bmi_display = f"{bmi_value:.1f}" if bmi_value else '?'
    
    patient_summary = f"""
👤 PROFIL PATIENT :
- Sexe : {patient_info.get('sex', '?')} | Âge : {patient_info.get('age', '?')} ans | IMC : {bmi_display}
- Antécédents : {patient_info.get('antecedents', 'Non renseignés')[:500]}
"""
    
    # Résumé biologie avec détails
    bio_summary = "\n🔬 BIOLOGIE :\n"
    if not bio_df.empty:
        # Biomarqueurs anormaux
        abnormal = bio_df[bio_df['Statut'].isin(['Bas', 'Élevé'])]
        bio_summary += f"- {len(abnormal)} biomarqueurs anormaux sur {len(bio_df)}\n"
        
        for _, row in abnormal.head(15).iterrows():
            bio_summary += f"  • {row['Biomarqueur']} : {row['Valeur']} {row['Unité']} ({row['Statut']}) - Réf: {row['Référence']}\n"
    else:
        bio_summary += "- Aucune donnée biologique\n"
    
    # Résumé microbiote avec détails
    micro_summary = "\n🦠 MICROBIOTE :\n"
    if microbiome_data:
        di = microbiome_data.get('dysbiosis_index')
        diversity = microbiome_data.get('diversity')
        micro_summary += f"- Indice dysbiose : {di}/5\n"
        micro_summary += f"- Diversité : {diversity}\n"
        
        # Groupes déviants
        groups = microbiome_data.get('bacteria_groups') or microbiome_data.get('bacteria', [])
        deviating = [g for g in groups if 'deviating' in str(g.get('result', '')).lower()]
        if deviating:
            micro_summary += f"- {len(deviating)} groupes déviants :\n"
            for g in deviating[:10]:
                micro_summary += f"  • {g.get('category', '')} - {g.get('result', '')}\n"
    else:
        micro_summary += "- Aucune donnée microbiote\n"
    
    # Signaux croisés
    cross_summary = "\n🔄 SIGNAUX CROISÉS BIO × MICRO :\n"
    if cross_analysis:
        for ca in cross_analysis[:8]:
            cross_summary += f"- {ca.get('title', '')}: {ca.get('description', '')[:200]}\n"
    else:
        cross_summary += "- Aucun signal croisé identifié\n"
    
    # Recommandations existantes (contexte)
    existing_summary = "\n📋 RECOMMANDATIONS EXISTANTES (système de règles) :\n"
    for section, items in existing_reco.items():
        if items and isinstance(items, list):
            existing_summary += f"\n**{section}** ({len(items)} items) :\n"
            for item in items[:5]:
                existing_summary += f"  • {item}\n"
    
    full_prompt = f"""{patient_summary}{bio_summary}{micro_summary}{cross_summary}{existing_summary}

🎯 TON TRAVAIL :
Génère 8-15 recommandations NOUVELLES ultra-précises en nutrition et micronutrition, contextualisées pour ce patient.
Focus sur les aliments, quantités, timing, formes bioactives, dosages suggérés, synergies.

⚠️ SORTIE JSON STRICTE UNIQUEMENT (pas de texte hors JSON)."""
    
    return full_prompt


def _openai_call_json(system_prompt: str, user_prompt: str, model: str) -> Dict[str, Any]:
    """Appel OpenAI avec gestion robuste"""
    api_key = _get_openai_api_key()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY manquant")
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
        )
        
        content = resp.choices[0].message.content
        return _json.loads(content)
    
    except Exception:
        # Fallback HTTP
        import requests
        
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.3,
        }
        r = requests.post(url, headers=headers, data=_json.dumps(body), timeout=90)
        r.raise_for_status()
        data = r.json()
        content = data["choices"][0]["message"]["content"]
        return _json.loads(content)


@st.cache_data(show_spinner=False, ttl=3600)
def ai_enrich_recommendations(
    patient_info: Dict,
    bio_df: pd.DataFrame,
    microbiome_data: Dict,
    cross_analysis: List[Dict],
    existing_reco: Dict
) -> Dict[str, Any]:
    """Enrichissement IA des recommandations"""
    user_prompt = _build_enrichment_payload(
        patient_info, bio_df, microbiome_data, cross_analysis, existing_reco
    )
    return _openai_call_json(_AI_ENRICHMENT_PROMPT, user_prompt, _DEFAULT_OPENAI_MODEL)


# =====================================================================
# CONFIGURATION & IMPORTS
# =====================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from extractors import extract_synlab_biology, extract_idk_microbiome, extract_microbiome_from_excel
from rules_engine import RulesEngine

try:
    from pdf_generator import generate_multimodal_report
    PDF_EXPORT_AVAILABLE = True
except Exception:
    PDF_EXPORT_AVAILABLE = False

RULES_EXCEL_PATH = os.path.join(BASE_DIR, "data", "Bases_regles_Synlab.xlsx")


# =====================================================================
# BFRAIL SCORE
# =====================================================================
@dataclass
class BiomarkerData:
    age: float
    sex: str
    crp: float
    hemoglobin: float
    vitamin_d: float
    albumin: Optional[float] = None


class BFrailScore:
    def __init__(self):
        self.coefficients_full = {
            'intercept': -5.0, 'age': 0.05, 'sex_male': 0.3,
            'crp_6_10': 0.28, 'crp_gt_10': 0.69,
            'albumin_ge_35': -0.14, 'hemoglobin_ge_12': -0.15,
            'vit_d_lt_20': 0.25,
        }
        self.coefficients_modified = {
            'intercept': -4.5, 'age': 0.055, 'sex_male': 0.35,
            'crp_6_10': 0.32, 'crp_gt_10': 0.75,
            'hemoglobin_ge_12': -0.18, 'vit_d_lt_20': 0.28,
        }
    
    def calculate(self, data: BiomarkerData) -> Dict:
        has_albumin = data.albumin is not None
        coeffs = self.coefficients_full if has_albumin else self.coefficients_modified
        
        linear_score = coeffs['intercept'] + coeffs['age'] * data.age
        if data.sex == 'M':
            linear_score += coeffs['sex_male']
        
        if 6 <= data.crp <= 10:
            linear_score += coeffs['crp_6_10']
        elif data.crp > 10:
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
        bio_age = data.age + (probability - 0.3) * 20
        
        if probability < 0.3:
            risk_category, color = "Faible risque", "green"
        elif probability < 0.5:
            risk_category, color = "Risque modéré", "orange"
        else:
            risk_category, color = "Risque élevé", "red"
        
        return {
            'bfrail_score': round(linear_score, 2),
            'frailty_probability': round(probability * 100, 1),
            'bio_age': round(bio_age, 1),
            'risk_category': risk_category,
            'color': color,
            'has_albumin': has_albumin
        }


# =====================================================================
# HELPERS
# =====================================================================
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


def _calc_age_from_birthdate(birthdate: date) -> int:
    today = date.today()
    age = today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))
    return age


def _calc_bmi(weight_kg: Any, height_cm: Any) -> Optional[float]:
    w = _safe_float(weight_kg)
    h = _safe_float(height_cm)
    if w is None or h is None or h <= 0:
        return None
    hm = h / 100.0
    return w / (hm * hm) if hm > 0 else None


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
            "Statut": status
        })
    
    df = pd.DataFrame(rows)
    if not df.empty:
        df["Valeur"] = df["Valeur"].apply(_safe_float)
    return df


def _microbiome_to_dataframe(bacteria: List[Dict]) -> pd.DataFrame:
    if not bacteria:
        return pd.DataFrame()
    
    rows = []
    for b in bacteria:
        result_value = b.get("result") or b.get("abundance", "")
        rows.append({
            "Catégorie": b.get("category", ""),
            "Groupe": (b.get("group", "") or b.get("name", ""))[:100],
            "Résultat": result_value,
            "Abondance": result_value
        })
    
    return pd.DataFrame(rows)


def _microbiome_get_groups(microbiome_dict: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not microbiome_dict:
        return []
    groups = microbiome_dict.get("bacteria_groups")
    if isinstance(groups, list) and groups:
        return groups
    legacy = microbiome_dict.get("bacteria")
    return legacy if isinstance(legacy, list) else []


def _microbiome_summary_dataframe(microbiome_dict: Dict[str, Any]) -> pd.DataFrame:
    if not microbiome_dict:
        return pd.DataFrame()
    
    di = microbiome_dict.get("dysbiosis_index")
    diversity = microbiome_dict.get("diversity")
    groups = _microbiome_get_groups(microbiome_dict)
    
    expected = len([g for g in groups if str(g.get("result", "")).lower().startswith("expected")])
    slight = len([g for g in groups if "slightly" in str(g.get("result", "")).lower()])
    deviating = len([g for g in groups if "deviating" in str(g.get("result", "")).lower() and "slightly" not in str(g.get("result", "")).lower()])
    
    non_ok = [g for g in groups if str(g.get("result", "")).lower() != "expected"]
    top_non_ok = ", ".join([f"{g.get('category','')}" for g in non_ok[:5]]) if non_ok else ""
    
    rows = [
        {"Paramètre": "Indice de dysbiose (DI)", "Valeur": f"{di}/5" if di is not None else "—", "Détail": ""},
        {"Paramètre": "Diversité", "Valeur": diversity or "—", "Détail": ""},
        {"Paramètre": "Groupes attendus", "Valeur": expected, "Détail": ""},
        {"Paramètre": "Groupes légèrement déviants", "Valeur": slight, "Détail": ""},
        {"Paramètre": "Groupes déviants", "Valeur": deviating, "Détail": ""},
    ]
    if top_non_ok:
        rows.append({"Paramètre": "Catégories concernées", "Valeur": top_non_ok, "Détail": ""})
    return pd.DataFrame(rows)


def _extract_biomarkers_for_bfrail(bio_df: pd.DataFrame) -> Dict[str, float]:
    markers = {}
    if bio_df.empty:
        return markers
    
    for _, row in bio_df.iterrows():
        name = str(row.get("Biomarqueur", "")).lower()
        val = _safe_float(row.get("Valeur"))
        
        if val is None:
            continue
        
        if "crp" in name:
            markers['crp'] = val
        elif "hémoglobine" in name or "hemoglobin" in name:
            markers['hemoglobin'] = val
        elif "vitamine d" in name or "vitamin d" in name:
            markers['vitamin_d'] = val
        elif "albumine" in name or "albumin" in name:
            markers['albumin'] = val
    
    return markers


@st.cache_resource
def _get_rules_engine():
    if not os.path.exists(RULES_EXCEL_PATH):
        st.error(f"❌ Fichier de règles introuvable: {RULES_EXCEL_PATH}")
        return None
    try:
        return RulesEngine(RULES_EXCEL_PATH)
    except Exception as e:
        st.error(f"❌ Erreur chargement règles: {e}")
        return None


# =====================================================================
# SESSION STATE
# =====================================================================
def init_session_state():
    defaults = {
        "data_extracted": False,
        "biology_df": pd.DataFrame(),
        "microbiome_data": {},
        "microbiome_df": pd.DataFrame(),
        "microbiome_summary_df": pd.DataFrame(),
        "patient_info": {},
        "consolidated_recommendations": {},
        "cross_analysis": [],
        "follow_up": {},
        "bio_age_result": None,
        "ai_enrichment_active": False,
        "ai_enrichment_output": None
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


# =====================================================================
# STREAMLIT APP
# =====================================================================
st.set_page_config(
    page_title="ALGO-LIFE - Analyse Multimodale",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

init_session_state()

# ─────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
        <div style="background: linear-gradient(135deg, #1a5490 0%, #2d7ab9 100%); 
                    padding: 25px; border-radius: 15px; text-align: center;
                    margin-bottom: 25px; box-shadow: 0 4px 15px rgba(26, 84, 144, 0.3);">
            <h1 style="color: white; margin: 0; font-size: 28px; font-weight: 700; letter-spacing: 2px;">
                UNILABS
            </h1>
            <p style="color: rgba(255,255,255,0.9); margin: 5px 0 0 0; font-size: 12px; letter-spacing: 1px;">
                BIOLOGIE FONCTIONNELLE
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
        <div style="background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%); 
                    padding: 20px; border-radius: 12px; border-left: 4px solid #1a5490; margin-bottom: 20px;">
            <h3 style="color: #1a5490; margin: 0 0 15px 0; font-size: 18px; font-weight: 600;">
                👤 Informations Patient
            </h3>
        </div>
    """, unsafe_allow_html=True)
    
    patient_name = st.text_input("Nom complet", value=st.session_state.patient_info.get("name", ""), placeholder="Ex: Dupont Marie")
    
    col1, col2 = st.columns(2)
    with col1:
        patient_sex = st.selectbox("Sexe", options=["F", "H"], index=0 if st.session_state.patient_info.get("sex", "F") == "F" else 1)
    with col2:
        birthdate_default = st.session_state.patient_info.get("birthdate") or date(1987, 10, 3)
        birthdate = st.date_input("Date de naissance", value=birthdate_default, min_value=date(1920, 1, 1), max_value=date.today(), format="DD/MM/YYYY")
    
    patient_age = _calc_age_from_birthdate(birthdate)
    st.markdown(f"""
        <div style="background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%); 
                    padding: 12px 15px; border-radius: 8px; margin: 10px 0; border-left: 3px solid #2196f3;">
            <p style="margin: 0; color: #1565c0; font-weight: 600; font-size: 15px;">
                📅 Âge : <span style="font-size: 18px;">{patient_age}</span> ans
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        patient_weight = st.number_input("Poids (kg)", min_value=30.0, max_value=200.0, value=70.0, step=0.1, format="%.1f")
    with col2:
        patient_height = st.number_input("Taille (cm)", min_value=100.0, max_value=230.0, value=170.0, step=0.1, format="%.1f")
    
    patient_bmi = _calc_bmi(patient_weight, patient_height)
    if patient_bmi:
        bmi_color = "#22c55e" if 18.5 <= patient_bmi <= 25 else "#f59e0b" if patient_bmi < 18.5 else "#ef4444"
        st.markdown(f"""
            <div style="background: linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 100%); 
                        padding: 12px 15px; border-radius: 8px; margin: 10px 0; border-left: 3px solid {bmi_color};">
                <p style="margin: 0; color: #334155; font-weight: 600; font-size: 15px;">
                    📊 IMC : <span style="color: {bmi_color}; font-size: 18px;">{patient_bmi:.1f}</span> kg/m²
                </p>
            </div>
        """, unsafe_allow_html=True)
    
    patient_antecedents = st.text_area("", value=st.session_state.patient_info.get("antecedents", ""), height=120, 
                                       placeholder="Antécédents / Contexte clinique...", label_visibility="collapsed", key="sidebar_antecedents")
    
    if st.button("💾 Enregistrer les informations", use_container_width=True, type="primary"):
        st.session_state.patient_info = {
            "name": patient_name, "sex": patient_sex, "age": patient_age,
            "birthdate": birthdate, "weight": patient_weight, "height": patient_height,
            "bmi": patient_bmi, "antecedents": patient_antecedents
        }
        st.success("✅ Informations sauvegardées")


# ─────────────────────────────────────────────────────────────────────
# MAIN CONTENT - TABS
# ─────────────────────────────────────────────────────────────────────
st.title("UNILABS - Plateforme d'analyse avancée en biologie et microbiote")

tabs = st.tabs([
    "📥 Import & Données",
    "🔬 Interprétation Multimodale",
    "🔄 Recommandations",
    "📅 Suivi",
    "📄 Export PDF"
])

# ═════════════════════════════════════════════════════════════════════
# TAB 0: IMPORT & DONNÉES
# ═════════════════════════════════════════════════════════════════════
with tabs[0]:
    st.markdown("""
        <div style="background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%); 
                    padding: 25px; border-radius: 15px; border-left: 5px solid #1a5490;
                    margin-bottom: 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.05);">
            <h2 style="color: #1a5490; margin: 0 0 10px 0; font-size: 24px; font-weight: 700;">
                📥 Import des Données
            </h2>
            <p style="color: #64748b; margin: 0; font-size: 14px;">
                Importez vos fichiers PDF ou Excel pour une analyse complète
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2, gap="large")
    
    with col1:
        st.markdown("""
            <div style="background: linear-gradient(135deg, #f0fdfa 0%, #ccfbf1 100%); 
                        padding: 20px; border-radius: 12px; border: 2px solid #14b8a6; margin-bottom: 20px;">
                <h3 style="color: #0f766e; margin: 0 0 15px 0; font-size: 18px; font-weight: 600;">
                    🧪 Biologie
                </h3>
            </div>
        """, unsafe_allow_html=True)
        
        bio_pdf = st.file_uploader("📄 PDF Biologie (SYNLAB/UNILABS)", type=["pdf"], key="bio_pdf")
        bio_excel = st.file_uploader("📊 Excel Biologie (optionnel)", type=["xlsx", "xls"], key="bio_excel")
    
    with col2:
        st.markdown("""
            <div style="background: linear-gradient(135deg, #faf5ff 0%, #f3e8ff 100%); 
                        padding: 20px; border-radius: 12px; border: 2px solid #a855f7; margin-bottom: 20px;">
                <h3 style="color: #7e22ce; margin: 0 0 15px 0; font-size: 18px; font-weight: 600;">
                    🦠 Microbiote
                </h3>
            </div>
        """, unsafe_allow_html=True)
        
        micro_pdf = st.file_uploader("📄 PDF Microbiote (IDK GutMAP)", type=["pdf"], key="micro_pdf")
        micro_excel = st.file_uploader("📊 Excel Microbiote (optionnel)", type=["xlsx", "xls"], key="micro_excel")
    
    if st.button("🚀 Extraire et Analyser", type="primary", use_container_width=True):
        if not bio_pdf and not micro_pdf and not bio_excel and not micro_excel:
            st.error("⚠️ Veuillez uploader au moins un fichier")
        else:
            with st.spinner("⏳ Extraction et analyse en cours..."):
                try:
                    biology_dict = {}
                    microbiome_dict = {}
                    
                    # Extraction biologie
                    if bio_pdf:
                        bio_path = _file_to_temp_path(bio_pdf, ".pdf")
                        biology_dict = extract_synlab_biology(bio_path)
                    
                    if bio_excel:
                        bio_excel_path = _file_to_temp_path(bio_excel, ".xlsx")
                        from extractors import extract_biology_from_excel
                        biology_excel = extract_biology_from_excel(bio_excel_path)
                        biology_dict.update(biology_excel)
                    
                    if biology_dict:
                        st.session_state.biology_df = _dict_bio_to_dataframe(biology_dict)
                    
                    # Extraction microbiome
                    if micro_pdf:
                        micro_path = _file_to_temp_path(micro_pdf, ".pdf")
                        micro_excel_path = _file_to_temp_path(micro_excel, ".xlsx") if micro_excel else None
                        microbiome_dict = extract_idk_microbiome(micro_path, micro_excel_path)
                    elif micro_excel:
                        micro_excel_path = _file_to_temp_path(micro_excel, ".xlsx")
                        microbiome_dict = extract_microbiome_from_excel(micro_excel_path)
                    
                    if microbiome_dict:
                        st.session_state.microbiome_data = microbiome_dict
                        st.session_state.microbiome_summary_df = _microbiome_summary_dataframe(microbiome_dict)
                        bacteria = _microbiome_get_groups(microbiome_dict)
                        st.session_state.microbiome_df = _microbiome_to_dataframe(bacteria)
                    
                    # Génération recommandations
                    engine = _get_rules_engine()
                    if engine:
                        consolidated = engine.generate_consolidated_recommendations(
                            biology_data=st.session_state.biology_df if not st.session_state.biology_df.empty else None,
                            microbiome_data=microbiome_dict if microbiome_dict else None,
                            patient_info=st.session_state.patient_info
                        )
                        st.session_state.consolidated_recommendations = consolidated
                        st.session_state.cross_analysis = consolidated.get("cross_analysis", [])
                    
                    # Calcul âge biologique
                    if not st.session_state.biology_df.empty:
                        markers = _extract_biomarkers_for_bfrail(st.session_state.biology_df)
                        if all(k in markers for k in ['crp', 'hemoglobin', 'vitamin_d']):
                            bfrail_calc = BFrailScore()
                            bfrail_data = BiomarkerData(
                                age=st.session_state.patient_info.get("age", 50),
                                sex=st.session_state.patient_info.get("sex", "F"),
                                crp=markers['crp'],
                                hemoglobin=markers['hemoglobin'],
                                vitamin_d=markers['vitamin_d'],
                                albumin=markers.get('albumin')
                            )
                            st.session_state.bio_age_result = bfrail_calc.calculate(bfrail_data)
                    
                    st.session_state.data_extracted = True
                    st.success("✅ Extraction et analyse terminées !")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ Erreur: {e}")
                    import traceback
                    st.code(traceback.format_exc())
    
    # Affichage données extraites
    if st.session_state.data_extracted:
        st.markdown("---")
        st.subheader("📊 Données Extraites")
        
        if not st.session_state.biology_df.empty:
            st.markdown("### 🧪 Biomarqueurs")
            df = st.session_state.biology_df
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("✅ Normaux", len(df[df["Statut"] == "Normal"]))
            col2.metric("⬇️ Bas", len(df[df["Statut"] == "Bas"]))
            col3.metric("⬆️ Élevés", len(df[df["Statut"] == "Élevé"]))
            col4.metric("❓ Inconnus", len(df[df["Statut"] == "Inconnu"]))
            
            st.dataframe(df, use_container_width=True, height=400)
        
        if not st.session_state.microbiome_summary_df.empty:
            st.markdown("---")
            st.markdown("### 🦠 Microbiote - Résumé")
            st.dataframe(st.session_state.microbiome_summary_df, use_container_width=True, height=240)
        
        if st.session_state.bio_age_result:
            st.markdown("---")
            st.markdown("### 🧬 Âge Biologique")
            result = st.session_state.bio_age_result
            col1, col2, col3 = st.columns(3)
            col1.metric("Âge Biologique", f"{result['bio_age']} ans", 
                       delta=f"{result['bio_age'] - st.session_state.patient_info.get('age', 0):.1f} ans")
            col2.metric("Probabilité de fragilité", f"{result['frailty_probability']}%")
            col3.metric("Catégorie", f"{result['risk_category']}")


# ═════════════════════════════════════════════════════════════════════
# TAB 1: INTERPRÉTATION MULTIMODALE
# ═════════════════════════════════════════════════════════════════════
with tabs[1]:
    st.subheader("🔬 Interprétation Multimodale des Résultats")
    
    if not st.session_state.data_extracted:
        st.warning("⚠️ Veuillez d'abord extraire les données")
    else:
        consolidated = st.session_state.consolidated_recommendations
        
        # ═══════════════════════════════════════════════════════════
        # RÉSUMÉ GLOBAL MULTIMODAL
        # ═══════════════════════════════════════════════════════════
        st.markdown("""
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                        padding: 25px; border-radius: 15px; margin-bottom: 30px;
                        box-shadow: 0 4px 20px rgba(102, 126, 234, 0.3);">
                <h2 style="color: white; margin: 0 0 10px 0; font-size: 24px; font-weight: 700;">
                    📊 Vue d'Ensemble Multimodale
                </h2>
                <p style="color: rgba(255,255,255,0.9); margin: 0; font-size: 14px;">
                    Analyse croisée Biologie × Microbiote
                </p>
            </div>
        """, unsafe_allow_html=True)
        
        summary = consolidated.get("summary", {})
        col1, col2, col3, col4 = st.columns(4)
        
        col1.metric("🔬 Anomalies Bio", summary.get("anomalies_count", 0))
        di_value = st.session_state.microbiome_data.get('dysbiosis_index', '—')
        col2.metric("🦠 Index Dysbiose", f"{di_value}/5" if di_value != '—' else "—")
        col3.metric("⚠️ Signaux Critiques", summary.get("critical_count", 0))
        col4.metric("🔄 Analyses Croisées", len(st.session_state.cross_analysis))
        
        st.markdown("---")
        
        # ═══════════════════════════════════════════════════════════
        # SECTION 1/3 : BIOLOGIE
        # ═══════════════════════════════════════════════════════════
        bio_details = consolidated.get("biology_details", [])
        if bio_details:
            st.markdown("""
                <div style="background: linear-gradient(135deg, #f0fdfa 0%, #ccfbf1 100%); 
                            padding: 20px; border-radius: 12px; border-left: 4px solid #14b8a6; margin: 25px 0;">
                    <h3 style="color: #0f766e; margin: 0 0 10px 0; font-size: 20px; font-weight: 600;">
                        🧪 1/3 - Analyse Biologique
                    </h3>
                </div>
            """, unsafe_allow_html=True)
            
            # Filtres
            filter_col1, filter_col2 = st.columns(2)
            with filter_col1:
                status_filter = st.multiselect("🔍 Filtrer par statut", 
                                              options=["Bas", "Normal", "Élevé", "Inconnu"], 
                                              default=["Bas", "Élevé"], key="bio_status_filter")
            with filter_col2:
                priority_filter = st.multiselect("⚡ Filtrer par priorité",
                                                options=["critical", "high", "medium", "normal"],
                                                default=["critical", "high", "medium"], key="bio_priority_filter")
            
            filtered_bio = [b for b in bio_details if b.get("status") in status_filter and b.get("priority") in priority_filter]
            
            for bio in filtered_bio:
                priority = bio.get('priority')
                
                if priority == 'critical':
                    badge_color, badge_bg, badge_text = "#dc2626", "#fef2f2", "CRITIQUE"
                    border_color, card_bg = "#ef4444", "#fff5f5"
                elif priority == 'high':
                    badge_color, badge_bg, badge_text = "#ea580c", "#fff7ed", "ÉLEVÉ"
                    border_color, card_bg = "#f97316", "#fffbeb"
                elif priority == 'medium':
                    badge_color, badge_bg, badge_text = "#0891b2", "#ecfeff", "MOYEN"
                    border_color, card_bg = "#06b6d4", "#f0fdfa"
                else:
                    badge_color, badge_bg, badge_text = "#059669", "#f0fdf4", "NORMAL"
                    border_color, card_bg = "#10b981", "#f6ffed"
                
                with st.expander(f"{bio.get('biomarker')} - {bio.get('status')} ({bio.get('value')} {bio.get('unit')})",
                                expanded=(priority in ['critical', 'high'])):
                    st.markdown(f"""
                        <div style="margin-bottom: 15px;">
                            <span style="background: {badge_bg}; color: {badge_color}; padding: 6px 16px; 
                                         border-radius: 20px; font-weight: 700; font-size: 12px; display: inline-block;">
                                {badge_text}
                            </span>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    st.markdown(f"""
                        <div style="background: {card_bg}; padding: 15px 20px; border-radius: 10px;
                                    border-left: 4px solid {border_color}; margin-bottom: 15px;">
                            <p style="margin: 0; color: {badge_color}; font-weight: 600; font-size: 14px;">
                                📊 Référence : <span style="font-weight: 700;">{bio.get('reference')}</span>
                            </p>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    if bio.get('interpretation'):
                        st.info(f"💡 {bio.get('interpretation')}")
        
        # ═══════════════════════════════════════════════════════════
        # SECTION 2/3 : MICROBIOTE
        # ═══════════════════════════════════════════════════════════
        micro_details = consolidated.get("microbiome_details", [])
        if micro_details:
            st.markdown("---")
            st.markdown("""
                <div style="background: linear-gradient(135deg, #faf5ff 0%, #f3e8ff 100%); 
                            padding: 20px; border-radius: 12px; border-left: 4px solid #a855f7; margin: 25px 0;">
                    <h3 style="color: #7e22ce; margin: 0 0 10px 0; font-size: 20px; font-weight: 600;">
                        🦠 2/3 - Analyse Microbiote
                    </h3>
                </div>
            """, unsafe_allow_html=True)
            
            deviating = [m for m in micro_details if m.get("severity", 0) > 0]
            
            if not deviating:
                st.success("✅ Tous les groupes bactériens sont dans les normes attendues")
            else:
                for micro in deviating:
                    severity = micro.get("severity", 0)
                    icon = "🔴" if severity >= 2 else "🟠"
                    
                    with st.expander(f"{icon} {micro.get('category')} - {micro.get('group')} ({micro.get('result')})",
                                    expanded=(severity >= 2)):
                        if micro.get('interpretation'):
                            st.info(f"💡 {micro.get('interpretation')}")
        
        # ═══════════════════════════════════════════════════════════
        # SECTION 3/3 : ANALYSES CROISÉES
        # ═══════════════════════════════════════════════════════════
        cross = st.session_state.cross_analysis
        if cross:
            st.markdown("---")
            st.markdown("""
                <div style="background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%); 
                            padding: 20px; border-radius: 12px; border-left: 4px solid #f59e0b; margin: 25px 0;">
                    <h3 style="color: #92400e; margin: 0 0 10px 0; font-size: 20px; font-weight: 600;">
                        🔄 3/3 - Analyses Croisées Multimodales
                    </h3>
                    <p style="color: #78350f; margin: 0; font-size: 14px;">
                        Interactions Biologie × Microbiote
                    </p>
                </div>
            """, unsafe_allow_html=True)
            
            for ca in cross:
                severity = ca.get("severity", "info")
                
                if severity == "critical":
                    badge_bg, badge_color, badge_text = "#fef2f2", "#dc2626", "CRITIQUE"
                    card_bg, border_color = "#fff5f5", "#ef4444"
                elif severity == "warning":
                    badge_bg, badge_color, badge_text = "#fff7ed", "#ea580c", "ATTENTION"
                    card_bg, border_color = "#fffbeb", "#f97316"
                else:
                    badge_bg, badge_color, badge_text = "#eff6ff", "#2563eb", "INFO"
                    card_bg, border_color = "#f0f9ff", "#3b82f6"
                
                with st.expander(f"{ca.get('title')}", expanded=(severity == "critical")):
                    st.markdown(f"""
                        <div style="margin-bottom: 15px;">
                            <span style="background: {badge_bg}; color: {badge_color}; padding: 6px 16px; 
                                         border-radius: 20px; font-weight: 700; font-size: 12px; display: inline-block;">
                                {badge_text}
                            </span>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    st.markdown(f"""
                        <div style="background: {card_bg}; padding: 18px 20px; border-radius: 10px;
                                    border-left: 4px solid {border_color}; margin-bottom: 15px;">
                            <p style="margin: 0; color: #1f2937; line-height: 1.7; font-size: 14px;">
                                {ca.get("description")}
                            </p>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    if ca.get("recommendations"):
                        st.markdown("**💊 Recommandations associées :**")
                        for reco in ca.get("recommendations"):
                            st.markdown(f"• {reco}")


# ═════════════════════════════════════════════════════════════════════
# TAB 2: RECOMMANDATIONS AVEC IA
# ═════════════════════════════════════════════════════════════════════
with tabs[2]:
    st.subheader("💊 Plan Thérapeutique Personnalisé")
    
    if not st.session_state.data_extracted:
        st.warning("⚠️ Veuillez d'abord extraire les données")
    else:
        consolidated = st.session_state.consolidated_recommendations
        recommendations = consolidated.get("recommendations", {})
        
        # ═══════════════════════════════════════════════════════════
        # MODULE IA ENRICHISSEMENT
        # ═══════════════════════════════════════════════════════════
        with st.expander("🤖 Enrichissement IA - Recommandations Précises Nutrition/Micronutrition", expanded=False):
            st.markdown("""
                **L'IA enrichit les recommandations du système de règles avec :**
                - 🥗 **Nutrition précise** : Aliments, quantités, fréquences, timing, mode de cuisson
                - 💊 **Micronutrition experte** : Formes bioactives, dosages suggérés, synergies, timing de prise
                - 🎯 **Personnalisation complète** : Basé sur votre profil (âge, sexe, IMC, biomarqueurs, microbiote)
            """)
            
            col_ai_1, col_ai_2 = st.columns([1, 1])
            with col_ai_1:
                use_ai = st.button("✨ Enrichir avec IA", type="primary", use_container_width=True)
            with col_ai_2:
                reset_ai = st.button("↩️ Revenir aux règles seules", use_container_width=True)
            
            if reset_ai:
                st.session_state.ai_enrichment_output = None
                st.session_state.ai_enrichment_active = False
                st.success("✅ Recommandations : système de règles uniquement")
                st.rerun()
            
            if use_ai:
                try:
                    with st.spinner("⏳ IA en cours d'analyse et d'enrichissement..."):
                        ai_out = ai_enrich_recommendations(
                            patient_info=st.session_state.patient_info,
                            bio_df=st.session_state.biology_df,
                            microbiome_data=st.session_state.microbiome_data,
                            cross_analysis=st.session_state.cross_analysis,
                            existing_reco=recommendations
                        )
                    
                    if not isinstance(ai_out, dict):
                        raise ValueError("Sortie IA invalide")
                    
                    st.session_state.ai_enrichment_output = ai_out
                    st.session_state.ai_enrichment_active = True
                    st.success("✅ IA appliquée : recommandations enrichies générées !")
                    st.rerun()
                
                except Exception as e:
                    st.error(f"❌ Erreur IA : {e}")
                    st.info("💡 Vérifiez que OPENAI_API_KEY est configurée dans les secrets Streamlit")
        
        # ═══════════════════════════════════════════════════════════
        # AFFICHAGE RECOMMANDATIONS
        # ═══════════════════════════════════════════════════════════
        if st.session_state.ai_enrichment_active and st.session_state.ai_enrichment_output:
            # MODE IA ENRICHI
            st.info("🤖 **Mode IA Enrichi activé** : Recommandations personnalisées nutrition/micronutrition")
            
            ai_out = st.session_state.ai_enrichment_output
            
            # Synthèse IA
            if ai_out.get("synthese_enrichie"):
                st.markdown(f"""
                    <div style="background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%); 
                                padding: 20px; border-radius: 12px; border-left: 4px solid #3b82f6; margin: 20px 0;">
                        <h4 style="color: #1e40af; margin: 0 0 10px 0;">📋 Synthèse Personnalisée IA</h4>
                        <p style="color: #1e3a8a; margin: 0; line-height: 1.6;">{ai_out.get("synthese_enrichie")}</p>
                    </div>
                """, unsafe_allow_html=True)
            
            # Contexte appliqué
            if ai_out.get("contexte_applique"):
                st.caption(f"🎯 Personnalisation : {ai_out.get('contexte_applique')}")
            
            st.markdown("---")
            
            # Nutrition enrichie IA
            nutrition_enrichie = ai_out.get("nutrition_enrichie", [])
            if nutrition_enrichie:
                st.markdown("""
                    <div style="background: linear-gradient(135deg, #f0fdf4 0%, #d1fae5 100%); 
                                padding: 20px 25px; border-radius: 12px; border-left: 5px solid #22c55e;
                                margin: 20px 0; box-shadow: 0 4px 15px rgba(34, 197, 94, 0.2);">
                        <h3 style="color: #14532d; margin: 0 0 15px 0; font-size: 20px; font-weight: 700;">
                            🥗 Nutrition Personnalisée (IA)
                        </h3>
                    </div>
                """, unsafe_allow_html=True)
                
                for i, item in enumerate(nutrition_enrichie, 1):
                    st.markdown(f"""
                        <div style="background: white; padding: 15px 20px; border-radius: 10px;
                                    border-left: 4px solid #22c55e; margin: 12px 0;
                                    box-shadow: 0 2px 8px rgba(0,0,0,0.08);">
                            <p style="margin: 0; color: #14532d; font-weight: 500; font-size: 15px;">
                                <strong>{i}.</strong> {item}
                            </p>
                        </div>
                    """, unsafe_allow_html=True)
            
            st.markdown("---")
            
            # Micronutrition enrichie IA
            micronutrition_enrichie = ai_out.get("micronutrition_enrichie", [])
            if micronutrition_enrichie:
                st.markdown("""
                    <div style="background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%); 
                                padding: 20px 25px; border-radius: 12px; border-left: 5px solid #3b82f6;
                                margin: 20px 0; box-shadow: 0 4px 15px rgba(59, 130, 246, 0.2);">
                        <h3 style="color: #1e3a8a; margin: 0 0 15px 0; font-size: 20px; font-weight: 700;">
                            💊 Micronutrition Experte (IA)
                        </h3>
                    </div>
                """, unsafe_allow_html=True)
                
                for i, item in enumerate(micronutrition_enrichie, 1):
                    st.markdown(f"""
                        <div style="background: white; padding: 15px 20px; border-radius: 10px;
                                    border-left: 4px solid #3b82f6; margin: 12px 0;
                                    box-shadow: 0 2px 8px rgba(0,0,0,0.08);">
                            <p style="margin: 0; color: #1e3a8a; font-weight: 500; font-size: 15px;">
                                <strong>{i}.</strong> {item}
                            </p>
                        </div>
                    """, unsafe_allow_html=True)
            
            st.markdown("---")
            st.markdown("### 📋 Recommandations du Système de Règles")
        
        # Afficher recommandations du système de règles
        if not any(recommendations.values()):
            st.info("ℹ️ Aucune recommandation générée par le système de règles")
        else:
            # Prioritaires
            prioritaires = recommendations.get("Prioritaires", [])
            if prioritaires:
                with st.expander("🔥 **Actions Prioritaires**", expanded=True):
                    for i, item in enumerate(prioritaires, 1):
                        st.markdown(f"**{i}.** {item}")
            
            # À surveiller
            a_surveiller = recommendations.get("À surveiller", [])
            if a_surveiller:
                with st.expander("⚠️ **À Surveiller**", expanded=False):
                    for i, item in enumerate(a_surveiller, 1):
                        st.markdown(f"**{i}.** {item}")
            
            # Nutrition (règles)
            nutrition = recommendations.get("Nutrition", [])
            if nutrition:
                with st.expander("🥗 **Nutrition (Règles)**", expanded=False):
                    for item in nutrition:
                        st.markdown(f"• {item}")
            
            # Micronutrition (règles)
            micronutrition = recommendations.get("Micronutrition", [])
            if micronutrition:
                with st.expander("💊 **Micronutrition (Règles)**", expanded=False):
                    for item in micronutrition:
                        st.markdown(f"• {item}")
            
            # Hygiène de vie
            hygiene_vie = recommendations.get("Hygiène de vie", [])
            if hygiene_vie:
                with st.expander("🏃 **Hygiène de Vie**", expanded=False):
                    for item in hygiene_vie:
                        st.markdown(f"• {item}")
            
            # Examens
            examens = recommendations.get("Examens complémentaires", [])
            if examens:
                with st.expander("🔬 **Examens Complémentaires**", expanded=False):
                    for item in examens:
                        st.markdown(f"• {item}")
            
            # Suivi
            suivi = recommendations.get("Suivi", [])
            if suivi:
                with st.expander("📅 **Plan de Suivi**", expanded=False):
                    for item in suivi:
                        st.markdown(f"• {item}")


# ═════════════════════════════════════════════════════════════════════
# TAB 3: SUIVI
# ═════════════════════════════════════════════════════════════════════
with tabs[3]:
    st.subheader("📅 Plan de Suivi")
    
    if not st.session_state.data_extracted:
        st.warning("⚠️ Veuillez d'abord extraire les données")
    else:
        next_date = st.date_input("Date du prochain contrôle", value=date.today(), key="follow_date")
        
        plan = st.text_area("Plan de suivi détaillé", value=st.session_state.follow_up.get("plan", ""),
                           height=150, placeholder="Décrivez le plan...", key="follow_plan")
        
        objectives = st.text_area("Objectifs mesurables", value=st.session_state.follow_up.get("objectives", ""),
                                 height=150, placeholder="Ex: Réduire LDL <1.0 g/L...", key="follow_objectives")
        
        if st.button("💾 Enregistrer le plan", type="primary", use_container_width=True):
            st.session_state.follow_up = {
                "next_date": next_date,
                "plan": plan,
                "objectives": objectives
            }
            st.success("✅ Plan de suivi enregistré")


# ═════════════════════════════════════════════════════════════════════
# TAB 4: EXPORT PDF
# ═════════════════════════════════════════════════════════════════════
with tabs[4]:
    st.subheader("📄 Export Rapport PDF")
    
    if not PDF_EXPORT_AVAILABLE:
        st.error("❌ Module PDF non disponible")
    else:
        if not st.session_state.data_extracted:
            st.warning("⚠️ Générez d'abord une analyse")
        else:
            patient_name_clean = st.session_state.patient_info.get("name", "patient").replace(" ", "_")
            default_filename = f"UNILABS_rapport_{patient_name_clean}_{datetime.now().strftime('%Y%m%d')}.pdf"
            
            pdf_filename = st.text_input("Nom du fichier PDF", value=default_filename)
            
            if st.button("📄 Générer PDF", type="primary", use_container_width=True):
                with st.spinner("⏳ Génération..."):
                    try:
                        out_path = os.path.join(tempfile.gettempdir(), pdf_filename)
                        
                        pdf_path = generate_multimodal_report(
                            patient_data=st.session_state.patient_info,
                            biology_data=st.session_state.biology_df.to_dict('records'),
                            microbiome_data=st.session_state.microbiome_data,
                            recommendations=consolidated.get("recommendations", {}),
                            cross_analysis=st.session_state.cross_analysis,
                            follow_up=st.session_state.follow_up,
                            bio_age_result=st.session_state.bio_age_result,
                            output_path=out_path
                        )
                        
                        with open(pdf_path, "rb") as f:
                            st.download_button("⬇️ Télécharger PDF", data=f.read(),
                                             file_name=pdf_filename, mime="application/pdf",
                                             use_container_width=True)
                        
                        st.success("✅ PDF généré !")
                    
                    except Exception as e:
                        st.error(f"❌ Erreur: {e}")


# ═════════════════════════════════════════════════════════════════════
# FOOTER
# ═════════════════════════════════════════════════════════════════════
st.markdown("---")
st.markdown("""
    <div style="text-align: center; color: #666; padding: 20px;">
        <strong>UNILABS © 2026</strong> | Dr Thibault SUTTER, PhD<br>
        <em>Rapport d'analyse multimodale - Ne remplace pas un avis médical</em>
    </div>
""", unsafe_allow_html=True)
