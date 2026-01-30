from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, List, Tuple, Callable


Number = float | int


# ============================================================
# Helpers
# ============================================================

def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def to_float(x: Any) -> Optional[float]:
    """Convertit en float si possible, sinon None."""
    if x is None:
        return None
    try:
        # Attention: bool est subclass de int → on l'exclut
        if isinstance(x, bool):
            return None
        return float(x)
    except (TypeError, ValueError):
        return None


def get_in(d: Optional[Dict[str, Any]], path: Tuple[str, ...]) -> Any:
    """Accès sécurisé à d['a']['b']['c'] via un tuple ('a','b','c')."""
    cur: Any = d
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return None
        cur = cur[key]
    return cur


# ============================================================
# Configuration (seuils & mappings)
# ============================================================

@dataclass(frozen=True)
class Threshold:
    upper: float
    label: str


@dataclass(frozen=True)
class MetricConfig:
    # Pour scorer
    norm_low: float
    norm_high: float
    reverse: bool
    # Pour catégoriser (liste ordonnée)
    thresholds: Tuple[Threshold, ...]
    # Etiquette si valeur manquante
    missing_label: str = "–"


DEFAULT_CONFIG: Dict[str, MetricConfig] = {
    "crp_us": MetricConfig(
        norm_low=0.0, norm_high=5.0, reverse=True,
        thresholds=(
            Threshold(1.0, "Bas – optimal"),
            Threshold(3.0, "Inflammation modérée"),
            Threshold(float("inf"), "Inflammation élevée"),
        )
    ),
    "aa_epa": MetricConfig(
        norm_low=1.0, norm_high=20.0, reverse=True,
        thresholds=(
            Threshold(3.0, "Anti-inflammatoire optimal"),
            Threshold(10.0, "Correct"),
            Threshold(15.0, "Inflammatoire modéré"),
            Threshold(float("inf"), "Profil inflammatoire"),
        )
    ),
    "homa": MetricConfig(
        norm_low=1.0, norm_high=4.0, reverse=True,
        thresholds=(
            Threshold(2.0, "Sensibilité à l'insuline normale"),
            Threshold(2.4, "Insulinorésistance légère"),
            Threshold(float("inf"), "Insulinorésistance"),
        )
    ),
    "zonuline": MetricConfig(
        norm_low=20.0, norm_high=70.0, reverse=True,
        thresholds=(
            Threshold(25.0, "Bonne intégrité intestinale"),
            Threshold(40.0, "Perméabilité augmentée (leaky gut)"),
            Threshold(float("inf"), "Perméabilité sévère"),
        )
    ),
    # aging_delta (biological - chronological)
    "aging_delta": MetricConfig(
        norm_low=-10.0, norm_high=10.0, reverse=True,
        thresholds=(
            Threshold(-2.0, "Âge biologique plus jeune"),
            Threshold(2.0, "Âge biologique cohérent"),
            Threshold(float("inf"), "Âge biologique accéléré"),
        )
    ),
    # CAR (cortisol réveil 30 - réveil)
    "car": MetricConfig(
        norm_low=-10.0, norm_high=10.0, reverse=False,
        thresholds=(
            Threshold(-5.0, "CAR effondré – Burnout avancé"),
            Threshold(0.0, "CAR diminué – Hypo-réactivité HPA"),
            Threshold(5.0, "CAR faible – Fatigue chronique"),
            Threshold(float("inf"), "CAR normal"),
        ),
        missing_label="Données insuffisantes"
    ),
}


# ============================================================
# Core Engine
# ============================================================

