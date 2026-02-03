"""
ALGO-LIFE - Plateforme Médecin
Application Streamlit pour l'analyse multimodale de santé
PATCH: chemin règles + compat RulesEngine (DataFrame bio)
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import sys
import os
import tempfile
from typing import Dict, Any, Optional

# ---------------------------------------------------------------------
# PATHS / IMPORTS
# ---------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from extractors import extract_synlab_biology, extract_idk_microbiome  # noqa
from rules_engine import RulesEngine  # noqa

# Chemin robuste vers le fichier Excel des règles
RULES_EXCEL_PATH = os.path.join(BASE_DIR, "data", "Bases_regles_Synlab.xlsx")


# ---------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------
def _file_to_temp_path(uploaded_file, suffix: str) -> str:
    """Sauve un UploadedFile Streamlit en fichier temporaire, renvoie le path."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.read())
        return tmp.name


def _dict_bio_to_dataframe(bio_dict: Dict[str, Any]) -> pd.DataFrame:
    """
    Convertit un dict de biomarqueurs en DataFrame compatible RulesEngine.
    Attendu par rules_engine.py: colonnes 'Biomarqueur','Valeur','Unité','Référence'
    """
    rows = []
    for name, data in (bio_dict or {}).items():
        if name is None:
            continue
        biomarker = str(name).strip()
        if not biomarker or biomarker.lower() == "nan":
            continue

        if isinstance(data, dict):
            value = data.get("value", data.get("Valeur", ""))
            unit = data.get("unit", data.get("Unité", ""))
            ref = data.get("reference", data.get("Référence", ""))
        else:
            value = data
            unit = ""
            ref = ""

        rows.append(
            {
                "Biomarqueur": biomarker,
                "Valeur": value,
                "Unité": unit,
                "Référence": ref,
            }
        )

    return pd.DataFrame(rows)


