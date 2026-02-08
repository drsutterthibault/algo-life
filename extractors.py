"""
UNILABS / ALGO-LIFE - Extractors v10.0 CORRECTED
✅ Bug ligne 215 corrigé (m.group("name") → m.group("n"))
✅ Extraction microbiote FORTEMENT améliorée
✅ Détection des points noirs et positions (-3 à +3)
✅ Extraction des bactéries individuelles avec noms complets
✅ Support multi-format (PDF + Excel)
"""

from __future__ import annotations

import os
import re
import unicodedata
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd


# =====================================================================
# NORMALISATION ROBUSTE POUR MATCHING
# =====================================================================
def normalize_biomarker_name(name: str) -> str:
    """
    Normalisation robuste pour matcher Excel:
    - trim, suppression accents, uppercase
    - nettoyage ponctuation, espaces normalisés
    """
    if name is None:
        return ""
    s = str(name).strip()

    # Supprimer accents
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))

    # Uppercase
    s = s.upper()

    # Harmoniser ponctuation
    s = s.replace(".", " ")
    s = s.replace(",", " ")
    s = s.replace("'", "'")

    # Garder A-Z 0-9 + séparateurs simples
    s = re.sub(r"[^A-Z0-9\s\-\+/]", " ", s)

    # Espaces propres
    s = re.sub(r"\s+", " ", s).strip()

    # Compacter certains acronymes fréquents
    s = s.replace("C P K", "CPK")
    s = s.replace("L D L", "LDL")
    s = s.replace("H D L", "HDL")
    s = s.replace("V G M", "VGM")
    s = s.replace("T C M H", "TCMH")
    s = s.replace("C C M H", "CCMH")
    s = s.replace("C R P", "CRP")
    s = s.replace("T S H", "TSH")
    s = s.replace("D F G", "DFG")
    s = s.replace("G P T", "GPT")
    s = s.replace("G O T", "GOT")

    return s


def _safe_float(x) -> Optional[float]:
    """Conversion sécurisée en float"""
    try:
        if x is None:
            return None
        s = str(x).strip().replace(",", ".")
        s = re.sub(r"[^0-9\.\-\+eE]", "", s)
        return float(s) if s else None
    except Exception:
        return None


def _clean_ref(ref: str) -> str:
    """Nettoie une référence"""
    if ref is None:
        return ""
    r = str(ref).strip()
    r = r.replace("—", "-").replace("–", "-")
    r = re.sub(r"\s+", " ", r)
    return r


def determine_biomarker_status(value, reference, biomarker_name=None) -> str:
    """
    Détermine le statut d'un biomarqueur
    Returns: 'Bas' | 'Normal' | 'Élevé' | 'Inconnu'
    """
    v = _safe_float(value)
    if v is None:
        return "Inconnu"

    ref = _clean_ref(reference)

    # Range: "x - y" ou "x à y"
    m = re.search(r"(-?\d+(?:[.,]\d+)?)\s*(?:-|à|to)\s*(-?\d+(?:[.,]\d+)?)", ref, flags=re.IGNORECASE)
    if m:
        lo = _safe_float(m.group(1))
        hi = _safe_float(m.group(2))
        if lo is None or hi is None:
            return "Inconnu"
        if v < lo:
            return "Bas"
        if v > hi:
            return "Élevé"
        return "Normal"

    # "< x" ou "≤ x"
    m = re.search(r"(?:<|≤)\s*(-?\d+(?:[.,]\d+)?)", ref)
    if m:
        hi = _safe_float(m.group(1))
        if hi is None:
            return "Inconnu"
        return "Élevé" if v > hi else "Normal"

    # "> x" ou "≥ x"
    m = re.search(r"(?:>|≥)\s*(-?\d+(?:[.,]\d+)?)", ref)
    if m:
        lo = _safe_float(m.group(1))
        if lo is None:
            return "Inconnu"
        return "Bas" if v < lo else "Normal"

    return "Inconnu"


# =====================================================================
# PDF TEXT LOADER
# =====================================================================
def _read_pdf_text(pdf_path: str) -> str:
    """Lit le texte complet d'un PDF"""
    try:
        import pdfplumber
    except ImportError as e:
        raise ImportError("pdfplumber manquant. pip install pdfplumber") from e

    chunks: List[str] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            chunks.append(page.extract_text() or "")
    return "\n".join(chunks)


