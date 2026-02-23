"""
ALGO-LIFE - Extractors v18.1 FINAL WITH EXCEL MICROBIOME SUPPORT
✅ Extraction PDF biologie (SYNLAB/UNILABS)
✅ Extraction PDF microbiome (IDK GutMAP)
✅ Extraction Excel biologie
✅ ✨ NOUVEAU: Extraction Excel microbiome (fichier structuré)
✅ ✨ CORRIGÉ: Gestion en-têtes Excel à ligne 1 (ligne 0 = titres décorés)
✅ Support des références avec et sans parenthèses
✅ Références par défaut pour biomarqueurs courants
✅ Extraction robuste des 48 bactéries + groupes
✅ Détection graphique des positions d'abondance
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


# ✅ Références par défaut pour biomarqueurs courants
DEFAULT_REFERENCES = {
    "glycemie": "0.70 — 1.05",
    "glucose": "0.70 — 1.05",
    "cpk": "30 — 200",
    "c.p.k": "30 — 200",
    "c p k": "30 — 200",
    "ck": "30 — 200",
    "creatine kinase": "30 — 200",
    "creatinine kinase": "30 — 200",
    "ferritine": "15 — 150",
    "ferritin": "15 — 150",
    "crp": "0 — 5",
    "c-reactive protein": "0 — 5",
    "crp ultrasensible": "0 — 3",
    "crp ultra": "0 — 3",
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
    """Cherche une référence par défaut pour un biomarqueur"""
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
    
    Supporte 3 formats:
    1. Français avec parenthèses: "GLUCOSE 5.2 g/L (0.70 - 1.05)"
    2. Français sans parenthèses: "GLUCOSE 5.2 g/L 0.70 - 1.05"
    3. Belge: "GLUCOSE 5.2 0.70 - 1.05 g/L"
    4. Fallback: Références par défaut
    """
    if progress:
        progress.update(5, "Lecture PDF biologie...")
    
    text = _read_pdf_text(pdf_path)
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    out = {}
    
    if progress:
        progress.update(15, "Parsing biomarqueurs...")

    # Pattern 1: Français avec parenthèses
    pat_fr_parens = re.compile(
        r"^(?P<n>[A-ZÀ-Ÿ0-9\.\-\/\s]{3,60})\s+"
        r"(?P<value>[<>]?\s*[\+\-]?\s*\d+(?:[.,]\d+)?)\s*"
        r"(?P<unit>[a-zA-ZµμÎ¼/%]+(?:\s*[a-zA-ZµμÎ¼/%]+)?)?\s*"
        r"\((?P<ref>[^)]+)\)",
        flags=re.UNICODE,
    )

    # Pattern 2: Français sans parenthèses
    pat_fr_no_parens = re.compile(
        r"^(?P<n>[A-ZÀ-Ÿ0-9\.\-\/\s]{3,60})\s+"
        r"(?P<value>[<>]?\s*[\+\-]?\s*\d+(?:[.,]\d+)?)\s+"
        r"(?P<unit>[a-zA-ZµμÎ¼/%]+(?:\s*[a-zA-ZµμÎ¼/%]+)?)?\s+"
        r"(?P<ref>\d+(?:[.,]\d+)?\s*[-—–]\s*\d+(?:[.,]\d+)?)",
        flags=re.UNICODE,
    )

    # Pattern 3: Belge
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

        # Essai 1: Belge
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

        # Essai 2: Français AVEC parenthèses
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

        # Essai 3: Français SANS parenthèses
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
            continue

    # Fallback: Ajouter références par défaut si manquantes
    for biomarker_name, data in out.items():
        if not data.get("reference") or data.get("reference") == "":
            default_ref = _get_default_reference(biomarker_name)
            if default_ref:
                data["reference"] = default_ref
                data["status"] = determine_biomarker_status(
                    data.get("value"), 
                    default_ref, 
                    biomarker_name
                )

    if progress:
        progress.update(30, f"Biologie: {len(out)} biomarqueurs")
    
    return out


def _extract_bacterial_groups_v2(text):
    """Extraction des 12 groupes bactériens standards"""
    
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
    
    # Extraction séquentielle
    result_pattern = r'Result:\s*(expected|slightly\s+deviating|deviating)\s+abundance'
    result_matches = list(re.finditer(result_pattern, text, re.IGNORECASE))
    
    if len(result_matches) == len(STANDARD_GROUPS):
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
        # Recherche individuelle
        for group_code, group_name in STANDARD_GROUPS:
            group_status = 'Expected'
            
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
            
            groups.append({
                'category': group_code,
                'name': group_name,
                'abundance': group_status
            })
    
    return groups


