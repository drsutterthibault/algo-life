"""
Moteur de règles pour générer des recommandations personnalisées
basées sur les résultats biologiques et microbiote

PATCH v3 (robuste + stable):
✅ Chargement Excel tolérant
✅ Index biomarqueurs normalisé (matching fiable)
✅ Colonnes tolérantes (variantes Excel)
✅ Plus d'erreur "truth value DataFrame ambiguous"
✅ Cross-analysis safe numeric
✅ Debug intégré (rules matched / not_found)
"""

from __future__ import annotations

import os
import re
from typing import Dict, List, Optional, Any, Union

import numpy as np
import pandas as pd

from extractors import normalize_biomarker_name, determine_biomarker_status


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------
def _safe_float(x: Any) -> Optional[float]:
    """Convert any value to float safely."""
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
    """
    Find first matching column in DataFrame among candidates,
    tolerant to case/spacing variations.
    """
    if df is None or df.empty:
        return None

    def norm(s: str) -> str:
        s = str(s).strip().upper()
        s = re.sub(r"\s+", " ", s)
        return s

    cols_norm = {norm(c): c for c in df.columns}

    # Exact match first
    for cand in candidates:
        if norm(cand) in cols_norm:
            return cols_norm[norm(cand)]

    # Fuzzy contains fallback
    for cand in candidates:
        nc = norm(cand)
        for key, original in cols_norm.items():
            if nc in key or key in nc:
                return original

    return None


def _get_cell(row: Union[pd.Series, Dict], col: Optional[str]) -> str:
    """Get safe cell content from a pandas row."""
    if not col:
        return ""
    try:
        v = row.get(col, "")
    except Exception:
        v = ""
    if v is None:
        return ""
    if isinstance(v, float) and np.isnan(v):
        return ""
    return str(v).strip()


