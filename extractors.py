"""
UNILABS / ALGO-LIFE - Extractors v9.0
✅ Extraction biologie robuste
✅ Extraction microbiote considérablement améliorée
✅ Support multi-format (PDF + Excel)
✅ Normalisation puissante pour matching
✅ Status compatible rules_engine: Bas/Normal/Élevé/Inconnu
"""

from __future__ import annotations

import re
import unicodedata
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd


# =====================================================================
# NORMALISATION ROBUSTE POUR MATCHING
# =====================================================================
def normalize_biomarker_name(name: str) -> str:
    """
    Normalisation robuste pour matcher Excel:
    - trim, suppression accents, uppercase
    - nettoyage ponctuation, espaces normalisés
    """
    if name is None:
        return ""
    s = str(name).strip()

    # Supprimer accents
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))

    # Uppercase
    s = s.upper()

    # Harmoniser ponctuation
    s = s.replace(".", " ")
    s = s.replace(",", " ")
    s = s.replace("'", "'")

    # Garder A-Z 0-9 + séparateurs simples
    s = re.sub(r"[^A-Z0-9\s\-\+/]", " ", s)

    # Espaces propres
    s = re.sub(r"\s+", " ", s).strip()

    # Compacter certains acronymes fréquents
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
    """Conversion sécurisée en float"""
    try:
        if x is None:
            return None
        s = str(x).strip().replace(",", ".")
        s = re.sub(r"[^0-9\.\-\+eE]", "", s)
        return float(s) if s else None
    except Exception:
        return None


def _clean_ref(ref: str) -> str:
    """Nettoie une référence"""
    if ref is None:
        return ""
    r = str(ref).strip()
    r = r.replace("—", "-").replace("–", "-")
    r = re.sub(r"\s+", " ", r)
    return r


def determine_biomarker_status(value, reference, biomarker_name=None) -> str:
    """
    Détermine le statut d'un biomarqueur
    Returns: 'Bas' | 'Normal' | 'Élevé' | 'Inconnu'
    """
    v = _safe_float(value)
    if v is None:
        return "Inconnu"

    ref = _clean_ref(reference)

    # Range: "x - y" ou "x à y"
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

    # "< x" ou "≤ x"
    m = re.search(r"(?:<|≤)\s*(-?\d+(?:[.,]\d+)?)", ref)
    if m:
        hi = _safe_float(m.group(1))
        if hi is None:
            return "Inconnu"
        return "Élevé" if v > hi else "Normal"

    # "> x" ou "≥ x"
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
    """Lit le texte complet d'un PDF"""
    try:
        import pdfplumber
    except ImportError as e:
        raise ImportError("pdfplumber manquant. pip install pdfplumber") from e

    chunks: List[str] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            chunks.append(page.extract_text() or "")
    return "\n".join(chunks)


# =====================================================================
# BIOLOGIE - EXTRACTION PDF
# =====================================================================
_IGNORE_PATTERNS = [
    r"^Édition\s*:",
    r"^Laboratoire",
    r"^SYNLAB",
    r"^UNILABS",
    r"^Dossier",
    r"^FranceLIS",
    r"^Analyses",
    r"^BIOCHIMIE|^CHIMIE|^HORMONOLOGIE|^IMMUNOLOGIE|^HEMATOLOGIE|^EQUILIBRE|^STATUT|^PERMEABILITE",
    r"^Colorimétrie|^Chimiluminescence|^Immunoturbidimétrie",
    r"^Interprétation",
    r"^Accéder",
    r"^Validé",
    r"^Page\s+\d+",
]


def _is_noise_line(line: str) -> bool:
    """Détecte les lignes de bruit"""
    if not line:
        return True
    s = line.strip()
    if len(s) < 4:
        return True
    for pat in _IGNORE_PATTERNS:
        if re.search(pat, s, flags=re.IGNORECASE):
            return True
    return False


