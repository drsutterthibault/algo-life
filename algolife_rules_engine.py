import os
import re
import pandas as pd

def _normalize_key(name: str) -> str:
    if not name:
        return ""
    key = name.lower()
    key = re.sub(r"[àâä]", "a", key)
    key = re.sub(r"[éèêë]", "e", key)
    key = re.sub(r"[îï]", "i", key)
    key = re.sub(r"[ôö]", "o", key)
    key = re.sub(r"[ùûü]", "u", key)
    key = re.sub(r"[ç]", "c", key)
    key = re.sub(r"[^a-z0-9]+", "_", key)
    key = re.sub(r"_+", "_", key).strip("_")
    return key

def _safe_float(x):
    try:
        return float(str(x).replace(",", "."))
    except Exception:
        return None

def _parse_norms_cell(cell: str):
    """
    Supporte:
      "13.5–17.5"
      "4.0–10.0 G/L"
      "12-16"
      "30 à 100"
    Retour: (low, high)
    """
    if cell is None:
        return (None, None)
    s = str(cell).strip()
    if not s:
        return (None, None)

    # uniformiser les tirets et "à"
    s = s.replace("−", "-").replace("–", "-").replace("à", "-")
    s = s.replace(",", ".")
    # enlever unités collées
    s = re.sub(r"[A-Za-zµμ/%°]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()

    m = re.search(r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)", s)
    if not m:
        return (None, None)

    low = _safe_float(m.group(1))
    high = _safe_float(m.group(2))
    if low is None or high is None:
        return (None, None)
    if low > high:
        low, high = high, low
    return (low, high)

def load_rules_from_excel(excel_path: str):
    df = pd.read_excel(excel_path)

    required_cols = [
        "Biomarqueur", "Unité", "Normes H", "Normes F",
        "BASSE - Interprétation", "BASSE - Nutrition", "BASSE - Micronutrition", "BASSE - Lifestyle",
        "HAUTE - Interprétation", "HAUTE - Nutrition", "HAUTE - Micronutrition", "HAUTE - Lifestyle",
    ]
    for c in required_cols:
        if c not in df.columns:
            raise ValueError(f"Colonne manquante dans Excel: {c}")

    rules = {}
    for _, row in df.iterrows():
        biom_name = str(row.get("Biomarqueur", "")).strip()
        if not biom_name:
            continue
        key = _normalize_key(biom_name)

        unit = str(row.get("Unité", "")).strip()
        low_h, high_h = _parse_norms_cell(row.get("Normes H"))
        low_f, high_f = _parse_norms_cell(row.get("Normes F"))

        rules[key] = {
            "name": biom_name,
            "unit": unit,
            "norms": {
                "Masculin": (low_h, high_h),
                "Féminin": (low_f, high_f),
                "default": (low_h or low_f, high_h or high_f),
            },
            "low": {
                "interpretation": row.get("BASSE - Interprétation", ""),
                "nutrition": row.get("BASSE - Nutrition", ""),
                "micronutrition": row.get("BASSE - Micronutrition", ""),
                "lifestyle": row.get("BASSE - Lifestyle", ""),
            },
            "high": {
                "interpretation": row.get("HAUTE - Interprétation", ""),
                "nutrition": row.get("HAUTE - Nutrition", ""),
                "micronutrition": row.get("HAUTE - Micronutrition", ""),
                "lifestyle": row.get("HAUTE - Lifestyle", ""),
            }
        }
    return rules

def apply_rules(extracted_biomarkers: dict, patient_sexe: str, rules_by_key: dict):
    """
    extracted_biomarkers: dict du type:
      - soit {"ferritine": 22, "crp": 1.2}
      - soit ton all_data: {key: {"value":..., "name":...}}
    Retour: objet recommendations prêt pour PDF
    """
    sexe = patient_sexe if patient_sexe in ("Masculin", "Féminin") else "default"

    results = {
        "priorities": [],
        "recommendations": {
            "supplements": [],
            "alimentation": [],
            "lifestyle": [],
            "interpretation": [],
        }
    }

    # harmoniser input
    items = []
    for k, v in (extracted_biomarkers or {}).items():
        if isinstance(v, dict):
            val = v.get("value")
            name = v.get("name", k)
            key = _normalize_key(v.get("canonical_key") or k)
        else:
            val = v
            name = k
            key = _normalize_key(k)
        val = _safe_float(val)
        if val is None:
            continue
        items.append((key, name, val))

    for key, name, val in items:
        rule = rules_by_key.get(key)
        if not rule:
            continue

        low, high = rule["norms"].get(sexe, rule["norms"]["default"])
        if low is None or high is None:
            continue

        if val < low:
            bucket = "low"
            prio_score = (low - val) / (low if low else 1.0)
        elif val > high:
            bucket = "high"
            prio_score = (val - high) / (high if high else 1.0)
        else:
            # normal -> rien à pousser en reco “corrective”
            continue

        # priorités (triables ensuite)
        results["priorities"].append({
            "biomarker": key,
            "display_name": rule["name"],
            "value": val,
            "unit": rule["unit"],
            "status": bucket,
            "priority_score": float(prio_score),
        })

        # injecte recommandations (split lignes si multi)
        block = rule[bucket]
        if block.get("interpretation"):
            results["recommendations"]["interpretation"] += [x.strip() for x in str(block["interpretation"]).split("\n") if x.strip()]
        if block.get("nutrition"):
            results["recommendations"]["alimentation"] += [x.strip() for x in str(block["nutrition"]).split("\n") if x.strip()]
        if block.get("micronutrition"):
            results["recommendations"]["supplements"] += [x.strip() for x in str(block["micronutrition"]).split("\n") if x.strip()]
        if block.get("lifestyle"):
            results["recommendations"]["lifestyle"] += [x.strip() for x in str(block["lifestyle"]).split("\n") if x.strip()]

    # tri des priorités (top N)
    results["priorities"].sort(key=lambda x: x["priority_score"], reverse=True)
    results["priorities"] = results["priorities"][:8]

    # dédoublonnage simple (conserve ordre)
    for k in ("supplements", "alimentation", "lifestyle", "interpretation"):
        seen = set()
        new = []
        for item in results["recommendations"][k]:
            s = str(item).strip()
            if not s or s in seen:
                continue
            seen.add(s)
            new.append(s)
        results["recommendations"][k] = new[:20]

    return results

def build_rules_engine():
    base_dir = os.path.dirname(__file__)
    excel_path = os.path.join(base_dir, "data", "BASE_BIOMARQUEURS_SYNLAB_FINAL.xlsx")
    return load_rules_from_excel(excel_path)
