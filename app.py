"""
UNILABS / ALGO-LIFE - Plateforme Multimodale AMÉLIORÉE
✅ Templates modernes pour biologie et microbiote
✅ Tableaux symétriques (pas de résumé dysbiosis/diversity)
✅ Édition manuelle des interprétations
✅ Analyse croisée auto-remplie
"""

from __future__ import annotations

import os
import sys
import re
import tempfile
from datetime import datetime, date
from typing import Dict, Any, Optional, List

import pandas as pd
import streamlit as st

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
    """Convertit le dict biologie en DataFrame avec colonnes standardisées"""
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
            "Interprétation": ""  # Sera rempli manuellement ou auto
        })

    df = pd.DataFrame(rows)
    if not df.empty:
        df["Valeur"] = df["Valeur"].apply(_safe_float)
    return df


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
        "antecedents": patient.get("antecedents", ""),
    }

    biology_data = st.session_state.biology_data or {}
    microbiome_data = st.session_state.microbiome_data or {}

    recos = st.session_state.recommendations or {}
    
    # Analyse croisée depuis session state (éditable)
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


def _generate_cross_analysis(biology_df: pd.DataFrame, microbiome_data: Dict[str, Any]) -> Dict[str, List[str]]:
    """Génère automatiquement l'analyse croisée à partir des données"""
    observations = []
    actions = []
    
    if biology_df is None or biology_df.empty:
        return {"observations": observations, "actions": actions}
    
    # Analyser les biomarqueurs anormaux
    abnormal_markers = biology_df[biology_df["Statut"].str.contains("Élevé|Bas|Critique", case=False, na=False)]
    
    dysbiosis_index = microbiome_data.get("dysbiosis_index", 0) if microbiome_data else 0
    
    # Observations basées sur biologie
    if not abnormal_markers.empty:
        for _, row in abnormal_markers.head(3).iterrows():
            marker = row["Biomarqueur"]
            status = row["Statut"]
            
            if "Glucose" in marker and "Élevé" in status:
                observations.append(f"Glucose {status.lower()} détecté - Potentiel impact sur l'équilibre du microbiote")
                if dysbiosis_index > 2:
                    observations.append("Corrélation possible entre hyperglycémie et dysbiose intestinale")
                    actions.append({
                        "text": "Optimiser l'équilibre glycémique par l'alimentation et soutenir le microbiote",
                        "priority": "high"
                    })
            
            elif "Cholestérol" in marker or "LDL" in marker:
                observations.append(f"{marker} {status.lower()} - Impact possible sur inflammation systémique")
                actions.append({
                    "text": "Optimiser le profil lipidique via nutrition et oméga-3",
                    "priority": "medium"
                })
            
            elif "Vitamine D" in marker and "Bas" in status:
                observations.append("Déficit en vitamine D détecté - Impact sur immunité et barrière intestinale")
                actions.append({
                    "text": "Corriger le déficit en vitamine D (4000 UI/jour pendant 3 mois)",
                    "priority": "high"
                })
            
            elif "Ferritine" in marker and "Bas" in status:
                observations.append("Ferritine basse - Peut affecter l'énergie et l'absorption intestinale")
                actions.append({
                    "text": "Évaluer les causes du déficit en fer et supplémenter si nécessaire",
                    "priority": "medium"
                })
    
    # Observations basées sur microbiote
    if dysbiosis_index >= 4:
        observations.append(f"Dysbiose sévère détectée (index {dysbiosis_index}/5)")
        actions.append({
            "text": "Protocole intensif de rééquilibrage du microbiote (probiotiques + prébiotiques)",
            "priority": "high"
        })
    elif dysbiosis_index >= 3:
        observations.append(f"Dysbiose modérée détectée (index {dysbiosis_index}/5)")
        actions.append({
            "text": "Soutenir le microbiote par alimentation riche en fibres et probiotiques",
            "priority": "medium"
        })
    
    # Analyse bactéries déviantes
    bacteria = microbiome_data.get("bacteria", []) if microbiome_data else []
    deviating = [b for b in bacteria if "deviating" in b.get("result", "").lower()]
    
    if len(deviating) > 3:
        observations.append(f"{len(deviating)} groupes bactériens déviant des normes - Déséquilibre microbien significatif")
    
    # Recherche de butyrate producers
    butyrate_producers = [b for b in bacteria if "butyrate" in b.get("group", "").lower()]
    if any("deviating" in b.get("result", "").lower() for b in butyrate_producers):
        observations.append("Producteurs de butyrate déviants - Impact sur santé intestinale et inflammation")
        actions.append({
            "text": "Augmenter apport en fibres prébiotiques (inuline 5g/jour)",
            "priority": "high"
        })
    
    # Si pas assez d'observations, ajouter un message général
    if not observations:
        observations.append("Profil global équilibré - Maintenir les bonnes pratiques actuelles")
        actions.append({
            "text": "Poursuivre une alimentation variée et équilibrée",
            "priority": "low"
        })
    
    return {"observations": observations, "actions": actions}


