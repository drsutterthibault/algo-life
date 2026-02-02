"""
microbiome_extractor_idk_gutmap.py
ALGO-LIFE – Extracteur Microbiote (IDK GutMAP / report type "Dysbiosis Index" + "Bacterial diversity")

Pourquoi ce fichier ?
- Sur certains PDF GutMAP, les valeurs (DI 1–5, diversité, z-scores) sont rendues sous forme de tableaux/indicateurs graphiques.
- Une extraction "texte seul" (PyPDF2) ne récupère pas ces infos => "Aucune donnée".
- Cet extracteur tente :
  1) extraction depuis le TEXTE (si présent),
  2) extraction depuis les TABLES PDF via pdfplumber (robuste pour DI 1–5),
  3) fallback OCR (optionnel) pour capturer des libellés simples si besoin.

Usage dans app.py (recommandé) :
    from microbiome_extractor_idk_gutmap import extract_microbiome_data

    text = AdvancedPDFExtractor.extract_text(microbiome_pdf)
    microbiome_data = extract_microbiome_data(text, pdf_file=microbiome_pdf, debug=True)

NB: pdf_file doit être l'objet Streamlit UploadedFile (ou bytes / path).
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Union
import io
import re

# Tables PDF
try:
    import pdfplumber  # type: ignore
    PDFPLUMBER_OK = True
except Exception:
    pdfplumber = None
    PDFPLUMBER_OK = False

# OCR optionnel
try:
    from PIL import Image  # type: ignore
    import pytesseract  # type: ignore
    OCR_OK = True
except Exception:
    Image = None
    pytesseract = None
    OCR_OK = False


UploadedLike = Union[bytes, bytearray, str, Any]  # str=path, Any=Streamlit UploadedFile


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def _to_bytes(pdf_file: UploadedLike) -> Optional[bytes]:
    """Convertit un fichier (Streamlit UploadedFile / path / bytes) en bytes."""
    if pdf_file is None:
        return None
    if isinstance(pdf_file, (bytes, bytearray)):
        return bytes(pdf_file)
    if isinstance(pdf_file, str):
        try:
            with open(pdf_file, "rb") as f:
                return f.read()
        except Exception:
            return None
    # Streamlit UploadedFile a .getvalue() ou .read()
    for attr in ("getvalue", "read"):
        if hasattr(pdf_file, attr):
            try:
                data = getattr(pdf_file, attr)()
                if isinstance(data, (bytes, bytearray)):
                    return bytes(data)
            except Exception:
                pass
    return None


def _debug_add(debug: bool, out: Dict, key: str, value: Any) -> None:
    if debug:
        out.setdefault("_debug", {})
        out["_debug"][key] = value


def _normalize_text(text: str) -> str:
    text = text or ""
    return re.sub(r"\s+", " ", text).strip()


# ---------------------------------------------------------------------
# Extraction TEXTE (si le PDF contient bien les valeurs en texte)
# ---------------------------------------------------------------------

def _extract_from_text(text: str, debug: bool = False) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    t = (text or "").lower()

    # Dysbiosis index: parfois écrit explicitement "Dysbiosis index: 2"
    m = re.search(r"dysbiosis\s*index\s*[:\-]?\s*(\d)\s*/?\s*5?", t)
    if m:
        try:
            out["dysbiosis_index"] = int(m.group(1))
        except Exception:
            pass

    # Diversité: phrases types
    # "The bacterial diversity is as expected" / "slightly lower than expected" / "lower than expected"
    if "bacterial diversity" in t and "expected" in t:
        if "slightly lower than expected" in t:
            out["diversity_shannon"] = "slightly lower than expected"
            out["shannon_index_numeric"] = 2
        elif "lower than expected" in t:
            out["diversity_shannon"] = "lower than expected"
            out["shannon_index_numeric"] = 1
        elif "as expected" in t:
            out["diversity_shannon"] = "as expected"
            out["shannon_index_numeric"] = 3

    # Ratio Firmicutes/Bacteroidetes: parfois écrit
    m = re.search(r"firmicutes\s*/\s*bacteroidetes\s*ratio\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)", t)
    if m:
        try:
            out["firmicutes_bacteroidetes_ratio"] = float(m.group(1))
        except Exception:
            pass

    _debug_add(debug, out, "from_text_keys", list(out.keys()))
    return out


# ---------------------------------------------------------------------
# Extraction TABLES via pdfplumber (robuste pour GutMAP DI 1–5)
# ---------------------------------------------------------------------

def _guess_selected_index_from_row(row: list) -> Optional[int]:
    """
    GutMAP a souvent une ligne type: ["11","2","3","4","5"] ou ["1","22","3","4","5"] etc.
    Le chiffre sélectionné apparaît parfois doublé ("11" => 1 sélectionné, "22" => 2 sélectionné).
    """
    if not row:
        return None
    cells = [(c or "").strip() for c in row if c is not None]
    if len(cells) < 5:
        return None

    # Garder uniquement ce qui ressemble à 1..5
    cleaned = []
    for c in cells:
        # enlever caractères non digit
        d = re.sub(r"[^\d]", "", c)
        if d:
            cleaned.append(d)

    # Exemples: ["11","2","3","4","5"] => 1
    #          ["1","22","3","4","5"] => 2
    #          ["1","2","33","4","5"] => 3
    for i in range(1, 6):
        token = str(i) * 2
        if token in cleaned:
            return i

    # Fallback: si une cellule contient "1" + un autre caractère non digit (rare)
    # ou si une cellule contient plus d'un digit dont tous identiques.
    for c in cleaned:
        if len(c) >= 2 and len(set(c)) == 1:
            v = int(c[0])
            if 1 <= v <= 5:
                return v

    return None


def _extract_from_tables(pdf_bytes: bytes, debug: bool = False) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    if not (PDFPLUMBER_OK and pdf_bytes):
        _debug_add(debug, out, "tables", "pdfplumber_not_available_or_empty_pdf")
        return out

    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            tables_found = 0
            di_candidates = []
            for page_i, page in enumerate(pdf.pages[:3]):  # DI est généralement en page 1
                tables = page.extract_tables() or []
                tables_found += len(tables)
                for tbl in tables:
                    for row in tbl:
                        sel = _guess_selected_index_from_row(row)
                        if sel is not None:
                            di_candidates.append((page_i, sel, row))
            _debug_add(debug, out, "tables_found", tables_found)
            _debug_add(debug, out, "di_candidates", di_candidates[:5])

            if di_candidates:
                # prendre le premier (souvent unique)
                out["dysbiosis_index"] = int(di_candidates[0][1])

    except Exception as e:
        _debug_add(debug, out, "tables_error", str(e))

    return out


# ---------------------------------------------------------------------
# OCR fallback (optionnel)
# ---------------------------------------------------------------------

def _extract_from_ocr(pdf_bytes: bytes, debug: bool = False) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    if not (OCR_OK and PDFPLUMBER_OK and pdf_bytes):
        _debug_add(debug, out, "ocr", "ocr_not_available_or_pdfplumber_missing_or_empty_pdf")
        return out

    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            # OCR uniquement sur la 1ère page pour rester léger
            page = pdf.pages[0]
            pil_img = page.to_image(resolution=200).original
            ocr_text = pytesseract.image_to_string(pil_img, config="--psm 6")
            o = ocr_text.lower()

            # même logique que texte
            tmp = _extract_from_text(ocr_text, debug=False)
            out.update(tmp)

            _debug_add(debug, out, "ocr_len", len(ocr_text))
    except Exception as e:
        _debug_add(debug, out, "ocr_error", str(e))

    return out


# ---------------------------------------------------------------------
# API publique
# ---------------------------------------------------------------------

def extract_microbiome_data(
    text: str,
    pdf_file: Optional[UploadedLike] = None,
    debug: bool = False,
) -> Dict[str, Any]:
    """
    Retourne un dict de paramètres microbiote.
    Clés possibles:
      - dysbiosis_index: int (1..5)
      - diversity_shannon: str ("as expected" / "slightly lower than expected" / "lower than expected")
      - shannon_index_numeric: int (1..3)
      - firmicutes_bacteroidetes_ratio: float (si présent en texte)

    Pour les bactéries individuelles (Akkermansia, Faecalibacterium, etc.):
      - sur de nombreux GutMAP, ce sont des barres/z-scores graphiques non textuels.
      - nécessiterait OCR ciblé par zones (plus lourd). On peut l’ajouter ensuite si tu veux.
    """
    out: Dict[str, Any] = {}

    # 1) texte (rapide)
    out.update(_extract_from_text(text, debug=debug))

    # 2) tables (si pdf fourni)
    pdf_bytes = _to_bytes(pdf_file) if pdf_file is not None else None
    if pdf_bytes:
        tbl = _extract_from_tables(pdf_bytes, debug=debug)
        for k, v in tbl.items():
            out.setdefault(k, v)

    # 3) OCR léger si toujours vide
    if pdf_bytes and not any(k in out for k in ("dysbiosis_index", "diversity_shannon", "shannon_index_numeric")):
        ocr = _extract_from_ocr(pdf_bytes, debug=debug)
        for k, v in ocr.items():
            out.setdefault(k, v)

    # Nettoyage debug
    if not debug and "_debug" in out:
        out.pop("_debug", None)

    return out
