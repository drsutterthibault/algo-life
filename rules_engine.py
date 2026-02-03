"""
Moteur de règles pour générer des recommandations personnalisées
basées sur les résultats biologiques et microbiote

PATCH v2 (robuste):
- Chargement Excel tolérant (feuilles manquantes -> warning, pas crash)
- Matching biomarqueurs fiable (index normalisé + fallback "contains")
- Colonnes règles tolérantes (variantes de noms, espaces, accents)
- Cross-analysis safe (comparaisons numériques uniquement)
- Debug intégré: stats "rules matched / not found"
"""

from __future__ import annotations

import os
import re
from typing import Dict, List, Optional, Union, Any

import numpy as np
import pandas as pd

from extractors import normalize_biomarker_name, determine_biomarker_status


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------
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
    """
    Return the first column name in df that matches one of candidates
    after light normalization.
    """
    if df is None or df.empty:
        return None

    def norm(s: str) -> str:
        s = str(s).strip().upper()
        s = re.sub(r"\s+", " ", s)
        s = s.replace("’", "'")
        return s

    cols_norm = {norm(c): c for c in df.columns}
    for cand in candidates:
        c = cols_norm.get(norm(cand))
        if c:
            return c

    # fuzzy contains fallback
    for cand in candidates:
        nc = norm(cand)
        for k, original in cols_norm.items():
            if nc in k or k in nc:
                return original
    return None


def _get_cell(row: Union[pd.Series, Dict], col: Optional[str]) -> str:
    if not col:
        return ""
    try:
        v = row.get(col, "")
    except Exception:
        v = ""
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return ""
    return str(v).strip()


