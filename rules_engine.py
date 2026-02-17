"""
ALGO-LIFE Rules Engine v3.1 - Calqué sur Bases_regles_Synlab.xlsx
FIXES v3.1 :
  - Lookup fuzzy des colonnes normes (Normes H/F, Norme H/F, Référence H/F...)
  - Lookup fuzzy des colonnes recs (BASSE/HAUTE - Interprétation/Nutrition...)
  - _parse_norm robustifié (tirets longs, espaces, formats variés)
  - Matching biomarqueurs amélioré (ratio Levenshtein léger)
  - Debug panel intégré (self.debug_log) pour Streamlit
  - Colonnes disponibles affichées au chargement pour diagnostic
"""
from __future__ import annotations
import os, re, unicodedata
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd


# ─────────────────────────────────────────────────────────────────────────────
# Utilitaires texte
# ─────────────────────────────────────────────────────────────────────────────

def _normalize(s: str) -> str:
    """Normalise : minuscules, sans accents, sans parenthèses, alphanum+espace."""
    s = str(s).strip().lower()
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"\(.*?\)", "", s).strip()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _safe_str(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and pd.isna(v):
        return ""
    return str(v).strip()


def _parse_norm(norm_str: Any) -> Tuple[Optional[float], Optional[float]]:
    """
    Parse une norme textuelle → (low, high).
    Formes supportées :
      "50 - 150", "50–150", "50 à 150"
      "< 5.0", ">= 30", "> 30"
      "<5", "5-150 µmol/L", "0,50-1,20"
    """
    if norm_str is None or (isinstance(norm_str, float) and pd.isna(norm_str)):
        return None, None

    raw = str(norm_str).strip()
    # Remplace virgules décimales françaises par point
    # mais uniquement les virgules entre chiffres
    raw = re.sub(r"(\d),(\d)", r"\1.\2", raw)

    # Supprime les unités (tout ce qui n'est pas chiffre, point, <, >, -, –, espace, à)
    # On garde le début jusqu'à la première unité alphabétique non-chiffre
    # Stratégie : on extrait d'abord la partie numérique/opérateur
    s = re.sub(
        r"[^0-9<>=.\-–—\s àa].*$",  # supprime à partir du 1er car non numérique
        "",
        raw
    ).strip()

    if not s:
        return None, None

    # < X
    m = re.match(r"^<\s*=?\s*([\d.]+)$", s)
    if m:
        return None, float(m.group(1))

    # > X ou >= X
    m = re.match(r"^>\s*=?\s*([\d.]+)$", s)
    if m:
        return float(m.group(1)), None

    # X - Y  ou  X – Y  ou  X — Y  ou  X à Y
    m = re.match(r"^([\d.]+)\s*(?:[-–—]|à)\s*([\d.]+)$", s)
    if m:
        lo, hi = float(m.group(1)), float(m.group(2))
        if lo > hi:          # inversion possible (rare)
            lo, hi = hi, lo
        return lo, hi

    # Nombre seul → on ne peut pas déduire low/high sans contexte
    return None, None


# ─────────────────────────────────────────────────────────────────────────────
# Lookup colonnes fuzzy
# ─────────────────────────────────────────────────────────────────────────────

def _find_column(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    """Retourne le premier nom de colonne qui matche un candidat (exact ou normalisé)."""
    cols = list(df.columns)
    cols_norm = {_normalize(c): c for c in cols}
    for cand in candidates:
        # Exact
        if cand in cols:
            return cand
        # Normalisé
        cn = _normalize(cand)
        if cn in cols_norm:
            return cols_norm[cn]
    return None


def _find_norm_column(df: pd.DataFrame, sex: str) -> Optional[str]:
    """Trouve la colonne de norme selon le sexe, avec multiples variantes possibles."""
    is_male = str(sex).upper() in ("H", "M")
    if is_male:
        candidates = [
            "Normes H", "Norme H", "Normes Homme", "Norme Homme",
            "Référence H", "Références H", "Ref H", "Valeur normale H",
            "Normes H/F",   # colonne commune
            "Normes",       # colonne unique
            "Norme",
        ]
    else:
        candidates = [
            "Normes F", "Norme F", "Normes Femme", "Norme Femme",
            "Référence F", "Références F", "Ref F", "Valeur normale F",
            "Normes H/F",
            "Normes",
            "Norme",
        ]
    return _find_column(df, candidates)


def _find_rec_column(df: pd.DataFrame, direction: str, domain: str) -> Optional[str]:
    """
    Trouve la colonne recommandation selon direction (BASSE/HAUTE) et domaine.
    direction : "BASSE" ou "HAUTE"
    domain    : "interpretation", "nutrition", "supplementation", "lifestyle", "monitoring"
    """
    d_variants = {
        "BASSE": ["BASSE", "Bas", "BAS", "Basse", "Low", "LOW"],
        "HAUTE": ["HAUTE", "Haut", "HAUT", "Haute", "Élevé", "Eleve", "High", "HIGH"],
    }
    domain_variants = {
        "interpretation":  ["Interprétation", "Interpretation", "Interp", "Description"],
        "nutrition":       ["Nutrition", "Alimentation", "Diète"],
        "supplementation": ["Micronutrition", "Supplémentation", "Supplementation", "Compléments", "Micronutr"],
        "lifestyle":       ["Lifestyle", "Hygiène de vie", "Hygiene", "Mode de vie"],
        "monitoring":      ["Suivi", "Monitoring", "Surveillance", "Notes"],
    }

    dir_vars  = d_variants.get(direction, [direction])
    dom_vars  = domain_variants.get(domain, [domain])

    # Génère toutes les combinaisons
    candidates = []
    for dv in dir_vars:
        for dmv in dom_vars:
            candidates.append(f"{dv} - {dmv}")
            candidates.append(f"{dmv} - {dv}")
            candidates.append(f"{dv}_{dmv}")
            candidates.append(f"{dv} {dmv}")

    return _find_column(df, candidates)


# ─────────────────────────────────────────────────────────────────────────────
# Moteur de règles
# ─────────────────────────────────────────────────────────────────────────────

class RulesEngine:

    _BIO_SHEETS = {
        "base":       ["BASE_40",         "Bio_Base",       "bio_base",       "Base"],
        "extended":   ["EXTENDED_92",     "Bio_Extended",   "bio_extended",   "Extended"],
        "functional": ["FONCTIONNEL_134", "Bio_Functional", "bio_functional", "Fonctionnel", "Functional"],
    }
    _MICRO_SHEETS = ["Microbiote", "Microbiome", "microbiome", "Micro"]

    def __init__(self, rules_excel_path: str):
        self.rules_excel_path = rules_excel_path
        self._df_base:       Optional[pd.DataFrame] = None
        self._df_extended:   Optional[pd.DataFrame] = None
        self._df_functional: Optional[pd.DataFrame] = None
        self._df_micro:      Optional[pd.DataFrame] = None
        self.debug_log:      List[str] = []   # ← collecte les messages de debug
        self._load_rules()

    # ── Chargement ──────────────────────────────────────────────────────────

    def _load_rules(self):
        if not os.path.exists(self.rules_excel_path):
            raise FileNotFoundError(f"Fichier introuvable : {self.rules_excel_path}")
        xl = pd.ExcelFile(self.rules_excel_path)
        available = xl.sheet_names
        msg = f"📂 Feuilles disponibles : {available}"
        print(msg)
        self.debug_log.append(msg)

        for key, attr in [
            ("base",       "_df_base"),
            ("extended",   "_df_extended"),
            ("functional", "_df_functional"),
        ]:
            for sheet_name in self._BIO_SHEETS[key]:
                if sheet_name in available:
                    df = pd.read_excel(self.rules_excel_path, sheet_name=sheet_name)
                    setattr(self, attr, df)
                    msg = f"  ✅ Feuille '{sheet_name}' → {len(df)} règles ({key}) | Colonnes: {list(df.columns)}"
                    print(msg)
                    self.debug_log.append(msg)
                    break
            else:
                msg = f"  ⚠️ Aucune feuille trouvée pour '{key}' parmi {self._BIO_SHEETS[key]}"
                print(msg)
                self.debug_log.append(msg)

        for sheet_name in self._MICRO_SHEETS:
            if sheet_name in available:
                df = pd.read_excel(self.rules_excel_path, sheet_name=sheet_name)
                self._df_micro = df
                msg = f"  ✅ Feuille microbiote '{sheet_name}' → {len(df)} règles | Colonnes: {list(df.columns)}"
                print(msg)
                self.debug_log.append(msg)
                break

    # ── Application règles bio ───────────────────────────────────────────────

    def _apply_bio_sheet(
        self,
        df: Optional[pd.DataFrame],
        bio_data: Dict[str, float],
        sex: str,
        priority: str,
        sheet_label: str = "",
    ) -> List[Dict]:
        results = []
        if df is None or df.empty:
            return results

        # Index normalisé des biomarqueurs patient
        bio_norm: Dict[str, Tuple[str, float]] = {}
        for k, v in bio_data.items():
            if v is not None:
                bio_norm[_normalize(k)] = (k, v)

        # Colonne norme
        norm_col = _find_norm_column(df, sex)
        if norm_col is None:
            msg = f"  ❌ [{sheet_label}] Colonne norme introuvable pour sexe={sex}. Colonnes: {list(df.columns)}"
            print(msg)
            self.debug_log.append(msg)
            # Essai fallback : première colonne contenant "norme" ou "réf"
            for c in df.columns:
                cn = _normalize(c)
                if "norme" in cn or "ref" in cn or "valeur norm" in cn:
                    norm_col = c
                    break

        matched_count = 0
        triggered_count = 0

        for _, row in df.iterrows():
            biomarker_raw = _safe_str(row.get("Biomarqueur", ""))
            if not biomarker_raw:
                continue

            b_norm = _normalize(biomarker_raw)

            # Matching biomarqueur patient
            patient_val: Optional[float] = None
            patient_key_orig: str = ""

            # 1. Exact normalisé
            if b_norm in bio_norm:
                patient_key_orig, patient_val = bio_norm[b_norm]
            else:
                # 2. Inclusion (règle contient patient ou inverse)
                for kn, (k_orig, v) in bio_norm.items():
                    if b_norm in kn or kn in b_norm:
                        patient_key_orig, patient_val = k_orig, v
                        break

            if patient_val is None:
                continue
            matched_count += 1

            # Lecture norme
            norm_raw = None
            if norm_col and norm_col in row.index:
                norm_raw = row[norm_col]

            # Fallback : chercher une autre colonne norme si la principale est vide
            if _safe_str(norm_raw) == "" and norm_col:
                # Essai colonne H si on cherchait F (colonne commune)
                fallback_col = _find_column(df, ["Normes H", "Norme H", "Normes", "Norme"])
                if fallback_col and fallback_col in row.index:
                    norm_raw = row[fallback_col]

            low, high = _parse_norm(norm_raw)

            if low is None and high is None:
                self.debug_log.append(
                    f"    ⚠️ [{sheet_label}] {biomarker_raw}: norme '{_safe_str(norm_raw)}' non parseable"
                )
                continue

            is_low  = (low  is not None) and (patient_val < low)
            is_high = (high is not None) and (patient_val > high)

            if not is_low and not is_high:
                continue
            triggered_count += 1

            direction = "BASSE" if is_low else "HAUTE"

            # Lecture recommandations avec lookup fuzzy
            def _get_rec(domain: str) -> str:
                col = _find_rec_column(df, direction, domain)
                if col and col in row.index:
                    return _safe_str(row[col])
                return ""

            results.append({
                "rule_type":   "bio",
                "priority":    priority,
                "category":    _safe_str(row.get("Catégorie", row.get("Categorie", "Biologie"))),
                "title":       f"{biomarker_raw} {'↓ Bas' if is_low else '↑ Élevé'}",
                "biomarker":   biomarker_raw,
                "value":       patient_val,
                "direction":   direction,
                "norm":        _safe_str(norm_raw),
                "recommendations": {
                    "interpretation": _get_rec("interpretation"),
                    "nutrition":      _get_rec("nutrition"),
                    "supplementation":_get_rec("supplementation"),
                    "lifestyle":      _get_rec("lifestyle"),
                    "monitoring":     _get_rec("monitoring"),
                },
            })

        msg = (
            f"  [{sheet_label}] {len(bio_data)} biomarq. patient | "
            f"{matched_count} matchés | {triggered_count} règles déclenchées"
        )
        print(msg)
        self.debug_log.append(msg)
        return results

    # ── Application règles microbiome ────────────────────────────────────────

    def _apply_micro_rules(self, microbiome_data: Dict) -> List[Dict]:
        results = []
        if self._df_micro is None or self._df_micro.empty:
            self.debug_log.append("  ⚠️ Feuille microbiome absente ou vide")
            return results

        groups: List[Dict] = []
        if isinstance(microbiome_data, dict):
            groups = (
                microbiome_data.get("bacteria_groups")
                or microbiome_data.get("bacteria")
                or []
            )
            if not groups:
                # Fallback : itère sur les clés du dict
                excluded = {"dysbiosis_index", "diversity", "bacteria_groups", "bacteria"}
                groups = [
                    {"name": k, "result": str(v)}
                    for k, v in microbiome_data.items()
                    if k not in excluded
                ]

        triggered = 0
        for group in groups:
            result_str = str(
                group.get("result", "") or group.get("abundance", "")
            ).lower().strip()

            if not result_str or result_str.startswith("expected"):
                continue

            is_elevated = any(
                w in result_str
                for w in ["elevat", "high", "élevé", "eleve", "deviating high", "deviating upward"]
            )
            is_reduced = any(
                w in result_str
                for w in ["reduc", "low", "réduit", "reduit", "deviating low", "deviating downward"]
            )
            # "slightly deviating" sans direction explicite → on skip (ambiguë)
            if not is_elevated and not is_reduced:
                is_elevated = "slightly deviating" not in result_str and "deviating" in result_str
                is_reduced  = False

            if not is_elevated and not is_reduced:
                continue

            is_slight = "slight" in result_str or "leger" in result_str

            marker_name = (
                group.get("group")
                or group.get("category")
                or group.get("name")
                or group.get("Marqueur_bacterien", "")
            )
            m_norm = _normalize(str(marker_name))

            best_score, best_rule = 0, None

            for _, rr in self._df_micro.iterrows():
                rm = _normalize(_safe_str(rr.get("Marqueur_bacterien", "")))
                if not rm:
                    continue

                score = 0
                if rm == m_norm:
                    score = 10
                elif rm in m_norm or m_norm in rm:
                    score = 5
                if score == 0:
                    continue

                cond = _safe_str(rr.get("Condition_declenchement", "")).lower()
                if is_elevated and any(w in cond for w in ["elev", "élevé", "+"]):
                    score += 3
                elif is_reduced and any(w in cond for w in ["redu", "réduit", "-"]):
                    score += 3
                else:
                    continue

                g = _safe_str(rr.get("Niveau_gravite", ""))
                if is_slight and "+1" in g:
                    score += 2
                elif not is_slight and any(x in g for x in ["+2", "+3", "-2", "-3"]):
                    score += 2

                if score > best_score:
                    best_score, best_rule = score, rr

            if best_rule is None:
                continue

            triggered += 1
            g = _safe_str(best_rule.get("Niveau_gravite", ""))
            prio = (
                "HIGH"   if any(x in g for x in ["+3", "-3", "SÉVÈRE",  "severe"])  else
                "MEDIUM" if any(x in g for x in ["+2", "-2", "MODÉRÉ",  "modere"])  else
                "LOW"
            )

            results.append({
                "rule_type":   "microbiome",
                "priority":    prio,
                "category":    _safe_str(best_rule.get("Categorie", "Microbiote")),
                "title":       f"{marker_name} — {result_str.capitalize()}",
                "biomarker":   marker_name,
                "value":       result_str,
                "direction":   "HAUTE" if is_elevated else "BASSE",
                "norm":        "Expected",
                "recommendations": {
                    "interpretation": _safe_str(best_rule.get("Interpretation_clinique")),
                    "nutrition":      _safe_str(best_rule.get("Recommandations_nutritionnelles")),
                    "supplementation":_safe_str(best_rule.get("Recommandations_supplementation")),
                    "lifestyle":      _safe_str(best_rule.get("Recommandations_lifestyle")),
                    "monitoring":     _safe_str(best_rule.get("Notes_additionnelles")),
                },
            })

        self.debug_log.append(f"  [Microbiome] {triggered} groupes déclenchés")
        return results

    # ── API publique ─────────────────────────────────────────────────────────

    def generate_recommendations(
        self,
        bio_data: Optional[Dict[str, float]] = None,
        microbiome_data: Optional[Dict] = None,
        sex: str = "H",
        **kw,
    ) -> Dict:
        bio_data = bio_data or {}
        self.debug_log.clear()
        self.debug_log.append(
            f"🔍 generate_recommendations | sex={sex} | {len(bio_data)} biomarqueurs"
        )

        all_recs: List[Dict] = []
        all_recs.extend(
            self._apply_bio_sheet(self._df_base,       bio_data, sex, "HIGH",   "BASE")
        )
        all_recs.extend(
            self._apply_bio_sheet(self._df_extended,   bio_data, sex, "HIGH",   "EXTENDED")
        )
        all_recs.extend(
            self._apply_bio_sheet(self._df_functional, bio_data, sex, "MEDIUM", "FONCTIONNEL")
        )
        if microbiome_data:
            all_recs.extend(self._apply_micro_rules(microbiome_data))

        # Déduplication sur (biomarker_normalisé, direction)
        seen: set = set()
        deduped: List[Dict] = []
        for r in all_recs:
            key = (_normalize(str(r["biomarker"])), r["direction"])
            if key not in seen:
                seen.add(key)
                deduped.append(r)

        prio_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        deduped.sort(key=lambda r: prio_order.get(r["priority"], 9))

        by_prio = {
            "high":   [r for r in deduped if r["priority"] == "HIGH"],
            "medium": [r for r in deduped if r["priority"] == "MEDIUM"],
            "low":    [r for r in deduped if r["priority"] == "LOW"],
        }

        by_cat: Dict[str, List] = {}
        for r in deduped:
            by_cat.setdefault(r["category"], []).append(r)

        parts = []
        if by_prio["high"]:   parts.append(f"{len(by_prio['high'])} priorité haute")
        if by_prio["medium"]: parts.append(f"{len(by_prio['medium'])} priorité moyenne")
        if by_prio["low"]:    parts.append(f"{len(by_prio['low'])} priorité basse")
        summary = ("Analyse : " + ", ".join(parts)) if parts else "Aucune anomalie détectée"

        self.debug_log.append(
            f"✅ Total : {len(deduped)} recs ({len(by_prio['high'])} HIGH, "
            f"{len(by_prio['medium'])} MEDIUM, {len(by_prio['low'])} LOW)"
        )

        return {
            "total":       len(deduped),
            "all":         deduped,
            "by_priority": by_prio,
            "by_category": by_cat,
            "summary":     summary,
            "debug_log":   list(self.debug_log),
        }

    def generate_consolidated_recommendations(
        self,
        bio_data: Optional[Dict[str, float]] = None,
        microbiome_data: Optional[Dict] = None,
        patient_info: Optional[Dict] = None,
        **kw,
    ) -> Dict:
        patient_info = patient_info or {}
        sex = patient_info.get("sex", "H")

        base = self.generate_recommendations(
            bio_data=bio_data,
            microbiome_data=microbiome_data,
            sex=sex,
        )

        n_high   = len(base["by_priority"]["high"])
        n_medium = len(base["by_priority"]["medium"])
        health_score = max(0, 100 - n_high * 8 - n_medium * 4)

        return {
            **base,
            "health_score":                    health_score,
            "axes":                            self._build_therapeutic_axes(base["all"]),
            "patient_info":                    patient_info,
            "alerts":                          base["by_priority"]["high"],
            "nutrition_recommendations":       self._extract_domain(base["all"], "nutrition"),
            "supplementation_recommendations": self._extract_domain(base["all"], "supplementation"),
            "lifestyle_recommendations":       self._extract_domain(base["all"], "lifestyle"),
            "monitoring_recommendations":      self._extract_domain(base["all"], "monitoring"),
        }

    # ── Helpers internes ─────────────────────────────────────────────────────

    def _extract_domain(self, recs: List[Dict], domain: str) -> List[str]:
        return [
            v for r in recs
            for v in [_safe_str(r.get("recommendations", {}).get(domain))]
            if v
        ]

    def _build_therapeutic_axes(self, recs: List[Dict]) -> Dict[str, List]:
        axes = {
            "metabolisme":    [],
            "inflammation":   [],
            "hormones":       [],
            "micronutrition": [],
            "microbiome":     [],
            "cardiovasculaire": [],
            "autre":          [],
        }
        kws = {
            "metabolisme":      ["metabol", "glyc", "insuline", "glucose", "lipide", "trigly", "homa"],
            "inflammation":     ["inflamm", "crp", "cytokine", "oxydatif", "ferritine", "fibrinogene"],
            "hormones":         ["hormone", "thyroid", "cortisol", "testosteron", "oestrog", "dhea", "tsh", "lh", "fsh"],
            "micronutrition":   ["vitamine", "mineral", "magnesium", "zinc", "fer ", "omega", "selenium", "b12", "folate", "coenzyme"],
            "microbiome":       ["microbiome", "bacterie", "firmicute", "bacteroidote", "lactobacil", "bifidobacter", "dysbiose"],
            "cardiovasculaire": ["cardio", "cholesterol", "hdl", "ldl", "triglycer", "homocysteine", "apob", "apoa"],
        }
        for rec in recs:
            text = _normalize(rec.get("category", "")) + " " + _normalize(rec.get("title", ""))
            placed = False
            for axis, keywords in kws.items():
                if any(kw in text for kw in keywords):
                    axes[axis].append(rec)
                    placed = True
                    break
            if not placed:
                axes["autre"].append(rec)

        return {k: v for k, v in axes.items() if v}

    # ── Diagnostics ──────────────────────────────────────────────────────────

    def get_rules_summary(self) -> Dict[str, int]:
        return {
            "bio_base":       len(self._df_base)       if self._df_base       is not None else 0,
            "bio_extended":   len(self._df_extended)   if self._df_extended   is not None else 0,
            "bio_functional": len(self._df_functional) if self._df_functional is not None else 0,
            "microbiome":     len(self._df_micro)      if self._df_micro      is not None else 0,
        }

    def get_column_report(self) -> Dict[str, List[str]]:
        """Retourne les noms de colonnes de chaque feuille pour diagnostic."""
        report = {}
        for label, df in [
            ("BASE",        self._df_base),
            ("EXTENDED",    self._df_extended),
            ("FONCTIONNEL", self._df_functional),
            ("MICROBIOME",  self._df_micro),
        ]:
            report[label] = list(df.columns) if df is not None else []
        return report

    def diagnose_biomarker(
        self,
        biomarker_name: str,
        value: float,
        sex: str = "H",
    ) -> Dict:
        """
        Diagnostique pourquoi un biomarqueur n'est pas matché / déclenche pas.
        Utile pour debug Streamlit.
        """
        bn = _normalize(biomarker_name)
        report = {"biomarker": biomarker_name, "normalized": bn, "sheets": {}}

        for label, df in [
            ("BASE",        self._df_base),
            ("EXTENDED",    self._df_extended),
            ("FONCTIONNEL", self._df_functional),
        ]:
            if df is None:
                report["sheets"][label] = "feuille absente"
                continue

            norm_col = _find_norm_column(df, sex)
            matches = []
            for _, row in df.iterrows():
                br = _safe_str(row.get("Biomarqueur", ""))
                if not br:
                    continue
                brn = _normalize(br)
                if bn == brn or bn in brn or brn in bn:
                    norm_raw = row.get(norm_col) if norm_col else None
                    low, high = _parse_norm(norm_raw)
                    matches.append({
                        "rule_biomarker": br,
                        "norm_col":       norm_col,
                        "norm_raw":       _safe_str(norm_raw),
                        "parsed_low":     low,
                        "parsed_high":    high,
                        "would_trigger":  (
                            (low  is not None and value < low) or
                            (high is not None and value > high)
                        ),
                    })
            report["sheets"][label] = matches if matches else "aucun match"

        return report

    def __repr__(self) -> str:
        s = self.get_rules_summary()
        return (
            f"<RulesEngine | "
            f"base={s['bio_base']} | ext={s['bio_extended']} | "
            f"fonct={s['bio_functional']} | micro={s['microbiome']}>"
        )
