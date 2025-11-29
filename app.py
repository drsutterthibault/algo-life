"""
ALGO-LIFE - Application Streamlit avec Import PDF Automatique
Plateforme d'Analyse Bio-Fonctionnelle avec Extraction PDF
Version 3.0 - Novembre 2025 - PDF IMPORT FEATURE

Auteur: Thibault - Product Manager Functional Biology, Espace Lab SA
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import sys
import os
import re
from io import BytesIO

# Import PDF extraction
try:
    import PyPDF2
    import pdfplumber
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    st.warning("⚠️ PyPDF2 ou pdfplumber non disponible. Installation requise pour l'extraction PDF.")

# Import des modules ALGO-LIFE
from algolife_statistical_analysis import AlgoLifeStatisticalAnalysis
from algolife_pdf_generator import generate_algolife_pdf_report
from algolife_engine import AlgoLifeEngine

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
    .info-box {
        background-color: #D1ECF1;
        padding: 1rem;
        border-radius: 5px;
        border-left: 5px solid #17A2B8;
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
    .upload-section {
        background-color: #F0F8FF;
        padding: 2rem;
        border-radius: 10px;
        border: 2px dashed #3498DB;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# FONCTIONS D'EXTRACTION PDF
# ============================================================================

class PDFExtractor:
    """Classe pour extraire les données des PDF médicaux"""
    
    @staticmethod
    def extract_text_from_pdf(pdf_file):
        """Extrait le texte d'un fichier PDF"""
        try:
            if pdfplumber:
                with pdfplumber.open(pdf_file) as pdf:
                    text = ""
                    for page in pdf.pages:
                        text += page.extract_text() or ""
                    return text
        except:
            pass
        
        # Fallback sur PyPDF2
        try:
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() or ""
            return text
        except Exception as e:
            st.error(f"❌ Erreur extraction PDF: {str(e)}")
            return ""
    
    @staticmethod
    def extract_biological_data(text, debug=False):
        """Extrait les données biologiques du texte PDF - Optimisé pour LIMS et SYNLAB"""
        data = {}
        
        # Patterns ULTRA-FLEXIBLES adaptés aux formats LIMS et SYNLAB
        patterns = {
            # Cortisol - PATTERNS INVERSÉS (valeur AVANT le label)
            'cortisol_reveil': [
                r'(\d+[.,]?\d*)\s+cortisol\s+r[ée]veil',  # "15.73 Cortisol réveil"
                r'cortisol\s+r[ée]veil\s+(\d+[.,]?\d*)',  # "Cortisol réveil 15.73"
                r'cortisol\s+salivaire\s+r[ée]veil\s+(\d+[.,]?\d*)',
            ],
            'cortisol_car_30': [
                r'(\d+[.,]?\d*)\s+cortisol\s+car\s+\([+]30\s*min\)',  # "3.04 Cortisol CAR (+30min)"
                r'cortisol\s+car\s+\([+]30\s*min\)\s+(\d+[.,]?\d*)',
                r'cortisol\s+salivaire\s+r[ée]veil\s*\+\s*30[\'\"′]?\s+(\d+[.,]?\d*)',
            ],
            'cortisol_12h': [
                r'(\d+[.,]?\d*)\s+cortisol\s+12h',  # "1.93 Cortisol 12h"
                r'cortisol\s+12h\s+(\d+[.,]?\d*)',
                r'cortisol\s+salivaire\s+12h\s+(\d+[.,]?\d*)',
            ],
            'cortisol_18h': [
                r'(\d+[.,]?\d*)\s+cortisol\s+18h',  # "0.55 Cortisol 18h"
                r'cortisol\s+18h\s+(\d+[.,]?\d*)',
                r'cortisol\s+salivaire\s+18h\s+(\d+[.,]?\d*)',
            ],
            'cortisol_22h': [
                r'(\d+[.,]?\d*)\s+cortisol\s+22h',  # "0.28 Cortisol 22h"
                r'cortisol\s+22h\s+(\d+[.,]?\d*)',
                r'cortisol\s+salivaire\s+22h\s+(\d+[.,]?\d*)',
            ],
            
            # DHEA - PATTERNS FLEXIBLES
            'dhea': [
                r'dhea\s+salivaire\s+(\d+[.,]?\d*)',  # Rapport labo
                r'dhea\s+(\d+[.,]?\d*)',  # Rapport synthétique
                r'dehydro\s+epi\s+androsterone.*?(\d+[.,]?\d*)\s*[µu]mol',
            ],
            
            # Inflammation
            'crp': [
                r'crp\s+ultra[-\s]sensible\s+(\d+[.,]?\d*)',
                r'crp[:\s]+(\d+[.,]?\d*)',
            ],
            
            # Glycémie
            'glycemie': [
                r'gly[cé][ée]mie\s+[àa]\s+jeun\s+(\d+[.,]?\d*)',
                r'gly[cé][ée]mie\s+(\d+[.,]?\d*)',
            ],
            'insuline': [
                r'insuline\s+[àa]\s+jeun\s+(\d+[.,]?\d*)',
                r'insuline\s+(\d+[.,]?\d*)',
            ],
            'homa_index': [
                r'index\s+homa\s+(\d+[.,]?\d*)',
                r'homa[:\s]+(\d+[.,]?\d*)',
            ],
            
            # Neurotransmetteurs - PATTERNS FLEXIBLES
            'dopamine': [
                r'dopamine\s+(\d+[.,]?\d*)',
            ],
            'serotonine': [
                r's[ée]rotonine\s+(\d+[.,]?\d*)',
            ],
            'noradrenaline': [
                r'noradr[ée]naline\s+(\d+[.,]?\d*)',
            ],
            'adrenaline': [
                r'adr[ée]naline\s+(\d+[.,]?\d*)',
            ],
            'hiaa_5': [
                r'5[-\s]?hiaa\s+(\d+[.,]?\d*)',
            ],
            'vma': [
                r'vma\s+(\d+[.,]?\d*)',
            ],
            
            # Micronutriments
            'vit_d': [
                r'25[-\s]?oh[-\s]?vitamine\s+d.*?(\d+[.,]?\d*)',
            ],
            'zinc': [
                r'zinc\s+(\d+[.,]?\d*)',
            ],
            'selenium': [
                r's[ée]l[ée]nium\s+(\d+[.,]?\d*)',
            ],
            'ferritine': [
                r'ferritine\s+(\d+[.,]?\d*)',
            ],
            
            # Perméabilité intestinale
            'zonuline': [
                r'zonuline\s+(\d+[.,]?\d*)',
            ],
            'lbp': [
                r'lbp\s+\(lipopolysaccharides?\s+binding.*?\)\s+(\d+[.,]?\d*)',
            ],
            
            # Oméga
            'aa_epa': [
                r'rapport\s+aa[/]epa\s+(\d+[.,]?\d*)',
            ],
            'omega3_index': [
                r'index\s+w3\s+(\d+[.,]?\d*)',
            ],
            
            # Homocystéine
            'homocysteine': [
                r'homocyst[ée]ine\s+(\d+[.,]?\d*)',
            ],
            
            # Microbiote
            'benzoate': [
                r'benzoate\s+(\d+[.,]?\d*)',
            ],
            'hippurate': [
                r'hippurate\s+(\d+[.,]?\d*)',
            ],
            'phenol': [
                r'phenols?\s+(\d+[.,]?\d*)',
            ],
            'p_cresol': [
                r'p[- ]?cr[ée]sol\s+(\d+[.,]?\d*)',
            ],
            'indican': [
                r'indican\s+(\d+[.,]?\d*)',
            ],
            'd_arabinitol': [
                r'arabinitol\s+(\d+[.,]?\d*)',
            ],
            'tartarate': [
                r'tartarate\s+(\d+[.,]?\d*)',
            ],
        }
        
        text_lower = text.lower()
        
        # Mode debug
        if debug:
            st.write("📄 **Texte extrait du PDF (premiers 3000 caractères):**")
            st.code(text[:3000])
            st.write("---")
            st.write("🔍 **Recherche en cours...**")
        
        # Essayer tous les patterns pour chaque biomarqueur
        for key, pattern_list in patterns.items():
            for pattern in pattern_list:
                match = re.search(pattern, text_lower, re.IGNORECASE)
                if match:
                    try:
                        value_str = match.group(1).replace(',', '.')
                        value = float(value_str)
                        data[key] = value
                        if debug:
                            st.success(f"✅ {key}: {value}")
                        break
                    except:
                        pass
        
        if debug and not data:
            st.warning("⚠️ Aucune donnée extraite avec les patterns actuels.")
        
        return data
    
    @staticmethod
    def extract_epigenetic_data(text):
        """Extrait les données épigénétiques du texte PDF"""
        data = {}
        
        patterns = {
            'biological_age': r'[âa]ge\s+biologique[:\s]+(\d+\.?\d*)',
            'telomere_length': r'longueur.*t[ée]lom[èe]re[:\s]+(\d+\.?\d*)',
            'methylation_score': r'm[ée]thylation.*score[:\s]+(\d+\.?\d*)',
        }
        
        text_lower = text.lower()
        
        for key, pattern in patterns.items():
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                try:
                    value = float(match.group(1))
                    data[key] = value
                except:
                    pass
        
        return data
    
    @staticmethod
    def extract_imaging_data(text):
        """Extrait les données d'imagerie (DXA, etc.) du texte PDF"""
        data = {}
        
        patterns = {
            'body_fat_percentage': r'masse\s+grasse[:\s]+(\d+\.?\d*)',
            'lean_mass': r'masse\s+maigre[:\s]+(\d+\.?\d*)',
            'bone_density': r'densit[ée].*osseuse[:\s]+(\d+\.?\d*)',
            'visceral_fat': r'graisse\s+visc[ée]rale[:\s]+(\d+\.?\d*)',
        }
        
        text_lower = text.lower()
        
        for key, pattern in patterns.items():
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                try:
                    value = float(match.group(1))
                    data[key] = value
                except:
                    pass
        
        return data

