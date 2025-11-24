import numpy as np

# ============================================================
#  ENGINE ALGO-LIFE – Scoring clinique & longévité
# ============================================================

class AlgoLifeEngine:

    def __init__(self):
        pass

    # --------------------------------------------------------
    # 1. Normalisation générique 0–100
    # --------------------------------------------------------
    def normalize(self, value, low, high, reverse=False):
        """Normalise des valeurs entre 0 et 100 (reverse si besoin)."""
        if value is None:
            return None
        try:
            score = (value - low) / (high - low)
            score = max(0, min(1, score))
            if reverse:
                score = 1 - score
            return round(score * 100, 1)
        except:
            return None

    # --------------------------------------------------------
    # 2. Stress phenotype (Cortisol CAR)
    # --------------------------------------------------------
    def evaluate_stress(self, bio):
        if not bio or "hormones_salivaires" not in bio:
            return {"stress_status": "Données insuffisantes", "stress_score": None}

        cortisol_reveil = bio["hormones_salivaires"].get("cortisol_reveil")
        cortisol_30 = bio["hormones_salivaires"].get("cortisol_reveil_30")

        if cortisol_reveil and cortisol_30:
            CAR = cortisol_30 - cortisol_reveil

            # Classification clinique
            if CAR < -5:
                status = "CAR effondré – Burnout avancé"
            elif CAR < 0:
                status = "CAR diminué – Hypo-réactivité HPA"
            elif CAR < 5:
                status = "CAR faible – Fatigue chronique"
            else:
                status = "CAR normal"

            # scoring : -10 to +10 mapped to 0–100
            score = self.normalize(CAR, -10, 10, reverse=False)

            return {
                "stress_status": status,
                "stress_score": score,
                "CAR": round(CAR, 2)
            }

        return {"stress_status": "Incomplet", "stress_score": None}

    # --------------------------------------------------------
    # 3. Inflammation (CRP ultrasensible)
    # --------------------------------------------------------
    def evaluate_inflammation(self, bio):
        crp = None
        if bio and "inflammation" in bio:
            crp = bio["inflammation"].get("crp_us")

        if crp is None:
            return {"inflammation_status": "–", "inflammation_score": None}

        if crp < 1:
            status = "Bas – optimal"
        elif crp < 3:
            status = "Inflammation modérée"
        else:
            status = "Inflammation élevée"

        score = self.normalize(crp, 0, 5, reverse=True)

        return {
            "inflammation_status": status,
            "inflammation_score": score,
            "crp": crp
        }

    # --------------------------------------------------------
    # 4. Omega profile (AA/EPA)
    # --------------------------------------------------------
    def evaluate_omegas(self, bio):
        aa_epa = None

        if bio and "acides_gras" in bio:
            aa_epa = bio["acides_gras"].get("aa_epa")

        if aa_epa is None:
            return {"omega_status": "–", "omega_score": None}

        if aa_epa < 3:
            status = "Anti-inflammatoire optimal"
        elif aa_epa < 10:
            status = "Correct"
        elif aa_epa < 15:
            status = "Inflammatoire modéré"
        else:
            status = "Profil inflammatoire"

        score = self.normalize(aa_epa, 1, 20, reverse=True)

        return {
            "omega_status": status,
            "omega_score": score,
            "aa_epa": aa_epa
        }

    # --------------------------------------------------------
    # 5. Glycemia (HOMA-IR)
    # --------------------------------------------------------
    def evaluate_glycemia(self, bio):
        homa = None
        if bio and "metabolisme_glucidique" in bio:
            homa = bio["metabolisme_glucidique"].get("homa")

        if homa is None:
            return {"glycemia_status": "–", "glycemia_score": None}

        if homa < 2:
            status = "Sensibilité à l'insuline normale"
        elif homa < 2.4:
            status = "Insulinorésistance légère"
        else:
            status = "Insulinorésistance"

        score = self.normalize(homa, 1, 4, reverse=True)

        return {
            "glycemia_status": status,
            "glycemia_score": score,
            "homa": homa
        }

    # --------------------------------------------------------
    # 6. Gut permeability (Zonuline / LBP)
    # --------------------------------------------------------
    def evaluate_gut(self, bio):
        gut_status = "–"
        score = None

        if bio and "permeabilite_intestinale" in bio:
            z = bio["permeabilite_intestinale"].get("zonuline")

            if z:
                if z < 25:
                    gut_status = "Bonne intégrité intestinale"
                elif z < 40:
                    gut_status = "Perméabilité augmentée (leaky gut)"
                else:
                    gut_status = "Perméabilité sévère"

                score = self.normalize(z, 20, 70, reverse=True)

        return {
            "gut_status": gut_status,
            "gut_score": score
        }

    # --------------------------------------------------------
    # 7. Aging (épigénétique)
    # --------------------------------------------------------
    def evaluate_aging(self, epi):
        if not epi or "epigenetic_age" not in epi:
            return {"aging_status": "–", "aging_score": None}

        data = epi["epigenetic_age"]
        if "biological_age" not in data or "chronological_age" not in data:
            return {"aging_status": "–", "aging_score": None}

        # Vérifier que les valeurs ne sont pas None
        biological_age = data["biological_age"]
        chronological_age = data["chronological_age"]
        
        if biological_age is None or chronological_age is None:
            return {"aging_status": "–", "aging_score": None}

        delta = biological_age - chronological_age

        if delta < -2:
            status = "Âge biologique plus jeune"
        elif delta < 2:
            status = "Âge biologique cohérent"
        else:
            status = "Âge biologique accéléré"

        score = self.normalize(delta, -10, 10, reverse=True)

        return {
            "aging_status": status,
            "aging_delta": round(delta, 2),
            "aging_score": score
        }

    # --------------------------------------------------------
    # 8. Global longevity score
    # --------------------------------------------------------
    def compute_global_score(self, scores):
        valid_scores = [s for s in scores if s is not None]
        if not valid_scores:
            return None
        return round(sum(valid_scores) / len(valid_scores), 1)

    # --------------------------------------------------------
    # 9. PLAN D'ACTION (Option C)
    # --------------------------------------------------------
    def generate_action_plan(self, results):
        plan = []

        # Stress
        if results["stress"]["stress_score"] and results["stress"]["stress_score"] < 60:
            plan.append("Optimiser l'axe HPA : Adaptogènes (rhodiola, ashwagandha), respiration 4-6, charge allostatique ↓")

        # Inflammation
        if results["inflam"]["inflammation_score"] and results["inflam"]["inflammation_score"] < 60:
            plan.append("Réduire inflammation : oméga-3 EPA, alimentation anti-inflammatoire, réduction sucres rapides")

        # Omegas
        if results["omega"]["omega_score"] and results["omega"]["omega_score"] < 50:
            plan.append("Augmenter EPA/DHA 2–3 g/j, réduire excès oméga-6")

        # Glycemia
        if results["glycemia"]["glycemia_score"] and results["glycemia"]["glycemia_score"] < 60:
            plan.append("Insulino-sensibilité : chrome, magnésium, marche post-prandiale, fenêtre alimentaire 10h")

        # Gut
        if results["gut"]["gut_score"] and results["gut"]["gut_score"] < 60:
            plan.append("Réparer la barrière intestinale : glutamine, zinc-carnosine, réduire gluten/alcool")

        # Aging
        if results["aging"]["aging_score"] and results["aging"]["aging_score"] < 60:
            plan.append("Optimisation longévité : exercice, sommeil profond, polyphénols, NAD+, sensibilité circadienne")

        return plan

    # --------------------------------------------------------
    # 10. ANALYSE FINALE
    # --------------------------------------------------------
    def analyze(self, dxa_data, bio_data, epi_data):

        stress = self.evaluate_stress(bio_data)
        inflam = self.evaluate_inflammation(bio_data)
        omega = self.evaluate_omegas(bio_data)
        glycemia = self.evaluate_glycemia(bio_data)
        gut = self.evaluate_gut(bio_data)
        aging = self.evaluate_aging(epi_data)

        # Global longevity score
        global_score = self.compute_global_score([
            stress["stress_score"],
            inflam["inflammation_score"],
            omega["omega_score"],
            glycemia["glycemia_score"],
            gut["gut_score"],
            aging["aging_score"]
        ])

        # Plan d'action
        action_plan = self.generate_action_plan({
            "stress": stress,
            "inflam": inflam,
            "omega": omega,
            "glycemia": glycemia,
            "gut": gut,
            "aging": aging
        })

        return {
            "stress": stress,
            "inflammation": inflam,
            "omega": omega,
            "glycemia": glycemia,
            "gut": gut,
            "aging": aging,
            "global_score": global_score,
            "action_plan": action_plan
        }
