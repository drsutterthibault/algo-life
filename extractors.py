from __future__ import annotations

import io
import re
from dataclasses import dataclass
from typing import Dict, Any, Optional, List, Tuple

import pandas as pd

# Optional PDF libs
PDF_OK = True
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


# -----------------------------
# Generic helpers
# -----------------------------
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

def _to_float(x: str) -> Optional[float]:
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

    if ext in {"csv"}:
        df = pd.read_csv(bio)
    else:
        # default first sheet
        df = pd.read_excel(bio)

    # Try to standardize columns if possible
    cols = {c.lower().strip(): c for c in df.columns}
    # candidates
    name_col = cols.get("biomarqueur") or cols.get("marqueur") or cols.get("analyte") or cols.get("nom") or cols.get("test")
    value_col = cols.get("valeur") or cols.get("resultat") or cols.get("résultat") or cols.get("result") or cols.get("value")
    unit_col = cols.get("unité") or cols.get("unite") or cols.get("unit")
    ref_low_col = cols.get("ref_low") or cols.get("bas") or cols.get("low") or cols.get("min") or cols.get("borne_inf")
    ref_high_col = cols.get("ref_high") or cols.get("haut") or cols.get("high") or cols.get("max") or cols.get("borne_sup")

    if name_col and value_col:
        out = pd.DataFrame({
            "marker": df[name_col].astype(str),
            "value": df[value_col].apply(_to_float),
            "unit": (df[unit_col].astype(str) if unit_col else None),
            "ref_low": (df[ref_low_col].apply(_to_float) if ref_low_col else None),
            "ref_high": (df[ref_high_col].apply(_to_float) if ref_high_col else None),
            "source": filename,
        })
        if unit_col is None:
            out["unit"] = None
        if ref_low_col is None:
            out["ref_low"] = None
        if ref_high_col is None:
            out["ref_high"] = None

        out = out.dropna(subset=["marker", "value"], how="any")
        out["marker_norm"] = out["marker"].apply(_normalize_marker_name)
        return out.reset_index(drop=True)

    # Otherwise: return as-is (user might have a custom format)
    df = df.copy()
    df["source"] = filename
    return df


# -----------------------------
# BIOLOGY PDF extraction (Synlab-like)
# -----------------------------
def _extract_biology_from_text(txt: str, filename: str) -> pd.DataFrame:
    """
    Targets common Synlab patterns.

    Patterns handled:
    1) "GLYCEMIE A JEUN 0.84 g/L (0.74 à 1.06)"
    2) "INSULINE * 2.94 mUI/L (3 à 25)"
    3) Belgian-like: "> Hémoglobine 12.9 11.5 - 16.0 g/dL"
    4) LBP style: "LBP(LPS-Binding-protein) 6.1 0-6.8:opt. 2.3-8.3:VN mg/L"
    """
    rows: List[Dict[str, Any]] = []
    lines = [l.strip() for l in txt.splitlines() if l.strip()]

    # Regex 1/2 (French parentheses refs)
    # marker ... value unit (low à high) OR (low - high)
    rx_paren = re.compile(
        r"^(?P<marker>[A-ZÀÂÄÇÉÈÊËÎÏÔÖÙÛÜŸÆŒ0-9\.\-\s\/]+?)\s+[*]?\s*(?P<value>-?\d+(?:[.,]\d+)?)\s*(?P<unit>[A-Za-zµ/%·\.\-\s]+)?\s*\(\s*(?P<low>-?\d+(?:[.,]\d+)?)\s*(?:à|a|\-)\s*(?P<high>-?\d+(?:[.,]\d+)?)\s*\)",
        re.IGNORECASE,
    )

    # Belgian style with reference range as separate columns
    rx_belg = re.compile(
        r"^>\s*(?P<marker>.+?)\s+(?P<value>-?\d+(?:[.,]\d+)?)\s+(?P<low>-?\d+(?:[.,]\d+)?)\s*[\-–]\s*(?P<high>-?\d+(?:[.,]\d+)?)\s+(?P<unit>[A-Za-zµ/%·\.\-]+)$",
        re.IGNORECASE,
    )

    # LBP special (has opt/VN blocks)
    rx_lbp = re.compile(
        r"^(?P<marker>LBP.*?|LPS[\-\s]*Binding.*?|LPS.*?Binding.*?|LBP)\s+(?P<value>-?\d+(?:[.,]\d+)?)\s+(?P<refs>.+?)\s+(?P<unit>[A-Za-zµ/%·\.\-]+)$",
        re.IGNORECASE,
    )

    # A "safe list" of header words to ignore
    ignore_prefix = (
        "EDITION", "NOM", "PRENOM", "DDN", "DOSSIER", "LABORATOIRE", "TEL", "WEB",
        "SITES", "DR", "FRANCELIS", "ANALYSES", "BIOCHIMIE", "CHIMIE", "IMMUNOLOGIE",
        "HORMONOLOGIE", "HEMATOLOGIE", "EQUILIBRE", "STATUT", "PERMEABILITE",
        "VALIDÉ", "VALIDE", "FIN DE", "ACCEDER", "VOTRE IDENTIFIANT", "PAGE"
    )

    def is_noise(line: str) -> bool:
        up = line.upper()
        if any(up.startswith(p) for p in ignore_prefix):
            return True
        # too long narrative lines
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
                rows.append({
                    "marker": marker,
                    "value": value,
                    "unit": unit if unit else None,
                    "ref_low": low,
                    "ref_high": high,
                    "source": filename,
                })
            continue

        m = rx_belg.match(line)
        if m:
            marker = _clean_spaces(m.group("marker"))
            value = _to_float(m.group("value"))
            low = _to_float(m.group("low"))
            high = _to_float(m.group("high"))
            unit = _clean_spaces(m.group("unit") or "")
            if marker and value is not None:
                rows.append({
                    "marker": marker,
                    "value": value,
                    "unit": unit if unit else None,
                    "ref_low": low,
                    "ref_high": high,
                    "source": filename,
                })
            continue

        m = rx_lbp.match(line)
        if m:
            marker = _clean_spaces(m.group("marker"))
            value = _to_float(m.group("value"))
            unit = _clean_spaces(m.group("unit") or "")
            # try to parse VN range "x-y:VN"
            refs = m.group("refs")
            vn = None
            vn2 = None
            # Example: "0-6.8:opt. 2.3-8.3:VN"
            m2 = re.search(r"(\d+(?:[.,]\d+)?)\s*[\-–]\s*(\d+(?:[.,]\d+)?)\s*:\s*VN", refs, flags=re.I)
            if m2:
                vn = _to_float(m2.group(1))
                vn2 = _to_float(m2.group(2))
            rows.append({
                "marker": marker,
                "value": value,
                "unit": unit if unit else None,
                "ref_low": vn,
                "ref_high": vn2,
                "source": filename,
            })
            continue

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    df["marker_norm"] = df["marker"].astype(str).apply(_normalize_marker_name)
    # Drop obvious duplicates
    df = df.drop_duplicates(subset=["marker_norm", "value", "unit"], keep="first")
    return df.reset_index(drop=True)


