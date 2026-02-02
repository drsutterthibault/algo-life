"""
ALGO-LIFE - Minimal Clean App (Bio + Microbiote)
Import PDF + Excel (pas uniquement PDF)
Extraction multimodale + recommandations via règles Excel

Auteur: Dr Thibault SUTTER, PhD
Version: Clean reboot - Feb 2026
"""

from __future__ import annotations

import io
from dataclasses import asdict
from typing import Optional, Dict, Any, Tuple, List

import pandas as pd
import streamlit as st

from extractors import (
    extract_biology_any,
    extract_microbiome_any,
    ExtractionResult,
)
from rules_engine import (
    load_rules_from_excel_bytes,
    generate_recommendations_multimodal,
)

# -----------------------------
# Streamlit config
# -----------------------------
st.set_page_config(
    page_title="ALGO-LIFE (Clean) - Bio + Microbiote",
    layout="wide",
)

st.title("ALGO-LIFE — Import multimodal (Biologie + Microbiote)")
st.caption("Importe un fichier Biologie (PDF ou Excel) + un fichier Microbiote (PDF ou Excel), applique les règles Excel, et génère des recommandations.")

# -----------------------------
# Helpers
# -----------------------------
def _read_upload(upload) -> Tuple[bytes, str]:
    if upload is None:
        return b"", ""
    return upload.read(), upload.name

def _download_json_button(label: str, payload: Dict[str, Any], filename: str):
    import json
    raw = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    st.download_button(label, data=raw, file_name=filename, mime="application/json")

def _download_csv_button(label: str, df: pd.DataFrame, filename: str):
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(label, data=csv, file_name=filename, mime="text/csv")

# -----------------------------
# Sidebar: global inputs
# -----------------------------
with st.sidebar:
    st.header("Paramètres")
    sex = st.selectbox("Sexe (pour normes H/F)", ["F", "H"], index=0)
    st.markdown("---")
    st.subheader("Règles (Excel)")
    rules_upload = st.file_uploader(
        "Importer le fichier de règles (.xlsx)",
        type=["xlsx"],
        accept_multiple_files=False,
    )
    st.caption("Astuce: utilise ton fichier 'Bases règles Synlab.xlsx'.")

# -----------------------------
# Main: uploads
# -----------------------------
col1, col2 = st.columns(2)

with col1:
    st.subheader("1) Fichier Biologie")
    bio_upload = st.file_uploader(
        "PDF ou Excel (biologie)",
        type=["pdf", "xlsx", "xls", "csv"],
        accept_multiple_files=False,
        key="bio_file",
    )

with col2:
    st.subheader("2) Fichier Microbiote")
    micro_upload = st.file_uploader(
        "PDF ou Excel (microbiote)",
        type=["pdf", "xlsx", "xls", "csv"],
        accept_multiple_files=False,
        key="micro_file",
    )

st.markdown("---")

# -----------------------------
# Run button
# -----------------------------
run = st.button("🚀 Extraire + Générer les recommandations", type="primary")

if run:
    if rules_upload is None:
        st.error("Tu dois importer le fichier de règles Excel (.xlsx).")
        st.stop()
    if bio_upload is None and micro_upload is None:
        st.error("Importe au moins un fichier (biologie ou microbiote).")
        st.stop()

    # Read rules
    rules_bytes, rules_name = _read_upload(rules_upload)
    try:
        rules = load_rules_from_excel_bytes(rules_bytes)
    except Exception as e:
        st.exception(e)
        st.stop()

    bio_res: Optional[ExtractionResult] = None
    micro_res: Optional[ExtractionResult] = None

    # Extract bio
    if bio_upload is not None:
        bio_bytes, bio_name = _read_upload(bio_upload)
        try:
            bio_res = extract_biology_any(bio_bytes, bio_name)
        except Exception as e:
            st.error("Erreur extraction Biologie")
            st.exception(e)
            st.stop()

    # Extract microbiome
    if micro_upload is not None:
        micro_bytes, micro_name = _read_upload(micro_upload)
        try:
            micro_res = extract_microbiome_any(micro_bytes, micro_name)
        except Exception as e:
            st.error("Erreur extraction Microbiote")
            st.exception(e)
            st.stop()

    # Display extractions
    st.subheader("Extraction — Résultats structurés")

    cA, cB = st.columns(2)
    with cA:
        st.markdown("### Biologie")
        if bio_res is None or bio_res.data is None or bio_res.data.empty:
            st.info("Aucun biomarqueur extrait.")
        else:
            st.dataframe(bio_res.data, use_container_width=True, height=420)
            _download_csv_button("⬇️ Télécharger extraction bio (CSV)", bio_res.data, "extraction_bio.csv")

    with cB:
        st.markdown("### Microbiote")
        if micro_res is None:
            st.info("Aucun fichier microbiote importé.")
        else:
            if micro_res.data is not None and not micro_res.data.empty:
                st.dataframe(micro_res.data, use_container_width=True, height=420)
                _download_csv_button("⬇️ Télécharger extraction microbiote (CSV)", micro_res.data, "extraction_microbiote.csv")
            else:
                st.info("Extraction microbiote: pas de table bactérienne exploitable, mais les marqueurs fonctionnels peuvent être présents.")
            if micro_res.meta:
                st.markdown("**Marqueurs fonctionnels détectés**")
                st.json(micro_res.meta)

    st.markdown("---")

    # Generate recos
    st.subheader("Recommandations — moteur de règles multimodal")
    recos = generate_recommendations_multimodal(
        rules=rules,
        sex=sex,
        bio_df=(bio_res.data if bio_res else pd.DataFrame()),
        micro_meta=(micro_res.meta if micro_res else {}),
        micro_df=(micro_res.data if (micro_res and micro_res.data is not None) else pd.DataFrame()),
    )

    # Render recos
    if not recos:
        st.info("Aucune recommandation déclenchée (soit tout est normal, soit matching règles ↔ biomarqueurs à ajuster).")
    else:
        for i, r in enumerate(recos, start=1):
            with st.expander(f"#{i} — {r.get('title','Reco')}", expanded=(i <= 3)):
                st.write(f"**Modalité :** {r.get('modality')}")
                st.write(f"**Biomarqueur / Marqueur :** {r.get('marker')}")
                st.write(f"**Statut :** {r.get('status')}")
                st.write(f"**Sévérité :** {r.get('severity')}")
                st.markdown("**Interprétation**")
                st.write(r.get("interpretation", ""))
                st.markdown("**Nutrition**")
                st.write(r.get("nutrition", ""))
                st.markdown("**Micronutrition / Supplementation**")
                st.write(r.get("supplementation", ""))
                st.markdown("**Lifestyle**")
                st.write(r.get("lifestyle", ""))
                if r.get("notes"):
                    st.markdown("**Notes**")
                    st.write(r.get("notes"))

    # Downloads
    st.markdown("---")
    payload = {
        "rules_file": rules_name,
        "sex": sex,
        "bio_extraction": (bio_res.data.to_dict(orient="records") if (bio_res and bio_res.data is not None) else []),
        "micro_meta": (micro_res.meta if micro_res else {}),
        "micro_extraction": (micro_res.data.to_dict(orient="records") if (micro_res and micro_res.data is not None) else []),
        "recommendations": recos,
    }
    _download_json_button("⬇️ Télécharger (JSON complet)", payload, "algolife_multimodal_output.json")
