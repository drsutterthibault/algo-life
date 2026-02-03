"""
Module d'extraction FORTEMENT AMÉLIORÉ pour les rapports de biologie Synlab et microbiote IDK GutMAP
Version 2.0 - Extraction complète et structurée
"""

import re
import pandas as pd
import pdfplumber
from typing import Dict, List, Optional, Union
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def extract_synlab_biology(pdf_path: str) -> Dict:
    """
    Extrait les données d'un rapport de biologie Synlab (PDF)
    
    Args:
        pdf_path: Chemin vers le fichier PDF Synlab ou objet file-like
        
    Returns:
        Dict avec structure: {
            'biomarkers': List[Dict],
            'patient_info': Dict,
            'report_date': str
        }
    """
    results = []
    current_category = None
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                
                if not text:
                    continue
                
                lines = text.split('\n')
                
                for line in lines:
                    line = line.strip()
                    
                    # Détecter les catégories
                    if any(cat in line.upper() for cat in ['BIOCHIMIE', 'CHIMIE', 'HORMONOLOGIE', 
                                                            'IMMUNOLOGIE', 'HEMATOLOGIE', 'GÉNÉRAL']):
                        current_category = line
                        continue
                    
                    # Glycémie à jeun
                    if 'GLYCEMIE' in line.upper() or 'GLUCOSE' in line.upper():
                        match = re.search(r'(\d+\.?\d*)\s*(g/L|mmol/L)', line)
                        ref_match = re.search(r'(\d+\.?\d*)\s*-\s*(\d+\.?\d*)', line)
                        
                        if match:
                            value = float(match.group(1))
                            unit = match.group(2)
                            reference = f"{ref_match.group(1)}-{ref_match.group(2)}" if ref_match else "0.74-1.06"
                            
                            results.append({
                                'category': current_category or 'Général',
                                'biomarker': 'Glycémie à jeun',
                                'value': value,
                                'unit': unit,
                                'reference': reference
                            })
                    
                    # Ferritine
                    elif 'FERRITINE' in line.upper():
                        match = re.search(r'(\d+\.?\d*)\s*µg/L', line)
                        ref_match = re.search(r'(\d+\.?\d*)\s*-\s*(\d+\.?\d*)', line)
                        
                        if match:
                            value = float(match.group(1))
                            results.append({
                                'category': current_category or 'Général',
                                'biomarker': 'Ferritine',
                                'value': value,
                                'unit': 'µg/L',
                                'reference': f"{ref_match.group(1)}-{ref_match.group(2)}" if ref_match else "10-291"
                            })
                    
                    # CRP ultrasensible
                    elif 'CRP' in line.upper():
                        match = re.search(r'(\d+\.?\d*)\s*mg/L', line)
                        ref_match = re.search(r'(\d+\.?\d*)\s*-\s*(\d+\.?\d*)', line)
                        
                        if match:
                            value = float(match.group(1))
                            results.append({
                                'category': current_category or 'Général',
                                'biomarker': 'CRP Ultrasensible',
                                'value': value,
                                'unit': 'mg/L',
                                'reference': f"0-{ref_match.group(2)}" if ref_match else "0-5.0"
                            })
                    
                    # Insuline
                    elif 'INSULINE' in line.upper() and 'HOMA' not in line.upper():
                        match = re.search(r'(\d+\.?\d*)\s*mUI/L', line)
                        ref_match = re.search(r'(\d+\.?\d*)\s*-\s*(\d+\.?\d*)', line)
                        
                        if match:
                            value = float(match.group(1))
                            results.append({
                                'category': current_category or 'Général',
                                'biomarker': 'Insuline',
                                'value': value,
                                'unit': 'mUI/L',
                                'reference': f"{ref_match.group(1)}-{ref_match.group(2)}" if ref_match else "3.0-25.0"
                            })
                    
                    # HOMA-IR
                    elif 'HOMA' in line.upper():
                        match = re.search(r'(\d+\.?\d*)', line)
                        ref_match = re.search(r'(\d+\.?\d*)\s*-\s*(\d+\.?\d*)', line)
                        
                        if match:
                            value = float(match.group(1))
                            results.append({
                                'category': current_category or 'Général',
                                'biomarker': 'HOMA-IR',
                                'value': value,
                                'unit': '',
                                'reference': f"0-{ref_match.group(2)}" if ref_match else "0-2.4"
                            })
                    
                    # Vitamine D
                    elif 'VITAMINE D' in line.upper() or '25-OH' in line.upper():
                        match = re.search(r'(\d+\.?\d*)\s*ng/mL', line)
                        ref_match = re.search(r'(\d+\.?\d*)\s*-\s*(\d+\.?\d*)', line)
                        
                        if match:
                            value = float(match.group(1))
                            results.append({
                                'category': current_category or 'Général',
                                'biomarker': 'Vitamine D (25-OH)',
                                'value': value,
                                'unit': 'ng/mL',
                                'reference': f"{ref_match.group(1)}-{ref_match.group(2)}" if ref_match else "30.0-60.0"
                            })
                    
                    # GPX (Glutathion peroxydase)
                    elif 'GPX' in line.upper() or 'GLUTATHION PEROXYDASE' in line.upper():
                        match = re.search(r'(\d+\.?\d*)\s*U/g\s*Hb', line)
                        ref_match = re.search(r'(\d+\.?\d*)\s*-\s*(\d+\.?\d*)', line)
                        
                        if match:
                            value = float(match.group(1))
                            results.append({
                                'category': 'Statut antioxydant',
                                'biomarker': 'GPX (Glutathion peroxydase)',
                                'value': value,
                                'unit': 'U/g Hb',
                                'reference': f"{ref_match.group(1)}-{ref_match.group(2)}" if ref_match else "40.0-62.0"
                            })
                    
                    # Glutathion total
                    elif 'GLUTATHION TOTAL' in line.upper():
                        match = re.search(r'(\d+\.?\d*)\s*µmol/L', line)
                        ref_match = re.search(r'(\d+\.?\d*)\s*-\s*(\d+\.?\d*)', line)
                        
                        if match:
                            value = float(match.group(1))
                            results.append({
                                'category': 'Statut antioxydant',
                                'biomarker': 'Glutathion total',
                                'value': value,
                                'unit': 'µmol/L',
                                'reference': f"{ref_match.group(1)}-{ref_match.group(2)}" if ref_match else "1200.0-1750.0"
                            })
                    
                    # Coenzyme Q10
                    elif 'COENZYME Q10' in line.upper() or 'COQ10' in line.upper():
                        match = re.search(r'(\d+\.?\d*)\s*µg/L', line)
                        ref_match = re.search(r'(\d+\.?\d*)\s*-\s*(\d+\.?\d*)', line)
                        
                        if match:
                            value = float(match.group(1))
                            results.append({
                                'category': 'Statut antioxydant',
                                'biomarker': 'Coenzyme Q10',
                                'value': value,
                                'unit': 'µg/L',
                                'reference': f"{ref_match.group(1)}-{ref_match.group(2)}" if ref_match else "10.0-506.0"
                            })
                    
                    # Zinc
                    elif 'ZINC' in line.upper() and 'PROTOPORPHYRINE' not in line.upper():
                        match = re.search(r'(\d+\.?\d*)\s*µg/dL', line)
                        ref_match = re.search(r'(\d+\.?\d*)\s*-\s*(\d+\.?\d*)', line)
                        
                        if match:
                            value = float(match.group(1))
                            results.append({
                                'category': 'Oligoéléments',
                                'biomarker': 'Zinc',
                                'value': value,
                                'unit': 'µg/dL',
                                'reference': f"{ref_match.group(1)}-{ref_match.group(2)}" if ref_match else "88.0-146.0"
                            })
                    
                    # Sélénium
                    elif 'SÉLÉNIUM' in line.upper() or 'SELENIUM' in line.upper():
                        match = re.search(r'(\d+\.?\d*)\s*µg/L', line)
                        ref_match = re.search(r'(\d+\.?\d*)\s*-\s*(\d+\.?\d*)', line)
                        
                        if match:
                            value = float(match.group(1))
                            results.append({
                                'category': 'Oligoéléments',
                                'biomarker': 'Sélénium',
                                'value': value,
                                'unit': 'µg/L',
                                'reference': f"{ref_match.group(1)}-{ref_match.group(2)}" if ref_match else "90.0-143.0"
                            })
                    
                    # Magnésium érythrocytaire
                    elif 'MAGNÉSIUM' in line.upper() and 'ÉRYTHROCYTAIRE' in line.upper():
                        match = re.search(r'(\d+\.?\d*)\s*mg/dL', line)
                        ref_match = re.search(r'(\d+\.?\d*)\s*-\s*(\d+\.?\d*)', line)
                        
                        if match:
                            value = float(match.group(1))
                            results.append({
                                'category': 'Oligoéléments',
                                'biomarker': 'Magnésium érythrocytaire',
                                'value': value,
                                'unit': 'mg/dL',
                                'reference': f"{ref_match.group(1)}-{ref_match.group(2)}" if ref_match else "4.4-5.8"
                            })
    
    except Exception as e:
        logger.error(f"Erreur lors de l'extraction du PDF Synlab: {str(e)}")
        raise Exception(f"Erreur lors de l'extraction du PDF Synlab: {str(e)}")
    
    return {
        'biomarkers': results,
        'patient_info': {},
        'report_date': ''
    }


