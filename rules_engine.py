from __future__ import annotations

import io
import re
from typing import Dict, Any, List, Optional, Tuple

import pandas as pd


def _to_float(x: Any) -> Optional[float]:
    if x is None:
        return None
    s = str(x).strip().replace(",", ".")
    s = re.sub(r"[^\d\.\-]+", "", s)
    if not s:
        return None
    try:
        return float(s)
    except Exception:
        return None


def _norm(s: str) -> str:
    s = (s or "").upper()
    s = re.sub(r"\(.*?\)", "", s)
    s = re.sub(r"[^A-Z0-9ÀÂÄÇÉÈÊËÎÏÔÖÙÛÜŸÆŒ \-\/]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _parse_range(s: Any) -> Tuple[Optional[float], Optional[float]]:
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return None, None
    txt = str(s)
    txt = txt.replace("—", "-").replace("–", "-")
    txt = txt.replace(" à ", "-").replace(" a ", "-")
    m = re.search(r"(-?\d+(?:[.,]\d+)?)\s*-\s*(-?\d+(?:[.,]\d+)?)", txt)
    if not m:
        return None, None
    lo = _to_float(m.group(1))
    hi = _to_float(m.group(2))
    return lo, hi


def load_rules_from_excel_bytes(file_bytes: bytes) -> Dict[str, pd.DataFrame]:
    bio = io.BytesIO(file_bytes)
    xls = pd.ExcelFile(bio)
    rules: Dict[str, pd.DataFrame] = {}
    for sh in xls.sheet_names:
        bio.seek(0)
        df = pd.read_excel(bio, sheet_name=sh)
        rules[sh] = df
    return rules


def _best_match_row_bio(rules_df: pd.DataFrame, marker_norm: str) -> Optional[pd.Series]:
    if rules_df.empty:
        return None

    col = None
    for c in rules_df.columns:
        if str(c).strip().lower() in {"biomarqueur", "marqueur"}:
            col = c
            break
    if col is None:
        return None

    target_tokens = set(marker_norm.split())
    best = None
    best_score = 0

    for _, row in rules_df.iterrows():
        name = str(row.get(col, "") or "")
        name_n = _norm(name)
        if not name_n:
            continue
        tokens = set(name_n.split())
        score = len(target_tokens & tokens)
        if name_n in marker_norm or marker_norm in name_n:
            score += 5
        if score > best_score:
            best_score = score
            best = row

    if best is None or best_score < 2:
        return None
    return best


def _status_from_ranges(value: float, low: Optional[float], high: Optional[float]) -> str:
    if low is not None and value < low:
        return "low"
    if high is not None and value > high:
        return "high"
    return "normal"


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


def _micro_diversity_to_rule_id(div_status: Optional[str]) -> Optional[str]:
    if not div_status:
        return None
    if div_status == "as_expected":
        return None
    if div_status == "slightly_lower_than_expected":
        return "SHANNON_DOWN11"
    return "SHANNON_DOWN22"


def _pick_micro_rule_row(micro_rules: pd.DataFrame, rule_id: str) -> Optional[pd.Series]:
    if m
