"""
ALGO-LIFE - Plateforme Médecin
Application Streamlit pour l'analyse multimodale de santé
VERSION AVEC RECOMMANDATIONS ÉDITABLES - CORRIGÉE
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import sys
import os
import tempfile

# Ajouter le répertoire courant au path pour les imports
sys.path.insert(0, os.path.dirname(__file__))

from extractors import extract_synlab_biology, extract_idk_microbiome
from rules_engine import RulesEngine

# Configuration de la page
st.set_page_config(
    page_title="ALGO-LIFE - Plateforme Médecin",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personnalisé pour ressembler à l'interface ALGO-LIFE
st.markdown("""
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
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #e0e0e0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        margin-bottom: 1rem;
    }
    .reco-section {
        background: #f0f8ff;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #b3d9ff;
        margin-bottom: 1rem;
    }
    .status-normal {
        color: #28a745;
        font-weight: bold;
    }
    .status-low {
        color: #dc3545;
        font-weight: bold;
    }
    .status-high {
        color: #dc3545;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# CHEMIN VERS LE FICHIER EXCEL DES RÈGLES (robuste Streamlit Cloud)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RULES_EXCEL_PATH = os.path.join(BASE_DIR, "data", "Bases_regles_Synlab.xlsx")

# FONCTION HELPER POUR COMPILER LES RECOMMANDATIONS AUTO
def compile_recommendations_text(reco, category):
    """Compile les recommandations automatiques en un seul texte"""
    text_parts = []
    if isinstance(reco, dict) and category in reco:
        category_recos = reco[category]
        if isinstance(category_recos, list):
            for item in category_recos:
                if isinstance(item, dict):
                    # Format: {title: "...", content: "..."}
                    title = item.get("title", "")
                    content = item.get("content", "")
                    if title and content:
                        text_parts.append(f"• {title}: {content}")
                    elif content:
                        text_parts.append(f"• {content}")
                elif isinstance(item, str):
                    text_parts.append(f"• {item}")
        elif isinstance(category_recos, str):
            text_parts.append(category_recos)
    return "\n".join(text_parts) if text_parts else ""

# HEADER PRINCIPAL
st.markdown("""
<div class="main-header">
    <h1>🧬 ALGO-LIFE</h1>
    <h3>Plateforme Médecin - Analyse Multimodale de Santé Fonctionnelle</h3>
    <p>Extraction automatique + Recommandations IA + Édition manuelle</p>
</div>
""", unsafe_allow_html=True)

# INITIALISATION DES VARIABLES DE SESSION
if 'patient_info' not in st.session_state:
    st.session_state.patient_info = {}
if 'biology_data' not in st.session_state:
    st.session_state.biology_data = {}
if 'microbiome_data' not in st.session_state:
    st.session_state.microbiome_data = {}
if 'recommendations' not in st.session_state:
    st.session_state.recommendations = {}
if 'edited_recommendations' not in st.session_state:
    st.session_state.edited_recommendations = {}
if 'data_extracted' not in st.session_state:
    st.session_state.data_extracted = False

# SIDEBAR - INFORMATIONS PATIENT
with st.sidebar:
    st.header("👤 Informations Patient")

    # Formulaire patient
    with st.form("patient_form"):
        col1, col2 = st.columns(2)

        with col1:
            patient_name = st.text_input("Nom complet", value=st.session_state.patient_info.get('name', ''))
            patient_age = st.number_input("Âge", min_value=0, max_value=120,
                                          value=st.session_state.patient_info.get('age', 30))
            patient_sex = st.selectbox("Sexe", ["F", "M"],
                                       index=0 if st.session_state.patient_info.get('sex', 'F') == 'F' else 1)

        with col2:
            patient_date = st.date_input("Date analyse",
                                         value=st.session_state.patient_info.get('date', datetime.now().date()))
            patient_notes = st.text_area("Notes médicales", value=st.session_state.patient_info.get('notes', ''),
                                         height=100)

        submitted = st.form_submit_button("💾 Enregistrer Patient")

        if submitted:
            st.session_state.patient_info = {
                'name': patient_name,
                'age': patient_age,
                'sex': patient_sex,
                'date': patient_date,
                'notes': patient_notes
            }
            st.success("✅ Informations patient enregistrées")

    st.divider()

    # UPLOAD FILES
    st.header("📁 Import Fichiers")

    biology_file = st.file_uploader(
        "Biologie (PDF ou Excel)",
        type=['pdf', 'xlsx', 'xls'],
        key="biology_upload"
    )

    microbiome_file = st.file_uploader(
        "Microbiote (PDF ou Excel)",
        type=['pdf', 'xlsx', 'xls'],
        key="microbiome_upload"
    )

    if st.button("🔍 Extraire données", type="primary"):
        if not st.session_state.patient_info.get('name'):
            st.error("❌ Veuillez d'abord enregistrer les informations patient")
        else:
            try:
                # EXTRACTION BIOLOGIE
                if biology_file:
                    st.info("🔄 Extraction biologie en cours...")

                    if biology_file.type == "application/pdf":
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                            tmp_file.write(biology_file.read())
                            tmp_path = tmp_file.name
                        st.session_state.biology_data = extract_synlab_biology(tmp_path)
                        os.unlink(tmp_path)
                    else:
                        # Excel
                        df_bio = pd.read_excel(biology_file)
                        # Convert to dict (simple heuristic)
                        st.session_state.biology_data = {}
                        for _, row in df_bio.iterrows():
                            if len(row) >= 2:
                                name = str(row.iloc[0]).strip()
                                val = row.iloc[1]
                                if name and name.lower() != "nan":
                                    st.session_state.biology_data[name] = {
                                        "value": val,
                                        "unit": row.iloc[2] if len(row) > 2 else "",
                                        "reference": row.iloc[3] if len(row) > 3 else ""
                                    }

                    st.success(f"✅ {len(st.session_state.biology_data)} biomarqueurs extraits")

                # EXTRACTION MICROBIOME
                if microbiome_file:
                    st.info("🔄 Extraction microbiote en cours...")

                    if microbiome_file.type == "application/pdf":
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                            tmp_file.write(microbiome_file.read())
                            tmp_path = tmp_file.name
                        st.session_state.microbiome_data = extract_idk_microbiome(tmp_path)
                        os.unlink(tmp_path)
                    else:
                        # Excel
                        df_micro = pd.read_excel(microbiome_file)
                        st.session_state.microbiome_data = {}
                        for _, row in df_micro.iterrows():
                            if len(row) >= 2:
                                name = str(row.iloc[0]).strip()
                                val = row.iloc[1]
                                if name and name.lower() != "nan":
                                    st.session_state.microbiome_data[name] = {
                                        "value": val,
                                        "unit": row.iloc[2] if len(row) > 2 else "",
                                        "reference": row.iloc[3] if len(row) > 3 else ""
                                    }

                    st.success(f"✅ {len(st.session_state.microbiome_data)} paramètres microbiote extraits")

                # GÉNÉRATION RECOMMANDATIONS
                if st.session_state.biology_data or st.session_state.microbiome_data:
                    st.info("🤖 Génération recommandations en cours...")

                    # Charger le moteur de règles
                    if not os.path.exists(RULES_EXCEL_PATH):
                        st.error(f"❌ Fichier des règles introuvable: {RULES_EXCEL_PATH}")
                        st.info("💡 Vérifie que ton fichier est bien dans data/Bases_regles_Synlab.xlsx")
                    else:
                        rules_engine = RulesEngine(RULES_EXCEL_PATH)

                        # Combiner données
                        combined_data = {}
                        combined_data.update(st.session_state.biology_data)
                        combined_data.update(st.session_state.microbiome_data)

                        # Générer recommandations
                        st.session_state.recommendations = rules_engine.generate_recommendations(combined_data)

                        # Initialiser recommandations éditables
                        st.session_state.edited_recommendations = {}
                        for category in st.session_state.recommendations.keys():
                            st.session_state.edited_recommendations[category] = compile_recommendations_text(
                                st.session_state.recommendations, category
                            )

                        st.success("✅ Recommandations générées")
                        st.session_state.data_extracted = True

            except Exception as e:
                st.error(f"❌ Erreur extraction: {str(e)}")

# MAIN CONTENT
if st.session_state.patient_info.get('name'):
    # Affichage infos patient
    st.markdown(f"""
    <div class="patient-info">
        <h3>👤 {st.session_state.patient_info['name']}</h3>
        <p><strong>Âge:</strong> {st.session_state.patient_info['age']} ans | 
           <strong>Sexe:</strong> {st.session_state.patient_info['sex']} | 
           <strong>Date:</strong> {st.session_state.patient_info['date']}</p>
        {f"<p><strong>Notes:</strong> {st.session_state.patient_info['notes']}</p>" if st.session_state.patient_info['notes'] else ""}
    </div>
    """, unsafe_allow_html=True)

    if st.session_state.data_extracted:
        # TABS
        tab1, tab2, tab3 = st.tabs(["📊 Biomarqueurs", "🦠 Microbiote", "📝 Recommandations"])

        with tab1:
            st.header("📊 Résultats Biologie Fonctionnelle")

            if st.session_state.biology_data:
                # Convert dict to dataframe for display
                bio_rows = []
                for name, data in st.session_state.biology_data.items():
                    if isinstance(data, dict):
                        bio_rows.append({
                            "Biomarqueur": name,
                            "Valeur": data.get("value", ""),
                            "Unité": data.get("unit", ""),
                            "Référence": data.get("reference", ""),
                            "Statut": data.get("status", "")
                        })
                    else:
                        bio_rows.append({"Biomarqueur": name, "Valeur": data, "Unité": "", "Référence": "", "Statut": ""})

                df_bio = pd.DataFrame(bio_rows)
                st.dataframe(df_bio, use_container_width=True)
            else:
                st.info("Aucune donnée de biologie importée")

        with tab2:
            st.header("🦠 Résultats Microbiote")

            if st.session_state.microbiome_data:
                micro_rows = []
                for name, data in st.session_state.microbiome_data.items():
                    if isinstance(data, dict):
                        micro_rows.append({
                            "Paramètre": name,
                            "Valeur": data.get("value", ""),
                            "Unité": data.get("unit", ""),
                            "Référence": data.get("reference", ""),
                            "Statut": data.get("status", "")
                        })
                    else:
                        micro_rows.append({"Paramètre": name, "Valeur": data, "Unité": "", "Référence": "", "Statut": ""})

                df_micro = pd.DataFrame(micro_rows)
                st.dataframe(df_micro, use_container_width=True)
            else:
                st.info("Aucune donnée de microbiote importée")

        with tab3:
            st.header("📝 Recommandations (éditables)")

            if st.session_state.recommendations:
                st.info("✍️ Tu peux modifier les recommandations avant export / PDF.")

                for category in st.session_state.edited_recommendations.keys():
                    st.subheader(f"📌 {category}")

                    edited_text = st.text_area(
                        f"Recommandations - {category}",
                        value=st.session_state.edited_recommendations[category],
                        height=200,
                        key=f"edit_{category}"
                    )

                    st.session_state.edited_recommendations[category] = edited_text
                    st.divider()

                # Export JSON
                if st.button("💾 Exporter recommandations (JSON)"):
                    export_data = {
                        "patient": st.session_state.patient_info,
                        "biology": st.session_state.biology_data,
                        "microbiome": st.session_state.microbiome_data,
                        "recommendations_raw": st.session_state.recommendations,
                        "recommendations_edited": st.session_state.edited_recommendations,
                        "export_date": datetime.now().isoformat()
                    }

                    st.download_button(
                        label="⬇️ Télécharger JSON",
                        data=pd.Series(export_data).to_json(),
                        file_name=f"algolife_export_{st.session_state.patient_info['name'].replace(' ', '_')}.json",
                        mime="application/json"
                    )
            else:
                st.warning("⚠️ Aucune recommandation générée. Vérifie les fichiers importés et les règles.")

else:
    st.info("👈 Commence par enregistrer les informations patient dans la sidebar.")
