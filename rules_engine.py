"""
UNILABS - Rules Engine v10.0
✅ Catégorisation structurée des recommandations
✅ Support multimodal (Bio + Microbiote + Cross-analysis)
✅ Segmentation exacte : Prioritaires, À surveiller, Nutrition, Micronutrition, Hygiène de vie, Examens complémentaires, Suivi
✅ Génération robuste avec matching Excel puissant
"""

from __future__ import annotations

import os
import re
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from extractors import normalize_biomarker_name, determine_biomarker_status


# =====================================================================
# DATACLASSES POUR STRUCTURE CLAIRE
# =====================================================================
@dataclass
class RecommendationSet:
    """Ensemble structuré de recommandations"""
    prioritaires: List[str] = field(default_factory=list)
    a_surveiller: List[str] = field(default_factory=list)
    nutrition: List[str] = field(default_factory=list)
    micronutrition: List[str] = field(default_factory=list)
    hygiene_vie: List[str] = field(default_factory=list)
    examens_complementaires: List[str] = field(default_factory=list)
    suivi: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, List[str]]:
        """Conversion en dictionnaire"""
        return {
            "Prioritaires": self.prioritaires,
            "À surveiller": self.a_surveiller,
            "Nutrition": self.nutrition,
            "Micronutrition": self.micronutrition,
            "Hygiène de vie": self.hygiene_vie,
            "Examens complémentaires": self.examens_complementaires,
            "Suivi": self.suivi
        }


@dataclass
class BiomarkerInterpretation:
    """Interprétation d'un biomarqueur individuel"""
    biomarker: str
    value: Any
    unit: str
    reference: str
    status: str  # Bas, Normal, Élevé, Inconnu
    interpretation: Optional[str] = None
    nutrition: Optional[str] = None
    micronutrition: Optional[str] = None
    lifestyle: Optional[str] = None
    priority: str = "normal"  # critical, high, medium, normal


@dataclass
class CrossAnalysisResult:
    """Résultat d'analyse croisée"""
    title: str
    description: str
    severity: str  # critical, warning, info
    recommendations: List[str] = field(default_factory=list)


# =====================================================================
# HELPERS
# =====================================================================
def _df_ok(df) -> bool:
    """Vérifie qu'un DataFrame est valide et non vide"""
    return (df is not None) and hasattr(df, "empty") and (not df.empty)


def _safe_float(x: Any) -> Optional[float]:
    """Conversion sécurisée en float"""
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
    """Trouve la première colonne correspondante (tolérant casse/espaces)"""
    if not _df_ok(df):
        return None
    
    def norm(s: str) -> str:
        s = str(s).strip().upper()
        s = re.sub(r"\s+", " ", s)
        s = s.replace("'", "'")
        return s
    
    cols_norm = {norm(c): c for c in df.columns}
    
    # Exact match
    for cand in candidates:
        nc = norm(cand)
        if nc in cols_norm:
            return cols_norm[nc]
    
    # Fuzzy contains
    for cand in candidates:
        nc = norm(cand)
        for key, original in cols_norm.items():
            if nc in key or key in nc:
                return original
    
    return None


def _get_cell(row: Union[pd.Series, Dict], col: Optional[str]) -> str:
    """Récupère une cellule de manière sécurisée"""
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


def _split_recommendations(text: str) -> List[str]:
    """Découpe un texte de recommandations en items individuels"""
    if not text:
        return []
    
    # Séparer par bullet points, numéros, ou retours à la ligne multiples
    items = []
    
    # Essayer de détecter les séparateurs
    if re.search(r"[•\-\*]\s", text):
        # Bullet points
        parts = re.split(r"[•\-\*]\s", text)
        items = [p.strip() for p in parts if p.strip()]
    elif re.search(r"\d+\.\s", text):
        # Numérotation
        parts = re.split(r"\d+\.\s", text)
        items = [p.strip() for p in parts if p.strip()]
    else:
        # Retours à la ligne multiples ou points-virgules
        parts = re.split(r"[;\n]+", text)
        items = [p.strip() for p in parts if p.strip()]
    
    # Nettoyer et filtrer
    cleaned = []
    for item in items:
        item = item.strip()
        if len(item) > 5:  # Éviter les fragments trop courts
            cleaned.append(item)
    
    return cleaned if cleaned else [text.strip()]


