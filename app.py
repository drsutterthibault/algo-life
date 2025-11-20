import streamlit as st
import re
import PyPDF2
import tempfile
import json
from datetime import datetime

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
# 1. Extraction texte PDF
# ===============================================================
def read_pdf_text(uploaded_file):
    pdf_reader = PyPDF2.PdfReader(uploaded_file)
    text = ""
    for page in pdf_reader.pages:
        extracted = page.extract_text()
        if extracted:
            text += extracted + "\n"
    return text


# ===============================================================
# 2. Extraction BIOMARQUEURS
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
# 4. Extraction DXA (Densitométrie osseuse)
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
# 5. Génération recommandations intelligentes
# ===============================================================
def _generate_smart_recommendations(bio_data, epi_data, dxa_data):
    """Génère des recommandations personnalisées basées sur les données"""
    
    recommendations = {
        "supplement_needs": [],
        "lifestyle_changes": [],
        "follow_up": []
    }
    
    # Analyse cortisol
    cortisol_data = bio_data.get("hormones_salivaires", {})
    if cortisol_data:
        cortisol_22h = cortisol_data.get("cortisol_22h", 0)
        cortisol_reveil = cortisol_data.get("cortisol_reveil", 0)
        
        if cortisol_22h > 1.5:
            recommendations["supplement_needs"].append({
                "categorie": "Gestion du stress",
                "produit": "Magnésium bisglycinate",
                "dosage": "300-400mg le soir",
                "objectif": "Réduire le cortisol nocturne et améliorer la qualité du sommeil"
            })
            recommendations["lifestyle_changes"].append({
                "domaine": "Sommeil",
                "recommandation": "Rituel du coucher à heure fixe (22h-22h30), éviter les écrans 2h avant, température chambre 18°C",
                "priorite": "Haute"
            })
        
        if cortisol_reveil < 4.0:
            recommendations["supplement_needs"].append({
                "categorie": "Support surrénalien",
                "produit": "Vitamine C liposomale + Vitamines B",
                "dosage": "Vit C: 1000mg matin | B-Complex: 1 gélule",
                "objectif": "Soutenir la fonction surrénalienne et la production de cortisol"
            })
    
    # Analyse acides gras
    ag_data = bio_data.get("acides_gras", {})
    if ag_data:
        epa = ag_data.get("epa", 0)
        dha = ag_data.get("dha", 0)
        ratio_aa_epa = ag_data.get("aa_epa", 0)
        
        if epa < 1.0 or dha < 2.5 or ratio_aa_epa > 10:
            recommendations["supplement_needs"].append({
                "categorie": "Anti-inflammatoire",
                "produit": "Oméga-3 EPA/DHA (huile de poisson purifiée)",
                "dosage": "2000-3000mg/jour (ratio EPA:DHA = 2:1)",
                "objectif": "Réduire l'inflammation systémique, optimiser ratio AA/EPA < 3"
            })
            recommendations["lifestyle_changes"].append({
                "domaine": "Nutrition",
                "recommandation": "Poissons gras sauvages (saumon, maquereau, sardines, anchois) 4x/semaine minimum. Réduire oméga-6 (huiles végétales, viandes industrielles)",
                "priorite": "Haute"
            })
    
    # Analyse inflammation
    inflammation = bio_data.get("inflammation", {})
    if inflammation:
        crp = inflammation.get("crp_us", 0)
        if crp > 2.0:
            recommendations["supplement_needs"].append({
                "categorie": "Anti-inflammatoire",
                "produit": "Curcumine + Pipérine",
                "dosage": "500-1000mg curcumine (95% curcuminoïdes) + 5mg pipérine, 2x/jour",
                "objectif": "Réduire l'inflammation chronique de bas grade"
            })
    
    # Analyse neurotransmetteurs
    neuro_data = bio_data.get("neurotransmetteurs", {})
    if neuro_data:
        dopamine = neuro_data.get("dopamine", 0)
        serotonine = neuro_data.get("serotonine", 0)
        
        if dopamine < 200:
            recommendations["supplement_needs"].append({
                "categorie": "Support neurologique - Dopamine",
                "produit": "L-Tyrosine",
                "dosage": "500-1000mg le matin à jeun",
                "objectif": "Soutenir la synthèse de dopamine (motivation, concentration)"
            })
            recommendations["lifestyle_changes"].append({
                "domaine": "Activité physique",
                "recommandation": "Exercice intense 20-30min le matin (HIIT, musculation) pour stimuler dopamine naturellement",
                "priorite": "Moyenne"
            })
        
        if serotonine < 150:
            recommendations["supplement_needs"].append({
                "categorie": "Support neurologique - Sérotonine",
                "produit": "5-HTP ou L-Tryptophane + Magnésium + B6",
                "dosage": "5-HTP: 50-100mg le soir | ou L-Tryptophane: 500-1000mg",
                "objectif": "Améliorer production sérotonine (humeur, sommeil, satiété)"
            })
            recommendations["lifestyle_changes"].append({
                "domaine": "Lumière naturelle",
                "recommandation": "Exposition lumière naturelle 30min le matin (avant 10h) pour réguler mélatonine/sérotonine",
                "priorite": "Haute"
            })
    
    # Analyse DXA - Densité osseuse
    dmo_data = dxa_data.get("densite_minerale_osseuse", {})
    if dmo_data:
        tscores = [v for k, v in dmo_data.items() if "tscore" in k]
        if tscores:
            tscore_min = min(tscores)
            
            if tscore_min < -2.5:
                recommendations["supplement_needs"].append({
                    "categorie": "Santé osseuse - Ostéoporose",
                    "produit": "Protocole osseux complet",
                    "dosage": "Vit D3: 4000-5000 UI + K2-MK7: 200µg + Calcium citrate: 1000mg + Magnésium: 400mg + Bore: 3mg",
                    "objectif": "Ralentir perte osseuse et stimuler ostéoblastes"
                })
                recommendations["lifestyle_changes"].append({
                    "domaine": "Activité physique - Ostéoporose",
                    "recommandation": "Exercices en charge obligatoires: marche rapide 45min/jour + musculation ciblée 3x/semaine. Éviter exercices à risque de chute",
                    "priorite": "Critique"
                })
            elif tscore_min < -1.0:
                recommendations["supplement_needs"].append({
                    "categorie": "Santé osseuse - Ostéopénie",
                    "produit": "Vitamine D3 + K2 + Calcium + Magnésium",
                    "dosage": "Vit D3: 2000-4000 UI + K2-MK7: 100-200µg + Calcium: 500-800mg + Magnésium: 300-400mg",
                    "objectif": "Prévenir progression vers ostéoporose"
                })
                recommendations["lifestyle_changes"].append({
                    "domaine": "Activité physique - Prévention",
                    "recommandation": "Exercices en charge et résistance 3-4x/semaine: marche, jogging, musculation, sauts modérés",
                    "priorite": "Haute"
                })
    
    # Analyse composition corporelle
    composition = dxa_data.get("composition_corporelle", {})
    if composition:
        masse_grasse_pct = composition.get("pourcentage_graisse", 0)
        masse_musculaire = composition.get("masse_musculaire", 0)
        
        if masse_grasse_pct > 30:  # Pour femmes, ajuster selon sexe
            recommendations["lifestyle_changes"].append({
                "domaine": "Recomposition corporelle",
                "recommandation": "Déficit calorique modéré 300-500 kcal/jour + Apport protéique élevé 1.8-2.2g/kg poids idéal",
                "priorite": "Moyenne"
            })
            recommendations["supplement_needs"].append({
                "categorie": "Métabolisme",
                "produit": "Protéines whey ou végétales + Créatine",
                "dosage": "Protéines: 25-30g post-workout | Créatine: 3-5g/jour",
                "objectif": "Préserver masse musculaire pendant perte de poids"
            })
    
    # Analyse épigénétique
    if epi_data:
        age_epi = epi_data.get("age_epigenetique", 0)
        age_chrono = epi_data.get("age_chronologique", 0)
        
        if age_epi > age_chrono + 5:
            recommendations["lifestyle_changes"].append({
                "domaine": "Longévité - Vieillissement accéléré",
                "recommandation": "Protocole anti-âge intensif: Jeûne intermittent 16:8, restriction calorique 15-20%, exercice 5x/semaine, gestion stress optimale",
                "priorite": "Haute"
            })
            recommendations["supplement_needs"].append({
                "categorie": "Anti-âge",
                "produit": "NAD+ précurseurs + Resvératrol + Quercétine",
                "dosage": "NMN: 250-500mg matin | Resvératrol: 250mg | Quercétine: 500mg",
                "objectif": "Ralentir vieillissement épigénétique, activer sirtuines"
            })
        elif age_epi > age_chrono + 2:
            recommendations["lifestyle_changes"].append({
                "domaine": "Longévité - Prévention",
                "recommandation": "Optimisation hygiène de vie: sommeil 7-8h, activité physique régulière, alimentation méditerranéenne, gestion stress",
                "priorite": "Moyenne"
            })
    
    # Recommandations nutritionnelles générales
    recommendations["lifestyle_changes"].append({
        "domaine": "Nutrition - Base",
        "recommandation": "Alimentation anti-inflammatoire: légumes colorés 5-7 portions/jour, fruits rouges, thé vert, épices (curcuma, gingembre). Éviter sucres raffinés, aliments ultra-transformés",
        "priorite": "Base"
    })
    
    # Hydratation
    recommendations["lifestyle_changes"].append({
        "domaine": "Hydratation",
        "recommandation": "2-2.5L eau pure/jour. Éviter eau du robinet si chlorée (préférer filtrée ou minérale faible résidu)",
        "priorite": "Base"
    })
    
    # Suivi biologique
    recommendations["follow_up"].append({
        "type": "Biologique complet",
        "delai": "3 mois",
        "examens": "Cortisol salivaire 4 points, Profil acides gras érythrocytaires, CRP-us, Bilan thyroïdien (TSH, T3, T4), Vitamine D, Magnésium érythrocytaire"
    })
    
    recommendations["follow_up"].append({
        "type": "Suivi clinique",
        "delai": "1 mois",
        "examens": "Évaluation symptômes, tolérance suppléments, observance recommandations"
    })
    
    if dmo_data and tscores and min(tscores) < -1.0:
        recommendations["follow_up"].append({
            "type": "DXA contrôle",
            "delai": "12 mois",
            "examens": "Densitométrie osseuse complète (rachis + hanches) + Marqueurs du remodelage osseux"
        })
    
    if epi_data and epi_data.get("age_epigenetique", 0) > epi_data.get("age_chronologique", 0) + 3:
        recommendations["follow_up"].append({
            "type": "Épigénétique",
            "delai": "12 mois",
            "examens": "Test âge épigénétique de contrôle pour évaluer efficacité interventions"
        })
    
    return recommendations