def _extract_dots_from_pdf_page(page):
    """Extrait les positions des points noirs"""
    try:
        dots = []
        
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
        
        if hasattr(page, 'rects') and len(dots) == 0:
            for rect in page.rects:
                if 'x0' in rect and 'y0' in rect and 'x1' in rect and 'y1' in rect:
                    width = abs(rect['x1'] - rect['x0'])
                    height = abs(rect['y1'] - rect['y0'])
                    
                    if 2 < width < 10 and 2 < height < 10:
                        center_x = (rect['x0'] + rect['x1']) / 2
                        center_y = (rect['y0'] + rect['y1']) / 2
                        
                        dots.append({
                            'x': center_x,
                            'y': center_y,
                            'type': 'rect'
                        })
        
        dots.sort(key=lambda d: d['y'])
        
        if dots:
            x_positions = [d['x'] for d in dots]
            x_min = min(x_positions)
            x_max = max(x_positions)
            
            col_width = (x_max - x_min) / 6 if x_max > x_min else 1
            
            for dot in dots:
                x_rel = dot['x'] - x_min
                col_index = int(x_rel / col_width) if col_width > 0 else 3
                abundance_level = col_index - 3
                abundance_level = max(-3, min(3, abundance_level))
                dot['abundance_level'] = abundance_level
        
        return dots
    
    except Exception:
        return []


def _map_abundance_to_status(abundance_level):
    """Convertit niveau d'abondance en statut"""
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
    else:
        return "Strongly Elevated"


