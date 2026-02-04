"""
UNILABS / ALGO-LIFE - Plateforme Multimodale v11.0
✅ Affichage complet des recommandations dans l'UI
✅ Segmentation claire : Prioritaires, À surveiller, Nutrition, Micronutrition, etc.
✅ Analyses croisées multimodales fonctionnelles
✅ Microbiote robuste
✅ Export PDF cohérent avec l'UI
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
# CONFIGURATION & IMPORTS
# =====================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from extractors import extract_synlab_biology, extract_idk_microbiome
from rules_engine import RulesEngine

# Tentative import PDF generator
try:
    from pdf_generator import generate_multimodal_report
    PDF_EXPORT_AVAILABLE = True
except Exception:
    PDF_EXPORT_AVAILABLE = False

RULES_EXCEL_PATH = os.path.join(BASE_DIR, "data", "Bases_regles_Synlab.xlsx")


# =====================================================================
# BFRAIL SCORE - ÂGE BIOLOGIQUE
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
        bio_age = data.age + (probability - 0.3) * 20
        
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


# =====================================================================
# HELPERS
# =====================================================================
def _file_to_temp_path(uploaded_file, suffix: str) -> str:
    """Sauvegarde un fichier uploadé dans un fichier temporaire"""
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.read())
        return tmp.name


def _safe_float(x) -> Optional[float]:
    """Conversion sécurisée en float"""
    try:
        if x is None:
            return None
        s = str(x).strip().replace(",", ".")
        s = re.sub(r"[^0-9\.\-\+eE]", "", s)
        return float(s) if s else None
    except Exception:
        return None


def _calc_age_from_birthdate(birthdate: date) -> int:
    """Calcule l'âge à partir de la date de naissance"""
    today = date.today()
    age = today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))
    return age


def _calc_bmi(weight_kg: Any, height_cm: Any) -> Optional[float]:
    """Calcule l'IMC"""
    w = _safe_float(weight_kg)
    h = _safe_float(height_cm)
    if w is None or h is None or h <= 0:
        return None
    hm = h / 100.0
    if hm <= 0:
        return None
    return w / (hm * hm)


def _dict_bio_to_dataframe(bio_dict: Dict[str, Any]) -> pd.DataFrame:
    """Convertit dictionnaire biologie en DataFrame"""
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
    """✅ NOUVEAU : Convertit les données bactériennes en DataFrame éditable"""
    if not bacteria:
        return pd.DataFrame()
    
    rows = []
    for b in bacteria:
        rows.append({
            "Catégorie": b.get("category", ""),
            "Groupe": b.get("group", "")[:100],  # Tronquer si trop long
            "Résultat": b.get("result", ""),
            "Abondance": b.get("abundance", "")
        })
    
    return pd.DataFrame(rows)



