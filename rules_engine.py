"""
Moteur de règles pour générer des recommandations personnalisées
basées sur les résultats biologiques et microbiote

UNILABS / ALGO-LIFE

PATCH:
✅ Anti "truth value of DataFrame is ambiguous" (pas de if df / pas de df1 or df2)
✅ Index biomarqueurs normalisés (matching robuste)
✅ Colonnes Excel tolérantes
✅ Debug matching
✅ + list_all_biomarkers(): liste complète des biomarqueurs de l'Excel
"""

from __future__ import annotations

import os
import re
from typing import Dict, List, Optional, Any, Union

import numpy as np
import pandas as pd

from extractors import normalize_biomarker_name, determine_biomarker_status


# ---------------------------------------------------------------------
# Helpers (critical: avoid DataFrame boolean ambiguity)
# ---------------------------------------------------------------------
def _df_ok(df) -> bool:
    return (df is not None) and hasattr(df, "empty") and (not df.empty)


def _first_non_empty(*dfs):
    for df in dfs:
        if _df_ok(df):
            return df
    return None


def _safe_float(x: Any) -> Optional[float]:
    try:
        if x is None:
            return None
        if isinstance(x, (int, float, np.number)):
            return float(x)
        s = str(x).strip().replace(",", ".")
        s = re.sub(r"[^0-9\.\-\+eE]", "", s)
        return float(s) if s else None
    except Exception:
        return None


