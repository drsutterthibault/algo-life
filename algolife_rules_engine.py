# algolife_rules_engine.py
"""
ALGO-LIFE - Rules Engine (Excel-driven)
Version 1.0 - Jan 2026

But:
- Charger un fichier Excel de règles (dans /data)
- Produire des recommandations (supplements / alimentation / lifestyle / micronutrition)
  en fonction des biomarqueurs et/ou de leur statut (low/high/insufficient/elevated/deficient/etc.)

✅ Tolérant au format Excel:
- Colonnes reconnues de façon "flexible" (synonymes / casse / accents)
- Peut fonctionner même si certaines colonnes manquent
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Tuple

import pandas as pd


# -----------------------------
# Helpers
# -----------------------------

def _norm(s: Any) -> str:
    """Normalise une chaîne pour matcher les colonnes/valeurs."""
    if s is None:
        return ""
    s = str(s).strip().lower()
    # simplification accents basique
    s = (
        s.replace("é", "e").replace("è", "e").replace("ê", "e")
         .replace("à", "a").replace("â", "a")
         .replace("î", "i").replace("ï", "i")
         .replace("ô", "o")
         .replace("ù", "u").replace("û", "u")
         .replace("ç", "c")
    )
    s = re.sub(r"\s+", " ", s)
    return s


def _to_float(x: Any) -> Optional[float]:
    try:
        if x is None:
            return None
        if isinstance(x, (int, float)):
            return float(x)
        s = str(x).strip().replace(",", ".")
        if s == "" or s.lower() in {"nan", "none", "null"}:
            return None
        return float(s)
    except Exception:
        return None


def _split_lines(x: Any) -> List[str]:
    """Transforme une cellule en liste de recommandations (lignes)."""
    if x is None:
        return []
    s = str(x).strip()
    if not s or _norm(s) in {"nan", "none", "null", "-"}:
        return []
    # Support: séparateurs ; | \n
    parts = re.split(r"(?:\r?\n)+|(?:\s*;\s*)|(?:\s*\|\s*)", s)
    out = []
    for p in parts:
        p = p.strip()
        if p:
            out.append(p)
    return out


def _infer_status_from_value_and_ranges(
    value: float,
    ref_low: Optional[float],
    ref_high: Optional[float],
    opt_low: Optional[float],
    opt_high: Optional[float],
) -> str:
    """
    Statut simple basé sur ranges si fournis:
    - optimal si dans opt range
    - normal si dans ref range
    - low/high sinon
    """
    if value is None:
        return "unknown"

    # optimal range
    if opt_low is not None and opt_high is not None:
        if opt_low <= value <= opt_high:
            return "optimal"

    # normal/reference range
    if ref_low is not None and ref_high is not None:
        if ref_low <= value <= ref_high:
            return "normal"
        if value < ref_low:
            return "low"
        if value > ref_high:
            return "high"

    # si une seule borne
    if ref_low is not None and value < ref_low:
        return "low"
    if ref_high is not None and value > ref_high:
        return "high"

    return "unknown"


# -----------------------------
# Column mapping (flexible)
# -----------------------------

COLUMN_SYNONYMS = {
    # identifiants biomarqueur
    "biomarker_key": [
        "biomarker_key", "biomarker", "marker", "code", "id",
        "key", "biomarqueur", "biomarqueur_key", "nom_court", "analyte_key"
    ],
    "biomarker_label": [
        "label", "name", "nom", "intitule", "analyte", "biomarqueur_nom", "display"
    ],
    "category": [
        "category", "categorie", "famille", "module", "domaine"
    ],

    # plages
    "ref_low": ["ref_low", "ref_min", "min_ref", "borne_basse_ref", "low_ref", "normal_min", "norme_min"],
    "ref_high": ["ref_high", "ref_max", "max_ref", "borne_haute_ref", "high_ref", "normal_max", "norme_max"],
    "opt_low": ["opt_low", "opt_min", "min_opt", "optimal_min", "borne_basse_opt"],
    "opt_high": ["opt_high", "opt_max", "max_opt", "optimal_max", "borne_haute_opt"],

    # logique de règle
    "status": ["status", "etat", "statut", "flag", "classification", "range_status", "niveau"],
    "sex": ["sex", "sexe", "genre"],
    "age_min": ["age_min", "min_age", "age_debut"],
    "age_max": ["age_max", "max_age", "age_fin"],
    "priority": ["priority", "priorite", "niveau_priorite", "urgence"],

    # recommandations
    "supplements": ["supplements", "supplement", "complements", "micronutrition", "supp", "supplementation"],
    "nutrition": ["nutrition", "alimentation", "diet", "food", "conseils_alimentaires"],
    "lifestyle": ["lifestyle", "hygiene_vie", "mode_de_vie", "habitudes", "style_de_vie"],

    # texte optionnel
    "rationale": ["rationale", "justification", "commentaire", "note", "explication"],
}


def _map_columns(df: pd.DataFrame) -> Dict[str, str]:
    """
    Retourne mapping logique -> colonne réelle
    en utilisant des synonymes.
    """
    cols = list(df.columns)
    norm_cols = {_norm(c): c for c in cols}

    mapping: Dict[str, str] = {}
    for logical, syns in COLUMN_SYNONYMS.items():
        for s in syns:
            ns = _norm(s)
            if ns in norm_cols:
                mapping[logical] = norm_cols[ns]
                break
    return mapping


# -----------------------------
# Rules Engine
# -----------------------------

@dataclass
class RuleMatch:
    biomarker_key: str
    status: str
    priority: str
    supplements: List[str]
    nutrition: List[str]
    lifestyle: List[str]
    rationale: str = ""
    category: str = ""


class AlgoLifeRulesEngine:
    """
    Excel-driven rules engine.

    Usage:
        engine = AlgoLifeRulesEngine("data/BASE_BIOMARQUEURS_SYNLAB_FINAL.xlsx")
        out = engine.apply(
            biomarkers={"crp": 4.2, "vit_d": 18},
            patient_info={"age": 45, "sexe": "Masculin"}
        )
    """

    def __init__(self, excel_path: str = "data/BASE_BIOMARQUEURS_SYNLAB_FINAL.xlsx", sheet_name: Optional[str] = None):
        self.excel_path = excel_path
        self.sheet_name = sheet_name
        self.df: Optional[pd.DataFrame] = None
        self.colmap: Dict[str, str] = {}

    def load(self) -> None:
        if not os.path.exists(self.excel_path):
            raise FileNotFoundError(f"Fichier règles introuvable: {self.excel_path}")

        # Charge sheet (par défaut: première)
        self.df = pd.read_excel(self.excel_path, sheet_name=self.sheet_name)
        if isinstance(self.df, dict):
            # si sheet_name=None, pandas renvoie dict de sheets
            # on prend la première
            first_key = list(self.df.keys())[0]
            self.df = self.df[first_key]

        # Nettoyage minimal
        self.df = self.df.copy()
        self.df.columns = [str(c).strip() for c in self.df.columns]

        self.colmap = _map_columns(self.df)

        # Si aucune colonne clé, on essaie de deviner une "colonne biomarqueur"
        if "biomarker_key" not in self.colmap:
            # heuristique: première colonne contenant "bio" / "marker" / "analyte"
            for c in self.df.columns:
                nc = _norm(c)
                if any(k in nc for k in ["biomarqueur", "biomarker", "marker", "analyte", "code", "id"]):
                    self.colmap["biomarker_key"] = c
                    break

        if "biomarker_key" not in self.colmap:
            raise ValueError(
                "Impossible d'identifier la colonne biomarqueur dans l'Excel. "
                "Ajoute une colonne type 'biomarker_key' / 'biomarqueur' / 'code'."
            )

    def _ensure_loaded(self) -> None:
        if self.df is None:
            self.load()

    def _row_matches_patient(self, row: pd.Series, patient_info: Dict[str, Any]) -> bool:
        age = patient_info.get("age")
        sex = patient_info.get("sexe") or patient_info.get("sex")

        # Filtre sexe si colonne présente
        if "sex" in self.colmap:
            rule_sex = _norm(row.get(self.colmap["sex"]))
            if rule_sex:
                # accepte "m", "masculin", "f", "feminin", "all"
                sx = _norm(sex)
                if rule_sex not in {"all", "tout", "tous", "any", "na", "-"}:
                    if sx.startswith("m") and not rule_sex.startswith("m"):
                        return False
                    if sx.startswith("f") and not rule_sex.startswith("f"):
                        return False

        # Filtre âge min/max si présents
        if age is not None:
            if "age_min" in self.colmap:
                amin = _to_float(row.get(self.colmap["age_min"]))
                if amin is not None and float(age) < amin:
                    return False
            if "age_max" in self.colmap:
                amax = _to_float(row.get(self.colmap["age_max"]))
                if amax is not None and float(age) > amax:
                    return False

        return True

    def _row_matches_status(self, row: pd.Series, computed_status: str) -> bool:
        # Si l'Excel a une colonne "status", on doit matcher
        if "status" not in self.colmap:
            return True

        rule_status = _norm(row.get(self.colmap["status"]))
        if not rule_status or rule_status in {"all", "any", "-", "na", "tout", "tous"}:
            return True

        # support multi statuts "low|insufficient" ou "low,insufficient"
        tokens = re.split(r"[,\|/;]+", rule_status)
        tokens = [_norm(t) for t in tokens if _norm(t)]
        return _norm(computed_status) in tokens

    def _compute_status_for_row(self, row: pd.Series, value: float) -> str:
        # Si le fichier contient des ranges, on calcule un statut
        ref_low = _to_float(row.get(self.colmap.get("ref_low", ""))) if "ref_low" in self.colmap else None
        ref_high = _to_float(row.get(self.colmap.get("ref_high", ""))) if "ref_high" in self.colmap else None
        opt_low = _to_float(row.get(self.colmap.get("opt_low", ""))) if "opt_low" in self.colmap else None
        opt_high = _to_float(row.get(self.colmap.get("opt_high", ""))) if "opt_high" in self.colmap else None

        status = _infer_status_from_value_and_ranges(value, ref_low, ref_high, opt_low, opt_high)

        # Si l'Excel impose un status unique (ex: "deficient") sans ranges,
        # alors on garde computed status mais il servira au match; l'output inclura computed_status.
        return status

    def _extract_rulematch(self, biomarker_key: str, row: pd.Series, status: str) -> RuleMatch:
        category = ""
        if "category" in self.colmap:
            category = str(row.get(self.colmap["category"]) or "").strip()

        priority = "Moyen"
        if "priority" in self.colmap:
            p = str(row.get(self.colmap["priority"]) or "").strip()
            if p:
                priority = p

        rationale = ""
        if "rationale" in self.colmap:
            rationale = str(row.get(self.colmap["rationale"]) or "").strip()

        supp = _split_lines(row.get(self.colmap["supplements"])) if "supplements" in self.colmap else []
        nutr = _split_lines(row.get(self.colmap["nutrition"])) if "nutrition" in self.colmap else []
        life = _split_lines(row.get(self.colmap["lifestyle"])) if "lifestyle" in self.colmap else []

        return RuleMatch(
            biomarker_key=biomarker_key,
            status=status,
            priority=priority,
            supplements=supp,
            nutrition=nutr,
            lifestyle=life,
            rationale=rationale,
            category=category
        )

    def apply(
        self,
        biomarkers: Dict[str, float],
        patient_info: Optional[Dict[str, Any]] = None,
        only_outliers: bool = True,
        outlier_statuses: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Applique les règles aux biomarqueurs.

        - only_outliers=True : ne sort des reco que si status ∈ outlier_statuses
          (par défaut: low/high/insufficient/elevated/deficient/abnormal)
        """
        self._ensure_loaded()
        assert self.df is not None

        patient_info = patient_info or {}
        outlier_statuses = outlier_statuses or ["low", "high", "insufficient", "elevated", "deficient", "abnormal"]

        # Index rapide par biomarker_key (normalisé)
        key_col = self.colmap["biomarker_key"]
        df = self.df.copy()

        # normalise la colonne biomarker_key
        df["_bio_key_norm"] = df[key_col].apply(_norm)

        matches: List[RuleMatch] = []

        for biomarker_key, value in (biomarkers or {}).items():
            if value is None:
                continue

            key_norm = _norm(biomarker_key)

            # Filtrer lignes correspondant au biomarqueur
            sub = df[df["_bio_key_norm"] == key_norm]
            if sub.empty:
                # fallback: match sur label si présent
                if "biomarker_label" in self.colmap:
                    label_col = self.colmap["biomarker_label"]
                    sub = df[df[label_col].apply(_norm) == key_norm]

            if sub.empty:
                continue

            for _, row in sub.iterrows():
                if not self._row_matches_patient(row, patient_info):
                    continue

                computed_status = self._compute_status_for_row(row, float(value))

                # Filtre outliers
                if only_outliers and _norm(computed_status) not in set(map(_norm, outlier_statuses)):
                    # si la règle vise explicitement un status et qu'il match, on garde
                    # (ex: règle "normal" si tu veux des conseils d'optimisation)
                    if not self._row_matches_status(row, computed_status):
                        continue
                    # sinon on skip
                    continue

                # Match status si la règle a une colonne status
                if not self._row_matches_status(row, computed_status):
                    continue

                matches.append(self._extract_rulematch(biomarker_key, row, computed_status))

        # Agrégation
        recs = {
            "supplements": [],
            "alimentation": [],
            "lifestyle": [],
            "micronutrition": [],  # alias si tu veux distinguer plus tard
        }
        priorities = []

        for m in matches:
            # merge recs
            recs["supplements"].extend(m.supplements)
            recs["alimentation"].extend(m.nutrition)
            recs["lifestyle"].extend(m.lifestyle)

            priorities.append({
                "biomarker": m.biomarker_key,
                "status": m.status,
                "priority": m.priority,
                "category": m.category,
                "rationale": m.rationale,
            })

        # dédup + nettoyage
        for k in recs:
            dedup = []
            seen = set()
            for item in recs[k]:
                ni = item.strip()
                if not ni:
                    continue
                key = _norm(ni)
                if key in seen:
                    continue
                seen.add(key)
                dedup.append(ni)
            recs[k] = dedup

        # trier priorités (si possible)
        def _prio_rank(p: str) -> int:
            p = _norm(p)
            if "tres" in p or "urgent" in p:
                return 0
            if "eleve" in p or "haut" in p or "high" in p:
                return 1
            if "moyen" in p or "medium" in p:
                return 2
            if "faible" in p or "low" in p:
                return 3
            return 9

        priorities = sorted(priorities, key=lambda x: (_prio_rank(x.get("priority", "")), _norm(x.get("biomarker", ""))))

        return {
            "recommendations": recs,
            "priorities": priorities,
            "debug": {
                "excel_path": self.excel_path,
                "sheet_name": self.sheet_name,
                "colmap": self.colmap,
                "matched_rules": len(matches),
            }
        }


# -----------------------------
# Quick test (local)
# -----------------------------
if __name__ == "__main__":
    engine = AlgoLifeRulesEngine("data/BASE_BIOMARQUEURS_SYNLAB_FINAL.xlsx")
    out = engine.apply(
        biomarkers={"crp": 4.2, "vit_d": 18, "homa_index": 3.1},
        patient_info={"age": 45, "sexe": "Masculin"},
        only_outliers=True
    )
    print("Matched:", out["debug"]["matched_rules"])
    print("Priorities:", out["priorities"][:3])
    print("Supplements:", out["recommendations"]["supplements"][:5])
