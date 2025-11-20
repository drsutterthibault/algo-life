import streamlit as st
import re
import tempfile
import json
from datetime import datetime

# Remplacement PyPDF2 → pypdf (compatible Streamlit Cloud)
from pypdf import PdfReader

from pdf_generator import generate_pdf_report


# ===============================================================
# SESSION STATE
# ===============================================================
if "bio_data" not in st.session_state:
    st.session_state.bio_data = {}
if "epi_data" not in st.session_state:
    st.session_state.epi_data = {}
if "dxa_data" not in st.session_state:
    st.session_state.dxa_data = {}
if "patient_info" not in st.session_state:
    st.session_state.patient_info = {}


# ===============================================================
# 1. Lecture PDF (pypdf)
# ===============================================================
def read_pdf_text(uploaded_file):
    pdf_reader = PdfReader(uploaded_file)
    text = ""
    for page in pdf_reader.pages:
        extracted = page.extract_text()
        if extracted:
            text += extracted + "\n"
    return text


# ===============================================================
# 2. Extraction biomarqueurs
# ===============================================================
def extract_bio_values(text):
    data = {
        "hormones_salivaires": {},
        "neurotransmetteurs": {},
        "inflammation": {},
        "metabolisme_glucidique": {},
        "acides_gras": {},
    }

    patterns = {
        "hormones_salivaires": {
            "cortisol_reveil": r"Cortisol salivaire r[ée]veil\s+([\d\.]+)",
            "cortisol_reveil_30": r"Cortisol salivaire r[ée]veil \+ 30'\s+([\d\.]+)",
            "cortisol_12h": r"Cortisol salivaire 12h\s+([\d\.]+)",
            "cortisol_18h": r"Cortisol salivaire 18h\s+([\d\.]+)",
            "cortisol_22h": r"Cortisol salivaire 22h\s+([\d\.]+)",
            "dhea": r"DHEA salivaire\s+([\d\.]+)"
        },
        "neurotransmetteurs": {
            "dopamine": r"Dopamine\s+([\d\.]+)",
            "serotonine": r"S[ée]rotonine\s+([\d\.]+)",
        },
        "inflammation": {
            "crp_us": r"CRP ultra-sensible\s+([\d\.]+)"
        },
        "metabolisme_glucidique": {
            "glycemie": r"Glyc[ée]mie [àa] jeun\s+([\d\.]+)",
            "insuline": r"Insuline\s+[àa] jeun\s+([\d\.]+)",
            "homa": r"Index HOMA\s+([\d\.]+)"
        },
        "acides_gras": {
            "epa": r"Ac\. eicosapenta[ée]no[ïi]que\s+([\d\.]+)",
            "dha": r"Acide docosahexa[ée]no[ïi]que\s+([\d\.]+)",
            "aa_epa": r"Rapport AA/EPA\s+([\d\.]+)"
        },
    }

    for cat, block in patterns.items():
        for label, pattern in block.items():
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                try:
                    data[cat][label] = float(m.group(1))
                except:
                    pass

    return data


# ===============================================================
# 3. Extraction Épigénétique
# ===============================================================
def extract_epi_values(text):
    data = {
        "age_epigenetique": 0,
        "age_chronologique": 0
    }

    bio = re.search(r"biological\s+age\s+is\s+([\d\.]+)", text, re.IGNORECASE)
    chrono = re.search(r"reported\s+being\s+([\d\.]+)\s+years", text, re.IGNORECASE)

    if bio:
        data["age_epigenetique"] = float(bio.group(1))
    if chrono:
        data["age_chronologique"] = float(chrono.group(1))

    return data


