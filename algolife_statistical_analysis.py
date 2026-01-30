"""
ALGO-LIFE - Module d'Analyse Statistique & Rapports
Auteur: Thibault - Product Manager Functional Biology
Version: 3.0 (refactor robuste & testable)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, List, Tuple, Iterable

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from scipy import stats
from datetime import datetime
from io import BytesIO
import logging


# ============================================================
# Logging
# ============================================================

logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)


# ============================================================
# Helpers
# ============================================================

Number = float | int


def to_float(x: Any) -> Optional[float]:
    """Convertit en float si possible, sinon None. (Attention: bool)"""
    if x is None or isinstance(x, bool):
        return None
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def mean_or_none(values: Iterable[Optional[float]]) -> Optional[float]:
    vals = [v for v in values if isinstance(v, (int, float))]
    return round(float(np.mean(vals)), 1) if vals else None


def now_str() -> str:
    return datetime.now().strftime("%d/%m/%Y %H:%M")


def safe_get(d: Dict[str, Any], key: str) -> Optional[float]:
    """Récupère un marqueur simple (flat dict) en float."""
    return to_float(d.get(key))


def score_linear(value: Optional[float], low: float, high: float, reverse: bool = False) -> Optional[float]:
    """
    Normalise une valeur vers un score 0-100 (linéaire) entre [low, high].
    reverse=True inverse le sens (plus haut = pire).
    """
    v = to_float(value)
    if v is None or high == low:
        return None
    ratio = (v - low) / (high - low)
    ratio = clamp(ratio, 0.0, 1.0)
    if reverse:
        ratio = 1.0 - ratio
    return round(ratio * 100.0, 1)


# ============================================================
# Config (seuils, recommandations)
# ============================================================

@dataclass(frozen=True)
class Rule:
    """Règle simple basée sur un score ou une valeur."""
    key: str
    condition: str
    message: str
    priority: int = 2


@dataclass
class ModelResult:
    success: bool
    r2_score: float = 0.0
    prediction: Optional[float] = None
    n_features: int = 0
    feature_importance: Dict[str, float] = field(default_factory=dict)
    correlations: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    coefficients: Optional[pd.DataFrame] = None
    message: Optional[str] = None


# ============================================================
# Main Class
# ============================================================

class AlgoLifeStatisticalAnalysis:
    """
    Analyse statistique (indices composites) + modélisation (optionnelle) + visualisation.
    - 'biological_markers' = dict flat pour certains modules (cortisol_22h, dopamine, etc.)
    - 'bio_data' = dict structuré (metabolisme_glucidique, lipides, etc.) pour metabolism_index
    """

    def __init__(self, patient_data: Dict[str, Any]):
        self.patient_data = patient_data or {}

        self.biological_markers: Dict[str, Any] = self.patient_data.get("biological_markers", {}) or {}
        self.epigenetic_data: Dict[str, Any] = self.patient_data.get("epigenetic_data", {}) or {}
        self.lifestyle_scores: Dict[str, Any] = self.patient_data.get("lifestyle_scores", {}) or {}
        self.patient_info: Dict[str, Any] = self.patient_data.get("patient_info", {}) or {}

        self.composite_indices: Dict[str, float] = {}
        self.statistical_model: Dict[str, Any] = {}
        self.predictions: Dict[str, Dict[str, Any]] = {}

    # ============================================================
    # 1) Indice métabolique (à partir de bio_data structuré)
    # ============================================================

    def calculate_metabolism_index(self, bio_data: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(bio_data, dict) or not bio_data:
            return {"score": None, "interpretation": "Données insuffisantes", "details": {}, "risk_level": "–"}

        details: Dict[str, Dict[str, Any]] = {}
        scores: List[Optional[float]] = []

        # HOMA
        homa = to_float(((bio_data.get("metabolisme_glucidique") or {}).get("homa")))
        homa_score = score_linear(homa, low=1.0, high=4.0, reverse=True)
        if homa_score is not None:
            scores.append(homa_score)
            details["homa"] = {
                "value": homa,
                "score": homa_score,
                "status": "Optimal" if homa is not None and homa < 2.0 else "Résistance insulinique",
            }

        # TG
        tg = to_float(((bio_data.get("lipides") or {}).get("triglycerides")))
        tg_score = score_linear(tg, low=50.0, high=200.0, reverse=True)
        if tg_score is not None:
            scores.append(tg_score)
            details["triglycerides"] = {
                "value": tg,
                "score": tg_score,
                "status": "Optimal" if tg is not None and tg < 150 else "Élevé",
            }

        # HDL (score direct)
        hdl = to_float(((bio_data.get("lipides") or {}).get("hdl")))
        # Score 0 à 100 entre 30 et 80 (cap)
        hdl_score = score_linear(hdl, low=30.0, high=80.0, reverse=False)
        if hdl_score is not None:
            scores.append(hdl_score)
            details["hdl"] = {
                "value": hdl,
                "score": hdl_score,
                "status": "Optimal" if hdl is not None and hdl > 50 else "Bas",
            }

        # Glycémie à jeun (70->100 ok, >110 moins bon)
        gly = to_float(((bio_data.get("metabolisme_glucidique") or {}).get("glycemie")))
        gly_score = score_linear(gly, low=70.0, high=120.0, reverse=True)
        if gly_score is not None:
            scores.append(gly_score)
            details["glycemie"] = {
                "value": gly,
                "score": gly_score,
                "status": "Optimal" if gly is not None and gly < 100 else "Élevée",
            }

        # Insuline
        ins = to_float(((bio_data.get("metabolisme_glucidique") or {}).get("insuline")))
        ins_score = score_linear(ins, low=2.0, high=20.0, reverse=True)
        if ins_score is not None:
            scores.append(ins_score)
            details["insuline"] = {
                "value": ins,
                "score": ins_score,
                "status": "Optimal" if ins is not None and ins < 10 else "Élevée",
            }

        score = mean_or_none(scores)
        if score is None:
            return {"score": None, "interpretation": "Données insuffisantes", "details": details, "risk_level": "–"}

        self.composite_indices["metabolism_index"] = score

        return {
            "score": score,
            "interpretation": self._interpret_metabolism(score),
            "details": details,
            "risk_level": self._risk_band(score, good_high=True),
        }

    def _interpret_metabolism(self, score: float) -> str:
        if score >= 80:
            return "Métabolisme optimal"
        if score >= 60:
            return "Métabolisme correct"
        if score >= 40:
            return "Dysrégulation métabolique modérée"
        if score >= 20:
            return "Dysrégulation métabolique importante"
        return "Syndrome métabolique"

    # ============================================================
    # 2) Stress index (flat markers)
    # ============================================================

    def calculate_stress_index(self) -> Dict[str, Any]:
        # On traite None vs 0 correctement
        cortisol_car = safe_get(self.biological_markers, "cortisol_car_30")
        if cortisol_car is None:
            cortisol_car = safe_get(self.biological_markers, "cortisol_car+30")

        cortisol_22h = safe_get(self.biological_markers, "cortisol_22h")
        dhea = safe_get(self.biological_markers, "dhea")
        cortisol_reveil = safe_get(self.biological_markers, "cortisol_reveil")

        # si aucune donnée, on sort
        if all(v is None for v in [cortisol_car, cortisol_22h, dhea, cortisol_reveil]):
            return {"score": None, "interpretation": "Données insuffisantes", "phase": "Indéterminé"}

        score = 0.0

        # règles simples (documentées)
        if cortisol_car is not None and cortisol_car < 7.5:
            score += 40
        if cortisol_22h is not None and cortisol_22h < 0.3:
            score += 30
        if dhea is not None and dhea > 1.5:
            score -= 10
        if cortisol_reveil is not None and cortisol_reveil > 17:
            score += 20

        score = clamp(score, 0.0, 100.0)
        score = round(score, 1)

        self.composite_indices["stress_index"] = score

        return {
            "score": score,
            "interpretation": self._interpret_stress(score),
            "phase": self._stress_phase(cortisol_car, cortisol_22h, dhea),
        }

    def _interpret_stress(self, score: float) -> str:
        if score < 20:
            return "Adaptation normale au stress"
        if score < 40:
            return "Stress modéré gérable"
        if score < 60:
            return "Épuisement surrénalien débutant"
        if score < 80:
            return "Épuisement surrénalien modéré"
        return "Épuisement surrénalien sévère"

    def _stress_phase(self, car: Optional[float], cortisol_22h: Optional[float], dhea: Optional[float]) -> str:
        if car is None or dhea is None:
            return "Phase indéterminée"
        if car > 7.5 and dhea > 1.5:
            return "Phase 1: Alarme (hyperactivation)"
        if car < 7.5 and dhea > 1.5:
            return "Phase 2: Résistance (épuisement débutant)"
        if car < 7.5 and dhea < 1.0:
            return "Phase 3: Épuisement (burnout)"
        return "Phase intermédiaire"

    # ============================================================
    # 3) Metabolic health score (flat markers)
    # ============================================================

    def calculate_metabolic_health_score(self) -> Dict[str, Any]:
        homa = safe_get(self.biological_markers, "homa_index")
        quicki = safe_get(self.biological_markers, "quicki_index")
        crp = safe_get(self.biological_markers, "crp")
        vit_d = safe_get(self.biological_markers, "vit_d")
        gly = safe_get(self.biological_markers, "glycemie")

        if all(v is None for v in [homa, quicki, crp, vit_d, gly]):
            return {"score": None, "interpretation": "Données insuffisantes", "issues": [], "risk_level": "–"}

        score = 100.0
        issues: List[str] = []

        # HOMA
        if homa is not None and homa > 2.4:
            penalty = min(30.0, (homa - 2.4) * 10.0)
            score -= penalty
            issues.append(f"Résistance insulinique (HOMA: {homa:.2f})")

        # QUICKI
        if quicki is not None and quicki < 0.34:
            score -= 20.0
            issues.append(f"Sensibilité insulinique diminuée (QUICKI: {quicki:.2f})")

        # CRP
        if crp is not None and crp > 1.0:
            penalty = min(25.0, (crp - 1.0) * 8.0)
            score -= penalty
            issues.append(f"Inflammation systémique (CRP: {crp:.2f} mg/L)")

        # Vit D (nmol/L)
        if vit_d is not None and vit_d < 75:
            penalty = min(15.0, (75.0 - vit_d) / 5.0)
            score -= penalty
            if vit_d < 30:
                issues.append(f"Carence vitamine D sévère ({vit_d:.1f} nmol/L)")
            elif vit_d < 50:
                issues.append(f"Insuffisance vitamine D ({vit_d:.1f} nmol/L)")

        # Gly
        if gly is not None and gly > 100:
            score -= 10.0
            if gly > 110:
                issues.append(f"Hyperglycémie modérée ({gly:.1f} mg/dL)")

        score = round(clamp(score, 0.0, 100.0), 1)
        self.composite_indices["metabolic_score"] = score

        return {
            "score": score,
            "interpretation": self._interpret_metabolic(score),
            "issues": issues,
            "risk_level": self._risk_band(score, good_high=True),
        }

    def _interpret_metabolic(self, score: float) -> str:
        if score >= 80:
            return "Santé métabolique optimale"
        if score >= 60:
            return "Santé métabolique correcte"
        if score >= 40:
            return "Dysrégulation métabolique modérée"
        if score >= 20:
            return "Dysrégulation métabolique importante"
        return "Syndrome métabolique établi"

    # ============================================================
    # 4) Neurotransmetteurs (flat markers)
    # ============================================================

    def calculate_neurotransmitter_balance(self) -> Dict[str, Any]:
        # valeurs attendues (existant dans ton code)
        dopamine = safe_get(self.biological_markers, "dopamine")
        serotonine = safe_get(self.biological_markers, "serotonine")
        noradrenaline = safe_get(self.biological_markers, "noradrenaline")
        adrenaline = safe_get(self.biological_markers, "adrenaline")

        # si aucune donnée
        if all(v is None for v in [dopamine, serotonine, noradrenaline, adrenaline]):
            return {"score": None, "interpretation": "Données insuffisantes", "details": {}, "recommendation": ""}

        details: Dict[str, Dict[str, Any]] = {}
        scores: List[Optional[float]] = []

        def add(name: str, value: Optional[float], low: float, high: float):
            s = score_linear(value, low=low, high=high, reverse=False)
            if s is None:
                return
            details[name] = {
                "value": value,
                "score": s,
                "status": "Optimal" if 40 <= s <= 70 else "Déséquilibré",
            }
            scores.append(s)

        # plages “référence” (celles de ton code)
        add("dopamine", dopamine, 108, 244)
        add("serotonine", serotonine, 38, 89)
        add("noradrenaline", noradrenaline, 11.1, 28)
        # adrenaline (si tu veux, mets une plage; sinon ignore)
        # add("adrenaline", adrenaline, X, Y)

        balance = mean_or_none(scores)
        if balance is None:
            return {"score": None, "interpretation": "Données insuffisantes", "details": details, "recommendation": ""}

        self.composite_indices["neuro_balance"] = balance

        return {
            "score": balance,
            "interpretation": self._interpret_neuro(balance),
            "details": details,
            "recommendation": self._neuro_reco(details),
        }

    def _interpret_neuro(self, score: float) -> str:
        if score >= 70:
            return "Équilibre neurotransmetteur optimal"
        if score >= 50:
            return "Équilibre neurotransmetteur correct"
        if score >= 30:
            return "Déséquilibre neurotransmetteur modéré"
        return "Déséquilibre neurotransmetteur important"

    def _neuro_reco(self, details: Dict[str, Dict[str, Any]]) -> str:
        recos: List[str] = []
        for neuro, data in details.items():
            s = data.get("score")
            if not isinstance(s, (int, float)):
                continue
            if s < 40:
                if neuro == "dopamine":
                    recos.append("Stimuler dopamine: L-tyrosine, exercice, objectifs")
                elif neuro == "serotonine":
                    recos.append("Stimuler sérotonine: 5-HTP, lumière, rythmes")
                elif neuro == "noradrenaline":
                    recos.append("Moduler noradrénaline: adaptogènes, respiration")
            elif s > 70:
                if neuro == "dopamine":
                    recos.append("Réguler dopamine: réduire stimulants")
                elif neuro == "noradrenaline":
                    recos.append("Réguler noradrénaline: relaxation, magnésium")
        return " | ".join(recos) if recos else "Équilibre optimal maintenu"

    # ============================================================
    # 5) Inflammation index (flat markers)
    # ============================================================

    def calculate_inflammation_index(self) -> Dict[str, Any]:
        crp = safe_get(self.biological_markers, "crp")
        lbp = safe_get(self.biological_markers, "lbp")
        zonuline = safe_get(self.biological_markers, "zonuline")
        homocysteine = safe_get(self.biological_markers, "homocysteine")

        if all(v is None for v in [crp, lbp, zonuline, homocysteine]):
            return {"score": None, "interpretation": "Données insuffisantes", "sources": [], "priority": "–"}

        score = 0.0
        sources: List[str] = []

        if crp is not None and crp > 1.0:
            score += min(40.0, (crp / 5.0) * 40.0)
            sources.append(f"CRP: {crp:.2f} mg/L (inflammation systémique)")

        if lbp is not None and lbp > 13.1:
            score += min(30.0, ((lbp - 13.1) / 13.1) * 30.0)
            sources.append(f"LBP: {lbp:.2f} ng/mL (endotoxémie)")

        if zonuline is not None and zonuline > 37:
            score += min(30.0, ((zonuline - 37) / 37) * 30.0)
            sources.append(f"Zonuline: {zonuline:.2f} ng/mL (perméabilité)")

        if homocysteine is not None and homocysteine > 12:
            score += 15.0
            sources.append(f"Homocystéine: {homocysteine:.2f} µmol/L (vasculaire)")

        score = round(clamp(score, 0.0, 100.0), 1)
        self.composite_indices["inflammation_index"] = score

        return {
            "score": score,
            "interpretation": self._interpret_inflammation(score),
            "sources": sources,
            "priority": self._priority_band(score),
        }

    def _interpret_inflammation(self, score: float) -> str:
        if score < 20:
            return "Inflammation physiologique normale"
        if score < 40:
            return "Inflammation modérée"
        if score < 60:
            return "Inflammation importante"
        return "Inflammation sévère systémique"

    def _priority_band(self, score: float) -> str:
        if score < 30:
            return "Surveillance"
        if score < 60:
            return "Intervention recommandée"
        return "Intervention urgente"

    # ============================================================
    # 6) Microbiome index (flat markers)
    # ============================================================

    def calculate_microbiome_index(self) -> Dict[str, Any]:
        benzoate = safe_get(self.biological_markers, "benzoate")
        hippurate = safe_get(self.biological_markers, "hippurate")
        phenol = safe_get(self.biological_markers, "phenol")
        p_cresol = safe_get(self.biological_markers, "p_cresol")
        indican = safe_get(self.biological_markers, "indican")

        if all(v is None for v in [benzoate, hippurate, phenol, p_cresol, indican]):
            return {"score": None, "interpretation": "Données insuffisantes", "issues": []}

        score = 100.0
        issues: List[str] = []

        if phenol is not None and phenol > 10:
            score -= min(20.0, (phenol - 10.0) * 2.0)
            issues.append(f"Phénol élevé: {phenol:.1f}")

        if p_cresol is not None and p_cresol > 5:
            score -= min(20.0, (p_cresol - 5.0) * 3.0)
            issues.append(f"P-crésol élevé: {p_cresol:.1f}")

        if indican is not None and indican > 20:
            score -= min(15.0, (indican - 20.0))
            issues.append(f"Indican élevé: {indican:.1f}")

        if hippurate is not None and hippurate < 200:
            score -= 15.0
            issues.append(f"Hippurate bas: {hippurate:.1f}")

        if benzoate is not None and benzoate < 5:
            score -= 10.0
            issues.append(f"Benzoate bas: {benzoate:.1f}")

        score = round(clamp(score, 0.0, 100.0), 1)
        self.composite_indices["microbiome_index"] = score

        return {"score": score, "interpretation": self._interpret_microbiome(score), "issues": issues}

    def _interpret_microbiome(self, score: float) -> str:
        if score >= 80:
            return "Microbiome équilibré"
        if score >= 60:
            return "Microbiome correct"
        if score >= 40:
            return "Dysbiose modérée"
        return "Dysbiose importante"

    # ============================================================
    # 7) Orchestration
    # ============================================================

    def calculate_all_indices(self, bio_data_structured: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        bio_data_structured = dict structuré (metabolisme_glucidique/lipides/...) pour calculate_metabolism_index
        """
        results = {
            "stress": self.calculate_stress_index(),
            "metabolic": self.calculate_metabolic_health_score(),
            "neurotransmitters": self.calculate_neurotransmitter_balance(),
            "inflammation": self.calculate_inflammation_index(),
            "microbiome": self.calculate_microbiome_index(),
        }

        if bio_data_structured is not None:
            results["metabolism_index"] = self.calculate_metabolism_index(bio_data_structured)

        return results

    # ============================================================
    # 8) Modèle prédictif (population synthétique) - isolé & tracé
    # ============================================================

    def build_predictive_model(
        self,
        target: str = "biological_age",
        synthetic_population_size: int = 80,
        noise_sd: float = 0.5,
        seed: int = 42,
    ) -> ModelResult:
        """
        IMPORTANT:
        - Ce modèle est une *démo* basée sur une population synthétique autour du patient.
        - À isoler clairement pour éviter de le présenter comme "appris" sur une cohorte réelle.
        """

        try:
            features = self._collect_features_for_model()

            if len(features) < 4:
                return ModelResult(
                    success=False,
                    message="Données insuffisantes pour construire le modèle (minimum 4 variables).",
                    n_features=len(features),
                )

            rng = np.random.default_rng(seed)
            X = pd.DataFrame()

            # synthèse (15% CV)
            for name, val in features.items():
                v = float(val)
                sd = abs(v) * 0.15 if v != 0 else 0.15
                X[name] = rng.normal(loc=v, scale=sd, size=synthetic_population_size)

            # poids "expert" (à documenter)
            weights = {
                "stress_index": -0.02,
                "metabolic_score": 0.03,
                "neuro_balance": 0.02,
                "inflammation_index": -0.015,
                "cortisol_car_30": -0.01,
                "homa_index": -0.015,
                "crp": -0.02,
                "vit_d": 0.01,
                "omega3_index": 0.05,
            }

            y = np.zeros(synthetic_population_size, dtype=float)
            for col in X.columns:
                y += weights.get(col, 0.01) * X[col].to_numpy()

            y += rng.normal(0, noise_sd, synthetic_population_size)

            scaler = StandardScaler()
            Xs = scaler.fit_transform(X)

            model = LinearRegression()
            model.fit(Xs, y)
            r2 = float(model.score(Xs, y))

            coeffs = pd.DataFrame(
                {"Feature": X.columns, "Coefficient": model.coef_, "Abs_Coefficient": np.abs(model.coef_)}
            ).sort_values("Abs_Coefficient", ascending=False)

            # prédire le patient
            patient_df = pd.DataFrame([features]).reindex(columns=X.columns, fill_value=0.0)
            pred = float(model.predict(scaler.transform(patient_df))[0])

            # corrélations
            corrs: Dict[str, Dict[str, Any]] = {}
            for col in X.columns:
                corr, pval = stats.pearsonr(X[col].to_numpy(), y)
                corrs[col] = {"correlation": float(corr), "p_value": float(pval), "significant": bool(pval < 0.05)}

            self.statistical_model = {
                "model": model,
                "scaler": scaler,
                "features": list(X.columns),
                "r2_score": r2,
                "coefficients": coeffs,
                "correlations": corrs,
                "target": target,
                "synthetic_population_size": synthetic_population_size,
                "seed": seed,
            }
            self.predictions[target] = {"value": pred, "confidence": r2}

            feature_importance = dict(zip(coeffs["Feature"], coeffs["Coefficient"]))

            return ModelResult(
                success=True,
                r2_score=r2,
                prediction=pred,
                n_features=len(features),
                feature_importance=feature_importance,
                correlations=corrs,
                coefficients=coeffs,
            )

        except Exception as e:
            logger.exception("Erreur construction modèle")
            return ModelResult(success=False, message=str(e), n_features=0)

    def _collect_features_for_model(self) -> Dict[str, float]:
        features: Dict[str, float] = {}

        # indices composites déjà calculés
        for k, v in self.composite_indices.items():
            if isinstance(v, (int, float)):
                features[k] = float(v)

        # biomarqueurs clés (flat)
        key_markers = [
            "cortisol_car_30",
            "dhea",
            "homa_index",
            "crp",
            "vit_d",
            "omega3_index",
            "dopamine",
            "serotonine",
            "glycemie",
        ]
        for m in key_markers:
            v = safe_get(self.biological_markers, m)
            if v is not None:
                features[m] = float(v)

        # lifestyle scores (numériques)
        for k, v in (self.lifestyle_scores or {}).items():
            fv = to_float(v)
            if fv is not None:
                features[k] = float(fv)

        return features

    # ============================================================
    # 9) Recommandations (simple, déterministe)
    # ============================================================

    def generate_recommendations(self) -> List[Dict[str, Any]]:
        recos: List[Dict[str, Any]] = []

        stress = self.composite_indices.get("stress_index")
        inflam = self.composite_indices.get("inflammation_index")
        metab = self.composite_indices.get("metabolic_score")

        if isinstance(stress, (int, float)) and stress > 60:
            recos.append({"area": "Gestion du stress", "priority": "Élevé", "recommendation": "Protocole stress prioritaire"})

        if isinstance(inflam, (int, float)) and inflam > 40:
            recos.append({"area": "Inflammation", "priority": "Élevé", "recommendation": "Protocole anti-inflammatoire recommandé"})

        if isinstance(metab, (int, float)) and metab < 60:
            recos.append({"area": "Métabolisme", "priority": "Élevé", "recommendation": "Optimisation métabolique nécessaire"})

        return recos if recos else [{"area": "Général", "priority": "Moyen", "recommendation": "Maintenir les bonnes pratiques"}]

    # ============================================================
    # 10) Visualisations (sans seaborn, pas de style global)
    # ============================================================

    def generate_statistical_visualizations(self) -> Optional[BytesIO]:
        try:
            fig = plt.figure(figsize=(16, 10))

            # 1) top coefficients
            ax1 = plt.subplot(2, 3, 1)
            if self.statistical_model.get("coefficients") is not None:
                coeffs = self.statistical_model["coefficients"].head(6)
                ax1.barh(range(len(coeffs)), coeffs["Coefficient"])
                ax1.set_yticks(range(len(coeffs)))
                ax1.set_yticklabels([str(f).replace("_", " ").title() for f in coeffs["Feature"]], fontsize=9)
                ax1.axvline(x=0, linestyle="--", linewidth=0.8)
                ax1.set_title("Impact des facteurs")
            else:
                ax1.text(0.5, 0.5, "Modèle non disponible", ha="center", va="center")

            # 2) indices (bar)
            ax2 = plt.subplot(2, 3, 2)
            if self.composite_indices:
                names = list(self.composite_indices.keys())
                vals = [self.composite_indices[k] for k in names]
                ax2.bar(range(len(names)), vals)
                ax2.set_xticks(range(len(names)))
                ax2.set_xticklabels([n.replace("_", "\n") for n in names], fontsize=8)
                ax2.set_ylim(0, 100)
                ax2.set_title("Indices composites")
            else:
                ax2.text(0.5, 0.5, "Indices non calculés", ha="center", va="center")

            # 3) corrélations (top 8)
            ax3 = plt.subplot(2, 3, 3)
            corrs = self.statistical_model.get("correlations") or {}
            if corrs:
                items = list(corrs.items())[:8]
                names = [k.replace("_", " ").title()[:18] for k, _ in items]
                vals = [v["correlation"] for _, v in items]
                ax3.barh(range(len(names)), vals)
                ax3.set_yticks(range(len(names)))
                ax3.set_yticklabels(names, fontsize=8)
                ax3.set_title("Corrélations (synthétiques)")
                ax3.axvline(0, linestyle="--", linewidth=0.8)
            else:
                ax3.text(0.5, 0.5, "Corrélations non disponibles", ha="center", va="center")

            # 4) cortisol profil
            ax4 = plt.subplot(2, 3, 4)
            times = ["Réveil", "+30", "12h", "18h", "22h"]
            keys = ["cortisol_reveil", "cortisol_car_30", "cortisol_12h", "cortisol_18h", "cortisol_22h"]
            vals = [safe_get(self.biological_markers, k) for k in keys]
            if any(v is not None for v in vals):
                xs = np.arange(len(times))
                y = [v if v is not None else np.nan for v in vals]
                ax4.plot(xs, y, marker="o")
                ax4.set_xticks(xs)
                ax4.set_xticklabels(times)
                ax4.set_title("Profil cortisol")
            else:
                ax4.text(0.5, 0.5, "Cortisol non disponible", ha="center", va="center")

            # 5) neurotransmetteurs
            ax5 = plt.subplot(2, 3, 5)
            neuro = self.calculate_neurotransmitter_balance()
            if neuro.get("details"):
                n_names = list(neuro["details"].keys())
                n_scores = [neuro["details"][k]["score"] for k in n_names]
                ax5.bar(range(len(n_names)), n_scores)
                ax5.set_xticks(range(len(n_names)))
                ax5.set_xticklabels([n.title() for n in n_names], fontsize=9)
                ax5.set_ylim(0, 100)
                ax5.set_title("Neurotransmetteurs")
            else:
                ax5.text(0.5, 0.5, "Neurotransmetteurs non disponibles", ha="center", va="center")

            # 6) distribution indices (horizontal)
            ax6 = plt.subplot(2, 3, 6)
            if self.composite_indices:
                names = list(self.composite_indices.keys())
                vals = [self.composite_indices[k] for k in names]
                ax6.barh(range(len(names)), vals)
                ax6.set_yticks(range(len(names)))
                ax6.set_yticklabels([n.replace("_", " ").title() for n in names], fontsize=8)
                ax6.set_xlim(0, 100)
                ax6.set_title("Scores (0-100)")
            else:
                ax6.text(0.5, 0.5, "Indices non calculés", ha="center", va="center")

            plt.tight_layout()

            buf = BytesIO()
            plt.savefig(buf, format="png", dpi=200, bbox_inches="tight")
            buf.seek(0)
            plt.close(fig)

            return buf

        except Exception:
            logger.exception("Erreur génération visualisations")
            return None

    # ============================================================
    # 11) Export données report
    # ============================================================

    def generate_comprehensive_report_data(self, bio_data_structured: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        indices = self.calculate_all_indices(bio_data_structured=bio_data_structured)
        model = self.build_predictive_model()

        return {
            "patient_info": self.patient_info,
            "composite_indices": indices,
            "statistical_model": {
                "success": model.success,
                "r2_score": model.r2_score,
                "prediction": model.prediction,
                "n_features": model.n_features,
                "message": model.message,
                "feature_importance": model.feature_importance,
            },
            "biological_markers": self.biological_markers,
            "analysis_date": now_str(),
            "recommendations": self.generate_recommendations(),
        }

    # ============================================================
    # Utils
    # ============================================================

    def _risk_band(self, score: float, good_high: bool = True) -> str:
        """
        good_high=True => score haut = bon
        """
        if good_high:
            if score >= 70:
                return "Faible"
            if score >= 50:
                return "Modéré"
            if score >= 30:
                return "Élevé"
            return "Très élevé"
        else:
            # score haut = pire (si tu en as besoin)
            if score < 30:
                return "Faible"
            if score < 50:
                return "Modéré"
            if score < 70:
                return "Élevé"
            return "Très élevé"


__all__ = ["AlgoLifeStatisticalAnalysis"]
