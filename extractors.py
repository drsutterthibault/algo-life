"""
ALGO-LIFE - extractors.py (PATCHED)
✅ determine_biomarker_status compatible 2 ou 3 arguments (anti-crash)
✅ normalize_biomarker_name fourni (requis par rules_engine.py)
✅ extract_synlab_biology (PDF)
✅ extract_idk_microbiome (PDF)

Auteur: Dr Thibault SUTTER
Date: Février 2026
"""

import re
from typing import Dict, Any


# ----------------------------------------------------------------------
# Normalisation des noms (requis par rules_engine.py)
# ----------------------------------------------------------------------
def normalize_biomarker_name(name: str) -> str:
    if name is None:
        return ""
    s = str(name).strip().lower()
    s = re.sub(r"\s+", " ", s)
    # enlever certains caractères parasites
    s = s.replace("µ", "u")
    s = s.replace("α", "alpha").replace("β", "beta")
    return s


# ----------------------------------------------------------------------
# Statut biomarqueur (PATCH: accepte 2 OU 3 args)
# ----------------------------------------------------------------------
def determine_biomarker_status(value, reference, biomarker_name=None, *args, **kwargs):
    """
    Retourne: 'low', 'normal', 'high', 'unknown'
    - Compatible appels: (value, reference) OU (value, reference, biomarker_name)
    - *args/**kwargs absorbent tout appel inattendu -> jamais de crash
    """

    def _to_float(x):
        try:
            if x is None:
                return None
            s = str(x).strip().replace(",", ".")
            # garde chiffres, signe, point, exponent
            s = re.sub(r"[^0-9\.\-\+eE]", "", s)
            return float(s) if s else None
        except Exception:
            return None

    v = _to_float(value)
    if v is None:
        return "unknown"

    ref = "" if reference is None else str(reference).strip()

    # "x - y" / "x à y" / "x–y"
    m = re.search(r"(-?\d+(?:[.,]\d+)?)\s*(?:-|–|—|à|to)\s*(-?\d+(?:[.,]\d+)?)", ref, flags=re.IGNORECASE)
    if m:
        low = _to_float(m.group(1))
        high = _to_float(m.group(2))
        if low is None or high is None:
            return "unknown"
        if v < low:
            return "low"
        if v > high:
            return "high"
        return "normal"

    # "< x" ou "≤ x"
    m = re.search(r"(?:<|≤)\s*(-?\d+(?:[.,]\d+)?)", ref)
    if m:
        high = _to_float(m.group(1))
        if high is None:
            return "unknown"
        return "high" if v > high else "normal"

    # "> x" ou "≥ x"
    m = re.search(r"(?:>|≥)\s*(-?\d+(?:[.,]\d+)?)", ref)
    if m:
        low = _to_float(m.group(1))
        if low is None:
            return "unknown"
        return "low" if v < low else "normal"

    return "unknown"


# ----------------------------------------------------------------------
# Extraction Synlab biologie PDF
# ----------------------------------------------------------------------
def extract_synlab_biology(pdf_path: str) -> Dict[str, Any]:
    """
    Sortie:
      { "Ferritine": {"value":..., "unit":..., "reference":..., "status":...}, ... }
    """
    try:
        import pdfplumber
    except ImportError:
        raise ImportError("pdfplumber manquant. Ajoute-le dans requirements.txt")

    biomarkers: Dict[str, Any] = {}

    with pdfplumber.open(pdf_path) as pdf:
        text = ""
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            text += page_text + "\n"

    # Pattern simple (à améliorer ensuite): Nom  Valeur  Unité  (Référence)
    # Exemple: "Ferritine 32 ng/mL (20 - 300)"
    pattern = re.findall(
        r"([A-Za-zÀ-ÿ0-9\-\s]{3,40})\s+([0-9]+(?:[.,][0-9]+)?)\s*([a-zA-Z/%µu]*)\s*\(?([0-9<>\-\s.,àto–—]*)\)?",
        text
    )

    for name, value, unit, ref in pattern:
        n = str(name).strip()
        if not n or len(n) < 3:
            continue

        v = str(value).strip()
        u = str(unit).strip()
        r = str(ref).strip()

        status = determine_biomarker_status(v, r, n)

        biomarkers[n] = {
            "value": v,
            "unit": u,
            "reference": r,
            "status": status
        }

    return biomarkers


# ----------------------------------------------------------------------
# Extraction IDK microbiote PDF (basique)
# ----------------------------------------------------------------------
def extract_idk_microbiome(pdf_path: str) -> Dict[str, Any]:
    """
    Sortie attendue par RulesEngine:
      {"bacteria": [{"group": "...", "result": "...", "status": "low/high/normal"}, ...]}
    """
    try:
        import pdfplumber
    except ImportError:
        raise ImportError("pdfplumber manquant. Ajoute-le dans requirements.txt")

    with pdfplumber.open(pdf_path) as pdf:
        text = ""
        for page in pdf.pages:
            text += (page.extract_text() or "") + "\n"

    bacteria = []
    matches = re.findall(r"([A-Za-z0-9\-\s]{4,50})\s+(low|high|normal)", text, flags=re.IGNORECASE)
    for name, stt in matches:
        bacteria.append({
            "group": name.strip(),
            "result": stt.lower(),
            "status": stt.lower()
        })

    return {"bacteria": bacteria}