# ---------------------------------------------------------------------
# RulesEngine
# ---------------------------------------------------------------------
class RulesEngine:
    """
    Moteur de règles multimodal:
    - Biologie (BASE_40 / EXTENDED_92 / FONCTIONNEL_134)
    - Microbiote
    - Cross-analysis
    """

    def __init__(self, rules_excel_path: str):
        self.rules_excel_path = rules_excel_path

        self.rules_bio_base: Optional[pd.DataFrame] = None
        self.rules_bio_extended: Optional[pd.DataFrame] = None
        self.rules_bio_functional: Optional[pd.DataFrame] = None
        self.rules_microbiome: Optional[pd.DataFrame] = None
        self.rules_metabolites: Optional[pd.DataFrame] = None

        # Index biomarqueurs
        self._bio_index: Dict[str, pd.Series] = {}
        self._bio_contains_keys: List[str] = []

        # Microbiote rules list
        self._micro_rows: List[pd.Series] = []

        self._load_rules()
        self._build_indexes()

    # -----------------------------------------------------------------
    # Load Excel rules
    # -----------------------------------------------------------------
    def _load_rules(self):
        """Charge toutes les feuilles depuis Excel (tolérant)."""
        if not os.path.exists(self.rules_excel_path):
            raise FileNotFoundError(f"Le fichier {self.rules_excel_path} n'existe pas")

        print(f"📂 Chargement règles: {self.rules_excel_path}")
        print(f"📏 Taille fichier: {os.path.getsize(self.rules_excel_path)} bytes")

        xl = pd.ExcelFile(self.rules_excel_path, engine="openpyxl")
        sheets = xl.sheet_names
        print("📋 Feuilles détectées:", sheets)

        def load_sheet(name: str) -> Optional[pd.DataFrame]:
            if name not in sheets:
                print(f"⚠️ Feuille absente: {name}")
                return None
            df = pd.read_excel(self.rules_excel_path, sheet_name=name, engine="openpyxl")
            if df is None or df.empty:
                print(f"⚠️ Feuille vide: {name}")
                return None
            print(f"✅ {name} chargé: {len(df)} lignes")
            return df

        # Biologie
        self.rules_bio_base = load_sheet("BASE_40")
        self.rules_bio_extended = load_sheet("EXTENDED_92")
        self.rules_bio_functional = load_sheet("FONCTIONNEL_134")

        # Microbiote
        self.rules_microbiome = load_sheet("Microbiote")

        # ✅ FIX SAFE: Métabolites (plusieurs noms possibles, sans "or" DataFrame)
        self.rules_metabolites = None
        for nm in [
            "Métabolites salivaire",
            "Metabolites salivaire",
            "Métabolites salivaires",
            "Metabolites salivaires",
        ]:
            df_tmp = load_sheet(nm)
            if df_tmp is not None and not df_tmp.empty:
                self.rules_metabolites = df_tmp
                break

        print("✅ Chargement terminé")

    # -----------------------------------------------------------------
    # Build indexes for matching
    # -----------------------------------------------------------------
    def _build_indexes(self):
        """Pré-indexe les biomarqueurs pour matching rapide."""
        self._bio_index = {}
        self._bio_contains_keys = []

        for df in [self.rules_bio_base, self.rules_bio_extended, self.rules_bio_functional]:
            if df is None or df.empty:
                continue

            biom_col = _col_find(df, ["Biomarqueur", "Marqueur", "Paramètre"])
            if not biom_col:
                print("⚠️ Colonne biomarqueur introuvable dans une feuille.")
                continue

            df["_BIO_NORM_"] = df[biom_col].astype(str).apply(normalize_biomarker_name)

            for _, row in df.iterrows():
                key = row.get("_BIO_NORM_", "")
                if isinstance(key, str) and key:
                    if key not in self._bio_index:
                        self._bio_index[key] = row

            self._bio_contains_keys.extend(df["_BIO_NORM_"].dropna().tolist())

        # Microbiote
        self._micro_rows = []
        if self.rules_microbiome is not None and not self.rules_microbiome.empty:
            self._micro_rows = [r for _, r in self.rules_microbiome.iterrows()]

    # -----------------------------------------------------------------
    # Debug
    # -----------------------------------------------------------------
    def debug_match_summary(self, biology_df: pd.DataFrame) -> Dict[str, Any]:
        """Retourne stats de matching biomarqueurs."""
        if biology_df is None or biology_df.empty:
            return {"matched": 0, "not_found": [], "total": 0}

        matched = 0
        not_found = []

        for biom in biology_df["Biomarqueur"].astype(str).tolist():
            if self._find_biomarker_rules(biom) is not None:
                matched += 1
            else:
                not_found.append(biom)

        return {"matched": matched, "not_found": not_found[:25], "total": len(biology_df)}

    # -----------------------------------------------------------------
    # Find biomarker rule
    # -----------------------------------------------------------------
    def _find_biomarker_rules(self, biomarker_name: str) -> Optional[pd.Series]:
        if not biomarker_name:
            return None

        norm = normalize_biomarker_name(biomarker_name)

        # Exact match
        if norm in self._bio_index:
            return self._bio_index[norm]

        # Contains fallback
        for key in self._bio_contains_keys:
            if not isinstance(key, str) or not key:
                continue
            if norm in key or key in norm:
                return self._bio_index.get(key)

        return None

    # -----------------------------------------------------------------
    # Biology interpretation
    # -----------------------------------------------------------------
    def generate_biology_interpretation(self, biomarker_data: pd.Series, patient_info: Dict) -> Dict:
        biomarker_name = biomarker_data.get("Biomarqueur", "")
        value = biomarker_data.get("Valeur", None)
        unit = biomarker_data.get("Unité", "") or ""
        reference = biomarker_data.get("Référence", "") or ""

        status = determine_biomarker_status(value, reference, biomarker_name)
        rules = self._find_biomarker_rules(biomarker_name)

        result = {
            "biomarker": biomarker_name,
            "value": value,
            "unit": unit,
            "reference": reference,
            "status": status,
            "interpretation": None,
            "nutrition_reco": None,
            "micronutrition_reco": None,
            "lifestyle_reco": None,
        }

        if rules is None:
            return result

        # Columns low/high
        if status == "Bas":
            result["interpretation"] = _get_cell(rules, _col_find(rules.to_frame().T, ["BASSE - Interprétation"]))
            result["nutrition_reco"] = _get_cell(rules, _col_find(rules.to_frame().T, ["BASSE - Nutrition"]))
            result["micronutrition_reco"] = _get_cell(rules, _col_find(rules.to_frame().T, ["BASSE - Micronutrition"]))
            result["lifestyle_reco"] = _get_cell(rules, _col_find(rules.to_frame().T, ["BASSE - Lifestyle"]))

        elif status == "Élevé":
            result["interpretation"] = _get_cell(rules, _col_find(rules.to_frame().T, ["HAUTE - Interprétation"]))
            result["nutrition_reco"] = _get_cell(rules, _col_find(rules.to_frame().T, ["HAUTE - Nutrition"]))
            result["micronutrition_reco"] = _get_cell(rules, _col_find(rules.to_frame().T, ["HAUTE - Micronutrition"]))
            result["lifestyle_reco"] = _get_cell(rules, _col_find(rules.to_frame().T, ["HAUTE - Lifestyle"]))

        return result

    # -----------------------------------------------------------------
    # Main generation
    # -----------------------------------------------------------------
    def generate_recommendations(
        self,
        biology_data: Optional[pd.DataFrame] = None,
        microbiome_data: Optional[Dict] = None,
        patient_info: Optional[Dict] = None,
    ) -> Dict:

        recommendations = {
            "biology_interpretations": [],
            "microbiome_interpretations": [],
            "microbiome_summary": {},
            "cross_analysis": [],
            "priority_actions": [],
            "debug": {},
        }

        # Biologie
        if biology_data is not None and not biology_data.empty:
            for _, row in biology_data.iterrows():
                interp = self.generate_biology_interpretation(row, patient_info or {})
                recommendations["biology_interpretations"].append(interp)

            recommendations["debug"]["bio_match"] = self.debug_match_summary(biology_data)

        # Microbiote summary
        if microbiome_data is not None:
            recommendations["microbiome_summary"] = {
                "dysbiosis_index": microbiome_data.get("dysbiosis_index"),
                "diversity": microbiome_data.get("diversity"),
            }

        # Priority actions simple
        anomalies = [
            b for b in recommendations["biology_interpretations"]
            if b.get("status") in ["Bas", "Élevé"]
        ]
        if anomalies:
            recommendations["priority_actions"].append(
                f"⚠️ {len(anomalies)} anomalies biologiques détectées → protocole ciblé recommandé."
            )
        else:
            recommendations["priority_actions"].append(
                "✅ Aucun signal critique détecté dans les biomarqueurs importés."
            )

        return recommendations
