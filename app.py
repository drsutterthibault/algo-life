"""
UNILABS / ALGO-LIFE - Plateforme Multimodale v12.0
✅ Tableau microbiote éditable dans Import & Données
✅ Édition des biomarqueurs (valeurs, unités, références)
✅ Édition des recommandations (Nutrition, Micronutrition, Lifestyle)
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
    from pdf_generator_visual import generate_multimodal_report
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
        
        frailty_prob = (np.exp(linear_score) / (1 + np.exp(linear_score))) * 100
        
        bio_age = data.age + (linear_score * 2)
        
        if frailty_prob < 15:
            risk_category = "Faible"
            color = "green"
        elif frailty_prob < 30:
            risk_category = "Modéré"
            color = "orange"
        else:
            risk_category = "Élevé"
            color = "red"
        
        return {
            "bio_age": round(bio_age, 1),
            "frailty_probability": round(frailty_prob, 1),
            "linear_score": round(linear_score, 2),
            "risk_category": risk_category,
            "color": color
        }


# =====================================================================
# HELPER FUNCTIONS
# =====================================================================
def _file_to_temp_path(uploaded_file, ext: str) -> Optional[str]:
    """Sauvegarde un fichier uploadé dans un fichier temporaire"""
    if uploaded_file is None:
        return None
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp_file:
        tmp_file.write(uploaded_file.read())
        return tmp_file.name


def _dict_bio_to_dataframe(bio_dict: Dict) -> pd.DataFrame:
    """Convertit dict biomarqueurs en DataFrame"""
    if not bio_dict:
        return pd.DataFrame()
    
    rows = []
    for name, data in bio_dict.items():
        rows.append({
            "Biomarqueur": name,
            "Valeur": data.get("value", ""),
            "Unité": data.get("unit", ""),
            "Référence": data.get("reference", ""),
            "Statut": data.get("status", "Inconnu")
        })
    
    return pd.DataFrame(rows)


def _microbiome_to_dataframe(bacteria: List[Dict]) -> pd.DataFrame:
    """Convertit les données bactériennes en DataFrame"""
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


@st.cache_resource
def _get_rules_engine():
    """Charge le moteur de règles (cached)"""
    if not os.path.exists(RULES_EXCEL_PATH):
        return None
    try:
        return RulesEngine(RULES_EXCEL_PATH)
    except Exception:
        return None


def _extract_biomarkers_for_bfrail(df: pd.DataFrame) -> Dict:
    """Extrait les biomarqueurs nécessaires pour bFRAil"""
    markers = {}
    
    for _, row in df.iterrows():
        name = row["Biomarqueur"].lower()
        try:
            value = float(row["Valeur"])
        except:
            continue
        
        if "crp" in name and "ultrasensible" in name:
            markers['crp'] = value
        elif "hémoglobine" in name or "hemoglobin" in name:
            markers['hemoglobin'] = value
        elif "vitamine d" in name or "vitamin d" in name:
            markers['vitamin_d'] = value
        elif "albumine" in name or "albumin" in name:
            markers['albumin'] = value
    
    return markers


# =====================================================================
# SESSION STATE INITIALIZATION
# =====================================================================
if "biology_df" not in st.session_state:
    st.session_state.biology_df = pd.DataFrame()

if "microbiome_data" not in st.session_state:
    st.session_state.microbiome_data = {}

if "microbiome_df" not in st.session_state:
    st.session_state.microbiome_df = pd.DataFrame()

if "consolidated_recommendations" not in st.session_state:
    st.session_state.consolidated_recommendations = {}

if "cross_analysis" not in st.session_state:
    st.session_state.cross_analysis = []

if "data_extracted" not in st.session_state:
    st.session_state.data_extracted = False

if "patient_info" not in st.session_state:
    st.session_state.patient_info = {
        "name": "",
        "age": 50,
        "sex": "F",
        "context": ""
    }

if "follow_up" not in st.session_state:
    st.session_state.follow_up = {
        "next_date": "",
        "next_tests": [],
        "objectives": ""
    }

if "bio_age_result" not in st.session_state:
    st.session_state.bio_age_result = None


# =====================================================================
# PAGE CONFIG
# =====================================================================
st.set_page_config(
    page_title="ALGO-LIFE | UNILABS",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =====================================================================
# SIDEBAR - INFORMATIONS PATIENT
# =====================================================================
with st.sidebar:
    st.title("🧬 ALGO-LIFE")
    st.caption("Powered by UNILABS")
    st.markdown("---")
    
    st.subheader("👤 Informations Patient")
    
    st.session_state.patient_info["name"] = st.text_input(
        "Nom complet",
        value=st.session_state.patient_info.get("name", "")
    )
    
    col1, col2 = st.columns(2)
    with col1:
        st.session_state.patient_info["age"] = st.number_input(
            "Âge",
            min_value=1,
            max_value=120,
            value=st.session_state.patient_info.get("age", 50)
        )
    with col2:
        st.session_state.patient_info["sex"] = st.selectbox(
            "Sexe",
            options=["F", "M"],
            index=0 if st.session_state.patient_info.get("sex") == "F" else 1
        )
    
    st.session_state.patient_info["context"] = st.text_area(
        "Contexte clinique",
        value=st.session_state.patient_info.get("context", ""),
        height=100,
        placeholder="Symptômes, antécédents, traitements..."
    )
    
    st.markdown("---")
    st.caption("Dr Thibault SUTTER, PhD")
    st.caption("Biologiste - UNILABS Group")


# =====================================================================
# MAIN TABS
# =====================================================================
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
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🧪 Biologie")
        bio_pdf = st.file_uploader(
            "PDF Biologie (SYNLAB/UNILABS)",
            type=["pdf"],
            key="bio_pdf"
        )
        bio_excel = st.file_uploader(
            "Excel Biologie (optionnel)",
            type=["xlsx", "xls"],
            key="bio_excel"
        )
    
    with col2:
        st.markdown("### 🦠 Microbiote")
        micro_pdf = st.file_uploader(
            "PDF Microbiote (IDK GutMAP)",
            type=["pdf"],
            key="micro_pdf"
        )
        micro_excel = st.file_uploader(
            "Excel Microbiote (optionnel)",
            type=["xlsx", "xls"],
            key="micro_excel"
        )
    
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
                        
                        # Créer DataFrame microbiote
                        bacteria = microbiome_dict.get("bacteria", [])
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
        
        # ─────────────────────────────────────────────────────────────
        # BIOLOGIE - TABLEAU ÉDITABLE
        # ─────────────────────────────────────────────────────────────
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
            
            st.info("💡 **Tableau éditable** : Cliquez sur une cellule pour modifier les valeurs, unités ou références")
            
            # Tableau ÉDITABLE
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
            
            # Sauvegarder les modifications
            if not edited_bio_df.equals(st.session_state.biology_df):
                if st.button("💾 Sauvegarder les modifications des biomarqueurs", key="save_bio"):
                    st.session_state.biology_df = edited_bio_df
                    st.success("✅ Modifications sauvegardées !")
                    st.rerun()
        
        # ─────────────────────────────────────────────────────────────
        # MICROBIOTE - TABLEAU ÉDITABLE
        # ─────────────────────────────────────────────────────────────
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
            
            # NOUVEAU : Tableau des souches bactériennes
            if not st.session_state.microbiome_df.empty:
                st.markdown("#### 🧬 Groupes Bactériens")
                
                df_micro = st.session_state.microbiome_df
                
                # Comptage résultats
                expected = len(df_micro[df_micro["Résultat"] == "Expected"])
                slight = len(df_micro[df_micro["Résultat"].str.contains("Slightly", na=False)])
                deviating = len(df_micro[df_micro["Résultat"] == "Deviating"])
                
                col1, col2, col3 = st.columns(3)
                col1.metric("✅ Attendus", expected)
                col2.metric("⚠️ Légèrement déviants", slight)
                col3.metric("🔴 Déviants", deviating)
                
                st.info("💡 **Tableau éditable** : Modifiez les résultats et abondances si nécessaire")
                
                # Tableau ÉDITABLE du microbiote
                edited_micro_df = st.data_editor(
                    df_micro,
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
                
                # Sauvegarder les modifications
                if not edited_micro_df.equals(st.session_state.microbiome_df):
                    if st.button("💾 Sauvegarder les modifications du microbiote", key="save_micro"):
                        st.session_state.microbiome_df = edited_micro_df
                        st.success("✅ Modifications sauvegardées !")
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
# TAB 1: INTERPRÉTATION (conservé tel quel pour l'instant)
# ═════════════════════════════════════════════════════════════════════
with tabs[1]:
    st.subheader("🔬 Interprétation des Résultats")
    
    if not st.session_state.data_extracted:
        st.warning("⚠️ Veuillez d'abord extraire les données dans l'onglet 'Import & Données'")
    else:
        st.info("Cette section sera développée dans la prochaine version")

# ═════════════════════════════════════════════════════════════════════
# TAB 2: RECOMMANDATIONS - ÉDITABLES
# ═════════════════════════════════════════════════════════════════════
with tabs[2]:
    st.subheader("🔄 Recommandations Personnalisées")
    
    if not st.session_state.data_extracted:
        st.warning("⚠️ Veuillez d'abord extraire les données dans l'onglet 'Import & Données'")
    else:
        consolidated = st.session_state.consolidated_recommendations
        recommendations = consolidated.get("recommendations", {})
        
        if not recommendations:
            st.info("Aucune recommandation générée")
        else:
            st.info("💡 **Recommandations éditables** : Modifiez le texte directement dans les zones ci-dessous")
            
            # ─────────────────────────────────────────────────────────
            # NUTRITION - ÉDITABLE
            # ─────────────────────────────────────────────────────────
            nutrition_items = recommendations.get("Nutrition", [])
            if nutrition_items:
                st.markdown("### 🥗 Nutrition")
                nutrition_text = "\n".join([f"• {item}" for item in nutrition_items])
                
                edited_nutrition = st.text_area(
                    "Recommandations nutritionnelles",
                    value=nutrition_text,
                    height=200,
                    key="nutrition_editor"
                )
                
                if st.button("💾 Sauvegarder Nutrition", key="save_nutrition"):
                    # Convertir le texte en liste
                    new_items = [line.strip("• ").strip() for line in edited_nutrition.split("\n") if line.strip()]
                    st.session_state.consolidated_recommendations["recommendations"]["Nutrition"] = new_items
                    st.success("✅ Recommandations nutritionnelles sauvegardées !")
                    st.rerun()
            
            # ─────────────────────────────────────────────────────────
            # MICRONUTRITION - ÉDITABLE
            # ─────────────────────────────────────────────────────────
            micronutrition_items = recommendations.get("Micronutrition", [])
            if micronutrition_items:
                st.markdown("### 💊 Micronutrition")
                micronutrition_text = "\n".join([f"• {item}" for item in micronutrition_items])
                
                edited_micronutrition = st.text_area(
                    "Recommandations en micronutrition",
                    value=micronutrition_text,
                    height=200,
                    key="micronutrition_editor"
                )
                
                if st.button("💾 Sauvegarder Micronutrition", key="save_micronutrition"):
                    new_items = [line.strip("• ").strip() for line in edited_micronutrition.split("\n") if line.strip()]
                    st.session_state.consolidated_recommendations["recommendations"]["Micronutrition"] = new_items
                    st.success("✅ Recommandations en micronutrition sauvegardées !")
                    st.rerun()
            
            # ─────────────────────────────────────────────────────────
            # HYGIÈNE DE VIE - ÉDITABLE
            # ─────────────────────────────────────────────────────────
            lifestyle_items = recommendations.get("Hygiène de vie", [])
            if lifestyle_items:
                st.markdown("### 🏃 Hygiène de Vie")
                lifestyle_text = "\n".join([f"• {item}" for item in lifestyle_items])
                
                edited_lifestyle = st.text_area(
                    "Recommandations d'hygiène de vie",
                    value=lifestyle_text,
                    height=200,
                    key="lifestyle_editor"
                )
                
                if st.button("💾 Sauvegarder Hygiène de Vie", key="save_lifestyle"):
                    new_items = [line.strip("• ").strip() for line in edited_lifestyle.split("\n") if line.strip()]
                    st.session_state.consolidated_recommendations["recommendations"]["Hygiène de vie"] = new_items
                    st.success("✅ Recommandations d'hygiène de vie sauvegardées !")
                    st.rerun()
            
            # Afficher les autres sections (non éditables pour l'instant)
            st.markdown("---")
            other_sections = ["Prioritaires", "À surveiller", "Examens complémentaires", "Suivi"]
            for section in other_sections:
                items = recommendations.get(section, [])
                if items:
                    icon_map = {
                        "Prioritaires": "🔥",
                        "À surveiller": "⚠️",
                        "Examens complémentaires": "🔬",
                        "Suivi": "📅"
                    }
                    st.markdown(f"### {icon_map.get(section, '📋')} {section}")
                    for item in items:
                        st.markdown(f"• {item}")

# ═════════════════════════════════════════════════════════════════════
# TAB 3: SUIVI (conservé tel quel)
# ═════════════════════════════════════════════════════════════════════
with tabs[3]:
    st.subheader("📅 Plan de Suivi")
    
    if not st.session_state.data_extracted:
        st.warning("⚠️ Veuillez d'abord extraire les données dans l'onglet 'Import & Données'")
    else:
        st.info("Cette section sera développée dans la prochaine version")

# ═════════════════════════════════════════════════════════════════════
# TAB 4: EXPORT PDF (conservé tel quel)
# ═════════════════════════════════════════════════════════════════════
with tabs[4]:
    st.subheader("📄 Export PDF")
    
    if not st.session_state.data_extracted:
        st.warning("⚠️ Veuillez d'abord extraire les données dans l'onglet 'Import & Données'")
    else:
        st.info("L'export PDF utilisera les données modifiées dans les tableaux éditables")
        
        if st.button("📥 Générer le Rapport PDF", type="primary", use_container_width=True):
            st.info("Export PDF en cours de développement avec le nouveau générateur visuel")