# ============================================================================
# FONCTION DE TRANSFORMATION DES DONNÉES
# ============================================================================

def prepare_data_for_engine(patient_data):
    """
    Transforme les données de patient_data vers le format attendu par AlgoLifeEngine
    """
    markers = patient_data.get('biological_markers', {})
    patient_info = patient_data.get('patient_info', {})
    
    bio_data = {
        'hormones_salivaires': {
            'cortisol_reveil': markers.get('cortisol_reveil'),
            'cortisol_reveil_30': markers.get('cortisol_car_30'),
            'cortisol_12h': markers.get('cortisol_12h'),
            'cortisol_18h': markers.get('cortisol_18h'),
            'cortisol_22h': markers.get('cortisol_22h'),
            'dhea': markers.get('dhea')
        },
        'inflammation': {
            'crp_us': markers.get('crp')
        },
        'acides_gras': {
            'aa_epa': markers.get('aa_epa')
        },
        'metabolisme_glucidique': {
            'homa': markers.get('homa_index'),
            'quicki': markers.get('quicki_index'),
            'glycemie': markers.get('glycemie'),
            'insuline': markers.get('insuline')
        },
        'permeabilite_intestinale': {
            'zonuline': markers.get('zonuline'),
            'lbp': markers.get('lbp')
        },
        'neurotransmetteurs': {
            'dopamine': markers.get('dopamine'),
            'serotonine': markers.get('serotonine'),
            'noradrenaline': markers.get('noradrenaline'),
            'adrenaline': markers.get('adrenaline'),
            'hiaa_5': markers.get('hiaa_5'),
            'vma': markers.get('vma')
        },
        'micronutriments': {
            'vit_d': markers.get('vit_d'),
            'selenium': markers.get('selenium'),
            'zinc': markers.get('zinc'),
            'ferritine': markers.get('ferritine')
        },
        'cardiovasculaire': {
            'homocysteine': markers.get('homocysteine'),
            'omega3_index': markers.get('omega3_index')
        },
        'lipides': {
            'triglycerides': markers.get('triglycerides'),
            'hdl': markers.get('hdl')
        },
        'microbiote': {
            'benzoate': markers.get('benzoate'),
            'hippurate': markers.get('hippurate'),
            'phenol': markers.get('phenol'),
            'p_cresol': markers.get('p_cresol'),
            'indican': markers.get('indican'),
            'tartarate': markers.get('tartarate'),
            'd_arabinitol': markers.get('d_arabinitol')
        }
    }
    
    epi_data = {
        'epigenetic_age': {
            'biological_age': markers.get('biological_age'),
            'chronological_age': patient_info.get('age')
        }
    }
    
    dxa_data = {
        'body_fat_percentage': markers.get('body_fat_percentage'),
        'lean_mass': markers.get('lean_mass'),
        'bone_density': markers.get('bone_density'),
        'visceral_fat': markers.get('visceral_fat')
    }
    
    return dxa_data, bio_data, epi_data