def _patient_to_rules_engine_format(patient_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    rules_engine.py utilise patient_info['genre'] == 'Homme' pour déterminer H/F.
    On mappe depuis ton formulaire (sex 'M'/'F').
    """
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
    Transforme la structure de recos du RulesEngine en textes éditables par section.
    """
    out = {}

    # Actions prioritaires
    pa = recos.get("priority_actions", []) or []
    out["Actions prioritaires"] = "\n".join([f"• {x}" for x in pa]) if pa else ""

    # Interprétations biologie
    bio = recos.get("biology_interpretations", []) or []
    bio_lines = []
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
        bio_lines.append(header)
        if interp:
            bio_lines.append(f"Interprétation: {interp}")
        if nutr:
            bio_lines.append(f"Nutrition: {nutr}")
        if micro:
            bio_lines.append(f"Micronutrition: {micro}")
        if life:
            bio_lines.append(f"Lifestyle: {life}")
        bio_lines.append("")  # séparation

    out["Biologie"] = "\n".join(bio_lines).strip()

    # Microbiome
    micro = recos.get("microbiome_interpretations", []) or []
    micro_lines = []
    for m in micro:
        title = m.get("title") or m.get("group") or ""
        status = m.get("status", "")
        interp = m.get("interpretation", "")
        reco = m.get("recommendations", "")

        line = f"{title} — {status}".strip()
        micro_lines.append(line)
        if interp:
            micro_lines.append(f"Interprétation: {interp}")
        if reco:
            micro_lines.append(f"Reco: {reco}")
        micro_lines.append("")

    summary = recos.get("microbiome_summary", {}) or {}
    if summary:
        micro_lines.insert(0, f"Résumé microbiote: {summary}")
        micro_lines.insert(1, "")

    out["Microbiote"] = "\n".join(micro_lines).strip()

    # Analyse croisée
    cross = recos.get("cross_analysis", []) or []
    cross_lines = []
    for c in cross:
        t = c.get("title", "")
        d = c.get("description", "")
        r = c.get("recommendations", "")
        if t:
            cross_lines.append(t)
        if d:
            cross_lines.append(d)
        if r:
            cross_lines.append(f"Reco: {r}")
        cross_lines.append("")
    out["Analyse croisée"] = "\n".join(cross_lines).strip()

    return out


# ---------------------------------------------------------------------
# STREAMLIT PAGE
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
    padding: 1.5rem;
    border-radius: 10px;
    color: white;
    margin-bottom: 2rem;
}
.patient-info {
    background: #f8f9ff;
    padding: 1rem;
    border-radius: 8px;
    border-left: 4px solid #667eea;
    margin-bottom: 1rem;
}
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
<div class="main-header">
  <h1>🧬 ALGO-LIFE</h1>
  <h3>Plateforme Médecin - Analyse Multimodale</h3>
  <p>Extraction automatique + Recommandations (Rules Engine) + Édition</p>
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
    st.header("👤 Informations Patient")

    with st.form("patient_form"):
        col1, col2 = st.columns(2)
        with col1:
            patient_name = st.text_input("Nom complet", value=st.session_state.patient_info.get("name", ""))
            patient_age = st.number_input(
                "Âge", min_value=0, max_value=120, value=int(st.session_state.patient_info.get("age", 30))
            )
            patient_sex = st.selectbox(
                "Sexe", ["F", "M"], index=0 if st.session_state.patient_info.get("sex", "F") == "F" else 1
            )
        with col2:
            patient_date = st.date_input(
                "Date analyse", value=st.session_state.patient_info.get("date", datetime.now().date())
            )
            patient_notes = st.text_area("Notes médicales", value=st.session_state.patient_info.get("notes", ""), height=100)

        submitted = st.form_submit_button("💾 Enregistrer Patient")
        if submitted:
            st.session_state.patient_info = {
                "name": patient_name,
                "age": patient_age,
                "sex": patient_sex,
                "date": patient_date,
                "notes": patient_notes,
            }
            st.success("✅ Informations patient enregistrées")

    st.divider()
    st.header("📁 Import Fichiers")

    biology_file = st.file_uploader("Biologie (PDF ou Excel)", type=["pdf", "xlsx", "xls"], key="biology_upload")
    microbiome_file = st.file_uploader("Microbiote (PDF ou Excel)", type=["pdf", "xlsx", "xls"], key="microbiome_upload")

    if st.button("🔍 Extraire + Générer recommandations", type="primary"):
        if not st.session_state.patient_info.get("name"):
            st.error("❌ Veuillez d'abord enregistrer les informations patient")
        else:
            try:
                # ------------------ BIOLOGY ------------------
                if biology_file:
                    st.info("🔄 Extraction biologie...")

                    if biology_file.type == "application/pdf":
                        tmp_path = _file_to_temp_path(biology_file, ".pdf")
                        try:
                            st.session_state.biology_data = extract_synlab_biology(tmp_path)
                        finally:
                            try:
                                os.unlink(tmp_path)
                            except Exception:
                                pass
                    else:
                        # Excel -> dict simple (col0=nom, col1=val, col2=unit, col3=ref si présent)
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

                    st.success(f"✅ Biologie: {len(st.session_state.biology_data)} biomarqueurs")

                # ------------------ MICROBIOME ------------------
                if microbiome_file:
                    st.info("🔄 Extraction microbiote...")

                    if microbiome_file.type == "application/pdf":
                        tmp_path = _file_to_temp_path(microbiome_file, ".pdf")
                        try:
                            st.session_state.microbiome_data = extract_idk_microbiome(tmp_path)
                        finally:
                            try:
                                os.unlink(tmp_path)
                            except Exception:
                                pass
                    else:
                        # Excel -> dict simple (peut être adapté ensuite)
                        df_micro = pd.read_excel(microbiome_file)
                        micro_dict = {"bacteria": []}
                        for _, row in df_micro.iterrows():
                            if len(row) < 2:
                                continue
                            group = str(row.iloc[0]).strip()
                            val = row.iloc[1]
                            if not group or group.lower() == "nan":
                                continue
                            micro_dict["bacteria"].append({"group": group, "result": val})
                        st.session_state.microbiome_data = micro_dict

                    st.success("✅ Microbiote importé")

                # ------------------ RULES ENGINE ------------------
                if not os.path.exists(RULES_EXCEL_PATH):
                    st.error(f"❌ Fichier des règles introuvable: {RULES_EXCEL_PATH}")
                    st.info("💡 Vérifie: data/Bases_regles_Synlab.xlsx (exactement ce nom) dans ton repo")
                else:
                    st.info("🤖 Génération recommandations (Rules Engine)...")

                    rules_engine = RulesEngine(RULES_EXCEL_PATH)

                    # ✅ FIX: dict -> DataFrame pour la biologie (sinon .empty plante)
                    biology_df = _dict_bio_to_dataframe(st.session_state.biology_data)

                    # Patient format attendu
                    patient_fmt = _patient_to_rules_engine_format(st.session_state.patient_info)

                    # Appel compatible rules_engine.py
                    st.session_state.recommendations = rules_engine.generate_recommendations(
                        biology_data=biology_df,
                        microbiome_data=st.session_state.microbiome_data,
                        patient_info=patient_fmt,
                    )

                    # Préparer textes éditables
                    st.session_state.edited_recommendations = _format_recos_for_editing(st.session_state.recommendations)

                    st.session_state.data_extracted = True
                    st.success("✅ Recommandations générées")

            except Exception as e:
                st.error(f"❌ Erreur extraction: {str(e)}")


