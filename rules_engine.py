"""
ALGO-LIFE Rules Engine v3.2 - Basé sur analyse réelle de Bases_regles_Synlab.xlsx
Fixes v3.2 (après inspection des fichiers Excel réels) :

BIO :
  - Colonnes CONFIRMÉES : 'Biomarqueur', 'Normes H', 'Normes F'
  - Colonnes recs CONFIRMÉES : 'BASSE/HAUTE - Interprétation/Nutrition/Micronutrition/Lifestyle'
  - _parse_norm robuste : tiret long U+2013, unités, doubles plages, formats français

MICROBIOME (refonte totale) :
  - Source de vérité : bacteria_individual (48 bactéries nominales), PAS bacteria_groups
  - Matching par nom exact de bactérie ex: 'Various Bacilli', 'Akkermansia muciniphila'
  - Sélection règle par abundance_level entier (+1/+2/+3/-1/-2/-3)
  - Condition_declenchement : contient 'lévation' (élevé) ou 'éduction' (réduit)
  - Niveau_gravite : entier ou string '+1 (LÉGER)', '-2 (MODÉRÉ)', 3, etc.
  - stool_biomarkers (calprotectine, sIgA, histamine...) aussi traités
"""
from __future__ import annotations
import os, re, unicodedata
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd


# ─────────────────────────────────────────────────────────────────────────────
# Utilitaires texte
# ─────────────────────────────────────────────────────────────────────────────

