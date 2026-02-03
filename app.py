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
    .editable-zone {
        background: #fff9e6;
        border: 2px solid #ffd700;
        border-radius: 8px;
        padding: 1.5rem;
        margin: 1rem 0;
    }
    .stRadio > label {
        display: none;
    }
</style>
""", unsafe_allow_html=True)

# CHEMIN VERS LE FICHIER EXCEL DES RÈGLES
RULES_EXCEL_PATH = "rules_combined.xlsx"  # Modifie ce chemin selon ton fichier

# FONCTION HELPER POUR COMPILER LES RECOMMANDATIONS AUTO
def compile_recommendations_text(reco, category):
    """Compile les recommandations automatiques en un seul texte"""
    text_parts = []
    
    if category == 'nutrition':
        if reco.get('biology_interpretations'):
            bio_parts = [f"• {i['biomarker']}: {i['nutrition_reco']}" 
                        for i in reco['biology_interpretations'] 
                        if i.get('nutrition_reco')]
            if bio_parts:
                text_parts.append("**Basé sur l'analyse biologique:**\n" + "\n".join(bio_parts))
        
        if reco.get('microbiome_interpretations'):
            micro_parts = [f"• {i['group']}: {i['nutrition_reco']}" 
                          for i in reco['microbiome_interpretations'] 
                          if i.get('nutrition_reco')]
            if micro_parts:
                text_parts.append("**Basé sur l'analyse microbiote:**\n" + "\n".join(micro_parts))
    
    elif category == 'micronutrition':
        if reco.get('biology_interpretations'):
            bio_parts = [f"• {i['biomarker']}: {i['micronutrition_reco']}" 
                        for i in reco['biology_interpretations'] 
                        if i.get('micronutrition_reco')]
            if bio_parts:
                text_parts.append("**Basé sur l'analyse biologique:**\n" + "\n".join(bio_parts))
        
        if reco.get('microbiome_interpretations'):
            micro_parts = [f"• {i['group']}: {i['supplementation_reco']}" 
                          for i in reco['microbiome_interpretations'] 
                          if i.get('supplementation_reco')]
            if micro_parts:
                text_parts.append("**Basé sur l'analyse microbiote:**\n" + "\n".join(micro_parts))
    
    elif category == 'lifestyle':
        if reco.get('biology_interpretations'):
            bio_parts = [f"• {i['biomarker']}: {i['lifestyle_reco']}" 
                        for i in reco['biology_interpretations'] 
                        if i.get('lifestyle_reco')]
            if bio_parts:
                text_parts.append("**Basé sur l'analyse biologique:**\n" + "\n".join(bio_parts))
        
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

def prepare_pdf_data():
    """Transforme les données de session en format pour le PDF generator"""
    patient_data = st.session_state.patient_data.copy()
    if 'date_naissance' in patient_data:
        patient_data['date_naissance'] = patient_data['date_naissance'].strftime('%d/%m/%Y')
        today = datetime.now()
        birth_date = datetime.strptime(patient_data['date_naissance'], '%d/%m/%Y')
        patient_data['age'] = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    
    patient_data['nom'] = patient_data.get('nom', 'Patient')
    patient_data['prenom'] = patient_data.get('prenom', '')
    
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
    
    cross_analysis = {}
    if st.session_state.recommendations and st.session_state.recommendations.get('cross_analysis'):
        cross_analysis['correlations'] = st.session_state.recommendations['cross_analysis']
    
    recommendations = {
        'nutrition': {'privilegier': [], 'limiter': []},
        'supplementation': []
    }
    
    if 'editable_reco' in st.session_state:
        recommendations['nutrition']['manual_text'] = st.session_state.editable_reco.get('reco_nutrition', '')
        recommendations['micronutrition_manual'] = st.session_state.editable_reco.get('reco_micronutrition', '')
        recommendations['lifestyle_manual'] = st.session_state.editable_reco.get('reco_lifestyle', '')
        recommendations['multimodal_manual'] = st.session_state.editable_reco.get('reco_multimodal', '')
    
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

# INITIALISATION DES ÉTATS DE SESSION
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
if 'editable_reco' not in st.session_state:
    st.session_state.editable_reco = {}
if 'reco_initialized' not in st.session_state:
    st.session_state.reco_initialized = False

# SIDEBAR
with st.sidebar:
    st.markdown("### Dr Thibault SUTTER")
    st.caption("Biologiste spécialisé en biologie fonctionnelle")
    
    st.markdown("---")
    page = st.radio(
        "Navigation",
        ["Tableau de bord", "Import Données", "Interprétations", "Recommandations", "Export PDF"],
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    st.caption("Version Beta v1.0")

# CONTENU PRINCIPAL

if page == "Tableau de bord":
    st.markdown("## 🧬 Tableau de Bord")
    
    if not st.session_state.patient_data:
        st.info("👋 Bienvenue ! Commencez par importer des données")
    else:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            patient_name = f"{st.session_state.patient_data.get('prenom', '')} {st.session_state.patient_data.get('nom', 'N/A')}"
            st.metric("Patient", patient_name.strip())
        
        with col2:
            bio_count = 0
            if st.session_state.biology_data:
                bio_count = len(st.session_state.biology_data.get('biomarkers', []))
            st.metric("Biomarqueurs", bio_count)
        
        with col3:
            micro_count = 0
            if st.session_state.microbiome_data:
                micro_count = len(st.session_state.microbiome_data.get('bacteria_groups', []))
            st.metric("Groupes microbiote", micro_count)
        
        with col4:
            anomalies = 0
            if st.session_state.recommendations:
                anomalies = len([b for b in st.session_state.recommendations.get('biology_interpretations', []) 
                               if b.get('status') != 'Normal'])
            st.metric("Anomalies", anomalies)

elif page == "Import Données":
    st.markdown("## 📥 Import & Données")
    
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
        
        if st.button("💾 Enregistrer"):
            st.session_state.patient_data = {
                'nom': nom,
                'prenom': prenom,
                'sexe': sexe,
                'date_naissance': date_naissance
            }
            st.success("✅ Informations enregistrées")
    
    with st.expander("🧪 Données Biologiques", expanded=True):
        biology_file = st.file_uploader("Fichier biologie", type=['pdf', 'csv'])
        
        if biology_file and st.button("🔍 Analyser biologie"):
            with st.spinner("Extraction..."):
                try:
                    bio_data = extract_synlab_biology(biology_file)
                    st.session_state.biology_data = bio_data
                    st.success(f"✅ {len(bio_data.get('biomarkers', []))} biomarqueurs extraits")
                except Exception as e:
                    st.error(f"❌ Erreur: {str(e)}")
    
    with st.expander("🦠 Données Microbiote", expanded=True):
        microbiome_file = st.file_uploader("Fichier microbiote", type=['pdf'])
        
        if microbiome_file and st.button("🔍 Analyser microbiote"):
            with st.spinner("Extraction..."):
                try:
                    micro_data = extract_idk_microbiome(microbiome_file)
                    st.session_state.microbiome_data = micro_data
                    st.success(f"✅ DI: {micro_data.get('dysbiosis_index')}, Groupes: {len(micro_data.get('bacteria_groups', []))}")
                except Exception as e:
                    st.error(f"❌ Erreur: {str(e)}")
    
    st.markdown("---")
    
    if st.session_state.biology_data or st.session_state.microbiome_data:
        if st.button("🚀 Lancer l'Analyse Complète", type="primary", use_container_width=True):
            with st.spinner("Analyse..."):
                try:
                    # CORRECTION: Initialiser RulesEngine avec le chemin du fichier Excel
                    if not os.path.exists(RULES_EXCEL_PATH):
                        st.error(f"❌ Fichier des règles introuvable: {RULES_EXCEL_PATH}")
                        st.info("💡 Créez le fichier 'rules_combined.xlsx' ou modifiez RULES_EXCEL_PATH dans le code")
                    else:
                        engine = RulesEngine(RULES_EXCEL_PATH)  # ← CORRECTION ICI
                        reco = engine.generate_recommendations(
                            st.session_state.biology_data,
                            st.session_state.microbiome_data
                        )
                        st.session_state.recommendations = reco
                        st.session_state.reco_initialized = False
                        st.success("✅ Analyse terminée!")
                        st.balloons()
                except Exception as e:
                    st.error(f"❌ Erreur: {str(e)}")
                    st.exception(e)

elif page == "Interprétations":
    st.markdown("## 📊 Interprétations")
    
    if st.session_state.recommendations is None:
        st.info("ℹ️ Aucune interprétation disponible")
    else:
        reco = st.session_state.recommendations
        
        if reco.get('biology_interpretations'):
            st.markdown("### 🧪 Biologie")
            for interp in reco['biology_interpretations']:
                is_abnormal = interp['status'] != 'Normal'
                with st.expander(f"{interp['biomarker']} - {interp['status']}", expanded=is_abnormal):
                    st.markdown(f"**Valeur:** {interp['value']} {interp.get('unit', '')}")
                    st.markdown(f"**Référence:** {interp.get('reference', 'N/A')}")
                    if interp.get('interpretation'):
                        st.info(interp['interpretation'])
        
        if reco.get('microbiome_interpretations'):
            st.markdown("### 🦠 Microbiote")
            for interp in reco['microbiome_interpretations']:
                is_abnormal = interp['result'] != 'Expected'
                with st.expander(f"{interp['group']} - {interp['result']}", expanded=is_abnormal):
                    if interp.get('interpretation'):
                        st.info(interp['interpretation'])

elif page == "Recommandations":
    st.markdown("## 💊 Recommandations")
    
    if st.session_state.recommendations is None:
        st.info("ℹ️ Aucune recommandation disponible")
    else:
        reco = st.session_state.recommendations
        
        if not st.session_state.reco_initialized:
            generated = {
                "nutrition": compile_recommendations_text(reco, 'nutrition'),
                "micronutrition": compile_recommendations_text(reco, 'micronutrition'),
                "lifestyle": compile_recommendations_text(reco, 'lifestyle'),
                "multimodal": compile_recommendations_text(reco, 'multimodal'),
            }
            
            for k, v in generated.items():
                key = f"reco_{k}"
                if key not in st.session_state.editable_reco:
                    st.session_state.editable_reco[key] = v or ""
            
            st.session_state.reco_initialized = True
        
        tab1, tab2, tab3, tab4 = st.tabs(["🥗 Nutrition", "💊 Micronutrition", "🏃 Lifestyle", "🔄 Multimodal"])
        
        with tab1:
            st.markdown("### Recommandations Nutritionnelles")
            st.markdown('<div class="editable-zone">', unsafe_allow_html=True)
            st.markdown("#### ✍️ Zone Éditable")
            
            edited_nutrition = st.text_area(
                "Nutrition",
                value=st.session_state.editable_reco.get("reco_nutrition", ""),
                height=300,
                key="ui_reco_nutrition"
            )
            st.session_state.editable_reco["reco_nutrition"] = edited_nutrition
            
            col1, col2 = st.columns([1, 4])
            with col1:
                if st.button("🔄 Réinitialiser", key="reset_nutrition"):
                    st.session_state.editable_reco["reco_nutrition"] = compile_recommendations_text(reco, 'nutrition')
                    st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        with tab2:
            st.markdown("### Recommandations en Micronutrition")
            st.markdown('<div class="editable-zone">', unsafe_allow_html=True)
            st.markdown("#### ✍️ Zone Éditable")
            
            edited_micro = st.text_area(
                "Micronutrition",
                value=st.session_state.editable_reco.get("reco_micronutrition", ""),
                height=300,
                key="ui_reco_micronutrition"
            )
            st.session_state.editable_reco["reco_micronutrition"] = edited_micro
            
            col1, col2 = st.columns([1, 4])
            with col1:
                if st.button("🔄 Réinitialiser", key="reset_micronutrition"):
                    st.session_state.editable_reco["reco_micronutrition"] = compile_recommendations_text(reco, 'micronutrition')
                    st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        with tab3:
            st.markdown("### Recommandations Lifestyle")
            st.markdown('<div class="editable-zone">', unsafe_allow_html=True)
            st.markdown("#### ✍️ Zone Éditable")
            
            edited_lifestyle = st.text_area(
                "Lifestyle",
                value=st.session_state.editable_reco.get("reco_lifestyle", ""),
                height=300,
                key="ui_reco_lifestyle"
            )
            st.session_state.editable_reco["reco_lifestyle"] = edited_lifestyle
            
            col1, col2 = st.columns([1, 4])
            with col1:
                if st.button("🔄 Réinitialiser", key="reset_lifestyle"):
                    st.session_state.editable_reco["reco_lifestyle"] = compile_recommendations_text(reco, 'lifestyle')
                    st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        with tab4:
            st.markdown("### Analyse Multimodale")
            st.markdown('<div class="editable-zone">', unsafe_allow_html=True)
            st.markdown("#### ✍️ Zone Éditable")
            
            edited_multimodal = st.text_area(
                "Multimodal",
                value=st.session_state.editable_reco.get("reco_multimodal", ""),
                height=300,
                key="ui_reco_multimodal"
            )
            st.session_state.editable_reco["reco_multimodal"] = edited_multimodal
            
            col1, col2 = st.columns([1, 4])
            with col1:
                if st.button("🔄 Réinitialiser", key="reset_multimodal"):
                    st.session_state.editable_reco["reco_multimodal"] = compile_recommendations_text(reco, 'multimodal')
                    st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)

elif page == "Export PDF":
    st.markdown("## 📄 Export PDF")
    
    if st.session_state.recommendations is None:
        st.info("ℹ️ Aucune donnée à exporter")
    else:
        if st.button("🚀 Générer le PDF", type="primary", use_container_width=True):
            try:
                with st.spinner("Génération..."):
                    pdf_data = prepare_pdf_data()
                    
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                        pdf_path = tmp_file.name
                    
                    generate_multimodal_report(
                        patient_data=pdf_data['patient'],
                        biology_data=pdf_data['biologie'],
                        microbiome_data=pdf_data['microbiote'],
                        cross_analysis=pdf_data['cross_analysis'],
                        recommendations=pdf_data['recommendations'],
                        follow_up=pdf_data['follow_up'],
                        output_path=pdf_path
                    )
                    
                    with open(pdf_path, 'rb') as f:
                        pdf_bytes = f.read()
                    
                    st.success("✅ PDF généré!")
                    
                    patient_name = st.session_state.patient_data.get('nom', 'Patient')
                    date_str = datetime.now().strftime("%Y%m%d")
                    filename = f"Rapport_{patient_name}_{date_str}.pdf"
                    
                    st.download_button(
                        label="📥 Télécharger le PDF",
                        data=pdf_bytes,
                        file_name=filename,
                        mime="application/pdf",
                        use_container_width=True
                    )
                    
                    os.unlink(pdf_path)
                    
            except Exception as e:
                st.error(f"❌ Erreur: {str(e)}")
                st.exception(e)

st.markdown("---")
st.caption("ALGO-LIFE © 2026 - Version Beta v1.0")