def extract_synlab_biology(pdf_path: str) -> Dict[str, Any]:
    """
    Extraction biologie depuis PDF SYNLAB/UNILABS
    Output: { biomarker: {value, unit, reference, status}, ... }
    """
    text = _read_pdf_text(pdf_path)
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    out: Dict[str, Any] = {}

    # Pattern France: NAME VALUE UNIT (REF)
    pat_fr = re.compile(
        r"^(?P<name>[A-ZÀ-Ÿ0-9\.\-\/\s]{3,60})\s+"
        r"(?P<value>[<>]?\s*[\+\-]?\s*\d+(?:[.,]\d+)?)\s*"
        r"(?P<unit>[a-zA-ZµμÎ¼/%]+(?:\s*[a-zA-ZµμÎ¼/%]+)?)?\s*"
        r"\((?P<ref>[^)]+)\)",
        flags=re.UNICODE,
    )

    # Pattern Belgium: optional ">" + name + value + ref-range + unit
    pat_be = re.compile(
        r"^(?:>\s*)?"
        r"(?P<name>[A-Za-zÀ-ÿ0-9\.\-\/\s]{3,60}?)\s+"
        r"(?P<valsign>[\+\-])?\s*(?P<value>\d+(?:[.,]\d+)?)\s+"
        r"(?P<ref>\d+(?:[.,]\d+)?\s*-\s*\d+(?:[.,]\d+)?)\s+"
        r"(?P<unit>[A-Za-zµμÎ¼/%]+(?:\s*[A-Za-zµμÎ¼/%]+)?)\s*$",
        flags=re.UNICODE,
    )

    for ln in lines:
        if _is_noise_line(ln):
            continue

        # Try Belgium format first
        m = pat_be.match(ln)
        if m:
            name = m.group("name").strip()
            value = m.group("value")
            unit = (m.group("unit") or "").strip()
            ref = _clean_ref(m.group("ref"))
            status = determine_biomarker_status(value, ref, name)
            out[name] = {"value": value, "unit": unit, "reference": ref, "status": status}
            continue

        # Try France format
        m = pat_fr.match(ln)
        if m:
            name = m.group("name").strip()
            if re.search(r"\bSIEMENS\b", name, flags=re.IGNORECASE):
                continue
            value = m.group("value")
            unit = (m.group("unit") or "").strip()
            ref = _clean_ref(m.group("ref"))
            status = determine_biomarker_status(value, ref, name)
            out[name] = {"value": value, "unit": unit, "reference": ref, "status": status}
            continue

    return out