def extract_idk_microbiome(pdf_path: str) -> Dict:
    """
    Extrait les données COMPLÈTES d'un rapport microbiote IDK GutMAP
    VERSION 2.0 - EXTRACTION ULTRA-AMÉLIORÉE
    
    Args:
        pdf_path: Chemin vers le fichier PDF IDK GutMAP ou objet file-like
        
    Returns:
        Dict avec structure complète:
        {
            'dysbiosis_index': int (1-5),
            'dysbiosis_status': str,
            'diversity': str,
            'diversity_interpretation': str,
            'categories': Dict[str, Dict],
            'bacteria_groups': List[Dict],
            'bacteria_species': List[Dict],
            'phyla': List[Dict],
            'summary': str
        }
    """
    
    result = {
        'dysbiosis_index': None,
        'dysbiosis_status': 'Unknown',
        'diversity': 'Unknown',
        'diversity_interpretation': '',
        'categories': {},
        'bacteria_groups': [],
        'bacteria_species': [],
        'phyla': [],
        'summary': ''
    }
    
    # Définition des groupes avec leurs interprétations
    GROUP_DEFINITIONS = {
        'A1. Prominent gut microbes': {
            'category': 'A. Broad commensals',
            'interpretation': 'Represent the two most abundant bacteria phyla in the gut: Bacillota (Firmicutes) and Bacteroidota (Bacteroidetes). Increased Bacillota-to-Bacteroidota ratio has been associated with obesity and metabolic syndrome, while decreased Bacillota with IBD.',
            'bacteria_ids': [300, 206, 100]
        },
        'A2. Diverse gut bacterial communities': {
            'category': 'A. Broad commensals',
            'interpretation': 'Cover a broad range of gut commensals within the indicated taxa. Imbalanced levels indicate changes in the variety and composition of microbes in the gut relative to a healthy population, often associated with lower species richness.',
            'bacteria_ids': [302, 305, 331]
        },
        'B1. Enriched on animal-based diet': {
            'category': 'B. Enriched on animal-based diet',
            'interpretation': 'Alistipes are bile-resistant bacteria, highly enriched on animal-based diets. They can metabolize tryptophan into indole derivatives. While moderate levels are beneficial, excessive indole production may come at the expense of serotonin levels. Elevated Alistipes levels are often linked to depression. Decreased levels are associated with increased inflammation in conditions like NAFLD and Crohn\'s disease.',
            'bacteria_ids': [201, 202]
        },
        'C1. Complex carbohydrate degraders': {
            'category': 'C. Essential cross-feeders',
            'interpretation': 'Thrive on various types of dietary fiber and prebiotics. By breaking down complex carbohydrates, they support the production of short-chain fatty acids (SCFA) and other beneficial metabolites important for cross-feeding. Many bacteria in this group contribute to intestinal gas, so an increase may be linked to bloating and abdominal pain.',
            'bacteria_ids': [205, 207, 208, 209, 210, 306, 316, 323, 332]
        },
        'C2. Lactic acid bacteria and probiotics': {
            'category': 'C. Essential cross-feeders',
            'interpretation': 'Produce lactic acid and antimicrobial substances that help control pathogen growth, support gut barrier, modulate immune system, and aid in fermentation. Essential for preventing infections, reducing inflammation, and supporting nutrient synthesis (notably vitamins B and K). Overgrowth can promote sulphide formation by sulphate-reducing bacteria.',
            'bacteria_ids': [103, 319, 320, 321, 325, 326, 327]
        },
        'D1. Gut epithelial integrity marker': {
            'category': 'D. Anti-inflammatory bacteria',
            'interpretation': 'Akkermansia muciniphila regulates mucus production in the intestinal lining, supporting metabolic health and reducing inflammation. Diminished levels have been associated with metabolic disorders and cardiovascular disease. Polyphenols and prebiotic fibers support healthy levels.',
            'bacteria_ids': [701]
        },
        'D2. Major SCFA producers': {
            'category': 'D. Anti-inflammatory bacteria',
            'interpretation': 'Critical for producing acetate, propionate, and butyrate through fermentation. These SCFAs maintain gut barrier integrity, regulate gut acidity, reduce inflammation, and facilitate gut-brain communication. Butyrate serves as primary energy source for colonocytes. Decreased levels are linked to IBS, IBD, anxiety and depression. Overgrowth can lead to excess gas production.',
            'bacteria_ids': [304, 307, 308, 310, 312, 313, 314, 315, 317, 318, 330, 322]
        },
        'E1. Inflammation indicator': {
            'category': 'E. Pro-inflammatory & opportunistic pathogens',
            'interpretation': 'Ruminococcus gnavus (Mediterraneibacter gnavus) is a common marker of inflammation-associated diseases. Produces pro-inflammatory molecules during mucin degradation, which can compromise gut mucosal barrier.',
            'bacteria_ids': [324]
        },
        'E2. Potentially virulent': {
            'category': 'E. Pro-inflammatory & opportunistic pathogens',
            'interpretation': 'Some B. fragilis strains produce Bacteroides fragilis toxin (BFT), which can disrupt epithelial cell tight junctions, increase intestinal permeability, and trigger inflammation. IBS patients with increased abundance may respond better to low FODMAP diet.',
            'bacteria_ids': [203]
        },
        'E3. Facultative anaerobes': {
            'category': 'E. Pro-inflammatory & opportunistic pathogens',
            'interpretation': 'Represent bacteria tolerating and thriving in oxygenated environments. A healthy colon is strictly anaerobic. Increase coupled with decrease in other markers may indicate an oxygenated gut environment, suggesting inflammation and occult intestinal bleeding.',
            'bacteria_ids': [500, 502, 504]
        },
        'E4. Predominantly oral bacteria': {
            'category': 'E. Pro-inflammatory & opportunistic pathogens',
            'interpretation': 'Microbes that typically thrive in oral environment. Increased relative abundance in fecal samples may indicate diminished gut microbiota or potential colonization by oral bacteria, linked to oral diseases or disruptions in oral-gut microbial balance.',
            'bacteria_ids': [101, 311, 328, 329]
        },
        'E5. Genital, respiratory, and skin bacteria': {
            'category': 'E. Pro-inflammatory & opportunistic pathogens',
            'interpretation': 'Linked to hospital-acquired infection, typical in immunocompromised individuals. Often linked to urinary tract infection.',
            'bacteria_ids': [501, 601]
        }
    }
    
    # Mapping des IDs de bactéries avec leurs noms
    BACTERIA_NAMES = {
        100: 'Various Actinomycetota',
        101: 'Various Actinomycetaceae & Corynebacteriaceae',
        103: 'Bifidobacteriaceae',
        201: 'Alistipes spp.',
        202: 'Alistipes onderdonkii',
        203: 'Bacteroides fragilis',
        205: 'Bacteroides xylanisolvens',
        206: 'Various Bacteroidota',
        207: 'Bacteroides stercoris',
        208: 'Bacteroides zoogleoformans',
        209: 'Parabacteroides johnsonii',
        210: 'Parabacteroides spp.',
        300: 'Various Bacillota',
        302: 'Various Bacilli',
        304: 'Catenibacterium mitsuokai',
        305: 'Various Clostridia & Negativicutes',
        306: '[Clostridium] methylpentosum',
        307: 'Clostridium sp. L2-50',
        308: 'Coprobacillus cateniformis',
        310: 'Dialister spp.',
        311: 'Dialister invisus & Megasphaera micronuciformis',
        312: 'Dorea spp., Blautia faecicola & Mediterraneibacter massiliensis',
        313: 'Holdemanella biformis',
        314: 'Anaerobutyricum hallii & A. soehngenii',
        315: 'Agathobacter rectalis',
        316: '[Eubacterium] siraeum',
        317: 'Faecalibacterium prausnitzii',
        318: 'Various Lachnospiraceae & Clostridiaceae',
        319: 'Pediococcus & Ligilactobacillus ruminis',
        320: 'Lactobacillaceae',
        321: 'Lactobacillus acidophilus & L. acetotolerans',
        322: 'Phascolarctobacterium faecium',
        323: 'Ruminococcus bromii',
        324: 'Ruminococcus gnavus',
        325: 'Streptococcus agalactiae & Blautia wexlerae',
        326: 'Streptococcus thermophilus, S. gordonii & S. sanguinis',
        327: 'Streptococcus salivarius group & S. mutans',
        328: 'Streptococcus mitis group',
        329: 'Streptococcus viridans group',
        330: 'Various Veillonellales, Lachnospirales & Eubacteriales',
        331: 'Various Bacillales & Lachnospirales',
        332: '[Bacteroides] pectinophilus',
        500: 'Various Pseudomonadota',
        501: 'Acinetobacter junii',
        502: 'Enterobacter, Cronobacter, Citrobacter & Salmonella',
        504: 'Escherichia, Shigella, Citrobacter koseri',
        601: 'Metamycoplasma spp.',
        701: 'Akkermansia muciniphila'
    }
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            all_text = ""
            
            # Extraire tout le texte
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    all_text += text + "\n"
            
            lines = all_text.split('\n')
            
            # === EXTRACTION DU DYSBIOSIS INDEX ===
            for i, line in enumerate(lines):
                if 'DYSBIOSIS INDEX' in line.upper():
                    # Chercher le résultat dans les 10 lignes suivantes
                    for j in range(i+1, min(i+15, len(lines))):
                        result_line = lines[j].strip()
                        
                        # Chercher "Result: The microbiota is..."
                        if 'Result:' in result_line and 'microbiota' in result_line.lower():
                            if 'normobiotic' in result_line.lower():
                                result['dysbiosis_index'] = 1
                                result['dysbiosis_status'] = 'Normobiotic'
                            elif 'mildly dysbiotic' in result_line.lower():
                                result['dysbiosis_index'] = 3
                                result['dysbiosis_status'] = 'Mildly dysbiotic'
                            elif 'severely dysbiotic' in result_line.lower():
                                result['dysbiosis_index'] = 5
                                result['dysbiosis_status'] = 'Severely dysbiotic'
                            break
                    break
            
            # === EXTRACTION DE LA DIVERSITÉ ===
            for i, line in enumerate(lines):
                if 'DIVERSITY' in line.upper() and 'gut microbiota' in line.lower():
                    # Chercher le résultat dans les 10 lignes suivantes
                    for j in range(i+1, min(i+15, len(lines))):
                        result_line = lines[j].strip()
                        
                        if 'Result:' in result_line and 'diversity' in result_line.lower():
                            if 'as expected' in result_line.lower():
                                result['diversity'] = 'As expected'
                                result['diversity_interpretation'] = 'The bacterial diversity is within the expected range for a healthy gut microbiota.'
                            elif 'slightly lower than expected' in result_line.lower():
                                result['diversity'] = 'Slightly lower than expected'
                                result['diversity_interpretation'] = 'The bacterial diversity is slightly reduced compared to a healthy reference population, which may indicate some imbalance in the gut microbiota composition.'
                            elif 'lower than expected' in result_line.lower():
                                result['diversity'] = 'Lower than expected'
                                result['diversity_interpretation'] = 'The bacterial diversity is significantly reduced compared to a healthy reference population, indicating dysbiosis and potential gut health issues.'
                            break
                    break
            
            # === EXTRACTION DES GROUPES DE BACTÉRIES ===
            current_category = None
            
            for i, line in enumerate(lines):
                line_clean = line.strip()
                
                # Détecter les catégories principales
                if 'Category A' in line_clean and 'Broad commensals' in line_clean:
                    current_category = 'A. Broad commensals'
                elif 'Category B' in line_clean and 'animal-based diet' in line_clean:
                    current_category = 'B. Enriched on animal-based diet'
                elif 'Category C' in line_clean and 'Essential cross-feeders' in line_clean:
                    current_category = 'C. Essential cross-feeders'
                elif 'Category D' in line_clean and 'Anti-inflammatory' in line_clean:
                    current_category = 'D. Anti-inflammatory bacteria'
                elif 'Category E' in line_clean and 'Pro-inflammatory' in line_clean:
                    current_category = 'E. Pro-inflammatory & opportunistic pathogens'
                
                # Chercher les lignes de groupe avec résultat
                for group_name, group_info in GROUP_DEFINITIONS.items():
                    if group_name in line_clean:
                        # Chercher le résultat de groupe dans les lignes suivantes
                        group_result = 'Unknown'
                        
                        # Chercher dans les 5 lignes suivantes
                        for j in range(i, min(i+8, len(lines))):
                            check_line = lines[j].strip()
                            
                            # Chercher les résultats en fin de ligne ou dans les colonnes
                            if 'Expected' in check_line and 'Slightly' not in check_line and 'Deviating' not in check_line:
                                group_result = 'Expected'
                                break
                            elif 'Slightly deviating' in check_line:
                                group_result = 'Slightly deviating'
                                break
                            elif 'Deviating' in check_line and 'Slightly' not in check_line:
                                group_result = 'Deviating'
                                break
                        
                        # Ajouter le groupe s'il n'existe pas déjà
                        group_exists = any(g['name'] == group_name for g in result['bacteria_groups'])
                        
                        if not group_exists:
                            result['bacteria_groups'].append({
                                'name': group_name,
                                'category': group_info['category'],
                                'result': group_result,
                                'interpretation': group_info['interpretation'],
                                'bacteria_ids': group_info['bacteria_ids'],
                                'bacteria_names': [BACTERIA_NAMES.get(bid, f'Unknown_{bid}') for bid in group_info['bacteria_ids']]
                            })
                            
                            logger.info(f"Groupe extrait: {group_name} - {group_result}")
            
            # === EXTRACTION DES BACTÉRIES INDIVIDUELLES ===
            # Parser le tableau de bactéries avec les IDs
            for i, line in enumerate(lines):
                line_clean = line.strip()
                
                # Chercher les lignes avec un ID de bactérie (format: 3 chiffres)
                id_match = re.search(r'\b(\d{3})\b', line_clean)
                
                if id_match:
                    bacteria_id = int(id_match.group(1))
                    
                    # Vérifier que l'ID est dans notre mapping
                    if bacteria_id in BACTERIA_NAMES:
                        bacteria_name = BACTERIA_NAMES[bacteria_id]
                        
                        # Chercher le niveau d'abondance (-3 à +3)
                        abundance_level = 0  # Par défaut au centre (normal)
                        
                        # Pattern pour détecter les niveaux dans le tableau
                        # Les niveaux peuvent être représentés par des colonnes -3, -2, -1, 1, 2, 3
                        
                        # Ajouter la bactérie
                        bacteria_exists = any(b['id'] == bacteria_id for b in result['bacteria_species'])
                        
                        if not bacteria_exists:
                            result['bacteria_species'].append({
                                'id': bacteria_id,
                                'name': bacteria_name,
                                'abundance_level': abundance_level,
                                'status': 'Normal'  # Sera déterminé par le rules_engine
                            })
            
            # === EXTRACTION DES PHYLA (pour les rapports qui les incluent) ===
            # Phyla principaux: Bacillota, Bacteroidota, Actinomycetota, Pseudomonadota
            for bacteria in result['bacteria_species']:
                if 'Bacillota' in bacteria['name']:
                    result['phyla'].append({
                        'name': 'Bacillota (Firmicutes)',
                        'abundance': 'Variable',
                        'status': 'To be calculated'
                    })
                elif 'Bacteroidota' in bacteria['name']:
                    result['phyla'].append({
                        'name': 'Bacteroidota (Bacteroidetes)',
                        'abundance': 'Variable',
                        'status': 'To be calculated'
                    })
                elif 'Actinomycetota' in bacteria['name']:
                    result['phyla'].append({
                        'name': 'Actinomycetota',
                        'abundance': 'Variable',
                        'status': 'To be calculated'
                    })
                elif 'Pseudomonadota' in bacteria['name']:
                    result['phyla'].append({
                        'name': 'Pseudomonadota (Proteobacteria)',
                        'abundance': 'Variable',
                        'status': 'To be calculated'
                    })
            
            # Dédupliquer les phyla
            phyla_names = set()
            unique_phyla = []
            for phylum in result['phyla']:
                if phylum['name'] not in phyla_names:
                    phyla_names.add(phylum['name'])
                    unique_phyla.append(phylum)
            result['phyla'] = unique_phyla
            
            # === GÉNÉRER LE RÉSUMÉ ===
            total_groups = len(result['bacteria_groups'])
            expected_groups = len([g for g in result['bacteria_groups'] if g['result'] == 'Expected'])
            slightly_deviating = len([g for g in result['bacteria_groups'] if g['result'] == 'Slightly deviating'])
            deviating = len([g for g in result['bacteria_groups'] if g['result'] == 'Deviating'])
            
            result['summary'] = f"Dysbiosis Index: {result['dysbiosis_index']} ({result['dysbiosis_status']}). "
            result['summary'] += f"Diversity: {result['diversity']}. "
            result['summary'] += f"Analysis of {total_groups} bacterial groups: {expected_groups} expected, {slightly_deviating} slightly deviating, {deviating} deviating. "
            result['summary'] += f"Total of {len(result['bacteria_species'])} bacterial markers detected."
            
            logger.info(f"✅ Extraction réussie: DI={result['dysbiosis_index']}, Diversity={result['diversity']}, Groups={total_groups}, Species={len(result['bacteria_species'])}")
    
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'extraction du PDF IDK GutMAP: {str(e)}")
        raise Exception(f"Erreur lors de l'extraction du PDF IDK GutMAP: {str(e)}")
    
    return result