# =====================================================================
# BIOLOGIE - EXTRACTION PDF
# =====================================================================
_IGNORE_PATTERNS = [
    r"^Édition\s*:",
    r"^Laboratoire",
    r"^SYNLAB",
    r"^UNILABS",
    r"^Dossier",
    r"^FranceLIS",
    r"^Analyses",
    r"^BIOCHIMIE|^CHIMIE|^HORMONOLOGIE|^IMMUNOLOGIE|^HEMATOLOGIE|^EQUILIBRE|^STATUT|^PERMEABILITE",
    r"^Colorimétrie|^Chimiluminescence|^Immunoturbidimétrie",
    r"^Interprétation",
    r"^Accéder",
    r"^Validé",
    r"^Page\s+\d+",
]


def _is_noise_line(line: str) -> bool:
    """Détecte les lignes de bruit"""
    if not line:
        return True
    s = line.strip()
    if len(s) < 4:
        return True
    for pat in _IGNORE_PATTERNS:
        if re.search(pat, s, flags=re.IGNORECASE):
            return True
    return False


def extract_synlab_biology(pdf_path: str) -> Dict[str, Any]:
    """
    Extraction biologie depuis PDF SYNLAB/UNILABS
    Output: { biomarker: {value, unit, reference, status}, ... }
    """
    text = _read_pdf_text(pdf_path)
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    out: Dict[str, Any] = {}

    # Pattern France: NAME VALUE UNIT (REF)
    pat_fr = re.compile(
        r"^(?P<n>[A-ZÀ-Ÿ0-9\.\-\/\s]{3,60})\s+"
        r"(?P<value>[<>]?\s*[\+\-]?\s*\d+(?:[.,]\d+)?)\s*"
        r"(?P<unit>[a-zA-ZµμÎ¼/%]+(?:\s*[a-zA-ZµμÎ¼/%]+)?)?\s*"
        r"\((?P<ref>[^)]+)\)",
        flags=re.UNICODE,
    )

    # Pattern Belgium: optional ">" + name + value + ref-range + unit
    pat_be = re.compile(
        r"^(?:>\s*)?"
        r"(?P<n>[A-Za-zÀ-ÿ0-9\.\-\/\s]{3,60}?)\s+"
        r"(?P<valsign>[\+\-])?\s*(?P<value>\d+(?:[.,]\d+)?)\s+"
        r"(?P<ref>\d+(?:[.,]\d+)?\s*-\s*\d+(?:[.,]\d+)?)\s+"
        r"(?P<unit>[A-Za-zµμÎ¼/%]+(?:\s*[A-Za-zµμÎ¼/%]+)?)\s*$",
        flags=re.UNICODE,
    )

    for ln in lines:
        if _is_noise_line(ln):
            continue

        # Try Belgium format first
        m = pat_be.match(ln)
        if m:
            name = m.group("n").strip()
            value_str = m.group("value")
            unit = (m.group("unit") or "").strip()
            ref = _clean_ref(m.group("ref"))

            # ✅ CONVERSION STRING → FLOAT (CRITIQUE!)
            value_float = _safe_float(value_str)

            status = determine_biomarker_status(value_float, ref, name)
            out[name] = {"value": value_float, "unit": unit, "reference": ref, "status": status}
            continue

        # Try France format
        m = pat_fr.match(ln)
        if m:
            name = m.group("n").strip()
            if re.search(r"\bSIEMENS\b", name, flags=re.IGNORECASE):
                continue
            value_str = m.group("value")
            unit = (m.group("unit") or "").strip()
            ref = _clean_ref(m.group("ref"))

            # ✅ CONVERSION STRING → FLOAT (CRITIQUE!)
            value_float = _safe_float(value_str)

            status = determine_biomarker_status(value_float, ref, name)
            out[name] = {"value": value_float, "unit": unit, "reference": ref, "status": status}
            continue

    return out


# =====================================================================
# MICROBIOTE - EXTRACTION FORTEMENT AMÉLIORÉE
# =====================================================================
def _parse_bacteria_line(line: str) -> Optional[Dict[str, Any]]:
    """
    Parse une ligne de bactérie du rapport GutMAP
    Returns:
        {
            "id": "300",
            "name": "Various Bacillota",
            "abundance_level": None,
            "status": "Unknown"
        }
    """
    pattern = re.compile(
        r"(?:^|\s)(\d{3})\s+([A-Za-z\[\]\(\)\.\-&,\s]+?)$",
        re.UNICODE,
    )

    match = pattern.search(line)
    if not match:
        return None

    bacteria_id = match.group(1)
    bacteria_name = match.group(2).strip()
    bacteria_name = re.sub(r"\s+", " ", bacteria_name).strip()

    return {
        "id": bacteria_id,
        "name": bacteria_name,
        "abundance_level": None,
        "status": "Unknown",
    }


