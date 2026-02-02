"""
ALGO-LIFE - App minimale (RESET)
- Import Biologie & Microbiote: PDF ou Excel
- Extraction robuste (bio + micro)
- Recommandations via règles multimodales (Bases rèlgles Synlab.xlsx)

Auteur: Dr Thibault SUTTER
"""

from __future__ import annotations

import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Dict, Any, Optional

from extractors import (
    extract_biology_from_file,
    extract_microbiome_from_file,
)
from rules_engine_multimodal import (
    MultimodalRulesEngine,
)

# =========================
# Streamlit config
# =========================
st.set_page_config(
    page_title="ALGO-LIFE | RESET",
    page_icon="🧬",
    layout="wide",
)

st.title("🧬 ALGO-LIFE — Reset GitHub (Import PDF + Excel)")
st.caption("Biologie + Microbiote → Extraction → Recommandations via règles (multimodal)")

# =========================
# Session state
# =========================
def _init_state():
    if "bio" not in st.session_state:
        st.session_state.bio = {}
    if "micro" not in st.session_state:
        st.session_state.micro = {}
    if "patient" not in st.session_state:
        st.session_state.patient = {"age": 45, "sex": "H"}  # H/F
    if "reco" not in st.session_state:
        st.session_state.reco = None
    if "rules_ready" not in st.session_state:
        st.session_state.rules_ready = False

_init_state()

# =========================
# Sidebar patient + rules
# =========================
with st.sidebar:
    st.header("👤 Patient (minimal)")
    st.session_state.patient["age"] = st.number_input("Âge", min_value=1, max_value=120, value=int(st.session_state.patient["age"]))
    st.session_state.patient["sex"] = st.selectbox("Sexe", ["H", "F"], index=0 if st.session_state.patient["sex"] == "H" else 1)

    st.divider()
    st.header("📚 Règles")
    st.caption("Option 1: uploader ton xlsx. Option 2: chemin local (ex: data/Bases rèlgles Synlab.xlsx)")

    rules_upload = st.file_uploader(
        "Fichier règles (Bases rèlgles Synlab.xlsx)",
        type=["xlsx"],
        accept_multiple_files=False,
        key="rules_xlsx",
    )

    default_rules_path = st.text_input(
        "Chemin local (si pas d'upload)",
        value="Bases rèlgles Synlab.xlsx",
        help="Si tu mets le fichier dans /data, mets: data/Bases rèlgles Synlab.xlsx",
    )

    st.session_state.rules_source = {"upload": rules_upload, "path": default_rules_path}

    st.divider()
    if st.button("🧹 Reset (vider extraction + reco)", use_container_width=True):
        st.session_state.bio = {}
        st.session_state.micro = {}
        st.session_state.reco = None
        st.success("Reset OK ✅")

# =========================
# Helpers
# =========================
def _pretty_df(d: Dict[str, Any], col_name: str) -> pd.DataFrame:
    if not d:
        return pd.DataFrame(columns=[col_name, "Valeur"])
    return pd.DataFrame([{col_name: k, "Valeur": v} for k, v in d.items()]).sort_values(col_name)

def _load_rules_engine() -> Optional[MultimodalRulesEngine]:
    src = st.session_state.rules_source
    try:
        if src["upload"] is not None:
            engine = MultimodalRulesEngine.from_uploaded_xlsx(src["upload"])
        else:
            engine = MultimodalRulesEngine.from_path(src["path"])
        st.session_state.rules_ready = True
        return engine
    except Exception as e:
        st.session_state.rules_ready = False
        st.error(f"❌ Impossible de charger les règles: {e}")
        return None

# =========================
# Layout
# =========================
tab1, tab2, tab3 = st.tabs(["📥 Import & Extraction", "🧾 Recommandations", "🛠️ Debug"])

