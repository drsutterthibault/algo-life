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

# CSS personnalisé
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
    
    /* Styling pour les zones éditables */
    .editable-section {
        background: #fff9e6;
        border: 2px solid #ffd700;
        border-radius: 8px;
        padding: 1.5rem;
        margin: 1rem 0;
    }
    
    .auto-section {
        background: #f0f7ff;
        border: 2px solid #4a90e2;
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


# ===== FONCTIONS HELPER =====

def compile_auto_recommendations(reco_data, category):
    """
    Compile les recommandations automatiques en un seul texte
    
    Args:
        reco_data: Données de recommandations
        category: 'nutrition', 'micronutrition', 'lifestyle', 'multimodal'
    
    Returns:
        str: Texte compilé des recommandations
    """
    recommendations_text = ""
    
    if category == 'nutrition':
        # Recommandations biologie
        if reco_data.get('biology_interpretations'):
            bio_recos = []
            for interp in reco_data['biology_interpretations']:
                if interp.get('nutrition_reco'):
                    bio_recos.append(f"• {interp['biomarker']}: {interp['nutrition_reco']}")
            
            if bio_recos:
                recommendations_text += "**Basé sur l'analyse biologique:**\n" + "\n".join(bio_recos) + "\n\n"
        
        # Recommandations microbiote
        if reco_data.get('microbiome_interpretations'):
            micro_recos = []
            for interp in reco_data['microbiome_interpretations']:
                if interp.get('nutrition_reco'):
                    micro_recos.append(f"• {interp['group']}: {interp['nutrition_reco']}")
            
            if micro_recos:
                recommendations_text += "**Basé sur l'analyse microbiote:**\n" + "\n".join(micro_recos)
    
    elif category == 'micronutrition':
        # Recommandations biologie
        if reco_data.get('biology_interpretations'):
            bio_recos = []
            for interp in reco_data['biology_interpretations']:
                if interp.get('micronutrition_reco'):
                    bio_recos.append(f"• {interp['biomarker']}: {interp['micronutrition_reco']}")
            
            if bio_recos:
                recommendations_text += "**Basé sur l'analyse biologique:**\n" + "\n".join(bio_recos) + "\n\n"
        
        # Recommandations microbiote
        if reco_data.get('microbiome_interpretations'):
            micro_recos = []
            for interp in reco_data['microbiome_interpretations']:
                if interp.get('supplementation_reco'):
                    micro_recos.append(f"• {interp['group']}: {interp['supplementation_reco']}")
            
            if micro_recos:
                recommendations_text += "**Basé sur l'analyse microbiote:**\n" + "\n".join(micro_recos)
    
    elif category == 'lifestyle':
        # Recommandations biologie
        if reco_data.get('biology_interpretations'):
            bio_recos = []
            for interp in reco_data['biology_interpretations']:
                if interp.get('lifestyle_reco'):
                    bio_recos.append(f"• {interp['biomarker']}: {interp['lifestyle_reco']}")
            
            if bio_recos:
                recommendations_text += "**Basé sur l'analyse biologique:**\n" + "\n".join(bio_recos) + "\n\n"
        
        # Recommandations microbiote
        if reco_data.get('microbiome_interpretations'):
            micro_recos = []
            for interp in reco_data['microbiome_interpretations']:
                if interp.get('lifestyle_reco'):
                    micro_recos.append(f"• {interp['group']}: {interp['lifestyle_reco']}")
            
            if micro_recos:
                recommendations_text += "**Basé sur l'analyse microbiote:**\n" + "\n".join(micro_recos)
    
    elif category == 'multimodal':
        if reco_data.get('cross_analysis'):
            cross_recos = []
            for analysis in reco_data['cross_analysis']:
                title = analysis.get('title', 'Analyse')
                desc = analysis.get('description', '')
                cross_recos.append(f"• **{title}**: {desc}")
            
            if cross_recos:
                recommendations_text += "**Analyses croisées:**\n" + "\n".join(cross_recos)
    
    return recommendations_text.strip()


def prepare_pdf_data():
    """Transforme les données de session en format pour le PDF generator"""
    
    # Données patient
    patient_data = st.session_state.patient_data.copy()
    if 'date_naissance' in patient_data:
        patient_data['date_naissance'] = patient_data['date_naissance'].strftime('%d/%m/%Y')
        today = datetime.now()
        birth_date = datetime.strptime(patient_data['date_naissance'], '%d/%m/%Y')
        patient_data['age'] = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    
    patient_data['nom'] = patient_data.get('nom', 'Patient')
    patient_data['prenom'] = patient_data.get('prenom', '')
    
    # Données biologiques
    biology_data = {'categories': {}, 'resume': ''}
    
    if st.session_state.recommendations and st.session_state.recommendations.get('biology_interpretations'):
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
        
        if st.session_state.microbiome_data and 'phyla' in st.session_state.microbiome_data:
            microbiome_data['phyla'] = st.session_state.microbiome_data['phyla']
        
        if st.session_state.recommendations.get('microbiome_interpretations'):
            microbiome_data['especes_cles'] = []
            for interp in st.session_state.recommendations['microbiome_interpretations']:
                if interp.get('result') != 'Expected':
                    interpretation = interp.get('interpretation', '')
                    if interpretation is None:
                        interpretation = ''
                    
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
    
    # RECOMMANDATIONS ÉDITABLES - Utiliser les versions éditées
    recommendations = {
        'nutrition': {'privilegier': [], 'limiter': []},
        'supplementation': []
    }
    
    # Ajouter les recommandations éditables
    if 'editable_recommendations' in st.session_state:
        recommendations['nutrition']['manual_text'] = st.session_state.editable_recommendations.get('nutrition', '')
        recommendations['micronutrition_manual'] = st.session_state.editable_recommendations.get('micronutrition', '')
        recommendations['lifestyle_manual'] = st.session_state.editable_recommendations.get('lifestyle', '')
        recommendations['multimodal_manual'] = st.session_state.editable_recommendations.get('multimodal', '')
    
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

# NOUVEAU: État pour les recommandations éditables
if 'editable_recommendations' not in st.session_state:
    st.session_state.editable_recommendations = {
        'nutrition': '',
        'micronutrition': '',
        'lifestyle': '',
        'multimodal': ''
    }

# NOUVEAU: Flag pour initialisation des recommandations auto
if 'auto_reco_initialized' not in st.session_state:
    st.session_state.auto_reco_initialized = False


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
            if st.button("🔍 Analyser le fichier microbiote"):
                with st.spinner("Extraction des données en cours..."):
                    try:
                        micro_data = extract_idk_microbiome(microbiome_file)
                        st.session_state.microbiome_data = micro_data
                        st.success(f"✅ Dysbiosis Index: {micro_data.get('dysbiosis_index')}, Groupes: {len(micro_data.get('bacteria_groups', []))}, Espèces: {len(micro_data.get('bacteria_species', []))}")
                        
                        # Afficher les groupes
                        if micro_data.get('bacteria_groups'):
                            st.write("**Groupes bactériens détectés:**")
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
                    
                    # Réinitialiser le flag pour permettre la compilation des recommandations auto
                    st.session_state.auto_reco_initialized = False
                    
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


# PAGE 4: RECOMMANDATIONS (VERSION ÉDITABLE)
elif page == "Recommandations":
    st.markdown("## 💊 Recommandations")
    
    if st.session_state.recommendations is None:
        st.info("ℹ️ Aucune recommandation disponible. Importez des données et lancez l'analyse.")
    else:
        reco = st.session_state.recommendations
        
        # INITIALISATION DES RECOMMANDATIONS AUTO (UNE SEULE FOIS)
        if not st.session_state.auto_reco_initialized:
            for category in ['nutrition', 'micronutrition', 'lifestyle', 'multimodal']:
                # Compiler les recommandations auto
                auto_text = compile_auto_recommendations(reco, category)
                
                # Initialiser seulement si vide (ne pas écraser les modifications)
                if not st.session_state.editable_recommendations[category]:
                    st.session_state.editable_recommendations[category] = auto_text
            
            st.session_state.auto_reco_initialized = True
        
        # TABS POUR LES RECOMMANDATIONS
        tab1, tab2, tab3, tab4 = st.tabs(["🥗 Nutrition", "💊 Micronutrition", "🏃 Lifestyle", "🔄 Multimodal"])
        
        # TAB 1: NUTRITION
        with tab1:
            st.markdown("### Recommandations Nutritionnelles")
            
            # Zone éditable
            st.markdown('<div class="editable-section">', unsafe_allow_html=True)
            st.markdown("#### ✍️ Recommandations (modifiables)")
            st.caption("💡 Vous pouvez modifier, ajouter ou supprimer du contenu ci-dessous")
            
            edited_nutrition = st.text_area(
                "Recommandations Nutrition",
                value=st.session_state.editable_recommendations['nutrition'],
                height=300,
                key="edit_nutrition",
                label_visibility="collapsed"
            )
            
            # Mise à jour en temps réel
            st.session_state.editable_recommendations['nutrition'] = edited_nutrition
            
            col1, col2 = st.columns([1, 4])
            with col1:
                if st.button("🔄 Réinitialiser", key="reset_nutrition"):
                    st.session_state.editable_recommendations['nutrition'] = compile_auto_recommendations(reco, 'nutrition')
                    st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        # TAB 2: MICRONUTRITION
        with tab2:
            st.markdown("### Recommandations en Micronutrition")
            
            st.markdown('<div class="editable-section">', unsafe_allow_html=True)
            st.markdown("#### ✍️ Recommandations (modifiables)")
            st.caption("💡 Vous pouvez modifier, ajouter ou supprimer du contenu ci-dessous")
            
            edited_micro = st.text_area(
                "Recommandations Micronutrition",
                value=st.session_state.editable_recommendations['micronutrition'],
                height=300,
                key="edit_micronutrition",
                label_visibility="collapsed"
            )
            
            st.session_state.editable_recommendations['micronutrition'] = edited_micro
            
            col1, col2 = st.columns([1, 4])
            with col1:
                if st.button("🔄 Réinitialiser", key="reset_micronutrition"):
                    st.session_state.editable_recommendations['micronutrition'] = compile_auto_recommendations(reco, 'micronutrition')
                    st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        # TAB 3: LIFESTYLE
        with tab3:
            st.markdown("### Recommandations Lifestyle")
            
            st.markdown('<div class="editable-section">', unsafe_allow_html=True)
            st.markdown("#### ✍️ Recommandations (modifiables)")
            st.caption("💡 Vous pouvez modifier, ajouter ou supprimer du contenu ci-dessous")
            
            edited_lifestyle = st.text_area(
                "Recommandations Lifestyle",
                value=st.session_state.editable_recommendations['lifestyle'],
                height=300,
                key="edit_lifestyle",
                label_visibility="collapsed"
            )
            
            st.session_state.editable_recommendations['lifestyle'] = edited_lifestyle
            
            col1, col2 = st.columns([1, 4])
            with col1:
                if st.button("🔄 Réinitialiser", key="reset_lifestyle"):
                    st.session_state.editable_recommendations['lifestyle'] = compile_auto_recommendations(reco, 'lifestyle')
                    st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        # TAB 4: MULTIMODAL
        with tab4:
            st.markdown("### Analyse Multimodale Croisée")
            
            st.markdown('<div class="editable-section">', unsafe_allow_html=True)
            st.markdown("#### ✍️ Observations (modifiables)")
            st.caption("💡 Vous pouvez modifier, ajouter ou supprimer du contenu ci-dessous")
            
            edited_multimodal = st.text_area(
                "Observations Multimodales",
                value=st.session_state.editable_recommendations['multimodal'],
                height=300,
                key="edit_multimodal",
                label_visibility="collapsed"
            )
            
            st.session_state.editable_recommendations['multimodal'] = edited_multimodal
            
            col1, col2 = st.columns([1, 4])
            with col1:
                if st.button("🔄 Réinitialiser", key="reset_multimodal"):
                    st.session_state.editable_recommendations['multimodal'] = compile_auto_recommendations(reco, 'multimodal')
                    st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)


