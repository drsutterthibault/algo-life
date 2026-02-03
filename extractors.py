"""
UNILABS / ALGO-LIFE - Extractors (PATCH MATCHING v8)
✅ Extraction PDF inchangée
✅ FIX: normalize_biomarker_name robuste pour matcher les règles Excel
✅ Status: Bas/Normal/Élevé/Inconnu (compatible rules_engine.py)
"""

from __future__ import annotations

import re
import unicodedata
from typing import Dict, Any, List, Optional


# ---------------------------------------------------------------------
# ✅ FIX MATCHING (seul changement important)
# ---------------------------------------------------------------------
def normalize_biomarker_name(name: str) -> str:
    """
    Normalisation robuste pour matcher Excel, sans toucher à l'extraction :
    - trim
    - suppression accents
    - uppercase
    - nettoyage ponctuation
    - espaces normalisés
    """
    if name is None:
        return ""
    s = str(name).strip()

    # Supprimer accents
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))

    # Uppercase
    s = s.upper()

    # Harmoniser ponctuation (C.P.K -> C P K -> CPK via squeeze)
    s = s.replace(".", " ")
    s = s.replace(",", " ")
    s = s.replace("’", "'")

    # Garder A-Z 0-9 + séparateurs simples
    s = re.sub(r"[^A-Z0-9\s\-\+/]", " ", s)

    # Espaces propres
    s = re.sub(r"\s+", " ", s).strip()

    # Compacte certains acronymes fréquents (option safe)
    s = s.replace("C P K", "CPK")

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
    r = r.replace("–", "-").replace("—", "-")
    r = re.sub(r"\s+", " ", r)
    return r


def determine_biomarker_status(value, reference, biomarker_name=None, *args, **kwargs) -> str:
    """
    Returns EXACT strings expected by rules_engine.py:
      'Bas' | 'Normal' | 'Élevé' | 'Inconnu'
    """
    v = _safe_float(value)
    if v is None:
        return "Inconnu"

    ref = _clean_ref(reference)

    # Range: "x - y" or "x à y" or "x to y"
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

    # "< x" or "≤ x"
    m = re.search(r"(?:<|≤)\s*(-?\d+(?:[.,]\d+)?)", ref)
    if m:
        hi = _safe_float(m.group(1))
        if hi is None:
            return "Inconnu"
        return "Élevé" if v > hi else "Normal"

    # "> x" or "≥ x"
    m = re.search(r"(?:>|≥)\s*(-?\d+(?:[.,]\d+)?)", ref)
    if m:
        lo = _safe_float(m.group(1))
        if lo is None:
            return "Inconnu"
        return "Bas" if v < lo else "Normal"

    return "Inconnu"


# ---------------------------------------------------------------------
# PDF text loader (INCHANGÉ)
# ---------------------------------------------------------------------
def _read_pdf_text(pdf_path: str) -> str:
    try:
        import pdfplumber
    except ImportError as e:
        raise ImportError("pdfplumber manquant. Ajoute-le dans requirements.txt") from e

    chunks: List[str] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            chunks.append(page.extract_text() or "")
    return "\n".join(chunks)


