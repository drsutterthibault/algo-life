import streamlit as st
import pandas as pd
from datetime import datetime
import sys
import os

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
    .patient-card {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 8px;
        border-left: 4px solid #667eea;
        margin-bottom: 1rem;
    }
    .upload-zone {
        border: 2px dashed #667eea;
        border-radius: 8px;
        padding: 2rem;
        text-align: center;
        background: #f8f9fa;
        margin: 1rem 0;
    }
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin: 0.5rem 0;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 1rem 2rem;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# Initialisation de la session
if 'patient_data' not in st.session_state:
    st.session_state.patient_data = {}
if 'biology_data' not in st.session_state:
    st.session_state.biology_data = None
if 'microbiome_data' not in st.session_state:
    st.session_state.microbiome_data = None
if 'rules_engine' not in st.session_state:
    st.session_state.rules_engine = None
if 'recommendations' not in st.session_state:
    st.session_state.recommendations = None

# En-tête
st.markdown("""
<div class="main-header">
    <h1>🧬 ALGO-LIFE</h1>
    <p style="margin: 0; opacity: 0.9;">PLATEFORME MÉDECIN - Analyse Multimodale de Santé</p>
    <p style="margin: 0; font-size: 0.85rem; opacity: 0.8;">Beta v1.0</p>
</div>
""", unsafe_allow_html=True)

# Sidebar pour la navigation
with st.sidebar:
    st.image("https://via.placeholder.com/150x50/667eea/ffffff?text=ALGO-LIFE", width=150)
    st.markdown("---")
    
    # Informations de l'utilisateur
    st.markdown("### 👤 Thibault SU")
    st.caption("Biologiste - Product Manager")
    
    st.markdown("---")
    
    # Menu de navigation
    st.markdown("### 📋 Navigation")
    page = st.radio(
        "",
        ["Import & Données", "Interprétation", "Recommandations", "Suivi", "Export PDF"],
        label_visibility="collapsed"
    )

