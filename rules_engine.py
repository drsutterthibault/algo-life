"""
Moteur de règles pour générer des recommandations personnalisées
basées sur les résultats biologiques et microbiote
ALGO-LIFE - Rules Engine v2.0
"""

import pandas as pd
import numpy as np
import os
from typing import Dict, List, Optional, Union


# ─────────────────────────────────────────────
# Helpers externes (si extractors.py disponible)
# ─────────────────────────────────────────────

def normalize_biomarker_name(name: str) -> str:
    """Normalise le nom d'un biomarqueur pour la comparaison."""
    if not name:
        return ""
    return (
        str(name)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
        .replace("(", "")
        .replace(")", "")
        .replace("'", "")
        .replace("é", "e")
        .replace("è", "e")
        .replace("ê", "e")
        .replace("à", "a")
        .replace("â", "a")
        .replace("ù", "u")
        .replace("û", "u")
        .replace("î", "i")
        .replace("ô", "o")
        .replace("ç", "c")
    )


def determine_biomarker_status(value: float, low: float, high: float) -> str:
    """Détermine le statut d'un biomarqueur."""
    if value is None or low is None or high is None:
        return "UNKNOWN"
    if value < low:
        return "LOW"
    elif value > high:
        return "HIGH"
    else:
        return "NORMAL"


# ─────────────────────────────────────────────
# Classe principale RulesEngine
# ─────────────────────────────────────────────

