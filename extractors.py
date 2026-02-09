"""
UNILABS / ALGO-LIFE - Extractors v13.0 COMPLETE
✅ Toutes les fonctions implémentées
✅ Détection vectorielle + fallback texte
✅ Compatible production Streamlit
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
    dots = []
    
    if not hasattr(page, 'curves'):
        return dots
    
    curves = page.curves
    page_width = page.width
    table_x_start = page_width * 0.30
    table_x_end = page_width * 0.80
    table_width = table_x_end - table_x_start
    col_width = table_width / 7
    
    for curve in curves:
        w = curve.get('width', 0)
        h = curve.get('height', 0)
        
        if not (5 < w < 10 and 5 < h < 10):
            continue
        
        x = curve.get('x0', 0)
        y = curve.get('top', 0)
        
        if not (table_x_start < x < table_x_end):
            continue
        
        relative_x = x - table_x_start
        col_index = int(relative_x / col_width)
        col_index = max(0, min(6, col_index))
        abundance_level = col_index - 3
        
        dots.append({
            'y': y,
            'x': x,
            'abundance_level': abundance_level
        })
    
    dots.sort(key=lambda d: d['y'])
    
    unique_dots = []
    last_y = None
    for dot in dots:
        if last_y is None or abs(dot['y'] - last_y) > 5:
            unique_dots.append(dot)
            last_y = dot['y']
    
    return unique_dots


def _map_abundance_to_status(abundance_level):
    if abundance_level is None:
        return "Unknown"
    if abundance_level <= -2:
        return "Reduced"
    elif abundance_level >= 2:
        return "Elevated"
    elif abundance_level == -1:
        return "Slightly Reduced"
    elif abundance_level == 1:
        return "Slightly Elevated"
    else:
        return "Normal"


def _map_group_result_to_abundance(result_text):
    result_lower = result_text.lower().strip()
    
    if "expected" in result_lower:
        return "Normal"
    elif "slightly deviating" in result_lower:
        return "Slightly Deviating"
    elif "deviating" in result_lower:
        return "Deviating"
    else:
        return "Unknown"


def extract_idk_microbiome(pdf_path, excel_path=None, enable_graphical_detection=True, 
                          resolution=200, progress=None):
    try:
        import pdfplumber
    except ImportError as e:
        raise ImportError("pdfplumber manquant") from e
    
    if progress:
        progress.update(35, "Lecture PDF microbiome...")
    
    text = _read_pdf_text(pdf_path)
    
    if progress:
        progress.update(40, "Extraction DI...")
    
    di = None
    m_di = re.search(r"(?:DI|Dysbiosis\s+index)\s*[:\-]?\s*([1-5])", text, flags=re.IGNORECASE)
    if m_di:
        di = int(m_di.group(1))
    else:
        m = re.search(r"Result:\s*The microbiota is\s+([A-Za-z\- ]+)", text, flags=re.IGNORECASE)
        if m:
            label = m.group(1).strip().lower()
            if "normobiotic" in label:
                di = 1
            elif "mild" in label:
                di = 3
            elif "sever" in label or "severe" in label:
                di = 5
            elif "moderate" in label:
                di = 3
    
    if progress:
        progress.update(45, "Extraction Diversity...")
    
    diversity = None
    md = re.search(r"Result:\s*The bacterial diversity is\s+([A-Za-z\- ]+)", text, flags=re.IGNORECASE)
    if md:
        diversity = md.group(1).strip()
    
    diversity_metrics = {}
    m_shannon = re.search(r"Shannon[:\s]+(\d+(?:\.\d+)?)", text, flags=re.IGNORECASE)
    if m_shannon:
        diversity_metrics["shannon"] = _safe_float(m_shannon.group(1))
    m_simpson = re.search(r"Simpson[:\s]+(\d+(?:\.\d+)?)", text, flags=re.IGNORECASE)
    if m_simpson:
        diversity_metrics["simpson"] = _safe_float(m_simpson.group(1))
    
    if progress:
        progress.update(50, "Extraction bactéries...")
    
    lines = text.splitlines()

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
    
    bacteria_groups = []
    found_groups = {}
    
    group_pattern = re.compile(r"^([A-E]\d)\.\s+(.+?)$")
    # PATCH: tolère "slightly" + "deviating" split sur 2 lignes via buffer
    result_pattern_en = re.compile(
        r"Result:\s*(expected|deviating|slightly\s+deviating)(?:\s+abundance)?",
        flags=re.IGNORECASE
    )
    result_pattern_de = re.compile(
        r"Ergebnis:\s*(erwartete|leicht\s+abweichende|abweichende)\s+Abundanz",
        flags=re.IGNORECASE
    )
    
    current_category = None
    current_group_code = None
    current_group_name = None
    
    # =========================
    # PATCH: scan avec buffer 2 lignes
    # =========================
    for i, line in enumerate(lines):
        line_strip = (line or "").strip()
        nxt = (lines[i + 1] if i + 1 < len(lines) else "").strip()
        buf = (line_strip + " " + nxt).strip()

        # PATCH: category peut être sur line ou buf
        cat_match = re.match(r"(?:Category\s+)?([A-E])\.\s+(.+)", line_strip, re.IGNORECASE)
        if not cat_match:
            cat_match = re.match(r"(?:Category\s+)?([A-E])\.\s+(.+)", buf, re.IGNORECASE)
        if cat_match:
            current_category = cat_match.group(1).upper()
            continue
        
        # PATCH: groupe peut être split sur 2 lignes
        grp_match = group_pattern.match(line_strip)
        if not grp_match:
            grp_match = group_pattern.match(buf)
        if grp_match:
            current_group_code = grp_match.group(1).upper()
            full_name = grp_match.group(2).strip()
            current_group_name = full_name[:50] if len(full_name) > 50 else full_name
            found_groups[current_group_code] = True
            continue
        
        # PATCH: résultat peut être split -> on teste sur buf
        res_match = result_pattern_en.search(buf)
        if not res_match:
            res_match = result_pattern_de.search(buf)
        
        if res_match and current_group_code:
            result_text = res_match.group(1).strip()
            
            # Mapper allemand → anglais
            de_to_en = {
                'erwartete': 'Expected',
                'leicht abweichende': 'Slightly deviating',
                'abweichende': 'Deviating'
            }
            result_text = de_to_en.get(result_text, result_text.capitalize())
            abundance = _map_group_result_to_abundance(result_text)
            
            bacteria_groups.append({
                "category": current_group_code,
                "group": f"{current_group_code}. {current_group_name}",
                "result": result_text.capitalize(),
                "abundance": abundance,
                "has_explicit_result": True
            })
            found_groups[current_group_code] = "processed"
    
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
    
    # =========================
    # PATCH: idem buffer 2 lignes pour le parsing des bactéries
    # =========================
    for i, line in enumerate(lines):
        line_strip = (line or "").strip()
        nxt = (lines[i + 1] if i + 1 < len(lines) else "").strip()
        buf = (line_strip + " " + nxt).strip()

        cat_match = re.match(r"(?:Category\s+)?([A-E])\.\s+(.+)", line_strip, re.IGNORECASE)
        if not cat_match:
            cat_match = re.match(r"(?:Category\s+)?([A-E])\.\s+(.+)", buf, re.IGNORECASE)
        if cat_match:
            current_category = cat_match.group(1).upper()
            continue
        
        grp_match = group_pattern.match(line_strip)
        if not grp_match:
            grp_match = group_pattern.match(buf)
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
                # PATCH: scanner toutes les pages (le GutMAP peut être >5 pages)
                for page_num in range(len(pdf.pages)):
                    page = pdf.pages[page_num]
                    page_dots = _extract_dots_vectorial(page)
                    all_dots.extend(page_dots)
                
                if progress:
                    progress.update(75, f"{len(all_dots)} points détectés")
        except Exception:
            if progress:
                progress.update(75, f"Détection échouée")
    
    for i, bact in enumerate(bacteria_order):
        if i < len(all_dots):
            dot = all_dots[i]
            abundance_level = dot['abundance_level']
            status = _map_abundance_to_status(abundance_level)
        else:
            group_abund = bact.get("group_abundance", "Normal")
            if group_abund == "Normal":
                abundance_level = 0
                status = "Normal"
            elif group_abund == "Slightly Deviating":
                abundance_level = None
                status = "Slightly Deviating"
            else:
                abundance_level = None
                status = "Unknown"
        
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