# ---------------------------------------------------------------------
# RulesEngine
# ---------------------------------------------------------------------
class RulesEngine:
    """
    Moteur de règles pour l'analyse multimodale et la génération de recommandations
    """

    def __init__(self, rules_excel_path: str):
        self.rules_excel_path = rules_excel_path

        self.rules_bio_base: Optional[pd.DataFrame] = None
        self.rules_bio_extended: Optional[pd.DataFrame] = None
        self.rules_bio_functional: Optional[pd.DataFrame] = None
        self.rules_microbiome: Optional[pd.DataFrame] = None
        self.rules_metabolites: Optional[pd.DataFrame] = None

        # Index normalisés (accélère + fiabilise)
        self._bio_index: Dict[str, pd.Series] = {}
        self._bio_contains_keys: List[str] = []  # pour fallback
        self._micro_index: List[pd.Series] = []

        self._load_rules()
        self._build_indexes()

    # -----------------------------------------------------------------
    # Load rules
    # -----------------------------------------------------------------
    def _load_rules(self):
        """Charge toutes les feuilles de règles depuis le fichier Excel (tolérant)"""
        if not os.path.exists(self.rules_excel_path):
            raise FileNotFoundError(f"Le fichier {self.rules_excel_path} n'existe pas")

        print(f"📂 Chargement règles: {self.rules_excel_path}")
        print(f"📏 Taille fichier: {os.path.getsize(self.rules_excel_path)} bytes")

        xl = pd.ExcelFile(self.rules_excel_path, engine="openpyxl")
        sheets = xl.sheet_names
        print("📋 Feuilles Excel détectées:", sheets)

        def load_sheet(name: str) -> Optional[pd.DataFrame]:
            if name not in sheets:
                print(f"⚠️ Feuille absente: {name} (skip)")
                return None
            df = pd.read_excel(self.rules_excel_path, sheet_name=name, engine="openpyxl")
            if df is None or df.empty:
                print(f"⚠️ Feuille vide: {name}")
            else:
                print(f"✅ {name} chargé: {len(df)} lignes")
            return df

        self.rules_bio_base = load_sheet("BASE_40")
        self.rules_bio_extended = load_sheet("EXTENDED_92")
        self.rules_bio_functional = load_sheet("FONCTIONNEL_134")
        self.rules_microbiome = load_sheet("Microbiote")

        # métabolites: nom variable possible
        self.rules_metabolites = (
            load_sheet("Métabolites salivaire")
            or load_sheet("Metabolites salivaire")
            or load_sheet("Métabolites salivaires")
            or load_sheet("Metabolites salivaires")
        )

        print("✅ Chargement terminé")

    # -----------------------------------------------------------------
    # Build indexes (bio + micro)
    # -----------------------------------------------------------------
    def _build_indexes(self):
        """Pré-indexe les règles pour matching rapide et robuste."""
        self._bio_index = {}
        self._bio_contains_keys = []

        bio_dfs = [self.rules_bio_base, self.rules_bio_extended, self.rules_bio_functional]
        for df in bio_dfs:
            if df is None or df.empty:
                continue

            biom_col = _col_find(df, ["Biomarqueur", "BIOMARQUEUR", "Marqueur", "Paramètre"])
            if not biom_col:
                print("⚠️ Impossible de trouver la colonne 'Biomarqueur' dans une feuille (skip)")
                continue

            # construire colonne normalisée
            df["_BIO_NORM_"] = df[biom_col].astype(str).apply(normalize_biomarker_name)

            # index exact
            for _, row in df.iterrows():
                key = row.get("_BIO_NORM_", "")
                if isinstance(key, str) and key and key not in self._bio_index:
                    self._bio_index[key] = row

            # clés pour fallback contains
            self._bio_contains_keys.extend([k for k in df["_BIO_NORM_"].tolist() if isinstance(k, str) and k])

        # Microbiote: on garde la df brute, matching se fait par boucle (petite table)
        self._micro_index = []
        if self.rules_microbiome is not None and not self.rules_microbiome.empty:
            self._micro_index = [r for _, r in self.rules_microbiome.iterrows()]

    # -----------------------------------------------------------------
    # Debug
    # -----------------------------------------------------------------
    def debug_match_summary(self, biology_df: pd.DataFrame) -> Dict[str, Any]:
        """Retourne stats utiles pour vérifier que les règles matchent."""
        if biology_df is None or biology_df.empty:
            return {"matched": 0, "not_found": [], "total": 0}

        col_b = _col_find(biology_df, ["Biomarqueur"])
        if not col_b:
            return {"matched": 0, "not_found": [], "total": len(biology_df)}

        matched = 0
        not_found = []
        for biom in biology_df[col_b].astype(str).tolist():
            if self._find_biomarker_rules(biom) is not None:
                matched += 1
            else:
                not_found.append(biom)
        return {"matched": matched, "not_found": not_found[:30], "total": len(biology_df)}

    # -----------------------------------------------------------------
    # Find biomarker rules
    # -----------------------------------------------------------------
    def _find_biomarker_rules(self, biomarker_name: str, gender: str = "H") -> Optional[pd.Series]:
        """
        Trouve les règles correspondant à un biomarqueur
        - matching exact via index normalisé
        - fallback contains (si Excel utilise variantes)
        """
        if not biomarker_name:
            return None

        normalized_name = normalize_biomarker_name(biomarker_name)

        # exact
        row = self._bio_index.get(normalized_name)
        if row is not None:
            return row

        # fallback contains: cherche une règle dont la clé contient le biomarqueur, ou inversement
        # (utile si Excel: "GLUTATHION TOTAL (SANG)" vs "GLUTATHION TOTAL")
        for key in self._bio_contains_keys:
            if not isinstance(key, str) or not key:
                continue
            if normalized_name in key or key in normalized_name:
                return self._bio_index.get(key)

        return None

    # -----------------------------------------------------------------
    # Microbiome rules
    # -----------------------------------------------------------------
    def _get_microbiome_rules(self, group: str, severity: int) -> Optional[pd.Series]:
        """
        Matching microbiote robuste:
        - group match (contains)
        - severity match:
            accepte '+1/+2/+3' OU '1/2/3' OU 'léger/modéré/sévère'
        """
        if self.rules_microbiome is None or self.rules_microbiome.empty:
            return None

        norm_group = str(group).upper().strip()

        # colonnes possibles
        col_group = _col_find(self.rules_microbiome, ["Groupe", "GROUP", "Categorie", "Catégorie"])
        col_sev = _col_find(self.rules_microbiome, ["Niveau_gravite", "NIVEAU_GRAVITE", "Sévérité", "Severite", "Severity"])
        if not col_group:
            return None

        for row in self._micro_index:
            rule_group = str(row.get(col_group, "")).upper().strip()
            if not rule_group:
                continue

            # group match
            if norm_group in rule_group or rule_group in norm_group:
                if severity <= 0:
                    return row

                if not col_sev:
                    # si pas de colonne sévérité, on prend la première règle du groupe
                    return row

                sev_val = str(row.get(col_sev, "")).strip().lower()

                # map severity
                if severity == 1:
                    if any(x in sev_val for x in ["+1", "1", "leger", "léger", "slight"]):
                        return row
                elif severity == 2:
                    if any(x in sev_val for x in ["+2", "2", "modere", "modéré", "moderate"]):
                        return row
                else:
                    if any(x in sev_val for x in ["+3", "3", "severe", "sévère", "severe"]):
                        return row

        return None

    # -----------------------------------------------------------------
    # Biology interpretation
    # -----------------------------------------------------------------
    def generate_biology_interpretation(self, biomarker_data: pd.Series, patient_info: Dict) -> Dict:
        biomarker_name = biomarker_data.get("Biomarqueur", "")
        value = biomarker_data.get("Valeur", None)
        unit = biomarker_data.get("Unité", biomarker_data.get("Unite", "")) or ""
        reference = biomarker_data.get("Référence", biomarker_data.get("Reference", "")) or ""

        # statut (Bas/Normal/Élevé/Inconnu) via extractors.py
        status = determine_biomarker_status(value, reference, biomarker_name)

        gender = "H" if patient_info.get("genre") == "Homme" else "F"
        rules = self._find_biomarker_rules(biomarker_name, gender)

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

        # Colonnes BIO (tolérantes)
        if status == "Bas":
            col_i = _col_find(rules.to_frame().T, ["BASSE - Interprétation", "BASSE-Interprétation", "BASSE Interprétation", "BASSE - Interpretation"])
            col_n = _col_find(rules.to_frame().T, ["BASSE - Nutrition", "BASSE-Nutrition", "BASSE Nutrition"])
            col_m = _col_find(rules.to_frame().T, ["BASSE - Micronutrition", "BASSE-Micronutrition", "BASSE Micronutrition"])
            col_l = _col_find(rules.to_frame().T, ["BASSE - Lifestyle", "BASSE-Lifestyle", "BASSE Lifestyle"])

            result["interpretation"] = _get_cell(rules, col_i) or None
            result["nutrition_reco"] = _get_cell(rules, col_n) or None
            result["micronutrition_reco"] = _get_cell(rules, col_m) or None
            result["lifestyle_reco"] = _get_cell(rules, col_l) or None

        elif status == "Élevé":
            col_i = _col_find(rules.to_frame().T, ["HAUTE - Interprétation", "HAUTE-Interprétation", "HAUTE Interprétation", "HAUTE - Interpretation"])
            col_n = _col_find(rules.to_frame().T, ["HAUTE - Nutrition", "HAUTE-Nutrition", "HAUTE Nutrition"])
            col_m = _col_find(rules.to_frame().T, ["HAUTE - Micronutrition", "HAUTE-Micronutrition", "HAUTE Micronutrition"])
            col_l = _col_find(rules.to_frame().T, ["HAUTE - Lifestyle", "HAUTE-Lifestyle", "HAUTE Lifestyle"])

            result["interpretation"] = _get_cell(rules, col_i) or None
            result["nutrition_reco"] = _get_cell(rules, col_n) or None
            result["micronutrition_reco"] = _get_cell(rules, col_m) or None
            result["lifestyle_reco"] = _get_cell(rules, col_l) or None

        return result

    # -----------------------------------------------------------------
    # Microbiome interpretation
    # -----------------------------------------------------------------
    def generate_microbiome_interpretation(self, bacteria_data: Dict) -> Dict:
        group = bacteria_data.get("group", "")
        result_status = bacteria_data.get("result", "")

        # severité
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

        # Colonnes microbiote (tolérantes)
        col_i = _col_find(rules.to_frame().T, ["Interpretation_clinique", "Interprétation clinique", "Interpretation", "Interprétation"])
        col_n = _col_find(rules.to_frame().T, ["Recommandations_nutritionnelles", "Reco nutrition", "Nutrition"])
        col_s = _col_find(rules.to_frame().T, ["Recommandations_supplementation", "Supplements", "Supplémentation"])
        col_l = _col_find(rules.to_frame().T, ["Recommandations_lifestyle", "Lifestyle"])

        out["interpretation"] = _get_cell(rules, col_i) or None
        out["nutrition_reco"] = _get_cell(rules, col_n) or None
        out["supplementation_reco"] = _get_cell(rules, col_s) or None
        out["lifestyle_reco"] = _get_cell(rules, col_l) or None
        return out

    # -----------------------------------------------------------------
    # Cross analysis (safe numeric comparisons)
    # -----------------------------------------------------------------
    def generate_cross_analysis(self, biology_data: pd.DataFrame, microbiome_data: Dict) -> List[Dict]:
        cross_analyses: List[Dict] = []

        if biology_data is None or biology_data.empty:
            return cross_analyses

        # Helper: find by contains
        def find_first(marker: str) -> Optional[pd.Series]:
            m = biology_data[biology_data["Biomarqueur"].astype(str).str.contains(marker, case=False, na=False)]
            if m.empty:
                return None
            return m.iloc[0]

        # Analyse 1: CRP + groupe E (pro-inflammatoire)
        crp = find_first("CRP")
        if crp is not None:
            crp_value = _safe_float(crp.get("Valeur"))
            if crp_value is not None:
                pro_inflammatory = [
                    b for b in (microbiome_data or {}).get("bacteria", [])
                    if str(b.get("category", "")).upper().startswith("E") and b.get("result") != "Expected"
                ]
                if crp_value > 3 and pro_inflammatory:
                    cross_analyses.append({
                        "title": "🔥 Inflammation Systémique Détectée",
                        "description": (
                            f"CRP élevée: {crp_value} mg/L (>3)\n"
                            f"Microbiome pro-inflammatoire perturbé: {len(pro_inflammatory)} groupe(s)\n\n"
                            "Recommandations: régime anti-inflammatoire + oméga-3 + polyphénols + sommeil."
                        )
                    })

        # Analyse 2: HOMA + dysbiose
        homa = find_first("HOMA")
        if homa is not None:
            homa_value = _safe_float(homa.get("Valeur"))
            di = _safe_float((microbiome_data or {}).get("dysbiosis_index"))
            if homa_value is not None and di is not None:
                if homa_value > 2.4 and di >= 3:
                    cross_analyses.append({
                        "title": "⚡ Résistance à l'insuline + Dysbiose",
                        "description": (
                            f"HOMA-IR: {homa_value} (>2.4)\n"
                            f"Dysbiosis Index: {int(di)}/5\n\n"
                            "Reco: réduction glucides raffinés + fibres + activité + berbérine (si pertinent)."
                        )
                    })

        # Analyse 3: glutathion + groupe D2 (SCFA)
        gsh = find_first("GLUTATHION")
        if gsh is not None:
            gsh_value = _safe_float(gsh.get("Valeur"))
            if gsh_value is not None:
                scfa = [b for b in (microbiome_data or {}).get("bacteria", []) if "D2" in str(b.get("group", ""))]
                if gsh_value < 1200 and scfa:
                    scfa_status = scfa[0].get("result", "Expected")
                    if scfa_status != "Expected":
                        cross_analyses.append({
                            "title": "🛡️ Stress oxydatif + SCFA perturbés",
                            "description": (
                                f"Glutathion total bas: {gsh_value} (<1200)\n"
                                f"Producteurs SCFA: {scfa_status}\n\n"
                                "Reco: fibres prébiotiques + soutien GSH (NAC/Glutamine/Vit C) + polyphénols."
                            )
                        })

        # Analyse 4: ferritine + LBP
        ferr = find_first("FERRITINE")
        lbp = find_first("LBP")
        if ferr is not None and lbp is not None:
            ferr_value = _safe_float(ferr.get("Valeur"))
            lbp_value = _safe_float(lbp.get("Valeur"))
            if ferr_value is not None and lbp_value is not None:
                if ferr_value < 30 and lbp_value > 6.8:
                    cross_analyses.append({
                        "title": "🔓 Carence martiale + hyperperméabilité",
                        "description": (
                            f"Ferritine: {ferr_value} (<30)\n"
                            f"LBP: {lbp_value} (>6.8)\n\n"
                            "Reco: réparer barrière (glutamine/zinc carnosine) + optimiser fer + probiotiques."
                        )
                    })

        return cross_analyses

    # -----------------------------------------------------------------
    # Main generation
    # -----------------------------------------------------------------
    def generate_recommendations(
        self,
        biology_data: Optional[pd.DataFrame] = None,
        microbiome_data: Optional[Dict] = None,
        patient_info: Optional[Dict] = None
    ) -> Dict:
        recommendations = {
            "biology_interpretations": [],
            "microbiome_interpretations": [],
            "microbiome_summary": {},
            "cross_analysis": [],
            "priority_actions": [],
            "debug": {}
        }

        # Debug: rules loaded?
        recommendations["debug"]["rules_loaded"] = {
            "BASE_40": 0 if self.rules_bio_base is None else len(self.rules_bio_base),
            "EXTENDED_92": 0 if self.rules_bio_extended is None else len(self.rules_bio_extended),
            "FONCTIONNEL_134": 0 if self.rules_bio_functional is None else len(self.rules_bio_functional),
            "Microbiote": 0 if self.rules_microbiome is None else len(self.rules_microbiome),
        }

        # Biologie
        if biology_data is not None and not biology_data.empty:
            for _, row in biology_data.iterrows():
                interp = self.generate_biology_interpretation(row, patient_info or {})
                recommendations["biology_interpretations"].append(interp)

            # Debug matching
            recommendations["debug"]["bio_match"] = self.debug_match_summary(biology_data)

        # Microbiote
        if microbiome_data is not None:
            recommendations["microbiome_summary"] = {
                "dysbiosis_index": microbiome_data.get("dysbiosis_index"),
                "diversity": microbiome_data.get("diversity"),
            }

            for bacteria in microbiome_data.get("bacteria", []):
                interp = self.generate_microbiome_interpretation(bacteria)
                recommendations["microbiome_interpretations"].append(interp)

        # Cross-analysis
        if biology_data is not None and microbiome_data is not None:
            recommendations["cross_analysis"] = self.generate_cross_analysis(biology_data, microbiome_data)

        # Priority actions
        recommendations["priority_actions"] = self._generate_priority_actions(recommendations)

        return recommendations

    # -----------------------------------------------------------------
    # Priority actions
    # -----------------------------------------------------------------
    def _generate_priority_actions(self, recommendations: Dict) -> List[str]:
        actions = []

        critical_bio = [b for b in recommendations.get("biology_interpretations", []) if b.get("status") in ["Bas", "Élevé"]]
        if len(critical_bio) >= 5:
            actions.append("🚨 PRIORITÉ HAUTE: nombreuses anomalies biologiques détectées → avis médical recommandé.")

        di = recommendations.get("microbiome_summary", {}).get("dysbiosis_index")
        di_val = _safe_float(di)
        if di_val is not None and di_val >= 4:
            actions.append("🦠 PRIORITÉ HAUTE: dysbiose sévère → protocole de restauration microbiome.")

        inflammation = [a for a in recommendations.get("cross_analysis", []) if "Inflammation" in a.get("title", "")]
        if inflammation:
            actions.append("🔥 PRIORITÉ: réduire l’inflammation (nutrition + sommeil + activité + supplémentation ciblée).")

        permeability = [a for a in recommendations.get("cross_analysis", []) if "perméabilité" in a.get("title", "").lower()]
        if permeability:
            actions.append("🔓 PRIORITÉ: réparer la barrière intestinale (glutamine + zinc carnosine + probiotiques).")

        if len(actions) < 2:
            actions.append("✅ Maintenir une activité physique régulière (2–4 séances/sem + marche).")
            actions.append("🥗 Adopter une alimentation méditerranéenne riche en fibres, légumes, oméga-3.")

        return actions