# =====================================================================
# RULES ENGINE
# =====================================================================
class RulesEngine:
    """
    Moteur de règles multimodal avec catégorisation structurée
    """
    
    def __init__(self, rules_excel_path: str):
        self.rules_excel_path = rules_excel_path
        
        # DataFrames des règles
        self.rules_bio_base: Optional[pd.DataFrame] = None
        self.rules_bio_extended: Optional[pd.DataFrame] = None
        self.rules_bio_functional: Optional[pd.DataFrame] = None
        self.rules_microbiome: Optional[pd.DataFrame] = None
        
        # Index pour matching rapide (biomarqueurs normalisés)
        self._bio_index: Dict[str, pd.Series] = {}
        self._bio_contains_keys: List[str] = []
        
        # Microbiome rows
        self._micro_rows: List[pd.Series] = []
        
        # Chargement
        self._load_rules()
        self._build_indexes()
    
    # ─────────────────────────────────────────────────────────────────
    # CHARGEMENT DES RÈGLES
    # ─────────────────────────────────────────────────────────────────
    def _load_rules(self) -> None:
        """Charge toutes les feuilles Excel de règles"""
        if not os.path.exists(self.rules_excel_path):
            raise FileNotFoundError(f"Fichier règles introuvable: {self.rules_excel_path}")
        
        print(f"📂 Chargement règles: {self.rules_excel_path}")
        
        xl = pd.ExcelFile(self.rules_excel_path, engine="openpyxl")
        sheets = xl.sheet_names
        print(f"📋 Feuilles disponibles: {sheets}")
        
        def load_sheet(name: str) -> Optional[pd.DataFrame]:
            if name not in sheets:
                print(f"⚠️ Feuille absente: {name}")
                return None
            df = pd.read_excel(self.rules_excel_path, sheet_name=name, engine="openpyxl")
            if not _df_ok(df):
                print(f"⚠️ Feuille vide: {name}")
                return None
            print(f"✅ {name}: {len(df)} lignes chargées")
            return df
        
        # Biologie
        self.rules_bio_base = load_sheet("BASE_40")
        self.rules_bio_extended = load_sheet("EXTENDED_92")
        self.rules_bio_functional = load_sheet("FONCTIONNEL_134")
        
        # Microbiome
        self.rules_microbiome = load_sheet("Microbiote")
        
        print("✅ Chargement terminé")
    
    def _build_indexes(self) -> None:
        """Construit les index de matching rapide"""
        self._bio_index = {}
        self._bio_contains_keys = []
        
        # Index biomarqueurs
        for df in [self.rules_bio_base, self.rules_bio_extended, self.rules_bio_functional]:
            if not _df_ok(df):
                continue
            
            col = _col_find(df, ["Biomarqueur", "BIOMARQUEUR", "Marqueur", "Paramètre"])
            if not col:
                continue
            
            for idx, row in df.iterrows():
                raw_name = str(row.get(col, "")).strip()
                if not raw_name or raw_name.lower() == "nan":
                    continue
                
                normalized = normalize_biomarker_name(raw_name)
                if normalized:
                    # Index exact
                    self._bio_index[normalized] = row
                    # Index contains pour fuzzy matching
                    self._bio_contains_keys.append((normalized, row))
        
        # Index microbiome
        if _df_ok(self.rules_microbiome):
            col_group = _col_find(self.rules_microbiome, ["Groupe", "Group", "Bacteria_Group"])
            if col_group:
                for idx, row in self.rules_microbiome.iterrows():
                    group = str(row.get(col_group, "")).strip()
                    if group and group.lower() != "nan":
                        self._micro_rows.append(row)
        
        print(f"🔍 Index construit: {len(self._bio_index)} biomarqueurs indexés")
        print(f"🦠 Microbiome: {len(self._micro_rows)} groupes indexés")
    
    # ─────────────────────────────────────────────────────────────────
    # MATCHING BIOMARQUEURS
    # ─────────────────────────────────────────────────────────────────
    def _find_biomarker_rules(self, biomarker_name: str) -> Optional[pd.Series]:
        """Trouve les règles pour un biomarqueur (matching robuste)"""
        norm = normalize_biomarker_name(biomarker_name)
        
        # Exact match
        if norm in self._bio_index:
            return self._bio_index[norm]
        
        # Fuzzy contains (substring matching bidirectionnel)
        for key, row in self._bio_contains_keys:
            if norm in key or key in norm:
                return row
        
        return None
    
    def _find_microbiome_rules(self, group: str, severity: int = 0) -> Optional[pd.Series]:
        """Trouve les règles microbiome pour un groupe"""
        norm_group = group.upper().strip()
        
        col_group = _col_find(
            pd.DataFrame([r.to_dict() for r in self._micro_rows[:1]]) if self._micro_rows else pd.DataFrame(),
            ["Groupe", "Group", "Bacteria_Group"]
        )
        col_sev = _col_find(
            pd.DataFrame([r.to_dict() for r in self._micro_rows[:1]]) if self._micro_rows else pd.DataFrame(),
            ["Sévérité", "Severity", "Niveau"]
        )
        
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
    
    # ─────────────────────────────────────────────────────────────────
    # INTERPRÉTATION BIOMARQUEUR INDIVIDUEL
    # ─────────────────────────────────────────────────────────────────
    def interpret_biomarker(
        self,
        biomarker_name: str,
        value: Any,
        unit: str,
        reference: str,
        patient_info: Optional[Dict] = None
    ) -> BiomarkerInterpretation:
        """
        Interprète un biomarqueur individuel
        """
        status = determine_biomarker_status(value, reference, biomarker_name)
        rules = self._find_biomarker_rules(biomarker_name)
        
        # Priorité par défaut
        priority = "normal"
        if status in ["Bas", "Élevé"]:
            priority = "medium"
        
        # Biomarqueurs critiques (liste extensible)
        critical_markers = [
            "CRP", "FERRITINE", "HEMOGLOBINE", "GLYCEMIE", "HBA1C",
            "CREATININE", "DFG", "TSH", "LDL", "CHOLESTEROL"
        ]
        norm_name = normalize_biomarker_name(biomarker_name)
        if any(crit in norm_name for crit in critical_markers):
            if status in ["Bas", "Élevé"]:
                priority = "high"
        
        interpretation = BiomarkerInterpretation(
            biomarker=biomarker_name,
            value=value,
            unit=unit,
            reference=reference,
            status=status,
            priority=priority
        )
        
        if rules is None:
            return interpretation
        
        # Extraire recommandations selon le statut
        one = rules.to_frame().T
        
        low_interp = _col_find(one, ["BASSE - Interprétation", "BASSE Interprétation"])
        low_nutri = _col_find(one, ["BASSE - Nutrition", "BASSE Nutrition"])
        low_micro = _col_find(one, ["BASSE - Micronutrition", "BASSE Micronutrition"])
        low_life = _col_find(one, ["BASSE - Lifestyle", "BASSE Lifestyle"])
        
        high_interp = _col_find(one, ["HAUTE - Interprétation", "HAUTE Interprétation"])
        high_nutri = _col_find(one, ["HAUTE - Nutrition", "HAUTE Nutrition"])
        high_micro = _col_find(one, ["HAUTE - Micronutrition", "HAUTE Micronutrition"])
        high_life = _col_find(one, ["HAUTE - Lifestyle", "HAUTE Lifestyle"])
        
        if status == "Bas":
            interpretation.interpretation = _get_cell(rules, low_interp) or None
            interpretation.nutrition = _get_cell(rules, low_nutri) or None
            interpretation.micronutrition = _get_cell(rules, low_micro) or None
            interpretation.lifestyle = _get_cell(rules, low_life) or None
        elif status == "Élevé":
            interpretation.interpretation = _get_cell(rules, high_interp) or None
            interpretation.nutrition = _get_cell(rules, high_nutri) or None
            interpretation.micronutrition = _get_cell(rules, high_micro) or None
            interpretation.lifestyle = _get_cell(rules, high_life) or None
        
        return interpretation
    
    # ─────────────────────────────────────────────────────────────────
    # INTERPRÉTATION MICROBIOME
    # ─────────────────────────────────────────────────────────────────
    def interpret_microbiome_group(self, bacteria_data: Dict) -> Dict[str, Any]:
        """Interprète un groupe bactérien du microbiome"""
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
            "severity": severity,
            "interpretation": None,
            "nutrition": None,
            "supplementation": None,
            "lifestyle": None,
        }
        
        if severity == 0:
            out["interpretation"] = "Niveau optimal - Continuer les bonnes pratiques actuelles"
            return out
        
        rules = self._find_microbiome_rules(group, severity)
        if rules is None:
            out["interpretation"] = f"Déviation détectée ({result_status})"
            return out
        
        one = rules.to_frame().T
        col_i = _col_find(one, ["Interpretation_clinique", "Interprétation", "Interpretation"])
        col_n = _col_find(one, ["Recommandations_nutritionnelles", "Nutrition"])
        col_s = _col_find(one, ["Recommandations_supplementation", "Supplémentation"])
        col_l = _col_find(one, ["Recommandations_lifestyle", "Lifestyle"])
        
        out["interpretation"] = _get_cell(rules, col_i) or None
        out["nutrition"] = _get_cell(rules, col_n) or None
        out["supplementation"] = _get_cell(rules, col_s) or None
        out["lifestyle"] = _get_cell(rules, col_l) or None
        
        return out
    
    # ─────────────────────────────────────────────────────────────────
    # ANALYSES CROISÉES MULTIMODALES
    # ─────────────────────────────────────────────────────────────────
    def generate_cross_analysis(
        self,
        biology_data: pd.DataFrame,
        microbiome_data: Dict
    ) -> List[CrossAnalysisResult]:
        """
        Génère des observations croisées biologie + microbiome
        """
        results = []
        
        if not _df_ok(biology_data):
            return results
        
        def find_marker(marker: str) -> Optional[pd.Series]:
            m = biology_data[
                biology_data["Biomarqueur"].astype(str).str.contains(marker, case=False, na=False)
            ]
            if not _df_ok(m):
                return None
            return m.iloc[0]
        
        # ─────────────────────────────────────────────────────────────
        # 1. INFLAMMATION + DYSBIOSE
        # ─────────────────────────────────────────────────────────────
        crp = find_marker("CRP")
        di = (microbiome_data or {}).get("dysbiosis_index")
        
        if crp is not None and di is not None:
            crp_val = _safe_float(crp.get("Valeur"))
            if crp_val and crp_val > 3 and di >= 3:
                results.append(CrossAnalysisResult(
                    title="🔥 Axe Inflammation-Dysbiose",
                    description=f"CRP élevée ({crp_val} mg/L) associée à une dysbiose modérée (indice {di}/5). Lien établi entre inflammation systémique et déséquilibre du microbiote.",
                    severity="warning",
                    recommendations=[
                        "Réduire l'inflammation par l'alimentation anti-inflammatoire",
                        "Restaurer l'équilibre du microbiote avec prébiotiques et probiotiques ciblés",
                        "Éviter les aliments pro-inflammatoires (sucres raffinés, graisses trans)"
                    ]
                ))
        
        # ─────────────────────────────────────────────────────────────
        # 2. MÉTABOLISME GLUCIDIQUE + MICROBIOTE
        # ─────────────────────────────────────────────────────────────
        glycemie = find_marker("GLYCEMIE")
        hba1c = find_marker("HBA1C")
        
        if glycemie is not None or hba1c is not None:
            gly_val = _safe_float(glycemie.get("Valeur")) if glycemie is not None else None
            hba_val = _safe_float(hba1c.get("Valeur")) if hba1c is not None else None
            
            dysbiosis = di and di >= 3
            
            if (gly_val and gly_val > 1.0) or (hba_val and hba_val > 5.7):
                if dysbiosis:
                    results.append(CrossAnalysisResult(
                        title="🍬 Axe Glycémie-Microbiote",
                        description="Tendance pré-diabétique associée à une dysbiose. Le microbiote intestinal joue un rôle clé dans la régulation glycémique.",
                        severity="warning",
                        recommendations=[
                            "Optimiser le microbiote pour améliorer la sensibilité à l'insuline",
                            "Fibres prébiotiques (inuline, FOS) pour nourrir les bactéries bénéfiques",
                            "Limiter les glucides raffinés, privilégier index glycémique bas"
                        ]
                    ))
        
        # ─────────────────────────────────────────────────────────────
        # 3. STRESS OXYDATIF + MICROBIOTE
        # ─────────────────────────────────────────────────────────────
        ferritine = find_marker("FERRITINE")
        
        if ferritine is not None:
            ferr_val = _safe_float(ferritine.get("Valeur"))
            if ferr_val:
                if ferr_val < 30 and di and di >= 3:
                    results.append(CrossAnalysisResult(
                        title="⚡ Axe Ferritine-Microbiote",
                        description=f"Ferritine basse ({ferr_val} µg/L) + dysbiose. Le microbiote influence l'absorption du fer.",
                        severity="warning",
                        recommendations=[
                            "Restaurer la santé intestinale pour améliorer l'absorption du fer",
                            "Probiotiques lactobacilles pour optimiser l'assimilation",
                            "Sources de fer héminique (viandes) + vitamine C"
                        ]
                    ))
        
        # ─────────────────────────────────────────────────────────────
        # 4. DÉTECTION AUTOMATIQUE AUTRES PATTERNS
        # ─────────────────────────────────────────────────────────────
        # Cholestérol + Inflammation
        ldl = find_marker("LDL")
        if ldl is not None and crp is not None:
            ldl_val = _safe_float(ldl.get("Valeur"))
            crp_val = _safe_float(crp.get("Valeur"))
            if ldl_val and ldl_val > 1.3 and crp_val and crp_val > 3:
                results.append(CrossAnalysisResult(
                    title="💓 Axe Cardiovasculaire-Inflammation",
                    description=f"LDL élevé ({ldl_val} g/L) + inflammation (CRP {crp_val} mg/L). Risque cardiovasculaire accru.",
                    severity="warning",
                    recommendations=[
                        "Réduire LDL par alimentation riche en fibres et oméga-3",
                        "Anti-inflammatoires naturels (curcuma, gingembre)",
                        "Activité physique régulière (cardio modéré)"
                    ]
                ))
        
        return results
    
    # ─────────────────────────────────────────────────────────────────
    # GÉNÉRATION CONSOLIDÉE DES RECOMMANDATIONS
    # ─────────────────────────────────────────────────────────────────
    def generate_consolidated_recommendations(
        self,
        biology_data: Optional[pd.DataFrame] = None,
        microbiome_data: Optional[Dict] = None,
        patient_info: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Génère l'ensemble complet des recommandations consolidées
        
        Returns:
            {
                "recommendations": {
                    "Prioritaires": [...],
                    "À surveiller": [...],
                    "Nutrition": [...],
                    "Micronutrition": [...],
                    "Hygiène de vie": [...],
                    "Examens complémentaires": [...],
                    "Suivi": [...]
                },
                "biology_details": [...],  # Interprétations détaillées
                "microbiome_details": [...],
                "cross_analysis": [...],
                "summary": {
                    "anomalies_count": int,
                    "critical_count": int,
                    "dysbiosis_level": str,
                }
            }
        """
        reco_set = RecommendationSet()
        biology_details = []
        microbiome_details = []
        cross_analysis = []
        
        anomalies_count = 0
        critical_count = 0
        
        # ═════════════════════════════════════════════════════════════
        # 1. BIOLOGIE
        # ═════════════════════════════════════════════════════════════
        if _df_ok(biology_data):
            for _, row in biology_data.iterrows():
                biomarker_name = row.get("Biomarqueur", "")
                value = row.get("Valeur")
                unit = row.get("Unité", row.get("Unite", ""))
                reference = row.get("Référence", row.get("Reference", ""))
                
                interp = self.interpret_biomarker(
                    biomarker_name, value, unit, reference, patient_info
                )
                biology_details.append(interp)
                
                # Compteurs
                if interp.status in ["Bas", "Élevé"]:
                    anomalies_count += 1
                    if interp.priority == "high":
                        critical_count += 1
                
                # Catégorisation
                if interp.status in ["Bas", "Élevé"]:
                    # Prioritaires pour les critiques
                    if interp.priority in ["high", "critical"]:
                        msg = f"{biomarker_name}: {interp.status} ({value} {unit})"
                        if interp.interpretation:
                            msg += f" - {interp.interpretation[:100]}"
                        reco_set.prioritaires.append(msg)
                    else:
                        # À surveiller pour les autres anomalies
                        msg = f"{biomarker_name}: {interp.status} ({value} {unit})"
                        reco_set.a_surveiller.append(msg)
                
                # Nutrition
                if interp.nutrition:
                    items = _split_recommendations(interp.nutrition)
                    for item in items:
                        if item and item not in reco_set.nutrition:
                            reco_set.nutrition.append(item)
                
                # Micronutrition
                if interp.micronutrition:
                    items = _split_recommendations(interp.micronutrition)
                    for item in items:
                        if item and item not in reco_set.micronutrition:
                            reco_set.micronutrition.append(item)
                
                # Hygiène de vie
                if interp.lifestyle:
                    items = _split_recommendations(interp.lifestyle)
                    for item in items:
                        if item and item not in reco_set.hygiene_vie:
                            reco_set.hygiene_vie.append(item)
        
        # ═════════════════════════════════════════════════════════════
        # 2. MICROBIOME
        # ═════════════════════════════════════════════════════════════
        dysbiosis_level = "Aucune"
        
        if microbiome_data:
            di = microbiome_data.get("dysbiosis_index")
            if di:
                if di == 1:
                    dysbiosis_level = "Aucune (normobiose)"
                elif di <= 2:
                    dysbiosis_level = "Légère"
                elif di <= 3:
                    dysbiosis_level = "Modérée"
                else:
                    dysbiosis_level = "Sévère"
            
            # Interprétation groupes bactériens
            for bacteria in microbiome_data.get("bacteria", []):
                interp = self.interpret_microbiome_group(bacteria)
                microbiome_details.append(interp)
                
                # Si déviation, ajouter aux recommandations
                if interp.get("severity", 0) > 0:
                    group_name = bacteria.get("group", "")
                    category = bacteria.get("category", "")
                    
                    # Prioritaires si sévère
                    if interp.get("severity") >= 2:
                        msg = f"Microbiote {category}: {group_name} - Déviation importante"
                        if msg not in reco_set.prioritaires:
                            reco_set.prioritaires.append(msg)
                    else:
                        msg = f"Microbiote {category}: {group_name} - Légère déviation"
                        if msg not in reco_set.a_surveiller:
                            reco_set.a_surveiller.append(msg)
                    
                    # Nutrition microbiome
                    if interp.get("nutrition"):
                        items = _split_recommendations(interp["nutrition"])
                        for item in items:
                            if item and item not in reco_set.nutrition:
                                reco_set.nutrition.append(item)
                    
                    # Supplémentation microbiome
                    if interp.get("supplementation"):
                        items = _split_recommendations(interp["supplementation"])
                        for item in items:
                            if item and item not in reco_set.micronutrition:
                                reco_set.micronutrition.append(item)
                    
                    # Lifestyle microbiome
                    if interp.get("lifestyle"):
                        items = _split_recommendations(interp["lifestyle"])
                        for item in items:
                            if item and item not in reco_set.hygiene_vie:
                                reco_set.hygiene_vie.append(item)
        
        # ═════════════════════════════════════════════════════════════
        # 3. ANALYSES CROISÉES
        # ═════════════════════════════════════════════════════════════
        if biology_data is not None and microbiome_data is not None:
            cross_analysis = self.generate_cross_analysis(biology_data, microbiome_data)
            
            # Ajouter recommandations croisées
            for ca in cross_analysis:
                for reco in ca.recommendations:
                    if reco and reco not in reco_set.prioritaires:
                        if ca.severity == "critical":
                            reco_set.prioritaires.append(reco)
                        elif ca.severity == "warning" and reco not in reco_set.a_surveiller:
                            reco_set.a_surveiller.append(reco)
        
        # ═════════════════════════════════════════════════════════════
        # 4. EXAMENS COMPLÉMENTAIRES & SUIVI
        # ═════════════════════════════════════════════════════════════
        # Suggestions automatiques selon anomalies
        if anomalies_count > 3:
            reco_set.examens_complementaires.append(
                "Bilan de suivi recommandé dans 3 mois pour réévaluer les anomalies détectées"
            )
        
        if dysbiosis_level in ["Modérée", "Sévère"]:
            reco_set.examens_complementaires.append(
                "Envisager test métabolites microbiens (SCFA) pour évaluation approfondie"
            )
        
        # Suivi par défaut
        if critical_count > 0:
            reco_set.suivi.append(
                f"Contrôle prioritaire dans 1-2 mois : {critical_count} paramètre(s) critique(s) détecté(s)"
            )
        elif anomalies_count > 0:
            reco_set.suivi.append(
                f"Suivi dans 3 mois recommandé : {anomalies_count} paramètre(s) hors normes"
            )
        else:
            reco_set.suivi.append(
                "Profil biologique optimal - Suivi annuel de routine"
            )
        
        # ═════════════════════════════════════════════════════════════
        # RÉSULTAT FINAL
        # ═════════════════════════════════════════════════════════════
        return {
            "recommendations": reco_set.to_dict(),
            "biology_details": [
                {
                    "biomarker": b.biomarker,
                    "value": b.value,
                    "unit": b.unit,
                    "reference": b.reference,
                    "status": b.status,
                    "interpretation": b.interpretation,
                    "priority": b.priority
                }
                for b in biology_details
            ],
            "microbiome_details": microbiome_details,
            "cross_analysis": [
                {
                    "title": ca.title,
                    "description": ca.description,
                    "severity": ca.severity,
                    "recommendations": ca.recommendations
                }
                for ca in cross_analysis
            ],
            "summary": {
                "anomalies_count": anomalies_count,
                "critical_count": critical_count,
                "dysbiosis_level": dysbiosis_level,
                "total_recommendations": sum(len(v) for v in reco_set.to_dict().values())
            }
        }
    
    # ─────────────────────────────────────────────────────────────────
    # UTILITAIRES
    # ─────────────────────────────────────────────────────────────────
    def list_all_biomarkers(self) -> List[str]:
        """Liste tous les biomarqueurs disponibles dans les règles"""
        biomarkers = []
        
        for df in [self.rules_bio_base, self.rules_bio_extended, self.rules_bio_functional]:
            if not _df_ok(df):
                continue
            
            col = _col_find(df, ["Biomarqueur", "BIOMARQUEUR", "Marqueur"])
            if col:
                vals = df[col].dropna().astype(str).str.strip().tolist()
                biomarkers.extend(vals)
        
        return sorted(set(b for b in biomarkers if b and b.lower() != "nan"))