# ---------------------------------------------------------------------
# SYNLAB Biology extractor (INCHANGÉ)
# ---------------------------------------------------------------------
_IGNORE_PATTERNS = [
    r"^Édition\s*:",
    r"^Laboratoire",
    r"^SYNLAB",
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
    Output dict:
      { biomarker: {value, unit, reference, status} , ... }
    status: Bas/Normal/Élevé/Inconnu (compat rules_engine.py)
    """
    text = _read_pdf_text(pdf_path)
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    out: Dict[str, Any] = {}

    # France style: NAME VALUE UNIT (REF)
    pat_fr = re.compile(
        r"^(?P<name>[A-ZÀ-Ÿ0-9\.\-\/\s]{3,60})\s+"
        r"(?P<value>[<>]?\s*[\+\-]?\s*\d+(?:[.,]\d+)?)\s*"
        r"(?P<unit>[a-zA-Zµμ/%]+(?:\s*[a-zA-Zµμ/%]+)?)?\s*"
        r"\((?P<ref>[^)]+)\)",
        flags=re.UNICODE,
    )

    # Belgium table style: optional ">" then name then value then ref-range then unit
    pat_be = re.compile(
        r"^(?:>\s*)?"
        r"(?P<name>[A-Za-zÀ-ÿ0-9\.\-\/\s]{3,60}?)\s+"
        r"(?P<valsign>[\+\-])?\s*(?P<value>\d+(?:[.,]\d+)?)\s+"
        r"(?P<ref>\d+(?:[.,]\d+)?\s*-\s*\d+(?:[.,]\d+)?)\s+"
        r"(?P<unit>[A-Za-zµμ/%]+(?:\s*[A-Za-zµμ/%]+)?)\s*$",
        flags=re.UNICODE,
    )

    for ln in lines:
        if _is_noise_line(ln):
            continue

        m = pat_be.match(ln)
        if m:
            name_raw = m.group("name")
            name = name_raw.strip()
            value = m.group("value")
            unit = (m.group("unit") or "").strip()
            ref = _clean_ref(m.group("ref"))
            status = determine_biomarker_status(value, ref, name)
            out[name] = {"value": value, "unit": unit, "reference": ref, "status": status}
            continue

        m = pat_fr.match(ln)
        if m:
            name_raw = m.group("name")
            name = name_raw.strip()
            if re.search(r"\bSIEMENS\b", name, flags=re.IGNORECASE):
                continue
            value = m.group("value")
            unit = (m.group("unit") or "").strip()
            ref = _clean_ref(m.group("ref"))
            status = determine_biomarker_status(value, ref, name)
            out[name] = {"value": value, "unit": unit, "reference": ref, "status": status}
            continue

    return out


# ---------------------------------------------------------------------
# IDK GutMAP extractor (INCHANGÉ côté parsing, mais normalisation prête)
# ---------------------------------------------------------------------
def extract_idk_microbiome(pdf_path: str) -> Dict[str, Any]:
    """
    Output dict expected by rules_engine.py:
      {
        "dysbiosis_index": int | None,
        "diversity": str | None,
        "bacteria": [
          {"category": "A1", "group": "A1. Prominent gut microbes", "result": "Expected|Slightly deviating|Deviating"},
          ...
        ]
      }
    """
    text = _read_pdf_text(pdf_path)

    # Dysbiosis index (best effort)
    di = None
    m2 = re.search(r"(?:DI|Dysbiosis index)\s*[:\-]?\s*([1-5])", text, flags=re.IGNORECASE)
    if m2:
        di = int(m2.group(1))
    else:
        m = re.search(r"Result:\s*The microbiota is\s+([A-Za-z\- ]+)", text, flags=re.IGNORECASE)
        if m:
            label = m.group(1).strip().lower()
            if "normobiotic" in label:
                di = 1
            elif "mild" in label:
                di = 3
            elif "sever" in label:
                di = 5

    diversity = None
    md = re.search(r"Result:\s*The bacterial diversity is\s+([A-Za-z\- ]+)", text, flags=re.IGNORECASE)
    if md:
        diversity = md.group(1).strip()

    group_header = re.compile(r"(?m)^([A-Z]\d)\.\s+(.+?)\s*$")
    result_line = re.compile(r"Result:\s*(expected|slightly deviating|deviating)\s+abundance", flags=re.IGNORECASE)

    bacteria: List[Dict[str, Any]] = []
    current_code = None
    current_group = None

    for ln in text.splitlines():
        ln = ln.strip()
        h = group_header.match(ln)
        if h:
            current_code = h.group(1).strip()
            current_group = f"{current_code}. {h.group(2).strip()}"
            continue

        r = result_line.search(ln)
        if r and current_code and current_group:
            raw = r.group(1).strip().lower()
            if raw == "expected":
                res = "Expected"
            elif raw == "slightly deviating":
                res = "Slightly deviating"
            else:
                res = "Deviating"

            bacteria.append({"category": current_code, "group": current_group, "result": res})

    # Deduplicate
    seen = set()
    uniq = []
    for b in bacteria:
        key = (b["category"], b["group"], b["result"])
        if key in seen:
            continue
        seen.add(key)
        uniq.append(b)

    return {
        "dysbiosis_index": di,
        "diversity": diversity,
        "bacteria": uniq,
    }
