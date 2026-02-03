"""
UNILABS / ALGO-LIFE - Extractors (ROBUST v6)
- SYNLAB Biology PDF: France report + Belgium table style
- IDK GutMAP PDF: Dysbiosis index + Diversity + group-level results (Expected/Slightly deviating/Deviating)

Drop-in replacement: put this file as ./extractors.py (same level as app.py)
"""

from __future__ import annotations

import re
from typing import Dict, Any, List, Optional


# ---------------------------------------------------------------------
# Helpers: normalization + numeric parsing
# ---------------------------------------------------------------------
def normalize_biomarker_name(name: str) -> str:
    if name is None:
        return ""
    s = str(name).strip()
    s = re.sub(r"\s+", " ", s)
    return s


def _safe_float(x) -> Optional[float]:
    try:
        if x is None:
            return None
        s = str(x).strip().replace(",", ".")
        # keep digits/sign/dot/exponent only
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
    Returns: 'low' | 'normal' | 'high' | 'unknown'
    Compatible with calls (value, reference) OR (value, reference, biomarker_name)
    """
    v = _safe_float(value)
    if v is None:
        return "unknown"

    ref = _clean_ref(reference)

    # ranges: "x - y" or "x à y" or "x to y"
    m = re.search(r"(-?\d+(?:[.,]\d+)?)\s*(?:-|à|to)\s*(-?\d+(?:[.,]\d+)?)", ref, flags=re.IGNORECASE)
    if m:
        lo = _safe_float(m.group(1))
        hi = _safe_float(m.group(2))
        if lo is None or hi is None:
            return "unknown"
        if v < lo:
            return "low"
        if v > hi:
            return "high"
        return "normal"

    # "< x" or "≤ x"
    m = re.search(r"(?:<|≤)\s*(-?\d+(?:[.,]\d+)?)", ref)
    if m:
        hi = _safe_float(m.group(1))
        if hi is None:
            return "unknown"
        return "high" if v > hi else "normal"

    # "> x" or "≥ x"
    m = re.search(r"(?:>|≥)\s*(-?\d+(?:[.,]\d+)?)", ref)
    if m:
        lo = _safe_float(m.group(1))
        if lo is None:
            return "unknown"
        return "low" if v < lo else "normal"

    return "unknown"


# ---------------------------------------------------------------------
# PDF text loader
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
# SYNLAB Biology extractor (France + Belgium)
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
    r"^\(>\)\s+nouveau",
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
    Output:
      { biomarker: {value, unit, reference, status} , ... }
    Handles:
      - France style: "FERRITINE 11 µg/L (10 à 291)"
      - France style: "CRP ULTRASENSIBLE 0.96 mg/L (< 5)"
      - Belgium table style: "> Hémoglobine 12.9 11.5 - 16.0 g/dL"
      - Belgium table style with +/- marker: "> Coenzyme Q10 - 506 670 - 990 μg/L"
    """
    text = _read_pdf_text(pdf_path)
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    out: Dict[str, Any] = {}

    # --- Pattern A (France): NAME VALUE UNIT (REF...)
    # Example: "GLYCEMIE A JEUN 0.84 g/L (0.74 à 1.06)"
    pat_fr = re.compile(
        r"^(?P<name>[A-ZÀ-Ÿ0-9\.\-\/\s]{3,60})\s+"
        r"(?P<value>[<>]?\s*[\+\-]?\s*\d+(?:[.,]\d+)?)\s*"
        r"(?P<unit>[a-zA-Zµμ/%]+(?:\s*[a-zA-Zµμ/%]+)?)?\s*"
        r"\((?P<ref>[^)]+)\)"
        r"(?:\s|$)",
        flags=re.UNICODE,
    )

    # --- Pattern B (Belgium table): optional ">" then name then value then ref-range then unit
    # Examples:
    # "> Hémoglobine 12.9 11.5 - 16.0 g/dL"
    # "> Coenzyme Q10 - 506 670 - 990 μg/L"
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

        # Try Belgium/table style first (more specific)
        m = pat_be.match(ln)
        if m:
            name = normalize_biomarker_name(m.group("name"))
            value = m.group("value")
            if m.group("valsign") == "-":
                # usually means "flag low", not negative concentration; keep as positive numeric value
                # (status will be determined from ref anyway)
                pass
            unit = (m.group("unit") or "").strip()
            ref = _clean_ref(m.group("ref"))
            status = determine_biomarker_status(value, ref, name)
            out[name] = {"value": value, "unit": unit, "reference": ref, "status": status}
            continue

        # France style
        m = pat_fr.match(ln)
        if m:
            name = normalize_biomarker_name(m.group("name"))
            value = m.group("value")
            unit = (m.group("unit") or "").strip()
            ref = _clean_ref(m.group("ref"))

            # Filter: avoid false positives like "SIEMENS 4.66 mmol/L (4.11 à 5.88)"
            # We keep if name contains letters and not just an instrument name
            if re.search(r"\bSIEMENS\b", name, flags=re.IGNORECASE):
                continue

            status = determine_biomarker_status(value, ref, name)
            out[name] = {"value": value, "unit": unit, "reference": ref, "status": status}
            continue

    return out


