"""
Moteur de règles pour générer des recommandations personnalisées
basées sur les résultats biologiques et microbiote

UNILABS / ALGO-LIFE
PATCH v5:
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
    if df is None or df.empty:
        return None

    def norm(s: str) -> str:
        s = str(s).strip().upper()
        s = re.sub(r"\s+", " ", s)
        s = s.replace("’", "'")
        return s

    cols_norm = {norm(c): c for c in df.columns}

    # exact
    for cand in candidates:
        nc = norm(cand)
        if nc in cols_norm:
            return cols_norm[nc]

    # fuzzy contains
    for cand in candidates:
        nc = norm(cand)
        for key, original in cols_norm.items():
            if nc in key or key in nc:
                return original

    return None


def _get_cell(row: Union[pd.Series, Dict], col: Optional[str]) -> str:
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
    - Analyses croisées
    """

    def __init__(self, rules_excel_path: str):
        self.rules_excel_path = rules_excel_path

        self.rules_bio_base: Optional[pd.DataFrame] = None
        self.rules_bio_extended: Optional[pd.DataFrame] = None
        self.rules_bio_functional: Optional[pd.DataFrame] = None
        self.rules_microbiome: Optional[pd.DataFrame] = None
        self.rules_metabolites: Optional[pd.DataFrame] = None

        # Index biomarqueurs (normalisés)
        self._bio_index: Dict[str, pd.Series] = {}
        self._bio_contains_keys: List[str] = []

        # Microbiote rows
        self._micro_rows: List[pd.Series] = []

        self._load_rules()
        self._build_indexes()

    # -----------------------------------------------------------------
    # NEW: list all biomarkers from Excel
    # -----------------------------------------------------------------
    def list_all_biomarkers(self) -> List[str]:
        """
        Retourne la liste unique (triée) de tous les biomarqueurs présents dans l'Excel de règles.
        Utilise les feuilles BASE_40 / EXTENDED_92 / FONCTIONNEL_134.
        """
        biom_list: List[str] = []

        for df in [self.rules_bio_base, self.rules_bio_extended, self.rules_bio_functional]:
            if not _df_ok(df):
                continue

            col = _col_find(df, ["Biomarqueur", "BIOMARQUEUR", "Marqueur", "Paramètre", "Parametre"])
            if not col:
                # fallback: heuristique
                for c in df.columns:
                    s = str(c).lower()
                    if "biomar" in s or "marqueur" in s or "param" in s:
                        col = c
                        break

            if col:
                vals = df[col].dropna().astype(str).str.strip().tolist()
                biom_list.extend(vals)

        # unique + clean + tri
        uniq = sorted({b for b in biom_list if b and b.lower() != "nan"})
        return uniq

    # -----------------------------------------------------------------
    # Load rules (NO DataFrame boolean operations)
    # -----------------------------------------------------------------
    def _load_rules(self) -> None:
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

        # Métabolites : plusieurs noms possibles (NO "or" between DFs)
        self.rules_metabolites = _first_non_empty(
            load_sheet("Métabolites salivaire"),
            load_sheet("Metabolites salivaire"),
            load_sheet("Métabolites salivaires"),
            load_sheet("Metabolites salivaires"),
        )

        print("✅ Chargement terminé")

    # -----------------------------------------------------------------
    # Build indexes for matching
    # -----------------------------------------------------------------
    def _build_indexes(self) -> None:
        self._bio_index = {}
        self._bio_contains_keys = []

        for df in [self.rules_bio_base, self.rules_bio_extended, self.rules_bio_functional]:
            if not _df_ok(df):
                continue

            biom_col = _col_find(df, ["Biomarqueur", "Marqueur", "Paramètre", "Parametre"])
            if not biom_col:
                print("⚠️ Colonne biomarqueur introuvable dans une feuille.")
                continue

            df["_BIO_NORM_"] = df[biom_col].astype(str).apply(normalize_biomarker_name)

            # exact index
            for _, row in df.iterrows():
                key = row.get("_BIO_NORM_", "")
                if isinstance(key, str) and key and key not in self._bio_index:
                    self._bio_index[key] = row

            # contains keys
            self._bio_contains_keys.extend([k for k in df["_BIO_NORM_"].dropna().tolist() if isinstance(k, str) and k])

        # Microbiote rows
        self._micro_rows = []
        if _df_ok(self.rules_microbiome):
            self._micro_rows = [r for _, r in self.rules_microbiome.iterrows()]

    # -----------------------------------------------------------------
    # Debug: biomarker match stats
    # -----------------------------------------------------------------
    def debug_match_summary(self, biology_df: pd.DataFrame) -> Dict[str, Any]:
        if biology_df is None or biology_df.empty:
            return {"matched": 0, "not_found": [], "total": 0}

        col_b = _col_find(biology_df, ["Biomarqueur"])
        if not col_b:
            return {"matched": 0, "not_found": [], "total": len(biology_df)}

        matched = 0
        not_found: List[str] = []

        for biom in biology_df[col_b].astype(str).tolist():
            if self._find_biomarker_rules(biom) is not None:
                matched += 1
            else:
                not_found.append(biom)

        return {"matched": matched, "not_found": not_found[:25], "total": len(biology_df)}

    # -----------------------------------------------------------------
    # Find biomarker rules (robust)
    # -----------------------------------------------------------------
    def _find_biomarker_rules(self, biomarker_name: str) -> Optional[pd.Series]:
        if not biomarker_name:
            return None

        norm = normalize_biomarker_name(biomarker_name)

        # exact
        row = self._bio_index.get(norm)
        if row is not None:
            return row

        # contains fallback
        for key in self._bio_contains_keys:
            if not isinstance(key, str) or not key:
                continue
            if norm in key or key in norm:
                return self._bio_index.get(key)

        return None

    # -----------------------------------------------------------------
    # Microbiome rules matching
    # -----------------------------------------------------------------
    def _get_microbiome_rules(self, group: str, severity: int) -> Optional[pd.Series]:
        if not _df_ok(self.rules_microbiome):
            return None

        norm_group = str(group).upper().strip()

        col_group = _col_find(self.rules_microbiome, ["Groupe", "Group", "Catégorie", "Categorie", "Category"])
        col_sev = _col_find(self.rules_microbiome, ["Niveau_gravite", "NIVEAU_GRAVITE", "Sévérité", "Severite", "Severity"])

        if not col_group:
            return None

        for row in self._micro_rows:
            rule_group = str(row.get(col_group, "")).upper().strip()
            if not rule_group:
                continue

            if norm_group in rule_group or rule_group in norm_group:
                if severity <= 0:
                    return row

                if not col_sev:
                    return row

                sev_val = str(row.get(col_sev, "")).strip().lower()

                if severity == 1 and any(x in sev_val for x in ["+1", "1", "leger", "léger", "slight"]):
                    return row
                if severity == 2 and any(x in sev_val for x in ["+2", "2", "modere", "modéré", "moderate"]):
                    return row
                if severity >= 3 and any(x in sev_val for x in ["+3", "3", "severe", "sévère"]):
                    return row

        return None

    # -----------------------------------------------------------------
    # Biology interpretation using Excel columns (tolerant)
    # -----------------------------------------------------------------
    def generate_biology_interpretation(self, biomarker_data: pd.Series, patient_info: Dict) -> Dict:
        biomarker_name = biomarker_data.get("Biomarqueur", "")
        value = biomarker_data.get("Valeur", None)
        unit = biomarker_data.get("Unité", biomarker_data.get("Unite", "")) or ""
        reference = biomarker_data.get("Référence", biomarker_data.get("Reference", "")) or ""

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

        one = rules.to_frame().T

        low_i = _col_find(one, ["BASSE - Interprétation", "BASSE-Interprétation", "BASSE Interprétation", "BASSE - Interpretation"])
        low_n = _col_find(one, ["BASSE - Nutrition", "BASSE-Nutrition", "BASSE Nutrition"])
        low_m = _col_find(one, ["BASSE - Micronutrition", "BASSE-Micronutrition", "BASSE Micronutrition"])
        low_l = _col_find(one, ["BASSE - Lifestyle", "BASSE-Lifestyle", "BASSE Lifestyle"])

        high_i = _col_find(one, ["HAUTE - Interprétation", "HAUTE-Interprétation", "HAUTE Interprétation", "HAUTE - Interpretation"])
        high_n = _col_find(one, ["HAUTE - Nutrition", "HAUTE-Nutrition", "HAUTE Nutrition"])
        high_m = _col_find(one, ["HAUTE - Micronutrition", "HAUTE-Micronutrition", "HAUTE Micronutrition"])
        high_l = _col_find(one, ["HAUTE - Lifestyle", "HAUTE-Lifestyle", "HAUTE Lifestyle"])

        if status == "Bas":
            result["interpretation"] = _get_cell(rules, low_i) or None
            result["nutrition_reco"] = _get_cell(rules, low_n) or None
            result["micronutrition_reco"] = _get_cell(rules, low_m) or None
            result["lifestyle_reco"] = _get_cell(rules, low_l) or None

        elif status == "Élevé":
            result["interpretation"] = _get_cell(rules, high_i) or None
            result["nutrition_reco"] = _get_cell(rules, high_n) or None
            result["micronutrition_reco"] = _get_cell(rules, high_m) or None
            result["lifestyle_reco"] = _get_cell(rules, high_l) or None

        return result

    # -----------------------------------------------------------------
    # Microbiome interpretation
    # -----------------------------------------------------------------
    def generate_microbiome_interpretation(self, bacteria_data: Dict) -> Dict:
        group = bacteria_data.get("group", "")
        result_status = bacteria_data.get("result", "")

        if result_status == "Expected":
            severity = 0
        elif result_status == "Slightly deviating":
            severity = 1
        else:
            severity = 2

        out = {
            "category": bacteria_data.get("category", ""),
            "group": group,
            "result": result_status,
            "interpretation": None,
            "nutrition_reco": None,
            "supplementation_reco": None,
            "lifestyle_reco": None,
        }

        if severity == 0:
            out["interpretation"] = "Niveau optimal - Continuer les bonnes pratiques actuelles"
            return out

        rules = self._get_microbiome_rules(group, severity)
        if rules is None:
            return out

        one = rules.to_frame().T
        col_i = _col_find(one, ["Interpretation_clinique", "Interprétation clinique", "Interpretation", "Interprétation"])
        col_n = _col_find(one, ["Recommandations_nutritionnelles", "Recommandations nutritionnelles", "Nutrition"])
        col_s = _col_find(one, ["Recommandations_supplementation", "Recommandations supplémentation", "Supplements", "Supplémentation"])
        col_l = _col_find(one, ["Recommandations_lifestyle", "Lifestyle"])

        out["interpretation"] = _get_cell(rules, col_i) or None
        out["nutrition_reco"] = _get_cell(rules, col_n) or None
        out["supplementation_reco"] = _get_cell(rules, col_s) or None
        out["lifestyle_reco"] = _get_cell(rules, col_l) or None
        return out

    # -----------------------------------------------------------------
    # Cross analysis (safe numeric comparisons) - minimal
    # -----------------------------------------------------------------
    def generate_cross_analysis(self, biology_data: pd.DataFrame, microbiome_data: Dict) -> List[Dict]:
        cross: List[Dict] = []
        if biology_data is None or biology_data.empty:
            return cross

        def find_first(marker: str) -> Optional[pd.Series]:
            m = biology_data[biology_data["Biomarqueur"].astype(str).str.contains(marker, case=False, na=False)]
            if m.empty:
                return None
            return m.iloc[0]

        crp = find_first("CRP")
        if crp is not None:
            crp_val = _safe_float(crp.get("Valeur"))
            if crp_val is not None:
                pro_inf = [
                    b for b in (microbiome_data or {}).get("bacteria", [])
                    if str(b.get("category", "")).upper().startswith("E") and b.get("result") != "Expected"
                ]
                if crp_val > 3 and len(pro_inf) > 0:
                    cross.append({
                        "title": "🔥 Inflammation Systémique Détectée",
                        "description": f"CRP: {crp_val} mg/L (>3) + microbiote pro-inflammatoire perturbé ({len(pro_inf)} groupe(s))."
                    })

        return cross

    # -----------------------------------------------------------------
    # Main generation
    # -----------------------------------------------------------------
    def generate_recommendations(
        self,
        biology_data: Optional[pd.DataFrame] = None,
        microbiome_data: Optional[Dict] = None,
        patient_info: Optional[Dict] = None,
    ) -> Dict:

        recos = {
            "biology_interpretations": [],
            "microbiome_interpretations": [],
            "microbiome_summary": {},
            "cross_analysis": [],
            "priority_actions": [],
            "debug": {},
        }

        # Debug rules loaded
        recos["debug"]["rules_loaded"] = {
            "BASE_40": 0 if not _df_ok(self.rules_bio_base) else len(self.rules_bio_base),
            "EXTENDED_92": 0 if not _df_ok(self.rules_bio_extended) else len(self.rules_bio_extended),
            "FONCTIONNEL_134": 0 if not _df_ok(self.rules_bio_functional) else len(self.rules_bio_functional),
            "Microbiote": 0 if not _df_ok(self.rules_microbiome) else len(self.rules_microbiome),
        }

        # Biology
        if biology_data is not None and not biology_data.empty:
            for _, row in biology_data.iterrows():
                recos["biology_interpretations"].append(self.generate_biology_interpretation(row, patient_info or {}))
            recos["debug"]["bio_match"] = self.debug_match_summary(biology_data)

        # Microbiome
        if microbiome_data is not None:
            recos["microbiome_summary"] = {
                "dysbiosis_index": microbiome_data.get("dysbiosis_index"),
                "diversity": microbiome_data.get("diversity"),
            }
            for b in microbiome_data.get("bacteria", []):
                recos["microbiome_interpretations"].append(self.generate_microbiome_interpretation(b))

        # Cross
        if biology_data is not None and microbiome_data is not None:
            recos["cross_analysis"] = self.generate_cross_analysis(biology_data, microbiome_data)

        # Priority actions
        anomalies = [b for b in recos["biology_interpretations"] if b.get("status") in ["Bas", "Élevé"]]
        if len(anomalies) > 0:
            recos["priority_actions"].append(f"⚠️ {len(anomalies)} anomalies biologiques détectées → protocole ciblé recommandé.")
        else:
            recos["priority_actions"].append("✅ Aucun signal critique détecté dans les biomarqueurs importés.")

        return recos