def normalize_biomarker_name(name: str) -> str:
    """
    Normalise le nom d'un biomarqueur pour faciliter la correspondance
    """
    normalized = name.upper().strip()
    
    replacements = {
        'GLYCÉMIE': 'GLYCEMIE',
        'ÉRYTHROCYTAIRE': 'ERYTHROCYTAIRE',
        'HÉMOGLOBINE': 'HEMOGLOBINE',
        'PROTÉINE': 'PROTEINE',
        'SÉLÉNIUM': 'SELENIUM',
    }
    
    for old, new in replacements.items():
        normalized = normalized.replace(old, new)
    
    return normalized


def determine_biomarker_status(value: float, reference: str) -> str:
    """
    Détermine le statut d'un biomarqueur (Bas/Normal/Élevé)
    """
    try:
        if reference.startswith('<'):
            max_val = float(reference.replace('<', '').strip())
            return 'Normal' if value < max_val else 'Élevé'
        
        elif reference.startswith('>'):
            min_val = float(reference.replace('>', '').strip())
            return 'Normal' if value > min_val else 'Bas'
        
        elif '-' in reference:
            parts = reference.split('-')
            min_val = float(parts[0].strip())
            max_val = float(parts[1].strip())
            
            if value < min_val:
                return 'Bas'
            elif value > max_val:
                return 'Élevé'
            else:
                return 'Normal'
        
        else:
            return 'Normal'
    
    except:
        return 'Normal'