# ---------------------------------------------------------------------
# IDK GutMAP extractor (group-level results)
# ---------------------------------------------------------------------
def extract_idk_microbiome(pdf_path: str) -> Dict[str, Any]:
    """
    Output:
      {
        "dysbiosis_index": int | None,
        "dysbiosis_label": str | None,
        "diversity": str | None,
        "bacteria": [
            {"group": "A1. Prominent gut microbes", "result": "expected|slightly_deviating|deviating"},
            ...
        ]
      }

    Note: PDF text does NOT reliably include per-bacteria 'low/high/normal'. We use group results
    reported in the narrative: "Result: expected / slightly deviating / deviating abundance..."
    """
    text = _read_pdf_text(pdf_path)

    # Dysbiosis label and DI
    dys_label = None
    di = None

    # Example: "Result: The microbiota is normobiotic"  -> DI 1 by default
    m = re.search(r"Result:\s*The microbiota is\s+([A-Za-z\- ]+)", text, flags=re.IGNORECASE)
    if m:
        dys_label = m.group(1).strip().lower()
        if "normobiotic" in dys_label:
            di = 1
        elif "mild" in dys_label:
            di = 3
        elif "sever" in dys_label:
            di = 5

    # Sometimes a digit appears near the scale; attempt a loose capture of "DYSBIOSIS INDEX ... Result:"
    # If present like "Result: 2" or "DI: 2"
    m2 = re.search(r"(?:DI|Dysbiosis index)\s*[:\-]?\s*([1-5])", text, flags=re.IGNORECASE)
    if m2:
        di = int(m2.group(1))

    # Diversity
    diversity = None
    m = re.search(r"Result:\s*The bacterial diversity is\s+([A-Za-z\- ]+)", text, flags=re.IGNORECASE)
    if m:
        diversity = m.group(1).strip().lower()

    # Group results: capture sections like "A1. Prominent gut microbes ... Result: expected abundance..."
    group_header = re.compile(r"(?m)^([A-Z]\d)\.\s+(.+?)\s*$")
    result_line = re.compile(r"Result:\s*(expected|slightly deviating|deviating)\s+abundance", flags=re.IGNORECASE)

    bacteria: List[Dict[str, Any]] = []

    # We iterate through the document linearly keeping "current group"
    current_group = None
    lines = [ln.rstrip() for ln in text.splitlines()]

    for ln in lines:
        h = group_header.match(ln.strip())
        if h:
            code = h.group(1).strip()
            title = h.group(2).strip()
            current_group = f"{code}. {title}"
            continue

        r = result_line.search(ln)
        if r and current_group:
            res = r.group(1).strip().lower()
            res = res.replace(" ", "_")  # "slightly deviating" -> "slightly_deviating"
            bacteria.append({"group": current_group, "result": res})
            # do not reset current_group, some PDFs repeat
            continue

    # Deduplicate keeping first
    seen = set()
    uniq = []
    for item in bacteria:
        key = (item["group"], item["result"])
        if key in seen:
            continue
        seen.add(key)
        uniq.append(item)

    return {
        "dysbiosis_index": di,
        "dysbiosis_label": dys_label,
        "diversity": diversity,
        "bacteria": uniq,
    }
