"""
UNILABS / ALGO-LIFE - Extractors v11.2 - FIXED
✅ Barre de progression corrigée
✅ Pas d'erreur de syntaxe
✅ Compatible Streamlit
"""

from __future__ import annotations

import os
import re
import sys
import unicodedata
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd

# Import conditionnel
try:
    import numpy as np
    from PIL import Image
    GRAPHICAL_AVAILABLE = True
except ImportError:
    GRAPHICAL_AVAILABLE = False
    np = None


# =====================================================================
# SYSTÈME DE PROGRESSION
# =====================================================================
class ProgressTracker:
    """Gestionnaire de barre de progression"""
    
    def __init__(self, total_steps: int = 100, show_bar: bool = True):
        self.total_steps = total_steps
        self.current_step = 0
        self.show_bar = show_bar
        self.current_task = ""
    
    def update(self, step: int, task: str = ""):
        """Met à jour la progression"""
        self.current_step = min(step, self.total_steps)
        self.current_task = task
        
        if self.show_bar:
            self._render()
    
    def _render(self):
        """Affiche la barre"""
        percent = int((self.current_step / self.total_steps) * 100)
        bar_length = 40
        filled = int((percent / 100) * bar_length)
        bar = "█" * filled + "░" * (bar_length - filled)
        
        sys.stdout.write(f"\r🔄 [{bar}] {percent}% - {self.current_task}")
        sys.stdout.flush()
        
        if self.current_step >= self.total_steps:
            sys.stdout.write("\n")
            sys.stdout.flush()


# =====================================================================
# NORMALISATION
# =====================================================================
def normalize_biomarker_name(name: str) -> str:
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
    s = s.replace("C P K", "CPK")
    s = s.replace("L D L", "LDL")
    s = s.replace("H D L", "HDL")
    s = s.replace("V G M", "VGM")
    s = s.replace("T C M H", "TCMH")
    s = s.replace("C C M H", "CCMH")
    s = s.replace("C R P", "CRP")
    s = s.replace("T S H", "TSH")
    s = s.replace("D F G", "DFG")
    s = s.replace("G P T", "GPT")
    s = s.replace("G O T", "GOT")
    return s


def _safe_float(x) -> Optional[float]:
    try:
        if x is None:
            return None
        s = str(x).strip().replace(",", ".")
        s = re.sub(r"[^0-9\.\-\+eE]", "", s)
        return float(s) if s else None
    except Exception:
        return None


def _clean_ref(ref: str) -> str:
    if ref is None:
        return ""
    r = str(ref).strip()
    r = r.replace("—", "-").replace("–", "-")
    r = re.sub(r"\s+", " ", r)
    return r


def determine_biomarker_status(value, reference, biomarker_name=None) -> str:
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


# =====================================================================
# PDF TEXT LOADER
# =====================================================================
def _read_pdf_text(pdf_path: str) -> str:
    try:
        import pdfplumber
    except ImportError as e:
        raise ImportError("pdfplumber manquant") from e
    chunks = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            chunks.append(page.extract_text() or "")
    return "\n".join(chunks)


# =====================================================================
# BIOLOGIE
# =====================================================================
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


def _is_noise_line(line: str) -> bool:
    if not line:
        return True
    s = line.strip()
    if len(s) < 4:
        return True
    for pat in _IGNORE_PATTERNS:
        if re.search(pat, s, flags=re.IGNORECASE):
            return True
    return False


def extract_synlab_biology(pdf_path: str, progress: Optional[ProgressTracker] = None) -> Dict[str, Any]:
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
        r"(?P<unit>[A-Za-zµμÎ¼/%]+(?:\s*[A-Za-zµμÎ¼/%]+)?)\s*$",
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
        progress.update(30, f"Biologie: {len(out)} extraits")
    
    return out


# =====================================================================
# DÉTECTION GRAPHIQUE
# =====================================================================
def _find_connected_components(binary_image):
    if not GRAPHICAL_AVAILABLE:
        return None, 0
    
    height, width = binary_image.shape
    labeled = np.zeros_like(binary_image, dtype=int)
    label = 0
    
    def flood_fill(y, x, current_label):
        stack = [(y, x)]
        while stack:
            cy, cx = stack.pop()
            if cy < 0 or cy >= height or cx < 0 or cx >= width:
                continue
            if labeled[cy, cx] != 0 or not binary_image[cy, cx]:
                continue
            
            labeled[cy, cx] = current_label
            
            for dy in [-1, 0, 1]:
                for dx in [-1, 0, 1]:
                    if dy == 0 and dx == 0:
                        continue
                    stack.append((cy + dy, cx + dx))
    
    for y in range(height):
        for x in range(width):
            if binary_image[y, x] and labeled[y, x] == 0:
                label += 1
                flood_fill(y, x, label)
    
    return labeled, label