# ===============================================================
# 6. Conversion des données extraites vers format JSON attendu
# ===============================================================
def convert_to_json_format(bio_data, epi_data, dxa_data, patient_info):
    """Convertit les données extraites vers le format attendu par pdf_generator"""
    
    data = {
        "patient_info": {
            "nom": patient_info.get("nom", "NOM"),
            "prenom": patient_info.get("prenom", "Prénom"),
            "date_naissance": patient_info.get("date_naissance", "01/01/1980"),
            "sexe": patient_info.get("sexe", "M"),
            "numero_dossier": patient_info.get("numero_dossier", "ALGO-001"),
            "date_prelevement": patient_info.get("date_prelevement", datetime.now().strftime("%d/%m/%Y")),
            "medecin_prescripteur": patient_info.get("medecin", "Dr. ALGO-LIFE")
        },
        "results": {
            "hormonologie_salivaire": [],
            "neurotransmetteurs": [],
            "acides_gras": [],
            "dxa": []
        },
        "epigenetique": epi_data,
        "recommendations": {}
    }
    
    # Conversion hormones salivaires (cortisol)
    hormones = bio_data.get("hormones_salivaires", {})
    
    cortisol_mapping = [
        ("cortisol_reveil", "Réveil", "3.0 - 8.0"),
        ("cortisol_reveil_30", "Réveil + 30min", "5.0 - 10.0"),
        ("cortisol_12h", "12h", "1.5 - 4.0"),
        ("cortisol_18h", "18h", "1.0 - 3.0"),
        ("cortisol_22h", "22h", "0.5 - 1.5")
    ]
    
    for key, moment, ref in cortisol_mapping:
        if key in hormones:
            data["results"]["hormonologie_salivaire"].append({
                "parametre": "Cortisol salivaire",
                "moment": moment,
                "resultat": str(hormones[key]),
                "unite": "ng/mL",
                "valeurs_reference": ref,
                "interpretation": "Normal"
            })
    
    if "dhea" in hormones:
        data["results"]["hormonologie_salivaire"].append({
            "parametre": "DHEA salivaire",
            "moment": "Matin",
            "resultat": str(hormones["dhea"]),
            "unite": "pg/mL",
            "valeurs_reference": "50 - 250",
            "interpretation": "Normal"
        })
    
    # Conversion neurotransmetteurs
    neuro = bio_data.get("neurotransmetteurs", {})
    
    neuro_mapping = [
        ("dopamine", "Dopamine", "µg/g créat", "150 - 500"),
        ("serotonine", "Sérotonine", "µg/g créat", "100 - 300")
    ]
    
    for key, param, unite, ref in neuro_mapping:
        if key in neuro:
            data["results"]["neurotransmetteurs"].append({
                "parametre": param,
                "resultat": str(neuro[key]),
                "unite": unite,
                "valeurs_reference": ref,
                "interpretation": "Normal"
            })
    
    # Conversion acides gras
    ag = bio_data.get("acides_gras", {})
    
    ag_mapping = [
        ("epa", "EPA (Oméga-3)", "%", "0.5 - 2.0"),
        ("dha", "DHA (Oméga-3)", "%", "2.0 - 4.0"),
        ("aa_epa", "Ratio AA/EPA", "", "< 15")
    ]
    
    for key, param, unite, ref in ag_mapping:
        if key in ag:
            data["results"]["acides_gras"].append({
                "parametre": param,
                "resultat": str(ag[key]),
                "unite": unite,
                "valeurs_reference": ref,
                "interpretation": "Normal"
            })
    
    # Conversion DXA
    dmo = dxa_data.get("densite_minerale_osseuse", {})
    composition = dxa_data.get("composition_corporelle", {})
    
    if dmo:
        for key, value in dmo.items():
            if "tscore" in key:
                site = key.replace("tscore_", "").replace("_", " ").title()
                interpretation = "Normal" if value > -1.0 else ("Ostéopénie" if value > -2.5 else "Ostéoporose")
                data["results"]["dxa"].append({
                    "parametre": f"T-Score {site}",
                    "resultat": str(value),
                    "unite": "SD",
                    "valeurs_reference": "> -1.0 (Normal) | -1.0 à -2.5 (Ostéopénie) | < -2.5 (Ostéoporose)",
                    "interpretation": interpretation
                })
    
    if composition:
        comp_mapping = {
            "masse_grasse": ("Masse Grasse", "kg", "Variable"),
            "masse_maigre": ("Masse Maigre", "kg", "Variable"),
            "masse_musculaire": ("Masse Musculaire", "kg", "Variable"),
            "pourcentage_graisse": ("% Masse Grasse", "%", "H: 10-20% | F: 20-30%")
        }
        
        for key, value in composition.items():
            if key in comp_mapping:
                param, unite, ref = comp_mapping[key]
                data["results"]["dxa"].append({
                    "parametre": param,
                    "resultat": str(value),
                    "unite": unite,
                    "valeurs_reference": ref,
                    "interpretation": "À évaluer"
                })
    
    # Génération des recommandations intelligentes
    data["recommendations"] = _generate_smart_recommendations(bio_data, epi_data, dxa_data)
    
    return data


