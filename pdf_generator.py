# pdf_generator.py
# -*- coding: utf-8 -*-

"""
ALGO-LIFE - Générateur de Rapports PDF Multimodaux ULTRA-AMÉLIORÉ
Version Beta v1.0 - AVEC JAUGES VISUELLES
Dr Thibault SUTTER - Biologiste spécialisé en biologie fonctionnelle
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Any, Tuple

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    Flowable,
)

# ---------------------------
# Helpers
# ---------------------------

def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        if isinstance(x, (int, float)):
            return float(x)
        s = str(x).strip().replace(",", ".")
        return float(s)
    except Exception:
        return default


def _safe_str(x: Any) -> str:
    return "" if x is None else str(x)


# ---------------------------
# Flowables (visual widgets)
# ---------------------------

class BiomarkerGauge(Flowable):
    """Jauge visuelle pour afficher un biomarqueur avec sa position par rapport aux valeurs de référence"""

    def __init__(
        self,
        name: str,
        value: float,
        ref_min: float,
        ref_max: float,
        unit: str = "",
        width: float = 16 * cm,
        height: float = 1.8 * cm,
    ):
        super().__init__()
        self.name = name
        self.value = value
        self.ref_min = ref_min
        self.ref_max = ref_max
        self.unit = unit
        self.width = width
        self.height = height

    def draw(self):
        COLOR_LOW = colors.HexColor("#FF9800")
        COLOR_NORMAL = colors.HexColor("#4CAF50")
        COLOR_HIGH = colors.HexColor("#F44336")

        gauge_width = self.width - 3 * cm
        gauge_height = 0.8 * cm
        gauge_x = 2.5 * cm
        gauge_y = 0.3 * cm

        # Label biomarqueur
        self.canv.setFont("Helvetica-Bold", 10)
        self.canv.setFillColor(colors.black)
        self.canv.drawString(0, gauge_y + 0.3 * cm, _safe_str(self.name))

        # Plage d'affichage étendue
        ref_min = _safe_float(self.ref_min, 0.0)
        ref_max = _safe_float(self.ref_max, 1.0)
        if ref_max <= ref_min:
            ref_max = ref_min + 1.0

        display_min = ref_min * 0.5 if ref_min != 0 else 0.0
        display_max = ref_max * 1.5
        range_width = max(display_max - display_min, 1e-9)

        normal_start = (ref_min - display_min) / range_width * gauge_width
        normal_width = (ref_max - ref_min) / range_width * gauge_width

        val = _safe_float(self.value, display_min)
        if val < display_min:
            value_pos = 0
        elif val > display_max:
            value_pos = gauge_width
        else:
            value_pos = (val - display_min) / range_width * gauge_width

        # Zones colorées
        self.canv.setFillColor(COLOR_LOW)
        self.canv.rect(gauge_x, gauge_y, max(normal_start, 0), gauge_height, fill=1, stroke=0)

        self.canv.setFillColor(COLOR_NORMAL)
        self.canv.rect(gauge_x + normal_start, gauge_y, max(normal_width, 0), gauge_height, fill=1, stroke=0)

        high_start = normal_start + normal_width
        high_width = gauge_width - high_start
        self.canv.setFillColor(COLOR_HIGH)
        self.canv.rect(gauge_x + high_start, gauge_y, max(high_width, 0), gauge_height, fill=1, stroke=0)

        # Bordure
        self.canv.setStrokeColor(colors.HexColor("#757575"))
        self.canv.setLineWidth(1)
        self.canv.rect(gauge_x, gauge_y, gauge_width, gauge_height, fill=0, stroke=1)

        # Marqueur
        marker_x = gauge_x + value_pos
        marker_y = gauge_y + gauge_height

        self.canv.setFillColor(colors.HexColor("#1976D2"))
        self.canv.setStrokeColor(colors.HexColor("#1976D2"))

        path = self.canv.beginPath()
        path.moveTo(marker_x, marker_y + 0.3 * cm)
        path.lineTo(marker_x - 0.15 * cm, marker_y)
        path.lineTo(marker_x + 0.15 * cm, marker_y)
        path.close()
        self.canv.drawPath(path, fill=1, stroke=1)

        self.canv.setLineWidth(2)
        self.canv.line(marker_x, marker_y, marker_x, gauge_y)

        # Valeur
        self.canv.setFont("Helvetica-Bold", 11)
        self.canv.setFillColor(colors.HexColor("#1976D2"))
        value_text = f"{val:g} {_safe_str(self.unit)}".strip()
        self.canv.drawString(marker_x - 0.7 * cm, marker_y + 0.4 * cm, value_text)

        # Référence
        self.canv.setFont("Helvetica", 8)
        self.canv.setFillColor(colors.HexColor("#757575"))
        self.canv.drawString(gauge_x, gauge_y - 0.3 * cm, f"{ref_min:g}")
        self.canv.drawRightString(gauge_x + gauge_width, gauge_y - 0.3 * cm, f"{ref_max:g}")
        self.canv.drawCentredString(
            gauge_x + gauge_width / 2,
            gauge_y - 0.3 * cm,
            f"Référence: {ref_min:g}-{ref_max:g} {_safe_str(self.unit)}".strip(),
        )


class ScoreCircle(Flowable):
    """Cercle de score pour afficher un pourcentage (PATCHED anti ZeroDivisionError)"""

    def __init__(self, score: float, title: str, width: float = 5 * cm, height: float = 5 * cm):
        super().__init__()
        self.score = _safe_float(score, 0.0)
        self.title = title
        self.width = width
        self.height = height

    def draw(self):
        # Clamp score pour éviter NaN / valeurs hors bornes
        s = _safe_float(self.score, 0.0)
        if s != s:  # NaN
            s = 0.0
        s = max(0.0, min(100.0, s))

        cx = self.width / 2
        cy = self.height / 2 - 0.3 * cm
        radius = 1.2 * cm

        if s >= 80:
            color = colors.HexColor("#4CAF50")
        elif s >= 60:
            color = colors.HexColor("#FF9800")
        else:
            color = colors.HexColor("#F44336")

        # fond gris
        self.canv.setFillColor(colors.HexColor("#E0E0E0"))
        self.canv.circle(cx, cy, radius, fill=1, stroke=0)

        # wedge (évite arcTo extent=0)
        angle = (s / 100.0) * 360.0
        self.canv.setFillColor(color)

        if angle <= 0.0001:
            # 0% => pas d'arc
            pass
        elif angle >= 359.999:
            # 100% => disque plein
            self.canv.circle(cx, cy, radius, fill=1, stroke=0)
        else:
            # arc partiel
            path = self.canv.beginPath()
            path.moveTo(cx, cy)
            path.arcTo(cx - radius, cy - radius, cx + radius, cy + radius, 90, angle)
            path.close()
            self.canv.drawPath(path, fill=1, stroke=0)

        # centre blanc
        self.canv.setFillColor(colors.white)
        self.canv.circle(cx, cy, radius - 0.25 * cm, fill=1, stroke=0)

        # texte
        self.canv.setFont("Helvetica-Bold", 20)
        self.canv.setFillColor(color)
        self.canv.drawCentredString(cx, cy - 0.2 * cm, f"{int(round(s))}")

        self.canv.setFont("Helvetica", 9)
        self.canv.setFillColor(colors.HexColor("#333333"))
        self.canv.drawCentredString(cx, cy - 0.5 * cm, "/100")

        self.canv.setFont("Helvetica-Bold", 10)
        self.canv.setFillColor(colors.HexColor("#333333"))
        self.canv.drawCentredString(cx, cy - radius - 0.5 * cm, _safe_str(self.title))


# ---------------------------
# Main generator
# ---------------------------

class PDFGenerator:
    """Générateur de rapports PDF multimodaux"""

    COLOR_PRIMARY = colors.HexColor("#5B5FCF")
    COLOR_SECONDARY = colors.HexColor("#8B7FCF")
    COLOR_SUCCESS = colors.HexColor("#4CAF50")
    COLOR_WARNING = colors.HexColor("#FF9800")
    COLOR_DANGER = colors.HexColor("#F44336")
    COLOR_INFO = colors.HexColor("#2196F3")
    COLOR_GREY = colors.HexColor("#757575")
    COLOR_LIGHT_GREY = colors.HexColor("#E0E0E0")

    def __init__(self, output_path: str):
        self.output_path = output_path
        self.doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=2 * cm,
            leftMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
        )
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
        self.story = []

    def _setup_custom_styles(self):
        self.styles.add(
            ParagraphStyle(
                name="CustomTitle",
                parent=self.styles["Heading1"],
                fontSize=24,
                textColor=self.COLOR_PRIMARY,
                spaceAfter=30,
                alignment=TA_CENTER,
                fontName="Helvetica-Bold",
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="CustomSubtitle",
                parent=self.styles["Heading2"],
                fontSize=14,
                textColor=self.COLOR_GREY,
                spaceAfter=20,
                alignment=TA_CENTER,
                fontName="Helvetica",
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="SectionTitle",
                parent=self.styles["Heading2"],
                fontSize=16,
                textColor=self.COLOR_PRIMARY,
                spaceAfter=15,
                spaceBefore=20,
                fontName="Helvetica-Bold",
                backColor=colors.HexColor("#F5F5F5"),
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="SubsectionTitle",
                parent=self.styles["Heading3"],
                fontSize=13,
                textColor=self.COLOR_SECONDARY,
                spaceAfter=10,
                spaceBefore=15,
                fontName="Helvetica-Bold",
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="CustomBody",
                parent=self.styles["BodyText"],
                fontSize=10,
                alignment=TA_JUSTIFY,
                spaceAfter=10,
                leading=14,
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="Recommendation",
                parent=self.styles["BodyText"],
                fontSize=10,
                alignment=TA_LEFT,
                leftIndent=20,
                spaceAfter=8,
                textColor=colors.HexColor("#333333"),
                leading=14,
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="Alert",
                parent=self.styles["BodyText"],
                fontSize=10,
                textColor=self.COLOR_DANGER,
                alignment=TA_LEFT,
                leftIndent=15,
                spaceAfter=10,
                fontName="Helvetica-Bold",
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="InfoBox",
                parent=self.styles["BodyText"],
                fontSize=9,
                textColor=self.COLOR_INFO,
                alignment=TA_LEFT,
                leftIndent=15,
                spaceAfter=10,
                backColor=colors.HexColor("#E3F2FD"),
            )
        )

    def add_header(self, patient_data: Dict[str, Any]):
        title = Paragraph("🧬 ALGO-LIFE", self.styles["CustomTitle"])
        subtitle = Paragraph(
            "PLATEFORME MÉDECIN - Analyse Multimodale de Santé<br/>Beta v1.0",
            self.styles["CustomSubtitle"],
        )
        self.story.extend([title, subtitle, Spacer(1, 0.5 * cm)])

        imc = patient_data.get("imc", None)
        imc_val = _safe_float(imc, default=float("nan"))

        patient_info = [
            ["<b>Informations Patient</b>", ""],
            ["Nom:", f"{patient_data.get('nom', 'N/A')} {patient_data.get('prenom', '')}".strip()],
            ["Date de naissance:", _safe_str(patient_data.get("date_naissance", "N/A"))],
            ["Âge:", f"{_safe_str(patient_data.get('age', 'N/A'))} ans"],
            ["Genre:", _safe_str(patient_data.get("genre", "N/A"))],
            ["Poids:", f"{_safe_str(patient_data.get('poids', 'N/A'))} kg"],
            ["Taille:", f"{_safe_str(patient_data.get('taille', 'N/A'))} cm"],
            ["IMC:", f"{imc_val:.1f} kg/m²" if imc == imc and imc is not None else "N/A"],
            ["Activité:", _safe_str(patient_data.get("activite", "N/A"))],
        ]

        patient_info.append(["Date du rapport:", datetime.now().strftime("%d/%m/%Y")])

        symptomes = patient_data.get("symptomes") or []
        if symptomes:
            patient_info.append(["Symptômes:", ", ".join(symptomes)])

        table = Table(patient_info, colWidths=[4.5 * cm, 12 * cm])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), self.COLOR_PRIMARY),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 11),
                    ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 1), (-1, -1), 9),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("TOPPADDING", (0, 1), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
                    ("GRID", (0, 0), (-1, -1), 0.5, self.COLOR_LIGHT_GREY),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9F9F9")]),
                ]
            )
        )
        self.story.extend([table, Spacer(1, 1 * cm)])

    def add_section(self, title: str, level: int = 1):
        style = "SectionTitle" if level == 1 else "SubsectionTitle"
        self.story.append(Paragraph(title, self.styles[style]))

    def _parse_reference_range(self, reference: str) -> Tuple[float, float]:
        ref = _safe_str(reference).strip()
        if not ref:
            return 0.0, 100.0

        # normaliser séparateurs
        ref = ref.replace("–", "-").replace("—", "-").replace(" à ", "-").replace("au", "-")
        ref = ref.replace(",", ".")
        try:
            if "-" in ref:
                parts = [p.strip() for p in ref.split("-") if p.strip()]
                if len(parts) >= 2:
                    return _safe_float(parts[0], 0.0), _safe_float(parts[1], 100.0)
            if "<" in ref:
                max_val = _safe_float(ref.replace("<", "").strip(), 100.0)
                return 0.0, max_val
            if ">" in ref:
                min_val = _safe_float(ref.replace(">", "").strip(), 0.0)
                return min_val, min_val * 2.0 if min_val != 0 else 100.0
            val = _safe_float(ref, 50.0)
            return val * 0.8, val * 1.2
        except Exception:
            return 0.0, 100.0

    def add_biology_section(self, bio_data: Dict[str, Any]):
        self.add_section("📊 ANALYSE BIOLOGIQUE", level=1)

        if bio_data.get("resume"):
            self.story.append(Paragraph(f"<b>Résumé:</b> {bio_data['resume']}", self.styles["CustomBody"]))
            self.story.append(Spacer(1, 0.5 * cm))

        categories = bio_data.get("categories") or {}
        for category, markers in categories.items():
            self.add_section(f"🔬 {category}", level=2)

            for marker in markers or []:
                ref_str = _safe_str(marker.get("reference", "0-100"))
                ref_min, ref_max = self._parse_reference_range(ref_str)

                value = marker.get("valeur", 0)
                value = _safe_float(value, 0.0)

                gauge = BiomarkerGauge(
                    name=_safe_str(marker.get("nom", "N/A")),
                    value=value,
                    ref_min=ref_min,
                    ref_max=ref_max,
                    unit=_safe_str(marker.get("unite", "")),
                    width=16 * cm,
                    height=1.8 * cm,
                )
                self.story.append(gauge)
                self.story.append(Spacer(1, 0.3 * cm))

                interpretations = marker.get("interpretations") or []
                for interp in interpretations:
                    if interp:
                        self.story.append(Paragraph(f"→ {_safe_str(interp)}", self.styles["Recommendation"]))
                if interpretations:
                    self.story.append(Spacer(1, 0.5 * cm))

    def add_microbiome_section(self, microbiome_data: Dict[str, Any]):
        self.add_section("🦠 ANALYSE MICROBIOTE", level=1)

        diversite = microbiome_data.get("diversite") or {}
        div_score = _safe_float(diversite.get("score", 0), 0.0)

        score_circle = ScoreCircle(score=div_score, title="Score de Diversité", width=5 * cm, height=5 * cm)
        self.story.append(score_circle)
        self.story.append(Spacer(1, 0.5 * cm))

        interp = diversite.get("interpretation", "")
        if interp:
            self.story.append(Paragraph(f"<b>Interprétation:</b> {interp}", self.styles["CustomBody"]))
            self.story.append(Spacer(1, 0.5 * cm))

        phyla = microbiome_data.get("phyla") or []
        if phyla:
            self.add_section("Répartition des Phyla", level=2)
            phyla_data = [["Phylum", "Abondance (%)", "Statut"]]
            for phylum in phyla:
                status = self._get_status_symbol(phylum.get("statut", "normal"))
                phyla_data.append(
                    [
                        _safe_str(phylum.get("nom", "N/A")),
                        f"{_safe_float(phylum.get('abondance', 0), 0.0):.1f}%",
                        status,
                    ]
                )
            table = Table(phyla_data, colWidths=[6 * cm, 4 * cm, 4 * cm])
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), self.COLOR_SUCCESS),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("ALIGN", (0, 1), (0, -1), "LEFT"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 10),
                        ("FONTSIZE", (0, 1), (-1, -1), 9),
                        ("GRID", (0, 0), (-1, -1), 0.5, self.COLOR_LIGHT_GREY),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F1F8F4")]),
                    ]
                )
            )
            self.story.append(table)
            self.story.append(Spacer(1, 0.5 * cm))

        especes = microbiome_data.get("especes_cles") or []
        if especes:
            self.add_section("Espèces Clés Identifiées", level=2)
            for espece in especes:
                impact = espece.get("impact", "neutre")
                icon = "✅" if impact == "positif" else "⚠️" if impact == "negatif" else "ℹ️"
                self.story.append(
                    Paragraph(
                        f"{icon} <b>{_safe_str(espece.get('nom', 'N/A'))}</b>: {_safe_str(espece.get('description', ''))}",
                        self.styles["CustomBody"],
                    )
                )
                self.story.append(Spacer(1, 0.2 * cm))

    def add_cross_analysis_section(self, cross_data: Dict[str, Any]):
        self.add_section("🔗 ANALYSE CROISÉE MULTIMODALE", level=1)
        self.story.append(
            Paragraph(
                "Cette section présente les corrélations identifiées entre vos analyses biologiques et votre profil microbiote.",
                self.styles["CustomBody"],
            )
        )
        self.story.append(Spacer(1, 0.5 * cm))

        correlations = cross_data.get("correlations") or []
        if correlations:
            self.add_section("🔍 Corrélations Identifiées", level=2)
            for i, corr in enumerate(correlations, 1):
                severity = corr.get("severite", "faible")
                icon = "🔴" if severity == "elevee" else "🟡" if severity == "moyenne" else "🟢"
                self.story.append(
                    Paragraph(
                        f"{icon} <b>Corrélation {i}:</b> {_safe_str(corr.get('titre',''))}",
                        self.styles["SubsectionTitle"],
                    )
                )

                corr_data = [
                    ["Biomarqueur", _safe_str(corr.get("biomarqueur", "N/A"))],
                    ["Élément microbiote", _safe_str(corr.get("microbiote_element", "N/A"))],
                    ["Interprétation", _safe_str(corr.get("interpretation", ""))],
                ]
                if corr.get("mecanisme"):
                    corr_data.append(["Mécanisme", _safe_str(corr.get("mecanisme", ""))])

                table = Table(corr_data, colWidths=[4 * cm, 12 * cm])
                table.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F5F5F5")),
                            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                            ("FONTSIZE", (0, 0), (-1, -1), 9),
                            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                            ("VALIGN", (0, 0), (-1, -1), "TOP"),
                            ("GRID", (0, 0), (-1, -1), 0.5, self.COLOR_LIGHT_GREY),
                            ("TOPPADDING", (0, 0), (-1, -1), 8),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                        ]
                    )
                )
                self.story.append(table)
                self.story.append(Spacer(1, 0.5 * cm))

    def add_recommendations_section(self, recommendations: Dict[str, Any]):
        self.add_section("💡 RECOMMANDATIONS PERSONNALISÉES", level=1)

        # --- NUTRITION ---
        nutrition = recommendations.get("nutrition") or {}
        if nutrition or recommendations.get('nutrition', {}).get('manual_text'):
            self.add_section("🥗 Nutrition et Alimentation", level=2)

            # Recommandations manuelles
            manual_nutrition = recommendations.get('nutrition', {}).get('manual_text', '').strip()
            if manual_nutrition:
                # Encadré spécial pour les recommandations manuelles
                self.story.append(
                    Paragraph(
                        "<b>✍️ RECOMMANDATIONS DU PRATICIEN:</b>",
                        self.styles["SubsectionTitle"]
                    )
                )
                
                # Créer un encadré coloré
                manual_data = [[Paragraph(manual_nutrition, self.styles["CustomBody"])]]
                manual_table = Table(manual_data, colWidths=[16 * cm])
                manual_table.setStyle(
                    TableStyle([
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFF9E6")),
                        ("BOX", (0, 0), (-1, -1), 2, colors.HexColor("#FFD700")),
                        ("LEFTPADDING", (0, 0), (-1, -1), 12),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                        ("TOPPADDING", (0, 0), (-1, -1), 12),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                    ])
                )
                self.story.append(manual_table)
                self.story.append(Spacer(1, 0.5 * cm))

            # Recommandations automatiques
            privilegier = nutrition.get("privilegier") or []
            if privilegier:
                self.story.append(Paragraph("<b>À PRIVILÉGIER:</b>", self.styles["SubsectionTitle"]))
                for item in privilegier:
                    self.story.append(
                        Paragraph(
                            f"✓ <b>{_safe_str(item.get('nom',''))}</b>: {_safe_str(item.get('raison',''))}",
                            self.styles["Recommendation"],
                        )
                    )
                self.story.append(Spacer(1, 0.3 * cm))

            limiter = nutrition.get("limiter") or []
            if limiter:
                self.story.append(Paragraph("<b>À LIMITER:</b>", self.styles["SubsectionTitle"]))
                for item in limiter:
                    self.story.append(
                        Paragraph(
                            f"✗ <b>{_safe_str(item.get('nom',''))}</b>: {_safe_str(item.get('raison',''))}",
                            self.styles["Alert"],
                        )
                    )
                self.story.append(Spacer(1, 0.3 * cm))

        # --- MICRONUTRITION ---
        manual_micronutrition = _safe_str(recommendations.get('micronutrition_manual', '')).strip()
        supplementation = recommendations.get("supplementation") or []
        
        if manual_micronutrition or supplementation:
            self.add_section("💊 Micronutrition et Supplémentation", level=2)
            
            # Recommandations manuelles
            if manual_micronutrition:
                self.story.append(
                    Paragraph(
                        "<b>✍️ RECOMMANDATIONS DU PRATICIEN:</b>",
                        self.styles["SubsectionTitle"]
                    )
                )
                
                manual_data = [[Paragraph(manual_micronutrition, self.styles["CustomBody"])]]
                manual_table = Table(manual_data, colWidths=[16 * cm])
                manual_table.setStyle(
                    TableStyle([
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFF9E6")),
                        ("BOX", (0, 0), (-1, -1), 2, colors.HexColor("#FFD700")),
                        ("LEFTPADDING", (0, 0), (-1, -1), 12),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                        ("TOPPADDING", (0, 0), (-1, -1), 12),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                    ])
                )
                self.story.append(manual_table)
                self.story.append(Spacer(1, 0.5 * cm))
            
            # Recommandations automatiques
            if supplementation:
                self.story.append(Paragraph("<b>Supplémentation Suggérée:</b>", self.styles["SubsectionTitle"]))
                suppl_data = [["Supplément", "Dosage", "Fréquence", "Durée", "Objectif"]]
                for suppl in supplementation:
                    suppl_data.append(
                        [
                            _safe_str(suppl.get("nom", "N/A")),
                            _safe_str(suppl.get("dosage", "N/A")),
                            _safe_str(suppl.get("frequence", "N/A")),
                            _safe_str(suppl.get("duree", "N/A")),
                            _safe_str(suppl.get("objectif", "N/A")),
                        ]
                    )
                table = Table(suppl_data, colWidths=[3.5 * cm, 2 * cm, 2.5 * cm, 2 * cm, 5.5 * cm])
                table.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, 0), self.COLOR_INFO),
                            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                            ("ALIGN", (0, 1), (0, -1), "LEFT"),
                            ("ALIGN", (4, 1), (4, -1), "LEFT"),
                            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                            ("FONTSIZE", (0, 0), (-1, 0), 9),
                            ("FONTSIZE", (0, 1), (-1, -1), 8),
                            ("GRID", (0, 0), (-1, -1), 0.5, self.COLOR_LIGHT_GREY),
                            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F0F7FF")]),
                        ]
                    )
                )
                self.story.append(table)
                self.story.append(Spacer(1, 0.3 * cm))
                self.story.append(
                    Paragraph(
                        "<i>⚠️ Note: ces suggestions sont basées sur votre profil multimodal. Consultez votre médecin avant toute nouvelle supplémentation.</i>",
                        self.styles["InfoBox"],
                    )
                )
                self.story.append(Spacer(1, 0.5 * cm))

        # --- LIFESTYLE ---
        manual_lifestyle = _safe_str(recommendations.get('lifestyle_manual', '')).strip()
        if manual_lifestyle:
            self.add_section("🏃 Lifestyle et Habitudes de Vie", level=2)
            
            self.story.append(
                Paragraph(
                    "<b>✍️ RECOMMANDATIONS DU PRATICIEN:</b>",
                    self.styles["SubsectionTitle"]
                )
            )
            
            manual_data = [[Paragraph(manual_lifestyle, self.styles["CustomBody"])]]
            manual_table = Table(manual_data, colWidths=[16 * cm])
            manual_table.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFF9E6")),
                    ("BOX", (0, 0), (-1, -1), 2, colors.HexColor("#FFD700")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 12),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                    ("TOPPADDING", (0, 0), (-1, -1), 12),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                ])
            )
            self.story.append(manual_table)
            self.story.append(Spacer(1, 0.5 * cm))

        # --- MULTIMODAL ---
        manual_multimodal = _safe_str(recommendations.get('multimodal_manual', '')).strip()
        if manual_multimodal:
            self.add_section("🔄 Observations Multimodales", level=2)
            
            self.story.append(
                Paragraph(
                    "<b>✍️ OBSERVATIONS DU PRATICIEN:</b>",
                    self.styles["SubsectionTitle"]
                )
            )
            
            manual_data = [[Paragraph(manual_multimodal, self.styles["CustomBody"])]]
            manual_table = Table(manual_data, colWidths=[16 * cm])
            manual_table.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFF9E6")),
                    ("BOX", (0, 0), (-1, -1), 2, colors.HexColor("#FFD700")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 12),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                    ("TOPPADDING", (0, 0), (-1, -1), 12),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                ])
            )
            self.story.append(manual_table)
            self.story.append(Spacer(1, 0.5 * cm))

    def add_follow_up_section(self, follow_up: Dict[str, Any]):
        self.add_section("📅 SUIVI ET CONTRÔLES", level=1)
        self.story.append(
            Paragraph(
                "Plan de suivi recommandé pour évaluer l'efficacité des interventions:",
                self.styles["CustomBody"],
            )
        )
        self.story.append(Spacer(1, 0.3 * cm))

        controles = follow_up.get("controles") or []
        if controles:
            controle_data = [["Analyse", "Timing", "Biomarqueurs à Surveiller"]]
            for controle in controles:
                markers = ", ".join(controle.get("biomarqueurs", []) or [])
                controle_data.append(
                    [
                        _safe_str(controle.get("type", "N/A")),
                        _safe_str(controle.get("delai", "N/A")),
                        markers,
                    ]
                )
            table = Table(controle_data, colWidths=[4 * cm, 3 * cm, 8.5 * cm])
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), self.COLOR_SECONDARY),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 10),
                        ("FONTSIZE", (0, 1), (-1, -1), 9),
                        ("GRID", (0, 0), (-1, -1), 0.5, self.COLOR_LIGHT_GREY),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FAF8FF")]),
                    ]
                )
            )
            self.story.append(table)
            self.story.append(Spacer(1, 0.5 * cm))

    def add_footer(self):
        self.story.append(PageBreak())
        self.story.append(Spacer(1, 2 * cm))
        footer_text = """
        <para alignment="center">
        <b>ALGO-LIFE © 2026</b><br/>
        Dr Thibault SUTTER, Dr en biologie spécialisé en biologie fonctionnelle<br/>
        Version Beta v1.0<br/><br/>
        <i>Ce rapport est généré à partir d'analyses multimodales. Il ne remplace pas un avis médical.</i><br/><br/>
        📧 Contact: contact@algo-life.com | 🌐 www.algo-life.com
        </para>
        """
        self.story.append(Paragraph(footer_text, self.styles["CustomBody"]))

    def _get_status_symbol(self, status: str) -> str:
        status_map = {
            "normal": "✓ Normal",
            "bas": "↓ Bas",
            "haut": "↑ Haut",
            "critique_bas": "⚠️ Très bas",
            "critique_haut": "⚠️ Très haut",
            "attention": "⚡ Attention",
        }
        key = status.lower().strip() if isinstance(status, str) else "normal"
        return status_map.get(key, "• N/A")

    def generate(self, data: Dict[str, Any]) -> str:
        self.add_header(data.get("patient", {}))

        if data.get("biologie"):
            self.add_biology_section(data["biologie"])
            self.story.append(PageBreak())

        if data.get("microbiote"):
            self.add_microbiome_section(data["microbiote"])
            self.story.append(PageBreak())

        if data.get("cross_analysis"):
            self.add_cross_analysis_section(data["cross_analysis"])
            self.story.append(PageBreak())

        if data.get("recommendations"):
            self.add_recommendations_section(data["recommendations"])
            self.story.append(PageBreak())

        if data.get("follow_up"):
            self.add_follow_up_section(data["follow_up"])

        self.add_footer()
        self.doc.build(self.story)
        return self.output_path


def generate_multimodal_report(
    patient_data: Dict[str, Any],
    biology_data: Dict[str, Any],
    microbiome_data: Dict[str, Any],
    cross_analysis: Dict[str, Any],
    recommendations: Dict[str, Any],
    follow_up: Dict[str, Any],
    output_path: str = "rapport_multimodal.pdf",
) -> str:
    data = {
        "patient": patient_data,
        "biologie": biology_data,
        "microbiote": microbiome_data,
        "cross_analysis": cross_analysis,
        "recommendations": recommendations,
        "follow_up": follow_up,
    }
    generator = PDFGenerator(output_path)
    return generator.generate(data)


if __name__ == "__main__":
    print("PDF Generator chargé avec succès - Version ultra-améliorée avec jauges visuelles!")
