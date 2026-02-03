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
    
    /* Style pour les zones de recommandations manuelles */
    .manual-reco-box {
        background: #fff9e6;
        border: 2px solid #ffd700;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# ===== INITIALISATION DES ÉTATS DE SESSION =====
if 'patient_data' not in st.session_state:
    st.session_state.patient_data = {}

if 'biology_file' not in st.session_state:
    st.session_state.biology_file = None

if 'biology_data' not in st.session_state:
    st.session_state.biology_data = None

if 'microbiome_file' not in st.session_state:
    st.session_state.microbiome_file = None

if 'microbiome_data' not in st.session_state:
    st.session_state.microbiome_data = None

if 'recommendations' not in st.session_state:
    st.session_state.recommendations = None

# NOUVEAU: Initialisation des recommandations manuelles
if 'manual_recommendations' not in st.session_state:
    st.session_state.manual_recommendations = {
        'nutrition': '',
        'micronutrition': '',
        'lifestyle': '',
        'multimodal': ''
    }

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
    cross_analysis = {}
    if st.session_state.recommendations and st.session_state.recommendations.get('cross_analysis'):
        cross_analysis['correlations'] = st.session_state.recommendations['cross_analysis']
    
    # Recommandations
    recommendations = {
        'nutrition': {'privilegier': [], 'limiter': []},
        'supplementation': []
    }
    
    # Extraire les recommandations nutritionnelles et de supplémentation
    if st.session_state.recommendations:
        nutrition_items = []
        supplementation_items = []
        
        # Depuis biologie
        for interp in st.session_state.recommendations.get('biology_interpretations', []):
            if interp.get('nutrition_reco'):
                nutrition_items.append({
                    'source': interp['biomarker'],
                    'content': interp['nutrition_reco']
                })
            if interp.get('micronutrition_reco'):
                supplementation_items.append({
                    'source': interp['biomarker'],
                    'content': interp['micronutrition_reco']
                })
        
        # Depuis microbiote
        for interp in st.session_state.recommendations.get('microbiome_interpretations', []):
            if interp.get('nutrition_reco'):
                nutrition_items.append({
                    'source': interp['group'],
                    'content': interp['nutrition_reco']
                })
            if interp.get('supplementation_reco'):
                supplementation_items.append({
                    'source': interp['group'],
                    'content': interp['supplementation_reco']
                })
        
        # NOUVEAU: Ajouter les recommandations manuelles
        recommendations['nutrition']['manual_text'] = st.session_state.manual_recommendations.get('nutrition', '')
        recommendations['micronutrition_manual'] = st.session_state.manual_recommendations.get('micronutrition', '')
        recommendations['lifestyle_manual'] = st.session_state.manual_recommendations.get('lifestyle', '')
        recommendations['multimodal_manual'] = st.session_state.manual_recommendations.get('multimodal', '')
    
    # Suivi
    follow_up = {
        'controles': [
            {
                'type': 'Bilan biologique',
                'delai': '3 mois',
                'biomarqueurs': ['Selon anomalies identifiées']
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

# ===== SIDEBAR =====
with st.sidebar:
    st.markdown("""
    <div class="sidebar-profile">
        <div class="profile-name">Dr Thibault SUTTER</div>
        <div class="profile-title">Biologiste spécialisé en<br/>biologie fonctionnelle</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### 🧭 Navigation")
    page = st.radio(
        "Navigation",
        ["Tableau de bord", "Import Données", "Interprétations", "Recommandations", "Suivi", "Export PDF"],
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    st.markdown("### ⚙️ Paramètres")
    st.checkbox("Mode Expert", value=False)
    st.selectbox("Langue", ["Français", "English"])
    
    st.markdown("---")
    st.caption("Version Beta v1.0")

# ===== CONTENU PRINCIPAL =====
# PAGE 1: TABLEAU DE BORD
if page == "Tableau de bord":
    st.markdown('<div class="main-header"><h1>🧬 Tableau de Bord</h1><p>Vue d\'ensemble de vos analyses multimodales</p></div>', unsafe_allow_html=True)
    
    if not st.session_state.patient_data:
        st.info("👋 Bienvenue ! Commencez par importer des données dans la section 'Import Données'")
    else:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Patient", 
                f"{st.session_state.patient_data.get('nom', 'N/A')} {st.session_state.patient_data.get('prenom', '')}"
            )
        
        with col2:
            bio_count = len(st.session_state.biology_data.get('biomarkers', [])) if st.session_state.biology_data else 0
            st.metric("Biomarqueurs", bio_count)
        
        with col3:
            micro_count = len(st.session_state.microbiome_data.get('species', [])) if st.session_state.microbiome_data else 0
            st.metric("Analyses Microbiote", micro_count)
        
        with col4:
            anomalies = 0
            if st.session_state.recommendations:
                anomalies = len([b for b in st.session_state.recommendations.get('biology_interpretations', []) 
                               if b.get('status') != 'Normal'])
            st.metric("Anomalies", anomalies)

# PAGE 2: IMPORT DONNÉES
elif page == "Import Données":
    st.markdown("## 📥 Import Données")
    
    # Section Patient
    with st.expander("👤 Informations Patient", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            nom = st.text_input("Nom", value=st.session_state.patient_data.get('nom', ''))
            sexe = st.selectbox("Sexe", ["M", "F"], index=0 if st.session_state.patient_data.get('sexe', 'M') == 'M' else 1)
        with col2:
            prenom = st.text_input("Prénom", value=st.session_state.patient_data.get('prenom', ''))
            date_naissance = st.date_input("Date de naissance", 
                                          value=st.session_state.patient_data.get('date_naissance', datetime.now()))
        
        if st.button("💾 Enregistrer les informations patient"):
            st.session_state.patient_data = {
                'nom': nom,
                'prenom': prenom,
                'sexe': sexe,
                'date_naissance': date_naissance
            }
            st.success("✅ Informations patient enregistrées")
    
    # Section Biologie
    with st.expander("🧪 Données Biologiques (Synlab)", expanded=True):
        biology_file = st.file_uploader("Import fichier biologique", type=['pdf', 'csv'])
        
        if biology_file:
            st.session_state.biology_file = biology_file
            
            if st.button("🔍 Analyser le fichier biologique"):
                with st.spinner("Extraction des données en cours..."):
                    try:
                        bio_data = extract_synlab_biology(biology_file)
                        st.session_state.biology_data = bio_data
                        st.success(f"✅ {len(bio_data.get('biomarkers', []))} biomarqueurs extraits")
                        
                        df = pd.DataFrame(bio_data.get('biomarkers', []))
                        st.dataframe(df, use_container_width=True)
                    except Exception as e:
                        st.error(f"❌ Erreur: {str(e)}")
    
    # Section Microbiote
    with st.expander("🦠 Données Microbiote (IDK)", expanded=True):
        microbiome_file = st.file_uploader("Import fichier microbiote", type=['pdf'])
        
        if microbiome_file:
            st.session_state.microbiome_file = microbiome_file
            
            if st.button("🔍 Analyser le fichier microbiote"):
                with st.spinner("Extraction des données en cours..."):
                    try:
                        micro_data = extract_idk_microbiome(microbiome_file)
                        st.session_state.microbiome_data = micro_data
                        st.success(f"✅ {len(micro_data.get('species', []))} espèces extraites")
                        
                        if micro_data.get('phyla'):
                            st.write("**Phyla détectés:**")
                            df_phyla = pd.DataFrame(micro_data['phyla'])
                            st.dataframe(df_phyla, use_container_width=True)
                    except Exception as e:
                        st.error(f"❌ Erreur: {str(e)}")
    
    # Bouton d'analyse globale
    st.markdown("---")
    if st.session_state.biology_data or st.session_state.microbiome_data:
        if st.button("🚀 Lancer l'Analyse Multimodale", type="primary", use_container_width=True):
            with st.spinner("🧠 Analyse en cours..."):
                try:
                    engine = RulesEngine()
                    reco = engine.generate_recommendations(
                        st.session_state.biology_data,
                        st.session_state.microbiome_data
                    )
                    st.session_state.recommendations = reco
                    st.success("✅ Analyse terminée ! Consultez les sections Interprétations et Recommandations")
                    st.balloons()
                except Exception as e:
                    st.error(f"❌ Erreur lors de l'analyse: {str(e)}")
                    st.exception(e)

# PAGE 3: INTERPRÉTATIONS
elif page == "Interprétations":
    st.markdown("## 📊 Interprétations")
    
    if st.session_state.recommendations is None:
        st.info("ℹ️ Aucune interprétation disponible. Importez des données et lancez l'analyse.")
    else:
        reco = st.session_state.recommendations
        
        # Métriques générales
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            bio_count = len(reco.get('biology_interpretations', []))
            st.metric("Biomarqueurs analysés", bio_count)
        
        with col2:
            micro_count = len(reco.get('microbiome_interpretations', []))
            st.metric("Groupes microbiote", micro_count)
        
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
            
            # Zone de recommandations manuelles
            st.markdown('<div class="manual-reco-box">', unsafe_allow_html=True)
            st.markdown("#### ✍️ Recommandations Manuelles")
            manual_nutrition = st.text_area(
                "Ajoutez vos recommandations nutritionnelles personnalisées",
                value=st.session_state.manual_recommendations.get('nutrition', ''),
                height=150,
                key="manual_nutrition_input",
                placeholder="Exemple: Privilégier les aliments riches en oméga-3, augmenter la consommation de légumes crucifères..."
            )
            if st.button("💾 Sauvegarder", key="save_nutrition"):
                st.session_state.manual_recommendations['nutrition'] = manual_nutrition
                st.success("✅ Recommandations nutritionnelles sauvegardées")
            st.markdown('</div>', unsafe_allow_html=True)
            
            st.markdown("---")
            st.markdown("### Recommandations Générées Automatiquement")
            
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
            
            # Zone de recommandations manuelles
            st.markdown('<div class="manual-reco-box">', unsafe_allow_html=True)
            st.markdown("#### ✍️ Recommandations Manuelles")
            manual_micronutrition = st.text_area(
                "Ajoutez vos recommandations en micronutrition personnalisées",
                value=st.session_state.manual_recommendations.get('micronutrition', ''),
                height=150,
                key="manual_micronutrition_input",
                placeholder="Exemple: Vitamine D3 2000 UI/jour, Magnésium bisglycinate 300mg/jour..."
            )
            if st.button("💾 Sauvegarder", key="save_micronutrition"):
                st.session_state.manual_recommendations['micronutrition'] = manual_micronutrition
                st.success("✅ Recommandations micronutrition sauvegardées")
            st.markdown('</div>', unsafe_allow_html=True)
            
            st.markdown("---")
            st.markdown("### Recommandations Générées Automatiquement")
            
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
            
            # Zone de recommandations manuelles
            st.markdown('<div class="manual-reco-box">', unsafe_allow_html=True)
            st.markdown("#### ✍️ Recommandations Manuelles")
            manual_lifestyle = st.text_area(
                "Ajoutez vos recommandations lifestyle personnalisées",
                value=st.session_state.manual_recommendations.get('lifestyle', ''),
                height=150,
                key="manual_lifestyle_input",
                placeholder="Exemple: Augmenter l'activité physique à 30min/jour, améliorer l'hygiène de sommeil..."
            )
            if st.button("💾 Sauvegarder", key="save_lifestyle"):
                st.session_state.manual_recommendations['lifestyle'] = manual_lifestyle
                st.success("✅ Recommandations lifestyle sauvegardées")
            st.markdown('</div>', unsafe_allow_html=True)
            
            st.markdown("---")
            st.markdown("### Recommandations Générées Automatiquement")
            
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
            
            # Zone de recommandations manuelles
            st.markdown('<div class="manual-reco-box">', unsafe_allow_html=True)
            st.markdown("#### ✍️ Observations Multimodales Manuelles")
            manual_multimodal = st.text_area(
                "Ajoutez vos observations et corrélations personnalisées",
                value=st.session_state.manual_recommendations.get('multimodal', ''),
                height=150,
                key="manual_multimodal_input",
                placeholder="Exemple: Corrélation observée entre l'inflammation intestinale et les marqueurs hépatiques..."
            )
            if st.button("💾 Sauvegarder", key="save_multimodal"):
                st.session_state.manual_recommendations['multimodal'] = manual_multimodal
                st.success("✅ Observations multimodales sauvegardées")
            st.markdown('</div>', unsafe_allow_html=True)
            
            st.markdown("---")
            st.markdown("### Analyses Croisées Automatiques")
            
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
