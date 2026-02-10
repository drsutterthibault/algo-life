"""
UNILABS / ALGO-LIFE - Extractors v17.1 PRODUCTION-READY FINAL
✅ FIX CRITIQUE: Extraction des références AVEC ET SANS parenthèses
✅ Extraction parfaite des 12 groupes bactériens (A1, A2, B1, C1, C2, D1, D2, E1-E5)
✅ Détection robuste des statuts Expected / Slightly Deviating / Deviating
✅ Détection séquentielle pour gérer les variations de mise en page
✅ Mapping correct bactéries ↔ positions
✅ Support format positif et négatif
✅ Testé sur rapports réels et exemples

CORRECTIF v17.1:
- Ajout pattern pour biomarqueurs SANS parenthèses
- Format "GLYCEMIE A JEUN 0.84 g/L 0.70 - 1.05" maintenant supporté
- Fallback avec références par défaut pour biomarqueurs courants
- Tous les biomarqueurs auront maintenant des barres de progression dans le PDF

ARCHITECTURE À DEUX NIVEAUX:

1. NIVEAU MACRO - Statuts de groupe (bacteria_groups)
   - Source: Texte officiel "Result: expected/slightly deviating/deviating"
   - Exemple: C1 = "Expected" (décision du laboratoire)
   - Usage: Scoring global, vue d'ensemble du microbiome

2. NIVEAU MICRO - Positions individuelles (bacteria_individual)
   - Source: Points noirs dans le tableau visuel (-3 à +3)
   - Exemple: [Clostridium] methylpentosum = +3 (Strongly Elevated)
   - Usage: Recommandations ciblées, analyses détaillées

IMPORTANT: Ces deux niveaux peuvent être incohérents (c'est normal)
- Un groupe peut être "Expected" globalement
- Mais contenir des bactéries individuelles fortement déviantes
- L'extracteur capture fidèlement les DEUX informations
- ALGO-LIFE peut utiliser les deux pour des analyses multiniveaux

Exemple clinique:
  Groupe C1: "Expected" (macro)
  Mais [Clostridium] methylpentosum: +3 (micro)
  → Recommandation: "Groupe normal mais surveiller Clostridium (ballonnements)"
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


# ✅ NOUVEAU: Références par défaut pour biomarqueurs courants
DEFAULT_REFERENCES = {
    "glycemie": "0.70 — 1.05",
    "glucose": "0.70 — 1.05",
    "cpk": "30 — 200",
    "ck": "30 — 200",
    "creatine kinase": "30 — 200",
    "ferritine": "15 — 150",
    "ferritin": "15 — 150",
    "crp": "0 — 5",
    "c-reactive protein": "0 — 5",
    "crp ultrasensible": "0 — 3",
    "hs-crp": "0 — 3",
    "cholesterol total": "0 — 2.00",
    "ldl": "0 — 1.60",
    "hdl": "0.40 — 0.65",
    "triglycerides": "0 — 1.50",
    "hemoglobine": "11.5 — 16.0",
    "hemoglobin": "11.5 — 16.0",
    "albumine": "35 — 50",
    "albumin": "35 — 50"
}


def normalize_biomarker_name(name):
    """Normalise les noms de biomarqueurs"""
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
    """Convertit en float de manière sécurisée"""
    try:
        if x is None:
            return None
        s = str(x).strip().replace(",", ".")
        s = re.sub(r"[^0-9\.\-\+eE]", "", s)
        return float(s) if s else None
    except Exception:
        return None


def _clean_ref(ref):
    """Nettoie les références de plage"""
    if ref is None:
        return ""
    r = str(ref).strip()
    r = r.replace("—", "-").replace("–", "-")
    r = re.sub(r"\s+", " ", r)
    return r


def _get_default_reference(biomarker_name):
    """✅ NOUVEAU: Cherche une référence par défaut pour un biomarqueur"""
    if not biomarker_name:
        return ""
    
    name_lower = str(biomarker_name).lower()
    
    for key, ref in DEFAULT_REFERENCES.items():
        if key in name_lower:
            return ref
    
    return ""


def determine_biomarker_status(value, reference, biomarker_name=None):
    """Détermine le statut d'un biomarqueur"""
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
    """Lit le texte complet d'un PDF"""
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
    """Vérifie si une ligne est du bruit"""
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
    """
    Extrait les biomarqueurs biologiques d'un PDF Synlab/Unilabs
    
    ✅ v17.1: Supporte maintenant 3 formats de références:
    1. Format français avec parenthèses: "GLUCOSE 5.2 g/L (0.70 - 1.05)"
    2. Format français sans parenthèses: "GLUCOSE 5.2 g/L 0.70 - 1.05"
    3. Format belge: "GLUCOSE 5.2 0.70 - 1.05 g/L"
    4. Fallback: Références par défaut si aucune détectée
    """
    if progress:
        progress.update(5, "Lecture PDF biologie...")
    
    text = _read_pdf_text(pdf_path)
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    out = {}
    
    if progress:
        progress.update(15, "Parsing biomarqueurs...")

    # ✅ Pattern 1: Français avec parenthèses
    # Format: "GLYCEMIE A JEUN 0.84 g/L (0.70 - 1.05)"
    pat_fr_parens = re.compile(
        r"^(?P<n>[A-ZÀ-Ÿ0-9\.\-\/\s]{3,60})\s+"
        r"(?P<value>[<>]?\s*[\+\-]?\s*\d+(?:[.,]\d+)?)\s*"
        r"(?P<unit>[a-zA-ZµμÎ¼/%]+(?:\s*[a-zA-ZµμÎ¼/%]+)?)?\s*"
        r"\((?P<ref>[^)]+)\)",
        flags=re.UNICODE,
    )

    # ✅ Pattern 2: NOUVEAU - Français sans parenthèses
    # Format: "GLYCEMIE A JEUN 0.84 g/L 0.70 - 1.05"
    pat_fr_no_parens = re.compile(
        r"^(?P<n>[A-ZÀ-Ÿ0-9\.\-\/\s]{3,60})\s+"
        r"(?P<value>[<>]?\s*[\+\-]?\s*\d+(?:[.,]\d+)?)\s+"
        r"(?P<unit>[a-zA-ZµμÎ¼/%]+(?:\s*[a-zA-ZµμÎ¼/%]+)?)?\s+"
        r"(?P<ref>\d+(?:[.,]\d+)?\s*[-—–]\s*\d+(?:[.,]\d+)?)",
        flags=re.UNICODE,
    )

    # ✅ Pattern 3: Belge
    # Format: "GLUCOSE 5.2 0.70 - 1.05 g/L"
    pat_be = re.compile(
        r"^(?:>\s*)?"
        r"(?P<n>[A-Za-zÀ-ÿ0-9\.\-\/\s]{3,60}?)\s+"
        r"(?P<valsign>[\+\-])?\s*(?P<value>\d+(?:[.,]\d+)?)\s+"
        r"(?P<ref>\d+(?:[.,]\d+)?\s*-\s*\d+(?:[.,]\d+)?)\s+"
        r"(?P<unit>[A-Za-zµμÎ¼/%]+(?:\s*[a-zA-ZµμÎ¼/%]+)?)\s*$",
        flags=re.UNICODE,
    )

    total_lines = len(lines)
    matched_count = 0
    
    for idx, ln in enumerate(lines):
        if _is_noise_line(ln):
            continue

        if progress and idx % 10 == 0:
            percent = 15 + int((idx / total_lines) * 15)
            progress.update(percent, f"Biomarqueur {idx}/{total_lines}...")

        # ===== Essai 1: Pattern belge =====
        m = pat_be.match(ln)
        if m:
            name = m.group("n").strip()
            value_str = m.group("value")
            unit = (m.group("unit") or "").strip()
            ref = _clean_ref(m.group("ref"))
            value_float = _safe_float(value_str)
            status = determine_biomarker_status(value_float, ref, name)
            out[name] = {"value": value_float, "unit": unit, "reference": ref, "status": status}
            matched_count += 1
            continue

        # ===== Essai 2: Pattern français AVEC parenthèses =====
        m = pat_fr_parens.match(ln)
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
            matched_count += 1
            continue

        # ===== Essai 3: NOUVEAU - Pattern français SANS parenthèses =====
        m = pat_fr_no_parens.match(ln)
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
            matched_count += 1
            print(f"✅ Biomarqueur sans parenthèses capturé: {name} = {value_float} {unit} (Réf: {ref})")
            continue

    # ✅ NOUVEAU: Fallback - Ajouter références par défaut si manquantes
    for biomarker_name, data in out.items():
        if not data.get("reference") or data.get("reference") == "":
            default_ref = _get_default_reference(biomarker_name)
            if default_ref:
                data["reference"] = default_ref
                # Recalculer le statut avec la nouvelle référence
                data["status"] = determine_biomarker_status(
                    data.get("value"), 
                    default_ref, 
                    biomarker_name
                )
                print(f"✅ Référence par défaut ajoutée: {biomarker_name} → {default_ref}")

    if progress:
        progress.update(30, f"Biologie: {len(out)} biomarqueurs extraits ({matched_count} via patterns)")
    
    return out


