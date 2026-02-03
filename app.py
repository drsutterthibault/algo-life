"""
UNILABS - Plateforme Multimodale
Analyse bio-fonctionnelle + microbiote · Extraction (PDF/Excel) · Interprétation · Recommandations · Suivi · Export PDF
"""

from __future__ import annotations

import os
import sys
import re
import tempfile
from datetime import datetime, date
from typing import Dict, Any, Optional

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
    rows = []
    for name, data in (bio_dict or {}).items():
        biomarker = str(name).strip()
        if not biomarker or biomarker.lower() == "nan":
            continue

        if isinstance(data, dict):
            val = data.get("value", data.get("Valeur", ""))
            unit = data.get("unit", data.get("Unité", ""))
            ref = data.get("reference", data.get("Référence", ""))
        else:
            val, unit, ref = data, "", ""

        rows.append({"Biomarqueur": biomarker, "Valeur": val, "Unité": unit, "Référence": ref})

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


def _build_follow_up_dict(session_follow: Dict[str, Any]) -> Dict[str, Any]:
    """
    follow_up["next_tests"] est une LISTE (multiselect).
    Pour le PDF, on convertit en texte lisible.
    """
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
    cross_analysis = {
        "cross_analysis": recos.get("cross_analysis", []),
        "priority_actions": recos.get("priority_actions", []),
    }

    recommendations = {
        "raw": recos,
        "edited": st.session_state.edited_recommendations or {},
        "bio_manual_overrides": st.session_state.get("bio_manual_overrides", {}) or {},
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


def _get_rules_engine() -> Optional[RulesEngine]:
    """
    Cache RulesEngine en session (évite rechargements, utile pour list_all_biomarkers()).
    """
    if not os.path.exists(RULES_EXCEL_PATH):
        return None

    if "rules_engine" not in st.session_state:
        st.session_state["rules_engine"] = RulesEngine(RULES_EXCEL_PATH)

    return st.session_state["rules_engine"]


def _build_text_blocks_from_recos(recos: Dict[str, Any]) -> Dict[str, str]:
    """
    Construit des blocs texte classés: interprétation / nutrition / micronutrition / lifestyle / microbiote / analyse croisée.
    """
    out: Dict[str, str] = {}

    # Actions prioritaires
    out["Actions prioritaires"] = "\n".join([f"• {x}" for x in (recos.get("priority_actions", []) or [])]).strip()

    # Biologie : classé
    bio = recos.get("biology_interpretations", []) or []
    interp_lines, nutri_lines, micro_lines, life_lines = [], [], [], []

    for x in bio:
        biom = str(x.get("biomarker", "")).strip()
        if not biom:
            continue
        status = x.get("status", "")
        val = x.get("value", "")
        unit = x.get("unit", "")
        head = f"{biom} — {status} — {val} {unit}".strip()

        interpretation = (x.get("interpretation") or "").strip()
        nutrition = (x.get("nutrition_reco") or "").strip()
        micronutrition = (x.get("micronutrition_reco") or "").strip()
        lifestyle = (x.get("lifestyle_reco") or "").strip()

        if interpretation:
            interp_lines.append(head)
            interp_lines.append(f"Interprétation: {interpretation}")
            interp_lines.append("")

        if nutrition:
            nutri_lines.append(head)
            nutri_lines.append(f"Nutrition: {nutrition}")
            nutri_lines.append("")

        if micronutrition:
            micro_lines.append(head)
            micro_lines.append(f"Micronutrition: {micronutrition}")
            micro_lines.append("")

        if lifestyle:
            life_lines.append(head)
            life_lines.append(f"Lifestyle: {lifestyle}")
            life_lines.append("")

    out["Interprétations biologie"] = "\n".join(interp_lines).strip()
    out["Nutrition"] = "\n".join(nutri_lines).strip()
    out["Micronutrition"] = "\n".join(micro_lines).strip()
    out["Lifestyle"] = "\n".join(life_lines).strip()

    # Microbiote (évite le “Résumé None/None”)
    micro_list = recos.get("microbiome_interpretations", []) or []
    micro_txt = []

    msum = recos.get("microbiome_summary") or {}
    di = msum.get("dysbiosis_index", None)
    dv = msum.get("diversity", None)
    if di is not None or (dv is not None and str(dv).strip() and str(dv).lower() != "none"):
        micro_txt.append(
            f"Résumé: dysbiosis_index={di if di is not None else '—'}, diversity={dv if dv is not None else '—'}"
        )
        micro_txt.append("")

    for m in micro_list:
        title = (m.get("title") or m.get("group") or "").strip()
        status = (m.get("status") or m.get("result") or "").strip()
        if title:
            micro_txt.append(f"{title} — {status}".strip("— ").strip())
        interpretation = (m.get("interpretation") or "").strip()
        nut = (m.get("nutrition_reco") or "").strip()
        supp = (m.get("supplementation_reco") or "").strip()
        life = (m.get("lifestyle_reco") or "").strip()

        if interpretation:
            micro_txt.append(f"Interprétation: {interpretation}")
        if nut:
            micro_txt.append(f"Nutrition: {nut}")
        if supp:
            micro_txt.append(f"Supplémentation: {supp}")
        if life:
            micro_txt.append(f"Lifestyle: {life}")
        micro_txt.append("")

    out["Recommandations microbiote"] = "\n".join(micro_txt).strip()

    # Analyse croisée -> uniquement dans Recos (pas dans Interprétation)
    cross = recos.get("cross_analysis", []) or []
    cross_txt = []
    for c in cross:
        title = (c.get("title") or "").strip()
        desc = (c.get("description") or "").strip()
        if title:
            cross_txt.append(title)
        if desc:
            cross_txt.append(desc)
        cross_txt.append("")
    out["Analyse croisée"] = "\n".join(cross_txt).strip()

    return out


# ---------------------------------------------------------------------
# STREAMLIT PAGE
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
    border-radius: 12px;
    border-left: 5px solid #1F6AA5;
    margin: 0.2rem 0 0.9rem 0;
}

