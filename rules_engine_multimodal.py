from __future__ import annotations

import io
import pandas as pd
from typing import Dict, Any, List, Optional


# =========================
# Engine multimodal
# =========================

class MultimodalRulesEngine:

    def __init__(self, excel_file: pd.ExcelFile):
        self.xls = excel_file

    @classmethod
    def from_uploaded_xlsx(cls, uploaded_file):
        data = uploaded_file.getvalue()
        bio = io.BytesIO(data)
        return cls(pd.ExcelFile(bio))

    @classmethod
    def from_path(cls, path: str):
        return cls(pd.ExcelFile(path))

    # =========================
    # Main runner
    # =========================

    def run(self, biology: Dict[str, float], microbiome: Dict[str, float], sex="H"):

        bio_hits = self.apply_bio_rules(biology)
        micro_hits = self.apply_micro_rules(microbiome)

        return {
            "summary": {
                "biology_hits": len(bio_hits),
                "microbiome_hits": len(micro_hits),
                "total_hits": len(bio_hits) + len(micro_hits),
            },
            "biology_hits": bio_hits,
            "microbiome_hits": micro_hits,
        }

    # =========================
    # BIO rules
    # =========================

    def apply_bio_rules(self, bio: Dict[str, float]) -> List[Dict[str, Any]]:
        if "FONCTIONNEL_134" not in self.xls.sheet_names:
            return []

        df = self.xls.parse("FONCTIONNEL_134")

        hits = []
        for _, row in df.iterrows():
            marker = str(row.get("Biomarqueur", "")).lower().strip()
            if marker in bio:
                hits.append({
                    "marker": marker,
                    "value": bio[marker],
                    "category": row.get("Catégorie", ""),
                    "low_interp": row.get("BASSE - Interprétation", ""),
                    "high_interp": row.get("HAUTE - Interprétation", ""),
                })
        return hits

    # =========================
    # MICRO rules
    # =========================

    def apply_micro_rules(self, micro: Dict[str, float]) -> List[Dict[str, Any]]:
        if "Microbiote" not in self.xls.sheet_names:
            return []

        df = self.xls.parse("Microbiote")

        hits = []
        for _, row in df.iterrows():
            marker = str(row.get("Marqueur_bacterien", "")).lower().strip()
            if marker in micro:
                hits.append({
                    "marker": marker,
                    "value": micro[marker],
                    "interpretation": row.get("Interpretation_clinique", ""),
                    "nutrition": row.get("Recommandations_nutritionnelles", ""),
                    "supplementation": row.get("Recommandations_supplementation", ""),
                })
        return hits