def _detect_abundance_dots_on_page(page, table_bbox=None, resolution=200):
    if not GRAPHICAL_AVAILABLE:
        return {}
    
    try:
        img = page.to_image(resolution=resolution)
        pil_img = img.original
        gray = pil_img.convert('L')
        arr = np.array(gray)
        
        if table_bbox is None:
            page_width = page.width
            page_height = page.height
            x0 = page_width * 0.15
            x1 = page_width * 0.85
            top = page_height * 0.20
            bottom = page_height * 0.80
        else:
            x0, top, x1, bottom = table_bbox
        
        scale = resolution / 72.0
        px0 = int(x0 * scale)
        px1 = int(x1 * scale)
        ptop = int(top * scale)
        pbottom = int(bottom * scale)
        
        table_region = arr[ptop:pbottom, px0:px1]
        dark_threshold = 80
        dark_pixels = table_region < dark_threshold
        num_columns = 7
        col_width = table_region.shape[1] / num_columns
        
        labeled, num_features = _find_connected_components(dark_pixels)
        
        if labeled is None:
            return {}
        
        results = {}
        
        for i in range(1, num_features + 1):
            blob_mask = (labeled == i)
            blob_coords = np.where(blob_mask)
            
            if len(blob_coords[0]) == 0:
                continue
            
            y_min, y_max = blob_coords[0].min(), blob_coords[0].max()
            x_min, x_max = blob_coords[1].min(), blob_coords[1].max()
            blob_height = y_max - y_min
            blob_width = x_max - x_min
            
            if not (3 < blob_height < 30 and 3 < blob_width < 30):
                continue
            
            blob_area = len(blob_coords[0])
            bounding_area = blob_height * blob_width
            if bounding_area == 0:
                continue
            fill_ratio = blob_area / bounding_area
            if fill_ratio < 0.5:
                continue
            
            y_center = np.mean(blob_coords[0])
            x_center = np.mean(blob_coords[1])
            
            col_index = int(x_center / col_width)
            col_index = max(0, min(6, col_index))
            abundance_level = col_index - 3
            
            row_index = int(y_center / 30)
            
            results[row_index] = abundance_level
        
        return results
    
    except Exception:
        return {}


def _map_abundance_to_status(abundance_level):
    if abundance_level is None:
        return "Unknown"
    if abundance_level < -1:
        return "Reduced"
    elif abundance_level > 1:
        return "Elevated"
    else:
        return "Normal"


def _map_group_abundance(bacteria_list):
    if not bacteria_list:
        return None
    
    levels = [b.get("abundance_level") for b in bacteria_list if b.get("abundance_level") is not None]
    if not levels:
        return None
    
    avg_level = sum(levels) / len(levels)
    
    if avg_level < -1:
        return "Reduced"
    elif avg_level > 1:
        return "Elevated"
    else:
        return "Normal"


