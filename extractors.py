from __future__ import annotations

import io
import re
from dataclasses import dataclass
from typing import Dict, Any, Optional, List, Tuple

import pandas as pd

# Optional PDF libs
try:
    import pdfplumber  # type: ignore
except Exception:
    pdfplumber = None

try:
    import PyPDF2  # type: ignore
except Exception:
    PyPDF2 = None


@dataclass
class ExtractionResult:
    data: pd.DataFrame
    meta: Dict[str, Any]
    raw_text: str


def _ext(filename: str) -> str:
    return filename.lower().split(".")[-1].strip()


def _read_text_from_pdf(file_bytes: bytes) -> str:
    # Prefer pdfplumber (often better extraction), fallback PyPDF2
    if pdfplumber is not None:
        out = []
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                txt = page.extract_text() or ""
                out.append(txt)
        return "\n".join(out)

    if PyPDF2 is not None:
        reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        out = []
        for p in reader.pages:
            out.append((p.extract_text() or ""))
        return "\n".join(out)

    raise RuntimeError("Aucune lib PDF dispo (installe pdfplumber ou PyPDF2).")


def _to_float(x: Any) -> Optional[float]:
    if x is None:
        return None
    s = str(x).strip()
    s = s.replace(",", ".")
    s = re.sub(r"[^\d\.\-]+", "", s)
    if not s or s in {".", "-", "-."}:
        return None
    try:
        return float(s)
    except Exception:
        return None


def _clean_spaces(s: str) -> str:
    return re.sub(r"[ \t]+", " ", s).strip()


