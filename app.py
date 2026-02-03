"""
ALGO-LIFE - Plateforme Médecin
Streamlit App - Import (PDF/Excel) + Extraction + Rules Engine
PATCHED: rules path + dict->df + safe float to avoid str>int crashes
"""

from __future__ import annotations

import os
import sys
import re
import tempfile
from datetime import datetime
from typing import Dict, Any

import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------
# PATHS / IMPORTS
# ---------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from extractors import extract_synlab_biology, extract_idk_microbiome  # noqa
from rules_engine import RulesEngine  # noqa

# ✅ Chemin robuste (Streamlit Cloud safe)
RULES_EXCEL_PATH = os.path.join(BASE_DIR, "data", "Bases_regles_Synlab.xlsx")


# ---------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------
def _file_to_temp_path(uploaded_file, suffix: str) -> str:
    """Save Streamlit UploadedFile to a temp path and return it."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.read())
        return tmp.name


def _safe_float(x):
    """Convert any messy value to float, else None."""
    try:
        if x is None:
            return None
        s = str(x).strip().replace(",", ".")
        # keep digits/sign/dot/exponent only
        s = re.sub(r"[^0-9\.\-\+eE]", "", s)
        return float(s) if s else None
    except Exception:
        return None


def _dict_bio_to_dataframe(bio_dict: Dict[str, Any]) -> pd.DataFrame:
    """
    Convert biology dict into DataFrame expected by RulesEngine:
    columns: Biomarqueur, Valeur, Unité, Référence
    """
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

        rows.append(
            {"Biomarqueur": biomarker, "Valeur": val, "Unité": unit, "Référence": ref}
        )

    df = pd.DataFrame(rows)
    if not df.empty:
        # ✅ CRITICAL PATCH: convert to float to avoid "str > int"
        df["Valeur"] = df["Valeur"].apply(_safe_float)
    return df


def _patient_to_rules_engine_format(patient_info: Dict[str, Any]) -> Dict[str, Any]:
    """Map UI patient fields to what rules_engine.py expects (genre=Homme/Femme)."""
    sex = (patient_info or {}).get("sex", "F")
    genre = "Homme" if sex == "M" else "Femme"
    return {
        "nom": (patient_info or {}).get("name", ""),
        "age": (patient_info or {}).get("age", None),
        "genre": genre,
        "date": str((patient_info or {}).get("date", "")),
        "notes": (patient_info or {}).get("notes", ""),
    }


def _format_recos_for_editing(recos: Dict[str, Any]) -> Dict[str, str]:
    """
    Make editable text blocks from RulesEngine output.
    Works even if some keys are missing.
    """
    out = {}

    # Priority actions
    pa = recos.get("priority_actions", []) or []
    out["Actions prioritaires"] = "\n".join([f"• {x}" for x in pa]) if pa else ""

    # Biology interpretations
    bio = recos.get("biology_interpretations", []) or []
    lines = []
    for b in bio:
        biom = b.get("biomarker", "")
        val = b.get("value", "")
        unit = b.get("unit", "")
        status = b.get("status", "")
        ref = b.get("reference", "")
        interp = b.get("interpretation", "")
        nutr = b.get("nutrition_reco", "")
        micro = b.get("micronutrition_reco", "")
        life = b.get("lifestyle_reco", "")

        header = f"{biom} — {val} {unit} (Ref: {ref}) — Statut: {status}".strip()
        if header.strip("— "):
            lines.append(header)
        if interp:
            lines.append(f"Interprétation: {interp}")
        if nutr:
            lines.append(f"Nutrition: {nutr}")
        if micro:
            lines.append(f"Micronutrition: {micro}")
        if life:
            lines.append(f"Lifestyle: {life}")
        lines.append("")
    out["Biologie"] = "\n".join(lines).strip()

    # Microbiome
    micro_list = recos.get("microbiome_interpretations", []) or []
    mlines = []
    summary = recos.get("microbiome_summary", {}) or {}
    if summary:
        mlines.append(f"Résumé microbiote: {summary}")
        mlines.append("")
    for m in micro_list:
        title = m.get("title") or m.get("group") or ""
        status = m.get("status", "")
        interp = m.get("interpretation", "")
        reco = m.get("recommendations", "")
        if title or status:
            mlines.append(f"{title} — {status}".strip("— "))
        if interp:
            mlines.append(f"Interprétation: {interp}")
        if reco:
            mlines.append(f"Reco: {reco}")
        mlines.append("")
    out["Microbiote"] = "\n".join(mlines).strip()

    # Cross analysis
    cross = recos.get("cross_analysis", []) or []
    clines = []
    for c in cross:
        t = c.get("title", "")
        d = c.get("description", "")
        r = c.get("recommendations", "")
        if t:
            clines.append(t)
        if d:
            clines.append(d)
        if r:
            clines.append(f"Reco: {r}")
        clines.append("")
    out["Analyse croisée"] = "\n".join(clines).strip()

    return out


# ---------------------------------------------------------------------
# STREAMLIT UI
# ---------------------------------------------------------------------
st.set_page_config(
    page_title="ALGO-LIFE - Plateforme Médecin",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
.main-header {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    padding: 1.2rem;
    border-radius: 12px;
    color: white;
    margin-bottom: 1.2rem;
}
.patient-info {
    background: #f8f9ff;
    padding: 0.9rem;
    border-radius: 10px;
    border-left: 5px solid #667eea;
    margin-bottom: 1rem;
}
.small-note { color: #555; font-size: 0.9rem; }
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
<div class="main-header">
  <h1 style="margin:0;">🧬 ALGO-LIFE</h1>
  <div class="small-note">Import (PDF/Excel) → Extraction → Rules Engine → Recommandations éditables</div>
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


# ---------------------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------------------
with st.sidebar:
    st.header("👤 Patient")

    with st.form("patient_form"):
        col1, col2 = st.columns(2)
        with col1:
            patient_name = st.text_input("Nom complet", value=st.session_state.patient_info.get("name", ""))
            patient_age = st.number_input("Âge", min_value=0, max_value=120, value=int(st.session_state.patient_info.get("age", 30)))
            patient_sex = st.selectbox("Sexe", ["F", "M"], index=0 if st.session_state.patient_info.get("sex", "F") == "F" else 1)
        with col2:
            patient_date = st.date_input("Date analyse", value=st.session_state.patient_info.get("date", datetime.now().date()))
            patient_notes = st.text_area("Notes médicales", value=st.session_state.patient_info.get("notes", ""), height=90)

        if st.form_submit_button("💾 Enregistrer"):
            st.session_state.patient_info = {
                "name": patient_name,
                "age": patient_age,
                "sex": patient_sex,
                "date": patient_date,
                "notes": patient_notes,
            }
            st.success("✅ Patient enregistré")

    st.divider()
    st.header("📁 Import")

    biology_file = st.file_uploader("Biologie (PDF/Excel)", type=["pdf", "xlsx", "xls"], key="bio_file")
    microbiome_file = st.file_uploader("Microbiote (PDF/Excel)", type=["pdf", "xlsx", "xls"], key="micro_file")

    st.caption(f"📌 Règles attendues: data/Bases_regles_Synlab.xlsx")

    if st.button("🔍 Extraire + Générer", type="primary"):
        if not st.session_state.patient_info.get("name"):
            st.error("❌ Enregistre le patient avant")
        else:
            try:
                # ---------------- BIO ----------------
                if biology_file:
                    st.info("🔄 Extraction biologie...")
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

                # ---------------- MICRO ----------------
                if microbiome_file:
                    st.info("🔄 Extraction microbiote...")
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

                # ---------------- RULES ----------------
                if not os.path.exists(RULES_EXCEL_PATH):
                    st.error(f"❌ Fichier règles introuvable: {RULES_EXCEL_PATH}")
                    st.stop()

                st.info("🤖 Génération recommandations (Rules Engine)...")

                # ✅ Convert dict -> df + Valeur->float
                biology_df = _dict_bio_to_dataframe(st.session_state.biology_data)

                # ✅ micro: cast dysbiosis_index if present
                if isinstance(st.session_state.microbiome_data, dict) and "dysbiosis_index" in st.session_state.microbiome_data:
                    try:
                        st.session_state.microbiome_data["dysbiosis_index"] = int(st.session_state.microbiome_data["dysbiosis_index"])
                    except Exception:
                        pass

                patient_fmt = _patient_to_rules_engine_format(st.session_state.patient_info)

                engine = RulesEngine(RULES_EXCEL_PATH)
                st.session_state.recommendations = engine.generate_recommendations(
                    biology_data=biology_df,
                    microbiome_data=st.session_state.microbiome_data,
                    patient_info=patient_fmt,
                )

                st.session_state.edited_recommendations = _format_recos_for_editing(st.session_state.recommendations)
                st.session_state.data_extracted = True
                st.success("✅ Recommandations générées")

            except Exception as e:
                st.error(f"❌ Erreur extraction: {str(e)}")


# ---------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------
if st.session_state.patient_info.get("name"):
    st.markdown(
        f"""