def _normalize(s: str) -> str:
    s = str(s).strip().lower()
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"\(.*?\)", "", s).strip()
    s = re.sub(r"[^a-z0-9 &]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _safe_str(v: Any) -> str:
    if v is None: return ""
    if isinstance(v, float) and pd.isna(v): return ""
    return str(v).strip()


def _parse_norm(norm_str: Any) -> Tuple[Optional[float], Optional[float]]:
    """
    Parse norme textuelle -> (low, high).
    Gère : '13.5-17.5', '13.5\u201317.5', '< 5.7 %', '> 40',
           '70-99 mg/dL (3.9-5.5 mmol/L)', '0,50-1,20', etc.
    """
    if norm_str is None or (isinstance(norm_str, float) and pd.isna(norm_str)):
        return None, None

    raw = str(norm_str).strip()
    raw = re.sub(r"(\d),(\d)", r"\1.\2", raw)       # virgule décimale FR
    raw = re.sub(r"\(.*?\)", "", raw).strip()         # supprimer parenthèses

    # Garder seulement partie numérique/opérateur
    s = re.sub(r"[^0-9<>=.\-\u2013\u2014\s].*$", "", raw).strip()
    if not s: return None, None

    m = re.match(r"^<\s*=?\s*([\d.]+)$", s)
    if m: return None, float(m.group(1))

    m = re.match(r"^>\s*=?\s*([\d.]+)$", s)
    if m: return float(m.group(1)), None

    m = re.match(r"^([\d.]+)\s*[\-\u2013\u2014]\s*([\d.]+)$", s)
    if m:
        lo, hi = float(m.group(1)), float(m.group(2))
        return (lo, hi) if lo <= hi else (hi, lo)

    return None, None


def _parse_gravite(g: Any) -> int:
    """Extrait le niveau entier depuis différents formats : 1, -1, '+1 (LEGER)', etc."""
    if g is None or (isinstance(g, float) and pd.isna(g)): return 0
    if isinstance(g, (int, float)) and not (isinstance(g, float) and pd.isna(g)):
        return int(g)
    m = re.search(r"([+-]?\d+)", str(g))
    return int(m.group(1)) if m else 0


# ─────────────────────────────────────────────────────────────────────────────
# Moteur de règles
# ─────────────────────────────────────────────────────────────────────────────

class RulesEngine:

    _BIO_SHEETS = {
        "base":       ["BASE_40", "Bio_Base", "bio_base", "Base"],
        "extended":   ["EXTENDED_92", "Bio_Extended", "bio_extended", "Extended"],
        "functional": ["FONCTIONNEL_134", "Bio_Functional", "bio_functional", "Fonctionnel"],
    }
    _MICRO_SHEETS = ["Microbiote", "Microbiome", "microbiome", "Micro"]

    def __init__(self, rules_excel_path: str):
        self.rules_excel_path = rules_excel_path
        self._df_base:       Optional[pd.DataFrame] = None
        self._df_extended:   Optional[pd.DataFrame] = None
        self._df_functional: Optional[pd.DataFrame] = None
        self._df_micro:      Optional[pd.DataFrame] = None
        self._micro_index:   Dict[str, pd.DataFrame] = {}
        self.debug_log:      List[str] = []
        self._load_rules()

    # ── Chargement ──────────────────────────────────────────────────────────

    def _load_rules(self):
        if not os.path.exists(self.rules_excel_path):
            raise FileNotFoundError(f"Fichier introuvable : {self.rules_excel_path}")

        xl = pd.ExcelFile(self.rules_excel_path)
        available = xl.sheet_names
        msg = f"Feuilles disponibles : {available}"
        print(msg); self.debug_log.append(msg)

        for key, attr in [
            ("base", "_df_base"), ("extended", "_df_extended"), ("functional", "_df_functional")
        ]:
            for name in self._BIO_SHEETS[key]:
                if name in available:
                    df = pd.read_excel(self.rules_excel_path, sheet_name=name)
                    setattr(self, attr, df)
                    msg = f"  OK '{name}' -> {len(df)} regles bio ({key})"
                    print(msg); self.debug_log.append(msg)
                    break
            else:
                msg = f"  ATTENTION: feuille bio '{key}' non trouvee"
                print(msg); self.debug_log.append(msg)

        for name in self._MICRO_SHEETS:
            if name in available:
                df = pd.read_excel(self.rules_excel_path, sheet_name=name)
                self._df_micro = df
                # Index par marqueur bacterien (normalise) pour lookup O(1)
                for bm, grp in df.groupby("Marqueur_bacterien"):
                    self._micro_index[_normalize(str(bm))] = grp.copy()
                msg = f"  OK '{name}' -> {len(df)} regles microbiote | {len(self._micro_index)} marqueurs indexes"
                print(msg); self.debug_log.append(msg)
                break

    # ── Application règles bio ───────────────────────────────────────────────

    def _apply_bio_sheet(
        self,
        df: Optional[pd.DataFrame],
        bio_data: Dict[str, float],
        sex: str,
        priority: str,
        label: str = "",
    ) -> List[Dict]:
        results = []
        if df is None or df.empty:
            return results

        # Index patient normalise
        bio_norm: Dict[str, Tuple[str, float]] = {}
        for k, v in bio_data.items():
            if v is not None:
                bio_norm[_normalize(k)] = (k, float(v))

        # Colonne norme - noms CONFIRMES dans le fichier Excel
        norm_col = "Normes H" if str(sex).upper() in ("H", "M") else "Normes F"
        if norm_col not in df.columns:
            for c in df.columns:
                if "norme" in c.lower():
                    norm_col = c; break

        matched = 0
        triggered = 0

        for _, row in df.iterrows():
            bm_raw = _safe_str(row.get("Biomarqueur", ""))
            if not bm_raw:
                continue

            bm_norm = _normalize(bm_raw)

            # Matching patient -> regle
            patient_orig = None
            patient_val  = None

            if bm_norm in bio_norm:
                patient_orig, patient_val = bio_norm[bm_norm]
            else:
                for kn, (k_orig, v) in bio_norm.items():
                    if bm_norm in kn or kn in bm_norm:
                        patient_orig, patient_val = k_orig, v
                        break

            if patient_val is None:
                continue
            matched += 1

            norm_raw = row.get(norm_col)
            if _safe_str(norm_raw) == "" and norm_col != "Normes H":
                norm_raw = row.get("Normes H")

            low, high = _parse_norm(norm_raw)
            if low is None and high is None:
                continue

            is_low  = (low  is not None) and (patient_val < low)
            is_high = (high is not None) and (patient_val > high)
            if not is_low and not is_high:
                continue
            triggered += 1

            d = "BASSE" if is_low else "HAUTE"

            # Colonnes recs - noms CONFIRMES dans le fichier Excel
            results.append({
                "rule_type":   "bio",
                "priority":    priority,
                "category":    _safe_str(row.get("Categorie", row.get("Catégorie", "Biologie"))),
                "title":       f"{bm_raw} {'bas' if is_low else 'eleve'}",
                "biomarker":   bm_raw,
                "value":       patient_val,
                "direction":   d,
                "norm":        _safe_str(norm_raw),
                "recommendations": {
                    "interpretation": _safe_str(row.get(f"{d} - Interprétation", "")),
                    "nutrition":      _safe_str(row.get(f"{d} - Nutrition", "")),
                    "supplementation":_safe_str(row.get(f"{d} - Micronutrition", "")),
                    "lifestyle":      _safe_str(row.get(f"{d} - Lifestyle", "")),
                    "monitoring":     "",
                },
            })

        msg = f"  [{label}] {len(bio_data)} bm | {matched} matches | {triggered} declenches"
        print(msg); self.debug_log.append(msg)
        return results

    # ── Application règles microbiome ────────────────────────────────────────

    def _apply_micro_rules(self, microbiome_data: Dict) -> List[Dict]:
        """
        Utilise bacteria_individual (48 bactéries nominales, clé abundance_level).
        Fallback : bacteria_groups si bacteria_individual absent.
        Traite aussi stool_biomarkers (calprotectine, sIgA, histamine...).
        """
        results = []
        if not self._micro_index:
            self.debug_log.append("  ATTENTION: index microbiote vide")
            return results

        if not isinstance(microbiome_data, dict):
            return results

        # ── Source 1 : bacteria_individual ───────────────────────────────────
        bacteria = microbiome_data.get("bacteria_individual", [])

        # Fallback si absence de bacteria_individual
        if not bacteria:
            bacteria = (
                microbiome_data.get("bacteria_groups")
                or microbiome_data.get("bacteria")
                or []
            )
            # Convertir format bacteria_groups -> format bacteria_individual
            # bacteria_groups a 'result' string, pas 'abundance_level' int
            # On mappe : 'Slightly Elevated' -> +1, 'Elevated' -> +2, 'Reduced' -> -1, etc.
            converted = []
            for b in bacteria:
                result_str = str(b.get("result", "") or b.get("abundance", "")).lower()
                if "expected" in result_str or not result_str:
                    continue
                lvl = (
                    2  if "deviating" in result_str and "slightly" not in result_str and ("high" in result_str or "elev" in result_str) else
                    -2 if "deviating" in result_str and "slightly" not in result_str and ("low" in result_str or "redu" in result_str) else
                    1  if "slightly" in result_str and ("high" in result_str or "elev" in result_str) else
                    -1 if "slightly" in result_str and ("low" in result_str or "redu" in result_str) else
                    1  if "elev" in result_str or "high" in result_str else
                    -1 if "redu" in result_str or "low" in result_str else
                    0
                )
                if lvl != 0:
                    converted.append({
                        "name": b.get("name") or b.get("category") or b.get("group", ""),
                        "abundance_level": lvl,
                    })
            bacteria = converted

        triggered = 0

        for bact in bacteria:
            abundance_level = bact.get("abundance_level", 0)
            if abundance_level == 0:
                continue

            bact_name = str(
                bact.get("name") or bact.get("group") or bact.get("category") or ""
            ).strip()
            if not bact_name:
                continue

            bact_norm = _normalize(bact_name)
            is_elevated = abundance_level > 0
            abs_level   = abs(abundance_level)  # 1, 2 ou 3

            # Chercher dans l'index
            rules_df = None
            if bact_norm in self._micro_index:
                rules_df = self._micro_index[bact_norm]
            else:
                for rk, rdf in self._micro_index.items():
                    if bact_norm in rk or rk in bact_norm:
                        rules_df = rdf; break

            if rules_df is None:
                self.debug_log.append(f"    MICRO no rule: '{bact_name}'")
                continue

            # Sélectionner la meilleure règle : direction + niveau
            best_row   = None
            best_score = -1

            for _, rr in rules_df.iterrows():
                cond    = _safe_str(rr.get("Condition_declenchement", "")).lower()
                gravite = _parse_gravite(rr.get("Niveau_gravite"))

                # Direction
                is_elev_rule = ("lev" in cond) or (gravite > 0)   # Élévation
                is_redu_rule = ("duc" in cond) or (gravite < 0)    # Réduction

                if is_elevated and not is_elev_rule: continue
                if not is_elevated and not is_redu_rule: continue

                # Niveau (correspondance exacte = max points)
                rule_abs = abs(gravite) if gravite != 0 else 1
                score = 10 if rule_abs == abs_level else (5 - abs(rule_abs - abs_level))

                if score > best_score:
                    best_score, best_row = score, rr

            if best_row is None:
                self.debug_log.append(
                    f"    MICRO no match rule: '{bact_name}' lvl={abundance_level:+d}"
                )
                continue

            triggered += 1
            g     = _parse_gravite(best_row.get("Niveau_gravite"))
            abs_g = abs(g)
            prio  = "HIGH" if abs_g >= 3 else ("MEDIUM" if abs_g == 2 else "LOW")

            results.append({
                "rule_type":   "microbiome",
                "priority":    prio,
                "category":    _safe_str(best_row.get("Categorie", "Microbiote")),
                "title":       f"{bact_name} ({'eleve' if is_elevated else 'reduit'}, niv {abundance_level:+d})",
                "biomarker":   bact_name,
                "value":       abundance_level,
                "direction":   "HAUTE" if is_elevated else "BASSE",
                "norm":        "Expected (0)",
                "recommendations": {
                    "interpretation": _safe_str(best_row.get("Interpretation_clinique")),
                    "nutrition":      _safe_str(best_row.get("Recommandations_nutritionnelles")),
                    "supplementation":_safe_str(best_row.get("Recommandations_supplementation")),
                    "lifestyle":      _safe_str(best_row.get("Recommandations_lifestyle")),
                    "monitoring":     _safe_str(best_row.get("Notes_additionnelles")),
                },
            })

        # ── Source 2 : stool_biomarkers ──────────────────────────────────────
        stool = microbiome_data.get("stool_biomarkers", {})
        if isinstance(stool, dict):
            for bm_name, bm_data in stool.items():
                status = str(bm_data.get("status", "")).upper()
                is_high = any(w in status for w in ["ÉLEVÉ", "ELEVE", "HIGH", "TRES"])
                is_low  = any(w in status for w in ["BAS", "LOW", "REDUIT"])
                if not is_high and not is_low:
                    continue

                try:
                    val_str = str(bm_data.get("value", "0")).replace("<","").replace(">","").replace(",",".").strip()
                    val = float(re.sub(r"[^0-9.]", "", val_str)) if val_str else None
                except:
                    val = None

                direction = "HAUTE" if is_high else "BASSE"
                prio = "HIGH" if "TRES" in status or "TRÈS" in status else "MEDIUM"
                triggered += 1

                # Chercher règle associée
                bm_norm = _normalize(bm_name)
                best_row_s = None
                for rk, rdf in self._micro_index.items():
                    if bm_norm in rk or rk in bm_norm:
                        for _, rr in rdf.iterrows():
                            g = _parse_gravite(rr.get("Niveau_gravite"))
                            if is_high and g > 0: best_row_s = rr; break
                            if is_low  and g < 0: best_row_s = rr; break
                    if best_row_s is not None: break

                results.append({
                    "rule_type":   "microbiome",
                    "priority":    prio,
                    "category":    "Biomarqueurs fecaux",
                    "title":       f"{bm_name} ({'eleve' if is_high else 'bas'}, selles)",
                    "biomarker":   bm_name,
                    "value":       val,
                    "direction":   direction,
                    "norm":        _safe_str(bm_data.get("reference", "")),
                    "recommendations": {
                        "interpretation": _safe_str(best_row_s.get("Interpretation_clinique") if best_row_s is not None else ""),
                        "nutrition":      _safe_str(best_row_s.get("Recommandations_nutritionnelles") if best_row_s is not None else ""),
                        "supplementation":_safe_str(best_row_s.get("Recommandations_supplementation") if best_row_s is not None else ""),
                        "lifestyle":      _safe_str(best_row_s.get("Recommandations_lifestyle") if best_row_s is not None else ""),
                        "monitoring":     f"Val: {val} | Ref: {bm_data.get('reference','')}",
                    },
                })

        msg = f"  [Microbiome] {len(bacteria)} bacteries | {triggered} declenches"
        print(msg); self.debug_log.append(msg)
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
            f"generate_recommendations | sex={sex} | {len(bio_data)} biomarqueurs"
        )

        all_recs: List[Dict] = []
        all_recs.extend(self._apply_bio_sheet(self._df_base,       bio_data, sex, "HIGH",   "BASE"))
        all_recs.extend(self._apply_bio_sheet(self._df_extended,   bio_data, sex, "HIGH",   "EXTENDED"))
        all_recs.extend(self._apply_bio_sheet(self._df_functional, bio_data, sex, "MEDIUM", "FONCTIONNEL"))
        if microbiome_data:
            all_recs.extend(self._apply_micro_rules(microbiome_data))

        # Deduplication (biomarker normalise, direction)
        seen, deduped = set(), []
        for r in all_recs:
            key = (_normalize(str(r["biomarker"])), r["direction"])
            if key not in seen:
                seen.add(key); deduped.append(r)

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
        if by_prio["high"]:   parts.append(f"{len(by_prio['high'])} priorite haute")
        if by_prio["medium"]: parts.append(f"{len(by_prio['medium'])} priorite moyenne")
        if by_prio["low"]:    parts.append(f"{len(by_prio['low'])} priorite basse")
        summary = ("Analyse : " + ", ".join(parts)) if parts else "Aucune anomalie detectee"

        self.debug_log.append(
            f"Total: {len(deduped)} recs | {len(by_prio['high'])} HIGH | "
            f"{len(by_prio['medium'])} MEDIUM | {len(by_prio['low'])} LOW"
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
        base = self.generate_recommendations(bio_data=bio_data, microbiome_data=microbiome_data, sex=sex)
        n_h = len(base["by_priority"]["high"])
        n_m = len(base["by_priority"]["medium"])
        return {
            **base,
            "health_score":                    max(0, 100 - n_h * 8 - n_m * 4),
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
        return [v for r in recs
                for v in [_safe_str((r.get("recommendations") or {}).get(domain))] if v]

    def _build_therapeutic_axes(self, recs: List[Dict]) -> Dict[str, List]:
        axes = {k: [] for k in ["metabolisme","inflammation","hormones","micronutrition",
                                 "microbiome","cardiovasculaire","autre"]}
        kws = {
            "metabolisme":      ["metabol","glyc","insuline","glucose","lipide","trigly","homa"],
            "inflammation":     ["inflamm","crp","cytokine","oxydatif","ferritine","fibrinogene","calprotect"],
            "hormones":         ["hormone","thyroid","cortisol","testosteron","oestrog","dhea","tsh"],
            "micronutrition":   ["vitamine","mineral","magnesium","zinc","omega","selenium","b12","folate","coenzyme","carnitine"],
            "microbiome":       ["bacterie","firmicute","bacteroidote","lactobacil","bifidobacter","akkermansia",
                                 "faecalibacterium","commensals","cross feeder","inflammatory","opportunistic",
                                 "microbiome","microbiote","fecal"],
            "cardiovasculaire": ["cardio","cholesterol","hdl","ldl","triglycer","homocysteine","apob","apoa"],
        }
        for rec in recs:
            text = " ".join([
                _normalize(rec.get("category", "")),
                _normalize(rec.get("title", "")),
                _normalize(rec.get("biomarker", "")),
            ])
            placed = False
            for axis, keywords in kws.items():
                if any(kw in text for kw in keywords):
                    axes[axis].append(rec); placed = True; break
            if not placed: axes["autre"].append(rec)
        return {k: v for k, v in axes.items() if v}

    # ── Diagnostics ──────────────────────────────────────────────────────────

    def get_rules_summary(self) -> Dict[str, int]:
        return {
            "bio_base":       len(self._df_base)       if self._df_base       is not None else 0,
            "bio_extended":   len(self._df_extended)   if self._df_extended   is not None else 0,
            "bio_functional": len(self._df_functional) if self._df_functional is not None else 0,
            "microbiome":     len(self._df_micro)      if self._df_micro      is not None else 0,
            "micro_marqueurs":len(self._micro_index),
        }

    def get_column_report(self) -> Dict[str, List[str]]:
        return {
            label: list(df.columns) if df is not None else []
            for label, df in [
                ("BASE", self._df_base), ("EXTENDED", self._df_extended),
                ("FONCTIONNEL", self._df_functional), ("MICROBIOME", self._df_micro),
            ]
        }

    def diagnose_biomarker(self, biomarker_name: str, value: float, sex: str = "H") -> Dict:
        bn = _normalize(biomarker_name)
        norm_col = "Normes H" if str(sex).upper() in ("H", "M") else "Normes F"
        report = {"biomarker": biomarker_name, "normalized": bn, "sheets": {}}
        for label, df in [
            ("BASE", self._df_base), ("EXTENDED", self._df_extended), ("FONCTIONNEL", self._df_functional)
        ]:
            if df is None: report["sheets"][label] = "absente"; continue
            matches = []
            for _, row in df.iterrows():
                br = _safe_str(row.get("Biomarqueur", ""))
                brn = _normalize(br)
                if not (bn == brn or bn in brn or brn in bn): continue
                norm_raw = row.get(norm_col)
                low, high = _parse_norm(norm_raw)
                matches.append({
                    "rule_bm": br,
                    "norm":    _safe_str(norm_raw),
                    "parsed":  (low, high),
                    "would_trigger": (low is not None and value < low) or (high is not None and value > high),
                })
            report["sheets"][label] = matches or "aucun match"
        return report

    def __repr__(self) -> str:
        s = self.get_rules_summary()
        return (f"<RulesEngine v3.2 | base={s['bio_base']} ext={s['bio_extended']} "
                f"fonct={s['bio_functional']} micro={s['microbiome']} marqueurs={s['micro_marqueurs']}>")