# ============================================================================
# INITIALISATION SESSION STATE
# ============================================================================

if 'patient_data' not in st.session_state:
    st.session_state.patient_data = {
        'patient_info': {},
        'biological_markers': {},
        'epigenetic_data': {},
        'imaging_data': {}
    }

if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = None

if 'chart_buffer' not in st.session_state:
    st.session_state.chart_buffer = None

if 'engine_results' not in st.session_state:
    st.session_state.engine_results = None

if 'pdf_extracted_data' not in st.session_state:
    st.session_state.pdf_extracted_data = {
        'biological': {},
        'epigenetic': {},
        'imaging': {}
    }

# ============================================================================
# HEADER
# ============================================================================

st.markdown('<h1 class="main-header">🧬 ALGO-LIFE</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Plateforme d\'Analyse Bio-Fonctionnelle avec Import PDF Automatique</p>', unsafe_allow_html=True)

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
    
    prelevement_date = st.date_input("Date du prélèvement", value=datetime.now())
    
    st.divider()
    
    # Sauvegarder les infos patient
    if st.button("💾 Enregistrer Informations Patient", key="save_patient_info"):
        st.session_state.patient_data['patient_info'] = {
            'nom': patient_name,
            'age': patient_age,
            'sexe': patient_sexe,
            'height': patient_height,
            'weight': patient_weight,
            'imc': patient_imc,
            'prelevement_date': prelevement_date.strftime('%Y-%m-%d')
        }
        st.success("✅ Informations patient enregistrées!")