<div class="patient-info">
  <b>👤 {st.session_state.patient_info.get('name','')}</b><br/>
  Âge: {st.session_state.patient_info.get('age','')} ans | Sexe: {st.session_state.patient_info.get('sex','')} |
  Date: {st.session_state.patient_info.get('date','')}
</div>
""",
        unsafe_allow_html=True,
    )

    if st.session_state.data_extracted:
        tab1, tab2, tab3 = st.tabs(["📊 Biologie", "🦠 Microbiote", "📝 Recos"])

        with tab1:
            st.subheader("📊 Biologie (DataFrame envoyé au RulesEngine)")
            df_bio = _dict_bio_to_dataframe(st.session_state.biology_data)
            if df_bio.empty:
                st.info("Aucune donnée biologie.")
            else:
                st.dataframe(df_bio, use_container_width=True)

        with tab2:
            st.subheader("🦠 Microbiote (json)")
            st.json(st.session_state.microbiome_data or {})

        with tab3:
            st.subheader("📝 Recommandations (éditables)")
            if not st.session_state.edited_recommendations:
                st.warning("Aucune recommandation générée.")
            else:
                for section, txt in st.session_state.edited_recommendations.items():
                    st.markdown(f"### {section}")
                    st.session_state.edited_recommendations[section] = st.text_area(
                        f"Texte - {section}",
                        value=txt,
                        height=220,
                        key=f"edit_{section}",
                    )
                    st.divider()

                export = {
                    "patient": st.session_state.patient_info,
                    "biology_df": _dict_bio_to_dataframe(st.session_state.biology_data).to_dict(orient="records"),
                    "microbiome": st.session_state.microbiome_data,
                    "recommendations_raw": st.session_state.recommendations,
                    "recommendations_edited": st.session_state.edited_recommendations,
                    "export_date": datetime.now().isoformat(),
                }

                st.download_button(
                    "⬇️ Télécharger export JSON",
                    data=pd.Series(export).to_json(),
                    file_name=f"algolife_export_{st.session_state.patient_info['name'].replace(' ', '_')}.json",
                    mime="application/json",
                )
else:
    st.info("👈 Enregistre d’abord le patient dans la sidebar.")