class AlgoLifeEngine:
    """
    Moteur rule-based: transforme des biomarqueurs en statuts + scores,
    calcule un score global et génère un plan d'action.
    """

    def __init__(self, config: Optional[Dict[str, MetricConfig]] = None):
        self.config = config or DEFAULT_CONFIG

    # -------------------------
    # Normalisation 0–100
    # -------------------------
    def normalize(self, value: Optional[Number], low: float, high: float, reverse: bool = False) -> Optional[float]:
        v = to_float(value)
        if v is None:
            return None
        # protection division par 0
        if high == low:
            return None
        ratio = (v - low) / (high - low)
        ratio = clamp(ratio, 0.0, 1.0)
        if reverse:
            ratio = 1.0 - ratio
        return round(ratio * 100.0, 1)

    # -------------------------
    # Utilitaires métriques
    # -------------------------
    def categorize(self, value: Optional[Number], metric_key: str) -> str:
        cfg = self.config[metric_key]
        v = to_float(value)
        if v is None:
            return cfg.missing_label
        for th in cfg.thresholds:
            if v < th.upper:
                return th.label
        return cfg.thresholds[-1].label  # fallback

    def score_metric(self, value: Optional[Number], metric_key: str) -> Optional[float]:
        cfg = self.config[metric_key]
        return self.normalize(value, cfg.norm_low, cfg.norm_high, cfg.reverse)

    # -------------------------
    # Evaluate blocks
    # -------------------------
    def evaluate_stress(self, bio: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        cortisol_reveil = to_float(get_in(bio, ("hormones_salivaires", "cortisol_reveil")))
        cortisol_30 = to_float(get_in(bio, ("hormones_salivaires", "cortisol_reveil_30")))

        if cortisol_reveil is None or cortisol_30 is None:
            return {"stress_status": self.config["car"].missing_label, "stress_score": None, "CAR": None}

        car = cortisol_30 - cortisol_reveil
        status = self.categorize(car, "car")
        score = self.score_metric(car, "car")
        return {"stress_status": status, "stress_score": score, "CAR": round(car, 2)}

    def evaluate_inflammation(self, bio: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        crp = to_float(get_in(bio, ("inflammation", "crp_us")))
        if crp is None:
            return {"inflammation_status": "–", "inflammation_score": None, "crp": None}
        return {
            "inflammation_status": self.categorize(crp, "crp_us"),
            "inflammation_score": self.score_metric(crp, "crp_us"),
            "crp": crp,
        }

    def evaluate_omegas(self, bio: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        aa_epa = to_float(get_in(bio, ("acides_gras", "aa_epa")))
        if aa_epa is None:
            return {"omega_status": "–", "omega_score": None, "aa_epa": None}
        return {
            "omega_status": self.categorize(aa_epa, "aa_epa"),
            "omega_score": self.score_metric(aa_epa, "aa_epa"),
            "aa_epa": aa_epa,
        }

    def evaluate_glycemia(self, bio: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        homa = to_float(get_in(bio, ("metabolisme_glucidique", "homa")))
        if homa is None:
            return {"glycemia_status": "–", "glycemia_score": None, "homa": None}
        return {
            "glycemia_status": self.categorize(homa, "homa"),
            "glycemia_score": self.score_metric(homa, "homa"),
            "homa": homa,
        }

    def evaluate_gut(self, bio: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        z = to_float(get_in(bio, ("permeabilite_intestinale", "zonuline")))
        if z is None:
            return {"gut_status": "–", "gut_score": None, "zonuline": None}
        return {
            "gut_status": self.categorize(z, "zonuline"),
            "gut_score": self.score_metric(z, "zonuline"),
            "zonuline": z,
        }

    def evaluate_aging(self, epi: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        biological_age = to_float(get_in(epi, ("epigenetic_age", "biological_age")))
        chronological_age = to_float(get_in(epi, ("epigenetic_age", "chronological_age")))

        if biological_age is None or chronological_age is None:
            return {"aging_status": "–", "aging_score": None, "aging_delta": None}

        delta = biological_age - chronological_age
        return {
            "aging_status": self.categorize(delta, "aging_delta"),
            "aging_score": self.score_metric(delta, "aging_delta"),
            "aging_delta": round(delta, 2),
        }

    # -------------------------
    # Global score
    # -------------------------
    def compute_global_score(self, scores: List[Optional[float]]) -> Optional[float]:
        valid = [s for s in scores if isinstance(s, (int, float))]
        if not valid:
            return None
        return round(sum(valid) / len(valid), 1)

    # -------------------------
    # Action plan (règles)
    # -------------------------
    @dataclass(frozen=True)
    class ActionRule:
        key: str
        score_key: str
        threshold: float
        message: str

    ACTION_RULES: Tuple[ActionRule, ...] = (
        ActionRule("stress", "stress_score", 60, "Optimiser l'axe HPA : adaptogènes (rhodiola/ashwagandha), respiration 4-6, charge allostatique ↓"),
        ActionRule("inflammation", "inflammation_score", 60, "Réduire inflammation : EPA, alimentation anti-inflammatoire, réduction sucres rapides"),
        ActionRule("omega", "omega_score", 50, "Augmenter EPA/DHA (2–3 g/j) et réduire excès oméga-6"),
        ActionRule("glycemia", "glycemia_score", 60, "Insulino-sensibilité : magnésium, marche post-prandiale, fenêtre alimentaire ~10h"),
        ActionRule("gut", "gut_score", 60, "Barrière intestinale : glutamine, zinc-carnosine, réduire alcool/ultra-transformés"),
        ActionRule("aging", "aging_score", 60, "Longévité : exercice, sommeil profond, polyphénols, cohérence circadienne"),
    )

    def generate_action_plan(self, results: Dict[str, Dict[str, Any]]) -> List[str]:
        plan: List[str] = []
        for rule in self.ACTION_RULES:
            block = results.get(rule.key, {})
            score = block.get(rule.score_key)
            if isinstance(score, (int, float)) and score < rule.threshold:
                plan.append(rule.message)
        return plan

    # -------------------------
    # Main orchestrator
    # -------------------------
    def analyze(self, dxa_data: Optional[Dict[str, Any]], bio_data: Optional[Dict[str, Any]], epi_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        # (Option) tu peux brancher DXA ici plus tard
        stress = self.evaluate_stress(bio_data)
        inflam = self.evaluate_inflammation(bio_data)
        omega = self.evaluate_omegas(bio_data)
        glycemia = self.evaluate_glycemia(bio_data)
        gut = self.evaluate_gut(bio_data)
        aging = self.evaluate_aging(epi_data)

        global_score = self.compute_global_score([
            stress.get("stress_score"),
            inflam.get("inflammation_score"),
            omega.get("omega_score"),
            glycemia.get("glycemia_score"),
            gut.get("gut_score"),
            aging.get("aging_score"),
        ])

        blocks = {
            "stress": stress,
            "inflammation": inflam,
            "omega": omega,
            "glycemia": glycemia,
            "gut": gut,
            "aging": aging,
        }

        action_plan = self.generate_action_plan(blocks)

        return {
            **blocks,
            "global_score": global_score,
            "action_plan": action_plan,
            "dxa_used": False if dxa_data is None else False,  # placeholder explicite
        }


# ============================================================
# Stat analysis (plus cohérent + réutilise normalize si tu veux)
# ============================================================

class AlgoLifeStatisticalAnalysis:
    def __init__(self):
        pass

    def _mean_or_none(self, xs: List[Optional[float]]) -> Optional[float]:
        valid = [x for x in xs if isinstance(x, (int, float))]
        return round(sum(valid) / len(valid), 1) if valid else None

    def calculate_metabolism_index(self, bio_data: Optional[Dict[str, Any]]) -> Optional[float]:
        if not isinstance(bio_data, dict):
            return None

        homa = to_float(get_in(bio_data, ("metabolisme_glucidique", "homa")))
        tg = to_float(get_in(bio_data, ("lipides", "triglycerides")))
        hdl = to_float(get_in(bio_data, ("lipides", "hdl")))

        parts: List[Optional[float]] = []

        # HOMA (plus bas = mieux)
        if homa is not None:
            parts.append(clamp(1 - (homa / 4.0), 0, 1) * 100)

        # TG (plus bas = mieux, ~200 mg/dL = très mauvais)
        if tg is not None:
            parts.append(clamp(1 - (tg / 200.0), 0, 1) * 100)

        # HDL (plus haut = mieux, cap à 80)
        if hdl is not None:
            parts.append(clamp(hdl / 80.0, 0, 1) * 100)

        return self._mean_or_none([round(p, 1) if p is not None else None for p in parts])

    def calculate_inflammatory_index(self, bio_data: Optional[Dict[str, Any]]) -> Optional[float]:
        if not isinstance(bio_data, dict):
            return None

        crp = to_float(get_in(bio_data, ("inflammation", "crp_us")))
        aa_epa = to_float(get_in(bio_data, ("acides_gras", "aa_epa")))

        parts: List[Optional[float]] = []

        # CRP (0->100, 5->0)
        if crp is not None:
            parts.append(clamp(1 - (crp / 5.0), 0, 1) * 100)

        # AA/EPA (1->100, 20->0)
        if aa_epa is not None:
            parts.append(clamp(1 - (aa_epa / 20.0), 0, 1) * 100)

        return self._mean_or_none([round(p, 1) if p is not None else None for p in parts])

    def get_percentile_rank(self, value: Optional[Number], reference_values: List[Number]) -> Optional[float]:
        v = to_float(value)
        if v is None or not reference_values:
            return None

        ref = sorted([float(x) for x in reference_values if to_float(x) is not None])
        if not ref:
            return None

        # % de valeurs strictement inférieures
        position = sum(1 for x in ref if x < v)
        percentile = (position / len(ref)) * 100.0
        return round(percentile, 1)