# PAGE 1: IMPORT & DONNÉES
if page == "Import & Données":
    st.markdown("## 📥 Import & Données")
    
    # Section Information Patient
    with st.expander("👤 Information Patient", expanded=True):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            genre = st.selectbox("Genre", ["Homme", "Femme", "Autre"])
            date_naissance = st.date_input("Date de Naissance", value=datetime(1987, 10, 3))
        
        with col2:
            poids = st.number_input("Poids (kg)", value=73.0, step=0.1)
            taille = st.number_input("Taille (cm)", value=175.0, step=0.1)
        
        with col3:
            activite = st.selectbox("Activité", 
                ["Sédentaire (0-1h/semaine)", 
                 "Légère (1-3h/semaine)", 
                 "Active (3-5h/semaine)",
                 "Très active (>5h/semaine)"])
        
        # Calcul IMC
        if poids > 0 and taille > 0:
            imc = poids / ((taille/100) ** 2)
            st.info(f"**IMC calculé:** {imc:.1f} kg/m²")
        
        # Symptômes
        st.markdown("**Symptômes:**")
        symptomes = st.multiselect(
            "Sélectionner les symptômes",
            ["Fatigue chronique", "Troubles digestifs", "Douleurs articulaires", 
             "Troubles du sommeil", "Anxiété/Dépression", "Prise de poids",
             "Troubles cutanés", "Autres"],
            default=["Fatigue chronique"]
        )
        
        # Antécédents médicaux
        antecedents = st.text_area("Antécédents médicaux", 
                                   placeholder="Exemple: Hypothyroïdie, traitement en cours...",
                                   height=100)
        
        # Sauvegarder les données patient
        st.session_state.patient_data = {
            'genre': genre,
            'date_naissance': date_naissance,
            'poids': poids,
            'taille': taille,
            'imc': imc if poids > 0 and taille > 0 else 0,
            'activite': activite,
            'symptomes': symptomes,
            'antecedents': antecedents
        }
    
    # Section Importation Multimodale
    st.markdown("---")
    st.markdown("## 📁 Zone d'importation Multimodale")
    st.caption("Chargez un ou plusieurs rapports pour lancer l'analyse croisée.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🧪 Rapport de Biologie")
        st.markdown('<div class="upload-zone">', unsafe_allow_html=True)
        
        biology_file = st.file_uploader(
            "Charger un rapport Synlab (PDF ou Excel)",
            type=['pdf', 'xlsx', 'xls'],
            key="biology_upload",
            help="Format accepté: PDF Synlab ou fichier Excel avec résultats biologiques"
        )
        
        if biology_file:
            try:
                file_extension = biology_file.name.split('.')[-1].lower()
                
                with st.spinner("Extraction des données biologiques..."):
                    if file_extension == 'pdf':
                        # Sauvegarder temporairement le PDF
                        temp_path = f"/tmp/{biology_file.name}"
                        with open(temp_path, 'wb') as f:
                            f.write(biology_file.getbuffer())
                        
                        # Extraire les données
                        biology_data = extract_synlab_biology(temp_path)
                        st.session_state.biology_data = biology_data
                        
                        st.success(f"✅ {len(biology_data)} biomarqueurs extraits")
                        
                        # Aperçu des données
                        if st.checkbox("Afficher les données extraites", key="show_bio"):
                            st.dataframe(biology_data, use_container_width=True)
                    
                    elif file_extension in ['xlsx', 'xls']:
                        # Lire le fichier Excel
                        df = pd.read_excel(biology_file)
                        st.session_state.biology_data = df
                        
                        st.success(f"✅ {len(df)} lignes importées")
                        
                        if st.checkbox("Afficher les données", key="show_bio_excel"):
                            st.dataframe(df, use_container_width=True)
                            
            except Exception as e:
                st.error(f"❌ Erreur lors de l'extraction: {str(e)}")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown("### 🦠 Rapport de Microbiote")
        st.markdown('<div class="upload-zone">', unsafe_allow_html=True)
        
        microbiome_file = st.file_uploader(
            "Charger un rapport IDK GutMAP (PDF ou Excel)",
            type=['pdf', 'xlsx', 'xls'],
            key="microbiome_upload",
            help="Format accepté: PDF IDK GutMAP ou fichier Excel avec résultats microbiote"
        )
        
        if microbiome_file:
            try:
                file_extension = microbiome_file.name.split('.')[-1].lower()
                
                with st.spinner("Extraction des données microbiote..."):
                    if file_extension == 'pdf':
                        # Sauvegarder temporairement le PDF
                        temp_path = f"/tmp/{microbiome_file.name}"
                        with open(temp_path, 'wb') as f:
                            f.write(microbiome_file.getbuffer())
                        
                        # Extraire les données
                        microbiome_data = extract_idk_microbiome(temp_path)
                        st.session_state.microbiome_data = microbiome_data
                        
                        st.success(f"✅ Dysbiosis Index: {microbiome_data.get('dysbiosis_index', 'N/A')}")
                        st.info(f"Diversité: {microbiome_data.get('diversity', 'N/A')}")
                        
                        # Aperçu des bactéries
                        if st.checkbox("Afficher les bactéries extraites", key="show_microbiome"):
                            bacteria_df = pd.DataFrame(microbiome_data.get('bacteria', []))
                            if not bacteria_df.empty:
                                st.dataframe(bacteria_df, use_container_width=True)
                    
                    elif file_extension in ['xlsx', 'xls']:
                        df = pd.read_excel(microbiome_file)
                        st.session_state.microbiome_data = {'raw_data': df}
                        
                        st.success(f"✅ {len(df)} lignes importées")
                        
                        if st.checkbox("Afficher les données", key="show_micro_excel"):
                            st.dataframe(df, use_container_width=True)
                            
            except Exception as e:
                st.error(f"❌ Erreur lors de l'extraction: {str(e)}")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Bouton pour lancer l'analyse
    st.markdown("---")
    if st.button("🚀 Lancer l'Analyse Multimodale", type="primary", use_container_width=True):
        if st.session_state.biology_data is not None or st.session_state.microbiome_data is not None:
            with st.spinner("Analyse en cours..."):
                try:
                    # Charger le fichier de règles (à adapter selon votre chemin)
                    rules_path = "/mnt/user-data/uploads/1770033776484_Bases_re_lgles_Synlab.xlsx"
                    
                    # Initialiser le moteur de règles
                    engine = RulesEngine(rules_path)
                    st.session_state.rules_engine = engine
                    
                    # Générer les recommandations
                    recommendations = engine.generate_recommendations(
                        biology_data=st.session_state.biology_data,
                        microbiome_data=st.session_state.microbiome_data,
                        patient_info=st.session_state.patient_data
                    )
                    st.session_state.recommendations = recommendations
                    
                    st.success("✅ Analyse terminée ! Consultez l'onglet Interprétation et Recommandations.")
                    
                except Exception as e:
                    st.error(f"❌ Erreur lors de l'analyse: {str(e)}")
        else:
            st.warning("⚠️ Veuillez importer au moins un fichier de rapport.")

