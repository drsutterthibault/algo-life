"""
Module d'extraction pour les rapports de biologie Synlab et microbiote IDK GutMAP
"""

import re
import pandas as pd
import pdfplumber
from typing import Dict, List, Optional, Union

def extract_synlab_biology(pdf_path: str) -> pd.DataFrame:
    """
    Extrait les données d'un rapport de biologie Synlab (PDF)
    
    Args:
        pdf_path: Chemin vers le fichier PDF Synlab
        
    Returns:
        DataFrame avec les colonnes: Biomarqueur, Valeur, Unité, Référence, Catégorie
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
                                                            'IMMUNOLOGIE', 'HEMATOLOGIE']):
                        current_category = line
                        continue
                    
                    # Pattern pour les biomarqueurs avec valeur
                    # Format: BIOMARQUEUR    valeur  unité   (ref_min à ref_max)  [valeur_precedente]
                    
                    # Glycémie à jeun
                    if 'GLYCEMIE' in line.upper() or 'GLUCOSE' in line.upper():
                        match = re.search(r'(\d+\.?\d*)\s*(g/L|mmol/L)', line)
                        ref_match = re.search(r'\((\d+\.?\d*)\s*à\s*(\d+\.?\d*)\)', line)
                        
                        if match:
                            value = float(match.group(1))
                            unit = match.group(2)
                            reference = f"{ref_match.group(1)}-{ref_match.group(2)}" if ref_match else "N/A"
                            
                            results.append({
                                'Catégorie': current_category or 'Biochimie',
                                'Biomarqueur': 'Glycémie à jeun',
                                'Valeur': value,
                                'Unité': unit,
                                'Référence': reference
                            })
                    
                    # Ferritine
                    elif 'FERRITINE' in line.upper():
                        match = re.search(r'(\d+)\s*µg/L', line)
                        ref_match = re.search(r'\((\d+)\s*à\s*(\d+)\)', line)
                        
                        if match:
                            value = int(match.group(1))
                            results.append({
                                'Catégorie': current_category or 'Biochimie',
                                'Biomarqueur': 'Ferritine',
                                'Valeur': value,
                                'Unité': 'µg/L',
                                'Référence': f"{ref_match.group(1)}-{ref_match.group(2)}" if ref_match else "10-291"
                            })
                    
                    # CRP ultrasensible
                    elif 'CRP' in line.upper() and 'ULTRASENSIBLE' in line.upper():
                        match = re.search(r'(\d+\.?\d*)\s*mg/L', line)
                        
                        if match:
                            value = float(match.group(1))
                            results.append({
                                'Catégorie': current_category or 'Chimie',
                                'Biomarqueur': 'CRP Ultrasensible',
                                'Valeur': value,
                                'Unité': 'mg/L',
                                'Référence': '<5'
                            })
                    
                    # Insuline
                    elif 'INSULINE' in line.upper() and 'HOMA' not in line.upper():
                        match = re.search(r'(\d+\.?\d*)\s*mUI/L', line)
                        ref_match = re.search(r'\((\d+)\s*à\s*(\d+)\)', line)
                        
                        if match:
                            value = float(match.group(1))
                            results.append({
                                'Catégorie': current_category or 'Hormonologie',
                                'Biomarqueur': 'Insuline',
                                'Valeur': value,
                                'Unité': 'mUI/L',
                                'Référence': f"{ref_match.group(1)}-{ref_match.group(2)}" if ref_match else "3-25"
                            })
                    
                    # HOMA-IR
                    elif 'HOMA' in line.upper():
                        match = re.search(r':\s*(\d+\.?\d*)', line)
                        
                        if match:
                            value = float(match.group(1))
                            results.append({
                                'Catégorie': current_category or 'Hormonologie',
                                'Biomarqueur': 'HOMA-IR',
                                'Valeur': value,
                                'Unité': '',
                                'Référence': '<2.4'
                            })
                    
                    # Vitamine D
                    elif 'VITAMINE D' in line.upper() or '25-OH' in line.upper():
                        match = re.search(r'(\d+\.?\d*)\s*ng/mL', line)
                        
                        if match:
                            value = float(match.group(1))
                            results.append({
                                'Catégorie': current_category or 'Immunologie',
                                'Biomarqueur': 'Vitamine D (25-OH)',
                                'Valeur': value,
                                'Unité': 'ng/mL',
                                'Référence': '30-60'
                            })
                    
                    # Magnésium érythrocytaire
                    elif 'MAGNÉSIUM' in line.upper() and 'ÉRYTHROCYTAIRE' in line.upper():
                        match = re.search(r'(\d+\.?\d*)\s*mg/dL', line)
                        ref_match = re.search(r'(\d+\.?\d*)\s*-\s*(\d+\.?\d*)', line)
                        
                        if match:
                            value = float(match.group(1))
                            results.append({
                                'Catégorie': 'Équilibre hydro-minéral',
                                'Biomarqueur': 'Magnésium érythrocytaire',
                                'Valeur': value,
                                'Unité': 'mg/dL',
                                'Référence': f"{ref_match.group(1)}-{ref_match.group(2)}" if ref_match else "4.4-5.8"
                            })
                    
                    # GPX (Glutathion peroxydase)
                    elif 'GPX' in line.upper() or 'GLUTATHION PEROXYDASE' in line.upper():
                        match = re.search(r'(\d+)\s*U/g\s*Hb', line)
                        ref_match = re.search(r'(\d+)\s*-\s*(\d+)', line)
                        
                        if match:
                            value = int(match.group(1))
                            results.append({
                                'Catégorie': 'Statut antioxydant',
                                'Biomarqueur': 'GPX (Glutathion peroxydase)',
                                'Valeur': value,
                                'Unité': 'U/g Hb',
                                'Référence': f"{ref_match.group(1)}-{ref_match.group(2)}" if ref_match else "40-62"
                            })
                    
                    # Glutathion total
                    elif 'GLUTATHION TOTAL' in line.upper():
                        match = re.search(r'(\d+)\s*µmol/L', line)
                        ref_match = re.search(r'(\d+)\s*-\s*(\d+)', line)
                        
                        if match:
                            value = int(match.group(1))
                            results.append({
                                'Catégorie': 'Statut antioxydant',
                                'Biomarqueur': 'Glutathion total',
                                'Valeur': value,
                                'Unité': 'µmol/L',
                                'Référence': f"{ref_match.group(1)}-{ref_match.group(2)}" if ref_match else "1200-1750"
                            })
                    
                    # Coenzyme Q10
                    elif 'COENZYME Q10' in line.upper() or 'COQ10' in line.upper():
                        match = re.search(r'(\d+)\s*μg/L', line)
                        ref_match = re.search(r'(\d+)\s*-\s*(\d+)', line)
                        
                        if match:
                            value = int(match.group(1))
                            results.append({
                                'Catégorie': 'Statut antioxydant',
                                'Biomarqueur': 'Coenzyme Q10',
                                'Valeur': value,
                                'Unité': 'μg/L',
                                'Référence': f"{ref_match.group(1)}-{ref_match.group(2)}" if ref_match else "670-990"
                            })
                    
                    # Zinc
                    elif 'ZINC' in line.upper() and 'PLASMA' not in line.upper():
                        match = re.search(r'(\d+)\s*μg/dL', line)
                        ref_match = re.search(r'(\d+)\s*-\s*(\d+)', line)
                        
                        if match:
                            value = int(match.group(1))
                            results.append({
                                'Catégorie': 'Statut antioxydant',
                                'Biomarqueur': 'Zinc',
                                'Valeur': value,
                                'Unité': 'μg/dL',
                                'Référence': f"{ref_match.group(1)}-{ref_match.group(2)}" if ref_match else "88-146"
                            })
                    
                    # Sélénium
                    elif 'SÉLÉNIUM' in line.upper() or 'SELENIUM' in line.upper():
                        match = re.search(r'(\d+)\s*μg/L', line)
                        ref_match = re.search(r'(\d+)\s*-\s*(\d+)', line)
                        
                        if match:
                            value = int(match.group(1))
                            results.append({
                                'Catégorie': 'Statut antioxydant',
                                'Biomarqueur': 'Sélénium',
                                'Valeur': value,
                                'Unité': 'μg/L',
                                'Référence': f"{ref_match.group(1)}-{ref_match.group(2)}" if ref_match else "90-143"
                            })
                    
                    # LBP (LPS-Binding protein)
                    elif 'LBP' in line.upper():
                        match = re.search(r'(\d+\.?\d*)\s*mg/L', line)
                        
                        if match:
                            value = float(match.group(1))
                            results.append({
                                'Catégorie': 'Perméabilité intestinale',
                                'Biomarqueur': 'LBP (LPS-Binding protein)',
                                'Valeur': value,
                                'Unité': 'mg/L',
                                'Référence': '0-6.8 (optimal) / 2.3-8.3 (normal)'
                            })
    
    except Exception as e:
        raise Exception(f"Erreur lors de l'extraction du PDF Synlab: {str(e)}")
    
    # Créer le DataFrame
    df = pd.DataFrame(results)
    
    # Trier par catégorie
    if not df.empty:
        df = df.sort_values('Catégorie')
    
    return df


def extract_idk_microbiome(pdf_path: str) -> Dict:
    """
    Extrait les données d'un rapport IDK GutMAP (PDF)
    
    Args:
        pdf_path: Chemin vers le fichier PDF IDK GutMAP
        
    Returns:
        Dictionnaire avec: dysbiosis_index, diversity, bacteria (liste de dict)
    """
    result = {
        'dysbiosis_index': None,
        'diversity': None,
        'bacteria': []
    }
    
    current_category = None
    current_group = None
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                
                if not text:
                    continue
                
                lines = text.split('\n')
                
                for i, line in enumerate(lines):
                    line = line.strip()
                    
                    # Extraire le Dysbiosis Index
                    if 'DYSBIOSIS INDEX' in line.upper():
                        # Chercher le niveau dans les lignes suivantes
                        for j in range(i+1, min(i+10, len(lines))):
                            next_line = lines[j].strip()
                            
                            if 'normobiotic' in next_line.lower():
                                result['dysbiosis_index'] = 1
                                break
                            elif 'mildly dysbiotic' in next_line.lower():
                                result['dysbiosis_index'] = 3
                                break
                            elif 'severely dysbiotic' in next_line.lower():
                                result['dysbiosis_index'] = 5
                                break
                    
                    # Extraire la Diversité
                    if 'DIVERSITY' in line.upper():
                        for j in range(i+1, min(i+5, len(lines))):
                            next_line = lines[j].strip()
                            
                            if 'as expected' in next_line.lower():
                                result['diversity'] = 'As expected'
                                break
                            elif 'slightly lower' in next_line.lower():
                                result['diversity'] = 'Slightly lower than expected'
                                break
                            elif 'lower than expected' in next_line.lower():
                                result['diversity'] = 'Lower than expected'
                                break
                    
                    # Détecter les catégories de bactéries
                    if 'Category A' in line or 'A. Broad commensals' in line:
                        current_category = 'A. Broad commensals'
                    elif 'Category B' in line or 'B. Enriched on animal-based diet' in line:
                        current_category = 'B. Enriched on animal-based diet'
                    elif 'Category C' in line or 'C. Essential cross-feeders' in line:
                        current_category = 'C. Essential cross-feeders'
                    elif 'Category D' in line or 'D. Anti-inflammatory' in line:
                        current_category = 'D. Anti-inflammatory bacteria'
                    elif 'Category E' in line or 'E. Pro-inflammatory' in line:
                        current_category = 'E. Pro-inflammatory & opportunistic pathogens'
                    
                    # Détecter les groupes
                    if 'A1. Prominent gut microbes' in line:
                        current_group = 'A1. Prominent gut microbes'
                    elif 'A2. Diverse gut bacterial communities' in line:
                        current_group = 'A2. Diverse gut bacterial communities'
                    elif 'B1. Enriched on animal-based diet' in line:
                        current_group = 'B1. Enriched on animal-based diet'
                    elif 'C1. Complex carbohydrate degraders' in line:
                        current_group = 'C1. Complex carbohydrate degraders'
                    elif 'C2. Lactic acid bacteria and probiotics' in line:
                        current_group = 'C2. Lactic acid bacteria and probiotics'
                    elif 'D1. Gut epithelial integrity marker' in line:
                        current_group = 'D1. Gut epithelial integrity marker'
                    elif 'D2. Major SCFA producers' in line:
                        current_group = 'D2. Major SCFA producers'
                    elif 'E1. Inflammation indicator' in line:
                        current_group = 'E1. Inflammation indicator'
                    elif 'E2. Potentially virulent' in line:
                        current_group = 'E2. Potentially virulent'
                    elif 'E3. Facultative anaerobes' in line:
                        current_group = 'E3. Facultative anaerobes'
                    elif 'E4. Predominantly oral bacteria' in line:
                        current_group = 'E4. Predominantly oral bacteria'
                    elif 'E5. Genital, respiratory, and skin bacteria' in line:
                        current_group = 'E5. Genital, respiratory, and skin bacteria'
                    
                    # Extraire les résultats de groupes (Expected/Slightly deviating/Deviating)
                    if current_group and ('Expected' in line or 'Slightly deviating' in line or 'Deviating' in line):
                        # Déterminer le résultat
                        if 'Expected' in line and 'Slightly' not in line and 'Deviating' not in line:
                            group_result = 'Expected'
                        elif 'Slightly deviating' in line:
                            group_result = 'Slightly deviating'
                        elif 'Deviating' in line and 'Slightly' not in line:
                            group_result = 'Deviating'
                        else:
                            continue
                        
                        # Ajouter l'entrée
                        result['bacteria'].append({
                            'category': current_category,
                            'group': current_group,
                            'result': group_result
                        })
                        
                        # Réinitialiser le groupe pour éviter les doublons
                        current_group = None
    
    except Exception as e:
        raise Exception(f"Erreur lors de l'extraction du PDF IDK GutMAP: {str(e)}")
    
    return result


def extract_data_from_excel(file_path: str, sheet_name: Optional[str] = None) -> pd.DataFrame:
    """
    Extrait les données d'un fichier Excel
    
    Args:
        file_path: Chemin vers le fichier Excel
        sheet_name: Nom de la feuille à lire (optionnel)
        
    Returns:
        DataFrame avec les données
    """
    try:
        if sheet_name:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
        else:
            df = pd.read_excel(file_path)
        
        return df
    
    except Exception as e:
        raise Exception(f"Erreur lors de la lecture du fichier Excel: {str(e)}")


def normalize_biomarker_name(name: str) -> str:
    """
    Normalise le nom d'un biomarqueur pour faciliter la correspondance avec les règles
    
    Args:
        name: Nom du biomarqueur
        
    Returns:
        Nom normalisé
    """
    # Supprimer les accents, mettre en majuscules, supprimer les espaces multiples
    normalized = name.upper().strip()
    
    # Remplacements courants
    replacements = {
        'GLYCÉMIE': 'GLYCEMIE',
        'ÉRYTHROCYTAIRE': 'ERYTHROCYTAIRE',
        'HÉMOGLOBINE': 'HEMOGLOBINE',
        'PROTÉINE': 'PROTEINE',
    }
    
    for old, new in replacements.items():
        normalized = normalized.replace(old, new)
    
    return normalized


def determine_biomarker_status(value: float, reference: str, biomarker: str) -> str:
    """
    Détermine le statut d'un biomarqueur (Bas/Normal/Élevé)
    
    Args:
        value: Valeur mesurée
        reference: Valeur de référence (format "min-max" ou "<max")
        biomarker: Nom du biomarqueur
        
    Returns:
        Statut: 'Bas', 'Normal', ou 'Élevé'
    """
    try:
        # Gérer les références avec "<"
        if reference.startswith('<'):
            max_val = float(reference.replace('<', '').strip())
            if value < max_val:
                return 'Normal'
            else:
                return 'Élevé'
        
        # Gérer les références avec ">"
        elif reference.startswith('>'):
            min_val = float(reference.replace('>', '').strip())
            if value > min_val:
                return 'Normal'
            else:
                return 'Bas'
        
        # Gérer les plages "min-max"
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
            # Format non reconnu, retourner Normal par défaut
            return 'Normal'
    
    except:
        return 'Normal'
