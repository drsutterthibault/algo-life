"""
ALGO-LIFE - Plateforme Médecin
Application Streamlit pour l'analyse multimodale de santé
VERSION AVEC RECOMMANDATIONS ÉDITABLES
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
    
    /* Zone éditable */
    .editable-zone {
        background: #fff9e6;
        border: 2px solid #ffd700;
        border-radius: 8px;
        padding: 1.5rem;
        margin: 1rem 0;
    }
    
    /* Styling pour les radio buttons */
    .stRadio > label {
        display: none;
    }
</style>
""", unsafe_allow_html=True)

# ===== FONCTION HELPER POUR COMPILER LES RECOMMANDATIONS AUTO =====
def compile_recommendations_text(reco, category):
    """Compile les recommandations automatiques en un seul texte"""
    text_parts = []
    
    if category == 'nutrition':
        # Depuis biologie
        if reco.get('biology_interpretations'):
            bio_parts = [f"• {i['biomarker']}: {i['nutrition_reco']}" 
                        for i in reco['biology_interpretations'] 
                        if i.get('nutrition_reco')]
            if bio_parts:
                text_parts.append("**Basé sur l'analyse biologique:**\n" + "\n".join(bio_parts))
        
        # Depuis microbiote
        if reco.get('microbiome_interpretations'):
            micro_parts = [f"• {i['group']}: {i['nutrition_reco']}" 
                          for i in reco['microbiome_interpretations'] 
                          if i.get('nutrition_reco')]
            if micro_parts:
                text_parts.append("**Basé sur l'analyse microbiote:**\n" + "\n".join(micro_parts))
    
    elif category == 'micronutrition':
        # Depuis biologie
        if reco.get('biology_interpretations'):
            bio_parts = [f"• {i['biomarker']}: {i['micronutrition_reco']}" 
                        for i in reco['biology_interpretations'] 
                        if i.get('micronutrition_reco')]
            if bio_parts:
                text_parts.append("**Basé sur l'analyse biologique:**\n" + "\n".join(bio_parts))
        
        # Depuis microbiote
        if reco.get('microbiome_interpretations'):
            micro_parts = [f"• {i['group']}: {i['supplementation_reco']}" 
                          for i in reco['microbiome_interpretations'] 
                          if i.get('supplementation_reco')]
            if micro_parts:
                text_parts.append("**Basé sur l'analyse microbiote:**\n" + "\n".join(micro_parts))
    
    elif category == 'lifestyle':
        # Depuis biologie
        if reco.get('biology_interpretations'):
            bio_parts = [f"• {i['biomarker']}: {i['lifestyle_reco']}" 
                        for i in reco['biology_interpretations'] 
                        if i.get('lifestyle_reco')]
            if bio_parts:
                text_parts.append("**Basé sur l'analyse biologique:**\n" + "\n".join(bio_parts))
        
        # Depuis microbiote
        if reco.get('microbiome_interpretations'):
            micro_parts = [f"• {i['group']}: {i['lifestyle_reco']}" 
                          for i in reco['microbiome_interpretations'] 
                          if i.get('lifestyle_reco')]
            if micro_parts:
                text_parts.append("**Basé sur l'analyse microbiote:**\n" + "\n".join(micro_parts))
    
    elif category == 'multimodal':
        if reco.get('cross_analysis'):
            cross_parts = [f"• **{a.get('title', 'Analyse')}**: {a.get('description', '')}" 
                          for a in reco['cross_analysis']]
            if cross_parts:
                text_parts.append("**Analyses croisées:**\n" + "\n".join(cross_parts))
    
    return "\n\n".join(text_parts)

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
    
    # Recommandations - UTILISER LES VERSIONS ÉDITÉES
    recommendations = {
        'nutrition': {'privilegier': [], 'limiter': []},
        'supplementation': []
    }
    
    # Ajouter les recommandations ÉDITÉES
    if 'editable_reco' in st.session_state:
        recommendations['nutrition']['manual_text'] = st.session_state.editable_reco.get('reco_nutrition', '')
        recommendations['micronutrition_manual'] = st.session_state.editable_reco.get('reco_micronutrition', '')
        recommendations['lifestyle_manual'] = st.session_state.editable_reco.get('reco_lifestyle', '')
        recommendations['multimodal_manual'] = st.session_state.editable_reco.get('reco_multimodal', '')
    
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

# ===== INITIALISATION DES ÉTATS DE SESSION =====
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