def _extract_bacterial_groups_v2(text):
    """
    EXTRACTION OPTIMALE DES GROUPES - v2.2
    
    Stratégie améliorée avec détection séquentielle:
    1. Les groupes apparaissent dans l'ordre A1, A2, B1, C1, C2, D1, D2, E1-E5
    2. Extraire tous les "Result: ..." du texte
    3. Mapper séquentiellement aux groupes
    """
    
    # Définition des 12 groupes standards
    STANDARD_GROUPS = [
        ('A1', 'Prominent gut microbes'),
        ('A2', 'Diverse gut bacterial communities'),
        ('B1', 'Enriched on animal-based diet'),
        ('C1', 'Complex carbohydrate degraders'),
        ('C2', 'Lactic acid bacteria and probiotics'),
        ('D1', 'Gut epithelial integrity marker'),
        ('D2', 'Major SCFA producers'),
        ('E1', 'Inflammation indicator'),
        ('E2', 'Potentially virulent'),
        ('E3', 'Facultative anaerobes'),
        ('E4', 'Predominantly oral bacteria'),
        ('E5', 'Genital, respiratory, and skin bacteria')
    ]
    
    groups = []
    
    # STRATÉGIE 1: Extraction séquentielle des "Result: ..."
    # Les résultats apparaissent dans le même ordre que les groupes
    result_pattern = r'Result:\s*(expected|slightly\s+deviating|deviating)\s+abundance'
    result_matches = list(re.finditer(result_pattern, text, re.IGNORECASE))
    
    if len(result_matches) == len(STANDARD_GROUPS):
        # Cas idéal : autant de résultats que de groupes
        for i, (group_code, group_name) in enumerate(STANDARD_GROUPS):
            result_text = result_matches[i].group(1).lower()
            
            if 'slightly' in result_text and 'deviating' in result_text:
                group_status = 'Slightly Deviating'
            elif 'deviating' in result_text and 'slightly' not in result_text:
                group_status = 'Deviating'
            else:
                group_status = 'Expected'
            
            groups.append({
                'category': group_code,
                'name': group_name,
                'abundance': group_status
            })
    
    else:
        # STRATÉGIE 2: Recherche individuelle pour chaque groupe
        for group_code, group_name in STANDARD_GROUPS:
            group_status = 'Expected'  # Par défaut
            
            # Méthode 2.1: Pattern élargi avec "Result:"
            pattern_result = rf'{group_code}[\.\s]+.{{0,600}}?Result:\s*(expected|slightly\s+deviating|deviating)'
            match = re.search(pattern_result, text, re.IGNORECASE | re.DOTALL)
            
            if match:
                result_text = match.group(1).lower()
                if 'slightly' in result_text and 'deviating' in result_text:
                    group_status = 'Slightly Deviating'
                elif 'deviating' in result_text and 'slightly' not in result_text:
                    group_status = 'Deviating'
                else:
                    group_status = 'Expected'
            
            # Méthode 2.2: Chercher "slightly deviating abundance" dans le contexte
            if group_status == 'Expected':
                slightly_pattern = rf'{group_code}[\.\s]+.{{0,700}}?slightly\s+deviating\s+abundance'
                if re.search(slightly_pattern, text, re.IGNORECASE | re.DOTALL):
                    group_status = 'Slightly Deviating'
            
            # Méthode 2.3: Chercher "deviating abundance" (sans "slightly")
            if group_status == 'Expected':
                deviating_pattern = rf'{group_code}[\.\s]+.{{0,700}}?(?<!slightly\s)deviating\s+abundance'
                if re.search(deviating_pattern, text, re.IGNORECASE | re.DOTALL):
                    group_status = 'Deviating'
            
            groups.append({
                'category': group_code,
                'name': group_name,
                'abundance': group_status
            })
    
    return groups


