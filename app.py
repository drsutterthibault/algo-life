"""
UNILABS - Plateforme Multimodale d'Analyse Bio-Fonctionnelle (ALGO-LIFE Engine)
Streamlit App - Import (PDF/Excel) + Extraction + Rules Engine

PATCHED UI:
- Branding Unilabs
- Sidebar: Antécédents médicaux (au lieu de Notes médicales)
- Ajout poids/taille + IMC
- Onglets sous la bannière
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
        s = re.sub(r"[^0-9\.\-\+eE]", "", s)
        return float(s) if s else None
    except Exception:
        return None


def _calc_bmi(weight_kg: Any, height_cm: Any):
    w = _safe_float(weight_kg)
    h = _safe_float(height_cm)
    if w is None or h is None or h <= 0:
        return None
    hm = h / 100.0
    if hm <= 0:
        return None
    return w / (hm * hm)


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

    # On passe "notes" = antécédents (pour que RulesEngine garde le champ sans casser)
    antecedents = (patient_info or {}).get("antecedents", "")

    return {
        "nom": (patient_info or {}).get("name", ""),
        "age": (patient_info or {}).get("age", None),
        "genre": genre,
        "date": str((patient_info or {}).get("date", "")),
        "notes": antecedents,
    }


def _format_recos_for_editing(recos: Dict[str, Any]) -> Dict[str, str]:
    """
    Make editable text blocks from RulesEngine output.
    Works even if some keys are missing.
    """
    out = {}

    pa = recos.get("priority_actions", []) or []
    out["Actions prioritaires"] = "\n".join([f"• {x}" for x in pa]) if pa else ""

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
    out["Interprétation biologie"] = "\n".join(lines).strip()

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
    out["Interprétation microbiote"] = "\n".join(mlines).strip()

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
    margin-bottom: 1.0rem;
}
.main-header h1 { margin: 0; font-size: 2.0rem; }
.main-header .sub { opacity: 0.95; margin-top: 0.35rem; font-size: 0.98rem; }

.patient-strip {
    background: #f6f8fb;
    padding: 0.85rem 1rem;
    border-radius: 12px;
    border-left: 5px solid #1F6AA5;
    margin: 0.5rem 0 1rem 0;
}

.mini-box {
    background: #ffffff;
    border: 1px solid #e8edf3;
    border-radius: 12px;
    padding: 0.7rem 0.8rem;
}
.mini-title { font-weight: 700; margin-bottom: 0.35rem; }
.small-note { color: rgba(255,255,255,0.9); font-size: 0.92rem; }
.small-muted { color: #5b6572; font-size: 0.9rem; }
hr { border: none; border-top: 1px solid #eceff4; margin: 0.9rem 0; }
</style>
""",
    unsafe_allow_html=True,
)