def _status_from_level(level: Optional[int]) -> str:
    """Map -3..+3 → Reduced/Normal/Elevated (compat GutMAP)."""
    if level is None:
        return "Unknown"
    if level <= -1:
        return "Reduced"
    if level >= 1:
        return "Elevated"
    return "Normal"


def _detect_gutmap_dot_levels(pdf_path: str) -> Dict[str, int]:
    """
    Détecte les points noirs (-3..+3) pour les lignes bactériennes GutMAP.

    Approche minimal-invasive:
    - Utilise pdfplumber pour récupérer les positions Y des IDs (3 chiffres)
    - Rend la page en image (to_image) et calcule un score "pixels sombres" autour des centres de colonnes
    - Retourne { "701": 0, "300": -2, ... }

    ⚠️ Si la détection échoue (PDF différent), renvoie {} sans casser l'extraction.
    """
    try:
        import pdfplumber
    except ImportError as e:
        raise ImportError("pdfplumber manquant. pip install pdfplumber") from e

    levels_by_id: Dict[str, int] = {}
    target_cols = [-3, -2, -1, 0, 1, 2, 3]

    def _parse_col_label(t: str) -> Optional[int]:
        s = str(t).strip().replace("−", "-")  # minus typographique
        if re.fullmatch(r"[+-]?[0-3]", s):
            return int(s)
        return None

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            words = page.extract_words() or []
            if not words:
                continue

            # (A) centres X des labels -3..+3 si présents
            col_centers: Dict[int, float] = {}
            for w in words:
                v = _parse_col_label(w.get("text", ""))
                if v in target_cols:
                    x0 = float(w.get("x0", 0))
                    x1 = float(w.get("x1", 0))
                    if x1 > x0:
                        col_centers[v] = (x0 + x1) / 2.0

            has_all = all(v in col_centers for v in target_cols)

            # (B) lignes bactéries: Y via ID (3 chiffres)
            id_rows: List[Tuple[str, float]] = []
            for w in words:
                txt = (w.get("text") or "").strip()
                if re.fullmatch(r"\d{3}", txt):
                    top = float(w.get("top", 0))
                    bottom = float(w.get("bottom", 0))
                    y_center = (top + bottom) / 2.0
                    id_rows.append((txt, y_center))

            if not id_rows:
                continue

            # (C) rendu image
            resolution = 220
            scale = resolution / 72.0  # points PDF → pixels
            im = page.to_image(resolution=resolution).original  # PIL Image
            im_rgb = im.convert("RGB")
            pix = im_rgb.load()
            width, height = im_rgb.size

            # Fallback centres colonnes si labels absents
            if not has_all:
                x_min = int(width * 0.58)
                x_max = int(width * 0.95)
                span = max(1, x_max - x_min)
                step = span / 6.0
                for idx, v in enumerate(target_cols):
                    col_centers[v] = (x_min + idx * step) / scale  # repasser en points PDF

            def _dark_score(px: int, py: int, r: int = 7) -> int:
                score = 0
                for yy in range(max(0, py - r), min(height, py + r + 1)):
                    for xx in range(max(0, px - r), min(width, px + r + 1)):
                        rr, gg, bb = pix[xx, yy]
                        if rr < 70 and gg < 70 and bb < 70:
                            score += 1
                return score

            band = int(10 * scale)

            for bid, y_center in id_rows:
                py = int(y_center * scale)
                if py < 0 or py >= height:
                    continue

                y_tests = [py, py - band // 2, py + band // 2]

                best_val: Optional[int] = None
                best_score = 0

                for v in target_cols:
                    cx_pdf = col_centers.get(v)
                    if cx_pdf is None:
                        continue
                    px = int(cx_pdf * scale)
                    if px < 0 or px >= width:
                        continue

                    score = 0
                    for y_try in y_tests:
                        if 0 <= y_try < height:
                            score = max(score, _dark_score(px, y_try, r=7))

                    if score > best_score:
                        best_score = score
                        best_val = v

                # seuil minimal pour éviter faux positifs
                if best_val is not None and best_score >= 12:
                    levels_by_id[bid] = int(best_val)

    return levels_by_id


def extract_idk_microbiome(pdf_path: str, excel_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Extraction microbiome IDK GutMAP AMÉLIORÉE

    ✅ Extraction des bactéries individuelles (48 marqueurs)
    ✅ Détection des points noirs et positions (-3 à +3)
    ✅ Noms complets des bactéries
    ✅ Regroupement par catégories (A, B, C, D, E)
    """
    text = _read_pdf_text(pdf_path)

    # ─────────────────────────────────────────────────────────────────
    # 1. DYSBIOSIS INDEX
    # ─────────────────────────────────────────────────────────────────
    di = None

    m_di = re.search(r"(?:DI|Dysbiosis\s+index)\s*[:\-]?\s*([1-5])", text, flags=re.IGNORECASE)
    if m_di:
        di = int(m_di.group(1))
    else:
        m = re.search(r"Result:\s*The microbiota is\s+([A-Za-z\- ]+)", text, flags=re.IGNORECASE)
        if m:
            label = m.group(1).strip().lower()
            if "normobiotic" in label:
                di = 1
            elif "mild" in label:
                di = 3
            elif "sever" in label or "severe" in label:
                di = 5
            elif "moderate" in label:
                di = 3

    # ─────────────────────────────────────────────────────────────────
    # 2. DIVERSITY
    # ─────────────────────────────────────────────────────────────────
    diversity = None
    md = re.search(r"Result:\s*The bacterial diversity is\s+([A-Za-z\- ]+)", text, flags=re.IGNORECASE)
    if md:
        diversity = md.group(1).strip()

    diversity_metrics = {}
    m_shannon = re.search(r"Shannon[:\s]+(\d+(?:\.\d+)?)", text, flags=re.IGNORECASE)
    if m_shannon:
        diversity_metrics["shannon"] = _safe_float(m_shannon.group(1))

    m_simpson = re.search(r"Simpson[:\s]+(\d+(?:\.\d+)?)", text, flags=re.IGNORECASE)
    if m_simpson:
        diversity_metrics["simpson"] = _safe_float(m_simpson.group(1))

    # ─────────────────────────────────────────────────────────────────
    # 3. BACTÉRIES INDIVIDUELLES (48 marqueurs)
    # ─────────────────────────────────────────────────────────────────
    bacteria_individual: List[Dict[str, Any]] = []

    current_category = None
    current_group = None
    current_group_code = None

    lines = text.splitlines()

    # (plus robuste sur GutMAP : une bactérie par ligne)
    bacteria_pattern = re.compile(r"^\s*(\d{3})\s+(.+?)\s*$")

    for _, line in enumerate(lines):
        line_strip = line.strip()
        if not line_strip:
            continue

        # éviter polluer l'extraction bactéries
        if line_strip.lower().startswith("result:"):
            continue

        # Catégories (reset groupe quand on change de catégorie)
        cat_match = re.match(r"Category\s+([A-E])\.\s+(.+)", line_strip, re.IGNORECASE)
        if cat_match:
            current_category = cat_match.group(1).upper()
            current_group = None
            current_group_code = None
            continue

        # Groupes
        group_match = re.match(r"([A-E]\d)\.\s+(.+)", line_strip)
        if group_match:
            current_group_code = group_match.group(1).upper()
            current_group = group_match.group(2).strip()
            continue  # on considère que le header ne contient pas une bactérie

        # Bactérie
        m_b = bacteria_pattern.match(line_strip)
        if m_b:
            bacteria_id = m_b.group(1).strip()
            bacteria_name = re.sub(r"\s+", " ", m_b.group(2).strip())
            if len(bacteria_name) < 3:
                continue

            bacteria_individual.append(
                {
                    "id": bacteria_id,
                    "name": bacteria_name,
                    "category": current_group_code or current_category or "Unknown",
                    "group": current_group or "",
                    "abundance_level": None,
                    "status": "Unknown",
                }
            )

    # ─────────────────────────────────────────────────────────────────
    # 3bis. DÉTECTION GRAPHIQUE DES POINTS NOIRS (-3..+3)
    # ─────────────────────────────────────────────────────────────────
    try:
        dot_levels = _detect_gutmap_dot_levels(pdf_path)
    except Exception:
        dot_levels = {}

    if dot_levels and bacteria_individual:
        for b in bacteria_individual:
            bid = str(b.get("id", "")).strip()
            lvl = dot_levels.get(bid)
            if lvl is not None:
                b["abundance_level"] = int(lvl)
                b["status"] = _status_from_level(int(lvl))

    # ─────────────────────────────────────────────────────────────────
    # 4. GROUPES DE BACTÉRIES (résumé par groupe)
    # ─────────────────────────────────────────────────────────────────
    group_header = re.compile(r"(?m)^([A-Z]\d)\.\s+(.+?)\s*$")
    result_line = re.compile(
        r"Result:\s*(expected|slightly deviating|deviating)\s+abundance",
        flags=re.IGNORECASE,
    )

    bacteria_groups: List[Dict[str, Any]] = []
    current_code = None
    current_grp = None

    for ln in lines:
        ln = ln.strip()
        if not ln:
            continue

        h = group_header.match(ln)
        if h:
            current_code = h.group(1).strip()
            current_grp = f"{current_code}. {h.group(2).strip()}"
            continue

        r = result_line.search(ln)
        if r and current_code and current_grp:
            raw = r.group(1).strip().lower()
            if raw == "expected":
                res = "Expected"
            elif raw == "slightly deviating":
                res = "Slightly deviating"
            else:
                res = "Deviating"

            bacteria_groups.append({"category": current_code, "group": current_grp, "result": res})

    seen_groups = set()
    uniq_groups: List[Dict[str, Any]] = []
    for b in bacteria_groups:
        key = (b["category"], b["group"], b["result"])
        if key in seen_groups:
            continue
        seen_groups.add(key)
        uniq_groups.append(b)

    # ─────────────────────────────────────────────────────────────────
    # 4bis. ABONDANCE RÉSUMÉ PAR GROUPE (optionnel, compat UI)
    # ─────────────────────────────────────────────────────────────────
    if bacteria_individual and uniq_groups:
        levels_by_cat: Dict[str, List[int]] = {}
        for b in bacteria_individual:
            cat = str(b.get("category", "")).strip()
            lvl = b.get("abundance_level")
            if isinstance(lvl, int):
                levels_by_cat.setdefault(cat, []).append(lvl)

        for g in uniq_groups:
            cat = str(g.get("category", "")).strip()
            lvls = levels_by_cat.get(cat) or []
            if lvls:
                g["abundance"] = round(sum(lvls) / len(lvls), 2)
            else:
                g["abundance"] = ""

    # ─────────────────────────────────────────────────────────────────
    # 5. MÉTABOLITES (si disponibles dans le texte)
    # ─────────────────────────────────────────────────────────────────
    metabolites = {}

    m_but = re.search(r"Butyrate[:\s]+(\d+(?:\.\d+)?)", text, flags=re.IGNORECASE)
    if m_but:
        metabolites["butyrate"] = _safe_float(m_but.group(1))

    m_ace = re.search(r"Acetate[:\s]+(\d+(?:\.\d+)?)", text, flags=re.IGNORECASE)
    if m_ace:
        metabolites["acetate"] = _safe_float(m_ace.group(1))

    m_pro = re.search(r"Propionate[:\s]+(\d+(?:\.\d+)?)", text, flags=re.IGNORECASE)
    if m_pro:
        metabolites["propionate"] = _safe_float(m_pro.group(1))

    # ─────────────────────────────────────────────────────────────────
    # 6. ENRICHISSEMENT EXCEL (optionnel)
    # ─────────────────────────────────────────────────────────────────
    if excel_path and os.path.exists(excel_path):
        try:
            df = pd.read_excel(excel_path)
            # Extraire données supplémentaires si colonnes pertinentes présentes
            pass
        except Exception:
            pass

    return {
        "dysbiosis_index": di,
        "diversity": diversity,
        "diversity_metrics": diversity_metrics if diversity_metrics else None,
        "bacteria_individual": bacteria_individual,
        "bacteria_groups": uniq_groups,
        "metabolites": metabolites if metabolites else None,
    }


# =====================================================================
# EXTRACTION DEPUIS EXCEL (helper pour biologie si besoin)
# =====================================================================
def extract_biology_from_excel(excel_path: str) -> Dict[str, Any]:
    """
    Extraction biologie depuis Excel (format custom)
    Utiliser si disponible en complément du PDF
    """
    try:
        df = pd.read_excel(excel_path)

        col_name = None
        col_value = None
        col_unit = None
        col_ref = None

        for col in df.columns:
            col_lower = str(col).lower()
            if "biomarqueur" in col_lower or "marqueur" in col_lower or "paramètre" in col_lower:
                col_name = col
            elif "valeur" in col_lower or "résultat" in col_lower or "result" in col_lower:
                col_value = col
            elif "unité" in col_lower or "unit" in col_lower:
                col_unit = col
            elif "référence" in col_lower or "norme" in col_lower or "range" in col_lower:
                col_ref = col

        if not col_name or not col_value:
            return {}

        out = {}
        for _, row in df.iterrows():
            name = str(row.get(col_name, "")).strip()
            if not name or name.lower() == "nan":
                continue

            value_raw = row.get(col_value)
            unit = str(row.get(col_unit, "")).strip() if col_unit else ""
            ref = str(row.get(col_ref, "")).strip() if col_ref else ""

            value = _safe_float(value_raw)
            status = determine_biomarker_status(value, ref, name)

            out[name] = {"value": value, "unit": unit, "reference": ref, "status": status}

        return out

    except Exception as e:
        print(f"⚠️ Erreur extraction Excel: {e}")
        return {}


# =====================================================================
# HELPERS - CONVERSION POUR LE PDF/UI
# =====================================================================
def biology_dict_to_list(biology: Dict[str, Any], default_category: str = "Autres") -> List[Dict[str, Any]]:
    """Convertit le dict {name: {value,unit,reference,status}} en liste [{name,...}] utilisable par le PDF/UI."""
    out: List[Dict[str, Any]] = []
    for name, d in (biology or {}).items():
        if not isinstance(d, dict):
            continue
        out.append(
            {
                "name": str(d.get("name", name)).strip(),
                "value": d.get("value"),
                "unit": str(d.get("unit", "")).strip(),
                "reference": str(d.get("reference", "")).strip(),
                "status": str(d.get("status", "Inconnu")).strip(),
                "category": str(d.get("category", default_category)).strip() or default_category,
            }
        )
    return out


# =====================================================================
# MAIN EXTRACTION ORCHESTRATOR
# =====================================================================
def extract_all_data(
    bio_pdf_path: Optional[str] = None,
    bio_excel_path: Optional[str] = None,
    micro_pdf_path: Optional[str] = None,
    micro_excel_path: Optional[str] = None,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Extraction orchestrée de toutes les données disponibles

    Returns:
        (biology_dict, microbiome_dict)
    """
    biology = {}
    microbiome = {}

    if bio_pdf_path:
        biology.update(extract_synlab_biology(bio_pdf_path))

    if bio_excel_path:
        biology.update(extract_biology_from_excel(bio_excel_path))

    if micro_pdf_path:
        microbiome = extract_idk_microbiome(micro_pdf_path, micro_excel_path)

    return biology, microbiome


# =====================================================================
# SCRIPT DE TEST
# =====================================================================
if __name__ == "__main__":
    import json

    print("=" * 80)
    print("🧪 TEST EXTRACTION MICROBIOTE GUTMAP")
    print("=" * 80)

    pdf_path = "/mnt/user-data/uploads/IDK_GutMAP_Sample_report_DI-1_EN.pdf"

    if os.path.exists(pdf_path):
        print(f"\n📄 Extraction depuis: {pdf_path}")

        result = extract_idk_microbiome(pdf_path)

        print(f"\n📊 RÉSULTATS:")
        print(f"  • Dysbiosis Index: {result['dysbiosis_index']}")
        print(f"  • Diversity: {result['diversity']}")
        print(f"  • Bactéries individuelles extraites: {len(result['bacteria_individual'])}")
        print(f"  • Groupes bactériens: {len(result['bacteria_groups'])}")

        # Stats sur détection points
        detected = sum(1 for b in result["bacteria_individual"] if isinstance(b.get("abundance_level"), int))
        print(f"  • Points détectés (abundance_level renseigné): {detected}")

        if result["bacteria_individual"]:
            print(f"\n🦠 Exemples de bactéries extraites (5 premières):")
            for i, bact in enumerate(result["bacteria_individual"][:5], 1):
                print(f"  {i}. {bact['id']} - {bact['name']}")
                print(f"     Catégorie: {bact['category']}")
                print(f"     Niveau: {bact['abundance_level']} ({bact['status']})")

        output_json = "/mnt/user-data/outputs/microbiome_extracted.json"
        with open(output_json, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        print(f"\n💾 Résultats complets sauvegardés: {output_json}")
    else:
        print(f"\n❌ Fichier non trouvé: {pdf_path}")