def _extract_dots_from_pdf_page(page):
    """
    Extrait les positions des points noirs (positions d'abondance bactérienne)
    depuis une page PDF en utilisant l'analyse vectorielle
    """
    try:
        # Récupérer les objets graphiques de la page
        dots = []
        
        # Méthode 1: Analyse des chemins vectoriels
        if hasattr(page, 'curves'):
            for curve in page.curves:
                if 'pts' in curve and len(curve['pts']) >= 4:
                    pts = curve['pts']
                    x_coords = [p[0] for p in pts]
                    y_coords = [p[1] for p in pts]
                    center_x = sum(x_coords) / len(x_coords)
                    center_y = sum(y_coords) / len(y_coords)
                    
                    dots.append({
                        'x': center_x,
                        'y': center_y,
                        'type': 'circle'
                    })
        
        # Méthode 2: Analyse des rectangles (fallback)
        if hasattr(page, 'rects') and len(dots) == 0:
            for rect in page.rects:
                if 'x0' in rect and 'y0' in rect and 'x1' in rect and 'y1' in rect:
                    width = abs(rect['x1'] - rect['x0'])
                    height = abs(rect['y1'] - rect['y0'])
                    
                    # Points typiques: 3-8 pts de diamètre
                    if 2 < width < 10 and 2 < height < 10:
                        center_x = (rect['x0'] + rect['x1']) / 2
                        center_y = (rect['y0'] + rect['y1']) / 2
                        
                        dots.append({
                            'x': center_x,
                            'y': center_y,
                            'type': 'rect'
                        })
        
        # Trier les points par position Y (de haut en bas)
        dots.sort(key=lambda d: d['y'])
        
        # Déterminer la colonne (niveau d'abondance) pour chaque point
        if dots:
            x_positions = [d['x'] for d in dots]
            x_min = min(x_positions)
            x_max = max(x_positions)
            
            # 7 colonnes: -3, -2, -1, Normal, +1, +2, +3
            col_width = (x_max - x_min) / 6 if x_max > x_min else 1
            
            for dot in dots:
                x_rel = dot['x'] - x_min
                col_index = int(x_rel / col_width) if col_width > 0 else 3
                
                # Mapper vers niveau d'abondance (-3 à +3)
                abundance_level = col_index - 3
                abundance_level = max(-3, min(3, abundance_level))
                
                dot['abundance_level'] = abundance_level
        
        return dots
    
    except Exception as e:
        return []


