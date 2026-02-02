"""
rules_engine_multimodal.py
- Charge Bases rèlgles Synlab.xlsx
- Applique règles BIO (LOW/HIGH vs normes H/F)
- Applique règles MICROBIOTE (Condition_declenchement)
- Retour: hits + priorités
"""

from __future__ import annotations

import io
import re
import unicodedata
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Tuple

import pandas as pd


# =========================
# Utils
# =========================
def normalize_key(s: str) -> str:
    if s is None:
        return ""
    s = str(s).strip().lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^\w\s-]", " ", s)
    s = re.sub(r"[\s\-]+", "_", s).strip("_")
    return s


def _to_float(x: Any) -> Optional[float]:
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x).strip()
    if not s:
        return None
    s = s.replace(",", ".")
    m = re.search(r"[-+]?\d+(?:\.\d+)?", s)
    if not m:
        return None
    try:
        return float(m.group(0))
    except Exception:
        return None


def parse_range(norm_str: Any) -> Tuple[Optional[float], Optional[float]]:
    """
    Parse "13.5–17.5" / "4.0–10.0 G/L" / "40–75 %" etc.
    Retour: (low, high)
    """
    if norm_str is None:
        return (None, None)
    s = str(norm_str).strip()
    if not s:
        return (None, None)

    s = s.replace(",", ".")
    # tirets possibles: -, –, —
    parts = re.split(r"\s*[-–—]\s*", s)
    nums = []
    for p in parts[:2]:
        v = _to_float(p)
        nums.append(v)

    if len(nums) == 1:
        return (nums[0], None)
    low = nums[0]
    high = nums[1]
    return (low, high)


def eval_condition(value: float, condition: str) -> bool:
    """
    Support:
    - > x, >= x, < x, <= x, = x
    - "a - b" (intervalle)
    - "between a and b"
    - "outside a - b"
    """
    if condition is None:
        return False
    s = str(condition).strip().lower()
    if not s:
        return False
    s = s.replace(",", ".")

    # between
    m = re.search(r"between\s+([-+]?\d+(?:\.\d+)?)\s+and\s+([-+]?\d+(?:\.\d+)?)", s)
    if m:
        a = float(m.group(1))
        b = float(m.group(2))
        lo, hi = (a, b) if a <= b else (b, a)
        return lo <= value <= hi

    # outside
    m = re.search(r"outside\s+([-+]?\d+(?:\.\d+)?)\s*[-–—]\s*([-+]?\d+(?:\.\d+)?)", s)
    if m:
        a = float(m.group(1))
        b = float(m.group(2))
        lo, hi = (a, b) if a <= b else (b, a)
        return value < lo or value > hi

    # operators
    m = re.match(r"^(>=|<=|>|<|=)\s*([-+]?\d+(?:\.\d+)?)$", s)
    if m:
        op = m.group(1)
        x = float(m.group(2))
        if op == ">":
            return value > x
        if op == ">=":
            return value >= x
        if op == "<":
            return value < x
        if op == "<=":
            return value <= x
        if op == "=":
            return abs(value - x) < 1e-9

    # intervalle "a - b"
    m = re.match(r"^([-+]?\d+(?:\.\d+)?)\s*[-–—]\s*([-+]?\d+(?:\.\d+)?)$", s)
    if m:
        a = float(m.group(1))
        b = float(m.group(2))
        lo, hi = (a, b) if a <= b else (b, a)
        return lo <= value <= hi

    # fallback: rien
    return False


