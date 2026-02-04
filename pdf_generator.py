# pdf_generator.py
# -*- coding: utf-8 -*-
"""
ALGO-LIFE / UNILABS - PDF Generator v4.1 (Premium Multimodal)
✅ Patch biologie (clés FR + accents) : Biomarqueur/Valeur/Unité/Référence/Statut/Catégorie
✅ Header premium + Logo ADN futuriste vectoriel (pas d'image requise)
✅ Tableau Microbiote sous Biologie
✅ Analyses croisées Biologie × Microbiote
✅ Recommandations segmentées : Biologie / Microbiote / Croisées
✅ COMPAT: generate_multimodal_report(payload) ET generate_multimodal_report(patient_data=..., biology_data=...)
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    Flowable,
    KeepTogether,
)
from reportlab.graphics.shapes import Drawing, Rect, Line, Circle, String


# ---------------------------------------------------------------------
# Utils
# ---------------------------------------------------------------------
def _clean_str(x: Any) -> str:
    if x is None:
        return ""
    return str(x).strip()


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        if isinstance(x, (int, float)):
            return float(x)
        s = str(x).strip().replace(",", ".")
        if s == "":
            return default
        return float(s)
    except Exception:
        return default


def _k(s: str) -> str:
    return str(s or "").strip().lower()


def _get_first(d: Dict[str, Any], keys: List[str], default: Any = None) -> Any:
    if not isinstance(d, dict):
        return default
    lkmap = {_k(k): k for k in d.keys()}
    for kk in keys:
        if _k(kk) in lkmap:
            return d.get(lkmap[_k(kk)], default)
    return default


def _normalize_status(raw: Any) -> str:
    s = _clean_str(raw).lower()
    if not s:
        return "Inconnu"

    if s in {"normal", "within range", "within", "ok", "as expected", "dans la norme"}:
        return "Normal"

    if any(w in s for w in ["surve", "border", "limite", "slight", "mild", "modéré", "watch", "à surve"]):
        return "À surveiller"

    if any(w in s for w in ["anormal", "abnormal", "high", "low", "haut", "élev", "bas", "faible", "deviat"]):
        return "Anormal"

    return _clean_str(raw) or "Inconnu"


def _status_color(status: str):
    s = _normalize_status(status)
    if s == "Normal":
        return colors.HexColor("#10B981")
    if s == "À surveiller":
        return colors.HexColor("#F59E0B")
    if s == "Anormal":
        return colors.HexColor("#EF4444")
    return colors.HexColor("#6B7280")


# ---------------------------------------------------------------------
# PATCH BIOLOGIE (clés FR/EN)
# ---------------------------------------------------------------------
def normalize_biology_data(biology: Any) -> List[Dict[str, Any]]:
    """
    Accepts:
      - list[dict] from df.to_dict('records') with FR keys (majuscule + accents)
      - list[dict] with EN keys
      - dict mapping { biomarker_name: {value/unit/reference/status} }

    Returns list of normalized dict:
      name, value, unit, reference, status, category
    """
    out: List[Dict[str, Any]] = []
    if biology is None:
        return out

    if isinstance(biology, dict):
        inner = _get_first(biology, ["biology", "biomarkers", "markers"], None)
        if inner is not None:
            return normalize_biology_data(inner)

        for name, v in biology.items():
            if isinstance(v, dict):
                nm = _clean_str(_get_first(v, ["name", "biomarker", "marqueur"], name) or name)
                val = _get_first(v, ["value", "valeur", "result", "résultat", "resultat"], None)
                unit = _get_first(v, ["unit", "unité", "unite"], "")
                ref = _get_first(v, ["reference", "référence", "reference_range", "norme", "ref"], "")
                stt = _get_first(v, ["status", "statut", "flag", "interpretation", "interprétation"], "")
                cat = _get_first(v, ["category", "catégorie", "categorie", "famille", "panel"], "")
            else:
                nm = _clean_str(name)
                val = v
                unit, ref, stt, cat = "", "", "", ""

            if nm:
                out.append(
                    dict(
                        name=nm,
                        value=val,
                        unit=_clean_str(unit),
                        reference=_clean_str(ref),
                        status=_normalize_status(stt),
                        category=_clean_str(cat),
                    )
                )
        return out

    if isinstance(biology, list):
        for row in biology:
            if not isinstance(row, dict):
                continue

            # EN
            name = _get_first(row, ["name", "biomarker", "marker"], "")
            value = _get_first(row, ["value", "result"], None)
            unit = _get_first(row, ["unit", "units"], "")
            ref = _get_first(row, ["reference", "ref", "range", "reference_range"], "")
            stt = _get_first(row, ["status", "flag"], "")
            cat = _get_first(row, ["category", "panel"], "")

            # FR (avec accents + majuscules)
            if not name:
                name = _get_first(row, ["Biomarqueur", "Marqueur", "Paramètre", "Parametre"], "")
            if value is None or value == "":
                value = _get_first(row, ["Valeur", "Résultat", "Resultat"], None)
            if not unit:
                unit = _get_first(row, ["Unité", "Unite"], "")
            if not ref:
                ref = _get_first(row, ["Référence", "Reference", "Norme"], "")
            if not stt:
                stt = _get_first(row, ["Statut", "Flag", "Interprétation", "Interpretation"], "")
            if not cat:
                cat = _get_first(row, ["Catégorie", "Categorie", "Famille"], "")

            nm = _clean_str(name)
            if nm:
                out.append(
                    dict(
                        name=nm,
                        value=value,
                        unit=_clean_str(unit),
                        reference=_clean_str(ref),
                        status=_normalize_status(stt),
                        category=_clean_str(cat),
                    )
                )
        return out

    return out


# ---------------------------------------------------------------------
# Styles
# ---------------------------------------------------------------------
_styles = getSampleStyleSheet()

STYLE_TITLE = ParagraphStyle(
    "AL_Title", parent=_styles["Title"],
    fontName="Helvetica-Bold", fontSize=20, leading=24,
    textColor=colors.HexColor("#0F172A"), alignment=TA_LEFT,
)

STYLE_SUB = ParagraphStyle(
    "AL_Sub", parent=_styles["Normal"],
    fontName="Helvetica", fontSize=10.5, leading=14,
    textColor=colors.HexColor("#334155"), alignment=TA_LEFT,
)

STYLE_H2 = ParagraphStyle(
    "AL_H2", parent=_styles["Heading2"],
    fontName="Helvetica-Bold", fontSize=14, leading=18,
    textColor=colors.HexColor("#0F172A"),
    spaceBefore=10, spaceAfter=6,
)

STYLE_H3 = ParagraphStyle(
    "AL_H3", parent=_styles["Heading3"],
    fontName="Helvetica-Bold", fontSize=11.5, leading=14,
    textColor=colors.HexColor("#0F172A"),
    spaceBefore=8, spaceAfter=4,
)

STYLE_BODY = ParagraphStyle(
    "AL_Body", parent=_styles["Normal"],
    fontName="Helvetica", fontSize=10, leading=13.5,
    textColor=colors.HexColor("#0F172A"), alignment=TA_JUSTIFY,
)

STYLE_SMALL = ParagraphStyle(
    "AL_Small", parent=_styles["Normal"],
    fontName="Helvetica", fontSize=9, leading=12,
    textColor=colors.HexColor("#475569"), alignment=TA_LEFT,
)

STYLE_BADGE = ParagraphStyle(
    "AL_Badge", parent=_styles["Normal"],
    fontName="Helvetica-Bold", fontSize=9, leading=11,
    textColor=colors.white, alignment=TA_CENTER,
)


# ---------------------------------------------------------------------
# Components
# ---------------------------------------------------------------------
class HR(Flowable):
    def __init__(self, width: float, thickness: float = 1, color=colors.HexColor("#E2E8F0")):
        super().__init__()
        self.width = width
        self.thickness = thickness
        self.color = color
        self.height = thickness + 4

    def draw(self):
        self.canv.setStrokeColor(self.color)
        self.canv.setLineWidth(self.thickness)
        self.canv.line(0, 2, self.width, 2)


def dna_logo_drawing(width: float = 78, height: float = 44) -> Drawing:
    d = Drawing(width, height)
    d.add(Rect(0, 0, width, height, fillColor=colors.HexColor("#EEF2FF"), strokeColor=colors.HexColor("#E2E8F0"), rx=10, ry=10))

    left_x = 18
    right_x = width - 18
    top = height - 10
    bottom = 12

    d.add(Line(left_x, bottom, left_x, top, strokeColor=colors.HexColor("#6366F1"), strokeWidth=2))
    d.add(Line(right_x, bottom, right_x, top, strokeColor=colors.HexColor("#0EA5E9"), strokeWidth=2))

    steps = 7
    for i in range(steps):
        t = i / (steps - 1)
        y = bottom + t * (top - bottom)
        col = colors.HexColor("#111827") if i % 2 == 0 else colors.HexColor("#334155")
        w = 1.4 if i % 2 == 0 else 1.0
        d.add(Line(left_x, y, right_x, y, strokeColor=col, strokeWidth=w, strokeCap=1))
        d.add(Circle(left_x, y, 2.2, fillColor=colors.white, strokeColor=colors.HexColor("#6366F1"), strokeWidth=1))
        d.add(Circle(right_x, y, 2.2, fillColor=colors.white, strokeColor=colors.HexColor("#0EA5E9"), strokeWidth=1))

    d.add(String(8, 6, "ALGO-LIFE", fontName="Helvetica-Bold", fontSize=8.5, fillColor=colors.HexColor("#0F172A")))
    return d


def header_block(patient: Dict[str, Any], page_width: float) -> Table:
    name = f"{patient.get('prenom','') or ''} {patient.get('nom','') or ''}".strip() or "—"
    dob = patient.get("dob", "") or "—"
    dr = patient.get("date_rapport", "") or datetime.now().strftime("%d/%m/%Y")
    antecedents = _clean_str(patient.get("antecedents", ""))

    logo = dna_logo_drawing(78, 44)

    title = Paragraph("Rapport Multimodal", STYLE_TITLE)
    sub = Paragraph("Biologie fonctionnelle + Microbiote · Lecture augmentée", STYLE_SUB)
    meta = Paragraph(f"<b>Patient</b> : {name} &nbsp;&nbsp;|&nbsp;&nbsp; <b>Naissance</b> : {dob} &nbsp;&nbsp;|&nbsp;&nbsp; <b>Date</b> : {dr}", STYLE_SMALL)

    text_tbl = Table([[title], [sub], [meta]], colWidths=[page_width - 120])
    text_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    hdr = Table([[logo, text_tbl]], colWidths=[90, page_width - 90])
    hdr.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))

    if antecedents:
        ctx = Paragraph(f"<b>Contexte clinique</b> : {antecedents}", STYLE_SMALL)
        ctx_tbl = Table([[ctx]], colWidths=[page_width])
        ctx_tbl.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
        return Table([[hdr], [ctx_tbl]], colWidths=[page_width])

    return hdr


# ---------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------
def biology_counts(rows: List[Dict[str, Any]]) -> Dict[str, int]:
    n = m = a = 0
    for r in rows:
        s = _normalize_status(r.get("status", ""))
        if s == "Normal":
            n += 1
        elif s == "À surveiller":
            m += 1
        elif s == "Anormal":
            a += 1
    return {"normal": n, "monitor": m, "abnormal": a, "total": len(rows)}


def summary_cards(counts: Dict[str, int], page_width: float) -> Table:
    def card(title: str, value: str) -> Table:
        t = Table(
            [[Paragraph(title, STYLE_SMALL)],
             [Paragraph(f"<b><font size=16>{value}</font></b>", ParagraphStyle("v", parent=STYLE_BODY, alignment=TA_LEFT))]],
            colWidths=[(page_width - 20) / 3],
        )
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.white),
            ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#E2E8F0")),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        return t

    c1 = card("Biomarqueurs — Total", str(counts.get("total", 0)))
    c2 = card("Normaux", str(counts.get("normal", 0)))
    c3 = card("À surveiller + Anormaux", str(counts.get("monitor", 0) + counts.get("abnormal", 0)))

    row = Table([[c1, c2, c3]], colWidths=[(page_width - 20) / 3] * 3)
    row.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
    return row


def biology_table(rows: List[Dict[str, Any]]) -> Table:
    data = [["Biomarqueur", "Valeur", "Unité", "Référence", "Statut"]]
    for r in rows:
        data.append([
            _clean_str(r.get("name")),
            _clean_str(r.get("value")),
            _clean_str(r.get("unit")),
            _clean_str(r.get("reference")),
            _normalize_status(r.get("status")),
        ])

    tbl = Table(data, colWidths=[6.3 * cm, 2.4 * cm, 1.8 * cm, 5.1 * cm, 2.2 * cm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#E2E8F0")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    for i in range(1, len(data)):
        col = _status_color(data[i][4])
        tbl.setStyle(TableStyle([("TEXTCOLOR", (4, i), (4, i), col), ("FONTNAME", (4, i), (4, i), "Helvetica-Bold")]))
    return tbl


def microbiome_summary_table(micro: Dict[str, Any]) -> Table:
    if not isinstance(micro, dict):
        micro = {}

    di = micro.get("di_score") or micro.get("DI") or micro.get("di") or "—"
    diversity = micro.get("diversity_status") or micro.get("diversity") or "—"
    groups = micro.get("bacterial_groups") or micro.get("bacteria_groups") or []

    expected = slightly = deviating = 0
    tags: List[str] = []
    if isinstance(groups, list):
        for g in groups:
            if not isinstance(g, dict):
                continue
            stt = _clean_str(g.get("deviation") or g.get("status") or "").lower()
            name = _clean_str(g.get("name") or g.get("label") or "")
            if "as expected" in stt or "expected" in stt or stt == "normal":
                expected += 1
            elif "slight" in stt or "mild" in stt or "surve" in stt:
                slightly += 1
                if name:
                    tags.append(name)
            elif "deviat" in stt or "abnormal" in stt or "high" in stt or "low" in stt:
                deviating += 1
                if name:
                    tags.append(name)

    top_tags = ", ".join(tags[:3]) if tags else "—"

    data = [
        ["Microbiote — Résumé", "Valeur"],
        ["DI", str(di)],
        ["Diversité", str(diversity)],
        ["Groupes (attendus)", str(expected)],
        ["Groupes (légèrement déviants)", str(slightly)],
        ["Groupes (déviants)", str(deviating)],
        ["Catégories concernées (top)", top_tags],
    ]

    tbl = Table(data, colWidths=[7.2 * cm, 10.6 * cm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#E2E8F0")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return tbl


# ---------------------------------------------------------------------
# Cross analysis
# ---------------------------------------------------------------------
def _find_marker(rows: List[Dict[str, Any]], keywords: List[str]) -> Optional[Dict[str, Any]]:
    for r in rows:
        nm = _clean_str(r.get("name", "")).lower()
        if any(k.lower() in nm for k in keywords):
            return r
    return None


def build_cross_insights(bio_rows: List[Dict[str, Any]], micro: Dict[str, Any]) -> List[Dict[str, str]]:
    insights: List[Dict[str, str]] = []
    if not isinstance(micro, dict):
        micro = {}

    di = _safe_float(micro.get("di_score") or micro.get("DI") or micro.get("di"), default=-1)
    diversity = _clean_str(micro.get("diversity_status") or micro.get("diversity") or "").lower()
    groups = micro.get("bacterial_groups") or micro.get("bacteria_groups") or []

    deviating_groups = 0
    if isinstance(groups, list):
        for g in groups:
            if not isinstance(g, dict):
                continue
            stt = _clean_str(g.get("deviation") or g.get("status") or "").lower()
            if "deviat" in stt or "abnormal" in stt or "high" in stt or "low" in stt:
                deviating_groups += 1

    dysbiosis_flag = (di >= 4) or ("deviat" in diversity) or (deviating_groups >= 2)

    crp = _find_marker(bio_rows, ["crp", "hs-crp", "c-reactive"])
    ferritin = _find_marker(bio_rows, ["ferritin", "ferritine"])
    iron = _find_marker(bio_rows, [" fer", "iron"])
    ldl_ox = _find_marker(bio_rows, ["ldl ox", "oxyd", "oxid"])

    if crp and (_normalize_status(crp.get("status")) in {"À surveiller", "Anormal"}) and dysbiosis_flag:
        insights.append({
            "title": "Inflammation ↔ Dysbiose",
            "why": f"CRP signalée ({_clean_str(crp.get('value'))} {_clean_str(crp.get('unit'))}) + microbiote avec signaux de dysbiose (DI/diversité/groupes).",
            "interpretation": "Terrain inflammatoire pouvant être entretenu par un déséquilibre du microbiote (barrière, LPS, métabolites).",
            "confidence": "Modérée",
        })

    iron_low = False
    if ferritin and _normalize_status(ferritin.get("status")) == "Anormal":
        iron_low = True
    if iron and _normalize_status(iron.get("status")) == "Anormal":
        iron_low = True

    low_div_flag = ("low" in diversity) or ("decreas" in diversity) or (di >= 4)
    if iron_low and low_div_flag:
        insights.append({
            "title": "Statut fer ↔ Microbiote appauvri",
            "why": "Signal compatible avec statut en fer bas + indicateurs microbiote (DI/diversité) défavorables.",
            "interpretation": "Un microbiote altéré peut impacter l’absorption/tolérance du fer. Adapter forme, fractionner, travailler la barrière puis recontrôler.",
            "confidence": "Modérée",
        })

    if ldl_ox and (_normalize_status(ldl_ox.get("status")) in {"À surveiller", "Anormal"}) and deviating_groups >= 2:
        insights.append({
            "title": "LDL oxydé ↔ Déséquilibre microbiote",
            "why": "LDL oxydé signalé + plusieurs groupes microbiote déviants.",
            "interpretation": "Un déséquilibre microbiote peut contribuer à un terrain pro-oxydant. Renforcer axes antioxydants + stratégie microbiote + recontrôle.",
            "confidence": "Faible à modérée",
        })

    return insights


# ---------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------
def _format_reco_items(items: Any) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    if not items:
        return out
    if isinstance(items, list):
        for it in items:
            if isinstance(it, dict):
                out.append({
                    "label": _clean_str(it.get("label") or it.get("title") or "Recommandation"),
                    "detail": _clean_str(it.get("detail") or it.get("text") or it.get("recommendation") or ""),
                    "rationale": _clean_str(it.get("rationale") or it.get("why") or ""),
                })
            else:
                out.append({"label": "Recommandation", "detail": _clean_str(it), "rationale": ""})
        return out
    if isinstance(items, dict):
        for k, v in items.items():
            out.append({"label": _clean_str(k), "detail": _clean_str(v), "rationale": ""})
        return out
    out.append({"label": "Recommandation", "detail": _clean_str(items), "rationale": ""})
    return out


def build_recommendations_fallback(bio_rows: List[Dict[str, Any]], micro: Dict[str, Any], cross: List[Dict[str, str]]) -> Dict[str, List[Dict[str, str]]]:
    rec_bio: List[Dict[str, str]] = []
    rec_micro: List[Dict[str, str]] = []
    rec_cross: List[Dict[str, str]] = []

    abnormal = [r for r in bio_rows if _normalize_status(r.get("status")) in {"À surveiller", "Anormal"}]
    if abnormal:
        rec_bio.append({
            "label": "Prioriser les biomarqueurs hors zone",
            "detail": "Revoir en priorité les paramètres “À surveiller/Anormaux”, puis planifier un recontrôle ciblé.",
            "rationale": "Focus sur les signaux les plus actionnables.",
        })

    di = _safe_float(micro.get("di_score") or micro.get("DI") or micro.get("di"), default=-1) if isinstance(micro, dict) else -1
    diversity = _clean_str(micro.get("diversity_status") or micro.get("diversity") or "") if isinstance(micro, dict) else ""
    if di >= 4 or "deviat" in diversity.lower():
        rec_micro.append({
            "label": "Stratégie microbiote (8–12 semaines)",
            "detail": "Augmenter fibres tolérées, diversification alimentaire, réduire ultra-transformés, protocole adapté selon catégories déviantes.",
            "rationale": "DI/diversité indiquent un déséquilibre à corriger.",
        })

    for c in cross or []:
        rec_cross.append({
            "label": f"Focus croisé : {c.get('title','')}",
            "detail": _clean_str(c.get("interpretation") or ""),
            "rationale": _clean_str(c.get("why") or ""),
        })

    return {"biology": rec_bio, "microbiome": rec_micro, "cross": rec_cross}


def reco_block(title: str, items: List[Dict[str, str]]) -> List[Flowable]:
    flows: List[Flowable] = [Paragraph(title, STYLE_H3)]
    if not items:
        flows.append(Paragraph("—", STYLE_SMALL))
        flows.append(Spacer(1, 6))
        return flows

    for it in items[:18]:
        lbl = _clean_str(it.get("label") or "Recommandation")
        det = _clean_str(it.get("detail") or "")
        why = _clean_str(it.get("rationale") or "")
        flows.append(Paragraph(f"<b>{lbl}</b>", STYLE_BODY))
        if det:
            flows.append(Paragraph(det, STYLE_BODY))
        if why:
            flows.append(Paragraph(f"<i>{why}</i>", STYLE_SMALL))
        flows.append(Spacer(1, 6))

    return flows


# ---------------------------------------------------------------------
# ✅ COMPAT ENTRYPOINT
# ---------------------------------------------------------------------
def generate_multimodal_report(*args, **kwargs) -> str:
    """
    Supports:
      1) generate_multimodal_report(payload_dict, output_path=None)
      2) generate_multimodal_report(patient_data=..., biology_data=..., microbiome_data=..., recommendations=..., output_path=...)
    """
    # Mode 2: kwargs with patient_data/biology_data...
    if "patient_data" in kwargs or "biology_data" in kwargs or "microbiome_data" in kwargs:
        return generate_unilabs_report(
            patient_data=kwargs.get("patient_data"),
            biology_data=kwargs.get("biology_data"),
            microbiome_data=kwargs.get("microbiome_data"),
            recommendations=kwargs.get("recommendations"),
            output_path=kwargs.get("output_path"),
        )

    # Mode 1: payload dict
    payload = args[0] if args else kwargs.get("payload")
    output_path = None
    if len(args) >= 2:
        output_path = args[1]
    if kwargs.get("output_path") is not None:
        output_path = kwargs["output_path"]

    if not isinstance(payload, dict):
        raise TypeError("generate_multimodal_report: expected payload dict or keyword args (patient_data, biology_data, ...)")

    return _generate_from_payload(payload, output_path=output_path)


def _generate_from_payload(payload: Dict[str, Any], output_path: Optional[str] = None) -> str:
    if output_path is None:
        out_dir = os.path.join(os.getcwd(), "exports")
        os.makedirs(out_dir, exist_ok=True)
        output_path = os.path.join(out_dir, f"UNILABS_rapport_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")

    patient = payload.get("patient", {}) if isinstance(payload, dict) else {}
    biology_raw = payload.get("biology") if isinstance(payload, dict) else None
    micro = payload.get("microbiome") if isinstance(payload, dict) else {}

    bio_rows = normalize_biology_data(biology_raw)
    counts = biology_counts(bio_rows)
    cross = build_cross_insights(bio_rows, micro if isinstance(micro, dict) else {})

    rec_payload = payload.get("recommendations") if isinstance(payload, dict) else None
    if isinstance(rec_payload, dict):
        recos = {
            "biology": _format_reco_items(rec_payload.get("biology")),
            "microbiome": _format_reco_items(rec_payload.get("microbiome")),
            "cross": _format_reco_items(rec_payload.get("cross")),
        }
    else:
        recos = build_recommendations_fallback(bio_rows, micro if isinstance(micro, dict) else {}, cross)

    _build_pdf(output_path, patient, bio_rows, counts, micro if isinstance(micro, dict) else {}, cross, recos)
    return output_path


def generate_unilabs_report(
    patient_data: Optional[Dict[str, Any]] = None,
    biology_data: Any = None,
    microbiome_data: Optional[Dict[str, Any]] = None,
    recommendations: Optional[Dict[str, Any]] = None,
    output_path: Optional[str] = None,
) -> str:
    payload = {
        "patient": patient_data or {},
        "biology": biology_data,
        "microbiome": microbiome_data or {},
        "recommendations": recommendations,
    }
    return _generate_from_payload(payload, output_path=output_path)


# ---------------------------------------------------------------------
# PDF builder
# ---------------------------------------------------------------------
def _build_pdf(
    output_path: str,
    patient: Dict[str, Any],
    bio_rows: List[Dict[str, Any]],
    counts: Dict[str, int],
    micro: Dict[str, Any],
    cross: List[Dict[str, str]],
    recos: Dict[str, List[Dict[str, str]]],
) -> None:
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title="Rapport Multimodal",
        author="ALGO-LIFE / UNILABS",
    )
    page_width = A4[0] - doc.leftMargin - doc.rightMargin

    story: List[Flowable] = []
    story.append(header_block(patient, page_width))
    story.append(Spacer(1, 8))
    story.append(HR(page_width))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Résumé", STYLE_H2))
    story.append(summary_cards(counts, page_width))
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "Ce rapport présente une lecture multimodale des données biologiques et microbiote. "
        "Les interprétations sont informatives et doivent être corrélées au contexte clinique.",
        STYLE_BODY
    ))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Biologie — Biomarqueurs", STYLE_H2))
    if not bio_rows:
        story.append(Paragraph(
            "Aucun biomarqueur exploitable n'a été reçu par le générateur PDF. "
            "Vérifier que l'application envoie bien biology_df.to_dict('records') au moment de l'export.",
            STYLE_SMALL,
        ))
    else:
        story.append(biology_table(bio_rows))

    story.append(Spacer(1, 10))

    story.append(Paragraph("Microbiote — Résumé (sous la biologie)", STYLE_H2))
    story.append(microbiome_summary_table(micro))
    story.append(Spacer(1, 8))

    story.append(HR(page_width))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Analyses croisées (Biologie × Microbiote)", STYLE_H2))
    if not cross:
        story.append(Paragraph("Aucun signal croisé détecté (ou données insuffisantes).", STYLE_SMALL))
    else:
        for c in cross:
            blk: List[Flowable] = []
            blk.append(Paragraph(f"<b>{_clean_str(c.get('title','Signal croisé'))}</b>", STYLE_BODY))
            if c.get("why"):
                blk.append(Paragraph(f"• {_clean_str(c.get('why'))}", STYLE_BODY))
            if c.get("interpretation"):
                blk.append(Paragraph(f"• <b>Lecture croisée :</b> {_clean_str(c.get('interpretation'))}", STYLE_BODY))
            if c.get("confidence"):
                blk.append(Paragraph(f"<i>Confiance : {_clean_str(c.get('confidence'))}</i>", STYLE_SMALL))
            blk.append(Spacer(1, 6))
            story.append(KeepTogether(blk))

    story.append(PageBreak())

    story.append(Paragraph("Recommandations", STYLE_H2))
    story.append(Paragraph("Recommandations structurées par modalité (biologie / microbiote) et par focus croisé.", STYLE_BODY))
    story.append(Spacer(1, 8))

    story.extend(reco_block("🧪 Biologie", recos.get("biology", [])))
    story.append(Spacer(1, 6))
    story.extend(reco_block("🦠 Microbiote", recos.get("microbiome", [])))
    story.append(Spacer(1, 6))
    story.extend(reco_block("🔗 Croisées (focus clinique)", recos.get("cross", [])))

    story.append(Spacer(1, 10))
    story.append(HR(page_width))
    story.append(Spacer(1, 6))
    story.append(Paragraph("Note : Les informations de ce rapport ne constituent pas un diagnostic médical.", STYLE_SMALL))

    doc.build(story)
