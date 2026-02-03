"""
ALGO-LIFE - Extractors Module (PATCHED v3.0)

✅ Extraction Synlab Biology PDF
✅ Extraction IDK Microbiome PDF
✅ determine_biomarker_status() FIXED (3 arguments compatible RulesEngine)

Auteur: Dr Thibault SUTTER
Date: Février 2026
"""

import re
from typing import Dict, Any


# ============================================================================
# ✅ STATUS FUNCTION (PATCHED)
# ============================================================================

def determine_biomarker_status(value, reference, biomarker_name=None):
    """
    Détermine le statut low/normal/high/unknown à partir de la valeur et de la référence.
    biomarker_name est optionnel → compatibilité RulesEngine.

    Exemple reference:
      "3.5 - 5.2"
      "< 1.0"
      "> 10"
    """

    def _to_float(x):
        try:
            if x is None:
                return None
            s = str(x).strip().replace(",", ".")
            s = re.sub(r"[^0-9\.\-\+eE]", "", s)
            return float(s) if s else None
        except Exception:
            return None

    v = _to_float(value)
    if v is None:
        return "unknown"

    ref = "" if reference is None else str(reference).strip()

    # Cas: "x - y"
    m = re.search(r"(-?\d+[.,]?\d*)\s*(?:-|–|—|à|to)\s*(-?\d+[.,]?\d*)", ref)
    if m:
        low = _to_float(m.group(1))
        high = _to_float(m.group(2))

        if low is None or high is None:
            return "unknown"

        if v < low:
            return "low"
        elif v > high:
            return "high"
        else:
            return "normal"

    # Cas: "< x"
    m = re.search(r"(?:<|≤)\s*(-?\d+[.,]?\d*)", ref)
    if m:
        high = _to_float(m.group(1))
        if high is None:
            return "unknown"
        return "high" if v > high else "normal"

    # Cas: "> x"
    m = re.search(r"(?:>|≥)\s*(-?\d+[.,]?\d*)", ref)
    if m:
        low = _to_float(m.group(1))
        if low is None:
            return "unknown"
        return "low" if v < low else "normal"

    return "unknown"


# ============================================================================
# ✅ BIOLOGY PDF EXTRACTION (SYNLAB)
# ============================================================================

def extract_synlab_biology(pdf_path: str) -> Dict[str, Any]:
    """
    Extraction simple Synlab:
    Renvoie dict biomarker -> {value, unit, reference, status}
    """

    try:
        import pdfplumber
    except ImportError:
        raise ImportError("pdfplumber manquant. Ajoute-le dans requirements.txt")

    biomarkers = {}

    with pdfplumber.open(pdf_path) as pdf:
        full_text = ""
        for page in pdf.pages:
            full_text += page.extract_text() + "\n"

    # Regex robuste:
    # Exemple ligne: "Ferritine 32 ng/mL (20 - 300)"
    pattern = re.findall(
        r"([A-Za-zÀ-ÿ0-9\-\s]{3,30})\s+([0-9]+[.,]?[0-9]*)\s*([a-zA-Z/%µ]*)\s*\(?([0-9.,<>\-\sàto]*)\)?",
        full_text
    )

    for match in pattern:
        name = match[0].strip()
        value = match[1].strip()
        unit = match[2].strip()
        ref = match[3].strip()

        if len(name) < 3:
            continue

        status = determine_biomarker_status(value, ref, name)

        biomarkers[name] = {
            "value": value,
            "unit": unit,
            "reference": ref,
            "status": status
        }

    return biomarkers


# ============================================================================
# ✅ MICROBIOME PDF EXTRACTION (IDK Gutmap)
# ============================================================================

def extract_idk_microbiome(pdf_path: str) -> Dict[str, Any]:
    """
    Extraction IDK microbiote GutMAP report.

    Sortie standard attendue:
    {
      "bacteria": [
        {"group": "...", "result": "...", "status": "..."}
      ]
    }
    """

    try:
        import pdfplumber
    except ImportError:
        raise ImportError("pdfplumber manquant. Ajoute-le dans requirements.txt")

    bacteria = []

    with pdfplumber.open(pdf_path) as pdf:
        full_text = ""
        for page in pdf.pages:
            full_text += page.extract_text() + "\n"

    # Extrait lignes type:
    # "Bifidobacterium low"
    matches = re.findall(
        r"([A-Za-z0-9\-\s]{4,40})\s+(low|high|normal)",
        full_text,
        flags=re.IGNORECASE
    )

    for name, status in matches:
        bacteria.append({
            "group": name.strip(),
            "result": status.lower(),
            "status": status.lower()
        })

    return {
        "bacteria": bacteria
    }


# ============================================================================
# ✅ TEST MODE
# ============================================================================

if __name__ == "__main__":
    print("✅ Extractors loaded correctly.")