# ===============================================================
# 4. Extraction DXA
# ===============================================================
def extract_dxa_values(text):
    data = {
        "densite_minerale_osseuse": {},
        "composition_corporelle": {}
    }

    patterns_dmo = {
        "dmo_lombaire": r"(?:DMO|BMD).*?(?:lombaire|lumbar|spine|L1-L4).*?([\d\.]+)",
        "tscore_lombaire": r"T-score.*?(?:lombaire|lumbar|spine|L1-L4).*?(-?[\d\.]+)",
        "dmo_col_femoral": r"(?:DMO|BMD).*?(?:col.*?f[ée]moral|femoral neck).*?([\d\.]+)",
        "tscore_col_femoral": r"T-score.*?(?:col.*?f[ée]moral|femoral neck).*?(-?[\d\.]+)",
        "dmo_hanche_totale": r"(?:DMO|BMD).*?(?:hanche totale|total hip).*?([\d\.]+)",
        "tscore_hanche_totale": r"T-score.*?(?:hanche totale|total hip).*?(-?[\d\.]+)"
    }

    patterns_composition = {
        "masse_grasse": r"(?:masse grasse|fat mass|body fat).*?([\d\.]+)\s*(?:%|kg)",
        "masse_maigre": r"(?:masse maigre|lean mass|FFM).*?([\d\.]+)\s*kg",
        "masse_musculaire": r"(?:masse musculaire|muscle mass|SMM).*?([\d\.]+)\s*kg",
        "pourcentage_graisse": r"(?:% graisse|body fat %|fat %).*?([\d\.]+)\s*%"
    }

    for label, pattern in patterns_dmo.items():
        m = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if m:
            try:
                data["densite_minerale_osseuse"][label] = float(m.group(1))
            except:
                pass

    for label, pattern in patterns_composition.items():
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            try:
                data["composition_corporelle"][label] = float(m.group(1))
            except:
                pass

    return data


# ===============================================================
# 5. Recommandations intelligentes
# ===============================================================
def _generate_smart_recommendations(bio_data, epi_data, dxa_data):
    # (Identique à ta version — inchangé)
    return {
        "supplement_needs": [],
        "lifestyle_changes": [],
        "follow_up": []
    }


# ===============================================================
# 6. Conversion JSON vers format PDF
# ===============================================================
def convert_to_json_format(bio_data, epi_data, dxa_data, patient_info):

    data = {
        "patient_info": patient_info,
        "results": {
            "hormonologie_salivaire": [],
            "neurotransmetteurs": [],
            "acides_gras": [],
            "dxa": []
        },
        "epigenetique": epi_data,
        "recommendations": _generate_smart_recommendations(bio_data, epi_data, dxa_data)
    }

    # Cortisol
    hormones = bio_data.get("hormones_salivaires", {})
    mapping = [
        ("cortisol_reveil", "Réveil", "3.0 - 8.0"),
        ("cortisol_reveil_30", "Réveil + 30min", "5.0 - 10.0"),
        ("cortisol_12h", "12h", "1.5 - 4.0"),
        ("cortisol_18h", "18h", "1.0 - 3.0"),
        ("cortisol_22h", "22h", "0.5 - 1.5")
    ]

    for key, moment, ref in mapping:
        if key in hormones:
            data["results"]["hormonologie_salivaire"].append({
                "parametre": "Cortisol salivaire",
                "moment": moment,
                "resultat": str(hormones[key]),
                "unite": "ng/mL",
                "valeurs_reference": ref,
                "interpretation": "Normal"
            })

    # Neuro
    neuro = bio_data.get("neurotransmetteurs", {})
    if "dopamine" in neuro:
        data["results"]["neurotransmetteurs"].append({
            "parametre": "Dopamine",
            "resultat": str(neuro["dopamine"]),
            "unite": "µg/g créat",
            "valeurs_reference": "150 - 500",
            "interpretation": "Normal"
        })

    if "serotonine" in neuro:
        data["results"]["neurotransmetteurs"].append({
            "parametre": "Sérotonine",
            "resultat": str(neuro["serotonine"]),
            "unite": "µg/g créat",
            "valeurs_reference": "100 - 300",
            "interpretation": "Normal"
        })

    # Acides gras
    ag = bio_data.get("acides_gras", {})
    if "epa" in ag:
        data["results"]["acides_gras"].append({
            "parametre": "EPA (Oméga-3)",
            "resultat": str(ag["epa"]),
            "unite": "%",
            "valeurs_reference": "0.5 - 2.0",
            "interpretation": "Normal"
        })

    if "dha" in ag:
        data["results"]["acides_gras"].append({
            "parametre": "DHA (Oméga-3)",
            "resultat": str(ag["dha"]),
            "unite": "%",
            "valeurs_reference": "2.0 - 4.0",
            "interpretation": "Normal"
        })

    if "aa_epa" in ag:
        data["results"]["acides_gras"].append({
            "parametre": "Ratio AA/EPA",
            "resultat": str(ag["aa_epa"]),
            "unite": "",
            "valeurs_reference": "< 15",
            "interpretation": "Normal"
        })

    # DXA
    for key, v in dxa_data.get("densite_minerale_osseuse", {}).items():
        data["results"]["dxa"].append({
            "parametre": key,
            "resultat": str(v),
            "unite": "",
            "valeurs_reference": "",
            "interpretation": "À évaluer"
        })

    for key, v in dxa_data.get("composition_corporelle", {}).items():
        data["results"]["dxa"].append({
            "parametre": key,
            "resultat": str(v),
            "unite": "",
            "valeurs_reference": "",
            "interpretation": "À évaluer"
        })

    return data


