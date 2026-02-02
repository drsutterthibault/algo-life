"""
ALGO-LIFE - Minimal Clean App (Bio + Microbiote)
Robust mode: accepte extractors qui renvoient ExtractionResult, tuple(df,meta), dict, ou df.
"""

from __future__ import annotations

from typing import Any, Dict, Tuple
import pandas as pd
import streamlit as st

from extractors import extract_biology_any, extract_microbiome_any
from rules_engine import load_rules_from_excel_bytes, generate_recommendations_multimodal


st.set_page_config(page_title="ALGO-LIFE (Clean) - Bio + Microbiote", layout="wide")
st.title("ALGO-LIFE — Import multimodal (Biologie + Microbiote)")

# -----------------------------
# Helpers
# -----------------------------
def read_upload(u) -> Tuple[bytes, str]:
    return u.read(), u.name

def coerce_extraction(res: Any) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Rend l'app compatible avec différentes formes de retour:
    - ExtractionResult: .data + .meta
    - tuple: (df, meta) ou (df,) etc.
    - dict: {"data": df, "meta": {...}} ou {"df":..., "meta":...}
    - pd.DataFrame: df
    """
    if res is None:
        return pd.DataFrame(), {}

    # Case 1: ExtractionResult-like object
    if hasattr(res, "data"):
        df = getattr(res, "data", None)
        meta = getattr(res, "meta", {}) or {}
        if isinstance(df, pd.DataFrame):
            return df, meta
        # si .data existe mais pas DF, fallback
        return pd.DataFrame(df) if df is not None else pd.DataFrame(), meta

    # Case 2: tuple
    if isinstance(res, tuple):
        if len(res) == 0:
            return pd.DataFrame(), {}
        if len(res) == 1:
            return (res[0] if isinstance(res[0], pd.DataFrame) else pd.DataFrame(res[0])), {}
        # len >=2
        df = res[0] if isinstance(res[0], pd.DataFrame) else pd.DataFrame(res[0])
        meta = res[1] if isinstance(res[1], dict) else {}
        return df, meta

    # Case 3: dict
    if isinstance(res, dict):
        df = res.get("data", None) or res.get("df", None) or res.get("table", None)
        meta = res.get("meta", {}) or {}
        if isinstance(df, pd.DataFrame):
            return df, meta
        if df is None:
            return pd.DataFrame(), meta
        return pd.DataFrame(df), meta

    # Case 4: DataFrame
    if isinstance(res, pd.DataFrame):
        return res, {}

    # Fallback
    return pd.DataFrame(), {"warning": f"Type extraction non supporté: {type(res)}"}


# -----------------------------
# Sidebar
# -----------------------------
with st.sidebar:
    sex = st.selectbox("Sexe (pour normes H/F)", ["F", "H"], index=0)
    rules_upload = st.file_uploader("Fichier de règles (.xlsx)", type=["xlsx"], accept_multiple_files=False)

c1, c2 = st.columns(2)
with c1:
    bio_upload = st.file_uploader("Biologie (PDF ou Excel)", type=["pdf", "xlsx", "xls", "csv"], key="bio")
with c2:
    micro_upload = st.file_uploader("Microbiote (PDF ou Excel)", type=["pdf", "xlsx", "xls", "csv"], key="micro")

run = st.button("🚀 Extraire + Reco", type="primary")

if run:
    if rules_upload is None:
        st.error("Importe le fichier de règles .xlsx")
        st.stop()

    # Load rules
    rules_bytes, _ = read_upload(rules_upload)
    try:
        rules = load_rules_from_excel_bytes(rules_bytes)
    except Exception as e:
        st.error("Erreur chargement règles")
        st.exception(e)
        st.stop()

    # Extract bio
    bio_df = pd.DataFrame()
    bio_meta: Dict[str, Any] = {}
    if bio_upload is not None:
        b, name = read_upload(bio_upload)
        try:
            bio_res = extract_biology_any(b, name)
            bio_df, bio_meta = coerce_extraction(bio_res)
        except Exception as e:
            st.error("Erreur extraction Biologie")
            st.exception(e)
            st.stop()

    # Extract microbiome
    micro_df = pd.DataFrame()
    micro_meta: Dict[str, Any] = {}
    if micro_upload is not None:
        b, name = read_upload(micro_upload)
        try:
            micro_res = extract_microbiome_any(b, name)
            micro_df, micro_meta = coerce_extraction(micro_res)
        except Exception as e:
            st.error("Erreur extraction Microbiote")
            st.exception(e)
            st.stop()

    # Display
    st.subheader("Extraction")

    st.write("### Biologie")
    if bio_df.empty:
        st.info("Aucune donnée bio extraite.")
    else:
        st.dataframe(bio_df, use_container_width=True, height=420)
    if bio_meta:
        st.caption("Meta bio")
        st.json(bio_meta)

    st.write("### Microbiote")
    if micro_df.empty:
        st.info("Aucune donnée microbiote extraite (table vide).")
    else:
        st.dataframe(micro_df, use_container_width=True, height=420)
    if micro_meta:
        st.caption("Meta microbiote")
        st.json(micro_meta)

    # Recos
    st.subheader("Recommandations")
    try:
        recos = generate_recommendations_multimodal(
            rules=rules,
            sex=sex,
            bio_df=bio_df,
            micro_meta=micro_meta,
            micro_df=micro_df,
        )
    except Exception as e:
        st.error("Erreur moteur de règles")
        st.exception(e)
        st.stop()

    if not recos:
        st.info("Aucune reco déclenchée.")
    else:
        for i, r in enumerate(recos, start=1):
            with st.expander(f"#{i} — {r.get('title','Reco')}", expanded=(i <= 3)):
                st.write(r)
