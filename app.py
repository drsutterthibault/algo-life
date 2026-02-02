"""
ALGO-LIFE - Minimal Clean App (Bio + Microbiote)
DEBUG MODE: no import wrappers (shows real error)
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

# IMPORTANT: no try/except here -> you'll see the REAL error directly
from extractors import extract_biology_any, extract_microbiome_any, ExtractionResult
from rules_engine import load_rules_from_excel_bytes, generate_recommendations_multimodal


st.set_page_config(page_title="ALGO-LIFE (Clean) - Bio + Microbiote", layout="wide")

st.title("ALGO-LIFE — Import multimodal (Biologie + Microbiote)")

with st.sidebar:
    sex = st.selectbox("Sexe (pour normes H/F)", ["F", "H"], index=0)
    rules_upload = st.file_uploader("Fichier de règles (.xlsx)", type=["xlsx"], accept_multiple_files=False)

c1, c2 = st.columns(2)
with c1:
    bio_upload = st.file_uploader("Biologie (PDF ou Excel)", type=["pdf", "xlsx", "xls", "csv"], key="bio")
with c2:
    micro_upload = st.file_uploader("Microbiote (PDF ou Excel)", type=["pdf", "xlsx", "xls", "csv"], key="micro")

run = st.button("🚀 Extraire + Reco", type="primary")

def read_upload(u):
    return u.read(), u.name

if run:
    if rules_upload is None:
        st.error("Importe le fichier de règles .xlsx")
        st.stop()

    rules_bytes, _ = read_upload(rules_upload)
    rules = load_rules_from_excel_bytes(rules_bytes)

    bio_df = pd.DataFrame()
    micro_df = pd.DataFrame()
    micro_meta = {}

    if bio_upload is not None:
        b, name = read_upload(bio_upload)
        bio_res = extract_biology_any(b, name)
        bio_df = bio_res.data

    if micro_upload is not None:
        b, name = read_upload(micro_upload)
        micro_res = extract_microbiome_any(b, name)
        micro_df = micro_res.data
        micro_meta = micro_res.meta

    st.subheader("Extraction")
    st.write("### Biologie")
    st.dataframe(bio_df, use_container_width=True)

    st.write("### Microbiote")
    st.dataframe(micro_df, use_container_width=True)
    if micro_meta:
        st.json(micro_meta)

    st.subheader("Recommandations")
    recos = generate_recommendations_multimodal(
        rules=rules,
        sex=sex,
        bio_df=bio_df,
        micro_meta=micro_meta,
        micro_df=micro_df,
    )

    if not recos:
        st.info("Aucune reco déclenchée.")
    else:
        for r in recos:
            st.markdown(f"### {r.get('title','Reco')}")
            st.write(r)