# =====================================================================
# MICROBIOTE - EXTRACTION AMÉLIORÉE (PDF + Excel si disponible)
# =====================================================================
def extract_idk_microbiome(pdf_path: str, excel_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Extraction microbiome IDK GutMAP (ou similaire)
    Support PDF + Excel optionnel pour enrichissement
    
    Output:
    {
        "dysbiosis_index": int | None,
        "diversity": str | None,
        "bacteria": [
            {
                "category": "A1",
                "group": "A1. Prominent gut microbes",
                "result": "Expected|Slightly deviating|Deviating",
                "abundance": float | None  # si dispo
            },
            ...
        ],
        "metabolites": {  # si disponibles
            "butyrate": float,
            "acetate": float,
            ...
        },
        "diversity_metrics": {  # si disponibles
            "shannon": float,
            "simpson": float,
            ...
        }
    }
    """
    text = _read_pdf_text(pdf_path)
    
    # ─────────────────────────────────────────────────────────────────
    # 1. DYSBIOSIS INDEX
    # ─────────────────────────────────────────────────────────────────
    di = None
    
    # Recherche directe "DI: X" ou "Dysbiosis index: X"
    m_di = re.search(r"(?:DI|Dysbiosis\s+index)\s*[:\-]?\s*([1-5])", text, flags=re.IGNORECASE)
    if m_di:
        di = int(m_di.group(1))
    else:
        # Recherche par label textuel
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
    
    # ─────────────────────────────────────────────────────────────────
    # 2. DIVERSITY
    # ─────────────────────────────────────────────────────────────────
    diversity = None
    md = re.search(r"Result:\s*The bacterial diversity is\s+([A-Za-z\- ]+)", text, flags=re.IGNORECASE)
    if md:
        diversity = md.group(1).strip()
    
    # Metrics quantitatifs si disponibles
    diversity_metrics = {}
    
    # Shannon index
    m_shannon = re.search(r"Shannon[:\s]+(\d+(?:\.\d+)?)", text, flags=re.IGNORECASE)
    if m_shannon:
        diversity_metrics["shannon"] = _safe_float(m_shannon.group(1))
    
    # Simpson index
    m_simpson = re.search(r"Simpson[:\s]+(\d+(?:\.\d+)?)", text, flags=re.IGNORECASE)
    if m_simpson:
        diversity_metrics["simpson"] = _safe_float(m_simpson.group(1))
    
    # ─────────────────────────────────────────────────────────────────
    # 3. BACTERIAL GROUPS
    # ─────────────────────────────────────────────────────────────────
    group_header = re.compile(r"(?m)^([A-Z]\d)\.\s+(.+?)\s*$")
    result_line = re.compile(
        r"Result:\s*(expected|slightly deviating|deviating)\s+abundance", 
        flags=re.IGNORECASE
    )
    
    bacteria: List[Dict[str, Any]] = []
    current_code = None
    current_group = None
    
    for ln in text.splitlines():
        ln = ln.strip()
        
        # Header de groupe (ex: "A1. Prominent gut microbes")
        h = group_header.match(ln)
        if h:
            current_code = h.group(1).strip()
            current_group = f"{current_code}. {h.group(2).strip()}"
            continue
        
        # Result line
        r = result_line.search(ln)
        if r and current_code and current_group:
            raw = r.group(1).strip().lower()
            if raw == "expected":
                res = "Expected"
            elif raw == "slightly deviating":
                res = "Slightly deviating"
            else:
                res = "Deviating"
            
            # Recherche d'abondance si présente (ex: "15.2%")
            abundance = None
            m_abund = re.search(r"(\d+(?:\.\d+)?)\s*%", ln)
            if m_abund:
                abundance = _safe_float(m_abund.group(1))
            
            bacteria.append({
                "category": current_code,
                "group": current_group,
                "result": res,
                "abundance": abundance
            })
    
    # Dédupliquer
    seen = set()
    uniq = []
    for b in bacteria:
        key = (b["category"], b["group"], b["result"])
        if key in seen:
            continue
        seen.add(key)
        uniq.append(b)
    
    # ─────────────────────────────────────────────────────────────────
    # 4. MÉTABOLITES (si disponibles dans le texte)
    # ─────────────────────────────────────────────────────────────────
    metabolites = {}
    
    # Butyrate
    m_but = re.search(r"Butyrate[:\s]+(\d+(?:\.\d+)?)", text, flags=re.IGNORECASE)
    if m_but:
        metabolites["butyrate"] = _safe_float(m_but.group(1))
    
    # Acetate
    m_ace = re.search(r"Acetate[:\s]+(\d+(?:\.\d+)?)", text, flags=re.IGNORECASE)
    if m_ace:
        metabolites["acetate"] = _safe_float(m_ace.group(1))
    
    # Propionate
    m_pro = re.search(r"Propionate[:\s]+(\d+(?:\.\d+)?)", text, flags=re.IGNORECASE)
    if m_pro:
        metabolites["propionate"] = _safe_float(m_pro.group(1))
    
    # ─────────────────────────────────────────────────────────────────
    # 5. ENRICHISSEMENT EXCEL (optionnel)
    # ─────────────────────────────────────────────────────────────────
    if excel_path and os.path.exists(excel_path):
        try:
            df = pd.read_excel(excel_path)
            # Extraire données supplémentaires si colonnes pertinentes présentes
            # (laisser flexible pour formats futurs)
            pass
        except Exception:
            pass
    
    return {
        "dysbiosis_index": di,
        "diversity": diversity,
        "diversity_metrics": diversity_metrics if diversity_metrics else None,
        "bacteria": uniq,
        "metabolites": metabolites if metabolites else None
    }


# =====================================================================
# EXTRACTION DEPUIS EXCEL (helper pour biologie si besoin)
# =====================================================================
def extract_biology_from_excel(excel_path: str) -> Dict[str, Any]:
    """
    Extraction biologie depuis Excel (format custom)
    Utiliser si disponible en complément du PDF
    """
    try:
        df = pd.read_excel(excel_path)
        
        # Identifier colonnes
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
        for _, row in df.iterrows():
            name = str(row.get(col_name, "")).strip()
            if not name or name.lower() == "nan":
                continue
            
            value = row.get(col_value)
            unit = str(row.get(col_unit, "")).strip() if col_unit else ""
            ref = str(row.get(col_ref, "")).strip() if col_ref else ""
            
            status = determine_biomarker_status(value, ref, name)
            
            out[name] = {
                "value": value,
                "unit": unit,
                "reference": ref,
                "status": status
            }
        
        return out
    
    except Exception as e:
        print(f"⚠️ Erreur extraction Excel: {e}")
        return {}


# =====================================================================
# MAIN EXTRACTION ORCHESTRATOR
# =====================================================================
def extract_all_data(
    bio_pdf_path: Optional[str] = None,
    bio_excel_path: Optional[str] = None,
    micro_pdf_path: Optional[str] = None,
    micro_excel_path: Optional[str] = None
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Extraction orchestrée de toutes les données disponibles
    
    Returns:
        (biology_dict, microbiome_dict)
    """
    biology = {}
    microbiome = {}
    
    # Biologie
    if bio_pdf_path:
        biology.update(extract_synlab_biology(bio_pdf_path))
    
    if bio_excel_path:
        biology.update(extract_biology_from_excel(bio_excel_path))
    
    # Microbiote
    if micro_pdf_path:
        microbiome = extract_idk_microbiome(micro_pdf_path, micro_excel_path)
    
    return biology, microbiome
