"""
ALGO-LIFE Rules Engine v3.0 - Calqué sur Bases_regles_Synlab.xlsx
"""
from __future__ import annotations
import os, re, unicodedata
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd


def _normalize(s: str) -> str:
    s = str(s).strip().lower()
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"\(.*?\)", "", s).strip()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _parse_norm(norm_str: Any) -> Tuple[Optional[float], Optional[float]]:
    if norm_str is None or (isinstance(norm_str, float) and pd.isna(norm_str)):
        return None, None
    s = re.sub(r"\s*[A-Za-z/%µ]+.*$", "", str(norm_str).strip()).strip()
    if not s:
        return None, None
    m = re.match(r"^<\s*([\d.,]+)$", s)
    if m: return None, float(m.group(1).replace(",", "."))
    m = re.match(r"^>\s*([\d.,]+)$", s)
    if m: return float(m.group(1).replace(",", ".")), None
    m = re.match(r"^([\d.,]+)\s*[–\-]\s*([\d.,]+)$", s)
    if m: return float(m.group(1).replace(",", ".")), float(m.group(2).replace(",", "."))
    return None, None


def _safe_str(v: Any) -> str:
    if v is None: return ""
    if isinstance(v, float) and pd.isna(v): return ""
    return str(v).strip()


class RulesEngine:
    _BIO_SHEETS = {
        "base":       ["BASE_40",        "Bio_Base",       "bio_base"],
        "extended":   ["EXTENDED_92",    "Bio_Extended",   "bio_extended"],
        "functional": ["FONCTIONNEL_134","Bio_Functional",  "bio_functional"],
    }
    _MICRO_SHEETS = ["Microbiote", "Microbiome", "microbiome"]

    def __init__(self, rules_excel_path: str):
        self.rules_excel_path = rules_excel_path
        self._df_base:       Optional[pd.DataFrame] = None
        self._df_extended:   Optional[pd.DataFrame] = None
        self._df_functional: Optional[pd.DataFrame] = None
        self._df_micro:      Optional[pd.DataFrame] = None
        self._load_rules()

    def _load_rules(self):
        if not os.path.exists(self.rules_excel_path):
            raise FileNotFoundError(f"Fichier introuvable : {self.rules_excel_path}")
        xl = pd.ExcelFile(self.rules_excel_path)
        available = xl.sheet_names
        print(f"📂 Feuilles : {available}")
        for key, attr in [("base","_df_base"),("extended","_df_extended"),("functional","_df_functional")]:
            for c in self._BIO_SHEETS[key]:
                if c in available:
                    df = pd.read_excel(self.rules_excel_path, sheet_name=c)
                    setattr(self, attr, df)
                    print(f"  ✅ {c} → {len(df)} règles ({key})")
                    break
        for c in self._MICRO_SHEETS:
            if c in available:
                df = pd.read_excel(self.rules_excel_path, sheet_name=c)
                self._df_micro = df
                print(f"  ✅ {c} → {len(df)} règles microbiote")
                break

    def _apply_bio_sheet(self, df, bio_data: Dict[str,float], sex: str, priority: str) -> List[Dict]:
        results = []
        if df is None or df.empty:
            return results
        bio_norm = {_normalize(k): v for k, v in bio_data.items() if v is not None}
        for _, row in df.iterrows():
            biomarker_raw = _safe_str(row.get("Biomarqueur",""))
            if not biomarker_raw:
                continue
            b_norm = _normalize(biomarker_raw)
            patient_val = None
            for kn, val in bio_norm.items():
                if kn == b_norm or b_norm in kn or kn in b_norm:
                    patient_val = val
                    break
            if patient_val is None:
                continue
            norm_col = "Normes H" if str(sex).upper() in ("H","M") else "Normes F"
            norm_raw = row.get(norm_col) or row.get("Normes H")
            low, high = _parse_norm(norm_raw)
            if low is None and high is None:
                continue
            is_low  = (low  is not None) and (patient_val < low)
            is_high = (high is not None) and (patient_val > high)
            if not is_low and not is_high:
                continue
            d = "BASSE" if is_low else "HAUTE"
            results.append({
                "rule_type":  "bio",
                "priority":   priority,
                "category":   _safe_str(row.get("Catégorie","Biologie")),
                "title":      f"{biomarker_raw} {'↓ Bas' if is_low else '↑ Élevé'}",
                "biomarker":  biomarker_raw,
                "value":      patient_val,
                "direction":  d,
                "norm":       _safe_str(norm_raw),
                "recommendations": {
                    "interpretation": _safe_str(row.get(f"{d} - Interprétation")),
                    "nutrition":      _safe_str(row.get(f"{d} - Nutrition")),
                    "supplementation":_safe_str(row.get(f"{d} - Micronutrition")),
                    "lifestyle":      _safe_str(row.get(f"{d} - Lifestyle")),
                    "monitoring":     "",
                },
            })
        return results

    def _apply_micro_rules(self, microbiome_data: Dict) -> List[Dict]:
        results = []
        if self._df_micro is None or self._df_micro.empty:
            return results
        groups: List[Dict] = []
        if isinstance(microbiome_data, dict):
            groups = microbiome_data.get("bacteria_groups") or microbiome_data.get("bacteria") or []
            if not groups:
                groups = [{"name": k, "result": str(v)} for k, v in microbiome_data.items()
                          if k not in ("dysbiosis_index","diversity","bacteria_groups","bacteria")]
        for group in groups:
            result_str = str(group.get("result","") or group.get("abundance","")).lower()
            if not result_str or "expected" in result_str:
                continue
            is_elevated = any(w in result_str for w in ["elevat","high","élevé","eleve","deviating high"])
            is_reduced  = any(w in result_str for w in ["reduc","low","réduit","reduit","deviating low"])
            is_slight   = "slight" in result_str or "leger" in result_str
            marker_name = (group.get("group") or group.get("category") or
                          group.get("name") or group.get("Marqueur_bacterien",""))
            m_norm = _normalize(str(marker_name))
            best, best_rule = 0, None
            for _, rr in self._df_micro.iterrows():
                rm = _normalize(_safe_str(rr.get("Marqueur_bacterien","")))
                if not rm: continue
                score = 0
                if rm == m_norm: score = 10
                elif rm in m_norm or m_norm in rm: score = 5
                if score == 0: continue
                cond = _safe_str(rr.get("Condition_declenchement","")).lower()
                if is_elevated and any(w in cond for w in ["elev","élevé","+"]):    score += 3
                elif is_reduced and any(w in cond for w in ["redu","réduit","-"]): score += 3
                else: continue
                g = _safe_str(rr.get("Niveau_gravite",""))
                if is_slight and "+1" in g: score += 2
                elif not is_slight and any(x in g for x in ["+2","+3","-2","-3"]): score += 2
                if score > best:
                    best, best_rule = score, rr
            if best_rule is None: continue
            g = _safe_str(best_rule.get("Niveau_gravite",""))
            prio = ("HIGH"   if any(x in g for x in ["+3","-3","SÉVÈRE"]) else
                    "MEDIUM" if any(x in g for x in ["+2","-2","MODÉRÉ"]) else "LOW")
            results.append({
                "rule_type":  "microbiome",
                "priority":   prio,
                "category":   _safe_str(best_rule.get("Categorie","Microbiote")),
                "title":      f"{marker_name} — {result_str.capitalize()}",
                "biomarker":  marker_name,
                "value":      result_str,
                "direction":  "HAUTE" if is_elevated else "BASSE",
                "norm":       "Expected",
                "recommendations": {
                    "interpretation": _safe_str(best_rule.get("Interpretation_clinique")),
                    "nutrition":      _safe_str(best_rule.get("Recommandations_nutritionnelles")),
                    "supplementation":_safe_str(best_rule.get("Recommandations_supplementation")),
                    "lifestyle":      _safe_str(best_rule.get("Recommandations_lifestyle")),
                    "monitoring":     _safe_str(best_rule.get("Notes_additionnelles")),
                },
            })
        return results

    def generate_recommendations(self, bio_data=None, microbiome_data=None, sex="H", **kw) -> Dict:
        bio_data = bio_data or {}
        all_recs = []
        all_recs.extend(self._apply_bio_sheet(self._df_base,       bio_data, sex, "HIGH"))
        all_recs.extend(self._apply_bio_sheet(self._df_extended,   bio_data, sex, "HIGH"))
        all_recs.extend(self._apply_bio_sheet(self._df_functional, bio_data, sex, "MEDIUM"))
        if microbiome_data:
            all_recs.extend(self._apply_micro_rules(microbiome_data))
        # Déduplication sur (biomarker, direction)
        seen, deduped = set(), []
        for r in all_recs:
            key = (r["biomarker"], r["direction"])
            if key not in seen:
                seen.add(key)
                deduped.append(r)
        prio_order = {"HIGH":0,"MEDIUM":1,"LOW":2}
        deduped.sort(key=lambda r: prio_order.get(r["priority"], 9))
        by_prio = {
            "high":   [r for r in deduped if r["priority"]=="HIGH"],
            "medium": [r for r in deduped if r["priority"]=="MEDIUM"],
            "low":    [r for r in deduped if r["priority"]=="LOW"],
        }
        by_cat: Dict[str,List] = {}
        for r in deduped:
            by_cat.setdefault(r["category"],[]).append(r)
        parts = []
        if by_prio["high"]:   parts.append(f"{len(by_prio['high'])} priorité haute")
        if by_prio["medium"]: parts.append(f"{len(by_prio['medium'])} priorité moyenne")
        summary = ("Analyse : " + ", ".join(parts)) if parts else "Aucune anomalie détectée"
        return {"total":len(deduped),"all":deduped,"by_priority":by_prio,"by_category":by_cat,"summary":summary}

    def generate_consolidated_recommendations(self, bio_data=None, microbiome_data=None,
                                               patient_info=None, **kw) -> Dict:
        patient_info = patient_info or {}
        sex = patient_info.get("sex","H")
        base = self.generate_recommendations(bio_data=bio_data, microbiome_data=microbiome_data, sex=sex)
        hs = max(0, 100 - len(base["by_priority"]["high"])*8 - len(base["by_priority"]["medium"])*4)
        return {
            **base,
            "health_score": hs,
            "axes":         self._build_therapeutic_axes(base["all"]),
            "patient_info": patient_info,
            "alerts":       base["by_priority"]["high"],
            "nutrition_recommendations":       self._extract_domain(base["all"],"nutrition"),
            "supplementation_recommendations": self._extract_domain(base["all"],"supplementation"),
            "lifestyle_recommendations":       self._extract_domain(base["all"],"lifestyle"),
            "monitoring_recommendations":      self._extract_domain(base["all"],"monitoring"),
        }

    def _extract_domain(self, recs, domain):
        return [_safe_str(r.get("recommendations",{}).get(domain)) for r in recs
                if _safe_str(r.get("recommendations",{}).get(domain))]

    def _build_therapeutic_axes(self, recs):
        axes = {"metabolisme":[],"inflammation":[],"hormones":[],"micronutrition":[],
                "microbiome":[],"cardiovasculaire":[],"autre":[]}
        kws = {
            "metabolisme":      ["metabol","glyc","insuline","glucose","lipide","trigly"],
            "inflammation":     ["inflamm","crp","cytokine","oxydatif","ferritine"],
            "hormones":         ["hormone","thyroid","cortisol","testosteron","oestrog","dhea","tsh"],
            "micronutrition":   ["vitamine","mineral","magnesium","zinc","fer","omega","selenium","b12","folate"],
            "microbiome":       ["microbiome","bacterie","firmicute","bacteroidote","lactobacil","bifidobacter"],
            "cardiovasculaire": ["cardio","cholesterol","hdl","ldl","triglycer","homocysteine"],
        }
        for rec in recs:
            text = _normalize(rec.get("category","")) + " " + _normalize(rec.get("title",""))
            placed = False
            for axis, keywords in kws.items():
                if any(kw in text for kw in keywords):
                    axes[axis].append(rec); placed=True; break
            if not placed: axes["autre"].append(rec)
        return {k:v for k,v in axes.items() if v}

    def get_rules_summary(self):
        return {
            "bio_base":       len(self._df_base)       if self._df_base       is not None else 0,
            "bio_extended":   len(self._df_extended)   if self._df_extended   is not None else 0,
            "bio_functional": len(self._df_functional) if self._df_functional is not None else 0,
            "microbiome":     len(self._df_micro)      if self._df_micro      is not None else 0,
        }

    def __repr__(self):
        s = self.get_rules_summary()
        return f"<RulesEngine | bio={s['bio_base']+s['bio_extended']+s['bio_functional']} | micro={s['microbiome']}>"
