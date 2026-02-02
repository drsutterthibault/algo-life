# -*- coding: utf-8 -*-
"""
IDK / GutMAP Microbiome Extractor (robuste)
- 1) Utilise le texte "universal extractor" si dispo
- 2) Fallback: relit le PDF en mode layout (pdfplumber) si pdf_bytes fourni
- 3) Regex robustes pour dysbiosis / shannon / ratios + quelques espèces clés
"""

from __future__ import annotations

import re
from io import BytesIO
from typing import Dict, Optional, Tuple

# pdfplumber en fallback (optionnel)
try:
    import pdfplumber  # type: ignore
    PDFPLUMBER_OK = True
except Exception:
    PDFPLUMBER_OK = False


# ----------------------------
# Utils
# ----------------------------

def _to_float(x: str) -> Optional[float]:
    if x is None:
        return None
    s = x.strip().replace(",", ".")
    # garde signe +/-
    s = re.sub(r"[^\d\.\-\+]", "", s)
    if s in ("", "+", "-"):
        return None
    try:
        return float(s)
    except Exception:
        return None


def _norm_text(t: str) -> str:
    # normalise espaces / tirets / caractères invisibles
    t = t.replace("\u00a0", " ")
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t


def _extract_with_pdfplumber(pdf_bytes: bytes) -> str:
    if not PDFPLUMBER_OK:
        return ""
    out = []
    with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            # extraction "layout" + tables si possible
            txt = page.extract_text(x_tolerance=2, y_tolerance=2) or ""
            out.append(txt)

            # tables (si présentes)
            try:
                tables = page.extract_tables() or []
                for tbl in tables:
                    for row in tbl:
                        if not row:
                            continue
                        out.append(" | ".join([(c or "") for c in row]))
            except Exception:
                pass

    return _norm_text("\n".join(out))


def _pick_first(patterns, text: str) -> Optional[str]:
    for p in patterns:
        m = re.search(p, text, flags=re.IGNORECASE)
        if m:
            return m.group(1)
    return None


# ----------------------------
# Core extraction
# ----------------------------

def extract_microbiome_data(
    text: str,
    pdf_bytes: Optional[bytes] = None,
    debug: bool = False,
) -> Dict[str, float]:
    """
    Retourne un dict de features microbiote:
    - dysbiosis_index
    - shannon_index_numeric + diversity_shannon (label)
    - firmicutes_bacteroidetes_ratio
    - quelques espèces clés si présentes (z-scores ou log-abundance)
    """

    if text is None:
        text = ""
    text0 = _norm_text(text)

    # Fallback PDF layout si texte trop pauvre
    if (len(text0.strip()) < 300) and pdf_bytes:
        layout_text = _extract_with_pdfplumber(pdf_bytes)
        if len(layout_text.strip()) > len(text0.strip()):
            text0 = layout_text

    # Normalise pour recherche
    t = text0

    data: Dict[str, float] = {}

    # ---- Dysbiosis Index (souvent 1–5)
    dys = _pick_first(
        [
            r"dysbiosis\s*index\s*[:\-]?\s*([0-9](?:\.[0-9])?)\s*/\s*5",
            r"dysbiosis\s*index\s*[:\-]?\s*([0-9](?:\.[0-9])?)\b",
            r"index\s*de\s*dysbiose\s*[:\-]?\s*([0-9](?:\.[0-9])?)\s*/\s*5",
            r"index\s*de\s*dysbiose\s*[:\-]?\s*([0-9](?:\.[0-9])?)\b",
        ],
        t,
    )
    dys_f = _to_float(dys) if dys else None
    if dys_f is not None:
        # clamp raisonnable
        if dys_f < 0:
            dys_f = 0.0
        if dys_f > 5:
            dys_f = 5.0
        data["dysbiosis_index"] = float(round(dys_f, 2))

    # ---- Shannon diversity (parfois un score + label)
    sh = _pick_first(
        [
            r"shannon\s*(?:diversity|index)\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)",
            r"diversit[ée]\s*\(shannon\)\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)",
        ],
        t,
    )
    sh_f = _to_float(sh) if sh else None
    if sh_f is not None:
        data["shannon_index_numeric"] = float(round(sh_f, 3))
        # label simple
        if sh_f >= 3.5:
            data["diversity_shannon"] = 3.0  # "haute" (mappé sur 3)
        elif sh_f >= 2.5:
            data["diversity_shannon"] = 2.0  # "moyenne"
        else:
            data["diversity_shannon"] = 1.0  # "basse"

    # ---- Firmicutes/Bacteroidetes ratio
    fb = _pick_first(
        [
            r"firmicutes\s*/\s*bacteroidetes\s*(?:ratio)?\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)",
            r"f\s*/\s*b\s*(?:ratio)?\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)",
        ],
        t,
    )
    fb_f = _to_float(fb) if fb else None
    if fb_f is not None:
        data["firmicutes_bacteroidetes_ratio"] = float(round(fb_f, 3))

    # ---- Espèces clés (souvent en Z-score / log)
    # On prend la valeur numérique sur la même ligne si trouvée
    species_patterns = {
        "akkermansia_muciniphila": [
            r"akkermansia\s*muciniphila[^0-9\-\+]*([\-+]?\d+(?:\.\d+)?)",
        ],
        "faecalibacterium_prausnitzii": [
            r"faecalibacterium\s*prausnitzii[^0-9\-\+]*([\-+]?\d+(?:\.\d+)?)",
        ],
        "bifidobacterium": [
            r"bifidobacterium[^0-9\-\+]*([\-+]?\d+(?:\.\d+)?)",
        ],
        "lactobacillus": [
            r"lactobacillus[^0-9\-\+]*([\-+]?\d+(?:\.\d+)?)",
        ],
        "escherichia_coli": [
            r"escherichia\s*coli[^0-9\-\+]*([\-+]?\d+(?:\.\d+)?)",
        ],
    }

    for key, pats in species_patterns.items():
        val = _pick_first(pats, t)
        fv = _to_float(val) if val else None
        if fv is not None:
            data[key] = float(round(fv, 3))

    if debug:
        # On met au moins un indicateur si rien trouvé
        data["_debug_text_len"] = float(len(t))

    # Nettoyage : enlever debug si vide utile
    if not debug and "_debug_text_len" in data:
        data.pop("_debug_text_len", None)

    return data