def _normalize_marker_name(s: str) -> str:
    s = s or ""
    s = s.upper()
    s = re.sub(r"\(.*?\)", "", s)  # drop parentheses content
    s = re.sub(r"[^A-Z0-9ÀÂÄÇÉÈÊËÎÏÔÖÙÛÜŸÆŒ \-\/]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


# -----------------------------
# Excel/CSV import
# -----------------------------
def _read_table_from_excel_or_csv(file_bytes: bytes, filename: str) -> pd.DataFrame:
    ext = _ext(filename)
    bio = io.BytesIO(file_bytes)

    if ext == "csv":
        df = pd.read_csv(bio)
    else:
        df = pd.read_excel(bio)

    # Try to standardize columns if possible
    cols = {c.lower().strip(): c for c in df.columns}

    name_col = (
        cols.get("biomarqueur")
        or cols.get("marqueur")
        or cols.get("analyte")
        or cols.get("nom")
        or cols.get("test")
    )
    value_col = (
        cols.get("valeur")
        or cols.get("resultat")
        or cols.get("résultat")
        or cols.get("result")
        or cols.get("value")
    )
    unit_col = cols.get("unité") or cols.get("unite") or cols.get("unit")
    ref_low_col = cols.get("ref_low") or cols.get("bas") or cols.get("low") or cols.get("min") or cols.get("borne_inf")
    ref_high_col = cols.get("ref_high") or cols.get("haut") or cols.get("high") or cols.get("max") or cols.get("borne_sup")

    if name_col and value_col:
        out = pd.DataFrame(
            {
                "marker": df[name_col].astype(str),
                "value": df[value_col].apply(_to_float),
                "unit": (df[unit_col].astype(str) if unit_col else None),
                "ref_low": (df[ref_low_col].apply(_to_float) if ref_low_col else None),
                "ref_high": (df[ref_high_col].apply(_to_float) if ref_high_col else None),
                "source": filename,
            }
        )
        if unit_col is None:
            out["unit"] = None
        if ref_low_col is None:
            out["ref_low"] = None
        if ref_high_col is None:
            out["ref_high"] = None

        out = out.dropna(subset=["marker", "value"], how="any")
        out["marker_norm"] = out["marker"].apply(_normalize_marker_name)
        return out.reset_index(drop=True)

    df = df.copy()
    df["source"] = filename
    return df


# -----------------------------
# BIOLOGY PDF extraction (Synlab-like)
# -----------------------------
def _extract_biology_from_text(txt: str, filename: str) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    lines = [l.strip() for l in txt.splitlines() if l.strip()]

    rx_paren = re.compile(
        r"^(?P<marker>[A-ZÀÂÄÇÉÈÊËÎÏÔÖÙÛÜŸÆŒ0-9\.\-\s\/]+?)\s+[*]?\s*(?P<value>-?\d+(?:[.,]\d+)?)\s*(?P<unit>[A-Za-zµ/%·\.\-\s]+)?\s*\(\s*(?P<low>-?\d+(?:[.,]\d+)?)\s*(?:à|a|\-)\s*(?P<high>-?\d+(?:[.,]\d+)?)\s*\)",
        re.IGNORECASE,
    )

    rx_belg = re.compile(
        r"^>\s*(?P<marker>.+?)\s+(?P<value>-?\d+(?:[.,]\d+)?)\s+(?P<low>-?\d+(?:[.,]\d+)?)\s*[\-–]\s*(?P<high>-?\d+(?:[.,]\d+)?)\s+(?P<unit>[A-Za-zµ/%·\.\-]+)$",
        re.IGNORECASE,
    )

    ignore_prefix = (
        "EDITION", "NOM", "PRENOM", "DDN", "DOSSIER", "LABORATOIRE", "TEL", "WEB",
        "SITES", "DR", "ANALYSES", "BIOCHIMIE", "CHIMIE", "IMMUNOLOGIE",
        "HORMONOLOGIE", "HEMATOLOGIE", "VALIDÉ", "VALIDE", "FIN DE", "PAGE"
    )

    def is_noise(line: str) -> bool:
        up = line.upper()
        if any(up.startswith(p) for p in ignore_prefix):
            return True
        if len(line) > 140 and not re.search(r"\d", line):
            return True
        return False

    for line in lines:
        if is_noise(line):
            continue

        m = rx_paren.match(line)
        if m:
            marker = _clean_spaces(m.group("marker"))
            value = _to_float(m.group("value"))
            unit = _clean_spaces(m.group("unit") or "")
            low = _to_float(m.group("low"))
            high = _to_float(m.group("high"))
            if marker and value is not None:
                rows.append(
                    {
                        "marker": marker,
                        "value": value,
                        "unit": unit if unit else None,
                        "ref_low": low,
                        "ref_high": high,
                        "source": filename,
                    }
                )
            continue

        m = rx_belg.match(line)
        if m:
            marker = _clean_spaces(m.group("marker"))
            value = _to_float(m.group("value"))
            low = _to_float(m.group("low"))
            high = _to_float(m.group("high"))
            unit = _clean_spaces(m.group("unit") or "")
            if marker and value is not None:
                rows.append(
                    {
                        "marker": marker,
                        "value": value,
                        "unit": unit if unit else None,
                        "ref_low": low,
                        "ref_high": high,
                        "source": filename,
                    }
                )
            continue

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    df["marker_norm"] = df["marker"].astype(str).apply(_normalize_marker_name)
    df = df.drop_duplicates(subset=["marker_norm", "value", "unit"], keep="first")
    return df.reset_index(drop=True)


# -----------------------------
# MICROBIOME PDF extraction (GutMAP: functional markers)
# -----------------------------
def _extract_microbiome_from_text(txt: str, filename: str) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    meta: Dict[str, Any] = {"source": filename}
    t = txt

    di_status = None
    if re.search(r"\bnormobiotic\b", t, flags=re.I):
        di_status = "normobiotic"
        di_score = 2
    elif re.search(r"\bmildly\s+dysbiotic\b", t, flags=re.I):
        di_status = "mildly_dysbiotic"
        di_score = 3
    elif re.search(r"\bseverely\s+dysbiotic\b", t, flags=re.I):
        di_status = "severely_dysbiotic"
        di_score = 5
    else:
        di_score = None

    meta["dysbiosis_status"] = di_status
    meta["dysbiosis_index_score_proxy"] = di_score

    diversity = None
    if re.search(r"diversity is as expected", t, flags=re.I):
        diversity = "as_expected"
    elif re.search(r"slightly lower than expected", t, flags=re.I):
        diversity = "slightly_lower_than_expected"
    elif re.search(r"lower than expected", t, flags=re.I):
        diversity = "lower_than_expected"
    meta["diversity_status"] = diversity

    rows = []
    if di_score is not None:
        rows.append(
            {
                "marker": "Dysbiosis Index (DI)",
                "value": float(di_score),
                "unit": "score_proxy",
                "ref_low": 1.0,
                "ref_high": 2.0,
                "source": filename,
                "marker_norm": _normalize_marker_name("Dysbiosis Index (DI)"),
            }
        )
    if diversity is not None:
        dv = {"as_expected": 0, "slightly_lower_than_expected": 1, "lower_than_expected": 2}[diversity]
        rows.append(
            {
                "marker": "Shannon Diversity Index",
                "value": float(dv),
                "unit": "ordinal_proxy",
                "ref_low": 0.0,
                "ref_high": 0.0,
                "source": filename,
                "marker_norm": _normalize_marker_name("Shannon Diversity Index"),
            }
        )

    df = pd.DataFrame(rows)
    return df, meta


# -----------------------------
# Public API
# -----------------------------
def extract_biology_any(file_bytes: bytes, filename: str) -> ExtractionResult:
    ext = _ext(filename)
    if ext in {"xlsx", "xls", "csv"}:
        df = _read_table_from_excel_or_csv(file_bytes, filename)
        return ExtractionResult(data=df, meta={"kind": "biology", "input": ext}, raw_text="")
    if ext == "pdf":
        txt = _read_text_from_pdf(file_bytes)
        df = _extract_biology_from_text(txt, filename)
        return ExtractionResult(data=df, meta={"kind": "biology", "input": "pdf"}, raw_text=txt)
    raise ValueError(f"Format non supporté pour biologie: {filename}")


def extract_microbiome_any(file_bytes: bytes, filename: str) -> ExtractionResult:
    ext = _ext(filename)
    if ext in {"xlsx", "xls", "csv"}:
        df = _read_table_from_excel_or_csv(file_bytes, filename)
        meta = {"kind": "microbiome", "input": ext}
        return ExtractionResult(data=df, meta=meta, raw_text="")
    if ext == "pdf":
        txt = _read_text_from_pdf(file_bytes)
        df, meta = _extract_microbiome_from_text(txt, filename)
        meta["kind"] = "microbiome"
        meta["input"] = "pdf"
        return ExtractionResult(data=df, meta=meta, raw_text=txt)
    raise ValueError(f"Format non supporté pour microbiote: {filename}")