def _col_find(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    """Find first matching column name in df among candidates, tolerant to case/spaces."""
    if not _df_ok(df):
        return None

    def norm(s: str) -> str:
        s = str(s).strip().upper()
        s = re.sub(r"\s+", " ", s)
        return s

    cols = {norm(c): c for c in df.columns}
    for cand in candidates:
        key = norm(cand)
        if key in cols:
            return cols[key]

    # loose match (contains)
    for cand in candidates:
        key = norm(cand)
        for k, orig in cols.items():
            if key in k:
                return orig
    return None


# ---------------------------------------------------------------------
# Rules Engine
# ---------------------------------------------------------------------
class RulesEngine:
    def __init__(self, excel_path: str):
        self.excel_path = excel_path
        if not os.path.exists(excel_path):
            raise FileNotFoundError(f"Rules Excel not found: {excel_path}")

        self.df_rules_bio = None
        self.df_rules_micro = None
        self.df_rules_followup = None

        self._bio_index = {}   # normalized biomarker -> list[rules rows]
        self._load_rules()

    def _load_rules(self):
        xls = pd.ExcelFile(self.excel_path)

        # Try best-effort sheet names
        sheet_names = [s.lower() for s in xls.sheet_names]
        bio_sheet = None
        micro_sheet = None
        follow_sheet = None

        for s in xls.sheet_names:
            sl = s.lower()
            if "bio" in sl or "biolog" in sl:
                bio_sheet = s
            if "micro" in sl or "gut" in sl or "flora" in sl:
                micro_sheet = s
            if "suivi" in sl or "follow" in sl:
                follow_sheet = s

        # Fallbacks
        if bio_sheet is None and xls.sheet_names:
            bio_sheet = xls.sheet_names[0]

        self.df_rules_bio = pd.read_excel(self.excel_path, sheet_name=bio_sheet) if bio_sheet else pd.DataFrame()
        self.df_rules_micro = pd.read_excel(self.excel_path, sheet_name=micro_sheet) if micro_sheet else pd.DataFrame()
        self.df_rules_followup = pd.read_excel(self.excel_path, sheet_name=follow_sheet) if follow_sheet else pd.DataFrame()

        # Build index for biology rules
        if _df_ok(self.df_rules_bio):
            col_biom = _col_find(self.df_rules_bio, ["Biomarqueur", "Biomarker", "Marqueur", "Analyte", "Nom"])
            if col_biom is None:
                col_biom = self.df_rules_bio.columns[0]

            self._bio_index = {}
            for _, row in self.df_rules_bio.iterrows():
                biom = str(row.get(col_biom, "")).strip()
                if not biom:
                    continue
                key = normalize_biomarker_name(biom)
                self._bio_index.setdefault(key, []).append(row.to_dict())

    def list_all_biomarkers(self) -> List[str]:
        out = []
        if _df_ok(self.df_rules_bio):
            col_biom = _col_find(self.df_rules_bio, ["Biomarqueur", "Biomarker", "Marqueur", "Analyte", "Nom"])
            if col_biom is None:
                col_biom = self.df_rules_bio.columns[0]
            out = [str(x).strip() for x in self.df_rules_bio[col_biom].dropna().tolist()]
            out = [x for x in out if x]
        return sorted(list(dict.fromkeys(out)))

    def _match_bio_rules(self, biomarker_name: str) -> List[Dict[str, Any]]:
        key = normalize_biomarker_name(biomarker_name)
        return self._bio_index.get(key, [])

    def generate_recommendations(
        self,
        biology_data: Optional[Union[pd.DataFrame, List[Dict[str, Any]]]] = None,
        microbiome_data: Optional[Dict[str, Any]] = None,
        patient_info: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:

        out = {
            "biology_interpretations": [],
            "microbiome_interpretations": [],
            "debug": {
                "bio_total": 0,
                "bio_matched": 0,
                "bio_unmatched": [],
            },
        }

        # ---------------- BIOLOGY ----------------
        bio_records: List[Dict[str, Any]] = []
        if isinstance(biology_data, pd.DataFrame):
            if _df_ok(biology_data):
                bio_records = biology_data.to_dict(orient="records")
        elif isinstance(biology_data, list):
            bio_records = biology_data

        out["debug"]["bio_total"] = len(bio_records)

        if bio_records:
            # Columns tolerant
            # Your extractor/editor uses: Biomarqueur / Valeur / Unité / Référence / Statut
            for entry in bio_records:
                biomarker = entry.get("Biomarqueur") or entry.get("Biomarker") or entry.get("Marqueur") or entry.get("Analyte")
                value = entry.get("Valeur") if "Valeur" in entry else entry.get("Value")
                unit = entry.get("Unité") if "Unité" in entry else entry.get("Unit")
                ref = entry.get("Référence") if "Référence" in entry else entry.get("Reference")
                status = entry.get("Statut") if "Statut" in entry else entry.get("Status")

                biomarker = str(biomarker or "").strip()
                if not biomarker:
                    continue

                v = _safe_float(value)

                # Determine status if empty
                st = str(status or "").strip()
                if not st:
                    st = determine_biomarker_status(v, ref)

                rules = self._match_bio_rules(biomarker)
                if not rules:
                    out["debug"]["bio_unmatched"].append(biomarker)
                    continue

                out["debug"]["bio_matched"] += 1

                # Apply first matching rule row (simple). If you have multiple, you can loop and merge.
                rule = rules[0]

                # Column names tolerant
                def _get_rule(*names):
                    for n in names:
                        if n in rule and str(rule[n]).strip() != "nan":
                            return rule[n]
                    return None

                interp = {
                    "biomarker": biomarker,
                    "value": v,
                    "unit": unit,
                    "reference": ref,
                    "status": st,
                    "interpretation": _get_rule("Interprétation", "Interpretation"),
                    "nutrition_reco": _get_rule("Nutrition", "Nutrition_reco", "Recommandation Nutrition"),
                    "micronutrition_reco": _get_rule("Micronutrition", "Micronutrition_reco", "Recommandation Micronutrition"),
                    "lifestyle_reco": _get_rule("Lifestyle", "Lifestyle_reco", "Recommandation Lifestyle"),
                }

                out["biology_interpretations"].append(interp)

        # ---------------- MICROBIOME (optional, passthrough) ----------------
        # Keep your existing micro logic if you already had it;
        # here is a very tolerant minimal implementation.
        if isinstance(microbiome_data, dict) and microbiome_data:
            bacteria = microbiome_data.get("bacteria", []) or []
            for b in bacteria:
                grp = b.get("group") or b.get("name") or b.get("taxon")
                res = b.get("result") or b.get("status")
                if not grp:
                    continue
                out["microbiome_interpretations"].append({
                    "group": grp,
                    "result": res,
                    "nutrition_reco": None,
                    "supplementation_reco": None,
                    "lifestyle_reco": None,
                })

        return out