# =====================================================================
# MICROBIOTE
# =====================================================================
def extract_idk_microbiome(pdf_path, excel_path=None, enable_graphical_detection=True, resolution=200, progress=None):
    try:
        import pdfplumber
    except ImportError as e:
        raise ImportError("pdfplumber manquant") from e
    
    if progress:
        progress.update(35, "Lecture PDF microbiome...")
    
    text = _read_pdf_text(pdf_path)
    
    if progress:
        progress.update(40, "Extraction DI...")
    
    # DI
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
    
    # Diversity
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
    
    # Bactéries
    bacteria_individual = []
    current_category = None
    current_group = None
    current_group_code = None
    
    lines = text.splitlines()
    bacteria_pattern = re.compile(r"^(\d{3})\s+([A-Za-z\[\]\(\)\.\-&,\s]+?)$")
    
    for idx, line in enumerate(lines):
        line_strip = line.strip()
        
        if progress and idx % 20 == 0:
            percent = 50 + int((idx / len(lines)) * 15)
            progress.update(percent, f"Parsing {idx}/{len(lines)}...")
        
        cat_match = re.match(r"Category\s+([A-E])\.\s+(.+)", line_strip, re.IGNORECASE)
        if cat_match:
            current_category = cat_match.group(1).upper()
            continue
        
        group_match = re.match(r"([A-E]\d)\.\s+(.+)", line_strip)
        if group_match:
            current_group_code = group_match.group(1).upper()
            current_group = group_match.group(2).strip()
        
        if re.match(r"Result:\s+", line_strip, re.IGNORECASE):
            continue
        
        bacteria_match = bacteria_pattern.match(line_strip)
        if bacteria_match:
            bacteria_id = bacteria_match.group(1)
            bacteria_name = bacteria_match.group(2).strip()
            
            if len(bacteria_name) < 5:
                continue
            
            bacteria_info = {
                "id": bacteria_id,
                "name": bacteria_name,
                "category": current_group_code or current_category or "Unknown",
                "group": current_group or "",
                "abundance_level": None,
                "status": "Unknown"
            }
            bacteria_individual.append(bacteria_info)
    
    if progress:
        progress.update(65, f"{len(bacteria_individual)} bactéries")
    
    # Groupes
    if progress:
        progress.update(68, "Extraction groupes...")
    
    group_header = re.compile(r"(?m)^([A-Z]\d)\.\s+(.+?)\s*$")
    result_line = re.compile(r"Result:\s*(expected|slightly deviating|deviating)\s+abundance", flags=re.IGNORECASE)
    
    bacteria_groups = []
    current_code = None
    current_grp = None
    
    for ln in lines:
        ln = ln.strip()
        h = group_header.match(ln)
        if h:
            current_code = h.group(1).strip()
            current_grp = f"{current_code}. {h.group(2).strip()}"
            continue
        
        r = result_line.search(ln)
        if r and current_code and current_grp:
            raw = r.group(1).strip().lower()
            if raw == "expected":
                res = "Expected"
            elif raw == "slightly deviating":
                res = "Slightly deviating"
            else:
                res = "Deviating"
            
            bacteria_groups.append({
                "category": current_code,
                "group": current_grp,
                "result": res,
                "abundance": None
            })
    
    # Dédupliquer
    seen_groups = set()
    uniq_groups = []
    for b in bacteria_groups:
        key = (b["category"], b["group"], b["result"])
        if key in seen_groups:
            continue
        seen_groups.add(key)
        uniq_groups.append(b)
    
    if progress:
        progress.update(70, "Extraction métabolites...")
    
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
    
    # Détection graphique
    if enable_graphical_detection and GRAPHICAL_AVAILABLE:
        try:
            if progress:
                progress.update(75, "Analyse graphique...")
            
            with pdfplumber.open(pdf_path) as pdf:
                all_dots = {}
                num_pages = min(6, len(pdf.pages)) - 2
                
                for page_idx, page_num in enumerate(range(2, min(6, len(pdf.pages)))):
                    if progress:
                        page_percent = 75 + int((page_idx / num_pages) * 15)
                        progress.update(page_percent, f"Scan page {page_num + 1}...")
                    
                    page = pdf.pages[page_num]
                    page_dots = _detect_abundance_dots_on_page(page, None, resolution)
                    
                    for row_idx, abundance in page_dots.items():
                        global_idx = (page_num - 2) * 50 + row_idx
                        all_dots[global_idx] = abundance
                
                if progress:
                    progress.update(90, f"{len(all_dots)} points détectés")
                
                sorted_dots = sorted(all_dots.items())
                
                for i, bacteria in enumerate(bacteria_individual):
                    if i < len(sorted_dots):
                        _, abundance_level = sorted_dots[i]
                        bacteria["abundance_level"] = abundance_level
                        bacteria["status"] = _map_abundance_to_status(abundance_level)
                
                for group in uniq_groups:
                    group_code = group["category"]
                    group_bacteria = [b for b in bacteria_individual if b["category"] == group_code]
                    group["abundance"] = _map_group_abundance(group_bacteria)
                
                if progress:
                    progress.update(95, "Analyse terminée")
        
        except Exception as e:
            if progress:
                progress.update(95, "Analyse graphique échouée")
    
    elif enable_graphical_detection and not GRAPHICAL_AVAILABLE:
        if progress:
            progress.update(95, "Détection désactivée")
    
    if progress:
        progress.update(100, "Extraction terminée")
    
    return {
        "dysbiosis_index": di,
        "diversity": diversity,
        "diversity_metrics": diversity_metrics if diversity_metrics else None,
        "bacteria_individual": bacteria_individual,
        "bacteria_groups": uniq_groups,
        "metabolites": metabolites if metabolites else None
    }


# =====================================================================
# EXCEL
# =====================================================================
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


# =====================================================================
# ORCHESTRATEUR
# =====================================================================
def extract_all_data(bio_pdf_path=None, bio_excel_path=None, micro_pdf_path=None, micro_excel_path=None, enable_graphical_detection=True, show_progress=True):
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
        microbiome = extract_idk_microbiome(micro_pdf_path, micro_excel_path, enable_graphical_detection, 200, progress)
    
    if progress:
        progress.update(100, "Terminé!")
    
    return biology, microbiome


# =====================================================================
# TEST
# =====================================================================
if __name__ == "__main__":
    import json
    
    print("="*80)
    print("🧪 TEST v11.2 FIXED")
    print("="*80)
    print()
    
    pdf_path = "/mnt/user-data/uploads/IDK_GutMAP_Sample_report_DI-1_EN.pdf"
    
    if os.path.exists(pdf_path):
        progress = ProgressTracker(total_steps=100, show_bar=True)
        result = extract_idk_microbiome(pdf_path, None, True, 200, progress)
        
        print(f"\n📊 RÉSULTATS:")
        print(f"  • DI: {result['dysbiosis_index']}")
        print(f"  • Diversity: {result['diversity']}")
        print(f"  • Bactéries: {len(result['bacteria_individual'])}")
        
        with_abundance = sum(1 for b in result['bacteria_individual'] if b['abundance_level'] is not None)
        print(f"  • Avec abondance: {with_abundance}/{len(result['bacteria_individual'])}")
        
        output = "/mnt/user-data/outputs/microbiome_v11_2_fixed.json"
        with open(output, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Sauvegardé: {output}")
    else:
        print(f"\n❌ Fichier non trouvé")
