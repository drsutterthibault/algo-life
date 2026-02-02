from __future__ import annotations

import io
import re
from typing import Dict, Any, List, Optional, Tuple

import pandas as pd


# -----------------------------
# Normalisation / parsing
# -----------------------------
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
    """
    Accepts '13.5–17.5', '4.0–10.0 G/L', '0.74 à 1.06', '11.5 - 16.0'
    """
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


# -----------------------------
# Load rules
# -----------------------------
def load_rules_from_excel_bytes(file_bytes: bytes) -> Dict[str, pd.DataFrame]:
    bio = io.BytesIO(file_bytes)
    xls = pd.ExcelFile(bio)
    rules: Dict[str, pd.DataFrame] = {}
    for sh in xls.sheet_names:
        df = pd.read_excel(bio, sheet_name=sh)
        rules[sh] = df
        bio.seek(0)
    return rules


# -----------------------------
# Matching biology markers to rule rows
# -----------------------------
def _best_match_row_bio(rules_df: pd.DataFrame, marker_norm: str) -> Optional[pd.Series]:
    if rules_df.empty:
        return None

    # requires column "Biomarqueur"
    col = None
    for c in rules_df.columns:
        if str(c).strip().lower() in {"biomarqueur", "marqueur"}:
            col = c
            break
    if col is None:
        return None

    # simple fuzzy: token overlap score
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
        # boost exact substring
        if name_n in marker_norm or marker_norm in name_n:
            score += 5
        if score > best_score:
            best_score = score
            best = row

    # require minimal match
    if best is None or best_score < 2:
        return None
    return best


def _status_from_ranges(value: float, low: Optional[float], high: Optional[float]) -> str:
    if low is not None and value < low:
        return "low"
    if high is not None and value > high:
        return "high"
    return "normal"


# -----------------------------
# Microbiome severity mapping (from GutMAP proxies)
# -----------------------------
def _micro_di_to_rule_id(di_score: Optional[int]) -> Optional[str]:
    if di_score is None:
        return None
    # proxy mapping
    if di_score <= 2:
        return None
    if di_score == 3:
        return "DI_UP11"
    if di_score == 4:
        return "DI_UP22"
    return "DI_UP33"  # 5

def _micro_diversity_to_rule_id(div_status: Optional[str]) -> Optional[str]:
    if not div_status:
        return None
    if div_status == "as_expected":
        return None
    if div_status == "slightly_lower_than_expected":
        return "SHANNON_DOWN11"
    return "SHANNON_DOWN22"  # lower_than_expected


def _pick_micro_rule_row(micro_rules: pd.DataFrame, rule_id: str) -> Optional[pd.Series]:
    if micro_rules.empty:
        return None
    if "ID_marqueur" not in micro_rules.columns:
        return None
    rows = micro_rules[micro_rules["ID_marqueur"].astype(str).str.strip().eq(rule_id)]
    if rows.empty:
        return None
    return rows.iloc[0]


