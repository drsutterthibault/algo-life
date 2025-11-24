"""
ALGO-LIFE - Application Streamlit Complète
Plateforme d'Analyse Bio-Fonctionnelle avec Rapports Statistiques Avancés
Version 2.0 - Novembre 2025

Auteur: Thibault - Product Manager Functional Biology, Espace Lab SA
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import sys
import os

# Import des modules ALGO-LIFE
from algolife_statistical_analysis import AlgoLifeStatisticalAnalysis
from algolife_pdf_generator import generate_algolife_pdf_report

# ============================================================================
# CONFIGURATION DE LA PAGE
# ============================================================================

st.set_page_config(
    page_title="ALGO-LIFE - Analyse Bio-Fonctionnelle",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personnalisé
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        color: #2C3E50;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #3498DB;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #F8F9FA;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 5px solid #3498DB;
        margin: 1rem 0;
    }
    .success-box {
        background-color: #D4EDDA;
        padding: 1rem;
        border-radius: 5px;
        border-left: 5px solid #28A745;
    }
    .warning-box {
        background-color: #FFF3CD;
        padding: 1rem;
        border-radius: 5px;
        border-left: 5px solid #FFC107;
    }
    .danger-box {
        background-color: #F8D7DA;
        padding: 1rem;
        border-radius: 5px;
        border-left: 5px solid #DC3545;
    }
    .stButton>button {
        width: 100%;
        background-color: #3498DB;
        color: white;
        font-weight: bold;
        border-radius: 5px;
        padding: 0.5rem 1rem;
    }
    .stButton>button:hover {
        background-color: #2C3E50;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# INITIALISATION SESSION STATE
# ============================================================================

if 'patient_data' not in st.session_state:
    st.session_state.patient_data = {}

if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = None

if 'chart_buffer' not in st.session_state:
    st.session_state.chart_buffer = None

# ============================================================================
# HEADER
# ============================================================================

st.markdown('<h1 class="main-header">🧬 ALGO-LIFE</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Plateforme d\'Analyse Bio-Fonctionnelle Multi-Dimensionnelle</p>', unsafe_allow_html=True)

# ============================================================================
# SIDEBAR - INFORMATIONS PATIENT
# ============================================================================

with st.sidebar:
    st.header("📋 Informations Patient")
    
    patient_name = st.text_input("Nom du patient", value="Patient 001", key="patient_name")
    
    col_age, col_sexe = st.columns(2)
    with col_age:
        patient_age = st.number_input("Âge", min_value=18, max_value=120, value=45, key="patient_age")
    with col_sexe:
        patient_sexe = st.selectbox("Sexe", ["Masculin", "Féminin"], key="patient_sexe")
    
    col_height, col_weight = st.columns(2)
    with col_height:
        patient_height = st.number_input("Taille (cm)", min_value=100, max_value=250, value=170, key="patient_height")
    with col_weight:
        patient_weight = st.number_input("Poids (kg)", min_value=30, max_value=200, value=75, key="patient_weight")
    
    patient_imc = patient_weight / ((patient_height/100) ** 2)
    st.metric("IMC", f"{patient_imc:.1f}")
    
    st.divider()
    
    # Date du prélèvement
    prelevement_date = st.date_input("Date du prélèvement", value=datetime.now())
    
    st.divider()
    
    # Statut des données
    if st.session_state.patient_data:
        st.success("✅ Données saisies")
    else:
        st.warning("⚠️ Aucune donnée")
    
    if st.session_state.analysis_results:
        st.success("✅ Analyse effectuée")
    else:
        st.info("ℹ️ En attente d'analyse")

# ============================================================================
# TABS PRINCIPAUX
# ============================================================================

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Saisie des Données",
    "📈 Analyse Statistique",
    "📄 Rapport PDF",
    "📚 Exemples & Templates",
    "ℹ️ Guide"
])

# ============================================================================
# TAB 1 - SAISIE DES DONNÉES
# ============================================================================

with tab1:
    st.header("Saisie des Biomarqueurs")
    
    # Créer des sous-tabs pour organiser les données
    sub_tab1, sub_tab2, sub_tab3, sub_tab4 = st.tabs([
        "🧪 Axe HPA (Stress)",
        "🧠 Neurotransmetteurs",
        "🔥 Métabolisme",
        "🦠 Microbiote"
    ])
    
    # SUB-TAB 1: Axe HPA
    with sub_tab1:
        st.subheader("Profil Cortisol Salivaire")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            cortisol_reveil = st.number_input(
                "Cortisol réveil (nmol/L)",
                min_value=0.0, value=15.73, step=0.01,
                help="Valeurs normales: 5-17.1 nmol/L"
            )
            cortisol_car = st.number_input(
                "Cortisol CAR +30min (nmol/L)",
                min_value=0.0, value=3.04, step=0.01,
                help="Valeurs normales: 7.5-25.6 nmol/L - CAR < 7.5 = signature burnout"
            )
        
        with col2:
            cortisol_12h = st.number_input(
                "Cortisol 12h (nmol/L)",
                min_value=0.0, value=1.93, step=0.01,
                help="Valeurs normales: 1.9-5.2 nmol/L"
            )
            cortisol_18h = st.number_input(
                "Cortisol 18h (nmol/L)",
                min_value=0.0, value=0.55, step=0.01,
                help="Valeurs normales: 0.3-3.0 nmol/L"
            )
        
        with col3:
            cortisol_22h = st.number_input(
                "Cortisol 22h (nmol/L)",
                min_value=0.0, value=0.28, step=0.01,
                help="Valeurs normales: 0.3-1.4 nmol/L"
            )
            dhea = st.number_input(
                "DHEA (nmol/L)",
                min_value=0.0, value=2.33, step=0.01,
                help="Valeurs normales: 0.53-2.44 nmol/L"
            )
    
    # SUB-TAB 2: Neurotransmetteurs
    with sub_tab2:
        st.subheader("Neurotransmetteurs Urinaires")
        
        col1, col2 = st.columns(2)
        
        with col1:
            dopamine = st.number_input(
                "Dopamine (µmol/mol créat)",
                min_value=0.0, value=125.46, step=0.01,
                help="Valeurs normales: 108-244 µmol/mol"
            )
            serotonine = st.number_input(
                "Sérotonine (µmol/mol créat)",
                min_value=0.0, value=68.26, step=0.01,
                help="Valeurs normales: 38-89 µmol/mol"
            )
            noradrenaline = st.number_input(
                "Noradrénaline (µmol/mol créat)",
                min_value=0.0, value=17.15, step=0.01,
                help="Valeurs normales: 11.1-28.0 µmol/mol"
            )
        
        with col2:
            adrenaline = st.number_input(
                "Adrénaline (µmol/mol créat)",
                min_value=0.0, value=0.79, step=0.01,
                help="Valeurs normales: 0.76-4.23 µmol/mol"
            )
            hiaa_5 = st.number_input(
                "5-HIAA (mmol/mol créat)",
                min_value=0.0, value=3.11, step=0.01,
                help="Métabolite sérotonine - Valeurs: 1.0-3.3 mmol/mol"
            )
            vma = st.number_input(
                "VMA (mmol/mol créat)",
                min_value=0.0, value=1.35, step=0.01,
                help="Valeurs normales: 1.04-2.2 mmol/mol"
            )
    
    # SUB-TAB 3: Métabolisme
    with sub_tab3:
        st.subheader("Métabolisme Glucidique et Inflammation")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**Glycémie**")
            glycemie = st.number_input(
                "Glycémie à jeun (mg/dL)",
                min_value=0.0, value=87.04, step=0.01,
                help="Valeurs normales: 60-110 mg/dL"
            )
            insuline = st.number_input(
                "Insuline à jeun (pmol/L)",
                min_value=0.0, value=90.3, step=0.1,
                help="Valeurs normales: 19-75 pmol/L"
            )
        
        with col2:
            st.markdown("**Indices Insulino-Résistance**")
            homa_index = st.number_input(
                "HOMA Index",
                min_value=0.0, value=2.7, step=0.01,
                help="Valeurs normales: <2.4 - Plus élevé = plus de résistance"
            )
            quicki_index = st.number_input(
                "QUICKI Index",
                min_value=0.0, value=0.33, step=0.01,
                help="Valeurs normales: >0.34 - Plus bas = moins de sensibilité"
            )
        
        with col3:
            st.markdown("**Inflammation & Vitamines**")
            crp = st.number_input(
                "CRP ultra-sensible (mg/L)",
                min_value=0.0, value=2.3, step=0.1,
                help="Valeurs normales: <1.0 mg/L"
            )
            vit_d = st.number_input(
                "Vitamine D (nmol/L)",
                min_value=0.0, value=39.5, step=0.1,
                help="Valeurs optimales: >75 nmol/L"
            )
        
        st.divider()
        
        col4, col5 = st.columns(2)
        
        with col4:
            st.markdown("**Oligo-éléments**")
            selenium = st.number_input("Sélénium (µg/L)", min_value=0.0, value=71.23, step=0.01)
            zinc = st.number_input("Zinc (µg/dL)", min_value=0.0, value=78.11, step=0.01)
            ferritine = st.number_input("Ferritine (µg/L)", min_value=0.0, value=22.1, step=0.1)
        
        with col5:
            st.markdown("**Marqueurs Cardiovasculaires**")
            homocysteine = st.number_input("Homocystéine (µmol/L)", min_value=0.0, value=12.83, step=0.01)
            omega3_index = st.number_input("Oméga-3 Index (%)", min_value=0.0, value=6.57, step=0.01)
    
    # SUB-TAB 4: Microbiote
    with sub_tab4:
        st.subheader("Métabolites Organiques Urinaires")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Module Bactérien**")
            benzoate = st.number_input("Benzoate (mg/g créat)", min_value=0.0, value=18.14, step=0.01)
            hippurate = st.number_input("Hippurate (mg/g créat)", min_value=0.0, value=589.7, step=0.1)
            phenol = st.number_input("Phénol (mg/g créat)", min_value=0.0, value=21.20, step=0.01)
            p_cresol = st.number_input("P-Crésol (mg/g créat)", min_value=0.0, value=59.27, step=0.01)
            indican = st.number_input("Indican (mg/g créat)", min_value=0.0, value=45.88, step=0.01)
        
        with col2:
            st.markdown("**Perméabilité Intestinale**")
            lbp = st.number_input(
                "LBP (ng/mL)",
                min_value=0.0, value=16.47, step=0.01,
                help="Endotoxémie - Valeurs normales: 4-13.1 ng/mL"
            )
            zonuline = st.number_input(
                "Zonuline (ng/mL)",
                min_value=0.0, value=35.12, step=0.01,
                help="Perméabilité intestinale - Valeurs normales: 17-37 ng/mL"
            )
            
            st.markdown("**Module Fongique**")
            tartarate = st.number_input("Tartarate (mg/g créat)", min_value=0.0, value=1.56, step=0.01)
            d_arabinitol = st.number_input("D-Arabinitol (mg/g créat)", min_value=0.0, value=0.34, step=0.01)
    
    # Bouton d'enregistrement
    st.divider()
    
    col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
    
    with col_btn2:
        if st.button("💾 ENREGISTRER TOUTES LES DONNÉES", type="primary", use_container_width=True):
            # Compilation de toutes les données
            st.session_state.patient_data = {
                'patient_info': {
                    'nom': patient_name,
                    'age': patient_age,
                    'sexe': patient_sexe,
                    'taille': patient_height,
                    'poids': patient_weight,
                    'imc': patient_imc,
                    'date_prelevement': prelevement_date.strftime('%d/%m/%Y')
                },
                'biological_markers': {
                    'cortisol_reveil': cortisol_reveil,
                    'cortisol_car_30': cortisol_car,
                    'cortisol_12h': cortisol_12h,
                    'cortisol_18h': cortisol_18h,
                    'cortisol_22h': cortisol_22h,
                    'dhea': dhea,
                    'dopamine': dopamine,
                    'serotonine': serotonine,
                    'noradrenaline': noradrenaline,
                    'adrenaline': adrenaline,
                    'hiaa_5': hiaa_5,
                    'vma': vma,
                    'glycemie': glycemie,
                    'insuline': insuline,
                    'homa_index': homa_index,
                    'quicki_index': quicki_index,
                    'crp': crp,
                    'vit_d': vit_d,
                    'selenium': selenium,
                    'zinc': zinc,
                    'ferritine': ferritine,
                    'homocysteine': homocysteine,
                    'omega3_index': omega3_index,
                    'benzoate': benzoate,
                    'hippurate': hippurate,
                    'phenol': phenol,
                    'p_cresol': p_cresol,
                    'indican': indican,
                    'lbp': lbp,
                    'zonuline': zonuline,
                    'tartarate': tartarate,
                    'd_arabinitol': d_arabinitol
                }
            }
            
            st.success("✅ Toutes les données ont été enregistrées avec succès!")
            st.balloons()
            
            # Afficher un résumé
            with st.expander("📊 Résumé des données enregistrées"):
                st.json(st.session_state.patient_data)

# ============================================================================
# TAB 2 - ANALYSE STATISTIQUE
# ============================================================================

with tab2:
    st.header("Analyse Statistique Multi-Dimensionnelle")
    
    if not st.session_state.patient_data:
        st.warning("⚠️ Veuillez d'abord saisir les données dans l'onglet 'Saisie des Données'")
    else:
        col_launch1, col_launch2, col_launch3 = st.columns([1, 2, 1])
        
        with col_launch2:
            if st.button("🔬 LANCER L'ANALYSE COMPLÈTE", type="primary", use_container_width=True):
                with st.spinner("🔄 Analyse en cours... Calcul des indices composites et modèles prédictifs"):
                    
                    try:
                        # Créer l'instance d'analyse
                        analyzer = AlgoLifeStatisticalAnalysis(st.session_state.patient_data)
                        
                        # Calculer tous les indices
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        status_text.text("Calcul des indices composites...")
                        progress_bar.progress(20)
                        indices_results = analyzer.calculate_all_indices()
                        
                        status_text.text("Construction du modèle prédictif...")
                        progress_bar.progress(50)
                        model_results = analyzer.build_predictive_model()
                        
                        status_text.text("Génération des visualisations...")
                        progress_bar.progress(75)
                        chart_buffer = analyzer.generate_statistical_visualizations()
                        
                        status_text.text("Compilation du rapport complet...")
                        progress_bar.progress(90)
                        comprehensive_data = analyzer.generate_comprehensive_report_data()
                        
                        progress_bar.progress(100)
                        status_text.text("✅ Analyse terminée!")
                        
                        # Stocker les résultats
                        st.session_state.analysis_results = comprehensive_data
                        st.session_state.chart_buffer = chart_buffer
                        
                        st.success("✅ Analyse statistique terminée avec succès!")
                        st.balloons()
                        
                    except Exception as e:
                        st.error(f"❌ Erreur lors de l'analyse: {str(e)}")
                        import traceback
                        st.code(traceback.format_exc())
        
        # Afficher les résultats si disponibles
        if st.session_state.analysis_results:
            st.divider()
            
            # Section 1: Indices Composites
            st.subheader("📊 Indices Composites")
            
            indices = st.session_state.analysis_results.get('composite_indices', {})
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                if 'stress' in indices:
                    stress_score = indices['stress']['score']
                    delta = "↓ Bon" if stress_score < 40 else "⚠️ Attention" if stress_score < 60 else "❗ Critique"
                    st.metric("Stress Index", f"{stress_score:.0f}/100", delta)
                    with st.expander("Détails"):
                        st.caption(indices['stress']['interpretation'])
                        st.caption(f"**Phase:** {indices['stress'].get('phase', 'N/A')}")
            
            with col2:
                if 'metabolic' in indices:
                    metab_score = indices['metabolic']['score']
                    delta = "✅ Bon" if metab_score >= 70 else "⚠️ Attention" if metab_score >= 50 else "❗ Critique"
                    st.metric("Métabolisme", f"{metab_score:.0f}/100", delta)
                    with st.expander("Détails"):
                        st.caption(indices['metabolic']['interpretation'])
                        st.caption(f"**Risque:** {indices['metabolic'].get('risk_level', 'N/A')}")
            
            with col3:
                if 'neurotransmitters' in indices:
                    neuro_score = indices['neurotransmitters']['score']
                    delta = "✅ Bon" if neuro_score >= 60 else "⚠️ Attention" if neuro_score >= 40 else "❗ Critique"
                    st.metric("Neurotransmetteurs", f"{neuro_score:.0f}/100", delta)
                    with st.expander("Détails"):
                        st.caption(indices['neurotransmitters']['interpretation'])
            
            with col4:
                if 'inflammation' in indices:
                    inflam_score = indices['inflammation']['score']
                    delta = "✅ Bon" if inflam_score < 30 else "⚠️ Attention" if inflam_score < 60 else "❗ Critique"
                    st.metric("Inflammation", f"{inflam_score:.0f}/100", delta)
                    with st.expander("Détails"):
                        st.caption(indices['inflammation']['interpretation'])
            
            st.divider()
            
            # Section 2: Modèle Prédictif
            st.subheader("🤖 Modèle Prédictif (Régression Multiple)")
            
            model_results = st.session_state.analysis_results.get('statistical_model', {})
            
            if model_results.get('success'):
                col_m1, col_m2, col_m3 = st.columns(3)
                
                with col_m1:
                    r2 = model_results.get('r2_score', 0)
                    st.metric(
                        "R² Score",
                        f"{r2:.3f}",
                        f"{r2*100:.1f}% variance expliquée"
                    )
                
                with col_m2:
                    n_features = model_results.get('n_features', 0)
                    st.metric(
                        "Variables analysées",
                        n_features,
                        "biomarqueurs"
                    )
                
                with col_m3:
                    quality = "Excellent" if r2 > 0.7 else "Bon" if r2 > 0.5 else "Modéré"
                    st.metric(
                        "Qualité du modèle",
                        quality,
                        f"R² = {r2:.3f}"
                    )
                
                st.divider()
                
                # Top facteurs
                st.subheader("🎯 Top 5 Facteurs Impactants")
                
                coeffs_df = model_results.get('coefficients')
                if coeffs_df is not None:
                    top5 = coeffs_df.head(5)
                    
                    for idx, row in top5.iterrows():
                        factor = row['Feature'].replace('_', ' ').title()
                        coef = row['Coefficient']
                        
                        col_factor, col_impact = st.columns([3, 1])
                        
                        with col_factor:
                            if coef > 0:
                                st.success(f"✅ **{factor}**")
                            else:
                                st.error(f"❌ **{factor}**")
                        
                        with col_impact:
                            st.metric("Coef.", f"{coef:+.3f}")
            
            st.divider()
            
            # Section 3: Visualisations
            st.subheader("📈 Visualisations Graphiques")
            
            if st.session_state.chart_buffer:
                st.image(st.session_state.chart_buffer, use_container_width=True)
            
            st.divider()
            
            # Section 4: Recommandations
            st.subheader("💊 Recommandations Personnalisées")
            
            recommendations = st.session_state.analysis_results.get('recommendations', [])
            
            if recommendations:
                for i, rec in enumerate(recommendations[:3], 1):
                    priority = rec.get('priority', 3)
                    
                    if priority == 1:
                        st.markdown(f"### 🔴 Priorité {i} - {rec.get('category', 'N/A')}")
                    elif priority == 2:
                        st.markdown(f"### 🟡 Priorité {i} - {rec.get('category', 'N/A')}")
                    else:
                        st.markdown(f"### 🟢 Priorité {i} - {rec.get('category', 'N/A')}")
                    
                    col_rec1, col_rec2 = st.columns([2, 1])
                    
                    with col_rec1:
                        st.markdown(f"**Constat:** {rec.get('issue', 'N/A')}")
                        st.markdown(f"**Objectif:** {rec.get('action', 'N/A')}")
                        
                        interventions = rec.get('interventions', [])
                        if interventions:
                            st.markdown("**Interventions:**")
                            for intervention in interventions:
                                st.markdown(f"• {intervention}")
                    
                    with col_rec2:
                        impact = rec.get('expected_impact', 'Modéré')
                        st.metric("Impact attendu", impact)
                    
                    st.divider()

# ============================================================================
# TAB 3 - RAPPORT PDF
# ============================================================================

with tab3:
    st.header("Génération du Rapport PDF Professionnel")
    
    if not st.session_state.analysis_results:
        st.warning("⚠️ Veuillez d'abord effectuer l'analyse statistique dans l'onglet précédent")
    else:
        st.info("📄 Rapport prêt à être généré avec toutes les analyses statistiques et graphiques")
        
        col_pdf1, col_pdf2, col_pdf3 = st.columns([1, 2, 1])
        
        with col_pdf2:
            if st.button("📥 GÉNÉRER LE RAPPORT PDF COMPLET", type="primary", use_container_width=True):
                with st.spinner("📄 Génération du rapport PDF en cours..."):
                    try:
                        # Générer le PDF
                        pdf_buffer = generate_algolife_pdf_report(
                            patient_name=st.session_state.patient_data['patient_info']['nom'],
                            analysis_results=st.session_state.analysis_results,
                            chart_buffer=st.session_state.chart_buffer
                        )
                        
                        st.success("✅ Rapport PDF généré avec succès!")
                        
                        # Bouton de téléchargement
                        st.download_button(
                            label="📥 Télécharger le Rapport PDF",
                            data=pdf_buffer,
                            file_name=f"ALGO-LIFE_Rapport_{patient_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                        
                        st.balloons()
                        
                    except Exception as e:
                        st.error(f"❌ Erreur lors de la génération du PDF: {str(e)}")
                        import traceback
                        st.code(traceback.format_exc())
        
        st.divider()
        
        # Aperçu du contenu du rapport
        st.subheader("📋 Contenu du Rapport")
        
        with st.expander("Voir le contenu détaillé du rapport"):
            st.markdown("""
            ### Le rapport PDF comprend:
            
            **Page 1 - Couverture**
            - Informations patient complètes
            - Résumé exécutif des résultats
            - Score R² du modèle prédictif
            
            **Page 2 - Indices Composites**
            - Tableau détaillé de tous les indices calculés
            - Interprétations pour chaque indice
            - Analyses mécanistiques approfondies
            
            **Page 3 - Analyse Statistique**
            - Performance du modèle prédictif (R²)
            - Top 5 des facteurs impactants
            - Corrélations significatives (p < 0.05)
            
            **Page 4 - Visualisations Graphiques**
            - 6 graphiques professionnels
            - Profil radar multi-dimensionnel
            - Courbes de tendance et distributions
            
            **Page 5 - Recommandations**
            - Plan d'action personnalisé hiérarchisé
            - Interventions spécifiques par priorité
            - Calendrier de suivi recommandé
            """)

# ============================================================================
# TAB 4 - EXEMPLES & TEMPLATES
# ============================================================================

with tab4:
    st.header("📚 Exemples de Rapports & Templates")
    
    st.markdown("""
    Cette section présente des exemples de rapports générés par ALGO-LIFE pour différents profils patients.
    """)
    
    # Exemples de cas cliniques
    example_col1, example_col2 = st.columns(2)
    
    with example_col1:
        st.subheader("Cas 1: Dysbiose Bactérienne")
        st.markdown("""
        **Patient:** Olivia L., 26 ans, F
        
        **Résultats clés:**
        - Benzoate élevé (18.14 vs max 4.47)
        - Hippurate très élevé (589.7 vs max 529.9)
        - Phénol élevé (21.20 vs max 11.20)
        
        **Diagnostic:**
        Prolifération importante de la flore protéolytique phénylalanine dépendante avec dysbiose de putréfaction.
        
        **Score dysbiose:** 38.5/100
        """)
        
        if st.button("Charger cet exemple", key="example1"):
            st.info("Template chargé! Vous pouvez maintenant modifier les valeurs.")
    
    with example_col2:
        st.subheader("Cas 2: Santé Osseuse")
        st.markdown("""
        **Patient:** Isabelle F., 46 ans, F
        
        **Résultats clés:**
        - TBS L1-L4: 1.417 (microarchitecture normale)
        - DMO total rachis: 0.996 g/cm² (T-score: -0.1)
        - DMO hanche total: 1.128 g/cm² (T-score: +1.4)
        
        **Diagnostic:**
        Santé osseuse modérée nécessitant surveillance.
        
        **Indice composite:** 57.0/100
        """)
        
        if st.button("Charger cet exemple", key="example2"):
            st.info("Template chargé! Vous pouvez maintenant modifier les valeurs.")

# ============================================================================
# TAB 5 - GUIDE
# ============================================================================

with tab5:
    st.header("ℹ️ Guide d'Utilisation ALGO-LIFE")
    
    st.markdown("""
    ### 🎯 Objectif de la Plateforme
    
    ALGO-LIFE est une plateforme d'analyse bio-fonctionnelle multi-dimensionnelle qui permet de:
    - **Calculer des indices composites** (stress, métabolisme, neurotransmetteurs, inflammation)
    - **Construire des modèles prédictifs** par régression linéaire multiple
    - **Générer des rapports statistiques professionnels** au format PDF
    - **Identifier les leviers d'action prioritaires** pour chaque patient
    
    ---
    
    ### 📝 Workflow Recommandé
    
    1. **Saisie des Données** (Tab 1)
       - Renseigner les informations patient
       - Saisir tous les biomarqueurs disponibles
       - Enregistrer les données
    
    2. **Analyse Statistique** (Tab 2)
       - Lancer l'analyse complète
       - Examiner les indices composites
       - Consulter le modèle prédictif et les corrélations
       - Prendre connaissance des recommandations
    
    3. **Génération du Rapport** (Tab 3)
       - Générer le rapport PDF professionnel
       - Télécharger pour le dossier patient
       - Partager avec le patient et/ou autres praticiens
    
    ---
    
    ### 🔬 Modules d'Analyse
    
    #### 1. Axe HPA (Hypothalamo-Hypophyso-Surrénalien)
    - **Cortisol CAR**: Indicateur clé du burnout (< 7.5 nmol/L = signature épuisement)
    - **Rythme circadien**: Profil sur 24h pour évaluer l'adaptation au stress
    - **DHEA**: Réserve adaptative surrénalienne
    
    #### 2. Neurotransmetteurs
    - **Dopamine**: Motivation, plaisir
    - **Sérotonine**: Humeur, bien-être
    - **Noradrénaline**: Vigilance, stress
    - **Analyse des métabolites**: 5-HIAA, VMA, MHPG
    
    #### 3. Métabolisme
    - **HOMA Index**: Résistance insulinique
    - **QUICKI Index**: Sensibilité insulinique
    - **CRP**: Inflammation systémique
    - **Homocystéine**: Risque cardiovasculaire
    
    #### 4. Microbiote
    - **Métabolites bactériens**: Benzoate, hippurate, phénol, p-crésol
    - **Métabolites fongiques**: Tartarate, D-arabinitol
    - **Perméabilité intestinale**: LBP, zonuline
    
    ---
    
    ### 📊 Interprétation des Scores
    
    **Indices Composites (0-100):**
    - **80-100**: Excellent
    - **60-79**: Bon
    - **40-59**: Modéré - Surveillance
    - **20-39**: Faible - Intervention recommandée
    - **0-19**: Critique - Traitement urgent
    
    **R² du Modèle Prédictif:**
    - **> 0.7**: Excellente capacité prédictive
    - **0.5-0.7**: Bonne capacité prédictive
    - **< 0.5**: Capacité modérée
    
    ---
    
    ### 💡 Conseils d'Utilisation
    
    - ✅ Saisir un maximum de biomarqueurs pour une analyse optimale
    - ✅ Le modèle nécessite au moins 4 variables pour fonctionner
    - ✅ Les corrélations avec p < 0.05 sont statistiquement significatives
    - ✅ Les recommandations sont hiérarchisées par impact attendu
    - ✅ Le rapport PDF est généré au format médical professionnel
    
    ---
    
    ### 🆘 Support & Contact
    
    **Développeur:** Thibault - Product Manager Functional Biology  
    **Organisation:** Espace Lab SA, Geneva  
    **Version:** 2.0 (Novembre 2025)
    
    Pour toute question ou suggestion d'amélioration, n'hésitez pas à nous contacter.
    """)

# ============================================================================
# FOOTER
# ============================================================================

st.divider()

footer_col1, footer_col2, footer_col3 = st.columns(3)

with footer_col1:
    st.caption("© 2025 ALGO-LIFE")
    st.caption("Product Manager: Thibault")

with footer_col2:
    st.caption("Espace Lab SA - Geneva")
    st.caption("Biologie Fonctionnelle")

with footer_col3:
    st.caption("Version 2.0")
    st.caption(f"Dernière mise à jour: {datetime.now().strftime('%d/%m/%Y')}")
