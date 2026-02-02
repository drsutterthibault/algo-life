from __future__ import annotations

import io
import re
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd


# -----------------------------
# Utils
# -----------------------------
def _to_float(x: Any) -> Optional[float]:
    if x is None:
        return None
    s = str(x).strip().replace(",", ".")
    s = re.sub(r"[^0-9\.\-]+", "", s)
    if s == "" or s in {".", "-", "-."}:
        return None
    try:
        return float(s)
    except Exception:
        return None


def _norm(s: str) -> str:
    s = (s or "").upper()
    # remove parentheses content
    s = re.sub(r"\(.*?\)", "", s)
    # keep only safe chars
    s = re.sub(r"[^A-Z0-9ÀÂÄÇÉÈÊËÎÏÔÖÙÛÜŸÆŒ \-\/]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _parse_range(cell: Any) -> Tuple[Optional[float], Optional[float]]:
    """
    Parses strings like:
    - "0.74 - 1.06"
    - "0,74 à 1,06"
    - "11.5–16.0"
    - "11.5—16.0"
    """
    if cell is None:
        return None, None
    if isinstance(cell, float) and pd.isna(cell):
        return None, None

    txt = str(cell)
    # normalize dashes and separators
    txt = txt.replace("—", "-").replace("–", "-")
    txt = txt.replace(" à ", "-").replace(" a ", "-")

    m = re.search(r"(-?\d+(?:[.,]\d+)?)\s*-\s*(-?\d+(?:[.,]\d+)?)", txt)
    if not m:
        return None, None

    lo = _to_float(m.group(1))
    hi = _to_float(m.group(2))
    return lo, hi


# -----------------------------
# Load rules
# -----------------------------
def load_rules_from_excel_bytes(file_bytes: bytes) -> Dict[str, pd.DataFrame]:
    bio = io.BytesIO(file_bytes)
    xls = pd.ExcelFile(bio)
    out: Dict[str, pd.DataFrame] = {}
    for sh in xls.sheet_names:
        bio.seek(0)
        out[sh] = pd.read_excel(bio, sheet_name=sh)
    return out


# -----------------------------
# Matching Bio rules
# -----------------------------
def _best_match_row_bio(rules_df: pd.DataFrame, marker_norm: str) -> Optional[pd.Series]:
    if rules_df is None or rules_df.empty:
        return None

    # find biomarker name column
    name_col = None
    for c in rules_df.columns:
        lc = str(c).strip().lower()
        if lc in {"biomarqueur", "marqueur"}:
            name_col = c
            break
    if name_col is None:
        return None

    target_tokens = set(marker_norm.split())
    best_row = None
    best_score = 0

    for _, r in rules_df.iterrows():
        name = str(r.get(name_col, "") or "")
        name_n = _norm(name)
        if not name_n:
            continue

        tokens = set(name_n.split())
        score = len(target_tokens.intersection(tokens))
        if name_n in marker_norm or marker_norm in name_n:
            score += 5

        if score > best_score:
            best_score = score
            best_row = r

    if best_row is None or best_score < 2:
        return None
    return best_row


def _status_from_ranges(value: float, low: Optional[float], high: Optional[float]) -> str:
    if low is not None and value < low:
        return "low"
    if high is not None and value > high:
        return "high"
    return "normal"


# -----------------------------
# Microbiome mapping (DI + Shannon proxies)
# -----------------------------
def _micro_di_to_rule_id(di_score: Optional[int]) -> Optional[str]:
    if di_score is None:
        return None
    if di_score <= 2:
        return None
    if di_score == 3:
        return "DI_UP11"
    if di_score == 4:
        return "DI_UP22"
    return "DI_UP33"


def _micro_div_to_rule_id(div_status: Optional[str]) -> Optional[str]:
    if not div_status:
        return None
    if div_status == "as_expected":
        return None
    if div_status == "slightly_lower_than_expected":
        return "SHANNON_DOWN11"
    return "SHANNON_DOWN22"


def _pick_micro_rule_row(micro_rules: pd.DataFrame, rule_id: str) -> Optional[pd.Series]:
    if micro_rules is None or micro_rules.empty:
        return None
    if "ID_marqueur" not in micro_rules.columns:
        return None
    mask = micro_rules["ID_marqueur"].astype(str).str.strip() == str(rule_id).strip()
    sub = micro_rules.loc[mask]
    if sub.empty:
        return None
    return sub.iloc[0]


# -----------------------------
# Main recommendation engine
# -----------------------------
def generate_recommendations_multimodal(
    rules: Dict[str, pd.DataFrame],
    sex: str,
    bio_df: pd.DataFrame,
    micro_meta: Dict[str, Any],
    micro_df: pd.DataFrame,
) -> List[Dict[str, Any]]:
    recos: List[Dict[str, Any]] = []

    sx = (sex or "F").upper().strip()
    sx = "H" if sx.startswith("H") else "F"

    # -------- BIO --------
    bio_sheets = []
    for k in ("BASE_40", "EXTENDED_92", "FONCTIONNEL_134"):
        if k in rules:
            bio_sheets.append(k)

    if bio_sheets:
        bio_rules = pd.concat([rules[k] for k in bio_sheets], ignore_index=True)
    else:
        bio_rules = pd.DataFrame()

    if bio_df is not None and not bio_df.empty and not bio_rules.empty:
        for _, r in bio_df.iterrows():
            marker = str(r.get("marker", "") or "")
            marker_norm = str(r.get("marker_norm", "") or "")
            if not marker_norm:
                marker_norm = _norm(marker)

            v = r.get("value", None)
            if v is None or (isinstance(v, float) and pd.isna(v)):
                continue
            try:
                value_f = float(v)
            except Exception:
                continue

            rule_row = _best_match_row_bio(bio_rules, marker_norm)
            if rule_row is None:
                continue

            # prefer extracted refs; else Excel norms
            lo = r.get("ref_low", None)
            hi = r.get("ref_high", None)
            lo = None if lo is None or (isinstance(lo, float) and pd.isna(lo)) else float(lo)
            hi = None if hi is None or (isinstance(hi, float) and pd.isna(hi)) else float(hi)

            if lo is None and hi is None:
                col_range = "Normes H" if sx == "H" else "Normes F"
                lo2, hi2 = _parse_range(rule_row.get(col_range, None))
                lo, hi = lo2, hi2

            status = _status_from_ranges(value_f, lo, hi)
            if status == "normal":
                continue

            if status == "low":
                interp = str(rule_row.get("BASSE - Interprétation", "") or "")
                nutr = str(rule_row.get("BASSE - Nutrition", "") or "")
                supp = str(rule_row.get("BASSE - Micronutrition", "") or "")
                life = str(rule_row.get("BASSE - Lifestyle", "") or "")
            else:
                interp = str(rule_row.get("HAUTE - Interprétation", "") or "")
                nutr = str(rule_row.get("HAUTE - Nutrition", "") or "")
                supp = str(rule_row.get("HAUTE - Micronutrition", "") or "")
                life = str(rule_row.get("HAUTE - Lifestyle", "") or "")

            recos.append(
                {
                    "title": marker + " (" + status.upper() + ")",
                    "modality": "biologie",
                    "marker": marker,
                    "status": status,
                    "severity": status,
                    "interpretation": interp.strip(),
                    "nutrition": nutr.strip(),
                    "supplementation": supp.strip(),
                    "lifestyle": life.strip(),
                    "notes": "Valeur=" + str(value_f) + " | Ref=(" + str(lo) + "," + str(hi) + ")",
                }
            )

    # -------- MICROBIOTE (DI + Shannon) --------
    micro_rules = rules.get("Microbiote", pd.DataFrame())

    di_proxy = micro_meta.get("dysbiosis_index_score_proxy", None)
    div_status = micro_meta.get("diversity_status", None)

    di_rule_id = None
    if di_proxy is not None:
        try:
            di_rule_id = _micro_di_to_rule_id(int(di_proxy))
        except Exception:
            di_rule_id = None

    if di_rule_id:
        rr = _pick_micro_rule_row(micro_rules, di_rule_id)
        if rr is not None:
            recos.append(
                {
                    "title": "Microbiote - Dysbiosis Index",
                    "modality": "microbiote",
                    "marker": "Dysbiosis Index (DI)",
                    "status": "DI=" + str(di_proxy),
                    "severity": str(rr.get("Niveau_gravite", "")),
                    "interpretation": str(rr.get("Interpretation_clinique", "") or "").strip(),
                    "nutrition": str(rr.get("Recommandations_nutritionnelles", "") or "").strip(),
                    "supplementation": str(rr.get("Recommandations_supplementation", "") or "").strip(),
                    "lifestyle": str(rr.get("Recommandations_lifestyle", "") or "").strip(),
                    "notes": str(rr.get("Notes_additionnelles", "") or "").strip(),
                }
            )

    sh_rule_id = _micro_div_to_rule_id(div_status)
    if sh_rule_id:
        rr = _pick_micro_rule_row(micro_rules, sh_rule_id)
        if rr is not None:
            recos.append(
                {
                    "title": "Microbiote - Diversite (Shannon)",
                    "modality": "microbiote",
                    "marker": "Shannon Diversity Index",
                    "status": str(div_status),
                    "severity": str(rr.get("Niveau_gravite", "")),
                    "interpretation": str(rr.get("Interpretation_clinique", "") or "").strip(),
                    "nutrition": str(rr.get("Recommandations_nutritionnelles", "") or "").strip(),
                    "supplementation": str(rr.get("Recommandations_supplementation", "") or "").strip(),
                    "lifestyle": str(rr.get("Recommandations_lifestyle", "") or "").strip(),
                    "notes": str(rr.get("Notes_additionnelles", "") or "").strip(),
                }
            )

    return recos