def _microbiome_get_groups(microbiome_dict: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Compat: anciens extracteurs ('bacteria') vs nouveaux ('bacteria_groups')."""
    if not microbiome_dict:
        return []
    groups = microbiome_dict.get("bacteria_groups")
    if isinstance(groups, list) and groups:
        return groups
    legacy = microbiome_dict.get("bacteria")
    if isinstance(legacy, list) and legacy:
        return legacy
    return []


def _microbiome_get_individual(microbiome_dict: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Bactéries individuelles (si dispo)."""
    if not microbiome_dict:
        return []
    indiv = microbiome_dict.get("bacteria_individual")
    return indiv if isinstance(indiv, list) else []


def _microbiome_summary_dataframe(microbiome_dict: Dict[str, Any]) -> pd.DataFrame:
    """Tableau résumé microbiote (à afficher sous la biologie)."""
    if not microbiome_dict:
        return pd.DataFrame()

    di = microbiome_dict.get("dysbiosis_index")
    diversity = microbiome_dict.get("diversity")

    groups = _microbiome_get_groups(microbiome_dict)
    expected = len([g for g in groups if str(g.get("result","")).lower().startswith("expected")])
    slight = len([g for g in groups if "slightly" in str(g.get("result","")).lower()])
    deviating = len([g for g in groups if "deviating" in str(g.get("result","")).lower() and "slightly" not in str(g.get("result","")).lower()])

    # Top 5 groupes non attendus
    non_ok = [g for g in groups if str(g.get("result","")).lower() != "expected"]
    top_non_ok = ", ".join([f"{g.get('category','')}" for g in non_ok[:5]]) if non_ok else ""

    rows = [
        {"Paramètre": "Indice de dysbiose (DI)", "Valeur": f"{di}/5" if di is not None else "—", "Détail": ""},
        {"Paramètre": "Diversité", "Valeur": diversity or "—", "Détail": ""},
        {"Paramètre": "Groupes attendus", "Valeur": expected, "Détail": ""},
        {"Paramètre": "Groupes légèrement déviants", "Valeur": slight, "Détail": ""},
        {"Paramètre": "Groupes déviants", "Valeur": deviating, "Détail": ""},
    ]
    if top_non_ok:
        rows.append({"Paramètre": "Catégories concernées (top)", "Valeur": top_non_ok, "Détail": "Groupes non attendus"})
    return pd.DataFrame(rows)


def _compute_cross_table(bio_df: pd.DataFrame, microbiome_dict: Dict[str, Any]) -> pd.DataFrame:
    """Petit tableau lisible de signaux croisés Biologie × Microbiote (heuristiques simples)."""
    if bio_df is None or bio_df.empty or not microbiome_dict:
        return pd.DataFrame()

    def _get_val(name_candidates: List[str]) -> Optional[float]:
        for cand in name_candidates:
            mask = bio_df["Biomarqueur"].astype(str).str.lower().str.contains(cand.lower(), na=False)
            if mask.any():
                v = bio_df.loc[mask, "Valeur"].iloc[0]
                try:
                    return float(str(v).replace(",", "."))
                except Exception:
                    return None
        return None

    def _get_status(name_candidates: List[str]) -> Optional[str]:
        for cand in name_candidates:
            mask = bio_df["Biomarqueur"].astype(str).str.lower().str.contains(cand.lower(), na=False)
            if mask.any():
                return str(bio_df.loc[mask, "Statut"].iloc[0])
        return None

    di = microbiome_dict.get("dysbiosis_index")
    diversity = str(microbiome_dict.get("diversity") or "").lower()

    # Flags bio
    crp_status = _get_status(["crp"])
    ferrit_status = _get_status(["ferritin", "ferritine"])
    hb_status = _get_status(["hemoglobin", "hémoglobine", "hemoglobine"])
    vitd_status = _get_status(["vitamin d", "25(oh)", "25-oh", "vit d"])

    flags = []
    if crp_status in ["Élevé", "Elevé", "High", "Haut"]:
        flags.append(("Inflammation", "CRP élevée"))
    if ferrit_status in ["Bas", "Low"] or hb_status in ["Bas", "Low"]:
        flags.append(("Carence martiale", "Ferritine/Hb basses"))
    if vitd_status in ["Bas", "Low"]:
        flags.append(("Hypovitaminose D", "Vitamine D basse"))

    # Micro flags
    micro_flags = []
    if isinstance(di, int) and di >= 3:
        micro_flags.append(("Dysbiose", f"DI {di}/5"))
    if "below" in diversity or "reduced" in diversity:
        micro_flags.append(("Diversité basse", str(microbiome_dict.get("diversity"))))
    if "as expected" in diversity:
        micro_flags.append(("Diversité OK", str(microbiome_dict.get("diversity"))))

    # Build cross rows
    rows = []
    for f in flags:
        if f[0] == "Inflammation" and any(mf[0] == "Dysbiose" for mf in micro_flags):
            rows.append({"Signal croisé": "Inflammation + Dysbiose", "Biologie": f[1], "Microbiote": f"DI={di}/5", "Lecture": "Terrain pro-inflammatoire possiblement entretenu par un déséquilibre du microbiote."})
        if f[0] == "Carence martiale" and (("Diversité basse" in [mf[0] for mf in micro_flags]) or any(mf[0]=="Dysbiose" for mf in micro_flags)):
            rows.append({"Signal croisé": "Carences + Microbiote", "Biologie": f[1], "Microbiote": (f"DI={di}/5" if di else "—"), "Lecture": "À discuter : absorption/terrain digestif (inflammation muqueuse, dysbiose) et apports."})
        if f[0] == "Hypovitaminose D" and any(mf[0] == "Dysbiose" for mf in micro_flags):
            rows.append({"Signal croisé": "Vit D basse + Dysbiose", "Biologie": f[1], "Microbiote": f"DI={di}/5", "Lecture": "Risque immuno-inflammatoire : associer correction Vit D et optimisation microbiote."})

    # fallback: si rien
    if not rows and (flags or micro_flags):
        rows.append({"Signal croisé": "Synthèse", "Biologie": ", ".join([x[1] for x in flags]) or "—", "Microbiote": ", ".join([x[1] for x in micro_flags]) or "—", "Lecture": "Signaux présents mais pas de pattern croisé fort selon les heuristiques simples."})

    return pd.DataFrame(rows)


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


@st.cache_resource
def _get_rules_engine():
    """Charge le moteur de règles (cached)"""
    if not os.path.exists(RULES_EXCEL_PATH):
        st.error(f"❌ Fichier de règles introuvable: {RULES_EXCEL_PATH}")
        return None
    try:
        return RulesEngine(RULES_EXCEL_PATH)
    except Exception as e:
        st.error(f"❌ Erreur chargement règles: {e}")
        return None


# =====================================================================
# SESSION STATE INITIALIZATION
# =====================================================================
def init_session_state():
    """Initialise toutes les variables de session"""
    defaults = {
        "data_extracted": False,
        "biology_df": pd.DataFrame(),
        "microbiome_data": {},
        "microbiome_df": pd.DataFrame(),  # ✅ NOUVEAU : DataFrame pour tableau microbiote
        "microbiome_summary_df": pd.DataFrame(),  # ✅ Résumé microbiote sous biologie
        "cross_table_df": pd.DataFrame(),  # ✅ Tableau de signaux croisés
        "patient_info": {},
        "consolidated_recommendations": {},
        "cross_analysis": [],
        "follow_up": {},
        "bio_age_result": None
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
# SIDEBAR - INFORMATIONS PATIENT
# ─────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://via.placeholder.com/200x80/0A4D8C/FFFFFF?text=UNILABS", use_container_width=True)
    st.title("👤 Informations Patient")
    
    patient_name = st.text_input("Nom du patient", value=st.session_state.patient_info.get("name", ""))
    
    col1, col2 = st.columns(2)
    with col1:
        patient_sex = st.selectbox(
            "Sexe",
            options=["F", "H"],
            index=0 if st.session_state.patient_info.get("sex", "F") == "F" else 1
        )
    with col2:
        birthdate = st.date_input(
            "Date de naissance",
            value=st.session_state.patient_info.get("birthdate") or date(1980, 1, 1),
            min_value=date(1920, 1, 1),
            max_value=date.today()
        )
    
    patient_age = _calc_age_from_birthdate(birthdate)
    st.info(f"📅 Âge: {patient_age} ans")
    
    col1, col2 = st.columns(2)
    with col1:
        patient_weight = st.number_input("Poids (kg)", min_value=30.0, max_value=200.0, value=70.0, step=0.1)
    with col2:
        patient_height = st.number_input("Taille (cm)", min_value=100.0, max_value=230.0, value=170.0, step=0.1)
    
    patient_bmi = _calc_bmi(patient_weight, patient_height)
    if patient_bmi:
        st.info(f"📊 IMC: {patient_bmi:.1f} kg/m²")
    
    patient_antecedents = st.text_area(
        "Antécédents / Contexte clinique",
        value=st.session_state.patient_info.get("antecedents", ""),
        height=100,
        placeholder="Ex: Fatigue chronique, troubles digestifs..."
    )
    
    if st.button("💾 Enregistrer les informations", use_container_width=True):
        st.session_state.patient_info = {
            "name": patient_name,
            "sex": patient_sex,
            "age": patient_age,
            "birthdate": birthdate,
            "weight": patient_weight,
            "height": patient_height,
            "bmi": patient_bmi,
            "antecedents": patient_antecedents
        }
        st.success("✅ Informations sauvegardées")


# ─────────────────────────────────────────────────────────────────────
# MAIN CONTENT - TABS
# ─────────────────────────────────────────────────────────────────────
st.title("🧬 ALGO-LIFE - Analyse Multimodale de Biologie Fonctionnelle")

tabs = st.tabs([
    "📥 Import & Données",
    "🔬 Interprétation",
    "🔄 Recommandations",
    "📅 Suivi",
    "📄 Export PDF"
])

# ═════════════════════════════════════════════════════════════════════
# TAB 0: IMPORT & DONNÉES
# ═════════════════════════════════════════════════════════════════════
with tabs[0]:
    st.subheader("📥 Import des Données")
    
    # Instructions claires
    st.info("""
    **📌 Comment importer vos fichiers :**
    1. Cliquez sur le bouton **"Browse files"** ci-dessous
    2. Parcourez votre ordinateur (Bureau, Documents, Téléchargements, etc.)
    3. Sélectionnez votre fichier PDF ou Excel
    4. Le fichier sera uploadé automatiquement
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🧪 Biologie")
        bio_pdf = st.file_uploader(
            "📄 Cliquez sur 'Browse files' pour sélectionner votre PDF Biologie (SYNLAB/UNILABS)",
            type=["pdf"],
            key="bio_pdf",
            help="Sélectionnez un fichier PDF depuis n'importe quel dossier de votre ordinateur"
        )
        bio_excel = st.file_uploader(
            "📊 Excel Biologie (optionnel)",
            type=["xlsx", "xls"],
            key="bio_excel",
            help="Fichier Excel optionnel pour enrichir les données"
        )
        
        # Afficher le nom du fichier uploadé
        if bio_pdf:
            st.success(f"✅ Fichier biologie chargé : {bio_pdf.name}")
        if bio_excel:
            st.success(f"✅ Excel biologie chargé : {bio_excel.name}")
    
    with col2:
        st.markdown("### 🦠 Microbiote")
        micro_pdf = st.file_uploader(
            "📄 Cliquez sur 'Browse files' pour sélectionner votre PDF Microbiote (IDK GutMAP)",
            type=["pdf"],
            key="micro_pdf",
            help="Sélectionnez un fichier PDF depuis n'importe quel dossier de votre ordinateur"
        )
        micro_excel = st.file_uploader(
            "📊 Excel Microbiote (optionnel)",
            type=["xlsx", "xls"],
            key="micro_excel",
            help="Fichier Excel optionnel pour enrichir les données"
        )
        
        # Afficher le nom du fichier uploadé
        if micro_pdf:
            st.success(f"✅ Fichier microbiote chargé : {micro_pdf.name}")
        if micro_excel:
            st.success(f"✅ Excel microbiote chargé : {micro_excel.name}")
    
    if st.button("🚀 Extraire et Analyser", type="primary", use_container_width=True):
        if not bio_pdf and not micro_pdf:
            st.error("⚠️ Veuillez uploader au moins un fichier (biologie ou microbiote)")
        else:
            with st.spinner("⏳ Extraction et analyse en cours..."):
                try:
                    # Extraction données
                    biology_dict = {}
                    microbiome_dict = {}
                    
                    if bio_pdf:
                        bio_path = _file_to_temp_path(bio_pdf, ".pdf")
                        biology_dict = extract_synlab_biology(bio_path)
                        st.session_state.biology_df = _dict_bio_to_dataframe(biology_dict)
                    
                    if micro_pdf:
                        micro_path = _file_to_temp_path(micro_pdf, ".pdf")
                        micro_excel_path = _file_to_temp_path(micro_excel, ".xlsx") if micro_excel else None
                        microbiome_dict = extract_idk_microbiome(micro_path, micro_excel_path)
                        st.session_state.microbiome_data = microbiome_dict

                        # ✅ NOUVEAU : Tableau résumé microbiote (DI, diversité, groupes)
                        st.session_state.microbiome_summary_df = _microbiome_summary_dataframe(microbiome_dict)
                        
                        # ✅ NOUVEAU : Créer le DataFrame microbiote pour tableau éditable
                        bacteria = _microbiome_get_groups(microbiome_dict)
                        st.session_state.microbiome_df = _microbiome_to_dataframe(bacteria)
                    
                    # Génération des recommandations consolidées
                    engine = _get_rules_engine()
                    if engine:
                        consolidated = engine.generate_consolidated_recommendations(
                            biology_data=st.session_state.biology_df if not st.session_state.biology_df.empty else None,
                            microbiome_data=microbiome_dict if microbiome_dict else None,
                            patient_info=st.session_state.patient_info
                        )
                        st.session_state.consolidated_recommendations = consolidated
                        st.session_state.cross_analysis = consolidated.get("cross_analysis", [])

                        # ✅ NOUVEAU : Tableau de signaux croisés simple (fallback + UI)
                        try:
                            st.session_state.cross_table_df = _compute_cross_table(st.session_state.biology_df, microbiome_dict if microbiome_dict else st.session_state.microbiome_data)
                        except Exception:
                            st.session_state.cross_table_df = pd.DataFrame()
                    
                    # Calcul âge biologique si données disponibles
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
                    st.error(f"❌ Erreur lors de l'extraction: {e}")
                    import traceback
                    st.code(traceback.format_exc())
    
    # Affichage des données extraites
    if st.session_state.data_extracted:
        st.markdown("---")
        st.subheader("📊 Données Extraites")
        
        # Biologie
        if not st.session_state.biology_df.empty:
            st.markdown("### 🧪 Biomarqueurs")
            
            # Résumé
            df = st.session_state.biology_df
            normal_count = len(df[df["Statut"] == "Normal"])
            low_count = len(df[df["Statut"] == "Bas"])
            high_count = len(df[df["Statut"] == "Élevé"])
            unknown_count = len(df[df["Statut"] == "Inconnu"])
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("✅ Normaux", normal_count)
            col2.metric("⬇️ Bas", low_count)
            col3.metric("⬆️ Élevés", high_count)
            col4.metric("❓ Inconnus", unknown_count)
            
            # ✅ NOUVEAU : Tableau ÉDITABLE
            st.info("💡 **Tableau éditable** : Double-cliquez sur une cellule pour modifier les valeurs, unités ou références")
            
            edited_bio_df = st.data_editor(
                df,
                use_container_width=True,
                height=400,
                column_config={
                    "Biomarqueur": st.column_config.TextColumn(
                        "Biomarqueur",
                        width="large",
                        disabled=True  # Nom non modifiable
                    ),
                    "Valeur": st.column_config.NumberColumn(
                        "Valeur",
                        format="%.2f",
                        width="small"
                    ),
                    "Unité": st.column_config.TextColumn(
                        "Unité",
                        width="small"
                    ),
                    "Référence": st.column_config.TextColumn(
                        "Référence",
                        width="medium"
                    ),
                    "Statut": st.column_config.SelectboxColumn(
                        "Statut",
                        options=["Normal", "Bas", "Élevé", "Inconnu"],
                        width="small"
                    )
                },
                num_rows="fixed",
                key="bio_editor"
            )
            
            # Bouton de sauvegarde si modifications détectées
            if not edited_bio_df.equals(st.session_state.biology_df):
                if st.button("💾 Sauvegarder les modifications des biomarqueurs", type="primary", use_container_width=True):
                    st.session_state.biology_df = edited_bio_df
                    st.success("✅ Modifications des biomarqueurs sauvegardées !")
                    st.rerun()
        

        # ✅ NOUVEAU : Résumé Microbiote (affiché sous le tableau biologie)
        if not st.session_state.microbiome_summary_df.empty:
            st.markdown("---")
            st.markdown("### 🦠 Microbiote — Résumé (sous la biologie)")
            st.dataframe(st.session_state.microbiome_summary_df, use_container_width=True, height=240)

        # Microbiote
        if st.session_state.microbiome_data:
            st.markdown("### 🦠 Microbiote")
            micro = st.session_state.microbiome_data
            
            col1, col2 = st.columns(2)
            with col1:
                di = micro.get("dysbiosis_index")
                if di:
                    st.metric("Indice de Dysbiose", f"{di}/5")
            with col2:
                div = micro.get("diversity")
                if div:
                    st.info(f"Diversité: {div}")
            
            bacteria = _microbiome_get_groups(micro)
            if bacteria:
                st.markdown(f"**{len(bacteria)} groupes bactériens analysés**")
                
                # Comptage résultats
                expected = len([b for b in bacteria if b.get("result") == "Expected"])
                slight = len([b for b in bacteria if b.get("result") == "Slightly deviating"])
                deviating = len([b for b in bacteria if b.get("result") == "Deviating"])
                
                col1, col2, col3 = st.columns(3)
                col1.metric("✅ Attendus", expected)
                col2.metric("⚠️ Légèrement déviants", slight)
                col3.metric("🔴 Déviants", deviating)
                
                # ✅ NOUVEAU : Tableau ÉDITABLE des groupes bactériens
                if not st.session_state.microbiome_df.empty:
                    st.markdown("---")
                    st.markdown("#### 🧬 Tableau des Groupes Bactériens")
                    st.info("💡 **Tableau éditable** : Modifiez les résultats et abondances si nécessaire")
                    
                    edited_micro_df = st.data_editor(
                        st.session_state.microbiome_df,
                        use_container_width=True,
                        height=400,
                        column_config={
                            "Catégorie": st.column_config.TextColumn(
                                "Catégorie",
                                width="small",
                                disabled=True
                            ),
                            "Groupe": st.column_config.TextColumn(
                                "Groupe",
                                width="large",
                                disabled=True
                            ),
                            "Résultat": st.column_config.SelectboxColumn(
                                "Résultat",
                                options=["Expected", "Slightly deviating", "Deviating"],
                                width="medium"
                            ),
                            "Abondance": st.column_config.TextColumn(
                                "Abondance",
                                width="small"
                            )
                        },
                        num_rows="fixed",
                        key="micro_editor"
                    )
                    
                    # Bouton de sauvegarde si modifications détectées
                    if not edited_micro_df.equals(st.session_state.microbiome_df):
                        if st.button("💾 Sauvegarder les modifications du microbiote", type="primary", use_container_width=True):
                            st.session_state.microbiome_df = edited_micro_df
                            st.success("✅ Modifications du microbiote sauvegardées !")
                            st.rerun()
        
        # Âge biologique
        if st.session_state.bio_age_result:
            st.markdown("---")
            st.markdown("### 🧬 Âge Biologique (bFRAil Score)")
            
            result = st.session_state.bio_age_result
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    "Âge Biologique",
                    f"{result['bio_age']} ans",
                    delta=f"{result['bio_age'] - st.session_state.patient_info.get('age', 0):.1f} ans"
                )
            with col2:
                st.metric("Probabilité de fragilité", f"{result['frailty_probability']}%")
            with col3:
                color_map = {"green": "🟢", "orange": "🟠", "red": "🔴"}
                st.metric("Catégorie de risque", f"{color_map.get(result['color'], '⚪')} {result['risk_category']}")

# ═════════════════════════════════════════════════════════════════════
# TAB 1: INTERPRÉTATION
# ═════════════════════════════════════════════════════════════════════
with tabs[1]:
    st.subheader("🔬 Interprétation des Résultats")
    
    if not st.session_state.data_extracted:
        st.warning("⚠️ Veuillez d'abord extraire les données dans l'onglet 'Import & Données'")
    else:
        consolidated = st.session_state.consolidated_recommendations
        
        if not consolidated:
            st.info("ℹ️ Aucune interprétation générée")
        else:
            # Résumé global
            summary = consolidated.get("summary", {})
            
            st.markdown("### 📊 Résumé Global")
            col1, col2, col3, col4 = st.columns(4)
            
            col1.metric("Anomalies détectées", summary.get("anomalies_count", 0))
            col2.metric("Paramètres critiques", summary.get("critical_count", 0))
            col3.metric("Dysbiose", summary.get("dysbiosis_level", "Aucune"))
            col4.metric("Recommandations totales", summary.get("total_recommendations", 0))
            
            st.markdown("---")
            
            # Détails biologie
            bio_details = consolidated.get("biology_details", [])
            if bio_details:
                st.markdown("### 🧪 Biologie - Détails")
                
                # Filtres
                filter_col1, filter_col2 = st.columns(2)
                with filter_col1:
                    status_filter = st.multiselect(
                        "Filtrer par statut",
                        options=["Bas", "Normal", "Élevé", "Inconnu"],
                        default=["Bas", "Élevé"]
                    )
                with filter_col2:
                    priority_filter = st.multiselect(
                        "Filtrer par priorité",
                        options=["critical", "high", "medium", "normal"],
                        default=["critical", "high", "medium"]
                    )
                
                # Affichage cartes biomarqueurs
                filtered_bio = [
                    b for b in bio_details
                    if b.get("status") in status_filter and b.get("priority") in priority_filter
                ]
                
                for bio in filtered_bio:
                    with st.expander(
                        f"{'🔴' if bio.get('priority') == 'critical' else '🟠' if bio.get('priority') == 'high' else '🟡' if bio.get('priority') == 'medium' else '🟢'} "
                        f"{bio.get('biomarker')} - {bio.get('status')} ({bio.get('value')} {bio.get('unit')})",
                        expanded=(bio.get('priority') in ['critical', 'high'])
                    ):
                        st.markdown(f"**Référence:** {bio.get('reference')}")
                        
                        if bio.get('interpretation'):
                            st.markdown("**Interprétation:**")
                            st.info(bio.get('interpretation'))
            
            # Microbiote
            micro_details = consolidated.get("microbiome_details", [])
            if micro_details:
                st.markdown("---")
                st.markdown("### 🦠 Microbiote - Détails")
                
                # Groupes déviants seulement
                deviating = [m for m in micro_details if m.get("severity", 0) > 0]
                
                if not deviating:
                    st.success("✅ Tous les groupes bactériens sont dans les normes attendues")
                else:
                    for micro in deviating:
                        severity = micro.get("severity", 0)
                        icon = "🔴" if severity >= 2 else "🟠"
                        
                        with st.expander(
                            f"{icon} {micro.get('category')} - {micro.get('group')} ({micro.get('result')})",
                            expanded=(severity >= 2)
                        ):
                            if micro.get('interpretation'):
                                st.markdown("**Interprétation:**")
                                st.info(micro.get('interpretation'))
            
            # Analyses croisées
            # ✅ Tableau synthèse des signaux croisés
            if isinstance(st.session_state.get("cross_table_df"), pd.DataFrame) and not st.session_state.cross_table_df.empty:
                st.markdown("---")
                st.markdown("### 🔗 Signaux croisés — Tableau synthèse")
                st.dataframe(st.session_state.cross_table_df, use_container_width=True, height=260)

            cross = st.session_state.cross_analysis
            if cross:
                st.markdown("---")
                st.markdown("### 🔄 Analyses Croisées Multimodales")
                
                for ca in cross:
                    severity_icon = {
                        "critical": "🔴",
                        "warning": "🟠",
                        "info": "ℹ️"
                    }.get(ca.get("severity"), "ℹ️")
                    
                    with st.expander(
                        f"{severity_icon} {ca.get('title')}",
                        expanded=(ca.get("severity") == "critical")
                    ):
                        st.markdown(ca.get("description"))
                        
                        if ca.get("recommendations"):
                            st.markdown("**Recommandations associées:**")
                            for reco in ca.get("recommendations"):
                                st.markdown(f"- {reco}")

# ═════════════════════════════════════════════════════════════════════
# TAB 2: RECOMMANDATIONS
# ═════════════════════════════════════════════════════════════════════
with tabs[2]:
    st.subheader("💊 Plan Thérapeutique Personnalisé")
    st.markdown("*Recommandations générées par IA à partir du système de règles*")
    
    if not st.session_state.data_extracted:
        st.warning("⚠️ Veuillez d'abord extraire les données")
    else:
        consolidated = st.session_state.consolidated_recommendations
        recommendations = consolidated.get("recommendations", {})

        # ✅ NOUVEAU : Focus Croisé (Biologie × Microbiote)
        if isinstance(st.session_state.get("cross_table_df"), pd.DataFrame) and not st.session_state.cross_table_df.empty:
            st.markdown("### 🔗 Focus Croisé (Biologie × Microbiote)")
            st.dataframe(st.session_state.cross_table_df, use_container_width=True, height=240)
            st.markdown("---")

        if st.session_state.cross_analysis:
            with st.expander("🔄 Analyses croisées détaillées", expanded=False):
                for ca in st.session_state.cross_analysis:
                    sev = ca.get("severity", "info")
                    icon = {"critical":"🔴","warning":"🟠","info":"ℹ️"}.get(sev, "ℹ️")
                    st.markdown(f"**{icon} {ca.get('title', 'Signal croisé')}**")
                    if ca.get("description"):
                        st.write(ca.get("description"))
                    if ca.get("recommendations"):
                        st.caption("Recommandations associées :")
                        for r in ca.get("recommendations"):
                            st.write(f"• {r}")
                    st.markdown("---")
        
        if not any(recommendations.values()):
            st.info("ℹ️ Aucune recommandation spécifique générée")
        else:
            # ─────────────────────────────────────────────────────────
            # 🔥 PRIORITAIRES
            # ─────────────────────────────────────────────────────────
            prioritaires = recommendations.get("Prioritaires", [])
            if prioritaires:
                st.markdown("### 🔥 Actions Prioritaires")
                with st.container():
                    st.markdown(
                        """
                        <style>
                        .priority-box {
                            background-color: #ffebee;
                            border-left: 4px solid #f44336;
                            padding: 15px;
                            border-radius: 5px;
                            margin-bottom: 10px;
                        }
                        </style>
                        """,
                        unsafe_allow_html=True
                    )
                    for i, item in enumerate(prioritaires, 1):
                        st.markdown(
                            f'<div class="priority-box">🔴 <strong>{i}.</strong> {item}</div>',
                            unsafe_allow_html=True
                        )
                st.markdown("---")
            
            # ─────────────────────────────────────────────────────────
            # ⚠️ À SURVEILLER
            # ─────────────────────────────────────────────────────────
            a_surveiller = recommendations.get("À surveiller", [])
            if a_surveiller:
                with st.expander("⚠️ **À Surveiller**", expanded=True):
                    for i, item in enumerate(a_surveiller, 1):
                        st.markdown(f"**{i}.** {item}")
                st.markdown("---")
            
            # ─────────────────────────────────────────────────────────
            # 🥗 NUTRITION
            # ─────────────────────────────────────────────────────────
            nutrition = recommendations.get("Nutrition", [])
            if nutrition:
                with st.expander("🥗 **Nutrition & Diététique**", expanded=True):
                    st.markdown(
                        """
                        <div style="background-color: #f1f8e9; padding: 15px; border-radius: 5px; border-left: 4px solid #8bc34a;">
                        """,
                        unsafe_allow_html=True
                    )
                    for i, item in enumerate(nutrition, 1):
                        st.markdown(f"• {item}")
                    st.markdown("</div>", unsafe_allow_html=True)
                st.markdown("---")
            
            # ─────────────────────────────────────────────────────────
            # 💊 MICRONUTRITION
            # ─────────────────────────────────────────────────────────
            micronutrition = recommendations.get("Micronutrition", [])
            if micronutrition:
                with st.expander("💊 **Micronutrition**", expanded=True):
                    st.markdown(
                        """
                        <div style="background-color: #e3f2fd; padding: 15px; border-radius: 5px; border-left: 4px solid #2196f3;">
                        """,
                        unsafe_allow_html=True
                    )
                    for i, item in enumerate(micronutrition, 1):
                        st.markdown(f"• {item}")
                    st.markdown("</div>", unsafe_allow_html=True)
                st.markdown("---")
            
            # ─────────────────────────────────────────────────────────
            # 🏃 HYGIÈNE DE VIE
            # ─────────────────────────────────────────────────────────
            hygiene_vie = recommendations.get("Hygiène de vie", [])
            if hygiene_vie:
                with st.expander("🏃 **Hygiène de Vie**", expanded=True):
                    st.markdown(
                        """
                        <div style="background-color: #fff3e0; padding: 15px; border-radius: 5px; border-left: 4px solid #ff9800;">
                        """,
                        unsafe_allow_html=True
                    )
                    for i, item in enumerate(hygiene_vie, 1):
                        st.markdown(f"• {item}")
                    st.markdown("</div>", unsafe_allow_html=True)
                st.markdown("---")
            
            # ─────────────────────────────────────────────────────────
            # 🔬 EXAMENS COMPLÉMENTAIRES
            # ─────────────────────────────────────────────────────────
            examens = recommendations.get("Examens complémentaires", [])
            if examens:
                with st.expander("🔬 **Examens Complémentaires**", expanded=False):
                    for i, item in enumerate(examens, 1):
                        st.markdown(f"**{i}.** {item}")
                st.markdown("---")
            
            # ─────────────────────────────────────────────────────────
            # 📅 SUIVI
            # ─────────────────────────────────────────────────────────
            suivi = recommendations.get("Suivi", [])
            if suivi:
                with st.expander("📅 **Plan de Suivi**", expanded=False):
                    for i, item in enumerate(suivi, 1):
                        st.markdown(f"**{i}.** {item}")
            
            # ─────────────────────────────────────────────────────────
            # ÉDITION DES RECOMMANDATIONS
            # ─────────────────────────────────────────────────────────
            st.markdown("---")
            st.markdown("### ✏️ Édition des Recommandations")
            
            edit_section = st.selectbox(
                "Sélectionner une section à modifier",
                options=list(recommendations.keys())
            )
            
            if edit_section:
                current_items = recommendations.get(edit_section, [])
                edited_text = st.text_area(
                    f"Modifier {edit_section} (une recommandation par ligne)",
                    value="\n".join(current_items),
                    height=200
                )
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("💾 Sauvegarder les modifications", use_container_width=True):
                        new_items = [line.strip() for line in edited_text.split("\n") if line.strip()]
                        st.session_state.consolidated_recommendations["recommendations"][edit_section] = new_items
                        st.success("✅ Modifications sauvegardées")
                        st.rerun()
                
                with col2:
                    if st.button("➕ Ajouter une nouvelle recommandation", use_container_width=True):
                        new_reco = st.text_input("Nouvelle recommandation")
                        if new_reco:
                            recommendations[edit_section].append(new_reco)
                            st.success("✅ Recommandation ajoutée")
                            st.rerun()

# ═════════════════════════════════════════════════════════════════════
# TAB 3: SUIVI
# ═════════════════════════════════════════════════════════════════════
with tabs[3]:
    st.subheader("📅 Plan de Suivi")
    
    if not st.session_state.data_extracted:
        st.warning("⚠️ Veuillez d'abord extraire les données")
    else:
        # Date prochain contrôle
        next_date = st.date_input(
            "Date du prochain contrôle",
            value=st.session_state.follow_up.get("next_date") or date.today(),
            key="follow_date"
        )
        
        # Biomarqueurs à recontrôler
        engine = _get_rules_engine()
        if engine:
            all_biomarkers = engine.list_all_biomarkers()
            
            # Suggestion automatique des biomarqueurs anormaux
            suggested = []
            if not st.session_state.biology_df.empty:
                for _, row in st.session_state.biology_df.iterrows():
                    if row.get("Statut") in ["Bas", "Élevé"]:
                        biomarker = row.get("Biomarqueur")
                        if biomarker:
                            suggested.append(biomarker)
            
            prev_tests = st.session_state.follow_up.get("next_tests", [])
            if isinstance(prev_tests, str):
                prev_tests = [x.strip() for x in prev_tests.split(",") if x.strip()]
            
            # Combiner suggestions et sélection précédente
            default_tests = list(set(suggested + prev_tests))
            
            next_tests_list = st.multiselect(
                "Biomarqueurs à recontrôler",
                options=all_biomarkers,
                default=[t for t in default_tests if t in all_biomarkers],
                key="follow_tests"
            )
        else:
            next_tests_list = []
            st.warning("⚠️ Moteur de règles non disponible")
        
        # Ajout manuel
        manual_add = st.text_input(
            "Ajouter un biomarqueur (manuel)",
            placeholder="Ex: Homocystéine, DAO, LBP...",
            key="follow_manual_add"
        )
        if manual_add.strip() and manual_add.strip() not in next_tests_list:
            next_tests_list.append(manual_add.strip())
        
        # Plan de suivi
        plan = st.text_area(
            "Plan de suivi détaillé",
            value=st.session_state.follow_up.get("plan", ""),
            height=150,
            key="follow_plan",
            placeholder="Décrivez le plan de suivi personnalisé..."
        )
        
        # Objectifs mesurables
        objectives = st.text_area(
            "Objectifs mesurables",
            value=st.session_state.follow_up.get("objectives", ""),
            height=150,
            key="follow_objectives",
            placeholder="Ex: Réduire LDL <1.0 g/L, Augmenter Vitamine D >40 ng/mL..."
        )
        
        # Notes internes
        clinician_notes = st.text_area(
            "Notes internes (confidentielles)",
            value=st.session_state.follow_up.get("clinician_notes", ""),
            height=100,
            key="follow_notes",
            placeholder="Notes pour le praticien..."
        )
        
        if st.button("💾 Enregistrer le plan de suivi", type="primary", use_container_width=True):
            st.session_state.follow_up = {
                "next_date": next_date,
                "next_tests": next_tests_list,
                "plan": plan,
                "objectives": objectives,
                "clinician_notes": clinician_notes
            }
            st.success("✅ Plan de suivi enregistré")
        
        # Affichage récapitulatif
        if st.session_state.follow_up:
            st.markdown("---")
            st.markdown("### 📋 Récapitulatif du Suivi")
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Prochain contrôle", next_date.strftime("%d/%m/%Y"))
            with col2:
                st.metric("Biomarqueurs à recontrôler", len(next_tests_list))
            
            if next_tests_list:
                with st.expander("🔬 Liste des biomarqueurs"):
                    for test in next_tests_list:
                        st.markdown(f"• {test}")

# ═════════════════════════════════════════════════════════════════════
# TAB 4: EXPORT PDF
# ═════════════════════════════════════════════════════════════════════
with tabs[4]:
    st.subheader("📄 Export Rapport PDF")
    
    if not PDF_EXPORT_AVAILABLE:
        st.error("❌ Module d'export PDF non disponible")
        st.info("Vérifiez que pdf_generator.py est présent et configuré correctement")
    else:
        if not st.session_state.data_extracted:
            st.warning("⚠️ Générez d'abord une analyse dans l'onglet 'Import & Données'")
        else:
            # Nom fichier
            patient_name_clean = st.session_state.patient_info.get("name", "patient").replace(" ", "_")
            default_filename = f"UNILABS_rapport_{patient_name_clean}_{datetime.now().strftime('%Y%m%d')}.pdf"
            
            pdf_filename = st.text_input(
                "Nom du fichier PDF",
                value=default_filename
            )
            
            # Options PDF
            st.markdown("### ⚙️ Options du Rapport")
            
            col1, col2 = st.columns(2)
            with col1:
                include_biology = st.checkbox("Inclure biologie détaillée", value=True)
                include_microbiome = st.checkbox("Inclure microbiome détaillé", value=True)
            with col2:
                include_cross = st.checkbox("Inclure analyses croisées", value=True)
                include_recommendations = st.checkbox("Inclure recommandations", value=True)
            
            # Génération
            if st.button("📄 Générer le Rapport PDF", type="primary", use_container_width=True):
                with st.spinner("⏳ Génération du rapport en cours..."):
                    try:
                        # Préparer les données
                        patient_data = st.session_state.patient_info
                        biology_data = st.session_state.biology_df.to_dict('records') if not st.session_state.biology_df.empty else []
                        microbiome_data = st.session_state.microbiome_data
                        consolidated = st.session_state.consolidated_recommendations
                        
                        # Filtrer selon les options
                        if not include_biology:
                            biology_data = []
                        if not include_microbiome:
                            microbiome_data = {}
                        if not include_cross:
                            consolidated["cross_analysis"] = []
                        if not include_recommendations:
                            consolidated["recommendations"] = {}
                        
                        # Générer PDF
                        out_path = os.path.join(tempfile.gettempdir(), pdf_filename)
                        
                        pdf_path = generate_multimodal_report(
                            patient_data=patient_data,
                            biology_data=biology_data,
                            microbiome_data=microbiome_data,
                            recommendations=consolidated.get("recommendations", {}),
                            cross_analysis=consolidated.get("cross_analysis", []),
                            follow_up=st.session_state.follow_up,
                            bio_age_result=st.session_state.bio_age_result,
                            output_path=out_path
                        )
                        
                        # Téléchargement
                        with open(pdf_path, "rb") as f:
                            pdf_bytes = f.read()
                            st.download_button(
                                "⬇️ Télécharger le Rapport PDF",
                                data=pdf_bytes,
                                file_name=pdf_filename,
                                mime="application/pdf",
                                use_container_width=True
                            )
                        
                        st.success("✅ Rapport PDF généré avec succès !")
                        
                        # Prévisualisation (optionnel)
                        with st.expander("👁️ Prévisualiser le PDF"):
                            import base64
                            base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
                            pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800" type="application/pdf"></iframe>'
                            st.markdown(pdf_display, unsafe_allow_html=True)
                        
                    except Exception as e:
                        st.error(f"❌ Erreur lors de la génération du PDF: {e}")
                        import traceback
                        with st.expander("🐛 Détails de l'erreur"):
                            st.code(traceback.format_exc())


# ═════════════════════════════════════════════════════════════════════
# FOOTER
# ═════════════════════════════════════════════════════════════════════
st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; color: #666; padding: 20px;">
        <strong>ALGO-LIFE © 2026</strong> | Powered by UNILABS Group<br>
        Dr Thibault SUTTER, PhD - Biologiste spécialisé en biologie fonctionnelle<br>
        <em>Ce rapport est généré automatiquement par analyse multimodale IA.</em><br>
        <em>Il ne remplace pas un avis médical personnalisé.</em>
    </div>
    """,
    unsafe_allow_html=True
)