class RulesEngine:
    """
    Moteur de règles pour l'analyse multimodale et la génération de recommandations.
    Charge les règles depuis un fichier Excel et les applique aux données patient.
    """

    def __init__(self, rules_excel_path: str):
        """
        Initialise le moteur de règles avec le fichier Excel des règles.

        Args:
            rules_excel_path: Chemin vers le fichier Excel contenant les règles
        """
        self.rules_excel_path = rules_excel_path
        self.rules_bio_base = None
        self.rules_bio_extended = None
        self.rules_bio_functional = None
        self.rules_microbiome = None
        self.rules_metabolites = None
        self.cross_rules = None

        self._load_rules()

    # ─────────────────────────────────────────
    # Chargement des règles
    # ─────────────────────────────────────────

    def _load_rules(self):
        """Charge toutes les feuilles de règles depuis le fichier Excel."""
        try:
            if not os.path.exists(self.rules_excel_path):
                raise FileNotFoundError(
                    f"Le fichier de règles '{self.rules_excel_path}' est introuvable."
                )

            print(f"📂 Chargement des règles depuis : {self.rules_excel_path}")
            print(f"📏 Taille : {os.path.getsize(self.rules_excel_path)} bytes")

            xl = pd.ExcelFile(self.rules_excel_path)
            available_sheets = xl.sheet_names
            print(f"📋 Feuilles disponibles : {available_sheets}")

            sheet_map = {
                "rules_bio_base":       ["Bio_Base", "Règles_Bio_Base", "bio_base"],
                "rules_bio_extended":   ["Bio_Extended", "Règles_Bio_Extended", "bio_extended"],
                "rules_bio_functional": ["Bio_Functional", "Règles_Bio_Fonctionnel", "bio_functional"],
                "rules_microbiome":     ["Microbiome", "Règles_Microbiome", "microbiome"],
                "rules_metabolites":    ["Metabolites", "Règles_Metabolites", "metabolites"],
                "cross_rules":          ["Cross_Rules", "Règles_Croisées", "cross_rules"],
            }

            for attr, candidates in sheet_map.items():
                for candidate in candidates:
                    if candidate in available_sheets:
                        df = pd.read_excel(self.rules_excel_path, sheet_name=candidate)
                        setattr(self, attr, df)
                        print(f"  ✅ {attr} chargé depuis '{candidate}' ({len(df)} règles)")
                        break
                else:
                    print(f"  ⚠️  Feuille non trouvée pour {attr} (cherché : {candidates})")

        except Exception as e:
            print(f"❌ Erreur lors du chargement des règles : {e}")
            raise

    # ─────────────────────────────────────────
    # Application des règles biologiques
    # ─────────────────────────────────────────

    def apply_bio_rules(self, bio_data: Dict) -> List[Dict]:
        """
        Applique les règles biologiques aux données patient.

        Args:
            bio_data: Dictionnaire {biomarqueur: valeur}

        Returns:
            Liste de recommandations déclenchées
        """
        recommendations = []

        for rules_df in [self.rules_bio_base, self.rules_bio_extended, self.rules_bio_functional]:
            if rules_df is None:
                continue

            for _, rule in rules_df.iterrows():
                try:
                    triggered = self._evaluate_bio_rule(rule, bio_data)
                    if triggered:
                        rec = self._build_recommendation(rule, "bio")
                        if rec:
                            recommendations.append(rec)
                except Exception as e:
                    print(f"⚠️ Erreur règle bio '{rule.get('RULE_ID', '?')}': {e}")

        return recommendations

    def _evaluate_bio_rule(self, rule: pd.Series, bio_data: Dict) -> bool:
        """Évalue si une règle biologique est déclenchée."""
        biomarker_col = self._find_column(rule, ["BIOMARKER", "BIOMARQUEUR", "MARQUEUR", "PARAMETER"])
        condition_col = self._find_column(rule, ["CONDITION", "OPERATOR", "OPERATEUR"])
        threshold_col = self._find_column(rule, ["THRESHOLD", "SEUIL", "VALUE", "VALEUR"])

        if not biomarker_col:
            return False

        biomarker = normalize_biomarker_name(str(rule.get(biomarker_col, "")))
        if not biomarker:
            return False

        # Chercher la valeur dans bio_data
        value = None
        for key, val in bio_data.items():
            if normalize_biomarker_name(str(key)) == biomarker:
                value = val
                break

        if value is None:
            return False

        try:
            value = float(value)
        except (ValueError, TypeError):
            return False

        condition = str(rule.get(condition_col, "")) if condition_col else ""
        threshold_raw = rule.get(threshold_col, None) if threshold_col else None

        if threshold_raw is None:
            return False

        try:
            threshold = float(threshold_raw)
        except (ValueError, TypeError):
            return False

        return self._compare(value, condition, threshold)

    # ─────────────────────────────────────────
    # Application des règles microbiome
    # ─────────────────────────────────────────

    def apply_microbiome_rules(self, microbiome_data: Dict) -> List[Dict]:
        """
        Applique les règles microbiome aux données patient.

        Args:
            microbiome_data: Dictionnaire {bactérie: valeur_relative}

        Returns:
            Liste de recommandations déclenchées
        """
        recommendations = []

        if self.rules_microbiome is None:
            return recommendations

        for _, rule in self.rules_microbiome.iterrows():
            try:
                triggered = self._evaluate_microbiome_rule(rule, microbiome_data)
                if triggered:
                    rec = self._build_recommendation(rule, "microbiome")
                    if rec:
                        recommendations.append(rec)
            except Exception as e:
                print(f"⚠️ Erreur règle microbiome '{rule.get('RULE_ID', '?')}': {e}")

        return recommendations

    def _evaluate_microbiome_rule(self, rule: pd.Series, microbiome_data: Dict) -> bool:
        """Évalue si une règle microbiome est déclenchée."""
        bacteria_col = self._find_column(rule, ["BACTERIA", "BACTERIE", "BIOMARKER", "MARQUEUR"])
        condition_col = self._find_column(rule, ["CONDITION", "OPERATOR"])
        threshold_col = self._find_column(rule, ["THRESHOLD", "SEUIL", "VALUE"])

        if not bacteria_col:
            return False

        bacteria = normalize_biomarker_name(str(rule.get(bacteria_col, "")))
        if not bacteria:
            return False

        value = None
        for key, val in microbiome_data.items():
            if normalize_biomarker_name(str(key)) == bacteria:
                value = val
                break

        if value is None:
            return False

        try:
            value = float(value)
        except (ValueError, TypeError):
            return False

        condition = str(rule.get(condition_col, "")) if condition_col else ""
        threshold_raw = rule.get(threshold_col, None) if threshold_col else None

        if threshold_raw is None:
            return False

        try:
            threshold = float(threshold_raw)
        except (ValueError, TypeError):
            return False

        return self._compare(value, condition, threshold)

    # ─────────────────────────────────────────
    # Règles croisées (bio + microbiome)
    # ─────────────────────────────────────────

    def apply_cross_rules(
        self,
        bio_data: Dict,
        microbiome_data: Optional[Dict] = None,
        epigenetic_data: Optional[Dict] = None,
    ) -> List[Dict]:
        """
        Applique les règles croisées multi-modales.

        Args:
            bio_data: Données biologiques
            microbiome_data: Données microbiome (optionnel)
            epigenetic_data: Données épigénétiques (optionnel)

        Returns:
            Liste de recommandations croisées
        """
        recommendations = []

        if self.cross_rules is None:
            return recommendations

        for _, rule in self.cross_rules.iterrows():
            try:
                bio_ok = self._evaluate_bio_rule(rule, bio_data)
                micro_ok = True
                epi_ok = True

                if microbiome_data:
                    micro_col = self._find_column(rule, ["MICRO_CONDITION", "MICROBIOME_CONDITION"])
                    if micro_col and pd.notna(rule.get(micro_col, None)):
                        micro_ok = self._evaluate_microbiome_rule(rule, microbiome_data)

                if epigenetic_data:
                    epi_col = self._find_column(rule, ["EPI_CONDITION", "EPIGENETIC_CONDITION"])
                    if epi_col and pd.notna(rule.get(epi_col, None)):
                        epi_ok = self._evaluate_bio_rule(rule, epigenetic_data)

                if bio_ok and micro_ok and epi_ok:
                    rec = self._build_recommendation(rule, "cross")
                    if rec:
                        recommendations.append(rec)

            except Exception as e:
                print(f"⚠️ Erreur règle croisée '{rule.get('RULE_ID', '?')}': {e}")

        return recommendations

    # ─────────────────────────────────────────
    # Construction des recommandations
    # ─────────────────────────────────────────

    def _build_recommendation(self, rule: pd.Series, rule_type: str) -> Optional[Dict]:
        """Construit un dictionnaire de recommandation depuis une règle."""
        try:
            rec = {
                "rule_id": str(rule.get("RULE_ID", "N/A")),
                "rule_type": rule_type,
                "priority": self._get_priority(rule),
                "title": self._get_value(rule, ["TITLE", "TITRE", "RULE_NAME", "NOM_REGLE"], "Recommandation"),
                "category": self._get_value(rule, ["CATEGORY", "CATEGORIE", "AXE"], "Général"),
                "description": self._get_value(rule, ["DESCRIPTION", "EXPLICATION"], ""),
                "recommendations": {
                    "nutrition": self._get_value(rule, ["NUTRITION", "RECO_NUTRITION"], ""),
                    "supplementation": self._get_value(rule, ["SUPPLEMENTATION", "RECO_SUPPLEMENT", "RECO_MICRO"], ""),
                    "lifestyle": self._get_value(rule, ["LIFESTYLE", "MODE_VIE", "RECO_LIFESTYLE"], ""),
                    "monitoring": self._get_value(rule, ["MONITORING", "SUIVI"], ""),
                },
                "expected_impact": self._get_value(rule, ["EXPECTED_IMPACT", "IMPACT_ATTENDU", "OBJECTIF"], ""),
                "evidence_level": self._get_value(rule, ["EVIDENCE_LEVEL", "NIVEAU_PREUVE"], "B"),
            }
            return rec
        except Exception as e:
            print(f"⚠️ Impossible de construire la recommandation : {e}")
            return None

    # ─────────────────────────────────────────
    # Point d'entrée principal
    # ─────────────────────────────────────────

    def generate_recommendations(
        self,
        bio_data: Dict,
        microbiome_data: Optional[Dict] = None,
        epigenetic_data: Optional[Dict] = None,
        dxa_data: Optional[Dict] = None,
    ) -> Dict:
        """
        Point d'entrée principal : génère toutes les recommandations.

        Args:
            bio_data: Données biologiques {marqueur: valeur}
            microbiome_data: Données microbiome (optionnel)
            epigenetic_data: Données épigénétiques (optionnel)
            dxa_data: Données DXA composition corporelle (optionnel)

        Returns:
            Dictionnaire structuré avec toutes les recommandations
        """
        all_recommendations = []

        # 1. Règles biologiques
        bio_recs = self.apply_bio_rules(bio_data)
        all_recommendations.extend(bio_recs)

        # 2. Règles microbiome
        if microbiome_data:
            micro_recs = self.apply_microbiome_rules(microbiome_data)
            all_recommendations.extend(micro_recs)

        # 3. Règles croisées
        cross_recs = self.apply_cross_rules(bio_data, microbiome_data, epigenetic_data)
        all_recommendations.extend(cross_recs)

        # 4. Déduplication et tri par priorité
        all_recommendations = self._deduplicate(all_recommendations)
        all_recommendations = sorted(
            all_recommendations,
            key=lambda x: {"HIGH": 0, "MEDIUM": 1, "LOW": 2}.get(x.get("priority", "LOW"), 2),
        )

        # 5. Regroupement par catégorie
        by_category = {}
        for rec in all_recommendations:
            cat = rec.get("category", "Général")
            by_category.setdefault(cat, []).append(rec)

        return {
            "total": len(all_recommendations),
            "by_priority": {
                "high": [r for r in all_recommendations if r.get("priority") == "HIGH"],
                "medium": [r for r in all_recommendations if r.get("priority") == "MEDIUM"],
                "low": [r for r in all_recommendations if r.get("priority") == "LOW"],
            },
            "by_category": by_category,
            "all": all_recommendations,
            "summary": self._generate_summary(all_recommendations),
        }

    # ─────────────────────────────────────────
    # Utilitaires internes
    # ─────────────────────────────────────────

    def _compare(self, value: float, condition: str, threshold: float) -> bool:
        """Compare une valeur à un seuil selon l'opérateur."""
        cond = condition.strip().lower()
        ops = {
            "<": value < threshold,
            "<=": value <= threshold,
            ">": value > threshold,
            ">=": value >= threshold,
            "=": value == threshold,
            "==": value == threshold,
            "low": value < threshold,
            "high": value > threshold,
            "bas": value < threshold,
            "eleve": value > threshold,
            "élevé": value > threshold,
        }
        return ops.get(cond, False)

    def _find_column(self, row: pd.Series, candidates: List[str]) -> Optional[str]:
        """Trouve le premier nom de colonne disponible parmi les candidats."""
        for col in candidates:
            if col in row.index and pd.notna(row.get(col)):
                return col
        return None

    def _get_value(self, row: pd.Series, candidates: List[str], default: str = "") -> str:
        """Récupère la valeur d'une colonne parmi les candidats."""
        for col in candidates:
            if col in row.index:
                val = row.get(col)
                if pd.notna(val) and str(val).strip():
                    return str(val).strip()
        return default

    def _get_priority(self, row: pd.Series) -> str:
        """Détermine la priorité d'une règle."""
        raw = self._get_value(row, ["PRIORITY", "PRIORITE", "URGENCE"], "MEDIUM")
        mapping = {
            "high": "HIGH", "haute": "HIGH", "1": "HIGH",
            "medium": "MEDIUM", "moyenne": "MEDIUM", "2": "MEDIUM",
            "low": "LOW", "basse": "LOW", "3": "LOW",
        }
        return mapping.get(raw.lower(), "MEDIUM")

    def _deduplicate(self, recommendations: List[Dict]) -> List[Dict]:
        """Supprime les doublons basés sur rule_id."""
        seen = set()
        unique = []
        for rec in recommendations:
            rid = rec.get("rule_id", "")
            if rid not in seen:
                seen.add(rid)
                unique.append(rec)
        return unique

    def _generate_summary(self, recommendations: List[Dict]) -> str:
        """Génère un résumé textuel des recommandations."""
        high = sum(1 for r in recommendations if r.get("priority") == "HIGH")
        medium = sum(1 for r in recommendations if r.get("priority") == "MEDIUM")
        low = sum(1 for r in recommendations if r.get("priority") == "LOW")

        summary_parts = []
        if high:
            summary_parts.append(f"{high} priorité haute")
        if medium:
            summary_parts.append(f"{medium} priorité moyenne")
        if low:
            summary_parts.append(f"{low} priorité faible")

        total = len(recommendations)
        if total == 0:
            return "Aucune anomalie détectée. Profil dans les normes."

        return (
            f"{total} recommandation(s) générée(s) : "
            + ", ".join(summary_parts)
            + "."
        )

    # ─────────────────────────────────────────
    # Consolidated (alias enrichi pour app.py)
    # ─────────────────────────────────────────

    def generate_consolidated_recommendations(
        self,
        bio_data: Dict,
        microbiome_data: Optional[Dict] = None,
        epigenetic_data: Optional[Dict] = None,
        dxa_data: Optional[Dict] = None,
        patient_info: Optional[Dict] = None,
    ) -> Dict:
        """
        Génère des recommandations consolidées multi-modales.
        Alias enrichi de generate_recommendations, compatible avec app.py.

        Args:
            bio_data: Données biologiques {marqueur: valeur}
            microbiome_data: Données microbiome (optionnel)
            epigenetic_data: Données épigénétiques (optionnel)
            dxa_data: Données DXA composition corporelle (optionnel)
            patient_info: Informations patient (âge, sexe, etc.) (optionnel)

        Returns:
            Dictionnaire consolidé avec recommandations structurées
        """
        # Générer les recommandations de base
        base_results = self.generate_recommendations(
            bio_data=bio_data,
            microbiome_data=microbiome_data,
            epigenetic_data=epigenetic_data,
            dxa_data=dxa_data,
        )

        # Enrichissement avec métadonnées patient
        patient_info = patient_info or {}

        # Construire les axes thérapeutiques consolidés
        axes = self._build_therapeutic_axes(base_results["all"])

        # Score global de santé (0-100)
        health_score = self._compute_health_score(base_results)

        consolidated = {
            # ── Données brutes ──────────────────────────────
            "total": base_results["total"],
            "all": base_results["all"],
            "by_priority": base_results["by_priority"],
            "by_category": base_results["by_category"],
            "summary": base_results["summary"],

            # ── Enrichissements consolidés ──────────────────
            "health_score": health_score,
            "axes": axes,
            "patient_info": patient_info,

            # ── Recommandations par domaine ─────────────────
            "nutrition_recommendations": self._extract_domain(base_results["all"], "nutrition"),
            "supplementation_recommendations": self._extract_domain(base_results["all"], "supplementation"),
            "lifestyle_recommendations": self._extract_domain(base_results["all"], "lifestyle"),
            "monitoring_recommendations": self._extract_domain(base_results["all"], "monitoring"),

            # ── Sources de données utilisées ────────────────
            "data_sources": {
                "biology": bio_data is not None and len(bio_data) > 0,
                "microbiome": microbiome_data is not None and len(microbiome_data) > 0,
                "epigenetics": epigenetic_data is not None and len(epigenetic_data) > 0,
                "dxa": dxa_data is not None and len(dxa_data) > 0,
            },

            # ── Alertes prioritaires ─────────────────────────
            "alerts": [
                r for r in base_results["all"]
                if r.get("priority") == "HIGH"
            ],
        }

        return consolidated

    def _build_therapeutic_axes(self, recommendations: List[Dict]) -> Dict:
        """Regroupe les recommandations par axe thérapeutique."""
        axes = {
            "metabolisme": [],
            "inflammation": [],
            "hormones": [],
            "micronutrition": [],
            "microbiome": [],
            "epigenetique": [],
            "cardiovasculaire": [],
            "autre": [],
        }

        axis_keywords = {
            "metabolisme":    ["métabol", "metabol", "glyc", "insuline", "glucose", "lipide"],
            "inflammation":   ["inflamm", "crp", "cytokine", "oxydatif", "oxidat"],
            "hormones":       ["hormone", "thyroid", "cortisol", "testosteron", "oestrog", "estrog", "dhea"],
            "micronutrition": ["vitamine", "vitamin", "mineral", "magnesium", "zinc", "fer", "omega"],
            "microbiome":     ["microbiome", "bacterie", "bactérie", "probiot", "prebiot", "intestin"],
            "epigenetique":   ["epigenet", "methylat", "age biolog"],
            "cardiovasculaire": ["cardio", "cardiovasc", "tension", "cholesterol", "triglyc"],
        }

        for rec in recommendations:
            cat = (rec.get("category", "") + " " + rec.get("title", "")).lower()
            placed = False
            for axis, keywords in axis_keywords.items():
                if any(kw in cat for kw in keywords):
                    axes[axis].append(rec)
                    placed = True
                    break
            if not placed:
                axes["autre"].append(rec)

        # Supprimer les axes vides
        return {k: v for k, v in axes.items() if v}

    def _compute_health_score(self, results: Dict) -> int:
        """Calcule un score de santé global (0-100, 100 = optimal)."""
        total = results.get("total", 0)
        if total == 0:
            return 95

        high   = len(results["by_priority"].get("high", []))
        medium = len(results["by_priority"].get("medium", []))
        low    = len(results["by_priority"].get("low", []))

        # Pénalités : HIGH -8pts, MEDIUM -3pts, LOW -1pt
        penalty = (high * 8) + (medium * 3) + (low * 1)
        score = max(0, min(100, 100 - penalty))
        return score

    def _extract_domain(self, recommendations: List[Dict], domain: str) -> List[str]:
        """Extrait les recommandations d'un domaine spécifique (nutrition, etc.)."""
        extracted = []
        for rec in recommendations:
            recs = rec.get("recommendations", {})
            value = recs.get(domain, "")
            if value and str(value).strip():
                extracted.append({
                    "rule_id": rec.get("rule_id"),
                    "priority": rec.get("priority"),
                    "title": rec.get("title"),
                    "text": str(value).strip(),
                })
        return extracted

    # ─────────────────────────────────────────
    # Infos & debug
    # ─────────────────────────────────────────

    def get_rules_summary(self) -> Dict:
        """Retourne un résumé des règles chargées."""
        return {
            "bio_base": len(self.rules_bio_base) if self.rules_bio_base is not None else 0,
            "bio_extended": len(self.rules_bio_extended) if self.rules_bio_extended is not None else 0,
            "bio_functional": len(self.rules_bio_functional) if self.rules_bio_functional is not None else 0,
            "microbiome": len(self.rules_microbiome) if self.rules_microbiome is not None else 0,
            "metabolites": len(self.rules_metabolites) if self.rules_metabolites is not None else 0,
            "cross_rules": len(self.cross_rules) if self.cross_rules is not None else 0,
        }

    def __repr__(self):
        summary = self.get_rules_summary()
        total = sum(summary.values())
        return f"<RulesEngine | {total} règles chargées | {self.rules_excel_path}>"
