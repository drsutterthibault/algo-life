"""
UNILABS / ALGO-LIFE - Extractors v14.0 FIXED
✅ Correction détection des anomalies microbiome (Slightly deviating)
✅ Toutes les fonctions implémentées
"""

from __future__ import annotations
import os
import re
import sys
import unicodedata
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    np = None


class ProgressTracker:
    def __init__(self, total_steps=100, show_bar=True):
        self.total_steps = total_steps
        self.current_step = 0
        self.show_bar = show_bar
        self.current_task = ""
    
    def update(self, step, task=""):
        self.current_step = min(step, self.total_steps)
        self.current_task = task
        if self.show_bar:
            self._render()
    
    def _render(self):
        try:
            percent = int((self.current_step / self.total_steps) * 100)
            bar_length = 40
            filled = int((percent / 100) * bar_length)
            bar = "█" * filled + "░" * (bar_length - filled)
            sys.stdout.write(f"\r🔄 [{bar}] {percent}% - {self.current_task}")
            sys.stdout.flush()
            if self.current_step >= self.total_steps:
                sys.stdout.write("\n")
                sys.stdout.flush()
        except Exception:
            pass


def normalize_biomarker_name(name):
    if name is None:
        return ""
    s = str(name).strip()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.upper()
    s = s.replace(".", " ")
    s = s.replace(",", " ")
    s = s.replace("'", "'")
    s = re.sub(r"[^A-Z0-9\s\-\+/]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    
    replacements = {
        "C P K": "CPK", "L D L": "LDL", "H D L": "HDL",
        "V G M": "VGM", "T C M H": "TCMH", "C C M H": "CCMH",
        "C R P": "CRP", "T S H": "TSH", "D F G": "DFG",
        "G P T": "GPT", "G O T": "GOT"
    }
    for old, new in replacements.items():
        s = s.replace(old, new)
    return s


def _safe_float(x):
    try:
        if x is None:
            return None
        s = str(x).strip().replace(",", ".")
        s = re.sub(r"[^0-9\.\-\+eE]", "", s)
        return float(s) if s else None
    except Exception:
        return None


def _clean_ref(ref):
    if ref is None:
        return ""
    r = str(ref).strip()
    r = r.replace("—", "-").replace("–", "-")
    r = re.sub(r"\s+", " ", r)
    return r


def determine_biomarker_status(value, reference, biomarker_name=None):
    v = _safe_float(value)
    if v is None:
        return "Inconnu"
    
    ref = _clean_ref(reference)
    m = re.search(r"(-?\d+(?:[.,]\d+)?)\s*(?:-|à|to)\s*(-?\d+(?:[.,]\d+)?)", ref, flags=re.IGNORECASE)
    if m:
        lo = _safe_float(m.group(1))
        hi = _safe_float(m.group(2))
        if lo is None or hi is None:
            return "Inconnu"
        if v < lo:
            return "Bas"
        if v > hi:
            return "Élevé"
        return "Normal"
    
    m = re.search(r"(?:<|≤)\s*(-?\d+(?:[.,]\d+)?)", ref)
    if m:
        hi = _safe_float(m.group(1))
        if hi is None:
            return "Inconnu"
        return "Élevé" if v > hi else "Normal"
    
    m = re.search(r"(?:>|≥)\s*(-?\d+(?:[.,]\d+)?)", ref)
    if m:
        lo = _safe_float(m.group(1))
        if lo is None:
            return "Inconnu"
        return "Bas" if v < lo else "Normal"
    
    return "Inconnu"


def _read_pdf_text(pdf_path):
    try:
        import pdfplumber
    except ImportError as e:
        raise ImportError("pdfplumber manquant") from e
    
    chunks = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            chunks.append(page.extract_text() or "")
    return "\n".join(chunks)


_IGNORE_PATTERNS = [
    r"^Édition\s*:",
    r"^Laboratoire",
    r"^SYNLAB",
    r"^UNILABS",
    r"^Dossier",
    r"^FranceLIS",
    r"^Analyses",
    r"^BIOCHIMIE|^CHIMIE|^HORMONOLOGIE|^IMMUNOLOGIE|^HEMATOLOGIE",
    r"^Colorimétrie|^Chimiluminescence",
    r"^Interprétation",
    r"^Accéder",
    r"^Validé",
    r"^Page\s+\d+",
]


def _is_noise_line(line):
    if not line:
        return True
    s = line.strip()
    if len(s) < 4:
        return True
    for pat in _IGNORE_PATTERNS:
        if re.search(pat, s, flags=re.IGNORECASE):
            return True
    return False


def extract_synlab_biology(pdf_path, progress=None):
    if progress:
        progress.update(5, "Lecture PDF biologie...")
    
    text = _read_pdf_text(pdf_path)
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    out = {}
    
    if progress:
        progress.update(15, "Parsing biomarqueurs...")

    pat_fr = re.compile(
        r"^(?P<n>[A-ZÀ-Ÿ0-9\.\-\/\s]{3,60})\s+"
        r"(?P<value>[<>]?\s*[\+\-]?\s*\d+(?:[.,]\d+)?)\s*"
        r"(?P<unit>[a-zA-ZµμÎ¼/%]+(?:\s*[a-zA-ZµμÎ¼/%]+)?)?\s*"
        r"\((?P<ref>[^)]+)\)",
        flags=re.UNICODE,
    )

    pat_be = re.compile(
        r"^(?:>\s*)?"
        r"(?P<n>[A-Za-zÀ-ÿ0-9\.\-\/\s]{3,60}?)\s+"
        r"(?P<valsign>[\+\-])?\s*(?P<value>\d+(?:[.,]\d+)?)\s+"
        r"(?P<ref>\d+(?:[.,]\d+)?\s*-\s*\d+(?:[.,]\d+)?)\s+"
        r"(?P<unit>[A-Za-zµμÎ¼/%]+(?:\s*[a-zA-ZµμÎ¼/%]+)?)\s*$",
        flags=re.UNICODE,
    )

    total_lines = len(lines)
    for idx, ln in enumerate(lines):
        if _is_noise_line(ln):
            continue

        if progress and idx % 10 == 0:
            percent = 15 + int((idx / total_lines) * 15)
            progress.update(percent, f"Biomarqueur {idx}/{total_lines}...")

        m = pat_be.match(ln)
        if m:
            name = m.group("n").strip()
            value_str = m.group("value")
            unit = (m.group("unit") or "").strip()
            ref = _clean_ref(m.group("ref"))
            value_float = _safe_float(value_str)
            status = determine_biomarker_status(value_float, ref, name)
            out[name] = {"value": value_float, "unit": unit, "reference": ref, "status": status}
            continue

        m = pat_fr.match(ln)
        if m:
            name = m.group("n").strip()
            if re.search(r"\bSIEMENS\b", name, flags=re.IGNORECASE):
                continue
            value_str = m.group("value")
            unit = (m.group("unit") or "").strip()
            ref = _clean_ref(m.group("ref"))
            value_float = _safe_float(value_str)
            status = determine_biomarker_status(value_float, ref, name)
            out[name] = {"value": value_float, "unit": unit, "reference": ref, "status": status}
            continue

    if progress:
        progress.update(30, f"Biologie: {len(out)} biomarqueurs extraits")
    
    return out


def _extract_dots_vectorial(page):
    """
    Extrait les points noirs (positions d'abondance bactérienne) depuis une page PDF.
    Utilise la structure réelle du tableau (lignes verticales) pour déterminer les colonnes.
    """
    dots = []
    
    if not hasattr(page, 'curves'):
        return dots
    
    page_height = page.height
    
    # Zone verticale valide (éviter headers/footers)
    table_y_start = page_height * 0.10
    table_y_end = page_height * 0.85
    
    # Trouver les lignes verticales pour délimiter les colonnes
    lines = page.lines if hasattr(page, 'lines') else []
    vertical_lines = [line for line in lines if abs(line.get('height', 0)) > 20]
    
    if len(vertical_lines) < 9:
        # Pas assez de lignes verticales, utiliser les positions par défaut
        # Basé sur l'analyse: centres des colonnes sont environ:
        column_centers = {
            -3: 114.4,
            -2: 244.2,
            -1: 372.7,
            0: 391.7,
            1: 410.7,
            2: 429.7,
            3: 448.7
        }
    else:
        # Calculer les centres des colonnes basés sur les lignes verticales
        x_positions = sorted(set([line.get('x0', 0) for line in vertical_lines]))
        
        # Les colonnes d'abondance vont de la ligne 2 à la ligne 8
        if len(x_positions) >= 9:
            column_centers = {
                -3: (x_positions[1] + x_positions[2]) / 2,
                -2: (x_positions[2] + x_positions[3]) / 2,
                -1: (x_positions[3] + x_positions[4]) / 2,
                0: (x_positions[4] + x_positions[5]) / 2,
                1: (x_positions[5] + x_positions[6]) / 2,
                2: (x_positions[6] + x_positions[7]) / 2,
                3: (x_positions[7] + x_positions[8]) / 2
            }
        else:
            # Fallback
            column_centers = {
                -3: 114.4, -2: 244.2, -1: 372.7,
                0: 391.7, 1: 410.7, 2: 429.7, 3: 448.7
            }
    
    seen_positions = set()  # Pour éliminer les doublons
    
    curves = page.curves
    for curve in curves:
        w = curve.get('width', 0)
        h = curve.get('height', 0)
        x = curve.get('x0', 0)
        y = curve.get('top', 0)
        color = curve.get('non_stroking_color', None)  # CORRECTION: Extraire couleur
        fill = curve.get('fill', False)  # CORRECTION: Extraire fill
        
        # Filtrer: taille entre 4 et 8 pixels (points noirs réels)
        if not (4.0 < w < 8.0 and 4.0 < h < 8.0):
            continue
        
        # CORRECTION: Filtrer NOIR uniquement (exclure légende colorée)
        if color != 0.0:
            continue
        
        # CORRECTION: Doit être rempli
        if not fill:
            continue
        
        # Filtrer: position verticale dans la zone du tableau
        if not (table_y_start <= y <= table_y_end):
            continue
        
        # Éliminer les doublons (même position arrondie)
        pos_key = (round(x, 1), round(y, 1))
        if pos_key in seen_positions:
            continue
        seen_positions.add(pos_key)
        
        # Trouver la colonne la plus proche
        closest_level = min(column_centers.keys(), 
                          key=lambda level: abs(column_centers[level] - x))
        
        # Vérifier que le point est assez proche du centre (tolérance de 15 pixels)
        if abs(column_centers[closest_level] - x) < 15:
            dots.append({
                'x': x,
                'y': y,
                'col_idx': closest_level + 3,  # Convertir en index 0-6
                'abundance_level': closest_level
            })
    
    # Trier par position Y (ordre vertical dans le tableau)
    dots.sort(key=lambda d: d['y'])
    return dots


def _map_abundance_to_status(level):
    if level is None:
        return "Unknown"
    if -1 <= level <= 1:
        return "Normal"
    elif level == -2:
        return "Reduced"
    elif level <= -3:
        return "Strongly Reduced"
    elif level == 2:
        return "Elevated"
    else:
        return "Strongly Elevated"


def _map_group_result_to_abundance(result):
    r = str(result).lower().strip()
    if "expected" in r:
        return "Normal"
    elif "slightly" in r and "deviating" in r:
        return "Slightly Deviating"
    elif "deviating" in r:
        return "Deviating"
    return "Unknown"


# Groupes GutMAP connus
ALL_GUTMAP_GROUPS = {
    "A1": "Prominent gut microbes",
    "A2": "Diverse gut bacterial communities",
    "B1": "Enriched on animal-based diet",
    "C1": "Complex carbohydrate degraders",
    "C2": "Lactic acid bacteria and probiotics",
    "D1": "Gut epithelial integrity marker",
    "D2": "Major SCFA producers",
    "E1": "Inflammation indicator",
    "E2": "Potentially virulent",
    "E3": "Facultative anaerobes",
    "E4": "Predominantly oral bacteria",
    "E5": "Genital, respiratory, and skin bacteria"
}


def extract_idk_microbiome(pdf_path, excel_path=None, enable_graphical_detection=True, 
                          resolution=200, progress=None):
    try:
        import pdfplumber
    except ImportError as e:
        raise ImportError("pdfplumber manquant") from e
    
    if progress:
        progress.update(35, "Lecture PDF microbiome...")
    
    text = _read_pdf_text(pdf_path)
    
    # === CRITIQUE: Nettoyer les sauts de ligne dans les paragraphes  ===
    # Remplacer les sauts de ligne au milieu des phrases par des espaces
    text = re.sub(r'([a-z])\n([a-z])', r'\1 \2', text)
    
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    
    if progress:
        progress.update(40, "Extraction dysbiose...")
    
    # Dysbiose - Convertir le texte en valeur numérique pour compatibilité avec rules_engine.py
    di = None
    di_text = None
    di_match = re.search(r"Result:\s*The microbiota is\s+(\w+)", text, flags=re.IGNORECASE)
    if di_match:
        di_text = di_match.group(1).lower()
        # Mapper le texte vers une valeur numérique (échelle 1-5)
        # normobiotic = 1-2, mildly dysbiotic = 3, severely dysbiotic = 4-5
        if "normobiotic" in di_text:
            di = 1
        elif "mild" in di_text:
            di = 3
        elif "severe" in di_text:
            di = 5
        else:
            # Fallback: essayer d'extraire un chiffre
            num_match = re.search(r'\d+', di_text)
            if num_match:
                di = int(num_match.group())
            else:
                di = 1  # Default normobiotic
    
    # Diversité
    diversity = None
    div_match = re.search(
        r"Result:\s*The bacterial diversity is\s+(.+?)(?=\n|For a more|Page|$)",
        text,
        flags=re.IGNORECASE
    )
    if div_match:
        diversity = div_match.group(1).strip()
    
    # Métriques de diversité (optionnel)
    diversity_metrics = {}
    shannon_match = re.search(r"Shannon[:\s]+(\d+(?:\.\d+)?)", text, flags=re.IGNORECASE)
    if shannon_match:
        diversity_metrics["shannon"] = _safe_float(shannon_match.group(1))
    
    if progress:
        progress.update(50, "Extraction groupes bactériens...")
    
    bacteria_groups = []
    found_groups = {}
    
    # === AMÉLIORATION CRITIQUE : Regex qui gère les sauts de ligne ===
    group_pattern = re.compile(r"^([A-E]\d)\.\s+(.+?)$")
    
    # Pattern amélioré qui cherche sur PLUSIEURS lignes avec DOTALL
    result_multiline_pattern = re.compile(
        r'Result:\s*(.{1,100}?abundance\s+of\s+these\s+bacteria)',
        flags=re.IGNORECASE | re.DOTALL
    )
    
    current_category = None
    current_group_code = None
    current_group_name = None
    
    # === Extraire d'abord tous les résultats avec contexte ===
    for match in result_multiline_pattern.finditer(text):
        result_text = match.group(1).lower().strip()
        # Nettoyer les sauts de ligne internes
        result_text = re.sub(r'\s+', ' ', result_text)
        
        # Trouver le code de groupe dans le contexte précédent (AUGMENTÉ à 800 caractères)
        context_start = max(0, match.start() - 800)
        context = text[context_start:match.start()]
        
        # Chercher le dernier groupe mentionné
        group_matches = list(re.finditer(r'([A-E]\d)\.', context))
        if not group_matches:
            continue
            
        last_group = group_matches[-1].group(1)
        
        # Déterminer le statut AVEC précision
        if 'expected abundance' in result_text and 'slightly' not in result_text and 'deviating' not in result_text:
            status_name = "Expected"
            abundance = "Normal"
        elif 'slightly' in result_text and ('deviating' in result_text or 'abundance' in result_text):
            status_name = "Slightly deviating"
            abundance = "Slightly Deviating"
        elif 'deviating abundance' in result_text and 'slightly' not in result_text:
            status_name = "Deviating"
            abundance = "Deviating"
        else:
            continue
        
        # Récupérer le nom du groupe
        group_name_match = re.search(rf'{last_group}\.\s+([A-Za-z\s\-]+?)(?=\n|No\.|Group|\d{{3}}|$)', text)
        group_name = group_name_match.group(1).strip()[:50] if group_name_match else "Unknown"
        
        bacteria_groups.append({
            "category": last_group,
            "group": f"{last_group}. {group_name}",
            "result": status_name.capitalize(),
            "abundance": abundance,
            "has_explicit_result": True
        })
        found_groups[last_group] = "processed"
    
    # Ajouter les groupes manquants
    for group_code, group_name in ALL_GUTMAP_GROUPS.items():
        if found_groups.get(group_code) != "processed":
            bacteria_groups.append({
                "category": group_code,
                "group": f"{group_code}. {group_name}",
                "result": "Expected",
                "abundance": "Normal",
                "has_explicit_result": False
            })
    
    bacteria_groups.sort(key=lambda x: x["category"])
    
    # Dédupliquer
    seen_groups = {}
    for grp in bacteria_groups:
        key = grp["category"]
        if key not in seen_groups:
            seen_groups[key] = grp
        elif grp.get("has_explicit_result", False):
            seen_groups[key] = grp
    
    bacteria_groups = list(seen_groups.values())
    bacteria_groups.sort(key=lambda x: x["category"])
    
    if progress:
        progress.update(65, f"{len(bacteria_groups)} groupes extraits")
    
    if progress:
        progress.update(68, "Extraction bactéries individuelles...")
    
    bacteria_individual = []
    current_category = None
    current_group_code = None
    current_group_name = None
    bacteria_pattern = re.compile(r"^(\d{3})\s+([A-Za-z\[\]\(\)\.\-&,\s]+?)$")
    
    bacteria_order = []
    seen_bacteria_ids = set()  # CORRECTION: Éviter doublons
    
    for line in lines:
        line_strip = line.strip()
        
        cat_match = re.match(r"Category\s+([A-E])\.\s+(.+)", line_strip, re.IGNORECASE)
        if cat_match:
            current_category = cat_match.group(1).upper()
            continue
        
        grp_match = group_pattern.match(line_strip)
        if grp_match:
            current_group_code = grp_match.group(1).upper()
            full_name = grp_match.group(2).strip()
            current_group_name = full_name[:50] if len(full_name) > 50 else full_name
            continue
        
        if re.match(r"Result:\s+", line_strip, re.IGNORECASE):
            continue
        
        bact_match = bacteria_pattern.match(line_strip)
        if bact_match:
            bacteria_id = bact_match.group(1)
            bacteria_name = bact_match.group(2).strip()
            
            if len(bacteria_name) < 5:
                continue
            
            # CORRECTION: Éviter doublons (page légende répète certains IDs)
            if bacteria_id in seen_bacteria_ids:
                continue
            seen_bacteria_ids.add(bacteria_id)
            
            group_abundance = None
            for grp in bacteria_groups:
                if grp["category"] == current_group_code:
                    group_abundance = grp["abundance"]
                    break
            
            bacteria_order.append({
                "id": bacteria_id,
                "name": bacteria_name,
                "category": current_group_code or current_category or "Unknown",
                "group": current_group_name or "",
                "group_abundance": group_abundance
            })
    
    if enable_graphical_detection and progress:
        progress.update(70, "Détection vectorielle points noirs...")
    
    all_dots = []
    
    if enable_graphical_detection:
        try:
            with pdfplumber.open(pdf_path) as pdf:
                # Parcourir les pages et ne traiter que celles avec des tableaux de bactéries
                for page_num in range(len(pdf.pages)):
                    page = pdf.pages[page_num]
                    page_text = page.extract_text() or ""
                    
                    # Vérifier si la page contient un tableau de bactéries
                    # CORRECTION: Exclure pages légende/explication
                    has_bacteria_table = (
                        'Category' in page_text and
                        re.search(r'^\d{3}\s+[A-Za-z]', page_text, re.MULTILINE) and
                        'REPORT FORM EXPLANATION' not in page_text and
                        'COMMON HUMAN GUT BACTERIA' not in page_text
                    )
                    
                    if not has_bacteria_table:
                        continue
                    
                    page_dots = _extract_dots_vectorial(page)
                    all_dots.extend(page_dots)
                
                if progress:
                    progress.update(75, f"{len(all_dots)} points détectés")
        except Exception as e:
            if progress:
                progress.update(75, f"Détection échouée: {e}")
    
    for i, bact in enumerate(bacteria_order):
        if i < len(all_dots):
            dot = all_dots[i]
            abundance_level = dot['abundance_level']
            status = _map_abundance_to_status(abundance_level)
        else:
            # CORRECTION: Pas de point détecté - utiliser groupe, pas +0 par défaut
            group_abund = bact.get("group_abundance", "Normal")
            if "Slightly Deviating" in group_abund:
                abundance_level = 2  # Élévation modérée
                status = "Slightly Elevated"
            elif "Deviating" in group_abund:
                abundance_level = 3
                status = "Strongly Elevated"
            else:
                # CORRECTION: None au lieu de 0
                abundance_level = None
                status = "Not Detected"
        
        bacteria_individual.append({
            "id": bact["id"],
            "name": bact["name"],
            "category": bact["category"],
            "group": bact["group"],
            "abundance_level": abundance_level,
            "status": status
        })
    
    if progress:
        progress.update(80, f"{len(bacteria_individual)} bactéries mappées")
    
    metabolites = {}
    m_but = re.search(r"Butyrate[:\s]+(\d+(?:\.\d+)?)", text, flags=re.IGNORECASE)
    if m_but:
        metabolites["butyrate"] = _safe_float(m_but.group(1))
    m_ace = re.search(r"Acetate[:\s]+(\d+(?:\.\d+)?)", text, flags=re.IGNORECASE)
    if m_ace:
        metabolites["acetate"] = _safe_float(m_ace.group(1))
    m_pro = re.search(r"Propionate[:\s]+(\d+(?:\.\d+)?)", text, flags=re.IGNORECASE)
    if m_pro:
        metabolites["propionate"] = _safe_float(m_pro.group(1))
    
    if progress:
        progress.update(100, "Extraction terminée")
    
    return {
        "dysbiosis_index": di,
        "dysbiosis_text": di_text,  # Texte original pour affichage
        "diversity": diversity,
        "diversity_metrics": diversity_metrics if diversity_metrics else None,
        "bacteria_individual": bacteria_individual,
        "bacteria_groups": bacteria_groups,
        "metabolites": metabolites if metabolites else None
    }


def extract_biology_from_excel(excel_path, progress=None):
    try:
        if progress:
            progress.update(10, "Lecture Excel...")
        
        df = pd.read_excel(excel_path)
        col_name = None
        col_value = None
        col_unit = None
        col_ref = None
        
        for col in df.columns:
            col_lower = str(col).lower()
            if "biomarqueur" in col_lower or "marqueur" in col_lower or "paramètre" in col_lower:
                col_name = col
            elif "valeur" in col_lower or "résultat" in col_lower or "result" in col_lower:
                col_value = col
            elif "unité" in col_lower or "unit" in col_lower:
                col_unit = col
            elif "référence" in col_lower or "norme" in col_lower or "range" in col_lower:
                col_ref = col
        
        if not col_name or not col_value:
            return {}
        
        out = {}
        total_rows = len(df)
        
        for idx, (_, row) in enumerate(df.iterrows()):
            if progress and idx % 5 == 0:
                percent = 10 + int((idx / total_rows) * 20)
                progress.update(percent, f"Excel: {idx}/{total_rows}...")
            
            name = str(row.get(col_name, "")).strip()
            if not name or name.lower() == "nan":
                continue
            
            value_raw = row.get(col_value)
            unit = str(row.get(col_unit, "")).strip() if col_unit else ""
            ref = str(row.get(col_ref, "")).strip() if col_ref else ""
            value = _safe_float(value_raw)
            status = determine_biomarker_status(value, ref, name)
            
            out[name] = {
                "value": value,
                "unit": unit,
                "reference": ref,
                "status": status
            }
        
        if progress:
            progress.update(30, f"Excel: {len(out)} entrées")
        
        return out
    
    except Exception:
        return {}


def biology_dict_to_list(biology, default_category="Autres"):
    out = []
    for name, d in (biology or {}).items():
        if not isinstance(d, dict):
            continue
        out.append({
            "name": str(d.get("name", name)).strip(),
            "value": d.get("value"),
            "unit": str(d.get("unit", "")).strip(),
            "reference": str(d.get("reference", "")).strip(),
            "status": str(d.get("status", "Inconnu")).strip(),
            "category": str(d.get("category", default_category)).strip() or default_category,
        })
    return out


def extract_all_data(bio_pdf_path=None, bio_excel_path=None, micro_pdf_path=None, 
                     micro_excel_path=None, enable_graphical_detection=True, 
                     show_progress=True):
    progress = ProgressTracker(total_steps=100, show_bar=show_progress) if show_progress else None
    
    biology = {}
    microbiome = {}
    
    if progress:
        progress.update(0, "Démarrage...")
    
    if bio_pdf_path:
        biology.update(extract_synlab_biology(bio_pdf_path, progress))
    
    if bio_excel_path:
        biology.update(extract_biology_from_excel(bio_excel_path, progress))
    
    if micro_pdf_path:
        microbiome = extract_idk_microbiome(
            micro_pdf_path, 
            micro_excel_path,
            enable_graphical_detection=enable_graphical_detection,
            resolution=200,
            progress=progress
        )
    
    if progress:
        progress.update(100, "Terminé!")
    
    return biology, microbiome