# PAGE 2: INTERPRÉTATION
elif page == "Interprétation":
    st.markdown("## 🔍 Interprétation")
    
    if st.session_state.recommendations is None:
        st.info("ℹ️ Aucune analyse disponible. Importez des données dans l'onglet 'Import & Données'.")
    else:
        reco = st.session_state.recommendations
        
        # Résumé global
        st.markdown("### 📊 Résumé Global")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Biomarqueurs analysés", 
                     len(reco.get('biology_interpretations', [])))
        
        with col2:
            st.metric("Dysbiosis Index",
                     reco.get('microbiome_summary', {}).get('dysbiosis_index', 'N/A'))
        
        with col3:
            anomalies = len([b for b in reco.get('biology_interpretations', []) 
                           if b.get('status') != 'Normal'])
            st.metric("Anomalies détectées", anomalies)
        
        with col4:
            st.metric("Niveau de priorité",
                     "Élevé" if anomalies > 5 else "Modéré" if anomalies > 2 else "Faible",
                     delta=None)
        
        # Interprétations biologiques
        if reco.get('biology_interpretations'):
            st.markdown("---")
            st.markdown("### 🧪 Interprétations Biologiques")
            
            for interp in reco['biology_interpretations']:
                with st.expander(f"{interp['biomarker']} - {interp['status']}", 
                               expanded=interp['status'] != 'Normal'):
                    col1, col2 = st.columns([1, 2])
                    
                    with col1:
                        st.markdown(f"**Valeur:** {interp['value']} {interp.get('unit', '')}")
                        st.markdown(f"**Référence:** {interp.get('reference', 'N/A')}")
                        st.markdown(f"**Statut:** {interp['status']}")
                    
                    with col2:
                        if interp.get('interpretation'):
                            st.markdown("**Interprétation:**")
                            st.info(interp['interpretation'])
        
        # Interprétations microbiote
        if reco.get('microbiome_interpretations'):
            st.markdown("---")
            st.markdown("### 🦠 Interprétations Microbiote")
            
            for interp in reco['microbiome_interpretations']:
                with st.expander(f"{interp['group']} - {interp['result']}", 
                               expanded=interp['result'] != 'Expected'):
                    st.markdown(f"**Groupe:** {interp['group']}")
                    st.markdown(f"**Résultat:** {interp['result']}")
                    
                    if interp.get('interpretation'):
                        st.markdown("**Interprétation:**")
                        st.info(interp['interpretation'])

# PAGE 3: RECOMMANDATIONS
elif page == "Recommandations":
    st.markdown("## 💊 Recommandations")
    
    if st.session_state.recommendations is None:
        st.info("ℹ️ Aucune recommandation disponible. Importez des données et lancez l'analyse.")
    else:
        reco = st.session_state.recommendations
        
        # Tabs pour les différents types de recommandations
        tab1, tab2, tab3, tab4 = st.tabs(["🥗 Nutrition", "💊 Micronutrition", "🏃 Lifestyle", "🔄 Multimodal"])
        
        with tab1:
            st.markdown("### Recommandations Nutritionnelles")
            if reco.get('biology_interpretations'):
                for interp in reco['biology_interpretations']:
                    if interp.get('nutrition_reco'):
                        with st.expander(f"{interp['biomarker']}"):
                            st.markdown(interp['nutrition_reco'])
            
            if reco.get('microbiome_interpretations'):
                for interp in reco['microbiome_interpretations']:
                    if interp.get('nutrition_reco'):
                        with st.expander(f"{interp['group']}"):
                            st.markdown(interp['nutrition_reco'])
        
        with tab2:
            st.markdown("### Recommandations en Micronutrition")
            if reco.get('biology_interpretations'):
                for interp in reco['biology_interpretations']:
                    if interp.get('micronutrition_reco'):
                        with st.expander(f"{interp['biomarker']}"):
                            st.markdown(interp['micronutrition_reco'])
            
            if reco.get('microbiome_interpretations'):
                for interp in reco['microbiome_interpretations']:
                    if interp.get('supplementation_reco'):
                        with st.expander(f"{interp['group']}"):
                            st.markdown(interp['supplementation_reco'])
        
        with tab3:
            st.markdown("### Recommandations Lifestyle")
            if reco.get('biology_interpretations'):
                for interp in reco['biology_interpretations']:
                    if interp.get('lifestyle_reco'):
                        with st.expander(f"{interp['biomarker']}"):
                            st.markdown(interp['lifestyle_reco'])
            
            if reco.get('microbiome_interpretations'):
                for interp in reco['microbiome_interpretations']:
                    if interp.get('lifestyle_reco'):
                        with st.expander(f"{interp['group']}"):
                            st.markdown(interp['lifestyle_reco'])
        
        with tab4:
            st.markdown("### Analyse Multimodale Croisée")
            if reco.get('cross_analysis'):
                st.info("Cette section présente les corrélations entre biologie et microbiote")
                for analysis in reco['cross_analysis']:
                    st.markdown(f"**{analysis.get('title', 'Analyse')}**")
                    st.write(analysis.get('description', ''))
            else:
                st.info("Aucune analyse croisée disponible pour le moment.")

# PAGE 4: SUIVI
elif page == "Suivi":
    st.markdown("## 📈 Suivi")
    st.info("Fonctionnalité de suivi en développement. Permettra de tracker l'évolution des biomarqueurs dans le temps.")

# PAGE 5: EXPORT PDF
elif page == "Export PDF":
    st.markdown("## 📄 Export PDF")
    
    if st.session_state.recommendations is None:
        st.info("ℹ️ Aucune donnée à exporter. Importez des données et lancez l'analyse.")
    else:
        st.markdown("### Générer le Rapport PDF")
        
        # Options d'export
        include_bio = st.checkbox("Inclure les résultats biologiques", value=True)
        include_micro = st.checkbox("Inclure les résultats microbiote", value=True)
        include_reco = st.checkbox("Inclure les recommandations", value=True)
        
        if st.button("📥 Générer le PDF", type="primary"):
            st.info("Fonctionnalité d'export PDF en développement.")

# Footer
st.markdown("---")
st.caption("ALGO-LIFE © 2026 - Thibault SU | Version Beta v1.0")