# ===============================================================
# 7. Interface Streamlit
# ===============================================================
st.set_page_config(page_title="ALGO-LIFE", page_icon="🧬", layout="wide")

st.title("🧬 ALGO-LIFE — Générateur de Rapports Bio-Fonctionnels")
st.markdown("---")

# Informations patient
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

# Upload des fichiers
st.subheader("📄 Upload des Rapports")
col1, col2, col3 = st.columns(3)

with col1:
    bio_file = st.file_uploader("Rapport biologique (PDF)", type=["pdf"], key="bio")
    
with col2:
    epi_file = st.file_uploader("Rapport épigénétique (PDF)", type=["pdf"], key="epi")

with col3:
    dxa_file = st.file_uploader("Rapport DXA (PDF)", type=["pdf"], key="dxa")

# Lecture et extraction
if bio_file:
    with st.expander("📊 Aperçu des données biologiques"):
        text = read_pdf_text(bio_file)
        st.session_state.bio_data = extract_bio_values(text)
        st.json(st.session_state.bio_data)

if epi_file:
    with st.expander("🧬 Aperçu des données épigénétiques"):
        text = read_pdf_text(epi_file)
        st.session_state.epi_data = extract_epi_values(text)
        st.json(st.session_state.epi_data)

if dxa_file:
    with st.expander("🦴 Aperçu des données DXA"):
        text = read_pdf_text(dxa_file)
        st.session_state.dxa_data = extract_dxa_values(text)
        st.json(st.session_state.dxa_data)