# ============================================================================
# TABS PRINCIPAUX
# ============================================================================

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📤 Import PDF",
    "📊 Analyse Statistique", 
    "📄 Rapport PDF",
    "📚 Exemples",
    "ℹ️ Guide"
])

# ============================================================================
# TAB 1 - IMPORT PDF
# ============================================================================

with tab1:
    st.header("📤 Import Automatique des Résultats PDF")
    
    st.markdown("""
    <div class="info-box">
    <h4>🎯 Instructions d'Import</h4>
    <p>Téléchargez vos fichiers PDF de résultats médicaux. Le système extraira automatiquement les données biologiques, 
    épigénétiques et d'imagerie pour les analyser.</p>
    <ul>
        <li>✅ Biologie: Hormones, neurotransmetteurs, inflammation, métabolisme</li>
        <li>✅ Épigénétique: Âge biologique, téloméres, méthylation</li>
        <li>✅ Imagerie: DXA, composition corporelle, densité osseuse</li>
    </ul>
    </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    
    # Section Upload
    col_upload1, col_upload2, col_upload3 = st.columns(3)
    
    with col_upload1:
        st.subheader("🧪 PDF Biologie")
        bio_pdf = st.file_uploader(
            "Analyses biologiques",
            type=['pdf'],
            key='bio_pdf',
            help="PDF contenant: cortisol, DHEA, neurotransmetteurs, inflammation, etc."
        )
        
        if bio_pdf:
            debug_mode = st.checkbox("🐛 Mode Debug (voir le texte extrait)", key="debug_bio")
            
            if st.button("🔍 Extraire Données Bio", key="extract_bio"):
                with st.spinner("Extraction en cours..."):
                    text = PDFExtractor.extract_text_from_pdf(bio_pdf)
                    extracted = PDFExtractor.extract_biological_data(text, debug=debug_mode)
                    
                    if extracted:
                        st.session_state.pdf_extracted_data['biological'] = extracted
                        st.session_state.patient_data['biological_markers'].update(extracted)
                        st.success(f"✅ {len(extracted)} biomarqueurs extraits!")
                        
                        with st.expander("Voir les données extraites"):
                            st.json(extracted)
                    else:
                        st.warning("⚠️ Aucune donnée trouvée. Activez le mode Debug pour voir le texte extrait.")
    
    with col_upload2:
        st.subheader("🧬 PDF Épigénétique")
        epi_pdf = st.file_uploader(
            "Analyses épigénétiques",
            type=['pdf'],
            key='epi_pdf',
            help="PDF contenant: âge biologique, téloméres, méthylation"
        )
        
        if epi_pdf:
            if st.button("🔍 Extraire Données Épi", key="extract_epi"):
                with st.spinner("Extraction en cours..."):
                    text = PDFExtractor.extract_text_from_pdf(epi_pdf)
                    extracted = PDFExtractor.extract_epigenetic_data(text)
                    
                    if extracted:
                        st.session_state.pdf_extracted_data['epigenetic'] = extracted
                        st.session_state.patient_data['biological_markers'].update(extracted)
                        st.success(f"✅ {len(extracted)} paramètres extraits!")
                        
                        with st.expander("Voir les données extraites"):
                            st.json(extracted)
                    else:
                        st.warning("⚠️ Aucune donnée trouvée. Vérifiez le format du PDF.")
    
    with col_upload3:
        st.subheader("🏥 PDF Imagerie")
        img_pdf = st.file_uploader(
            "Analyses imagerie (DXA)",
            type=['pdf'],
            key='img_pdf',
            help="PDF contenant: composition corporelle, densité osseuse, masse grasse"
        )
        
        if img_pdf:
            if st.button("🔍 Extraire Données Img", key="extract_img"):
                with st.spinner("Extraction en cours..."):
                    text = PDFExtractor.extract_text_from_pdf(img_pdf)
                    extracted = PDFExtractor.extract_imaging_data(text)
                    
                    if extracted:
                        st.session_state.pdf_extracted_data['imaging'] = extracted
                        st.session_state.patient_data['biological_markers'].update(extracted)
                        st.success(f"✅ {len(extracted)} paramètres extraits!")
                        
                        with st.expander("Voir les données extraites"):
                            st.json(extracted)
                    else:
                        st.warning("⚠️ Aucune donnée trouvée. Vérifiez le format du PDF.")
    
    st.divider()
    
    # Récapitulatif des données extraites
    st.subheader("📊 Récapitulatif des Données Extraites")
    
    total_biological = len(st.session_state.pdf_extracted_data['biological'])
    total_epigenetic = len(st.session_state.pdf_extracted_data['epigenetic'])
    total_imaging = len(st.session_state.pdf_extracted_data['imaging'])
    total_params = total_biological + total_epigenetic + total_imaging
    
    col_sum1, col_sum2, col_sum3, col_sum4 = st.columns(4)
    
    with col_sum1:
        st.metric("🧪 Biomarqueurs Bio", total_biological)
    with col_sum2:
        st.metric("🧬 Paramètres Épi", total_epigenetic)
    with col_sum3:
        st.metric("🏥 Données Imagerie", total_imaging)
    with col_sum4:
        st.metric("📈 Total Paramètres", total_params)
    
    if total_params > 0:
        st.success(f"✅ {total_params} paramètres disponibles pour l'analyse!")
        
        if st.button("🚀 Lancer l'Analyse Complète", key="launch_analysis", type="primary"):
            with st.spinner("Analyse en cours..."):
                try:
                    # Analyse statistique
                    analyzer = AlgoLifeStatisticalAnalysis(st.session_state.patient_data)
                    
                    # Préparer bio_data pour les méthodes qui en ont besoin
                    dxa_data, bio_data, epi_data = prepare_data_for_engine(st.session_state.patient_data)
                    
                    stress_result = analyzer.calculate_stress_index()
                    metabolism_result = analyzer.calculate_metabolism_index(bio_data)
                    neuro_result = analyzer.calculate_neurotransmitter_index()
                    inflam_result = analyzer.calculate_inflammation_index()
                    microbiome_result = analyzer.calculate_microbiome_index()
                    
                    composite_indices = {
                        'stress': stress_result,
                        'metabolism': metabolism_result,
                        'neurotransmitter': neuro_result,
                        'inflammation': inflam_result,
                        'microbiome': microbiome_result
                    }
                    
                    model_results = analyzer.build_predictive_model()
                    correlations = analyzer.calculate_correlations()
                    recommendations = analyzer.generate_recommendations()
                    chart_buffer = analyzer.generate_visualizations()
                    
                    st.session_state.analysis_results = {
                        'composite_indices': composite_indices,
                        'model': model_results,
                        'correlations': correlations,
                        'recommendations': recommendations
                    }
                    st.session_state.chart_buffer = chart_buffer
                    
                    # Analyse AlgoLifeEngine
                    engine = AlgoLifeEngine()
                    engine_results = engine.analyze(dxa_data, bio_data, epi_data)
                    st.session_state.engine_results = engine_results
                    
                    st.success("✅ Analyse complète terminée! Consultez l'onglet 'Analyse Statistique'")
                    st.balloons()
                    
                except Exception as e:
                    st.error(f"❌ Erreur lors de l'analyse: {str(e)}")
                    import traceback
                    st.code(traceback.format_exc())
    else:
        st.info("📥 Importez au moins un fichier PDF pour commencer l'analyse.")
    
    st.divider()
    
    # Section saisie manuelle optionnelle
    with st.expander("➕ Saisie Manuelle Complémentaire"):
        st.markdown("""
        <div class="warning-box">
        <strong>Note:</strong> Utilisez cette section pour ajouter ou corriger des valeurs non extraites automatiquement.
        </div>
        """, unsafe_allow_html=True)
        
        st.subheader("Axe HPA - Cortisol & DHEA")
        col1, col2 = st.columns(2)
        
        with col1:
            cortisol_reveil = st.number_input(
                "Cortisol réveil (nmol/L)",
                min_value=0.0, max_value=100.0, value=0.0, step=0.1,
                key="manual_cortisol_reveil"
            )
            cortisol_car_30 = st.number_input(
                "Cortisol CAR +30 (nmol/L)",
                min_value=0.0, max_value=100.0, value=0.0, step=0.1,
                key="manual_cortisol_car_30"
            )
            cortisol_12h = st.number_input(
                "Cortisol 12h (nmol/L)",
                min_value=0.0, max_value=100.0, value=0.0, step=0.1,
                key="manual_cortisol_12h"
            )
        
        with col2:
            cortisol_18h = st.number_input(
                "Cortisol 18h (nmol/L)",
                min_value=0.0, max_value=100.0, value=0.0, step=0.1,
                key="manual_cortisol_18h"
            )
            cortisol_22h = st.number_input(
                "Cortisol 22h (nmol/L)",
                min_value=0.0, max_value=100.0, value=0.0, step=0.1,
                key="manual_cortisol_22h"
            )
            dhea = st.number_input(
                "DHEA (ng/mL)",
                min_value=0.0, max_value=50.0, value=0.0, step=0.1,
                key="manual_dhea"
            )
        
        if st.button("💾 Enregistrer Saisie Manuelle"):
            manual_data = {
                'cortisol_reveil': cortisol_reveil if cortisol_reveil > 0 else None,
                'cortisol_car_30': cortisol_car_30 if cortisol_car_30 > 0 else None,
                'cortisol_12h': cortisol_12h if cortisol_12h > 0 else None,
                'cortisol_18h': cortisol_18h if cortisol_18h > 0 else None,
                'cortisol_22h': cortisol_22h if cortisol_22h > 0 else None,
                'dhea': dhea if dhea > 0 else None,
            }
            
            # Supprimer les None
            manual_data = {k: v for k, v in manual_data.items() if v is not None}
            
            st.session_state.patient_data['biological_markers'].update(manual_data)
            st.success(f"✅ {len(manual_data)} valeurs ajoutées/mises à jour!")

# ============================================================================
# TAB 2 - ANALYSE STATISTIQUE
# ============================================================================

with tab2:
    st.header("📊 Analyse Statistique Multi-Dimensionnelle")
    
    if st.session_state.analysis_results is None:
        st.info("📥 Importez des données PDF et lancez l'analyse depuis l'onglet 'Import PDF'")
    else:
        results = st.session_state.analysis_results
        
        # Section 1: Indices Composites
        st.subheader("🎯 Indices Composites")
        
        indices = results['composite_indices']
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            stress_score = indices['stress']['score']
            st.metric(
                "Stress Index",
                f"{stress_score:.1f}/100",
                delta=None,
                help="Basé sur cortisol CAR, rythme circadien, DHEA"
            )
        
        with col2:
            metab_score = indices['metabolism']['score']
            st.metric(
                "Métabolisme",
                f"{metab_score:.1f}/100",
                delta=None,
                help="HOMA, QUICKI, inflammation"
            )
        
        with col3:
            neuro_score = indices['neurotransmitter']['score']
            st.metric(
                "Neurotransmetteurs",
                f"{neuro_score:.1f}/100",
                delta=None,
                help="Dopamine, sérotonine, catécholamines"
            )
        
        with col4:
            inflam_score = indices['inflammation']['score']
            st.metric(
                "Inflammation",
                f"{inflam_score:.1f}/100",
                delta=None,
                help="CRP, homocystéine, oméga-3"
            )
        
        with col5:
            micro_score = indices['microbiome']['score']
            st.metric(
                "Microbiome",
                f"{micro_score:.1f}/100",
                delta=None,
                help="Métabolites bactériens et fongiques"
            )
        
        st.divider()
        
        # Section 2: AlgoLifeEngine Results
        if st.session_state.engine_results:
            st.subheader("🧬 Scores AlgoLifeEngine")
            
            engine_res = st.session_state.engine_results
            
            col_e1, col_e2, col_e3, col_e4, col_e5, col_e6 = st.columns(6)
            
            with col_e1:
                stress_eng = engine_res['stress'].get('stress_score', 0)
                st.metric("Stress", f"{stress_eng or 0:.1f}", help=engine_res['stress'].get('stress_status', '—'))
            
            with col_e2:
                inflam_eng = engine_res['inflammation'].get('inflammation_score', 0)
                st.metric("Inflammation", f"{inflam_eng or 0:.1f}", help=engine_res['inflammation'].get('inflammation_status', '—'))
            
            with col_e3:
                omega_eng = engine_res['omega'].get('omega_score', 0)
                st.metric("Oméga-3", f"{omega_eng or 0:.1f}", help=engine_res['omega'].get('omega_status', '—'))
            
            with col_e4:
                glyc_eng = engine_res['glycemia'].get('glycemia_score', 0)
                st.metric("Glycémie", f"{glyc_eng or 0:.1f}", help=engine_res['glycemia'].get('glycemia_status', '—'))
            
            with col_e5:
                gut_eng = engine_res['gut'].get('gut_score', 0)
                st.metric("Intestin", f"{gut_eng or 0:.1f}", help=engine_res['gut'].get('gut_status', '—'))
            
            with col_e6:
                aging_eng = engine_res['aging'].get('aging_score', 0)
                st.metric("Vieillissement", f"{aging_eng or 0:.1f}", help=engine_res['aging'].get('aging_status', '—'))
            
            # Score global
            global_score = engine_res.get('global_score')
            if global_score:
                st.markdown(f"""
                <div class="success-box" style="text-align: center; margin-top: 1rem;">
                <h3>Score Global de Longévité: {global_score}/100</h3>
                </div>
                """, unsafe_allow_html=True)
        
        st.divider()
        
        # Section 3: Modèle Prédictif
        st.subheader("🤖 Modèle Prédictif Multi-Variés")
        
        model = results['model']
        
        col_m1, col_m2 = st.columns(2)
        
        with col_m1:
            st.metric(
                "R² Score",
                f"{model['r2_score']:.3f}",
                help="Capacité prédictive du modèle (0-1)"
            )
        
        with col_m2:
            st.metric(
                "Variables",
                len(model['feature_importance']),
                help="Nombre de variables dans le modèle"
            )
        
        # Top 5 facteurs
        st.markdown("**Top 5 Facteurs Impactants:**")
        
        top_factors = sorted(
            model['feature_importance'].items(),
            key=lambda x: abs(x[1]),
            reverse=True
        )[:5]
        
        for i, (feature, importance) in enumerate(top_factors, 1):
            st.write(f"{i}. **{feature}**: {importance:.3f}")
        
        st.divider()
        
        # Section 4: Corrélations
        st.subheader("🔗 Corrélations Significatives (p < 0.05)")
        
        corr_data = results['correlations']
        
        if corr_data['significant_correlations']:
            df_corr = pd.DataFrame(corr_data['significant_correlations'])
            st.dataframe(df_corr, use_container_width=True)
        else:
            st.info("Aucune corrélation significative détectée.")
        
        st.divider()
        
        # Section 5: Recommandations
        st.subheader("💡 Recommandations Personnalisées")
        
        recommendations = results['recommendations']
        
        for i, rec in enumerate(recommendations, 1):
            priority = rec.get('priority', 'Moyen')
            
            if priority == 'Urgent':
                box_class = 'danger-box'
            elif priority == 'Élevé':
                box_class = 'warning-box'
            else:
                box_class = 'info-box'
            
            st.markdown(f"""
            <div class="{box_class}">
            <strong>#{i} - {rec['area']}</strong> ({priority})
            <br>{rec['recommendation']}
            </div>
            """, unsafe_allow_html=True)
        
        # Plan d'action AlgoLifeEngine
        if st.session_state.engine_results and st.session_state.engine_results.get('action_plan'):
            st.markdown("### 🎯 Plan d'Action AlgoLifeEngine")
            
            for action in st.session_state.engine_results['action_plan']:
                st.markdown(f"- {action}")
        
        st.divider()
        
        # Section 6: Visualisations
        if st.session_state.chart_buffer:
            st.subheader("📈 Visualisations Graphiques")
            st.image(st.session_state.chart_buffer, use_container_width=True)

# ============================================================================
# TAB 3 - RAPPORT PDF
# ============================================================================

with tab3:
    st.header("📄 Génération du Rapport PDF Professionnel")
    
    if st.session_state.analysis_results is None:
        st.info("📥 Effectuez d'abord une analyse complète")
    else:
        st.markdown("""
        <div class="success-box">
        <h4>✅ Rapport Prêt à Générer</h4>
        <p>Le rapport PDF comprendra toutes les analyses, graphiques et recommandations personnalisées.</p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("📥 Générer & Télécharger le Rapport PDF", type="primary"):
            with st.spinner("Génération du rapport PDF en cours..."):
                try:
                    # MODIFICATION ICI - Enlever analysis_results et utiliser les bons paramètres
                    pdf_buffer = generate_algolife_pdf_report(
                        patient_data=st.session_state.patient_data,
                        biomarker_results=st.session_state.patient_data.get('biological_markers', {}),
                        engine_results=st.session_state.engine_results,
                        chart_buffer=st.session_state.chart_buffer
                    )
                    
                    st.success("✅ Rapport PDF généré avec succès!")
                    
                    st.download_button(
                        label="📥 Télécharger le Rapport PDF",
                        data=pdf_buffer,
                        file_name=f"ALGO-LIFE_{st.session_state.patient_data['patient_info'].get('nom', 'Patient')}_{datetime.now().strftime('%Y%m%d')}.pdf",
                        mime="application/pdf"
                    )
                    
                except Exception as e:
                    st.error(f"❌ Erreur lors de la génération du PDF: {str(e)}")
                    import traceback
                    st.code(traceback.format_exc())

# ============================================================================
# TAB 4 - EXEMPLES
# ============================================================================

with tab4:
    st.header("📚 Exemples de Profils Patients")
    
    st.markdown("""
    Cette section présente des cas cliniques types analysés avec ALGO-LIFE.
    """)
    
    example_col1, example_col2 = st.columns(2)
    
    with example_col1:
        st.subheader("Cas 1: Burnout Sévère")
        st.markdown("""
        **Patient:** Marc D., 42 ans, M
        
        **Résultats clés:**
        - CAR effondré: -12.69 nmol/L
        - Cortisol réveil: 15.73 nmol/L
        - Cortisol CAR +30: 3.04 nmol/L
        
        **Diagnostic:** Épuisement surrénalien avancé
        
        **Score Stress:** 12.3/100 (Critique)
        """)
    
    with example_col2:
        st.subheader("Cas 2: Dysbiose Intestinale")
        st.markdown("""
        **Patient:** Olivia L., 26 ans, F
        
        **Résultats clés:**
        - Benzoate: 18.14 (élevé)
        - Hippurate: 589.7 (très élevé)
        - Phénol: 21.20 (élevé)
        
        **Diagnostic:** Dysbiose de putréfaction
        
        **Score Microbiome:** 38.5/100
        """)

# ============================================================================
# TAB 5 - GUIDE
# ============================================================================

with tab5:
    st.header("ℹ️ Guide d'Utilisation")
    
    st.markdown("""
    ### 🎯 Workflow Complet
    
    **1. Import des PDF** (Tab 1)
    - Téléchargez vos PDF de résultats médicaux
    - Le système extrait automatiquement les données
    - Complétez manuellement si nécessaire
    - Lancez l'analyse complète
    
    **2. Consultation des Résultats** (Tab 2)
    - Examinez les indices composites
    - Consultez les scores AlgoLifeEngine
    - Analysez le modèle prédictif
    - Prenez connaissance des recommandations
    
    **3. Génération du Rapport** (Tab 3)
    - Générez le rapport PDF professionnel
    - Téléchargez pour archivage
    - Partagez avec le patient
    
    ### 🔬 Modules d'Analyse
    
    #### AlgoLifeEngine
    - Score de Stress (CAR)
    - Score d'Inflammation (CRP)
    - Score Glycémique (HOMA)
    - Score Intestinal (Zonuline)
    - Score de Vieillissement
    - **Score Global de Longévité**
    
    #### Analyse Statistique
    - Indices composites multi-dimensionnels
    - Modèle prédictif par régression linéaire
    - Corrélations significatives
    - Recommandations hiérarchisées
    
    ### 📊 Interprétation des Scores
    
    - **80-100**: Excellent
    - **60-79**: Bon
    - **40-59**: Modéré
    - **20-39**: Faible
    - **0-19**: Critique
    
    ### 💡 Formats PDF Supportés
    
    Le système peut extraire des données de la plupart des PDF médicaux standards.
    Pour une extraction optimale, assurez-vous que:
    - Le PDF contient du texte (pas uniquement des images)
    - Les valeurs numériques sont clairement indiquées
    - Les unités sont mentionnées
    
    ### 🆘 Support
    
    **Développeur:** Thibault  
    **Organisation:** Espace Lab SA, Geneva  
    **Version:** 3.0 (PDF Import Feature)
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
    st.caption("Version 3.0 - PDF Import")
    st.caption(f"Dernière mise à jour: {datetime.now().strftime('%d/%m/%Y')}")