# NOUVEAU: Recommandations éditables
if 'editable_reco' not in st.session_state:
    st.session_state.editable_reco = {}

if 'reco_initialized' not in st.session_state:
    st.session_state.reco_initialized = False

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
        "Navigation principale",
        ["Tableau de bord", "Import Données", "Interprétations", "Recommandations", "Suivi", "Export PDF"],
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    st.markdown("### ⚙️ Paramètres")
    mode_expert = st.checkbox("Mode Expert", value=False)
    langue = st.selectbox("Langue", ["Français", "English"])
    
    st.markdown("---")
    st.caption("Version Beta v1.0 - Powered by ALGO-LIFE")

# ===== CONTENU PRINCIPAL =====

# PAGE 1: TABLEAU DE BORD
if page == "Tableau de bord":
    st.markdown('<div class="main-header"><h1>🧬 Tableau de Bord</h1><p>Vue d\'ensemble de vos analyses multimodales</p></div>', unsafe_allow_html=True)
    
    if not st.session_state.patient_data:
        st.info("👋 Bienvenue ! Commencez par importer des données dans la section 'Import Données'")
        
        # Afficher quelques stats générales
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("### 🧪 Biologie")
            st.write("Analyse de biomarqueurs sanguins")
        with col2:
            st.markdown("### 🦠 Microbiote")
            st.write("Analyse de la flore intestinale")
        with col3:
            st.markdown("### 🔄 Multimodal")
            st.write("Corrélations entre analyses")
    else:
        # Métriques générales
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            patient_name = f"{st.session_state.patient_data.get('prenom', '')} {st.session_state.patient_data.get('nom', 'N/A')}"
            st.metric("👤 Patient", patient_name.strip())
        
        with col2:
            bio_count = 0
            if st.session_state.biology_data:
                bio_count = len(st.session_state.biology_data.get('biomarkers', []))
            st.metric("🧪 Biomarqueurs", bio_count)
        
        with col3:
            micro_count = 0
            if st.session_state.microbiome_data:
                micro_count = len(st.session_state.microbiome_data.get('bacteria_groups', []))
            st.metric("🦠 Groupes microbiote", micro_count)
        
        with col4:
            anomalies = 0
            if st.session_state.recommendations:
                anomalies = len([b for b in st.session_state.recommendations.get('biology_interpretations', []) 
                               if b.get('status') != 'Normal'])
            st.metric("⚠️ Anomalies", anomalies)
        
        # Graphique de résumé
        if st.session_state.recommendations:
            st.markdown("---")
            st.markdown("### 📊 Résumé de l'analyse")
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                bio_interp = st.session_state.recommendations.get('biology_interpretations', [])
                if bio_interp:
                    df_status = pd.DataFrame([
                        {'Statut': 'Normal', 'Nombre': len([b for b in bio_interp if b['status'] == 'Normal'])},
                        {'Statut': 'Élevé', 'Nombre': len([b for b in bio_interp if '↑' in b['status']])},
                        {'Statut': 'Bas', 'Nombre': len([b for b in bio_interp if '↓' in b['status']])}
                    ])
                    st.bar_chart(df_status.set_index('Statut'))
            
            with col2:
                st.markdown("**Points clés:**")
                if anomalies == 0:
                    st.success("✅ Tous les biomarqueurs dans les normes")
                elif anomalies <= 3:
                    st.warning(f"⚠️ {anomalies} anomalie(s) mineure(s)")
                else:
                    st.error(f"🔴 {anomalies} anomalie(s) nécessitant attention")