def extract_idk_microbiome(pdf_path, excel_path=None, enable_graphical_detection=True,
                          resolution=200, progress=None):
    """
    Extrait les données microbiome depuis rapport IDK® GutMAP
    
    Returns:
        dict: {
            'dysbiosis_index', 'dysbiosis_text', 'diversity',
            'bacteria_groups' (12 groupes),
            'bacteria_individual' (48 bactéries),
            'metabolites'
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
    
    # Dysbiosis Index
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
    
    # Diversity
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
    
    # Groupes bactériens
    bacteria_groups = _extract_bacterial_groups_v2(text)
    
    # Bactéries individuelles
    bacteria_individual = []
    bacteria_pattern = re.compile(r'^\s*(\d{3})\s+([A-Za-z\[\]\s\.\-\&]+?)(?:\s+Group|\s*$)', re.MULTILINE)
    
    bacteria_order = []
    seen_ids = set()
    
    current_category = None
    current_group_code = None
    current_group_name = None
    
    for line in lines:
        line_strip = line.strip()
        
        cat_match = re.match(r'Category\s+([A-E])\.\s+(.+)', line_strip, re.IGNORECASE)
        if cat_match:
            current_category = cat_match.group(1).upper()
            continue
        
        group_match = re.match(r'([A-E]\d+)\.\s+([A-Za-z\s]{3,40})', line_strip, re.IGNORECASE)
        if group_match:
            current_group_code = group_match.group(1).upper()
            current_group_name = group_match.group(2).strip()
            
            for grp in bacteria_groups:
                if grp['category'] == current_group_code:
                    current_group_name = grp['name']
                    break
            continue
        
        bact_match = bacteria_pattern.match(line_strip)
        if bact_match:
            bacteria_id = bact_match.group(1)
            bacteria_name = bact_match.group(2).strip()
            
            if len(bacteria_name) < 5 or bacteria_id in seen_ids:
                continue
            seen_ids.add(bacteria_id)
            
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
    
    # Détection graphique
    all_dots = []
    
    if enable_graphical_detection:
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num in range(len(pdf.pages)):
                    page = pdf.pages[page_num]
                    page_text = page.extract_text() or ""
                    
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
        
        except Exception:
            pass
    
    # Mapping
    for i, bact in enumerate(bacteria_order):
        if i < len(all_dots):
            dot = all_dots[i]
            abundance_level = dot.get('abundance_level', 0)
            status = _map_abundance_to_status(abundance_level)
        else:
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
    
    # Métabolites
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
    
    # ===== STOOL BIOMARKERS depuis l'Excel companion =====
    # L'excel_path contient la feuille "Biomarqueurs Base" avec calprotectine, histamine, etc.
    # On l'extrait ici et on recalcule le statut via determine_biomarker_status.
    stool_biomarkers = {}
    if excel_path:
        try:
            excel_result = extract_microbiome_from_excel(excel_path)
            raw_stool = excel_result.get("stool_biomarkers", {})
            for bm_name, bm_data in raw_stool.items():
                raw_value = bm_data.get("value")
                raw_ref   = str(bm_data.get("reference", ""))
                computed  = determine_biomarker_status(raw_value, raw_ref, bm_name)
                stool_biomarkers[bm_name] = {
                    "value":     raw_value,
                    "unit":      bm_data.get("unit", ""),
                    "reference": raw_ref,
                    "status":    computed if computed != "Inconnu" else bm_data.get("status", "Normal")
                }
        except Exception:
            pass

    if progress:
        progress.update(100, "Extraction terminée")
    
    return {
        "dysbiosis_index":    di,
        "dysbiosis_text":     di_text,
        "diversity":          diversity,
        "diversity_metrics":  diversity_metrics if diversity_metrics else None,
        "bacteria_individual": bacteria_individual,
        "bacteria_groups":    bacteria_groups,
        "metabolites":        metabolites if metabolites else None,
        "stool_biomarkers":   stool_biomarkers
    }


def extract_biology_from_excel(excel_path, progress=None):
    """Extrait biomarqueurs depuis Excel.
    ✅ FIX v18.2: Détection automatique de la ligne d'en-tête.
    Supporte les fichiers avec un titre fusionné en ligne 1
    (en-têtes réels en ligne 2, donc skiprows=1).
    """
    
    def _detect_columns(df):
        """Cherche les colonnes utiles dans un DataFrame, retourne (col_name, col_value, col_unit, col_ref)."""
        col_name = col_value = col_unit = col_ref = None
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
        return col_name, col_value, col_unit, col_ref
    
    try:
        if progress:
            progress.update(10, "Lecture Excel...")
        
        # Tentative 1 : header en ligne 1 (standard)
        df = pd.read_excel(excel_path)
        col_name, col_value, col_unit, col_ref = _detect_columns(df)
        
        # Tentative 2 : header en ligne 2 (ligne 1 = titre décoratif/fusionné)
        if not col_name or not col_value:
            df = pd.read_excel(excel_path, skiprows=1)
            col_name, col_value, col_unit, col_ref = _detect_columns(df)
        
        # Tentative 3 : header en ligne 3 (double titre)
        if not col_name or not col_value:
            df = pd.read_excel(excel_path, skiprows=2)
            col_name, col_value, col_unit, col_ref = _detect_columns(df)
        
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


# ✅ ✨ NOUVELLE FONCTION: Extraction microbiome depuis Excel
def extract_microbiome_from_excel(excel_path: str) -> Dict[str, Any]:
    """
    ✨ NOUVEAU: Extrait microbiome depuis fichier Excel structuré
    ✅ CORRIGÉ: Gestion en-têtes à ligne 1 (ligne 0 = titres décorés)
    
    Format attendu (comme Analyse_Microbiome_00484.xlsx):
    - Feuille "Informations Patient": DI, diversité
    - Feuille "Biomarqueurs Base": Calprotectine, sIgA, etc.
    - Feuille "Microbiome Détaillé": 48 bactéries
    - Feuille "Résumé Catégories": vue d'ensemble
    
    Returns:
        dict: Compatible avec extract_idk_microbiome
    """
    
    try:
        excel_file = pd.ExcelFile(excel_path)
        sheet_names = excel_file.sheet_names
        
        result = {
            "dysbiosis_index": None,
            "dysbiosis_text": "Unknown",
            "diversity": None,
            "diversity_metrics": None,
            "bacteria_groups": [],
            "bacteria_individual": [],
            "metabolites": None,
            "stool_biomarkers": {}
        }
        
        # ===== 1. INFORMATIONS PATIENT =====
        if "Informations Patient" in sheet_names:
            # ✅ CORRECTION: skiprows=1 pour ignorer titre, header=None pour indices numériques
            df_info = pd.read_excel(excel_file, "Informations Patient", skiprows=1, header=None)
            
            for _, row in df_info.iterrows():
                # Utiliser indices numériques [0] et [1]
                champ = str(row[0]) if 0 in row.index else ""
                valeur = str(row[1]) if 1 in row.index else ""
                
                # Ignorer les lignes vides ou en-têtes
                if pd.isna(champ) or champ == "nan" or not champ.strip() or champ.lower() == "champ":
                    continue
                
                champ_lower = champ.lower()
                
                # Dysbiosis Index
                if "dysbiosis" in champ_lower or "dysbiose" in champ_lower:
                    import re
                    match = re.search(r'(\d+)', valeur)
                    if match:
                        di = int(match.group(1))
                        result["dysbiosis_index"] = di
                        
                        if di <= 2:
                            result["dysbiosis_text"] = "Normobiotic (DI 1-2)"
                        elif di == 3:
                            result["dysbiosis_text"] = "Mildly dysbiotic (DI 3)"
                        else:
                            result["dysbiosis_text"] = "Severely dysbiotic (DI 4-5)"
                
                # Diversity
                if "diversit" in champ_lower:
                    result["diversity"] = valeur
        
        # ===== 2. BIOMARQUEURS BASE =====
        if "Biomarqueurs Base" in sheet_names:
            # ✅ CORRECTION: skiprows=1 pour ignorer titre, header=None pour indices numériques
            df_bio = pd.read_excel(excel_file, "Biomarqueurs Base", skiprows=1, header=None)
            
            for _, row in df_bio.iterrows():
                # Utiliser indices numériques [0]=Bio, [1]=Valeur, [2]=Unité, [3]=Référence, [4]=Statut
                biomarker = str(row[0]) if 0 in row.index else ""
                
                if not biomarker or biomarker == "nan" or pd.isna(biomarker) or biomarker.lower() == "biomarqueur":
                    continue
                
                raw_value = row[1] if 1 in row.index else None
                raw_ref = str(row[3]) if 3 in row.index else ""
                computed_status = determine_biomarker_status(raw_value, raw_ref, biomarker)
                result["stool_biomarkers"][biomarker] = {
                    "value": raw_value,
                    "unit": str(row[2]) if 2 in row.index else "",
                    "reference": raw_ref,
                    "status": computed_status if computed_status != "Inconnu" else (str(row[4]) if 4 in row.index else "Normal")
                }
        
        # ===== 3. MICROBIOME DÉTAILLÉ =====
        if "Microbiome Détaillé" in sheet_names:
            # ✅ CORRECTION: skiprows=1 pour ignorer titre, header=None pour indices numériques
            df_micro = pd.read_excel(excel_file, "Microbiome Détaillé", skiprows=1, header=None)
            
            categories_map = {}
            
            for _, row in df_micro.iterrows():
                # Indices: [0]=Catégorie, [1]=Groupe, [2]=No., [3]=Bactérie, [4]=Position, [5]=Statut, [6]=Interprétation
                category = str(row[0]) if 0 in row.index else ""
                groupe = str(row[1]) if 1 in row.index else ""
                no = str(row[2]) if 2 in row.index else ""
                bacterie = str(row[3]) if 3 in row.index else ""
                position = row[4] if 4 in row.index else 0
                statut = str(row[5]) if 5 in row.index else "Normal"
                
                # Ignorer en-têtes et lignes vides
                if not category or category == "nan" or pd.isna(category) or category.lower() == "catégorie":
                    continue
                
                # ✅ IMPORTANT: Dans l'Excel:
                # - "Catégorie" = nom long (ex: "A. Broad commensals")
                # - "Groupe" = code court (ex: "A1")
                # On inverse pour correspondre au format attendu
                group_code = groupe  # "A1"
                group_name = category  # "A. Broad commensals"
                
                if group_code not in categories_map:
                    categories_map[group_code] = {
                        "category": group_code,  # "A1"
                        "group": group_name,  # "A. Broad commensals"
                        "bacteria_count": 0,
                        "normal_count": 0,
                        "abnormal_count": 0,
                        "bacteria": []
                    }
                
                cat_info = categories_map[group_code]
                cat_info["bacteria_count"] += 1
                
                try:
                    position = int(position)
                except:
                    position = 0
                
                if position == 0:
                    cat_info["normal_count"] += 1
                else:
                    cat_info["abnormal_count"] += 1
                
                abundance_level = position
                
                if abundance_level <= -2:
                    status = "Strongly Reduced"
                elif abundance_level == -1:
                    status = "Reduced"
                elif abundance_level == 0:
                    status = "Normal"
                elif abundance_level == 1:
                    status = "Slightly Elevated"
                elif abundance_level == 2:
                    status = "Elevated"
                else:
                    status = "Strongly Elevated"
                
                result["bacteria_individual"].append({
                    "id": no,
                    "name": bacterie,
                    "category": group_code,  # "A1" au lieu de "A. Broad commensals"
                    "group": group_name,  # "A. Broad commensals"
                    "abundance_level": abundance_level,
                    "status": status
                })
            
            # Générer bacteria_groups à partir des catégories
            for cat_code, cat_info in categories_map.items():
                if cat_info["abnormal_count"] == 0:
                    group_result = "Expected"
                elif cat_info["abnormal_count"] <= cat_info["bacteria_count"] * 0.3:
                    group_result = "Slightly Deviating"
                else:
                    group_result = "Deviating"
                
                result["bacteria_groups"].append({
                    "category": cat_code,
                    "name": cat_info["group"],
                    "abundance": group_result,
                    "result": group_result
                })
        
        return result
    
    except Exception as e:
        print(f"❌ Erreur extraction Excel microbiome: {e}")
        import traceback
        traceback.print_exc()
        return {
            "dysbiosis_index": None,
            "dysbiosis_text": "Unknown",
            "diversity": None,
            "bacteria_groups": [],
            "bacteria_individual": [],
            "metabolites": None
        }


def biology_dict_to_list(biology, default_category="Autres"):
    """Convertit dictionnaire biologie en liste"""
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
    """Fonction principale d'extraction"""
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
    elif micro_excel_path:
        # ✅ ✨ NOUVEAU: Support Excel seul pour microbiome
        microbiome = extract_microbiome_from_excel(micro_excel_path)
    
    if progress:
        progress.update(100, "Terminé!")
    
    return biology, microbiome