.mini-box {
    background: #ffffff;
    border: 1px solid #e8edf3;
    border-radius: 12px;
    padding: 0.7rem 0.8rem;
}
.mini-title { font-weight: 700; margin-bottom: 0.35rem; }
.small-muted { color: #5b6572; font-size: 0.9rem; }
hr { border: none; border-top: 1px solid #eceff4; margin: 0.9rem 0; }

/* Fix selectbox clipping */
div[data-baseweb="select"] > div { min-height: 46px !important; }
div[data-baseweb="select"] span { line-height: 46px !important; }
div[data-baseweb="select"] input { padding-top: 10px !important; padding-bottom: 10px !important; }

/* Fix text input height */
div[data-baseweb="input"] > div { min-height: 46px !important; }
div[data-baseweb="input"] input { padding-top: 10px !important; padding-bottom: 10px !important; }
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
<div class="main-header">
  <h1>UNILABS · Plateforme Multimodale</h1>
  <div class="sub">Analyse bio-fonctionnelle + microbiote · Extraction (PDF/Excel) · Interprétation · Recommandations · Suivi · Export PDF</div>
</div>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------
# SESSION STATE
# ---------------------------------------------------------------------
if "patient_info" not in st.session_state:
    st.session_state.patient_info = {}
if "biology_data" not in st.session_state:
    st.session_state.biology_data = {}
if "microbiome_data" not in st.session_state:
    st.session_state.microbiome_data = {}
if "recommendations" not in st.session_state:
    st.session_state.recommendations = {}
if "edited_recommendations" not in st.session_state:
    st.session_state.edited_recommendations = {}
if "data_extracted" not in st.session_state:
    st.session_state.data_extracted = False
if "follow_up" not in st.session_state:
    st.session_state.follow_up = {}
if "bio_manual_overrides" not in st.session_state:
    st.session_state.bio_manual_overrides = {}  # {biomarker: {interpretation,nutrition,micronutrition,lifestyle}}

# ---------------------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------------------
with st.sidebar:
    st.header("👤 Patient")

    if "ui_patient_sex" not in st.session_state:
        st.session_state.ui_patient_sex = st.session_state.patient_info.get("sex", "F")

    with st.form("patient_form"):
        patient_name = st.text_input(
            "Nom complet",
            value=st.session_state.patient_info.get("name", ""),
            key="ui_patient_name",
        )

        cols = st.columns(2)
        with cols[0]:
            patient_age = st.number_input(
                "Âge",
                min_value=0,
                max_value=120,
                value=int(st.session_state.patient_info.get("age", 30)),
                key="ui_patient_age",
            )
        with cols[1]:
            current_sex = st.session_state.ui_patient_sex
            patient_sex = st.selectbox(
                "Sexe",
                ["F", "H"],
                index=0 if current_sex == "F" else 1,
                key="ui_patient_sex_select",
            )

        cols2 = st.columns(2)
        with cols2[0]:
            patient_weight = st.number_input(
                "Poids (kg)",
                min_value=0.0,
                max_value=300.0,
                value=float(st.session_state.patient_info.get("weight_kg", 70.0)),
                step=0.1,
                key="ui_patient_weight",
            )
        with cols2[1]:
            patient_height = st.number_input(
                "Taille (cm)",
                min_value=0.0,
                max_value=250.0,
                value=float(st.session_state.patient_info.get("height_cm", 170.0)),
                step=0.1,
                key="ui_patient_height",
            )

        bmi = _calc_bmi(patient_weight, patient_height)
        st.caption("IMC: —" if bmi is None else f"IMC: **{bmi:.1f}**")

        st.markdown('<div class="mini-box">', unsafe_allow_html=True)
        st.markdown('<div class="mini-title">Antécédents médicaux</div>', unsafe_allow_html=True)
        patient_antecedents = st.text_area(
            "",
            value=st.session_state.patient_info.get("antecedents", ""),
            height=80,
            placeholder="Ex: HTA, diabète, thyroïde, traitements, ATCD familiaux…",
            label_visibility="collapsed",
            key="ui_patient_antecedents",
        )
        st.markdown("</div>", unsafe_allow_html=True)

        if st.form_submit_button("💾 Enregistrer"):
            st.session_state.ui_patient_sex = st.session_state.ui_patient_sex_select

            st.session_state.patient_info = {
                "name": st.session_state.ui_patient_name,
                "age": st.session_state.ui_patient_age,
                "sex": st.session_state.ui_patient_sex,  # F/H
                "weight_kg": float(st.session_state.ui_patient_weight),
                "height_cm": float(st.session_state.ui_patient_height),
                "bmi": bmi,
                "antecedents": st.session_state.ui_patient_antecedents,
            }
            st.success("✅ Patient enregistré")

    st.markdown("<hr/>", unsafe_allow_html=True)

    st.header("📁 Import")
    biology_file = st.file_uploader("Biologie (PDF/Excel)", type=["pdf", "xlsx", "xls"], key="bio_file")
    microbiome_file = st.file_uploader("Microbiote (PDF/Excel)", type=["pdf", "xlsx", "xls"], key="micro_file")
    st.caption("📌 Règles: data/Bases_regles_Synlab.xlsx")

    if st.button("🔍 Extraire + Générer", type="primary"):
        if not st.session_state.patient_info.get("name"):
            st.error("❌ Enregistre le patient avant")
        else:
            try:
                # BIO
                if biology_file:
                    st.info("🔄 Extraction biologie…")
                    if biology_file.type == "application/pdf":
                        tmp = _file_to_temp_path(biology_file, ".pdf")
                        try:
                            st.session_state.biology_data = extract_synlab_biology(tmp)
                        finally:
                            try:
                                os.unlink(tmp)
                            except Exception:
                                pass
                    else:
                        df_bio = pd.read_excel(biology_file)
                        bio_dict = {}
                        for _, row in df_bio.iterrows():
                            if len(row) < 2:
                                continue
                            name = str(row.iloc[0]).strip()
                            if not name or name.lower() == "nan":
                                continue
                            bio_dict[name] = {
                                "value": row.iloc[1],
                                "unit": row.iloc[2] if len(row) > 2 else "",
                                "reference": row.iloc[3] if len(row) > 3 else "",
                            }
                        st.session_state.biology_data = bio_dict
                    st.success(f"✅ Biologie: {len(st.session_state.biology_data)} items")

                # MICRO
                if microbiome_file:
                    st.info("🔄 Extraction microbiote…")
                    if microbiome_file.type == "application/pdf":
                        tmp = _file_to_temp_path(microbiome_file, ".pdf")
                        try:
                            st.session_state.microbiome_data = extract_idk_microbiome(tmp)
                        finally:
                            try:
                                os.unlink(tmp)
                            except Exception:
                                pass
                    else:
                        df_micro = pd.read_excel(microbiome_file)
                        micro = {"bacteria": []}
                        for _, row in df_micro.iterrows():
                            if len(row) < 2:
                                continue
                            group = str(row.iloc[0]).strip()
                            if not group or group.lower() == "nan":
                                continue
                            micro["bacteria"].append({"group": group, "result": row.iloc[1]})
                        st.session_state.microbiome_data = micro
                    st.success("✅ Microbiote importé")

                # RULES
                if not os.path.exists(RULES_EXCEL_PATH):
                    st.error(f"❌ Fichier règles introuvable: {RULES_EXCEL_PATH}")
                    st.stop()

                st.info("🤖 Génération recommandations (Rules Engine)…")
                biology_df = _dict_bio_to_dataframe(st.session_state.biology_data)

                if isinstance(st.session_state.microbiome_data, dict) and "dysbiosis_index" in st.session_state.microbiome_data:
                    try:
                        st.session_state.microbiome_data["dysbiosis_index"] = int(
                            st.session_state.microbiome_data["dysbiosis_index"]
                        )
                    except Exception:
                        pass

                patient_fmt = _patient_to_rules_engine_format(st.session_state.patient_info)

                # ✅ engine cached
                engine = _get_rules_engine() or RulesEngine(RULES_EXCEL_PATH)

                st.session_state.recommendations = engine.generate_recommendations(
                    biology_data=biology_df,
                    microbiome_data=st.session_state.microbiome_data,
                    patient_info=patient_fmt,
                )

                # ✅ Reconstruire les textes (classés)
                st.session_state.edited_recommendations = _build_text_blocks_from_recos(
                    st.session_state.recommendations or {}
                )

                st.session_state.data_extracted = True
                st.success("✅ Recommandations générées")

            except Exception as e:
                st.error(f"❌ Erreur extraction: {str(e)}")


# ---------------------------------------------------------------------
# MAIN CONTENT
# ---------------------------------------------------------------------
patient = st.session_state.patient_info or {}

if patient.get("name"):
    bmi = patient.get("bmi", None)
    bmi_txt = "—" if bmi is None else f"{float(bmi):.1f}"
    antecedents = patient.get("antecedents", "").strip() or "—"

    st.markdown(
        f"""
<div class="patient-strip">
  <div><b>👤 {patient.get('name','')}</b></div>
  <div class="small-muted">
    Âge: {patient.get('age','')} ans · Sexe: {patient.get('sex','')}
    · Poids: {patient.get('weight_kg','—')} kg · Taille: {patient.get('height_cm','—')} cm · IMC: <b>{bmi_txt}</b>
  </div>
  <div class="small-muted" style="margin-top:0.35rem;">
    <b>Antécédents:</b> {antecedents}
  </div>
</div>
""",
        unsafe_allow_html=True,
    )
else:
    st.info("👈 Commence par enregistrer un patient dans la sidebar.")

tabs = st.tabs(["📊 Analyse", "🧠 Interprétation", "📝 Recommandations", "📅 Suivi", "📄 Export PDF"])

# ---------------------------------------------------------------------
# TAB 0 - ANALYSE
# ---------------------------------------------------------------------
with tabs[0]:
    st.subheader("📊 Analyse (données extraites)")
    colA, colB = st.columns(2)

    with colA:
        st.markdown("### Biologie")
        df_bio = _dict_bio_to_dataframe(st.session_state.biology_data)
        if df_bio.empty:
            st.info("Aucune donnée biologie importée.")
        else:
            st.dataframe(df_bio, use_container_width=True)

    with colB:
        st.markdown("### Microbiote")
        micro = st.session_state.microbiome_data or {}

        if not micro:
            st.info("Aucune donnée microbiote importée.")
        else:
            # Résumé DI / diversité
            di = micro.get("dysbiosis_index", "—")
            div = micro.get("diversity", "—")

            c1, c2 = st.columns(2)
            with c1:
                st.metric("Dysbiosis index", di if di is not None else "—")
            with c2:
                st.metric("Diversity", div if div is not None else "—")

            # Tableau bactéries
            bacteria = micro.get("bacteria", [])
            if isinstance(bacteria, list) and len(bacteria) > 0:
                dfm = pd.DataFrame(bacteria)

                # Nettoyage description
                if "group" in dfm.columns:
                    dfm["group"] = dfm["group"].astype(str).str.replace(r"\s+", " ", regex=True).str.strip()

                # Affichage agréable : description tronquée
                if "group" in dfm.columns:
                    dfm["Description"] = dfm["group"].apply(lambda s: (s[:120] + "…") if len(s) > 120 else s)

                show_cols = []
                if "category" in dfm.columns:
                    show_cols.append("category")
                if "Description" in dfm.columns:
                    show_cols.append("Description")
                elif "group" in dfm.columns:
                    show_cols.append("group")
                if "result" in dfm.columns:
                    show_cols.append("result")

                st.dataframe(dfm[show_cols] if show_cols else dfm, use_container_width=True)
            else:
                st.info("Aucun groupe bactérien trouvé (liste vide).")

# ---------------------------------------------------------------------
# TAB 1 - INTERPRETATION
# ---------------------------------------------------------------------
with tabs[1]:
    st.subheader("🧠 Interprétation (rules engine)")
    recos = st.session_state.recommendations or {}
    if not recos:
        st.warning("Aucune interprétation disponible (génère d'abord via le bouton de la sidebar).")
    else:
        st.markdown("### Actions prioritaires")
        pa = recos.get("priority_actions", []) or []
        if pa:
            for x in pa:
                st.write(f"• {x}")
        else:
            st.write("—")

        st.markdown("### Biologie")
        bio = recos.get("biology_interpretations", []) or []
        if bio:
            df = pd.DataFrame(
                [
                    {
                        "Biomarqueur": x.get("biomarker", ""),
                        "Valeur": f"{x.get('value','')} {x.get('unit','')}".strip(),
                        "Référence": x.get("reference", ""),
                        "Statut": x.get("status", ""),
                        "Interprétation": x.get("interpretation", ""),
                    }
                    for x in bio
                ]
            )
            # ✅ pas de colonnes reco vides ici
            st.dataframe(df, use_container_width=True)
        else:
            st.write("—")

        st.markdown("### Microbiote")
        msum = recos.get("microbiome_summary", {}) or {}
        # ✅ éviter l’affichage None/None
        di = msum.get("dysbiosis_index", None)
        dv = msum.get("diversity", None)
        if di is not None or (dv is not None and str(dv).strip() and str(dv).lower() != "none"):
            st.info(f"Résumé: dysbiosis_index={di if di is not None else '—'}, diversity={dv if dv is not None else '—'}")

        micro = recos.get("microbiome_interpretations", []) or []
        if micro:
            dfm = pd.DataFrame(
                [
                    {
                        "Élément": (x.get("title") or x.get("group") or ""),
                        "Statut": x.get("status", x.get("result", "")),
                        "Interprétation": x.get("interpretation", ""),
                    }
                    for x in micro
                ]
            )
            st.dataframe(dfm, use_container_width=True)
        else:
            st.write("—")

        # ✅ demandé: enlever le tableau Analyse croisée ici (uniquement dans Recommandations)
        with st.expander("Debug (JSON brut)"):
            st.json(recos)

# ---------------------------------------------------------------------
# TAB 2 - RECOMMANDATIONS
# ---------------------------------------------------------------------
with tabs[2]:
    st.subheader("📝 Recommandations (éditables)")

    if not st.session_state.data_extracted or not st.session_state.edited_recommendations:
        st.warning("Aucune recommandation éditable (génère d'abord via le bouton de la sidebar).")
    else:
        recos = st.session_state.recommendations or {}
        bio = recos.get("biology_interpretations", []) or []

        st.markdown("## 🧪 Biologie — édition manuelle (par biomarqueur)")
        if not bio:
            st.info("Aucune interprétation biologie à éditer.")
        else:
            for b in bio:
                biom = str(b.get("biomarker", "")).strip()
                if not biom:
                    continue

                # init overrides
                if biom not in st.session_state.bio_manual_overrides:
                    st.session_state.bio_manual_overrides[biom] = {
                        "interpretation": b.get("interpretation", "") or "",
                        "nutrition": b.get("nutrition_reco", "") or "",
                        "micronutrition": b.get("micronutrition_reco", "") or "",
                        "lifestyle": b.get("lifestyle_reco", "") or "",
                    }

                status = b.get("status", "")
                val = b.get("value", "")
                unit = b.get("unit", "")
                head = f"{biom} — {status} — {val} {unit}".strip()

                with st.expander(head):
                    ov = st.session_state.bio_manual_overrides[biom]

                    ov["interpretation"] = st.text_area(
                        "Interprétation (modifiable)",
                        value=ov.get("interpretation", ""),
                        height=90,
                        key=f"ov_interp_{biom}",
                    )
                    c1, c2 = st.columns(2)
                    with c1:
                        ov["nutrition"] = st.text_area(
                            "Nutrition",
                            value=ov.get("nutrition", ""),
                            height=110,
                            key=f"ov_nut_{biom}",
                        )
                    with c2:
                        ov["micronutrition"] = st.text_area(
                            "Micronutrition",
                            value=ov.get("micronutrition", ""),
                            height=110,
                            key=f"ov_micro_{biom}",
                        )

                    ov["lifestyle"] = st.text_area(
                        "Lifestyle",
                        value=ov.get("lifestyle", ""),
                        height=90,
                        key=f"ov_life_{biom}",
                    )

                    st.session_state.bio_manual_overrides[biom] = ov

            # ✅ Rebuild blocs classés à partir des overrides (pour texte + PDF)
            interp_lines, nutri_lines, micro_lines, life_lines = [], [], [], []
            for biom, ov in (st.session_state.bio_manual_overrides or {}).items():
                ov = ov or {}
                if ov.get("interpretation", "").strip():
                    interp_lines.append(biom)
                    interp_lines.append(ov["interpretation"].strip())
                    interp_lines.append("")
                if ov.get("nutrition", "").strip():
                    nutri_lines.append(biom)
                    nutri_lines.append(ov["nutrition"].strip())
                    nutri_lines.append("")
                if ov.get("micronutrition", "").strip():
                    micro_lines.append(biom)
                    micro_lines.append(ov["micronutrition"].strip())
                    micro_lines.append("")
                if ov.get("lifestyle", "").strip():
                    life_lines.append(biom)
                    life_lines.append(ov["lifestyle"].strip())
                    life_lines.append("")

            st.session_state.edited_recommendations["Interprétations biologie"] = "\n".join(interp_lines).strip()
            st.session_state.edited_recommendations["Nutrition"] = "\n".join(nutri_lines).strip()
            st.session_state.edited_recommendations["Micronutrition"] = "\n".join(micro_lines).strip()
            st.session_state.edited_recommendations["Lifestyle"] = "\n".join(life_lines).strip()

        st.divider()

        # ✅ Sections éditables (classées)
        ordered_sections = [
            "Actions prioritaires",
            "Interprétations biologie",
            "Nutrition",
            "Micronutrition",
            "Lifestyle",
            "Recommandations microbiote",
            "Analyse croisée",
        ]

        for section in ordered_sections:
            if section not in st.session_state.edited_recommendations:
                continue
            txt = st.session_state.edited_recommendations.get(section, "") or ""
            st.markdown(f"### {section}")

            # ✅ hauteur adaptée pour micronutrition (meilleure mise en page)
            height = 220
            if section in ("Nutrition", "Micronutrition"):
                height = 280
            if section == "Analyse croisée":
                height = 260

            st.session_state.edited_recommendations[section] = st.text_area(
                f"Texte - {section}",
                value=txt,
                height=height,
                key=f"edit_{section}",
            )
            st.divider()

        export = {
            "patient": st.session_state.patient_info,
            "biology_df": _dict_bio_to_dataframe(st.session_state.biology_data).to_dict(orient="records"),
            "microbiome": st.session_state.microbiome_data,
            "recommendations_raw": st.session_state.recommendations,
            "recommendations_edited": st.session_state.edited_recommendations,
            "bio_manual_overrides": st.session_state.bio_manual_overrides,
            "export_date": datetime.now().isoformat(),
        }

        st.download_button(
            "⬇️ Télécharger export JSON",
            data=pd.Series(export).to_json(),
            file_name=f"unilabs_export_{(patient.get('name','patient')).replace(' ', '_')}.json",
            mime="application/json",
        )

# ---------------------------------------------------------------------
# TAB 3 - SUIVI
# ---------------------------------------------------------------------
with tabs[3]:
    st.subheader("📅 Suivi")

    engine = _get_rules_engine()
    all_biomarkers = engine.list_all_biomarkers() if engine is not None else []

    # Valeur initiale: follow_up["next_tests"] doit être une LISTE
    prev_tests = st.session_state.follow_up.get("next_tests", [])
    if isinstance(prev_tests, str):
        # migration si ancienne version stockait un texte
        prev_tests = [x.strip() for x in prev_tests.split(",") if x.strip()]

    col1, col2 = st.columns([1, 2])
    with col1:
        next_date = st.date_input(
            "Prochain contrôle",
            value=st.session_state.follow_up.get("next_date", date.today()),
            key="follow_next_date",
        )

    with col2:
        if all_biomarkers:
            next_tests_list = st.multiselect(
                "Examens / bilans à recontrôler",
                options=all_biomarkers,
                default=prev_tests,
                key="follow_next_tests_list",
                help="Liste issue du fichier de règles (Excel).",
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
        placeholder="Ex: hypothèses, points d’alerte, éléments à vérifier…",
    )

    if st.button("💾 Enregistrer le suivi"):
        st.session_state.follow_up = {
            "next_date": next_date,
            "next_tests": next_tests_list,  # ✅ LISTE
            "plan": plan,
            "clinician_notes": clinician_notes,
        }
        st.success("✅ Suivi enregistré")

# ---------------------------------------------------------------------
# TAB 4 - EXPORT PDF
# ---------------------------------------------------------------------
with tabs[4]:
    st.subheader("📄 Export PDF")
    if not PDF_EXPORT_AVAILABLE:
        st.error("❌ Export PDF indisponible: vérifie pdf_generator.py + reportlab dans requirements.txt.")
    else:
        if not st.session_state.data_extracted:
            st.warning("Génère d’abord une analyse + recommandations avant d’exporter.")
        else:
            pdf_filename = st.text_input(
                "Nom du fichier PDF",
                value=f"UNILABS_rapport_{(patient.get('name','patient')).replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf",
            )

            if st.button("📄 Générer le PDF", type="primary"):
                payload = _build_pdf_payload()
                out_path = os.path.join(tempfile.gettempdir(), pdf_filename)

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