# PAGE 2: IMPORT DONNÉES
elif page == "Import Données":
    st.markdown("## 📥 Import & Données")
    
    # Section Informations Patient
    with st.expander("👤 Informations Patient", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            nom = st.text_input("Nom", value=st.session_state.patient_data.get('nom', ''))
            sexe = st.selectbox("Sexe", ["M", "F"], 
                              index=0 if st.session_state.patient_data.get('sexe', 'M') == 'M' else 1)
        
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
    
    # Section Données Biologiques
    with st.expander("🧪 Données Biologiques (Synlab)", expanded=True):
        biology_file = st.file_uploader(
            "Importer un fichier de biologie",
            type=['pdf', 'csv'],
            help="Fichier PDF ou CSV contenant les résultats biologiques"
        )
        
        if biology_file:
            if st.button("🔍 Analyser le fichier biologique"):
                with st.spinner("Extraction des données en cours..."):
                    try:
                        bio_data = extract_synlab_biology(biology_file)
                        st.session_state.biology_data = bio_data
                        
                        biomarkers_count = len(bio_data.get('biomarkers', []))
                        st.success(f"✅ {biomarkers_count} biomarqueurs extraits avec succès")
                        
                        # Afficher un aperçu
                        if biomarkers_count > 0:
                            df = pd.DataFrame(bio_data.get('biomarkers', []))
                            st.dataframe(df, use_container_width=True)
                    
                    except Exception as e:
                        st.error(f"❌ Erreur lors de l'extraction: {str(e)}")
                        st.exception(e)
    
    # Section Données Microbiote
    with st.expander("🦠 Données Microbiote (IDK GutMAP)", expanded=True):
        microbiome_file = st.file_uploader(
            "Importer un fichier microbiote",
            type=['pdf'],
            help="Fichier PDF IDK GutMAP contenant les résultats du microbiote"
        )
        
        if microbiome_file:
            if st.button("🔍 Analyser le fichier microbiote"):
                with st.spinner("Extraction des données microbiote en cours..."):
                    try:
                        micro_data = extract_idk_microbiome(microbiome_file)
                        st.session_state.microbiome_data = micro_data
                        
                        di = micro_data.get('dysbiosis_index', 'N/A')
                        diversity = micro_data.get('diversity', 'N/A')
                        groups_count = len(micro_data.get('bacteria_groups', []))
                        species_count = len(micro_data.get('bacteria_species', []))
                        
                        st.success(f"✅ Extraction réussie!")
                        
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("Dysbiosis Index", di)
                        with col2:
                            st.metric("Diversité", diversity)
                        with col3:
                            st.metric("Groupes", groups_count)
                        with col4:
                            st.metric("Espèces", species_count)
                        
                        # Afficher les groupes
                        if groups_count > 0:
                            st.markdown("**Groupes bactériens détectés:**")
                            groups_df = pd.DataFrame([
                                {
                                    'Groupe': g['name'],
                                    'Catégorie': g['category'],
                                    'Résultat': g['result']
                                }
                                for g in micro_data['bacteria_groups']
                            ])
                            st.dataframe(groups_df, use_container_width=True)
                    
                    except Exception as e:
                        st.error(f"❌ Erreur lors de l'extraction: {str(e)}")
                        st.exception(e)
    
    # Bouton d'analyse multimodale
    st.markdown("---")
    
    if st.session_state.biology_data or st.session_state.microbiome_data:
        st.markdown("### 🚀 Lancer l'Analyse Multimodale")
        st.info("💡 L'analyse croisera vos données biologiques et microbiote pour générer des recommandations personnalisées")
        
        if st.button("🚀 Lancer l'Analyse Complète", type="primary", use_container_width=True):
            with st.spinner("🧠 Analyse multimodale en cours..."):
                try:
                    engine = RulesEngine()
                    reco = engine.generate_recommendations(
                        st.session_state.biology_data,
                        st.session_state.microbiome_data
                    )
                    st.session_state.recommendations = reco
                    
                    # Réinitialiser le flag pour permettre la génération des recos éditables
                    st.session_state.reco_initialized = False
                    
                    st.success("✅ Analyse terminée avec succès !")
                    st.balloons()
                    
                    # Afficher un résumé
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        bio_count = len(reco.get('biology_interpretations', []))
                        st.metric("Biomarqueurs analysés", bio_count)
                    with col2:
                        micro_count = len(reco.get('microbiome_interpretations', []))
                        st.metric("Groupes microbiote", micro_count)
                    with col3:
                        cross_count = len(reco.get('cross_analysis', []))
                        st.metric("Analyses croisées", cross_count)
                    
                    st.info("👉 Consultez les sections **Interprétations** et **Recommandations**")
                
                except Exception as e:
                    st.error(f"❌ Erreur lors de l'analyse: {str(e)}")
                    st.exception(e)

# PAGE 3: INTERPRÉTATIONS
elif page == "Interprétations":
    st.markdown("## 📊 Interprétations")
    
    if st.session_state.recommendations is None:
        st.info("ℹ️ Aucune interprétation disponible. Importez des données et lancez l'analyse dans la section 'Import Données'.")
    else:
        reco = st.session_state.recommendations
        
        # Métriques générales
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            bio_count = len(reco.get('biology_interpretations', []))
            st.metric("📊 Biomarqueurs analysés", bio_count)
        
        with col2:
            micro_count = len(reco.get('microbiome_interpretations', []))
            st.metric("🦠 Groupes microbiote", micro_count)
        
        with col3:
            anomalies = len([b for b in reco.get('biology_interpretations', []) if b.get('status') != 'Normal'])
            st.metric("⚠️ Anomalies détectées", anomalies)
        
        with col4:
            priority = "Élevé" if anomalies > 5 else "Modéré" if anomalies > 2 else "Faible"
            st.metric("🎯 Niveau de priorité", priority)
        
        # Interprétations biologiques
        if reco.get('biology_interpretations'):
            st.markdown("---")
            st.markdown("### 🧪 Interprétations Biologiques")
            
            for interp in reco['biology_interpretations']:
                is_abnormal = interp['status'] != 'Normal'
                with st.expander(f"{interp['biomarker']} - {interp['status']}", expanded=is_abnormal):
                    col1, col2 = st.columns([1, 2])
                    
                    with col1:
                        st.markdown(f"**Valeur:** {interp['value']} {interp.get('unit', '')}")
                        st.markdown(f"**Référence:** {interp.get('reference', 'N/A')}")
                        st.markdown(f"**Statut:** {interp['status']}")
                        st.markdown(f"**Catégorie:** {interp.get('category', 'N/A')}")
                    
                    with col2:
                        if interp.get('interpretation'):
                            st.markdown("**📋 Interprétation:**")
                            st.info(interp['interpretation'])
        
        # Interprétations microbiote
        if reco.get('microbiome_interpretations'):
            st.markdown("---")
            st.markdown("### 🦠 Interprétations Microbiote")
            
            for interp in reco['microbiome_interpretations']:
                is_abnormal = interp['result'] != 'Expected'
                with st.expander(f"{interp['group']} - {interp['result']}", expanded=is_abnormal):
                    st.markdown(f"**Groupe bactérien:** {interp['group']}")
                    st.markdown(f"**Catégorie:** {interp.get('category', 'N/A')}")
                    st.markdown(f"**Résultat:** {interp['result']}")
                    
                    if interp.get('interpretation'):
                        st.markdown("**📋 Interprétation:**")
                        st.info(interp['interpretation'])

# PAGE 4: RECOMMANDATIONS (AVEC ZONES ÉDITABLES)
elif page == "Recommandations":
    st.markdown("## 💊 Recommandations")
    
    if st.session_state.recommendations is None:
        st.info("ℹ️ Aucune recommandation disponible. Importez des données et lancez l'analyse.")
    else:
        reco = st.session_state.recommendations
        
        # INITIALISATION DES RECOMMANDATIONS ÉDITABLES (UNE SEULE FOIS)
        if not st.session_state.reco_initialized:
            # Générer les recommandations automatiques
            generated = {
                "nutrition": compile_recommendations_text(reco, 'nutrition'),
                "micronutrition": compile_recommendations_text(reco, 'micronutrition'),
                "lifestyle": compile_recommendations_text(reco, 'lifestyle'),
                "multimodal": compile_recommendations_text(reco, 'multimodal'),
            }
            
            # Initialiser UNIQUEMENT si la clé n'existe pas (pour ne pas écraser les édits)
            for k, v in generated.items():
                key = f"reco_{k}"
                if key not in st.session_state.editable_reco:
                    st.session_state.editable_reco[key] = v or ""
            
            st.session_state.reco_initialized = True
        
        # TABS POUR LES RECOMMANDATIONS
        tab1, tab2, tab3, tab4 = st.tabs(["🥗 Nutrition", "💊 Micronutrition", "🏃 Lifestyle", "🔄 Multimodal"])
        
        # TAB 1: NUTRITION
        with tab1:
            st.markdown("### Recommandations Nutritionnelles")
            
            st.markdown('<div class="editable-zone">', unsafe_allow_html=True)
            st.markdown("#### ✍️ Zone Éditable")
            st.caption("💡 Modifiez, ajoutez ou supprimez du contenu ci-dessous. Vos modifications sont automatiquement sauvegardées.")
            
            edited_nutrition = st.text_area(
                "Recommandations Nutrition (modifiables)",
                value=st.session_state.editable_reco.get("reco_nutrition", ""),
                height=300,
                key="ui_reco_nutrition"
            )
            st.session_state.editable_reco["reco_nutrition"] = edited_nutrition
            
            col1, col2, col3 = st.columns([1, 1, 4])
            with col1:
                if st.button("🔄 Réinitialiser", key="reset_nutrition"):
                    st.session_state.editable_reco["reco_nutrition"] = compile_recommendations_text(reco, 'nutrition')
                    st.rerun()
            with col2:
                char_count = len(edited_nutrition)
                st.caption(f"📝 {char_count} caractères")
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        # TAB 2: MICRONUTRITION
        with tab2:
            st.markdown("### Recommandations en Micronutrition")
            
            st.markdown('<div class="editable-zone">', unsafe_allow_html=True)
            st.markdown("#### ✍️ Zone Éditable")
            st.caption("💡 Modifiez, ajoutez ou supprimez du contenu ci-dessous. Vos modifications sont automatiquement sauvegardées.")
            
            edited_micro = st.text_area(
                "Recommandations Micronutrition (modifiables)",
                value=st.session_state.editable_reco.get("reco_micronutrition", ""),
                height=300,
                key="ui_reco_micronutrition"
            )
            st.session_state.editable_reco["reco_micronutrition"] = edited_micro
            
            col1, col2, col3 = st.columns([1, 1, 4])
            with col1:
                if st.button("🔄 Réinitialiser", key="reset_micronutrition"):
                    st.session_state.editable_reco["reco_micronutrition"] = compile_recommendations_text(reco, 'micronutrition')
                    st.rerun()
            with col2:
                char_count = len(edited_micro)
                st.caption(f"📝 {char_count} caractères")
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        # TAB 3: LIFESTYLE
        with tab3:
            st.markdown("### Recommandations Lifestyle")
            
            st.markdown('<div class="editable-zone">', unsafe_allow_html=True)
            st.markdown("#### ✍️ Zone Éditable")
            st.caption("💡 Modifiez, ajoutez ou supprimez du contenu ci-dessous. Vos modifications sont automatiquement sauvegardées.")
            
            edited_lifestyle = st.text_area(
                "Recommandations Lifestyle (modifiables)",
                value=st.session_state.editable_reco.get("reco_lifestyle", ""),
                height=300,
                key="ui_reco_lifestyle"
            )
            st.session_state.editable_reco["reco_lifestyle"] = edited_lifestyle
            
            col1, col2, col3 = st.columns([1, 1, 4])
            with col1:
                if st.button("🔄 Réinitialiser", key="reset_lifestyle"):
                    st.session_state.editable_reco["reco_lifestyle"] = compile_recommendations_text(reco, 'lifestyle')
                    st.rerun()
            with col2:
                char_count = len(edited_lifestyle)
                st.caption(f"📝 {char_count} caractères")
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        # TAB 4: MULTIMODAL
        with tab4:
            st.markdown("### Analyse Multimodale Croisée")
            
            st.markdown('<div class="editable-zone">', unsafe_allow_html=True)
            st.markdown("#### ✍️ Zone Éditable")
            st.caption("💡 Modifiez, ajoutez ou supprimez du contenu ci-dessous. Vos modifications sont automatiquement sauvegardées.")
            
            edited_multimodal = st.text_area(
                "Observations Multimodales (modifiables)",
                value=st.session_state.editable_reco.get("reco_multimodal", ""),
                height=300,
                key="ui_reco_multimodal"
            )
            st.session_state.editable_reco["reco_multimodal"] = edited_multimodal
            
            col1, col2, col3 = st.columns([1, 1, 4])
            with col1:
                if st.button("🔄 Réinitialiser", key="reset_multimodal"):
                    st.session_state.editable_reco["reco_multimodal"] = compile_recommendations_text(reco, 'multimodal')
                    st.rerun()
            with col2:
                char_count = len(edited_multimodal)
                st.caption(f"📝 {char_count} caractères")
            
            st.markdown('</div>', unsafe_allow_html=True)

# PAGE 5: SUIVI
elif page == "Suivi":
    st.markdown("## 📈 Suivi")
    st.info("Fonctionnalité de suivi en développement. Permettra de tracker l'évolution des biomarqueurs dans le temps.")

# PAGE 6: EXPORT PDF
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
        st.info("💡 **Info**: Le rapport PDF inclut vos recommandations éditées dans les zones jaunes.")

# Footer
st.markdown("---")
st.caption("Unilabs © 2026 - Dr Thibault SUTTER, Biologiste spécialisé en biologie fonctionnelle | Version Beta v1.0 - Powered by ALGO-LIFE")
