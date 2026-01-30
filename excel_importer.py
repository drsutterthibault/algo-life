from __future__ import annotations
import pandas as pd

REQUIRED_COLUMNS = ["biomarker", "value", "unit", "ref_low", "ref_high", "sample_date"]

def load_biomarkers_excel_path(excel_path: str) -> tuple[pd.DataFrame, list[str]]:
    errors: list[str] = []
    try:
        xls = pd.ExcelFile(excel_path)
        sheet = "raw" if "raw" in xls.sheet_names else xls.sheet_names[0]
        df = pd.read_excel(xls, sheet_name=sheet)
    except Exception as e:
        return pd.DataFrame(), [f"Impossible de lire l'Excel : {e}"]

    df.columns = [str(c).strip() for c in df.columns]
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        return pd.DataFrame(), [
            f"Colonnes manquantes : {', '.join(missing)}. Requis : {', '.join(REQUIRED_COLUMNS)}"
        ]

    df = df[REQUIRED_COLUMNS].copy().dropna(how="all")
    df["biomarker"] = df["biomarker"].astype(str).str.strip()

    for col in ["value", "ref_low", "ref_high"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["sample_date"] = df["sample_date"].astype(str).str.strip()

    if df["biomarker"].eq("").any():
        errors.append("Au moins une ligne a un biomarqueur vide.")
    if df["value"].isna().any():
        errors.append("Au moins une ligne a une valeur non numérique/manquante (value).")

    return df, errors