# =========================
# Engine
# =========================
@dataclass
class MultimodalRulesEngine:
    xls: pd.ExcelFile

    # ---------- constructors ----------
    @classmethod
    def from_path(cls, path: str) -> "MultimodalRulesEngine":
        xls = pd.ExcelFile(path)
        return cls(xls=xls)

    @classmethod
    def from_uploaded_xlsx(cls, uploaded_file) -> "MultimodalRulesEngine":
        data = uploaded_file.getvalue() if hasattr(uploaded_file, "getvalue") else uploaded_file.read()
        bio = io.BytesIO(data)
        xls = pd.ExcelFile(bio)
        return cls(xls=xls)

    # ---------- public run ----------
    def run(self, biology: Dict[str, float], microbiome: Dict[str, float], sex: str = "H") -> Dict[str, Any]:
        sex = (sex or "H").upper()
        bio_hits = self.apply_bio_rules(biology, sex=sex, sheet_preference="FONCTIONNEL_134")
        micro_hits = self.apply_microbiome_rules(microbiome)

        priorities = self.build_priorities(bio_hits, micro_hits)

        return {
            "summary": {
                "biology_hits": len(bio_hits),
                "microbiome_hits": len(micro_hits),
                "total_hits": len(bio_hits) + len(micro_hits),
            },
            "priorities": priorities,
            "biology_hits": bio_hits,
            "microbiome_hits": micro_hits,
        }

    # ---------- BIO rules ----------
    def apply_bio_rules(self, biology: Dict[str, float], sex: str = "H", sheet_preference: str = "FONCTIONNEL_134") -> List[Dict[str, Any]]:
        if not biology:
            return []

        # choose best sheet among known bio sheets
        bio_sheets = [s for s in self.xls.sheet_names if s in {"BASE_40", "EXTENDED_92", "FONCTIONNEL_134"}]
        sheet = sheet_preference if sheet_preference in bio_sheets else (bio_sheets[-1] if bio_sheets else None)
        if sheet is None:
            return []

        df = self.xls.parse(sheet).copy()
        # normalize columns expected:
        # 'Catégorie','Biomarqueur','Unité','Normes H','Normes F', and LOW/HIGH columns
        hits: List[Dict[str, Any]] = []

        # create lookup from normalized extracted keys -> value
        bio_norm = {normalize_key(k): v for k, v in biology.items()}

        for _, r in df.iterrows():
            biomarker_label = r.get("Biomarqueur", None)
            if biomarker_label is None:
                continue
            rule_key = normalize_key(biomarker_label)

            # try direct match
            v = bio_norm.get(rule_key)

            # fallback: partial match (si labels très longs)
            if v is None:
                # tente inclusion (ex: "hemoglobine_hb" vs "hemoglobine")
                candidates = [k for k in bio_norm.keys() if rule_key and (rule_key in k or k in rule_key)]
                if candidates:
                    v = bio_norm.get(candidates[0])

            if v is None:
                continue

            norm = r.get("Normes H" if sex == "H" else "Normes F", None)
            lo, hi = parse_range(norm)

            if lo is None and hi is None:
                continue

            status = None
            if lo is not None and v < lo:
                status = "LOW"
                interp = r.get("BASSE - Interprétation", "")
                nut = r.get("BASSE - Nutrition", "")
                micro = r.get("BASSE - Micronutrition", "")
                life = r.get("BASSE - Lifestyle", "")
            elif hi is not None and v > hi:
                status = "HIGH"
                interp = r.get("HAUTE - Interprétation", "")
                nut = r.get("HAUTE - Nutrition", "")
                micro = r.get("HAUTE - Micronutrition", "")
                life = r.get("HAUTE - Lifestyle", "")
            else:
                continue  # dans la norme → pas de reco

            hits.append(
                {
                    "modality": "biology",
                    "category": r.get("Catégorie", ""),
                    "biomarker": str(biomarker_label),
                    "value": float(v),
                    "unit": r.get("Unité", ""),
                    "sex": sex,
                    "ref_range": str(norm),
                    "flag": status,
                    "interpretation": "" if pd.isna(interp) else str(interp),
                    "nutrition": "" if pd.isna(nut) else str(nut),
                    "micronutrition": "" if pd.isna(micro) else str(micro),
                    "lifestyle": "" if pd.isna(life) else str(life),
                }
            )

        return hits

    # ---------- MICRO rules ----------
    def apply_microbiome_rules(self, microbiome: Dict[str, float]) -> List[Dict[str, Any]]:
        if not microbiome:
            return []
        if "Microbiote" not in self.xls.sheet_names:
            return []

        df = self.xls.parse("Microbiote").copy()
        micro_norm = {normalize_key(k): v for k, v in microbiome.items()}
        hits: List[Dict[str, Any]] = []

        for _, r in df.iterrows():
            marker = r.get("Marqueur_bacterien", None)
            if marker is None:
                continue
            rule_key = normalize_key(marker)
            v = micro_norm.get(rule_key)

            # fallback partial
            if v is None:
                candidates = [k for k in micro_norm.keys() if rule_key and (rule_key in k or k in rule_key)]
                if candidates:
                    v = micro_norm.get(candidates[0])

            if v is None:
                continue

            cond = r.get("Condition_declenchement", "")
            try:
                trig = eval_condition(float(v), str(cond))
            except Exception:
                trig = False

            if not trig:
                continue

            hits.append(
                {
                    "modality": "microbiome",
                    "category": r.get("Categorie", ""),
                    "group": r.get("Groupe", ""),
                    "marker": str(marker),
                    "value": float(v),
                    "condition": str(cond),
                    "severity": r.get("Niveau_gravite", ""),
                    "interpretation": r.get("Interpretation_clinique", ""),
                    "nutrition": r.get("Recommandations_nutritionnelles", ""),
                    "supplementation": r.get("Recommandations_supplementation", ""),
                    "lifestyle": r.get("Recommandations_lifestyle", ""),
                    "notes": r.get("Notes_additionnelles", ""),
                }
            )

        return hits

    # ---------- PRIORITIES ----------
    def build_priorities(self, bio_hits: List[Dict[str, Any]], micro_hits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Heuristique simple:
        - Microbiote: severity si numérique → tri desc
        - Bio: HIGH/LOW → poids fixe
        """
        prios: List[Dict[str, Any]] = []

        # Bio priorities
        for h in bio_hits:
            score = 70 if h.get("flag") == "HIGH" else 60
            prios.append(
                {
                    "priority_score": score,
                    "modality": "biology",
                    "item": h.get("biomarker"),
                    "flag": h.get("flag"),
                    "value": h.get("value"),
                    "key_reco": (h.get("micronutrition") or h.get("nutrition") or h.get("lifestyle") or "")[:140],
                }
            )

        # Micro priorities
        for h in micro_hits:
            sev_raw = h.get("severity", "")
            sev = _to_float(sev_raw)
            score = 80 + (sev if sev is not None else 0)
            prios.append(
                {
                    "priority_score": float(score),
                    "modality": "microbiome",
                    "item": h.get("marker"),
                    "flag": h.get("condition"),
                    "value": h.get("value"),
                    "key_reco": (h.get("supplementation") or h.get("nutrition") or h.get("lifestyle") or "")[:140],
                }
            )

        prios = sorted(prios, key=lambda x: float(x["priority_score"]), reverse=True)
        return prios[:40]
