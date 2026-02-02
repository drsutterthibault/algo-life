"""
microbiome_extractor_idk_gutmap.py
---------------------------------
Extracteur "light" pour rapports IDK® GutMAP (EN) à partir du texte PDF déjà extrait.

⚠️ Important
- Les rapports IDK GutMAP contiennent une grande partie des résultats sous forme de graphiques.
  Selon le PDF, pdfplumber/PyPDF2 peuvent ne pas récupérer les valeurs quantitatives (z-scores).
- Cet extracteur récupère donc de manière robuste :
  - Dysbiosis Index (DI) : via texte si présent, sinon via le nom de fichier (ex: "..._DI-1_EN.pdf"),
    sinon via l'interprétation ("normobiotic" -> DI 1/2, "mildly" -> DI 3, "severely" -> DI 4/5).
  - Diversité (Shannon) : via la phrase "bacterial diversity is ..." (as expected / lower than expected / ...).
  - Présence (bool) de quelques espèces clés, si elles apparaissent dans le texte du rapport
    (présence dans la liste ≠ quantification).

Usage (dans app.py)
-------------------
from microbiome_extractor_idk_gutmap import extract_microbiome_data

text = AdvancedPDFExtractor.extract_text(microbiome_pdf)
microbiome_data = extract_microbiome_data(text, filename=microbiome_pdf.name, debug=True)
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip().lower()


def _extract_di_from_filename(filename: Optional[str]) -> Optional[int]:
    if not filename:
        return None
    fn = filename.upper()
    # Common patterns: "_DI-1_", "DI-1", "DI 1"
    m = re.search(r"\bDI[-_ ]?([1-5])\b", fn)
    if m:
        try:
            return int(m.group(1))
        except Exception:
            return None
    return None


def _extract_di_from_text(text: str) -> Optional[int]:
    t = text or ""
    # If the report contains an explicit numeric statement (rare):
    # "Dysbiosis Index (DI): 1" or "DI: 3"
    m = re.search(r"(dysbiosis\s+index\s*\(di\)\s*[:=]\s*|di\s*[:=]\s*)([1-5])\b", t, re.IGNORECASE)
    if m:
        try:
            return int(m.group(2))
        except Exception:
            return None
    return None


def _infer_di_from_interpretation(text: str) -> Optional[int]:
    tl = _norm(text)

    # Direct interpretations commonly present in IDK GutMAP sample reports
    if "result: the microbiota is normobiotic" in tl or "microbiota is normobiotic" in tl:
        return 1  # safest default within "1–2"
    if "mildly dysbiotic" in tl:
        return 3
    if "severely dysbiotic" in tl:
        return 4

    # Generic fallbacks
    if "normobiotic" in tl:
        return 1
    if "dysbiotic" in tl and "mild" in tl:
        return 3
    if "dysbiotic" in tl and ("severe" in tl or "severely" in tl):
        return 4

    return None


def _extract_diversity(text: str) -> Dict[str, Any]:
    tl = _norm(text)

    # Typical sentence:
    # "Result: The bacterial diversity is as expected."
    # or "Result: The bacterial diversity is lower than expected."
    out: Dict[str, Any] = {}

    m = re.search(r"result:\s*the bacterial diversity is ([a-z ]+?)(?:\.|\n|$)", text, re.IGNORECASE)
    if m:
        phrase = _norm(m.group(1))
        out["diversity_shannon"] = phrase

        # Map to an ordinal (not the real Shannon index)
        if "as expected" in phrase or "expected" in phrase:
            out["shannon_index_numeric"] = 3
        elif "slightly" in phrase or "mild" in phrase:
            out["shannon_index_numeric"] = 2
        elif "lower" in phrase or "reduced" in phrase or "low" in phrase:
            out["shannon_index_numeric"] = 1
        else:
            out["shannon_index_numeric"] = 2
    else:
        # alternative wording sometimes seen
        if "bacterial diversity is as expected" in tl:
            out["diversity_shannon"] = "as expected"
            out["shannon_index_numeric"] = 3

    return out


def _presence_flags(text: str) -> Dict[str, bool]:
    tl = _norm(text)

    def has(term: str) -> bool:
        return term.lower() in tl

    return {
        "akkermansia_muciniphila_present": has("akkermansia muciniphila"),
        "faecalibacterium_prausnitzii_present": has("faecalibacterium prausnitzii"),
        "bifidobacterium_present": has("bifidobacterium"),
        "lactobacillus_present": has("lactobacillus"),
        "prevotella_present": has("prevotella"),
        "escherichia_coli_present": has("escherichia coli"),
        "clostridium_difficile_present": has("clostridium difficile"),
    }


def extract_microbiome_data(text: str, filename: Optional[str] = None, debug: bool = False) -> Dict[str, Any]:
    """
    Retourne un dictionnaire exploitable par l'UI Streamlit.

    Le dictionnaire peut contenir (selon disponibilité):
      - dysbiosis_index (int 1–5)
      - dysbiosis_status (str)
      - diversity_shannon (str)
      - shannon_index_numeric (int 1–3)
      - *_present (bool) pour quelques espèces clés
    """
    raw = text or ""
    data: Dict[str, Any] = {}

    # 1) DI
    di = _extract_di_from_text(raw)
    if di is None:
        di = _extract_di_from_filename(filename)
    if di is None:
        di = _infer_di_from_interpretation(raw)

    if di is not None:
        data["dysbiosis_index"] = int(di)
        if di <= 2:
            data["dysbiosis_status"] = "normobiotic"
        elif di == 3:
            data["dysbiosis_status"] = "mildly dysbiotic"
        else:
            data["dysbiosis_status"] = "severely dysbiotic"

    # 2) Diversity (Shannon - qualitative)
    data.update(_extract_diversity(raw))

    # 3) Presence flags
    data.update(_presence_flags(raw))

    # 4) Minimal sanity: if nothing extracted, return {}
    extracted_keys = [k for k, v in data.items() if v is not None]
    if debug:
        data["_debug"] = {
            "filename": filename,
            "keys": extracted_keys,
        }

    # Consider "useful" if DI or diversity or at least one key species present
    useful = ("dysbiosis_index" in data) or ("diversity_shannon" in data) or any(
        k.endswith("_present") and data.get(k) for k in data.keys()
    )

    return data if useful else {}