# ✅ Bannière
st.markdown(
    """
<div class="main-header">
  <h1>UNILABS · Plateforme Multimodale</h1>
  <div class="sub">Analyse bio-fonctionnelle + microbiote · Extraction (PDF/Excel) · Interprétation · Recommandations (Rules Engine)</div>
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
        # Identité
        patient_name = st.text_input("Nom complet", value=st.session_state.patient_info.get("name", ""))

        cols = st.columns(3)
        with cols[0]:
            patient_age = st.number_input(
                "Âge", min_value=0, max_value=120, value=int(st.session_state.patient_info.get("age", 30))
            )
        with cols[1]:
            patient_sex = st.selectbox(
                "Sexe", ["F", "M"], index=0 if st.session_state.patient_info.get("sex", "F") == "F" else 1
            )
        with cols[2]:
            patient_date = st.date_input(
                "Date analyse", value=st.session_state.patient_info.get("date", datetime.now().date())
            )

        # Morphologie
        cols2 = st.columns(2)
        with cols2[0]:
            patient_weight = st.number_input(
                "Poids (kg)",
                min_value=0.0,
                max_value=300.0,
                value=float(st.session_state.patient_info.get("weight_kg", 70.0)),
                step=0.1,
            )
        with cols2[1]:
            patient_height = st.number_input(
                "Taille (cm)",
                min_value=0.0,
                max_value=250.0,
                value=float(st.session_state.patient_info.get("height_cm", 170.0)),
                step=0.1,
            )

        bmi = _calc_bmi(patient_weight, patient_height)
        if bmi is None:
            st.caption("IMC: —")
        else:
            st.caption(f"IMC: **{bmi:.1f}**")

        # ✅ Antécédents médicaux (petit cadre)
        st.markdown('<div class="mini-box">', unsafe_allow_html=True)
        st.markdown('<div class="mini-title">Antécédents médicaux</div>', unsafe_allow_html=True)
        patient_antecedents = st.text_area(
            "",
            value=st.session_state.patient_info.get("antecedents", ""),
            height=80,
            placeholder="Ex: HTA, diabète, thyroïde, traitements, ATCD familiaux…",
            label_visibility="collapsed",
        )
        st.markdown("</div>", unsafe_allow_html=True)

        if st.form_submit_button("💾 Enregistrer"):
            st.session_state.patient_info = {
                "name": patient_name,
                "age": patient_age,
                "sex": patient_sex,
                "date": patient_date,
                "weight_kg": float(patient_weight),
                "height_cm": float(patient_height),
                "bmi": bmi,
                "antecedents": patient_antecedents,
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
# MAIN CONTENT
# ---------------------------------------------------------------------
patient = st.session_state.patient_info

# ✅ Bandeau patient + IMC
if patient.get("name"):
    bmi = patient.get("bmi", None)
    bmi_txt = "—" if bmi is None else f"{float(bmi):.1f}"

    antecedents = patient.get("antecedents", "").strip()
    antecedents_preview = antecedents if antecedents else "—"

    st.markdown(
        f"""
<div class="patient-strip">
  <div><b>👤 {patient.get('name','')}</b></div>
  <div class="small-muted">
    Âge: {patient.get('age','')} ans · Sexe: {patient.get('sex','')} · Date: {patient.get('date','')}
    · Poids: {patient.get('weight_kg','—')} kg · Taille: {patient.get('height_cm','—')} cm · IMC: <b>{bmi_txt}</b>
  </div>
  <div class="small-muted" style="margin-top:0.35rem;">
    <b>Antécédents:</b> {antecedents_preview}
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    # ✅ Onglets sous la bannière (comme demandé)
    tab1, tab2, tab3 = st.tabs(["📊 Analyse", "🧠 Interprétation", "📝 Recommandations"])

    with tab1:
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
            if st.session_state.microbiome_data:
                st.json(st.session_state.microbiome_data)
            else:
                st.info("Aucune donnée microbiote importée.")

    with tab2:
        st.subheader("🧠 Interprétation (rules engine)")
        if not st.session_state.recommendations:
            st.warning("Aucune interprétation disponible (génère d'abord).")
        else:
            # On affiche brut + blocs (interprétation)
            st.markdown("### Actions prioritaires")
            pa = st.session_state.recommendations.get("priority_actions", []) or []
            if pa:
                st.write("\n".join([f"- {x}" for x in pa]))
            else:
                st.write("—")

            st.markdown("### Détails interprétation (biologie + microbiote + analyse croisée)")
            st.json(st.session_state.recommendations)

    with tab3:
        st.subheader("📝 Recommandations (éditables)")
        if not st.session_state.data_extracted or not st.session_state.edited_recommendations:
            st.warning("Aucune recommandation éditable (génère d'abord).")
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
                file_name=f"unilabs_export_{patient.get('name','patient').replace(' ', '_')}.json",
                mime="application/json",
            )

else:
    st.info("👈 Commence par enregistrer un patient dans la sidebar.")