# ---------------------------------------------------------------------
# MAIN UI
# ---------------------------------------------------------------------
if st.session_state.patient_info.get("name"):
    st.markdown(
        f"""
<div class="patient-info">
  <h3>👤 {st.session_state.patient_info.get('name','')}</h3>
  <p>
    <strong>Âge:</strong> {st.session_state.patient_info.get('age','')} ans |
    <strong>Sexe:</strong> {st.session_state.patient_info.get('sex','')} |
    <strong>Date:</strong> {st.session_state.patient_info.get('date','')}
  </p>
  {f"<p><strong>Notes:</strong> {st.session_state.patient_info.get('notes','')}</p>" if st.session_state.patient_info.get('notes') else ""}
</div>
""",
        unsafe_allow_html=True,
    )

    if st.session_state.data_extracted:
        tab1, tab2, tab3 = st.tabs(["📊 Biomarqueurs", "🦠 Microbiote", "📝 Recommandations"])

        with tab1:
            st.header("📊 Biologie")
            df_bio = _dict_bio_to_dataframe(st.session_state.biology_data)
            if not df_bio.empty:
                st.dataframe(df_bio, use_container_width=True)
            else:
                st.info("Aucune donnée de biologie")

        with tab2:
            st.header("🦠 Microbiote")
            st.json(st.session_state.microbiome_data or {})

        with tab3:
            st.header("📝 Recommandations (éditables)")
            if not st.session_state.edited_recommendations:
                st.warning("⚠️ Aucune recommandation.")
            else:
                for section, txt in st.session_state.edited_recommendations.items():
                    st.subheader(section)
                    st.session_state.edited_recommendations[section] = st.text_area(
                        f"Texte - {section}",
                        value=txt,
                        height=220,
                        key=f"edit_{section}",
                    )
                    st.divider()

                # Export JSON
                export = {
                    "patient": st.session_state.patient_info,
                    "biology_df": _dict_bio_to_dataframe(st.session_state.biology_data).to_dict(orient="records"),
                    "microbiome": st.session_state.microbiome_data,
                    "recommendations_raw": st.session_state.recommendations,
                    "recommendations_edited": st.session_state.edited_recommendations,
                    "export_date": datetime.now().isoformat(),
                }

                st.download_button(
                    "⬇️ Télécharger JSON (export complet)",
                    data=pd.Series(export).to_json(),
                    file_name=f"algolife_export_{st.session_state.patient_info['name'].replace(' ', '_')}.json",
                    mime="application/json",
                )
else:
    st.info("👈 Commence par enregistrer les informations patient dans la sidebar.")