st.markdown("---")

# Génération PDF
st.subheader("📄 Génération du Rapport")

if st.button("🔄 Générer le Rapport PDF", type="primary", use_container_width=True):
    
    if not st.session_state.bio_data:
        st.error("⚠️ Veuillez d'abord uploader un rapport biologique.")
    else:
        with st.spinner("Génération du rapport en cours..."):
            
            # Conversion vers format JSON attendu
            json_data = convert_to_json_format(
                st.session_state.bio_data,
                st.session_state.epi_data,
                st.session_state.dxa_data,
                st.session_state.patient_info
            )
            
            # Sauvegarde temporaire du JSON
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as tmp_json:
                json.dump(json_data, tmp_json, ensure_ascii=False, indent=2)
                json_path = tmp_json.name
            
            try:
                # Génération du PDF
                pdf_path = generate_pdf_report(
                    patient_data=json_data,
                    output_filename="rapport_algolife.pdf"
                )
                
                st.success("✅ PDF généré avec succès!")
                
                # Téléchargement
                with open(pdf_path, "rb") as f:
                    st.download_button(
                        label="📥 Télécharger le Rapport PDF",
                        data=f.read(),
                        file_name=f"ALGO-LIFE_{nom}_{datetime.now().strftime('%Y%m%d')}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                
            except Exception as e:
                st.error(f"❌ Erreur lors de la génération: {str(e)}")
                st.exception(e)