# =========================
# TAB 1 - Import
# =========================
with tab1:
    st.subheader("📥 Import Biologie + Microbiote (PDF ou Excel)")

    c1, c2 = st.columns(2)

    with c1:
        st.markdown("### 🧪 Biologie")
        bio_file = st.file_uploader(
            "Import biologie",
            type=["pdf", "xlsx", "xls", "csv"],
            key="bio_file",
            help="PDF résultats labo OU Excel/CSV (2 colonnes: biomarqueur/valeur).",
        )
        if st.button("🔍 Extraire biologie", use_container_width=True):
            if bio_file is None:
                st.warning("Ajoute un fichier biologie.")
            else:
                with st.spinner("Extraction biologie..."):
                    bio = extract_biology_from_file(bio_file)
                    st.session_state.bio = bio
                st.success(f"✅ Biologie: {len(st.session_state.bio)} marqueurs extraits")

        st.dataframe(_pretty_df(st.session_state.bio, "Biomarqueur"), use_container_width=True, height=380)

    with c2:
        st.markdown("### 🦠 Microbiote")
        micro_file = st.file_uploader(
            "Import microbiote",
            type=["pdf", "xlsx", "xls", "csv"],
            key="micro_file",
            help="PDF microbiote OU Excel/CSV (2 colonnes: marqueur/valeur).",
        )
        if st.button("🔍 Extraire microbiote", use_container_width=True):
            if micro_file is None:
                st.warning("Ajoute un fichier microbiote.")
            else:
                with st.spinner("Extraction microbiote..."):
                    micro = extract_microbiome_from_file(micro_file)
                    st.session_state.micro = micro
                st.success(f"✅ Microbiote: {len(st.session_state.micro)} marqueurs extraits")

        st.dataframe(_pretty_df(st.session_state.micro, "Marqueur"), use_container_width=True, height=380)

    st.divider()
    st.markdown("### 🚀 Lancer recommandations (multimodal)")
    if st.button("⚡ Générer recommandations via règles", type="primary", use_container_width=True):
        if not st.session_state.bio and not st.session_state.micro:
            st.error("Il faut au moins une extraction (biologie ou microbiote).")
        else:
            engine = _load_rules_engine()
            if engine is None:
                st.stop()

            with st.spinner("Application des règles..."):
                reco = engine.run(
                    biology=st.session_state.bio,
                    microbiome=st.session_state.micro,
                    sex=st.session_state.patient["sex"],
                )
                st.session_state.reco = reco

            st.success("✅ Recommandations générées")

# =========================
# TAB 2 - Reco
# =========================
with tab2:
    st.subheader("🧾 Recommandations (issues du fichier de règles)")

    if not st.session_state.reco:
        st.info("Aucune recommandation pour l'instant. Va dans l'onglet Import & Extraction → Générer.")
    else:
        reco = st.session_state.reco

        colA, colB, colC = st.columns(3)
        colA.metric("Biologie (hits)", reco["summary"]["biology_hits"])
        colB.metric("Microbiote (hits)", reco["summary"]["microbiome_hits"])
        colC.metric("Total (hits)", reco["summary"]["total_hits"])

        st.divider()

        st.markdown("### 🎯 Priorités (top)")
        if reco["priorities"]:
            st.dataframe(pd.DataFrame(reco["priorities"]), use_container_width=True, height=260)
        else:
            st.info("Pas de priorités détectées.")

        st.divider()

        st.markdown("### 🧪 Détails Biologie")
        if reco["biology_hits"]:
            st.dataframe(pd.DataFrame(reco["biology_hits"]), use_container_width=True, height=360)
        else:
            st.info("Aucun hit biologie.")

        st.markdown("### 🦠 Détails Microbiote")
        if reco["microbiome_hits"]:
            st.dataframe(pd.DataFrame(reco["microbiome_hits"]), use_container_width=True, height=360)
        else:
            st.info("Aucun hit microbiote.")

# =========================
# TAB 3 - Debug
# =========================
with tab3:
    st.subheader("🛠️ Debug")
    st.write("Horodatage:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    st.write("Bio keys sample:", list(st.session_state.bio.keys())[:30])
    st.write("Micro keys sample:", list(st.session_state.micro.keys())[:30])

    st.markdown("### Reco brute (JSON)")
    st.json(st.session_state.reco or {})