# -----------------------------
# Main engine
# -----------------------------
def generate_recommendations_multimodal(
    rules: Dict[str, pd.DataFrame],
    sex: str,
    bio_df: pd.DataFrame,
    micro_meta: Dict[str, Any],
    micro_df: pd.DataFrame,
) -> List[Dict[str, Any]]:

    recos: List[Dict[str, Any]] = []
    sex = (sex or "F").upper().strip()
    sex = "H" if sex.startswith("H") else "F"

    # -------------------------
    # BIO recommendations
    # -------------------------
    # We stack the main bio sheets if present
    bio_sheets = [k for k in rules.keys() if k in {"BASE_40", "EXTENDED_92", "FONCTIONNEL_134"}]
    bio_rules = pd.concat([rules[k] for k in bio_sheets if k in rules], ignore_index=True) if bio_sheets else pd.DataFrame()

    if not bio_df.empty and not bio_rules.empty:
        for _, row in bio_df.iterrows():
            marker = str(row.get("marker", "") or "")
            marker_norm = str(row.get("marker_norm", "") or "")
            value = row.get("value", None)
            if value is None or (isinstance(value, float) and pd.isna(value)):
                continue
            try:
                value_f = float(value)
            except Exception:
                continue

            rule_row = _best_match_row_bio(bio_rules, marker_norm if marker_norm else _norm(marker))
            if rule_row is None:
                continue

            # Determine range: prefer extracted refs if present; else rules Normes H/F
            ref_low = row.get("ref_low", None)
            ref_high = row.get("ref_high", None)
            lo = ref_low if ref_low is not None and not pd.isna(ref_low) else None
            hi = ref_high if ref_high is not None and not pd.isna(ref_high) else None

            if lo is None and hi is None:
                col_range = "Normes H" if sex == "H" else "Normes F"
                lo2, hi2 = _parse_range(rule_row.get(col_range, None))
                lo, hi = lo2, hi2

            status = _status_from_ranges(value_f, lo, hi)
            if status == "normal":
                continue

            # Build reco content from corresponding LOW/HIGH columns
            if status == "low":
                interp = str(rule_row.get("BASSE - Interprétation", "") or "")
                nutr = str(rule_row.get("BASSE - Nutrition", "") or "")
                supp = str(rule_row.get("BASSE - Micronutrition", "") or "")
                life = str(rule_row.get("BASSE - Lifestyle", "") or "")
                severity = "low"
            else:
                interp = str(rule_row.get("HAUTE - Interprétation", "") or "")
                nutr = str(rule_row.get("HAUTE - Nutrition", "") or "")
                supp = str(rule_row.get("HAUTE - Micronutrition", "") or "")
                life = str(rule_row.get("HAUTE - Lifestyle", "") or "")
                severity = "high"

            recos.append({
                "title": f"{marker} ({status.upper()})",
                "modality": "biologie",
                "marker": marker,
                "status": status,
                "severity": severity,
                "interpretation": interp.strip(),
                "nutrition": nutr.strip(),
                "supplementation": supp.strip(),
                "lifestyle": life.strip(),
                "notes": f"Valeur={value_f} | Réf=({lo},{hi})",
            })

    # -------------------------
    # MICROBIOME recommendations (functional markers robust)
    # -------------------------
    micro_rules = rules.get("Microbiote", pd.DataFrame())

    di_proxy = micro_meta.get("dysbiosis_index_score_proxy", None)
    div_status = micro_meta.get("diversity_status", None)

    # DI
    di_rule_id = _micro_di_to_rule_id(int(di_proxy) if di_proxy is not None else None)
    if di_rule_id:
        rr = _pick_micro_rule_row(micro_rules, di_rule_id)
        if rr is not None:
            recos.append({
                "title": "Microbiote — Dysbiosis Index",
                "modality": "microbiote",
                "marker": "Dysbiosis Index (DI)",
                "status": f"DI={di_proxy}",
                "severity": str(rr.get("Niveau_gravite", "")),
                "interpretation": str(rr.get("Interpretation_clinique", "") or "").strip(),
                "nutrition": str(rr.get("Recommandations_nutritionnelles", "") or "").strip(),
                "supplementation": str(rr.get("Recommandations_supplementation", "") or "").strip(),
                "lifestyle": str(rr.get("Recommandations_lifestyle", "") or "").strip(),
                "notes": str(rr.get("Notes_additionnelles", "") or "").strip(),
            })

    # Shannon diversity
    sh_rule_id = _micro_diversity_to_rule_id(div_status)
    if sh_rule_id:
        rr = _pick_micro_rule_row(micro_rules, sh_rule_id)
        if rr is not None:
            recos.append({
                "title": "Microbiote — Diversité (Shannon)",
                "modality": "microbiote",
                "marker": "Shannon Diversity Index",
                "status": div_status,
                "severity": str(rr.get("Niveau_gravite", "")),
                "interpretation": str(rr.get("Interpretation_clinique", "") or "").strip(),
                "nutrition": str(rr.get("Recommandations_nutritionnelles", "") or "").strip(),
                "supplementation": str(rr.get("Recommandations_supplementation", "") or "").strip(),
                "lifestyle": str(rr.get("Recommandations_lifestyle", "") or "").strip(),
                "notes": str(rr.get("Notes_additionnelles", "") or "").strip(),
            })

    # (Optionnel) plus tard: matcher micro_df bactéries ↔ Microbiote sheet (Marqueur_bacterien / ID_marqueur)
    # Ici on a déjà un socle fiable via DI + Shannon.

    return recos
