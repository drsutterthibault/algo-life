"""
ALGO-LIFE - Plateforme Médecin
Application Streamlit pour l'analyse multimodale de santé
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
from pdf_generator import generate_multimodal_report

# Configuration de la page
st.set_page_config(
    page_title="Unilabs - Plateforme Médecin",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personnalisé pour le nouveau design
st.markdown("""
<style>
    /* Header principal */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 1rem;
    }
    
    /* Sidebar améliorée */
    .css-1d391kg, [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #f8f9fa 0%, #e9ecef 100%);
    }
    
    .sidebar-profile {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        margin-bottom: 1.5rem;
        text-align: center;
    }
    
    .profile-name {
        font-size: 1.1rem;
        font-weight: 700;
        color: #667eea;
        margin-bottom: 0.3rem;
    }
    
    .profile-title {
        font-size: 0.85rem;
        color: #6c757d;
        line-height: 1.4;
    }
    
    /* Navigation tabs horizontale */
    .nav-tabs {
        display: flex;
        gap: 0.5rem;
        margin-bottom: 2rem;
        border-bottom: 2px solid #e9ecef;
        padding-bottom: 0.5rem;
    }
    
    .nav-tab {
        padding: 0.75rem 1.5rem;
        background: white;
        border: 1px solid #dee2e6;
        border-radius: 8px 8px 0 0;
        cursor: pointer;
        font-weight: 500;
        color: #495057;
        transition: all 0.3s;
    }
    
    .nav-tab:hover {
        background: #f8f9fa;
        border-color: #667eea;
        color: #667eea;
    }
    
    .nav-tab.active {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-color: #667eea;
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
    
    /* Styling pour les radio buttons */
    .stRadio > label {
        display: none;
    }
</style>
""", unsafe_allow_html=True)

# ===== FONCTION HELPER POUR TRANSFORMER LES DONNÉES ===== 
def prepare_pdf_data():
    """Transforme les données de session en format pour le PDF generator"""
    
    # Données patient
    patient_data = st.session_state.patient_data.copy()
    if 'date_naissance' in patient_data:
        patient_data['date_naissance'] = patient_data['date_naissance'].strftime('%d/%m/%Y')
        # Calculer l'âge
        today = datetime.now()
        birth_date = datetime.strptime(patient_data['date_naissance'], '%d/%m/%Y')
        patient_data['age'] = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    
    patient_data['nom'] = patient_data.get('nom', 'Patient')
    patient_data['prenom'] = patient_data.get('prenom', '')
    
    # Données biologiques
    biology_data = {'categories': {}, 'resume': ''}
    
    if st.session_state.recommendations and st.session_state.recommendations.get('biology_interpretations'):
        # Grouper par catégorie
        categories = {}
        for interp in st.session_state.recommendations['biology_interpretations']:
            category = interp.get('category', 'Général')
            if category not in categories:
                categories[category] = []
            
            marker = {
                'nom': interp['biomarker'],
                'valeur': interp['value'],
                'unite': interp.get('unit', ''),
                'reference': interp.get('reference', ''),
                'statut': 'normal' if interp['status'] == 'Normal' else 'haut' if '↑' in interp['status'] else 'bas',
                'interpretations': [interp.get('interpretation', '')] if interp.get('interpretation') else []
            }
            categories[category].append(marker)
        
        biology_data['categories'] = categories
        
        # Résumé
        anomalies = len([i for i in st.session_state.recommendations['biology_interpretations'] if i['status'] != 'Normal'])
        biology_data['resume'] = f"Analyse de {len(st.session_state.recommendations['biology_interpretations'])} biomarqueurs avec {anomalies} anomalie(s) détectée(s)."
    
    # Données microbiote
    microbiome_data = {}
    
    if st.session_state.recommendations and st.session_state.recommendations.get('microbiome_summary'):
        microbiome_summary = st.session_state.recommendations['microbiome_summary']
        
        microbiome_data['diversite'] = {
            'score': microbiome_summary.get('diversity_score', 0),
            'interpretation': microbiome_summary.get('diversity_interpretation', '')
        }
        
        # Phyla (si disponible)
        if st.session_state.microbiome_data and 'phyla' in st.session_state.microbiome_data:
            microbiome_data['phyla'] = st.session_state.microbiome_data['phyla']
        
        # Espèces clés - VERSION CORRIGÉE
        if st.session_state.recommendations.get('microbiome_interpretations'):
            microbiome_data['especes_cles'] = []
            for interp in st.session_state.recommendations['microbiome_interpretations']:
                if interp.get('result') != 'Expected':
                    # FIX: Vérifier que interpretation existe et n'est pas None
                    interpretation = interp.get('interpretation', '')
                    if interpretation is None:
                        interpretation = ''
                    
                    # Conversion safe en lowercase
                    impact = 'positif' if 'beneficial' in interpretation.lower() else 'negatif'
                    
                    microbiome_data['especes_cles'].append({
                        'nom': interp['group'],
                        'description': interpretation,
                        'impact': impact
                    })
    
    # Analyse croisée
    cross_analysis = {'correlations': [], 'axes_intervention': []}
    
    if st.session_state.recommendations and st.session_state.recommendations.get('cross_analysis'):
        for idx, analysis in enumerate(st.session_state.recommendations['cross_analysis'], 1):
            cross_analysis['correlations'].append({
                'titre': analysis.get('title', f'Corrélation {idx}'),
                'biomarqueur': analysis.get('biology_marker', 'N/A'),
                'microbiote_element': analysis.get('microbiome_marker', 'N/A'),
                'interpretation': analysis.get('description', ''),
                'mecanisme': analysis.get('mechanism', ''),
                'severite': 'moyenne'
            })
        
        # Ajouter des axes d'intervention si disponibles
        if st.session_state.recommendations.get('intervention_axes'):
            for axe in st.session_state.recommendations['intervention_axes']:
                cross_analysis['axes_intervention'].append({
                    'titre': axe.get('title', ''),
                    'description': axe.get('description', ''),
                    'impact': axe.get('expected_impact', '')
                })
    
    # Recommandations
    recommendations = {
        'priorites': [],
        'nutrition': {'privilegier': [], 'limiter': []},
        'supplementation': [],
        'hygiene_vie': {}
    }
    
    if st.session_state.recommendations:
        # Nutrition
        if st.session_state.recommendations.get('biology_interpretations'):
            for interp in st.session_state.recommendations['biology_interpretations']:
                if interp.get('nutrition_reco'):
                    recommendations['nutrition']['privilegier'].append({
                        'nom': interp['biomarker'],
                        'raison': interp['nutrition_reco']
                    })
                
                if interp.get('micronutrition_reco'):
                    recommendations['supplementation'].append({
                        'nom': interp['biomarker'],
                        'dosage': 'Voir protocole',
                        'frequence': '1x/jour',
                        'duree': '3 mois',
                        'objectif': interp['micronutrition_reco'][:100]
                    })
    
    # Suivi
    follow_up = {
        'controles': [
            {
                'type': 'Bilan biologique de contrôle',
                'delai': '6-8 semaines',
                'biomarqueurs': ['Biomarqueurs anormaux identifiés']
            },
            {
                'type': 'Analyse microbiote (si applicable)',
                'delai': '3 mois',
                'biomarqueurs': ['Diversité', 'Espèces clés']
            }
        ]
    }
    
    return {
        'patient': patient_data,
        'biologie': biology_data,
        'microbiote': microbiome_data,
        'cross_analysis': cross_analysis,
        'recommendations': recommendations,
        'follow_up': follow_up
    }
# ========================================================

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
if 'current_page' not in st.session_state:
    st.session_state.current_page = "Import & Données"

# Sidebar avec profil utilisateur amélioré
with st.sidebar:
    st.markdown("""
    <div class="sidebar-profile">
        <div class="profile-name">Dr Thibault SUTTER</div>
        <div class="profile-title">Biologiste<br>spécialisé en biologie fonctionnelle</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Informations complémentaires
    st.markdown("### 📊 Statistiques")
    st.metric("Analyses en cours", "0")
    st.metric("Rapports générés", "0")
    
    st.markdown("---")
    
    # Liens utiles
    st.markdown("### 🔗 Liens utiles")
    st.markdown("• [Documentation](https://algo-life.com)")
    st.markdown("• [Support](mailto:support@algo-life.com)")
    st.markdown("• [FAQ](https://algo-life.com/faq)")

# En-tête principal avec Unilabs
st.markdown("""
<div class="main-header">
    <h1>🧬 Unilabs</h1>
    <p style="margin: 0; opacity: 0.9;">PLATEFORME MÉDECIN - Analyse Multimodale de Santé</p>
    <p style="margin: 0; font-size: 0.85rem; opacity: 0.8;">Beta v1.0 - Powered by ALGO-LIFE</p>
</div>
""", unsafe_allow_html=True)

# Navigation horizontale sous le header
col1, col2, col3, col4, col5, col_spacer = st.columns([1.5, 1.2, 1.3, 0.8, 1.2, 3])

with col1:
    if st.button("📥 Import & Données", use_container_width=True, 
                 type="primary" if st.session_state.current_page == "Import & Données" else "secondary"):
        st.session_state.current_page = "Import & Données"
        st.rerun()

with col2:
    if st.button("🔍 Interprétation", use_container_width=True,
                 type="primary" if st.session_state.current_page == "Interprétation" else "secondary"):
        st.session_state.current_page = "Interprétation"
        st.rerun()

with col3:
    if st.button("💊 Recommandations", use_container_width=True,
                 type="primary" if st.session_state.current_page == "Recommandations" else "secondary"):
        st.session_state.current_page = "Recommandations"
        st.rerun()

with col4:
    if st.button("📈 Suivi", use_container_width=True,
                 type="primary" if st.session_state.current_page == "Suivi" else "secondary"):
        st.session_state.current_page = "Suivi"
        st.rerun()

with col5:
    if st.button("📄 Export PDF", use_container_width=True,
                 type="primary" if st.session_state.current_page == "Export PDF" else "secondary"):
        st.session_state.current_page = "Export PDF"
        st.rerun()

st.markdown("---")

# Récupérer la page courante
page = st.session_state.current_page

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
        else:
            imc = 0
        
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
        antecedents = st.text_area(
            "Antécédents médicaux",
            placeholder="Exemple: Hypothyroïdie, traitement en cours...",
            height=100
        )
        
        # Sauvegarder les données patient
        st.session_state.patient_data = {
            'genre': genre,
            'date_naissance': date_naissance,
            'poids': poids,
            'taille': taille,
            'imc': imc,
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
                        temp_path = f"/tmp/{biology_file.name}"
                        with open(temp_path, 'wb') as f:
                            f.write(biology_file.getbuffer())
                        
                        biology_data = extract_synlab_biology(temp_path)
                        st.session_state.biology_data = biology_data
                        
                        st.success(f"✅ {len(biology_data)} biomarqueurs extraits")
                        
                        if st.checkbox("Afficher les données extraites", key="show_bio"):
                            st.dataframe(biology_data, use_container_width=True)
                    
                    elif file_extension in ['xlsx', 'xls']:
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
                        temp_path = f"/tmp/{microbiome_file.name}"
                        with open(temp_path, 'wb') as f:
                            f.write(microbiome_file.getbuffer())
                        
                        microbiome_data = extract_idk_microbiome(temp_path)
                        st.session_state.microbiome_data = microbiome_data
                        
                        st.success(f"✅ Dysbiosis Index: {microbiome_data.get('dysbiosis_index', 'N/A')}")
                        st.info(f"Diversité: {microbiome_data.get('diversity', 'N/A')}")
                        
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
                    script_dir = os.path.dirname(os.path.abspath(__file__))
                    rules_path = os.path.join(script_dir, "data", "Bases_regles_Synlab.xlsx")
                    
                    if not os.path.exists(rules_path):
                        st.error(f"❌ Fichier de règles introuvable : {rules_path}")
                        raise FileNotFoundError(f"Fichier de règles introuvable: {rules_path}")
                    
                    engine = RulesEngine(rules_path)
                    st.session_state.rules_engine = engine
                    
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
            st.metric("Biomarqueurs analysés", len(reco.get('biology_interpretations', [])))
        
        with col2:
            st.metric("Dysbiosis Index", reco.get('microbiome_summary', {}).get('dysbiosis_index', 'N/A'))
        
        with col3:
            anomalies = len([b for b in reco.get('biology_interpretations', []) if b.get('status') != 'Normal'])
            st.metric("Anomalies détectées", anomalies)
        
        with col4:
            st.metric(
                "Niveau de priorité",
                "Élevé" if anomalies > 5 else "Modéré" if anomalies > 2 else "Faible",
                delta=None
            )
        
        # Interprétations biologiques
        if reco.get('biology_interpretations'):
            st.markdown("---")
            st.markdown("### 🧪 Interprétations Biologiques")
            
            for interp in reco['biology_interpretations']:
                with st.expander(f"{interp['biomarker']} - {interp['status']}", expanded=interp['status'] != 'Normal'):
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
                with st.expander(f"{interp['group']} - {interp['result']}", expanded=interp['result'] != 'Expected'):
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
        st.markdown("### 📥 Générer le Rapport PDF Multimodal")
        
        # Aperçu des données à exporter
        col1, col2, col3 = st.columns(3)
        
        with col1:
            bio_count = len(st.session_state.recommendations.get('biology_interpretations', []))
            st.metric("📊 Biomarqueurs", bio_count)
        
        with col2:
            micro_count = len(st.session_state.recommendations.get('microbiome_interpretations', []))
            st.metric("🦠 Analyses microbiote", micro_count)
        
        with col3:
            cross_count = len(st.session_state.recommendations.get('cross_analysis', []))
            st.metric("🔗 Analyses croisées", cross_count)
        
        st.markdown("---")
        
        # Options d'export
        st.markdown("### ⚙️ Options du rapport")
        
        col1, col2 = st.columns(2)
        
        with col1:
            include_bio = st.checkbox("✅ Inclure les résultats biologiques", value=True)
            include_micro = st.checkbox("✅ Inclure les résultats microbiote", value=True)
        
        with col2:
            include_cross = st.checkbox("✅ Inclure les analyses croisées", value=True)
            include_reco = st.checkbox("✅ Inclure les recommandations", value=True)
        
        st.markdown("---")
        
        # Génération du PDF
        if st.button("🚀 Générer le Rapport PDF", type="primary", use_container_width=True):
            try:
                with st.spinner("📄 Génération du rapport PDF en cours..."):
                    pdf_data = prepare_pdf_data()
                    
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                        pdf_path = tmp_file.name
                    
                    generate_multimodal_report(
                        patient_data=pdf_data['patient'],
                        biology_data=pdf_data['biologie'] if include_bio else {},
                        microbiome_data=pdf_data['microbiote'] if include_micro else {},
                        cross_analysis=pdf_data['cross_analysis'] if include_cross else {},
                        recommendations=pdf_data['recommendations'] if include_reco else {},
                        follow_up=pdf_data['follow_up'],
                        output_path=pdf_path
                    )
                    
                    with open(pdf_path, 'rb') as f:
                        pdf_bytes = f.read()
                    
                    st.success("✅ Rapport PDF généré avec succès !")
                    
                    patient_name = st.session_state.patient_data.get('nom', 'Patient')
                    date_str = datetime.now().strftime("%Y%m%d")
                    filename = f"Rapport_Unilabs_{patient_name}_{date_str}.pdf"
                    
                    st.download_button(
                        label="📥 Télécharger le Rapport PDF",
                        data=pdf_bytes,
                        file_name=filename,
                        mime="application/pdf",
                        use_container_width=True
                    )
                    
                    os.unlink(pdf_path)
                    
            except Exception as e:
                st.error(f"❌ Erreur lors de la génération du PDF: {str(e)}")
                st.exception(e)
        
        st.markdown("---")
        st.info("💡 **Conseil**: Le rapport PDF inclut toutes les analyses, interprétations et recommandations personnalisées.")

# Footer
st.markdown("---")
st.caption("Unilabs © 2026 - Dr Thibault SUTTER, Biologiste spécialisé en biologie fonctionnelle | Version Beta v1.0 - Powered by ALGO-LIFE")