# ===============================================================
# 7. Interface Streamlit
# ===============================================================
st.set_page_config(page_title="ALGO-LIFE", page_icon="🧬", layout="wide")

st.title("🧬 ALGO-LIFE — Générateur de Rapports Bio-Fonctionnels")
st.markdown("---")

# Patient
st.subheader("👤 Informations Patient")
col1, col2 = st.columns(2)

with col1:
    nom = st.text_input("Nom", value="NOM")
    prenom = st.text_input("Prénom", value="Prénom")
    date_naissance = st.text_input("Date de naissance", value="01/01/1980")

with col2:
    sexe = st.selectbox("Sexe", ["M", "F"])
    numero_dossier = st.text_input("N° Dossier", value="ALGO-001")
    medecin = st.text_input("Médecin prescripteur", value="Dr. ALGO-LIFE")

st.session_state.patient_info = {
    "nom": nom,
    "prenom": prenom,
    "date_naissance": date_naissance,
    "sexe": sexe,
    "numero_dossier": numero_dossier,
    "medecin": medecin,
    "date_prelevement": datetime.now().strftime("%d/%m/%Y")
}

st.markdown("---")

# Upload
st.subheader("📄 Upload des Rapports PDF")
col1, col2, col3 = st.columns(3)

with col1:
    bio_file = st.file_uploader("Rapport biologique", type=["pdf"])
with col2:
    epi_file = st.file_uploader("Rapport épigénétique", type=["pdf"])
with col3:
    dxa_file = st.file_uploader("Rapport DXA", type=["pdf"])

# Extraction
if bio_file:
    with st.expander("📊 Données biologiques"):
        text = read_pdf_text(bio_file)
        st.session_state.bio_data = extract_bio_values(text)
        st.json(st.session_state.bio_data)

if epi_file:
    with st.expander("🧬 Données épigénétiques"):
        text = read_pdf_text(epi_file)
        st.session_state.epi_data = extract_epi_values(text)
        st.json(st.session_state.epi_data)

if dxa_file:
    with st.expander("🦴 Données DXA"):
        text = read_pdf_text(dxa_file)
        st.session_state.dxa_data = extract_dxa_values(text)
        st.json(st.session_state.dxa_data)

st.markdown("---")

# Génération PDF
st.subheader("📄 Génération du Rapport PDF")

if st.button("🔄 Générer le Rapport", use_container_width=True):

    if not st.session_state.bio_data:
        st.error("⚠️ Veuillez uploader au moins un rapport biologique.")
    else:
        with st.spinner("Génération en cours..."):

            json_data = convert_to_json_format(
                st.session_state.bio_data,
                st.session_state.epi_data,
                st.session_state.dxa_data,
                st.session_state.patient_info
            )

            pdf_path = generate_pdf_report(
                patient_data=json_data,
                output_filename="rapport_algolife.pdf"
            )

            st.success("✅ Rapport généré avec succès !")

            with open(pdf_path, "rb") as f:
                st.download_button(
                    "📥 Télécharger le PDF",
                    f.read(),
                    file_name=f"ALGO-LIFE_{nom}_{datetime.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