# -----------------------------
# MICROBIOME PDF extraction (IDK GutMAP - functional markers)
# -----------------------------
def _extract_microbiome_from_text(txt: str, filename: str) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    For GutMAP PDF: we reliably extract:
    - Dysbiosis result category (normobiotic / mildly dysbiotic / severely dysbiotic) -> DI score proxy
    - Diversity result (as expected / slightly lower / lower than expected)

    Additionally, we attempt to extract group-level 'Result: expected abundance ...' statements,
    but those are usually not enough for per-bacteria marker rules (can be expanded later).
    """
    meta: Dict[str, Any] = {"source": filename}
    t = txt

    # Dysbiosis "Result: The microbiota is normobiotic" etc.
    di_status = None
    if re.search(r"\bnormobiotic\b", t, flags=re.I):
        di_status = "normobiotic"
        di_score = 2  # proxy 1-2
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

    # Diversity
    diversity = None
    if re.search(r"diversity is as expected", t, flags=re.I):
        diversity = "as_expected"
    elif re.search(r"slightly lower than expected", t, flags=re.I):
        diversity = "slightly_lower_than_expected"
    elif re.search(r"lower than expected", t, flags=re.I):
        diversity = "lower_than_expected"

    meta["diversity_status"] = diversity

    # Try capture "Result: (expected|slightly deviating|deviating) abundance of these bacteria."
    group_hits = re.findall(
        r"Result:\s*(expected|slightly deviating|deviating)\s+abundance of these bacteria",
        t,
        flags=re.I,
    )
    meta["group_results_counts"] = {
        "expected": sum(1 for x in group_hits if x.lower().startswith("expected")),
        "slightly_deviating": sum(1 for x in group_hits if x.lower().startswith("slightly")),
        "deviating": sum(1 for x in group_hits if x.lower().startswith("deviating")),
    }

    # Build a minimal DF for functional markers (so we can display & export)
    rows = []
    if di_score is not None:
        rows.append({
            "marker": "Dysbiosis Index (DI)",
            "value": float(di_score),
            "unit": "score_proxy",
            "ref_low": 1.0,
            "ref_high": 2.0,
            "source": filename,
            "marker_norm": _normalize_marker_name("Dysbiosis Index (DI)"),
        })
    if diversity is not None:
        # encode diversity as ordinal
        # as_expected=0 (normal), slightly_lower=1, lower=2
        dv = {"as_expected": 0, "slightly_lower_than_expected": 1, "lower_than_expected": 2}[diversity]
        rows.append({
            "marker": "Shannon Diversity Index",
            "value": float(dv),
            "unit": "ordinal_proxy",
            "ref_low": 0.0,
            "ref_high": 0.0,
            "source": filename,
            "marker_norm": _normalize_marker_name("Shannon Diversity Index"),
        })

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
    elif ext == "pdf":
        txt = _read_text_from_pdf(file_bytes)
        df = _extract_biology_from_text(txt, filename)
        return ExtractionResult(data=df, meta={"kind": "biology", "input": "pdf"}, raw_text=txt)
    else:
        raise ValueError(f"Format non supporté pour biologie: {filename}")

def extract_microbiome_any(file_bytes: bytes, filename: str) -> ExtractionResult:
    ext = _ext(filename)
    if ext in {"xlsx", "xls", "csv"}:
        df = _read_table_from_excel_or_csv(file_bytes, filename)
        meta = {"kind": "microbiome", "input": ext}
        return ExtractionResult(data=df, meta=meta, raw_text="")
    elif ext == "pdf":
        txt = _read_text_from_pdf(file_bytes)
        df, meta = _extract_microbiome_from_text(txt, filename)
        meta["kind"] = "microbiome"
        meta["input"] = "pdf"
        return ExtractionResult(data=df, meta=meta, raw_text=txt)
    else:
        raise ValueError(f"Format non supporté pour microbiote: {filename}")
