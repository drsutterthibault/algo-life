# -*- coding: utf-8 -*-
"""
ALGO-LIFE - Microbiome Extractor (IDK® GutMAP / Immundiagnostik)
Version: 1.0 - Jan 2026

Objectif
--------
Extraire les informations microbiote depuis le TEXTE (pas OCR) issu du PDF GutMAP:
- Dysbiosis label (+ index estimé)
- Diversity label (+ shannon index "catégoriel" estimé)
- Résultats A1..E5 (expected / slightly deviating / deviating)
- Liste de marqueurs/bactéries si présentes dans le texte

⚠️ Limite connue (normale)
--------------------------
Sur certains rapports GutMAP, les abondances -3..+3 sont surtout graphiques (points sur échelle).
Le texte PDF ne contient pas la valeur numérique. Ce module se base donc sur les éléments textuels robustes.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


def _clean_spaces(s: str) -> str:
    s = s.replace("\u00a0", " ")  # nbsp
    s = re.sub(r"[ \t]+", " ", s)
    return s.strip()


def _safe_float(x: str) -> Optional[float]:
    try:
        x = x.replace(",", ".")
        return float(x)
    except Exception:
        return None


def _find_first(patterns: List[str], text: str, flags: int = re.IGNORECASE) -> Optional[str]:
    for p in patterns:
        m = re.search(p, text, flags)
        if m:
            if m.lastindex:
                return m.group(1).strip()
            return m.group(0).strip()
    return None


def _extract_sample_id(text: str) -> Optional[str]:
    # Ex: "Sample ID 123456" / "ID 123456"
    return _find_first(
        [
            r"sample\s*id[:\s]+([A-Za-z0-9\-_/]+)",
            r"\bid[:\s]+([A-Za-z0-9\-_/]{6,})",
        ],
        text,
    )


def _extract_report_date(text: str) -> Optional[str]:
    # Ex: 01.02.2026 / 01/02/2026
    return _find_first(
        [
            r"(?:report\s*date|date\s*of\s*report|date)\s*[:\s]+(\d{2}[./-]\d{2}[./-]\d{4})",
            r"\b(\d{2}[./-]\d{2}[./-]\d{4})\b",
        ],
        text,
    )


def _extract_dysbiosis_label(text_lower: str) -> Optional[str]:
    # Texte typique: normobiotic / mildly dysbiotic / severely dysbiotic
    if "severely dysbiotic" in text_lower:
        return "severely dysbiotic"
    if "mildly dysbiotic" in text_lower:
        return "mildly dysbiotic"
    if "normobiotic" in text_lower:
        return "normobiotic"
    # FR parfois
    if "dysbiose sévère" in text_lower or "dysbiose severe" in text_lower:
        return "severely dysbiotic"
    if "dysbiose légère" in text_lower or "dysbiose legere" in text_lower:
        return "mildly dysbiotic"
    if "normobiose" in text_lower:
        return "normobiotic"
    return None


def _dysbiosis_index_from_label(label: Optional[str]) -> Optional[int]:
    if not label:
        return None
    # Mapping simple (catégoriel) -> 1..5
    if label == "normobiotic":
        return 1
    if label == "mildly dysbiotic":
        return 3
    if label == "severely dysbiotic":
        return 5
    return None


def _extract_diversity_label(text_lower: str) -> Optional[str]:
    # On cherche la phrase "high / moderate / low bacterial diversity"
    if "high bacterial diversity" in text_lower or "diversity high" in text_lower:
        return "high"
    if "moderate bacterial diversity" in text_lower or "diversity moderate" in text_lower:
        return "moderate"
    if "low bacterial diversity" in text_lower or "diversity low" in text_lower:
        return "low"

    # FR
    if "diversité élevée" in text_lower or "diversite elevee" in text_lower:
        return "high"
    if "diversité modérée" in text_lower or "diversite moderee" in text_lower:
        return "moderate"
    if "diversité faible" in text_lower or "diversite faible" in text_lower:
        return "low"
    return None


def _shannon_numeric_from_label(label: Optional[str]) -> Optional[int]:
    # Catégorie simplifiée: High=3, Moderate=2, Low=1
    if not label:
        return None
    if label == "high":
        return 3
    if label == "moderate":
        return 2
    if label == "low":
        return 1
    return None


def _extract_group_results(text: str) -> Dict[str, str]:
    """
    Extrait les items A1..E5 avec statut textuel:
    - expected
    - slightly deviating
    - deviating

    Format GutMAP fréquent:
      "A1 Result: expected"
      "B2 Result: deviating"
    """
    results: Dict[str, str] = {}

    # Exemple robuste: "A1 Result: expected" ou "A1 Result expected"
    pat = re.compile(
        r"\b([A-E][1-5])\b.*?\bresult\b\s*[:\-]?\s*(expected|slightly\s+deviating|deviating)",
        re.IGNORECASE | re.DOTALL,
    )
    for m in pat.finditer(text):
        code = m.group(1).upper()
        status = m.group(2).lower().replace("  ", " ").strip()
        results[code] = status

    # Variante: "Result: expected" sur la ligne suivante
    if not results:
        pat2 = re.compile(
            r"\b([A-E][1-5])\b[\s:]*\n.*?\bresult\b\s*[:\-]?\s*(expected|slightly\s+deviating|deviating)",
            re.IGNORECASE | re.DOTALL,
        )
        for m in pat2.finditer(text):
            code = m.group(1).upper()
            status = m.group(2).lower().replace("  ", " ").strip()
            results[code] = status

    return results


def _extract_markers(text: str) -> List[Dict[str, Any]]:
    """
    Récupère une liste de bactéries/espèces si elles apparaissent explicitement dans le texte.
    GutMAP contient parfois des noms latins sous forme 'Genus species' ou 'Genus spp.'.
    """
    markers: List[Dict[str, Any]] = []

    # Noms latins: "Faecalibacterium prausnitzii", "Akkermansia muciniphila"
    latin_pat = re.compile(r"\b([A-Z][a-z]+)\s+([a-z]+(?:_[a-z]+)?)\b")
    # Filtre anti-bruit: exclure des mots trop communs
    blacklist = {"Result", "Sample", "Bacterial", "Diversity", "Report", "Index"}

    seen = set()
    for m in latin_pat.finditer(text):
        genus = m.group(1)
        species = m.group(2).replace("_", " ")
        if genus in blacklist:
            continue

        name = f"{genus} {species}"
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)

        # Filtre: garder des espèces plausibles (évite de ramasser du texte random)
        if len(species) < 4:
            continue
        markers.append({"name": name})

    return markers


def _compute_simple_scores(group_results: Dict[str, str]) -> Dict[str, float]:
    """
    Petits scores "catégoriels" basés sur A1..E5.
    - expected -> 100
    - slightly deviating -> 50
    - deviating -> 0

    Puis moyenne par groupes A..E + global.
    """
    if not group_results:
        return {}

    def map_score(s: str) -> int:
        s = s.lower()
        if "expected" in s:
            return 100
        if "slightly" in s:
            return 50
        if "deviating" in s:
            return 0
        return 0

    buckets: Dict[str, List[int]] = {"A": [], "B": [], "C": [], "D": [], "E": []}
    for code, status in group_results.items():
        group = code[0]
        buckets.setdefault(group, []).append(map_score(status))

    scores: Dict[str, float] = {}
    all_vals: List[int] = []
    for g, vals in buckets.items():
        if vals:
            scores[f"group_{g}_score"] = round(sum(vals) / len(vals), 1)
            all_vals.extend(vals)

    if all_vals:
        scores["global_score"] = round(sum(all_vals) / len(all_vals), 1)

    # Heuristiques d'interprétation (optionnel)
    # Anti-inflammatoire/commensal etc. dépend de la signification A..E de ton PDF.
    # Tu pourras mapper A..E plus tard selon la doc GutMAP.
    return scores


def extract_microbiome_data(text: str, debug: bool = False) -> Dict[str, Any]:
    """
    Fonction principale appelée par app.py.
    Paramètre:
      - text: str (texte déjà extrait du PDF)
    Retour:
      - dict structuré pour st.session_state
    """
    if not text or not isinstance(text, str):
        return {}

    raw = _clean_spaces(text)
    text_lower = raw.lower()

    sample_id = _extract_sample_id(raw)
    report_date = _extract_report_date(raw)

    dys_label = _extract_dysbiosis_label(text_lower)
    dys_index = _dysbiosis_index_from_label(dys_label)

    div_label = _extract_diversity_label(text_lower)
    shannon_numeric = _shannon_numeric_from_label(div_label)

    group_results = _extract_group_results(text)
    scores = _compute_simple_scores(group_results)

    markers = _extract_markers(text)

    out: Dict[str, Any] = {
        "sample_id": sample_id,
        "report_date": report_date,
        "dysbiosis_label": dys_label,
        "dysbiosis_index": dys_index,
        "diversity_label": div_label,
        "shannon_index_numeric": shannon_numeric,
        "group_results": group_results,  # A1..E5 -> expected/slightly deviating/deviating
        "scores": scores,                # group_A_score ... global_score
        "markers": markers,              # liste de bactéries si trouvées
        "source": "idk_gutmap_text",
    }

    # Nettoyage (retire les clés None vides pour ne pas polluer)
    cleaned = {}
    for k, v in out.items():
        if v is None:
            continue
        if isinstance(v, (dict, list)) and len(v) == 0:
            continue
        cleaned[k] = v

    if debug:
        cleaned["_debug"] = {
            "len_text": len(text),
            "found_group_items": len(group_results),
            "found_markers": len(markers),
        }

    return cleaned
