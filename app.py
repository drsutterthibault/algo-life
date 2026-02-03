"""
UNILABS / ALGO-LIFE - Plateforme Multimodale COMPLÈTE
✅ Bug reco corrigé (ordre + mapping sections)
✅ Date de naissance + âge biologique estimé (prototype interne)
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

# ---------------------------------------------------------------------
# PATHS / IMPORTS
# ---------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from extractors import extract_synlab_biology, extract_idk_microbiome  # noqa
from rules_engine import RulesEngine  # noqa

try:
    from pdf_generator import generate_multimodal_report  # noqa
    PDF_EXPORT_AVAILABLE = True
except Exception:
    PDF_EXPORT_AVAILABLE = False

RULES_EXCEL_PATH = os.path.join(BASE_DIR, "data", "Bases_regles_Synlab.xlsx")

# ---------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------

def _normalize_reco_sections(reco_raw: Dict[str, Any]) -> Dict[str, Any]:
    """Convertit la sortie du RulesEngine en sections UI stables.
    Objectif: toujours fournir Nutrition / Micronutrition / Lifestyle (list[str]).
    """
    if not isinstance(reco_raw, dict):
        return {
            "Nutrition": [],
            "Micronutrition": [],
            "Lifestyle": [],
            "debug": {"reason": "reco_raw_not_dict"},
        }

    nutrition: List[str] = []
    micronut: List[str] = []
    lifestyle: List[str] = []

    # Biologie
    for item in reco_raw.get("biology_interpretations", []) or []:
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

    # Microbiote
    for item in reco_raw.get("microbiome_interpretations", []) or []:
        if not isinstance(item, dict):
            continue
        grp = str(item.get("group", "")).strip()
        prefix = f"[{grp}] " if grp else ""

        n = item.get("nutrition_reco")
        if n:
            nutrition.append(prefix + str(n).strip())

        s = item.get("supplementation_reco")
        if s:
            micronut.append(prefix + str(s).strip())

        l = item.get("lifestyle_reco")
        if l:
            lifestyle.append(prefix + str(l).strip())

    # Nettoyage doublons (en gardant l'ordre)
    def _dedupe(seq: List[str]) -> List[str]:
        seen = set()
        out = []
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
        "_raw": reco_raw,  # conservé pour debug / export
        "debug": reco_raw.get("debug", {}),
    }


def _compute_biological_age_estimate(bio_df: Optional[pd.DataFrame], chrono_age: int) -> Dict[str, Any]:
    """Prototype d'âge biologique (non clinique, interne).

    Heuristique simple et robuste:
    - regarde un panel limité si présent
    - applique un delta en fonction du nombre de marqueurs anormaux (si statut dispo)
    - ne casse jamais si données manquantes

    Retour:
      {"bio_age": float|None, "delta": float|None, "signals": {...}}
    """
    if bio_df is None or not isinstance(bio_df, pd.DataFrame) or bio_df.empty:
        return {"bio_age": None, "delta": None, "signals": {"reason": "no_biology_df"}}

    panel = [
        "CRP", "hs-CRP", "CRP ultrasensible",
        "Albumine", "Albumin",
        "HbA1c", "Hémoglobine glyquée",
        "Glycémie", "Glucose",
        "Créatinine", "Creatinine",
        "Ferritine", "Ferritin",
        "Vitamine D", "25(OH)D",
    ]

    def _norm(s: str) -> str:
        return re.sub(r"\s+", " ", str(s or "")).strip().lower()

    # Colonnes
    col_b = None
    for c in bio_df.columns:
        if _norm(c) in [_norm(x) for x in ["Biomarqueur", "Biomarker", "Marqueur"]]:
            col_b = c
            break
    if not col_b:
        col_b = bio_df.columns[0]

    col_v = None
    for c in bio_df.columns:
        if _norm(c) in [_norm(x) for x in ["Valeur", "Value", "Resultat", "Résultat"]]:
            col_v = c
            break

    col_r = None
    for c in bio_df.columns:
        if _norm(c) in [_norm(x) for x in ["Référence", "Reference", "Norme"]]:
            col_r = c
            break

    col_s = None
    for c in bio_df.columns:
        if _norm(c) in [_norm(x) for x in ["Statut", "Status", "Flag"]]:
            col_s = c
            break

    abnormal = 0
    total_found = 0
    found: Dict[str, Any] = {}

    panel_norm = [_norm(p) for p in panel]

    for _, row in bio_df.iterrows():
        biom = str(row.get(col_b, ""))
        biom_n = _norm(biom)
        if not biom_n:
            continue

        if any(p in biom_n for p in panel_norm):
            total_found += 1

            status = str(row.get(col_s, "")).lower() if col_s else ""
            is_abn = False

            # si status pas là -> on reste conservateur (pas d'inférence)
            if status:
                if any(k in status for k in ["high", "low", "abnormal", "haut", "bas", "anormal"]):
                    is_abn = True

            if is_abn:
                abnormal += 1

            found[biom] = {
                "value": row.get(col_v) if col_v else None,
                "reference": row.get(col_r) if col_r else None,
                "status": row.get(col_s) if col_s else None,
            }

    # delta: +0.75 an / biomarqueur anormal (cap 8 ans)
    delta = min(8.0, abnormal * 0.75)
    bio_age = float(chrono_age) + float(delta)

    return {
        "bio_age": bio_age,
        "delta": delta,
        "signals": {
            "panel_found": total_found,
            "abnormal_count": abnormal,
            "details": found,
        },
    }


def _file_to_temp_path(uploaded_file, suffix: str) -> str:
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.getbuffer())
        return tmp.name


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        if isinstance(x, (int, float)):
            return float(x)
        s = str(x).strip().replace(",", ".")
        return float(s)
    except Exception:
        return default


def _calc_age_from_birthdate(birthdate: date) -> int:
    today = date.today()
    years = today.year - birthdate.year
    if (today.month, today.day) < (birthdate.month, birthdate.day):
        years -= 1
    return max(0, years)


def _patient_to_rules_engine_format(pi: Dict[str, Any]) -> Dict[str, Any]:
    if not pi:
        return {}
    return {
        "name": pi.get("name", ""),
        "birthdate": pi.get("birthdate"),
        "age": pi.get("age"),
        "sex": pi.get("sex"),
        "weight": pi.get("weight"),
        "height": pi.get("height"),
        "bmi": pi.get("bmi"),
        "antecedents": pi.get("antecedents", ""),
    }


def _get_rules_engine() -> Optional[RulesEngine]:
    if not os.path.exists(RULES_EXCEL_PATH):
        return None
    return RulesEngine(RULES_EXCEL_PATH)


def _df_to_html_download_link(df: pd.DataFrame, filename: str = "export.csv") -> str:
    csv = df.to_csv(index=False).encode("utf-8")
    b64 = base64.b64encode(csv).decode()
    return f'<a href="data:file/csv;base64,{b64}" download="{filename}">📥 Télécharger CSV</a>'


def _generate_cross_analysis(bio_df: pd.DataFrame, micro_data: Optional[Dict]) -> Dict[str, Any]:
    observations: List[str] = []
    actions: List[str] = []

    if bio_df is not None and isinstance(bio_df, pd.DataFrame) and not bio_df.empty:
        # Exemple simple: anomalies statut si colonne "Statut" existe
        if "Statut" in bio_df.columns:
            abn = bio_df[bio_df["Statut"].astype(str).str.lower().str.contains("high|low|abnormal|haut|bas|anormal", na=False)]
            if not abn.empty:
                observations.append(f"{len(abn)} biomarqueur(s) signalé(s) comme anormal(aux) (à prioriser).")
                actions.append("Recontrôle biologique ciblé + contextualisation clinique.")

    if micro_data:
        dx = micro_data.get("dysbiosis_index")
        if dx is not None:
            observations.append(f"Indice de dysbiose: {dx}")
            actions.append("Cibler alimentation + fibres + stratégies probiotiques/prébiotiques selon profil.")

    if not observations:
        observations = ["Aucune observation croisée automatique (données insuffisantes ou normalité)."]
    if not actions:
        actions = ["Rien à prioriser automatiquement."]

    return {"observations": observations, "actions": actions}


# ---------------------------------------------------------------------
# SESSION STATE INIT
# ---------------------------------------------------------------------
if "patient_info" not in st.session_state:
    st.session_state.patient_info = {}

if "biology_df" not in st.session_state:
    st.session_state.biology_df = None

if "microbiome_data" not in st.session_state:
    st.session_state.microbiome_data = None

if "data_extracted" not in st.session_state:
    st.session_state.data_extracted = False

if "recommendations" not in st.session_state:
    st.session_state.recommendations = None

if "cross_analysis_observations" not in st.session_state:
    st.session_state.cross_analysis_observations = []

if "cross_analysis_actions" not in st.session_state:
    st.session_state.cross_analysis_actions = []

if "follow_up" not in st.session_state:
    st.session_state.follow_up = {}

# ---------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------
st.set_page_config(
    page_title="ALGO-LIFE - Multimodal",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🧬 ALGO-LIFE - Plateforme Multimodale")

tabs = st.tabs(["📥 Import & Données", "💡 Interprétation", "🔄 Analyse croisée", "📈 Suivi", "🧾 Export PDF"])

# ═════════════════════════════════════════════════════════════════════
# TAB 0: IMPORT & DONNÉES
# ═════════════════════════════════════════════════════════════════════
with tabs[0]:
    st.subheader("📥 Import & Données")

    # --- Patient info
    st.markdown("### 👤 Informations patient")

    patient_name = st.text_input(
        "Nom / ID patient",
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

    # Calculer l'âge automatiquement + âge biologique estimé
    patient_age = _calc_age_from_birthdate(patient_birthdate)
    st.metric("Âge calculé", f"{patient_age} ans")

    # Âge biologique (prototype interne, calculable après extraction des biomarqueurs)
    bio_age_info = _compute_biological_age_estimate(st.session_state.get("biology_df"), patient_age)
    if bio_age_info.get("bio_age") is not None:
        st.metric("Âge biologique estimé", f"{bio_age_info['bio_age']:.1f} ans", delta=f"+{bio_age_info['delta']:.1f} ans")
    else:
        st.metric("Âge biologique estimé", "—")

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
            value=float(st.session_state.patient_info.get("weight") or 0.0),
            key="patient_weight",
        )
    with col_height:
        patient_height = st.number_input(
            "Taille (cm)",
            min_value=0.0,
            max_value=250.0,
            value=float(st.session_state.patient_info.get("height") or 0.0),
            key="patient_height",
        )

    bmi = None
    if patient_height and patient_weight:
        try:
            bmi = patient_weight / ((patient_height / 100.0) ** 2)
        except Exception:
            bmi = None
    if bmi is not None:
        st.metric("IMC", f"{bmi:.1f}")

    patient_antecedents = st.text_area(
        "Antécédents médicaux / contexte",
        value=st.session_state.patient_info.get("antecedents", ""),
        height=100,
        key="patient_antecedents",
    )

    if st.button("✅ Enregistrer les informations patient"):
        st.session_state.patient_info = {
            "name": patient_name,
            "birthdate": patient_birthdate,
            "age": patient_age,
            "sex": patient_sex,
            "weight": patient_weight,
            "height": patient_height,
            "bmi": bmi,
            "antecedents": patient_antecedents,
        }
        st.success("✅ Informations patient enregistrées")

    st.markdown("---")

    # --- Uploads
    st.markdown("### 📄 Import fichiers")
    col1, col2 = st.columns(2)

    with col1:
        bio_file = st.file_uploader(
            "Bilan de biologie (PDF)",
            type=["pdf"],
            key="bio_file_uploader",
        )
    with col2:
        micro_file = st.file_uploader(
            "Rapport microbiote (PDF)",
            type=["pdf"],
            key="micro_file_uploader",
        )

    if st.button("⚙️ Extraire les données", type="primary"):
        if not bio_file and not micro_file:
            st.error("❌ Merci d'importer au moins un fichier (biologie et/ou microbiote).")
        else:
            with st.spinner("Extraction en cours..."):
                try:
                    if bio_file:
                        bio_path = _file_to_temp_path(bio_file, ".pdf")
                        bio_df = extract_synlab_biology(bio_path)
                        st.session_state.biology_df = bio_df

                    if micro_file:
                        micro_path = _file_to_temp_path(micro_file, ".pdf")
                        micro_data = extract_idk_microbiome(micro_path)
                        st.session_state.microbiome_data = micro_data

                    st.session_state.data_extracted = True
                    st.success("✅ Extraction terminée")
                    st.rerun()
                except Exception as e:
                    st.session_state.data_extracted = False
                    st.error(f"❌ Erreur extraction: {e}")

    # --- Display extracted data
    if st.session_state.data_extracted:
        st.markdown("### 🧪 Données extraites")

        if st.session_state.biology_df is not None and isinstance(st.session_state.biology_df, pd.DataFrame):
            st.markdown("#### Biologie")
            st.dataframe(st.session_state.biology_df, use_container_width=True)
            st.markdown(_df_to_html_download_link(st.session_state.biology_df, "biology_export.csv"), unsafe_allow_html=True)

        if st.session_state.microbiome_data:
            st.markdown("#### Microbiote")
            st.json(st.session_state.microbiome_data)

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

                        # ✅ FIX: appel sûr + normalisation sections UI
                        reco_raw = engine.generate_recommendations(
                            biology_data=bio_df,
                            microbiome_data=micro_data,
                            patient_info=patient_fmt,
                        )
                        reco = _normalize_reco_sections(reco_raw)

                        st.session_state.recommendations = reco
                        st.success("✅ Interprétation générée")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Erreur: {e}")
                        import traceback
                        st.code(traceback.format_exc())

        # AFFICHAGE DES RECOMMANDATIONS (3 blocs éditables)
        if st.session_state.recommendations:
            reco = st.session_state.recommendations

            def _as_text(items: Any) -> str:
                if not items:
                    return ""
                if isinstance(items, str):
                    return items.strip()
                if isinstance(items, list):
                    return "\n".join([str(x).strip() for x in items if str(x).strip()])
                return str(items).strip()

            st.caption("Recommandations générées par IA à partir du système de règles. Modifiables avant export.")

            # Micronutrition
            st.markdown("### 💊 Micronutrition")
            micro_text = _as_text(reco.get("Micronutrition", []))
            edited_micro = st.text_area("Micronutrition (une reco par ligne)", value=micro_text, height=160)
            reco["Micronutrition"] = [x.strip() for x in edited_micro.split("\n") if x.strip()]
            st.markdown("---")

            # Nutrition
            st.markdown("### 🥗 Nutrition & Diététique")
            nut_text = _as_text(reco.get("Nutrition", []))
            edited_nut = st.text_area("Nutrition (une reco par ligne)", value=nut_text, height=160)
            reco["Nutrition"] = [x.strip() for x in edited_nut.split("\n") if x.strip()]
            st.markdown("---")

            # Lifestyle
            st.markdown("### 🏃 Lifestyle")
            life_text = _as_text(reco.get("Lifestyle", []))
            edited_life = st.text_area("Lifestyle (une reco par ligne)", value=life_text, height=160)
            reco["Lifestyle"] = [x.strip() for x in edited_life.split("\n") if x.strip()]
            st.markdown("---")

            # Debug optionnel si tout est vide
            if (not reco.get("Nutrition")) and (not reco.get("Micronutrition")) and (not reco.get("Lifestyle")):
                with st.expander("🛠️ Debug (si rien ne s'affiche)"):
                    st.write("Aucune recommandation n'a été classée dans les 3 sections. Vérifiez le matching règles ↔ biomarqueurs.")
                    raw = reco.get("_raw")
                    if isinstance(raw, dict):
                        st.json(raw.get("debug", {}))
                        st.write("Extrait biology_interpretations (first 5):")
                        st.json((raw.get("biology_interpretations") or [])[:5])

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

        st.markdown("### 🔍 Observations Croisées")
        observations_text = "\n".join(st.session_state.cross_analysis_observations)
        edited_observations = st.text_area(
            "Observations (une par ligne)",
            value=observations_text,
            height=200,
            help="Modifiez, ajoutez ou supprimez des observations",
        )

        if edited_observations != observations_text:
            st.session_state.cross_analysis_observations = [
                line.strip() for line in edited_observations.split("\n") if line.strip()
            ]

        st.markdown("### ⚡ Actions Prioritaires")
        actions_text = "\n".join(st.session_state.cross_analysis_actions)
        edited_actions = st.text_area(
            "Actions (une par ligne)",
            value=actions_text,
            height=160,
            help="Modifiez, ajoutez ou supprimez des actions",
        )
        if edited_actions != actions_text:
            st.session_state.cross_analysis_actions = [
                line.strip() for line in edited_actions.split("\n") if line.strip()
            ]

# ═════════════════════════════════════════════════════════════════════
# TAB 3: SUIVI
# ═════════════════════════════════════════════════════════════════════
with tabs[3]:
    st.subheader("📈 Suivi")

    st.markdown("### 🗓️ Prochain contrôle")
    next_date = st.date_input(
        "Date du prochain contrôle",
        value=st.session_state.follow_up.get("next_date") or date.today(),
        key="followup_next_date",
    )
    notes = st.text_area(
        "Notes de suivi",
        value=st.session_state.follow_up.get("notes", ""),
        height=140,
        key="followup_notes",
    )

    if st.button("💾 Enregistrer le suivi"):
        st.session_state.follow_up = {"next_date": next_date, "notes": notes}
        st.success("✅ Suivi enregistré")

# ═════════════════════════════════════════════════════════════════════
# TAB 4: EXPORT PDF
# ═════════════════════════════════════════════════════════════════════
with tabs[4]:
    st.subheader("🧾 Export PDF")

    if not PDF_EXPORT_AVAILABLE:
        st.warning("⚠️ Module PDF indisponible (pdf_generator.py non importable).")
    elif not st.session_state.data_extracted:
        st.warning("⚠️ Veuillez d'abord extraire les données")
    else:
        st.info("Le PDF inclura: infos patient, tableaux, recos éditées, analyse croisée.")
        if st.button("📄 Générer PDF", type="primary"):
            with st.spinner("Génération PDF..."):
                try:
                    patient = st.session_state.patient_info
                    bio_df = st.session_state.biology_df
                    micro_data = st.session_state.microbiome_data
                    reco = st.session_state.recommendations or {}
                    cross_obs = st.session_state.cross_analysis_observations
                    cross_actions = st.session_state.cross_analysis_actions

                    out_pdf = os.path.join(tempfile.gettempdir(), f"ALGO_LIFE_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
                    generate_multimodal_report(
                        output_path=out_pdf,
                        patient_info=patient,
                        biology_df=bio_df,
                        microbiome_data=micro_data,
                        recommendations=reco,
                        cross_observations=cross_obs,
                        cross_actions=cross_actions,
                    )

                    with open(out_pdf, "rb") as f:
                        pdf_bytes = f.read()

                    st.success("✅ PDF généré")
                    st.download_button(
                        label="⬇️ Télécharger le PDF",
                        data=pdf_bytes,
                        file_name=os.path.basename(out_pdf),
                        mime="application/pdf",
                    )
                except Exception as e:
                    st.error(f"❌ Erreur PDF: {e}")