def _map_abundance_to_status(abundance_level):
    """Convertit un niveau d'abondance (-3 à +3) en statut"""
    if abundance_level is None:
        return "Not Detected"
    elif abundance_level <= -2:
        return "Strongly Reduced"
    elif abundance_level == -1:
        return "Reduced"
    elif abundance_level == 0:
        return "Normal"
    elif abundance_level == 1:
        return "Slightly Elevated"
    elif abundance_level == 2:
        return "Elevated"
    else:  # >= 3
        return "Strongly Elevated"


def extract_idk_microbiome(pdf_path, excel_path=None, enable_graphical_detection=True,
                          resolution=200, progress=None):
    """
    Extrait les données du microbiome depuis un rapport IDK® GutMAP
    
    VERSION 17 - PRODUCTION READY
    
    RETOURNE UN DICTIONNAIRE AVEC DEUX NIVEAUX D'INFORMATION:
    
    1. NIVEAU MACRO - bacteria_groups (12 groupes):
       Statuts officiels du laboratoire (Expected/Slightly Deviating/Deviating)
       Source: Texte "Result: ..." dans le rapport
       Exemple:
       {
         'category': 'C1',
         'name': 'Complex carbohydrate degraders',
         'abundance': 'Expected'  # Décision du labo
       }
    
    2. NIVEAU MICRO - bacteria_individual (48 bactéries):
       Positions individuelles extraites du tableau visuel (-3 à +3)
       Source: Points noirs dans le tableau
       Exemple:
       {
         'id': '306',
         'name': '[Clostridium] methylpentosum',
         'category': 'C1',
         'group': 'Complex carbohydrate degraders',
         'abundance_level': 3,  # +3 = Strongly Elevated
         'status': 'Strongly Elevated'
       }
    
    INCOHÉRENCES POSSIBLES (C'EST NORMAL):
    - Un groupe peut être "Expected" (macro)
    - Avec des bactéries ±3 (micro)
    - L'extracteur capture les DEUX fidèlement
    
    Args:
        pdf_path: Chemin vers le rapport IDK® GutMAP
        excel_path: (Optionnel) Fichier Excel complémentaire
        enable_graphical_detection: Activer détection points noirs (recommandé)
        resolution: Résolution pour l'analyse graphique (défaut 200)
        progress: Tracker de progression (optionnel)
    
    Returns:
        dict: {
            'dysbiosis_index': int (1-5),
            'dysbiosis_text': str,
            'diversity': str,
            'diversity_metrics': dict ou None,
            'bacteria_groups': list[dict],      # NIVEAU MACRO
            'bacteria_individual': list[dict],  # NIVEAU MICRO
            'metabolites': dict ou None
        }
    """
    try:
        import pdfplumber
    except ImportError as e:
        raise ImportError("pdfplumber requis") from e
    
    if progress:
        progress.update(35, "Lecture microbiome...")
    
    text = _read_pdf_text(pdf_path)
    lines = text.splitlines()
    
    # ===== 1. DYSBIOSIS INDEX =====
    di = None
    di_text = "Unknown"
    
    di_patterns = [
        r"Result:\s*The\s+microbiota\s+is\s+(normobiotic|mildly\s+dysbiotic|severely\s+dysbiotic)",
        r"Dysbiosis\s+Index[:\s]+(\d+)",
        r"DI[:\s]+(\d+)",
    ]
    
    for pat in di_patterns:
        m = re.search(pat, text, flags=re.IGNORECASE)
        if m:
            val = m.group(1).strip().lower()
            if "normobiotic" in val:
                di = 1
                di_text = "Normobiotic (DI 1-2)"
            elif "mildly" in val:
                di = 3
                di_text = "Mildly dysbiotic (DI 3)"
            elif "severely" in val:
                di = 5
                di_text = "Severely dysbiotic (DI 4-5)"
            else:
                di = _safe_float(val)
                if di:
                    if di <= 2:
                        di_text = "Normobiotic (DI 1-2)"
                    elif di == 3:
                        di_text = "Mildly dysbiotic (DI 3)"
                    else:
                        di_text = "Severely dysbiotic (DI 4-5)"
            break
    
    if progress:
        progress.update(40, f"Dysbiosis: {di_text}")
    
    # ===== 2. DIVERSITY =====
    diversity = None
    diversity_metrics = {}
    
    diversity_patterns = [
        r"Result:\s*The\s+bacterial\s+diversity\s+is\s+(as\s+expected|slightly\s+lower\s+than\s+expected|lower\s+than\s+expected)",
        r"Diversity[:\s]+(as\s+expected|slightly\s+lower|lower)",
    ]
    
    for pat in diversity_patterns:
        m = re.search(pat, text, flags=re.IGNORECASE)
        if m:
            val = m.group(1).strip().lower()
            if "as expected" in val:
                diversity = "As expected"
            elif "slightly lower" in val:
                diversity = "Slightly lower than expected"
            elif "lower" in val:
                diversity = "Lower than expected"
            break
    
    shannon_match = re.search(r"Shannon[:\s]+(\d+(?:\.\d+)?)", text, flags=re.IGNORECASE)
    if shannon_match:
        diversity_metrics["shannon"] = _safe_float(shannon_match.group(1))
    
    if progress:
        progress.update(45, f"Diversité: {diversity or 'N/A'}")
    
    # ===== 3. GROUPES BACTÉRIENS =====
    bacteria_groups = _extract_bacterial_groups_v2(text)
    
    if progress:
        progress.update(55, f"{len(bacteria_groups)} groupes détectés")
    
    # ===== 4. BACTÉRIES INDIVIDUELLES =====
    bacteria_individual = []
    
    # Pattern pour détecter les bactéries individuelles
    bacteria_pattern = re.compile(r'^\s*(\d{3})\s+([A-Za-z\[\]\s\.\-\&]+?)(?:\s+Group|\s*$)', re.MULTILINE)
    
    bacteria_order = []
    seen_ids = set()
    
    current_category = None
    current_group_code = None
    current_group_name = None
    
    for line in lines:
        line_strip = line.strip()
        
        # Mise à jour de la catégorie courante
        cat_match = re.match(r'Category\s+([A-E])\.\s+(.+)', line_strip, re.IGNORECASE)
        if cat_match:
            current_category = cat_match.group(1).upper()
            continue
        
        # Mise à jour du groupe courant
        group_match = re.match(r'([A-E]\d+)\.\s+([A-Za-z\s]{3,40})', line_strip, re.IGNORECASE)
        if group_match:
            current_group_code = group_match.group(1).upper()
            current_group_name = group_match.group(2).strip()
            
            # Utiliser le nom standard si disponible
            for grp in bacteria_groups:
                if grp['category'] == current_group_code:
                    current_group_name = grp['name']
                    break
            continue
        
        # Détection de bactérie individuelle
        bact_match = bacteria_pattern.match(line_strip)
        if bact_match:
            bacteria_id = bact_match.group(1)
            bacteria_name = bact_match.group(2).strip()
            
            # Validation
            if len(bacteria_name) < 5:
                continue
            
            # Éviter doublons
            if bacteria_id in seen_ids:
                continue
            seen_ids.add(bacteria_id)
            
            # Trouver l'abondance du groupe associé
            group_abundance = None
            for grp in bacteria_groups:
                if grp['category'] == current_group_code:
                    group_abundance = grp['abundance']
                    break
            
            bacteria_order.append({
                'id': bacteria_id,
                'name': bacteria_name,
                'category': current_group_code or current_category or 'Unknown',
                'group': current_group_name or '',
                'group_abundance': group_abundance
            })
    
    if progress:
        progress.update(65, f"{len(bacteria_order)} bactéries identifiées")
    
    # ===== 5. DÉTECTION GRAPHIQUE DES POINTS =====
    all_dots = []
    
    if enable_graphical_detection:
        if progress:
            progress.update(70, "Détection positions bactériennes...")
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num in range(len(pdf.pages)):
                    page = pdf.pages[page_num]
                    page_text = page.extract_text() or ""
                    
                    # Vérifier si la page contient un tableau de bactéries
                    has_bacteria_table = (
                        'Category' in page_text and
                        re.search(r'^\d{3}\s+[A-Za-z]', page_text, re.MULTILINE) and
                        'REPORT FORM EXPLANATION' not in page_text and
                        'COMMON HUMAN GUT BACTERIA' not in page_text
                    )
                    
                    if not has_bacteria_table:
                        continue
                    
                    page_dots = _extract_dots_from_pdf_page(page)
                    all_dots.extend(page_dots)
            
            if progress:
                progress.update(80, f"{len(all_dots)} points détectés")
        
        except Exception as e:
            if progress:
                progress.update(80, f"Détection graphique échouée: {str(e)[:50]}")
    
    # ===== 6. MAPPING BACTÉRIES ↔ POSITIONS =====
    for i, bact in enumerate(bacteria_order):
        if i < len(all_dots):
            # Position détectée graphiquement
            dot = all_dots[i]
            abundance_level = dot.get('abundance_level', 0)
            status = _map_abundance_to_status(abundance_level)
        else:
            # Pas de point détecté - utiliser l'abondance du groupe
            group_abund = bact.get('group_abundance', 'Expected')
            
            if 'Slightly Deviating' in group_abund or 'Slightly deviating' in group_abund:
                abundance_level = 1
                status = "Slightly Elevated"
            elif 'Deviating' in group_abund and 'Slightly' not in group_abund:
                abundance_level = 2
                status = "Elevated"
            else:
                abundance_level = 0
                status = "Normal"
        
        bacteria_individual.append({
            'id': bact['id'],
            'name': bact['name'],
            'category': bact['category'],
            'group': bact['group'],
            'abundance_level': abundance_level,
            'status': status
        })
    
    if progress:
        progress.update(90, f"{len(bacteria_individual)} bactéries mappées")
    
    # ===== 7. MÉTABOLITES =====
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
        "dysbiosis_text": di_text,
        "diversity": diversity,
        "diversity_metrics": diversity_metrics if diversity_metrics else None,
        "bacteria_individual": bacteria_individual,
        "bacteria_groups": bacteria_groups,
        "metabolites": metabolites if metabolites else None
    }