# ---------------------------------------------------------------------
# STREAMLIT PAGE CONFIG
# ---------------------------------------------------------------------
st.set_page_config(
    page_title="UNILABS - Plateforme Multimodale",
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

/* Cartes biomarqueurs modernes */
.biomarker-card {
    background: white;
    border: 1px solid #e0e0e0;
    border-radius: 12px;
    padding: 1rem;
    margin-bottom: 1rem;
    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

.biomarker-card-header {
    display: flex;
    align-items: center;
    margin-bottom: 0.8rem;
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

/* Tables symétriques */
.dataframe {
    width: 100% !important;
}

/* Sections */
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

    col_age, col_sex = st.columns(2)
    with col_age:
        patient_age = st.number_input(
            "Âge",
            min_value=0,
            max_value=120,
            value=st.session_state.patient_info.get("age", 0),
            key="patient_age",
        )
    with col_sex:
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

    patient_antecedents = st.text_area(
        "Antécédents médicaux",
        value=st.session_state.patient_info.get("antecedents", ""),
        height=100,
        key="patient_antecedents",
    )

    if st.button("💾 Enregistrer les infos patient", type="primary"):
        st.session_state.patient_info = {
            "name": patient_name,
            "age": patient_age,
            "sex": patient_sex,
            "weight_kg": patient_weight if patient_weight > 0 else None,
            "height_cm": patient_height if patient_height > 0 else None,
            "bmi": patient_bmi,
            "antecedents": patient_antecedents,
        }
        st.success("✅ Informations patient enregistrées")

# Patient strip
patient = st.session_state.patient_info
if patient.get("name"):
    patient_display = f"<b>{patient['name']}</b>"
    if patient.get("age"):
        patient_display += f" • {patient['age']} ans"
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
    "📊 Analyse (données extraites)",
    "💡 Recommandations",
    "🔄 Analyse Croisée",
    "📅 Suivi",
    "📄 Export PDF"
])

# ═════════════════════════════════════════════════════════════════════
# TAB 0: ANALYSE (DONNÉES EXTRAITES)
# ═════════════════════════════════════════════════════════════════════
with tabs[0]:
    st.subheader("📊 Analyse (données extraites)")

    col_bio_upload, col_micro_upload = st.columns(2)

    # ─────────────────────────────────────────────────────────────────
    # BIOLOGIE UPLOAD
    # ─────────────────────────────────────────────────────────────────
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
                    st.session_state.data_extracted = True
                    st.success(f"✅ {len(bio_data)} biomarqueurs extraits")
                except Exception as e:
                    st.error(f"❌ Erreur extraction: {e}")
                finally:
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)

    # ─────────────────────────────────────────────────────────────────
    # MICROBIOTE UPLOAD
    # ─────────────────────────────────────────────────────────────────
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
                    st.session_state.data_extracted = True
                    
                    bacteria_count = len(micro_data.get("bacteria", []))
                    st.success(f"✅ Microbiote extrait ({bacteria_count} groupes)")
                except Exception as e:
                    st.error(f"❌ Erreur extraction: {e}")
                finally:
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)

    # ─────────────────────────────────────────────────────────────────
    # AFFICHAGE DONNÉES EXTRAITES (TABLES SYMÉTRIQUES)
    # ─────────────────────────────────────────────────────────────────
    if st.session_state.data_extracted:
        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
        
        col_bio_table, col_micro_table = st.columns(2)
        
        # ═══════════════════════════════════════════════════════════════
        # BIOLOGIE TABLE ÉDITABLE
        # ═══════════════════════════════════════════════════════════════
        with col_bio_table:
            st.markdown("### Biologie")
            
            if not st.session_state.biology_df.empty:
                # Data editor pour permettre l'édition
                edited_bio_df = st.data_editor(
                    st.session_state.biology_df,
                    use_container_width=True,
                    hide_index=False,
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
                
                # Mettre à jour le dataframe en session state
                st.session_state.biology_df = edited_bio_df
                
                st.caption(f"📊 {len(edited_bio_df)} biomarqueurs • Vous pouvez modifier les interprétations")
            else:
                st.info("Aucune donnée biologique extraite")
        
        # ═══════════════════════════════════════════════════════════════
        # MICROBIOTE TABLE SYMÉTRIQUE (sans résumé dysbiosis/diversity)
        # ═══════════════════════════════════════════════════════════════
        with col_micro_table:
            st.markdown("### Microbiote")
            
            micro_data = st.session_state.microbiome_data
            if micro_data and micro_data.get("bacteria"):
                # Créer un DataFrame éditable pour le microbiote
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
                
                # Afficher les infos dysbiosis/diversity en discret sous le tableau
                dysbiosis = micro_data.get("dysbiosis_index", "N/A")
                diversity = micro_data.get("diversity", "N/A")
                
                st.caption(f"ℹ️ Résumé: dysbiosis_index={dysbiosis}, diversity={diversity}")
                
                # Data editor
                edited_micro_df = st.data_editor(
                    bacteria_df,
                    use_container_width=True,
                    hide_index=False,
                    column_config={
                        "Catégorie": st.column_config.TextColumn("category", width="small"),
                        "Élément": st.column_config.TextColumn("Description", width="large"),
                        "Statut": st.column_config.TextColumn("result", width="medium"),
                        "Interprétation": st.column_config.TextColumn("Interprétation", width="large"),
                    },
                    key="micro_editor"
                )
                
                # Sauvegarder les modifications
                if "edited_microbiome_df" not in st.session_state:
                    st.session_state.edited_microbiome_df = edited_micro_df
                else:
                    st.session_state.edited_microbiome_df = edited_micro_df
                
                st.caption(f"🦠 {len(bacteria_list)} groupes bactériens • Vous pouvez modifier les interprétations")
            else:
                st.info("Aucune donnée microbiote extraite")

# ═════════════════════════════════════════════════════════════════════
# TAB 1: RECOMMANDATIONS
# ═════════════════════════════════════════════════════════════════════
with tabs[1]:
    st.subheader("💡 Recommandations Personnalisées")

    if not st.session_state.data_extracted:
        st.warning("⚠️ Veuillez d'abord extraire les données (Biologie et/ou Microbiote)")
    else:
        if st.button("🤖 Générer les recommandations automatiques", type="primary"):
            engine = _get_rules_engine()
            if not engine:
                st.error(f"❌ Fichier de règles introuvable: {RULES_EXCEL_PATH}")
            else:
                with st.spinner("Génération des recommandations..."):
                    try:
                        patient_fmt = _patient_to_rules_engine_format(st.session_state.patient_info)
                        bio_df = st.session_state.biology_df
                        micro_data = st.session_state.microbiome_data

                        reco = engine.generate_recommendations(patient_fmt, bio_df, micro_data)
                        
                        st.session_state.recommendations = reco
                        st.success("✅ Recommandations générées")
                    except Exception as e:
                        st.error(f"❌ Erreur: {e}")
                        import traceback
                        st.code(traceback.format_exc())

        # Afficher les recommandations si générées
        if st.session_state.recommendations:
            reco = st.session_state.recommendations

            # Nutrition
            if reco.get("Nutrition"):
                st.markdown("### 🥗 Nutrition")
                for i, item in enumerate(reco["Nutrition"]):
                    st.markdown(f"**{i+1}.** {item}")

            # Micronutrition
            if reco.get("Micronutrition"):
                st.markdown("### 💊 Micronutrition")
                for i, item in enumerate(reco["Micronutrition"]):
                    st.markdown(f"**{i+1}.** {item}")

            # Microbiome
            if reco.get("Microbiome"):
                st.markdown("### 🦠 Microbiome")
                for i, item in enumerate(reco["Microbiome"]):
                    st.markdown(f"**{i+1}.** {item}")

            # Lifestyle
            if reco.get("Lifestyle"):
                st.markdown("### 🏃 Lifestyle")
                for i, item in enumerate(reco["Lifestyle"]):
                    st.markdown(f"**{i+1}.** {item}")

            # Supplementation
            if reco.get("Supplementation"):
                st.markdown("### 📋 Protocole de Supplémentation")
                suppl_df = pd.DataFrame(reco["Supplementation"])
                st.dataframe(suppl_df, use_container_width=True)

# ═════════════════════════════════════════════════════════════════════
# TAB 2: ANALYSE CROISÉE (AUTO-REMPLIE)
# ═════════════════════════════════════════════════════════════════════
with tabs[2]:
    st.subheader("🔄 Analyse Croisée Multimodale")

    if not st.session_state.data_extracted:
        st.warning("⚠️ Veuillez d'abord extraire les données")
    else:
        # Bouton pour générer l'analyse croisée auto
        if st.button("🤖 Générer l'analyse croisée automatique", type="primary"):
            with st.spinner("Analyse en cours..."):
                bio_df = st.session_state.biology_df
                micro_data = st.session_state.microbiome_data
                
                cross_analysis = _generate_cross_analysis(bio_df, micro_data)
                
                st.session_state.cross_analysis_observations = cross_analysis["observations"]
                st.session_state.cross_analysis_actions = cross_analysis["actions"]
                
                st.success("✅ Analyse croisée générée")
        
        # Affichage et édition des observations
        st.markdown("### 🔍 Observations Croisées")
        
        # Permettre l'édition
        observations_text = "\n".join(st.session_state.cross_analysis_observations)
        
        edited_observations = st.text_area(
            "Observations (une par ligne)",
            value=observations_text,
            height=200,
            help="Vous pouvez modifier, ajouter ou supprimer des observations"
        )
        
        # Sauvegarder les modifications
        if edited_observations != observations_text:
            st.session_state.cross_analysis_observations = [
                line.strip() for line in edited_observations.split("\n") if line.strip()
            ]
        
        # Actions prioritaires
        st.markdown("### ⚡ Actions Prioritaires")
        
        # Afficher et permettre l'édition des actions
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
            
            # Mettre à jour
            st.session_state.cross_analysis_actions[i] = {
                "text": new_text,
                "priority": new_priority
            }
        
        # Ajouter une nouvelle action
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

    # Liste des tests
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
        st.warning("Règles non chargées → liste biomarqueurs indisponible.")
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
        placeholder="Ex: ajustements nutritionnels + supplémentation + activité + recontrôle…",
    )

    clinician_notes = st.text_area(
        "Notes internes (optionnel)",
        value=st.session_state.follow_up.get("clinician_notes", ""),
        key="follow_notes",
        height=90,
        placeholder="Ex: hypothèses, points d'alerte, éléments à vérifier…",
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
        st.error("❌ Export PDF indisponible: vérifie pdf_generator.py + reportlab dans requirements.txt.")
    else:
        if not st.session_state.data_extracted:
            st.warning("Génère d'abord une analyse + recommandations avant d'exporter.")
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
                    st.error(f"❌ Erreur génération PDF: {e}")
                    import traceback
                    st.code(traceback.format_exc())
