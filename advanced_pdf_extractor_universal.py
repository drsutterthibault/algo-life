"""
ALGO-LIFE — Universal PDF Extractor
Version 1.3 — Feb 2026
✅ Robust import: exposes `UniversalPDFExtractor`
✅ No Streamlit dependency (pure module)
✅ Works with Streamlit UploadedFile / bytes / file path
✅ Extracts:
   - raw text (pdfplumber preferred, PyPDF2 fallback)
   - biomarkers (name/value/unit/ref ranges) with strong anti-noise filters
   - patient info (name/sex/age/date when detectable)

Author: Dr Thibault SUTTER
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple, Union, List

# Optional deps
try:
    import pdfplumber  # type: ignore
except Exception:
    pdfplumber = None

try:
    import PyPDF2  # type: ignore
except Exception:
    PyPDF2 = None


PdfInput = Union[bytes, bytearray, io.BytesIO, Any, str, None]  # Any = Streamlit UploadedFile-like


# -------------------------------
# Helpers
# -------------------------------

def _to_bytes(pdf_file: PdfInput) -> bytes:
    """Normalize input into raw PDF bytes."""
    if pdf_file is None:
        return b""

    # Path
    if isinstance(pdf_file, str):
        with open(pdf_file, "rb") as f:
            return f.read()

    # Bytes / bytearray
    if isinstance(pdf_file, (bytes, bytearray)):
        return bytes(pdf_file)

    # BytesIO
    if isinstance(pdf_file, io.BytesIO):
        return pdf_file.getvalue()

    # Streamlit UploadedFile-like (has getvalue or read)
    if hasattr(pdf_file, "getvalue"):
        try:
            return pdf_file.getvalue()
        except Exception:
            pass
    if hasattr(pdf_file, "read"):
        try:
            data = pdf_file.read()
            # Some file objects advance pointer; best effort reset
            try:
                pdf_file.seek(0)
            except Exception:
                pass
            return data if isinstance(data, (bytes, bytearray)) else str(data).encode("utf-8", errors="ignore")
        except Exception:
            pass

    raise TypeError(f"Unsupported pdf_file type: {type(pdf_file)}")


def _clean_text(s: str) -> str:
    # Normalize spaces, keep line breaks
    s = s.replace("\x00", " ")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\r\n?", "\n", s)
    return s.strip()


def _safe_float(x: str) -> Optional[float]:
    x = x.strip()
    # Convert commas to dots, remove thin spaces
    x = x.replace("\u202f", "").replace("\xa0", "").replace(" ", "")
    x = x.replace(",", ".")
    # Drop trailing symbols
    x = re.sub(r"[^0-9\.\-+]", "", x)
    if x in ("", ".", "-", "+"):
        return None
    try:
        return float(x)
    except Exception:
        return None


def _looks_like_year_or_code(token: str) -> bool:
    t = token.strip()
    # Years 1900-2099
    if re.fullmatch(r"(19|20)\d{2}", t):
        return True
    # Sample IDs / long codes
    if len(t) >= 8 and re.fullmatch(r"[A-Z0-9\-_/]+", t, flags=re.IGNORECASE):
        return True
    return False


# -------------------------------
# Core extractor
# -------------------------------

@dataclass
class BiomarkerHit:
    key: str
    value: float
    unit: str = ""
    ref_low: Optional[float] = None
    ref_high: Optional[float] = None
    raw_name: str = ""


class UniversalPDFExtractor:
    """
    Universal extractor:
    - extract_text() -> str
    - extract_biomarkers_universal(text) -> Dict[str, float]
    - extract_patient_info(text) -> Dict[str, str]
    """

    def __init__(self, pdf_file: PdfInput = None):
        self.pdf_file = pdf_file

    # ---------------------------
    # Text extraction
    # ---------------------------
    def extract_text(self) -> str:
        pdf_bytes = _to_bytes(self.pdf_file)
        if not pdf_bytes:
            return ""

        # Prefer pdfplumber (better layout)
        if pdfplumber is not None:
            try:
                with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                    pages = []
                    for p in pdf.pages:
                        t = p.extract_text() or ""
                        if t:
                            pages.append(t)
                return _clean_text("\n".join(pages))
            except Exception:
                # Fall back below
                pass

        # Fallback: PyPDF2
        if PyPDF2 is not None:
            try:
                reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
                pages = []
                for page in reader.pages:
                    t = page.extract_text() or ""
                    if t:
                        pages.append(t)
                return _clean_text("\n".join(pages))
            except Exception:
                return ""

        return ""

    # ---------------------------
    # Patient info (best effort)
    # ---------------------------
    def extract_patient_info(self, text: str) -> Dict[str, str]:
        t = text
        out: Dict[str, str] = {}

        # Date prélèvement
        m = re.search(r"(date\s+(du\s+)?)?(pr[ée]l[ée]vement|pr[ée]l[èe]v\.)\s*[:\-]?\s*(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})", t, flags=re.IGNORECASE)
        if m:
            out["prelevement_date"] = m.group(4).replace(".", "/").replace("-", "/")

        # Sex
        m = re.search(r"\b(sexe|sex)\s*[:\-]?\s*(f[ée]minin|masculin|f|m)\b", t, flags=re.IGNORECASE)
        if m:
            val = m.group(2).lower()
            out["sexe"] = "Féminin" if val in ("f", "féminin", "feminin") else "Masculin"

        # Age
        m = re.search(r"\b(age|â?ge)\s*[:\-]?\s*(\d{1,3})\s*(ans|y)?\b", t, flags=re.IGNORECASE)
        if m:
            out["age"] = m.group(2)

        # Name (very variable; best effort)
        m = re.search(r"\b(nom|patient)\s*[:\-]?\s*([A-ZÀ-Ü][A-ZÀ-Ü'\- ]{2,})\b", t)
        if m:
            cand = m.group(2).strip()
            # Avoid capturing whole lines like "PATIENT : RESULTATS"
            if len(cand.split()) <= 6:
                out["nom"] = cand.title()

        return out

    # ---------------------------
    # Biomarkers extraction
    # ---------------------------
    def extract_biomarkers_universal(self, text: str, debug: bool = False) -> Dict[str, float]:
        """
        Extract biomarker numeric values.
        Output keys are snake_case normalized from raw names.
        """
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        hits: List[BiomarkerHit] = []

        # Pattern examples:
        # "CRP  1.2 mg/L (0.0 - 3.0)"
        # "Ferritine : 28 ng/mL  30 - 300"
        # "Vitamine D  22 ng/mL  [30-100]"
        # "TSH 2,1 mUI/L 0,5 à 4,5"
        value_pat = r"(?P<val>[<>]?\s*[-+]?\d+(?:[.,]\d+)?)"
        unit_pat = r"(?P<unit>(?:[a-zA-Zµμ/%]+(?:/[a-zA-Z]+)?)|(?:10\^?\d+/?[a-zA-Z]+))?"
        ref_pat = r"(?P<r1>[-+]?\d+(?:[.,]\d+)?)\s*(?:-|à|to|–)\s*(?P<r2>[-+]?\d+(?:[.,]\d+)?)"

        # We keep name flexible but avoid lines that are clearly headers
        for ln in lines:
            # Fast filters for noise
            if len(ln) < 4:
                continue
            if ln.lower().startswith(("page ", "www.", "http", "laboratoire", "résultats", "resultats", "analyse", "commentaire", "méthode", "method")):
                continue

            # Try to capture: name + value + unit + optional ref
            # 1) name then value
            m = re.search(rf"^(?P<name>.+?)\s+{value_pat}\s*{unit_pat}\s*(?:\(?\s*{ref_pat}\s*\)?)?\s*$", ln)
            if not m:
                # 2) name : value unit ref
                m = re.search(rf"^(?P<name>.+?)\s*[:\-]\s*{value_pat}\s*{unit_pat}\s*(?:\(?\s*{ref_pat}\s*\)?)?\s*$", ln)
            if not m:
                continue

            raw_name = m.group("name").strip()
            raw_val = m.group("val").strip()

            # Avoid capturing junk names containing long sentences
            if len(raw_name) > 60:
                continue

            # Avoid years/codes being interpreted as biomarker values
            if _looks_like_year_or_code(raw_val):
                continue

            val = _safe_float(raw_val)
            if val is None:
                continue

            unit = (m.group("unit") or "").strip()

            # Optional refs
            r1 = _safe_float(m.group("r1")) if m.groupdict().get("r1") else None
            r2 = _safe_float(m.group("r2")) if m.groupdict().get("r2") else None

            key = self._normalize_key(raw_name)

            # Additional anti-parasite rules
            if key in ("page", "date", "nom", "patient"):
                continue
            if len(key) < 2:
                continue

            hits.append(BiomarkerHit(key=key, value=val, unit=unit, ref_low=r1, ref_high=r2, raw_name=raw_name))

        # De-duplicate: keep last occurrence (often final validated value)
        out: Dict[str, float] = {}
        for h in hits:
            out[h.key] = h.value

        if debug:
            # Add minimal traceability if user logs it
            out["_debug_n_hits"] = float(len(hits))

        return out

    # ---------------------------
    # Name normalization
    # ---------------------------
    @staticmethod
    def _normalize_key(name: str) -> str:
        n = name.lower().strip()

        # Remove bracketed notes
        n = re.sub(r"\(.*?\)", "", n).strip()

        # Common accents -> ascii-ish
        repl = {
            "é": "e", "è": "e", "ê": "e", "ë": "e",
            "à": "a", "â": "a",
            "î": "i", "ï": "i",
            "ô": "o", "ö": "o",
            "û": "u", "ü": "u",
            "ç": "c",
            "’": "'", "–": "-", "—": "-",
        }
        for a, b in repl.items():
            n = n.replace(a, b)

        # Replace separators by spaces
        n = re.sub(r"[/,:;]+", " ", n)
        n = re.sub(r"[^a-z0-9\s\-\+%µμ]", " ", n)
        n = re.sub(r"\s+", " ", n).strip()

        # Canonical mappings for frequent markers
        mappings = {
            "crp us": "crp",
            "crp ultrasensible": "crp",
            "vitamine d": "vitamine_d",
            "25 oh vitamine d": "vitamine_d",
            "ferritine": "ferritine",
            "homocysteine": "homocysteine",
            "glycemie": "glycemie",
            "glucose": "glycemie",
            "insuline": "insuline",
            "hba1c": "hba1c",
            "cholesterol total": "cholesterol_total",
            "hdl cholesterol": "hdl",
            "ldl cholesterol": "ldl",
            "triglycerides": "triglycerides",
            "tsh": "tsh",
            "t3 libre": "t3_libre",
            "ft3": "t3_libre",
            "t4 libre": "t4_libre",
            "ft4": "t4_libre",
            "dhea": "dhea",
            "dhea s": "dhea",
            "zonuline": "zonuline",
            "lbp": "lbp",
            "magnesium": "magnesium",
            "zinc": "zinc",
            "selenium": "selenium",
            "vitamine b12": "vitamine_b12",
        }

        if n in mappings:
            return mappings[n]

        # snake_case
        n = n.replace("-", " ")
        n = re.sub(r"\s+", "_", n).strip("_")

        return n


# Backward compatible aliases (in case old code imports another name)
AdvancedPDFExtractorUniversal = UniversalPDFExtractor
__all__ = ["UniversalPDFExtractor", "AdvancedPDFExtractorUniversal", "BiomarkerHit"]

# ============================================================
# ✅ EXPORT STABLE POUR APP.PY
# ============================================================
# Objectif: garantir que "from advanced_pdf_extractor_universal import UniversalPDFExtractor"
# fonctionne TOUJOURS, même si la classe interne s'appelle différemment.

def _resolve_universal_extractor_class():
    # Liste de noms possibles déjà présents dans ton module
    candidates = [
        "UniversalPDFExtractor",
        "AdvancedPDFExtractor",
        "AdvancedPDFExtractorUniversal",
        "UniversalExtractor",
        "PDFExtractor",
        "Extractor",
    ]
    for name in candidates:
        obj = globals().get(name)
        if isinstance(obj, type):
            return obj
    return None

_cls = _resolve_universal_extractor_class()

if _cls is None:
    # On crée un fallback explicite: l'import ne casse plus,
    # et tu auras une erreur claire au moment de l'utilisation.
    class UniversalPDFExtractor:  # noqa: N801
        def __init__(self, *args, **kwargs):
            raise ImportError(
                "UniversalPDFExtractor introuvable dans advanced_pdf_extractor_universal.py. "
                "Ajoute ta classe extractor (ou renomme-la), ou assure-toi qu'elle est définie au niveau global."
            )
else:
    # Alias officiel: c'est CE symbole que ton app importe
    UniversalPDFExtractor = _cls  # noqa: N816