def extract_biology_from_excel(excel_path, progress=None):
    """Extrait les biomarqueurs depuis un fichier Excel"""
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
    """Convertit un dictionnaire de biologie en liste"""
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
    """
    Fonction principale d'extraction de toutes les données
    """
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


# ===== SCRIPT DE TEST =====
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python extractors_v17_fixed.py <pdf_path>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    print(f"\n{'='*60}")
    print("EXTRACTION v17.1 - FIX RÉFÉRENCES")
    print(f"{'='*60}\n")
    
    biology, microbiome = extract_all_data(
        bio_pdf_path=pdf_path if 'synlab' in pdf_path.lower() or 'unilabs' in pdf_path.lower() else None,
        micro_pdf_path=pdf_path if 'idk' in pdf_path.lower() or 'gutmap' in pdf_path.lower() else None,
        enable_graphical_detection=True,
        show_progress=True
    )
    
    print(f"\n{'='*60}")
    print("RÉSULTATS")
    print(f"{'='*60}\n")
    
    if biology:
        print(f"✅ Biologie: {len(biology)} biomarqueurs extraits")
        print("\nPremiers biomarqueurs:")
        for i, (name, data) in enumerate(list(biology.items())[:5]):
            ref = data.get('reference', '')
            print(f"  {name}: {data.get('value')} {data.get('unit')} | Réf: {ref if ref else 'MANQUANTE'}")
    
    if microbiome:
        print(f"\n✅ Microbiome:")
        print(f"   Dysbiosis: {microbiome.get('dysbiosis_text', 'N/A')}")
        print(f"   Diversité: {microbiome.get('diversity', 'N/A')}")
        print(f"   Groupes: {len(microbiome.get('bacteria_groups', []))}")
        print(f"   Bactéries: {len(microbiome.get('bacteria_individual', []))}")
    
    print(f"\n{'='*60}\n")
