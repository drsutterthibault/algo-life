"""
UNILABS - Générateur PDF Premium v2.0
✅ Design moderne et futuriste
✅ Biomarqueurs avec jauges visuelles colorées
✅ Logos professionnels
✅ Sections de recommandations dans des cadres stylisés
✅ Bug des valeurs par défaut corrigé
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Dict, Any, List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    Image,
    KeepTogether,
    ListFlowable,
    Flowable,
)

from reportlab.graphics.shapes import Drawing, Rect, Line, Circle, String

# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------
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


def _clean_str(x: Any) -> str:
    if x is None:
        return ""
    return str(x).strip()


def _first_present(d: Dict[str, Any], keys: List[str], default: Any = None) -> Any:
    """Return first present key from d among keys, case-insensitive, and supporting nested dict."""
    if not isinstance(d, dict):
        return default
    lower_map = {str(k).strip().lower(): k for k in d.keys()}
    for k in keys:
        lk = str(k).strip().lower()
        if lk in lower_map:
            return d.get(lower_map[lk], default)
    return default


def _normalize_status(raw: Any) -> str:
    """Normalize status to one of: Normal, À surveiller, Anormal (plus fallback)."""
    s = _clean_str(raw).lower()
    if not s:
        return "Inconnu"
    # Normal
    if s in {"normal", "within", "ok", "dans la norme", "as expected"}:
        return "Normal"
    # Monitor / borderline
    if any(w in s for w in ["surve", "border", "limite", "modéré", "slightly", "mild", "watch"]):
        return "À surveiller"
    # Abnormal high/low
    if any(w in s for w in ["anormal", "abnormal", "haut", "élev", "high", "low", "bas", "faible", "deviating"]):
        return "Anormal"
    return raw if isinstance(raw, str) and raw.strip() else "Inconnu"


# ---------------------------------------------------------------------
# PATCH CRITIQUE: Normalisation biologie depuis app.py (DF -> dict records)
# ---------------------------------------------------------------------
def normalize_biology_data(biology: Any) -> List[Dict[str, Any]]:
    """
    Accept many possible shapes:
    - list[dict] with keys: name/value/unit/reference/status/category
    - list[dict] coming from pandas df.to_dict('records') with FRENCH headers:
      Biomarqueur / Valeur / Unité / Référence / Statut / Catégorie
    - dict mapping biomarker_name -> dict(value/unit/reference/status/...)
    - other minor variants

    Returns list of normalized dicts with:
      name, value, unit, reference, status, category
    """
    out: List[Dict[str, Any]] = []

    if biology is None:
        return out

    # If dict: { "CRP": {..}, ... }
    if isinstance(biology, dict):
        # could already be payload with "biomarkers" key
        if any(k in [str(x).lower() for x in biology.keys()] for k in ["biomarkers", "markers", "biology"]):
            inner = _first_present(biology, ["biomarkers", "markers", "biology"], default=None)
            return normalize_biology_data(inner)

        # Otherwise assume mapping name -> dict
        for k, v in biology.items():
            if isinstance(v, dict):
                name = _clean_str(_first_present(v, ["name", "biomarker", "marqueur"], default=k) or k)
                value = _first_present(v, ["value", "result", "valeur", "mesure"], default=None)
                unit = _first_present(v, ["unit", "units", "unité", "unite"], default="")
                ref = _first_present(v, ["reference", "ref", "range", "référence", "reference_range"], default="")
                status = _first_present(v, ["status", "flag", "statut"], default=_first_present(v, ["interpretation"], default=""))
                category = _first_present(v, ["category", "panel", "famille", "catégorie", "categorie"], default="")
            else:
                name = _clean_str(k)
                value = v
                unit, ref, status, category = "", "", "", ""

            if not name:
                continue

            out.append(
                dict(
                    name=name,
                    value=value,
                    unit=_clean_str(unit),
                    reference=_clean_str(ref),
                    status=_normalize_status(status),
                    category=_clean_str(category),
                )
            )
        return out

    # If list: records
    if isinstance(biology, list):
        for row in biology:
            if not isinstance(row, dict):
                continue

            # Support EN keys
            name = _first_present(row, ["name", "biomarker", "marker"], default=None)
            value = _first_present(row, ["value", "result"], default=None)
            unit = _first_present(row, ["unit", "units"], default="")
            ref = _first_present(row, ["reference", "ref", "range", "reference_range"], default="")
            status = _first_present(row, ["status", "flag"], default="")
            category = _first_present(row, ["category", "panel"], default="")

            # Support FR keys from your DataFrame
            if not name:
                name = _first_present(row, ["Biomarqueur", "Marqueur", "Paramètre", "Parametre"], default="")

            if value is None or value == "":
                value = _first_present(row, ["Valeur", "Résultat", "Resultat"], default=None)

            if not unit:
                unit = _first_present(row, ["Unité", "Unite"], default="")

            if not ref:
                ref = _first_present(row, ["Référence", "Reference", "Norme"], default="")

            if not status:
                status = _first_present(row, ["Statut", "Flag", "Interprétation", "Interpretation"], default="")

            if not category:
                category = _first_present(row, ["Catégorie", "Categorie", "Famille"], default="")

            name = _clean_str(name)
            if not name:
                continue

            out.append(
                dict(
                    name=name,
                    value=value,
                    unit=_clean_str(unit),
                    reference=_clean_str(ref),
                    status=_normalize_status(status),
                    category=_clean_str(category),
                )
            )

        return out

    return out


# ---------------------------------------------------------------------
# Design blocks
# ---------------------------------------------------------------------
styles = getSampleStyleSheet()

STYLE_TITLE = ParagraphStyle(
    "Title",
    parent=styles["Title"],
    fontName="Helvetica-Bold",
    fontSize=20,
    leading=24,
    textColor=colors.HexColor("#111827"),
    alignment=TA_LEFT,
)

STYLE_SUBTITLE = ParagraphStyle(
    "Subtitle",
    parent=styles["Normal"],
    fontName="Helvetica",
    fontSize=11,
    leading=14,
    textColor=colors.HexColor("#374151"),
    alignment=TA_LEFT,
)

STYLE_H2 = ParagraphStyle(
    "H2",
    parent=styles["Heading2"],
    fontName="Helvetica-Bold",
    fontSize=14,
    leading=18,
    textColor=colors.HexColor("#111827"),
    spaceBefore=10,
    spaceAfter=6,
)

STYLE_BODY = ParagraphStyle(
    "Body",
    parent=styles["Normal"],
    fontName="Helvetica",
    fontSize=10,
    leading=13,
    textColor=colors.HexColor("#111827"),
    alignment=TA_JUSTIFY,
)

STYLE_SMALL = ParagraphStyle(
    "Small",
    parent=styles["Normal"],
    fontName="Helvetica",
    fontSize=9,
    leading=12,
    textColor=colors.HexColor("#374151"),
)


def _header_band(width: float, height: float, patient: Dict[str, Any]) -> Drawing:
    d = Drawing(width, height)
    # Background
    d.add(Rect(0, 0, width, height, fillColor=colors.HexColor("#EEF2FF"), strokeColor=colors.HexColor("#E5E7EB")))
    # Accent line
    d.add(Line(0, 0, width, 0, strokeColor=colors.HexColor("#6366F1"), strokeWidth=3))

    title = "Rapport Multimodal - Biologie fonctionnelle & Microbiote"
    d.add(String(12, height - 18, title, fontName="Helvetica-Bold", fontSize=13, fillColor=colors.HexColor("#111827")))

    name = f"{patient.get('prenom','') or ''} {patient.get('nom','') or ''}".strip()
    dob = patient.get("dob", "")
    date_rapport = patient.get("date_rapport", datetime.now().strftime("%d/%m/%Y"))

    meta = f"Patient: {name or '—'}   |   Date naissance: {dob or '—'}   |   Rapport: {date_rapport}"
    d.add(String(12, height - 34, meta, fontName="Helvetica", fontSize=9, fillColor=colors.HexColor("#374151")))

    return d


class HR(Flowable):
    def __init__(self, width: float, thickness: float = 1, color=colors.HexColor("#E5E7EB")):
        super().__init__()
        self.width = width
        self.thickness = thickness
        self.color = color
        self.height = thickness + 2

    def draw(self):
        self.canv.setStrokeColor(self.color)
        self.canv.setLineWidth(self.thickness)
        self.canv.line(0, 1, self.width, 1)


def _status_color(status: str):
    s = _normalize_status(status)
    if s == "Normal":
        return colors.HexColor("#10B981")  # green
    if s == "À surveiller":
        return colors.HexColor("#F59E0B")  # amber
    if s == "Anormal":
        return colors.HexColor("#EF4444")  # red
    return colors.HexColor("#6B7280")      # gray


def _biomarker_row_table(rows: List[Dict[str, Any]]) -> Table:
    data = [["Biomarqueur", "Valeur", "Unité", "Référence", "Statut"]]
    for r in rows:
        data.append([r.get("name", ""), str(r.get("value", "")), r.get("unit", ""), r.get("reference", ""), r.get("status", "")])

    tbl = Table(data, colWidths=[6.2 * cm, 2.4 * cm, 1.8 * cm, 5.0 * cm, 2.4 * cm])
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("ALIGN", (1, 1), (3, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#E5E7EB")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9FAFB")]),
                ("FONTSIZE", (0, 1), (-1, -1), 9),
            ]
        )
    )

    # Colorize status cell per row
    for i in range(1, len(data)):
        st_col = _status_color(data[i][4])
        tbl.setStyle(TableStyle([("TEXTCOLOR", (4, i), (4, i), st_col), ("FONTNAME", (4, i), (4, i), "Helvetica-Bold")]))

    return tbl


def _section_box(title: str, content_flowables: List[Any]) -> List[Any]:
    out = [Paragraph(title, STYLE_H2), Spacer(1, 3)]
    out.extend(content_flowables)
    out.append(Spacer(1, 8))
    return out


def _summary_counts(rows: List[Dict[str, Any]]) -> Dict[str, int]:
    n = 0
    m = 0
    a = 0
    for r in rows:
        s = _normalize_status(r.get("status", ""))
        if s == "Normal":
            n += 1
        elif s == "À surveiller":
            m += 1
        elif s == "Anormal":
            a += 1
    return {"normal": n, "monitor": m, "abnormal": a}


def _summary_table(counts: Dict[str, int]) -> Table:
    data = [
        ["Synthèse", "Normal", "À surveiller", "Anormal"],
        ["Biomarqueurs", str(counts.get("normal", 0)), str(counts.get("monitor", 0)), str(counts.get("abnormal", 0))],
    ]
    tbl = Table(data, colWidths=[5.0 * cm, 3.2 * cm, 3.2 * cm, 3.2 * cm])
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#E5E7EB")),
                ("ALIGN", (1, 1), (-1, -1), "CENTER"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#F9FAFB")]),
                ("FONTSIZE", (0, 1), (-1, -1), 9),
            ]
        )
    )
    # Color numbers
    tbl.setStyle(TableStyle([("TEXTCOLOR", (1, 1), (1, 1), colors.HexColor("#10B981")),
                             ("TEXTCOLOR", (2, 1), (2, 1), colors.HexColor("#F59E0B")),
                             ("TEXTCOLOR", (3, 1), (3, 1), colors.HexColor("#EF4444")),
                             ("FONTNAME", (1, 1), (3, 1), "Helvetica-Bold")]))
    return tbl


def _microbiome_section(microbiome: Dict[str, Any]) -> List[Any]:
    """
    Accepts typical microbiome structures:
      - di_score / diversity_status
      - bacterial_groups (list) / bacteria_groups
      - bacteria_individual (list)
    """
    if not isinstance(microbiome, dict) or not microbiome:
        return [Paragraph("Aucune donnée microbiote fournie.", STYLE_SMALL)]

    di = microbiome.get("di_score") or microbiome.get("DI") or microbiome.get("di") or ""
    diversity = microbiome.get("diversity_status") or microbiome.get("diversity") or ""

    groups = microbiome.get("bacterial_groups") or microbiome.get("bacteria_groups") or []
    bacteria = microbiome.get("bacteria_individual") or microbiome.get("bacteria") or []

    flow: List[Any] = []
    flow.append(Paragraph(f"<b>DI</b> : {di or '—'} &nbsp;&nbsp;|&nbsp;&nbsp; <b>Diversité</b> : {diversity or '—'}", STYLE_BODY))
    flow.append(Spacer(1, 6))

    # Groups table
    if isinstance(groups, list) and groups:
        data = [["Groupe", "Nom", "Statut"]]
        for g in groups[:18]:
            if not isinstance(g, dict):
                continue
            group = _clean_str(g.get("group") or g.get("code") or "")
            name = _clean_str(g.get("name") or g.get("label") or "")
            stt = _clean_str(g.get("status") or g.get("deviation") or "")
            data.append([group, name, stt])

        tbl = Table(data, colWidths=[2.0 * cm, 10.0 * cm, 5.0 * cm])
        tbl.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#E5E7EB")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9FAFB")]),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                ]
            )
        )
        flow.append(Paragraph("<b>Groupes bactériens</b>", STYLE_SMALL))
        flow.append(tbl)
        flow.append(Spacer(1, 8))

    # Bacteria table
    if isinstance(bacteria, list) and bacteria:
        data = [["Bactérie", "Abondance", "Unité", "Statut"]]
        for b in bacteria[:20]:
            if not isinstance(b, dict):
                continue
            name = _clean_str(b.get("name") or b.get("taxon") or "")
            abundance = _clean_str(b.get("abundance") or b.get("value") or "")
            unit = _clean_str(b.get("unit") or "")
            stt = _clean_str(b.get("status") or b.get("deviation") or "")
            data.append([name, abundance, unit, stt])

        tbl = Table(data, colWidths=[8.5 * cm, 3.0 * cm, 2.0 * cm, 3.5 * cm])
        tbl.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#E5E7EB")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9FAFB")]),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                ]
            )
        )
        flow.append(Paragraph("<b>Bactéries (extrait)</b>", STYLE_SMALL))
        flow.append(tbl)

    if len(flow) == 0:
        return [Paragraph("Aucune donnée microbiote structurée détectée.", STYLE_SMALL)]
    return flow


# ---------------------------------------------------------------------
# Main entrypoint
# ---------------------------------------------------------------------
def generate_multimodal_report(payload: Dict[str, Any], output_path: Optional[str] = None) -> str:
    """
    Compatible with your app.py call:
      generate_multimodal_report(payload_dict)
    """
    if output_path is None:
        out_dir = os.path.join(os.getcwd(), "exports")
        os.makedirs(out_dir, exist_ok=True)
        output_path = os.path.join(out_dir, f"UNILABS_rapport_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")

    patient = payload.get("patient", {}) if isinstance(payload, dict) else {}
    raw_biology = payload.get("biology") if isinstance(payload, dict) else None
    raw_microbiome = payload.get("microbiome") if isinstance(payload, dict) else None

    biology_rows = normalize_biology_data(raw_biology)
    counts = _summary_counts(biology_rows)

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=14 * mm,
        leftMargin=14 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title="Rapport Multimodal",
        author="ALGO-LIFE / UNILABS",
    )

    story: List[Any] = []

    # Header band
    story.append(_header_band(A4[0] - 28 * mm, 44, patient))
    story.append(Spacer(1, 10))

    # Intro
    story.append(Paragraph("Synthèse", STYLE_H2))
    story.append(_summary_table(counts))
    story.append(Spacer(1, 8))
    story.append(Paragraph("Ce rapport présente une lecture multimodale des données biologiques et microbiote.", STYLE_BODY))
    story.append(Spacer(1, 10))
    story.append(HR(A4[0] - 28 * mm))
    story.append(Spacer(1, 10))

    # Biology section
    story.append(Paragraph("Biologie — Biomarqueurs", STYLE_H2))
    if not biology_rows:
        story.append(Paragraph(
            "Aucun biomarqueur exploitable n'a été reçu par le générateur PDF. "
            "Cause la plus fréquente : clés inattendues (ex: 'Biomarqueur', 'Valeur', 'Unité', 'Référence', 'Statut'). "
            "Ce fichier est patché pour les accepter ; si c'est encore vide, alors le payload envoyé est réellement vide.",
            STYLE_SMALL
        ))
    else:
        # Reduce to safe strings
        cleaned = []
        for r in biology_rows:
            cleaned.append({
                "name": _clean_str(r.get("name")),
                "value": r.get("value", ""),
                "unit": _clean_str(r.get("unit")),
                "reference": _clean_str(r.get("reference")),
                "status": _normalize_status(r.get("status")),
                "category": _clean_str(r.get("category")),
            })
        story.append(_biomarker_row_table(cleaned))
    story.append(PageBreak())

    # Microbiome section
    story.append(Paragraph("Microbiote — Résumé", STYLE_H2))
    story.extend(_microbiome_section(raw_microbiome if isinstance(raw_microbiome, dict) else {}))

    # Footer note
    story.append(Spacer(1, 10))
    story.append(HR(A4[0] - 28 * mm))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "Note: Les interprétations fournies sont informatives et doivent être corrélées au contexte clinique.",
        STYLE_SMALL
    ))

    doc.build(story)
    return output_path