# PAGE 5: SUIVI
elif page == "Suivi":
    st.markdown("## 📈 Suivi")
    st.info("Fonctionnalité de suivi en développement.")


# PAGE 6: EXPORT PDF
elif page == "Export PDF":
    st.markdown("## 📄 Export PDF")
    
    if st.session_state.recommendations is None:
        st.info("ℹ️ Aucune donnée à exporter. Importez des données et lancez l'analyse.")
    else:
        st.markdown("### 📥 Générer le Rapport PDF Multimodal")
        
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
        
        st.markdown("### ⚙️ Options du rapport")
        
        col1, col2 = st.columns(2)
        
        with col1:
            include_bio = st.checkbox("✅ Inclure les résultats biologiques", value=True)
            include_micro = st.checkbox("✅ Inclure les résultats microbiote", value=True)
        
        with col2:
            include_cross = st.checkbox("✅ Inclure les analyses croisées", value=True)
            include_reco = st.checkbox("✅ Inclure les recommandations", value=True)
        
        st.markdown("---")
        
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
        st.info("💡 **Info**: Le rapport PDF inclut vos recommandations éditées.")


# Footer
st.markdown("---")
st.caption("Unilabs © 2026 - Dr Thibault SUTTER, Biologiste spécialisé en biologie fonctionnelle | Version Beta v1.0 - Powered by ALGO-LIFE")
