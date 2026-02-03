# pdf_generator_premium.py
# -*- coding: utf-8 -*-

"""
ALGO-LIFE / UNILABS - Générateur de Rapports PDF Premium
Version 2.0 - Design Haut de Gamme
Dr Thibault SUTTER - Biologiste spécialisé en biologie fonctionnelle

Features:
✓ Logo Unilabs + Logo ADN
✓ Design moderne et épuré
✓ Jauges visuelles sophistiquées
✓ Templates différenciés biologie/microbiote
✓ Sections regroupées et optimisées
✓ Couleurs et mise en page premium
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional
import os

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
    Flowable,
    KeepTogether,
    Image as ReportLabImage,
)
from reportlab.pdfgen import canvas
from reportlab.graphics.shapes import Drawing, Circle, Rect, String, Line, Polygon
from reportlab.graphics import renderPDF


# ═══════════════════════════════════════════════════════════════════════════
# CONSTANTS & BRANDING
# ═══════════════════════════════════════════════════════════════════════════

class BrandColors:
    """Charte graphique UNILABS/ALGO-LIFE"""
    # Couleurs principales
    PRIMARY = colors.HexColor("#0A4D8C")          # Bleu UNILABS profond
    PRIMARY_LIGHT = colors.HexColor("#1E88E5")    # Bleu clair
    PRIMARY_DARK = colors.HexColor("#01579B")     # Bleu très foncé
    
    # Couleurs secondaires
    ACCENT = colors.HexColor("#00ACC1")           # Cyan médical
    ACCENT_LIGHT = colors.HexColor("#4DD0E1")     # Cyan clair
    
    # Couleurs ADN/Génétique
    DNA_PRIMARY = colors.HexColor("#7B1FA2")      # Violet ADN
    DNA_SECONDARY = colors.HexColor("#AB47BC")    # Violet clair
    
    # Status colors
    NORMAL = colors.HexColor("#4CAF50")           # Vert
    WARNING = colors.HexColor("#FF9800")          # Orange
    CRITICAL = colors.HexColor("#F44336")         # Rouge
    LOW = colors.HexColor("#FF9800")              # Orange
    HIGH = colors.HexColor("#F44336")             # Rouge
    
    # Neutres
    DARK_GREY = colors.HexColor("#424242")
    GREY = colors.HexColor("#757575")
    LIGHT_GREY = colors.HexColor("#BDBDBD")
    VERY_LIGHT_GREY = colors.HexColor("#F5F5F5")
    
    # Backgrounds
    BG_LIGHT_BLUE = colors.HexColor("#E3F2FD")
    BG_LIGHT_PURPLE = colors.HexColor("#F3E5F5")
    BG_WHITE = colors.white
    
    # Sections microbiote
    MICROBIOME_NORMAL = colors.HexColor("#4CAF50")
    MICROBIOME_SLIGHT = colors.HexColor("#FF9800")
    MICROBIOME_DEVIATION = colors.HexColor("#F44336")


# ═══════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

def _safe_float(x: Any, default: float = 0.0) -> float:
    """Convertit en float de manière sécurisée"""
    try:
        if x is None:
            return default
        if isinstance(x, (int, float)):
            return float(x)
        s = str(x).strip().replace(",", ".")
        return float(s) if s else default
    except Exception:
        return default


def _safe_str(x: Any) -> str:
    """Convertit en string de manière sécurisée"""
    return "" if x is None else str(x)


def parse_reference_range(reference: str) -> Tuple[Optional[float], Optional[float]]:
    """Parse une référence type '10-20' ou '< 50' ou '> 5'"""
    import re
    
    if not reference:
        return None, None
    
    ref = reference.strip().replace(",", ".")
    
    # Range: "10-20" ou "10 - 20" ou "10 à 20"
    m = re.search(r"(-?\d+(?:\.\d+)?)\s*(?:-|à|to)\s*(-?\d+(?:\.\d+)?)", ref, re.IGNORECASE)
    if m:
        return _safe_float(m.group(1)), _safe_float(m.group(2))
    
    # "< X" ou "≤ X"
    m = re.search(r"(?:<|≤)\s*(-?\d+(?:\.\d+)?)", ref)
    if m:
        return None, _safe_float(m.group(1))
    
    # "> X" ou "≥ X"
    m = re.search(r"(?:>|≥)\s*(-?\d+(?:\.\d+)?)", ref)
    if m:
        return _safe_float(m.group(1)), None
    
    return None, None


# ═══════════════════════════════════════════════════════════════════════════
# CUSTOM FLOWABLES - VISUALISATIONS
# ═══════════════════════════════════════════════════════════════════════════

class DNALogo(Flowable):
    """Logo ADN stylisé pour les rapports"""
    
    def __init__(self, width=2*cm, height=2*cm):
        super().__init__()
        self.width = width
        self.height = height
    
    def draw(self):
        """Dessine une double hélice ADN stylisée"""
        c = self.canv
        
        # Dimensions
        w = float(self.width)
        h = float(self.height)
        
        # Couleurs dégradées
        c.setStrokeColor(BrandColors.DNA_PRIMARY)
        c.setFillColor(BrandColors.DNA_PRIMARY)
        c.setLineWidth(1.5)
        
        # Hélice 1
        for i in range(5):
            y = h * (0.2 + i * 0.15)
            x1 = w * 0.3
            x2 = w * 0.7
            
            # Barre transversale
            c.setStrokeColor(BrandColors.DNA_SECONDARY)
            c.line(x1, y, x2, y)
            
            # Nœuds
            c.setFillColor(BrandColors.DNA_PRIMARY)
            c.circle(x1, y, 1.5*mm, fill=1)
            c.circle(x2, y, 1.5*mm, fill=1)
        
        # Courbes hélicoïdales
        c.setStrokeColor(BrandColors.DNA_PRIMARY)
        c.setLineWidth(2)
        
        # Courbe gauche
        path = c.beginPath()
        path.moveTo(w * 0.3, h * 0.1)
        for i in range(6):
            y = h * (0.2 + i * 0.15)
            x = w * 0.3
            path.lineTo(x, y)
        c.drawPath(path, stroke=1)
        
        # Courbe droite
        path = c.beginPath()
        path.moveTo(w * 0.7, h * 0.1)
        for i in range(6):
            y = h * (0.2 + i * 0.15)
            x = w * 0.7
            path.lineTo(x, y)
        c.drawPath(path, stroke=1)


class BiomarkerCard(Flowable):
    """Carte moderne pour biomarqueur - Style capture d'écran"""
    
    def __init__(
        self,
        name: str,
        value: float,
        ref_min: Optional[float],
        ref_max: Optional[float],
        unit: str = "",
        status: str = "Normal",
        width: float = 8 * cm,
        height: float = 3.5 * cm,
    ):
        super().__init__()
        self.name = name
        self.value = value
        self.ref_min = ref_min
        self.ref_max = ref_max
        self.unit = unit
        self.status = status.lower()
        self.width = width
        self.height = height
    
    def draw(self):
        c = self.canv
        
        # === CARTE AVEC FOND BLANC ET OMBRE ===
        # Fond blanc arrondi
        c.setFillColor(colors.white)
        c.setStrokeColor(colors.HexColor("#E0E0E0"))
        c.setLineWidth(1)
        c.roundRect(0, 0, self.width, self.height, 0.5*cm, fill=1, stroke=1)
        
        # === NOM DU BIOMARQUEUR ===
        # Point de couleur selon status
        if self.status == "normal":
            dot_color = BrandColors.NORMAL
        elif "bas" in self.status or "low" in self.status:
            dot_color = BrandColors.LOW
        elif "élevé" in self.status or "high" in self.status or "haut" in self.status:
            dot_color = BrandColors.HIGH
        else:
            dot_color = BrandColors.GREY
        
        # Dessiner le point
        c.setFillColor(dot_color)
        c.circle(0.5*cm, self.height - 0.7*cm, 0.15*cm, fill=1, stroke=0)
        
        # Nom du biomarqueur
        c.setFont("Helvetica", 11)
        c.setFillColor(BrandColors.DARK_GREY)
        c.drawString(0.9*cm, self.height - 0.8*cm, self.name)
        
        # === BARRE DE JAUGE ===
        if self.ref_min is not None and self.ref_max is not None:
            self._draw_gauge_bar(c)
        else:
            # Pas de référence - afficher juste la valeur
            c.setFont("Helvetica-Bold", 14)
            c.setFillColor(BrandColors.PRIMARY)
            value_text = f"{self.value:.2f}".rstrip('0').rstrip('.') + f" {self.unit}".strip()
            c.drawCentredString(self.width / 2, self.height / 2, value_text)
    
    def _draw_gauge_bar(self, c):
        """Dessine la barre de jauge comme dans la capture d'écran"""
        
        # Dimensions de la barre
        bar_x = 0.8*cm
        bar_y = 1.8*cm
        bar_width = self.width - 1.6*cm
        bar_height = 0.35*cm
        
        # Calculer la plage d'affichage
        ref_range = self.ref_max - self.ref_min
        display_min = self.ref_min - ref_range * 0.2
        display_max = self.ref_max + ref_range * 0.2
        display_range = display_max - display_min
        
        if display_range <= 0:
            display_range = 1
        
        # Positions relatives dans la barre
        normal_start_x = (self.ref_min - display_min) / display_range * bar_width
        normal_end_x = (self.ref_max - display_min) / display_range * bar_width
        normal_width = normal_end_x - normal_start_x
        
        # === DESSINER LES ZONES DE COULEUR ===
        # Zone basse (rouge-orangé)
        c.setFillColor(colors.HexColor("#EF5350"))
        c.rect(bar_x, bar_y, normal_start_x * 0.5, bar_height, fill=1, stroke=0)
        
        # Transition orange
        c.setFillColor(colors.HexColor("#FF9800"))
        c.rect(bar_x + normal_start_x * 0.5, bar_y, normal_start_x * 0.5, bar_height, fill=1, stroke=0)
        
        # Zone normale (vert)
        c.setFillColor(colors.HexColor("#66BB6A"))
        c.rect(bar_x + normal_start_x, bar_y, normal_width, bar_height, fill=1, stroke=0)
        
        # Transition orange haute
        c.setFillColor(colors.HexColor("#FF9800"))
        c.rect(bar_x + normal_end_x, bar_y, (bar_width - normal_end_x) * 0.5, bar_height, fill=1, stroke=0)
        
        # Zone haute (rouge)
        c.setFillColor(colors.HexColor("#EF5350"))
        c.rect(bar_x + normal_end_x + (bar_width - normal_end_x) * 0.5, bar_y, 
               (bar_width - normal_end_x) * 0.5, bar_height, fill=1, stroke=0)
        
        # Bordure de la barre
        c.setStrokeColor(colors.HexColor("#BDBDBD"))
        c.setLineWidth(0.5)
        c.rect(bar_x, bar_y, bar_width, bar_height, fill=0, stroke=1)
        
        # === CURSEUR DE VALEUR ===
        # Calculer la position du curseur
        if self.value < display_min:
            cursor_x = bar_x
        elif self.value > display_max:
            cursor_x = bar_x + bar_width
        else:
            cursor_x = bar_x + (self.value - display_min) / display_range * bar_width
        
        # Dessiner le curseur (cercle vert avec bordure blanche)
        c.setFillColor(BrandColors.NORMAL)
        c.setStrokeColor(colors.white)
        c.setLineWidth(2)
        c.circle(cursor_x, bar_y + bar_height / 2, 0.25*cm, fill=1, stroke=1)
        
        # Ligne pointillée verticale depuis le curseur
        c.setStrokeColor(colors.HexColor("#9E9E9E"))
        c.setDash(2, 2)
        c.setLineWidth(0.5)
        c.line(cursor_x, bar_y + bar_height, cursor_x, bar_y + bar_height + 0.4*cm)
        c.setDash()  # Reset dash
        
        # === VALEURS MIN/MAX ===
        c.setFont("Helvetica", 9)
        c.setFillColor(BrandColors.GREY)
        
        # Min
        c.drawString(bar_x, bar_y - 0.35*cm, f"{self.ref_min:.2f}".rstrip('0').rstrip('.'))
        
        # Max
        max_text = f"{self.ref_max:.2f}".rstrip('0').rstrip('.')
        c.drawRightString(bar_x + bar_width, bar_y - 0.35*cm, max_text)
        
        # === VALEUR ACTUELLE ===
        c.setFont("Helvetica-Bold", 14)
        c.setFillColor(BrandColors.DARK_GREY)
        
        value_text = f"{self.value:.2f}".rstrip('0').rstrip('.')
        if self.unit:
            value_text += f" {self.unit}"
        
        # Centré sous la barre
        c.drawCentredString(self.width / 2, 0.5*cm, value_text)


class PremiumGauge(Flowable):
    """Jauge premium pour biomarqueurs avec design moderne"""
    
    def __init__(
        self,
        name: str,
        value: float,
        ref_min: Optional[float],
        ref_max: Optional[float],
        unit: str = "",
        status: str = "Normal",
        width: float = 16 * cm,
        height: float = 2.5 * cm,
    ):
        super().__init__()
        self.name = name
        self.value = value
        self.ref_min = ref_min
        self.ref_max = ref_max
        self.unit = unit
        self.status = status.lower()
        self.width = width
        self.height = height
    
    def draw(self):
        c = self.canv
        
        # Dimensions
        label_width = 5 * cm
        gauge_x = label_width + 0.5 * cm
        gauge_width = self.width - gauge_x - 0.5 * cm
        gauge_height = 1 * cm
        gauge_y = (self.height - gauge_height) / 2
        
        # === LABEL BIOMARQUEUR ===
        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(BrandColors.DARK_GREY)
        
        # Nom du biomarqueur (multiline si nécessaire)
        name_parts = self.name.split()
        if len(self.name) > 30:
            # Split en deux lignes si trop long
            mid = len(name_parts) // 2
            line1 = " ".join(name_parts[:mid])
            line2 = " ".join(name_parts[mid:])
            c.drawString(0, gauge_y + 1.2 * cm, line1)
            c.setFont("Helvetica-Bold", 10)
            c.drawString(0, gauge_y + 0.8 * cm, line2)
        else:
            c.drawString(0, gauge_y + 0.5 * cm, self.name)
        
        # Status badge
        status_colors = {
            "normal": BrandColors.NORMAL,
            "bas": BrandColors.LOW,
            "élevé": BrandColors.HIGH,
            "critique": BrandColors.CRITICAL,
        }
        status_color = status_colors.get(self.status, BrandColors.GREY)
        
        c.setFillColor(status_color)
        badge_y = gauge_y + 0.1 * cm
        c.roundRect(0, badge_y, 0.15 * cm, 0.15 * cm, 0.05 * cm, fill=1)
        
        # === GAUGE ===
        if self.ref_min is not None and self.ref_max is not None:
            # Mode range complet
            self._draw_full_range_gauge(c, gauge_x, gauge_y, gauge_width, gauge_height)
        elif self.ref_max is not None:
            # Mode "< max"
            self._draw_upper_limit_gauge(c, gauge_x, gauge_y, gauge_width, gauge_height)
        elif self.ref_min is not None:
            # Mode "> min"
            self._draw_lower_limit_gauge(c, gauge_x, gauge_y, gauge_width, gauge_height)
        else:
            # Mode valeur seule
            self._draw_value_only(c, gauge_x, gauge_y, gauge_width, gauge_height)
        
        # === VALEUR ===
        value_text = f"{self.value:.2f}".rstrip('0').rstrip('.')
        if self.unit:
            value_text += f" {self.unit}"
        
        c.setFont("Helvetica-Bold", 13)
        c.setFillColor(BrandColors.PRIMARY)
        
        # Valeur au-dessus de la jauge, centrée
        text_x = gauge_x + gauge_width / 2
        text_y = gauge_y + gauge_height + 0.3 * cm
        c.drawCentredString(text_x, text_y, value_text)
    
    def _draw_full_range_gauge(self, c, x, y, width, height):
        """Jauge avec plage de référence complète (min-max)"""
        # Calculer la plage d'affichage
        ref_range = self.ref_max - self.ref_min
        display_min = self.ref_min - ref_range * 0.5
        display_max = self.ref_max + ref_range * 0.5
        display_range = display_max - display_min
        
        if display_range <= 0:
            display_range = 1
        
        # Positions relatives
        normal_start = (self.ref_min - display_min) / display_range * width
        normal_width = (self.ref_max - self.ref_min) / display_range * width
        
        # Zone basse (orange)
        c.setFillColor(BrandColors.LOW)
        c.setStrokeColor(BrandColors.LOW)
        c.rect(x, y, normal_start, height, fill=1, stroke=0)
        
        # Zone normale (verte avec dégradé)
        c.setFillColor(BrandColors.NORMAL)
        c.setStrokeColor(BrandColors.NORMAL)
        c.rect(x + normal_start, y, normal_width, height, fill=1, stroke=0)
        
        # Zone haute (rouge)
        high_start = normal_start + normal_width
        high_width = width - high_start
        c.setFillColor(BrandColors.HIGH)
        c.setStrokeColor(BrandColors.HIGH)
        c.rect(x + high_start, y, high_width, height, fill=1, stroke=0)
        
        # Bordure élégante
        c.setStrokeColor(BrandColors.GREY)
        c.setLineWidth(1)
        c.roundRect(x, y, width, height, 0.2 * cm, fill=0, stroke=1)
        
        # Marqueur de valeur
        if display_min <= self.value <= display_max:
            value_pos = (self.value - display_min) / display_range * width
        elif self.value < display_min:
            value_pos = 0
        else:
            value_pos = width
        
        self._draw_marker(c, x + value_pos, y, height)
        
        # Légendes
        c.setFont("Helvetica", 8)
        c.setFillColor(BrandColors.GREY)
        c.drawString(x, y - 0.4 * cm, f"{self.ref_min:.1f}")
        c.drawRightString(x + width, y - 0.4 * cm, f"{self.ref_max:.1f}")
        c.drawCentredString(x + width / 2, y - 0.4 * cm, "Référence")
    
    def _draw_upper_limit_gauge(self, c, x, y, width, height):
        """Jauge pour valeur maximale (< max)"""
        display_max = self.ref_max * 1.5
        
        normal_width = (self.ref_max / display_max) * width
        
        # Zone normale (verte)
        c.setFillColor(BrandColors.NORMAL)
        c.rect(x, y, normal_width, height, fill=1, stroke=0)
        
        # Zone haute (rouge)
        c.setFillColor(BrandColors.HIGH)
        c.rect(x + normal_width, y, width - normal_width, height, fill=1, stroke=0)
        
        # Bordure
        c.setStrokeColor(BrandColors.GREY)
        c.setLineWidth(1)
        c.roundRect(x, y, width, height, 0.2 * cm, fill=0, stroke=1)
        
        # Marqueur
        if self.value <= display_max:
            value_pos = (self.value / display_max) * width
        else:
            value_pos = width
        
        self._draw_marker(c, x + value_pos, y, height)
        
        # Légende
        c.setFont("Helvetica", 8)
        c.setFillColor(BrandColors.GREY)
        c.drawString(x + normal_width - 0.5*cm, y - 0.4 * cm, f"< {self.ref_max:.1f}")
    
    def _draw_lower_limit_gauge(self, c, x, y, width, height):
        """Jauge pour valeur minimale (> min)"""
        display_max = self.ref_min * 2
        
        low_width = (self.ref_min / display_max) * width
        
        # Zone basse (orange)
        c.setFillColor(BrandColors.LOW)
        c.rect(x, y, low_width, height, fill=1, stroke=0)
        
        # Zone normale (verte)
        c.setFillColor(BrandColors.NORMAL)
        c.rect(x + low_width, y, width - low_width, height, fill=1, stroke=0)
        
        # Bordure
        c.setStrokeColor(BrandColors.GREY)
        c.setLineWidth(1)
        c.roundRect(x, y, width, height, 0.2 * cm, fill=0, stroke=1)
        
        # Marqueur
        if self.value <= display_max:
            value_pos = (self.value / display_max) * width
        else:
            value_pos = width
        
        self._draw_marker(c, x + value_pos, y, height)
        
        # Légende
        c.setFont("Helvetica", 8)
        c.setFillColor(BrandColors.GREY)
        c.drawString(x + low_width - 0.5*cm, y - 0.4 * cm, f"> {self.ref_min:.1f}")
    
    def _draw_value_only(self, c, x, y, width, height):
        """Affichage simple si pas de référence"""
        # Barre neutre
        c.setFillColor(BrandColors.LIGHT_GREY)
        c.roundRect(x, y, width, height, 0.2 * cm, fill=1, stroke=0)
        
        # Bordure
        c.setStrokeColor(BrandColors.GREY)
        c.setLineWidth(1)
        c.roundRect(x, y, width, height, 0.2 * cm, fill=0, stroke=1)
        
        # Message
        c.setFont("Helvetica-Oblique", 9)
        c.setFillColor(BrandColors.GREY)
        c.drawCentredString(x + width / 2, y + height / 2 - 0.15 * cm, "Pas de valeur de référence")
    
    def _draw_marker(self, c, x, y, height):
        """Dessine le marqueur de valeur actuelle"""
        # Triangle pointant vers la jauge
        c.setFillColor(BrandColors.PRIMARY_DARK)
        c.setStrokeColor(BrandColors.PRIMARY_DARK)
        c.setLineWidth(1.5)
        
        path = c.beginPath()
        path.moveTo(x, y + height + 0.05 * cm)
        path.lineTo(x - 0.2 * cm, y + height + 0.25 * cm)
        path.lineTo(x + 0.2 * cm, y + height + 0.25 * cm)
        path.close()
        c.drawPath(path, fill=1, stroke=1)
        
        # Ligne verticale
        c.setStrokeColor(BrandColors.PRIMARY_DARK)
        c.setLineWidth(2)
        c.line(x, y, x, y + height)


class MicrobiomeCard(Flowable):
    """Carte visuelle pour afficher les groupes bactériens"""
    
    def __init__(
        self,
        category: str,
        group_name: str,
        result: str,
        width: float = 8 * cm,
        height: float = 2 * cm,
    ):
        super().__init__()
        self.category = category
        self.group_name = group_name
        self.result = result.lower()
        self.width = width
        self.height = height
    
    def draw(self):
        c = self.canv
        
        # Couleur selon résultat
        if "expected" in self.result or "attendu" in self.result:
            bg_color = BrandColors.BG_LIGHT_BLUE
            icon_color = BrandColors.MICROBIOME_NORMAL
            icon = "✓"
        elif "slight" in self.result or "légèrement" in self.result:
            bg_color = colors.HexColor("#FFF3E0")
            icon_color = BrandColors.MICROBIOME_SLIGHT
            icon = "⚠"
        else:
            bg_color = colors.HexColor("#FFEBEE")
            icon_color = BrandColors.MICROBIOME_DEVIATION
            icon = "✗"
        
        # Fond de carte arrondi
        c.setFillColor(bg_color)
        c.setStrokeColor(icon_color)
        c.setLineWidth(2)
        c.roundRect(0, 0, self.width, self.height, 0.3 * cm, fill=1, stroke=1)
        
        # Icône
        c.setFont("Helvetica-Bold", 16)
        c.setFillColor(icon_color)
        c.drawString(0.3 * cm, self.height / 2 - 0.2 * cm, icon)
        
        # Catégorie
        c.setFont("Helvetica-Bold", 10)
        c.setFillColor(BrandColors.PRIMARY)
        c.drawString(1.2 * cm, self.height - 0.6 * cm, self.category)
        
        # Nom du groupe
        c.setFont("Helvetica", 9)
        c.setFillColor(BrandColors.DARK_GREY)
        
        # Tronquer si trop long
        group_display = self.group_name
        if len(group_display) > 45:
            group_display = group_display[:42] + "..."
        
        c.drawString(1.2 * cm, self.height / 2 - 0.2 * cm, group_display)
        
        # Résultat
        c.setFont("Helvetica-Bold", 8)
        c.setFillColor(icon_color)
        result_display = self.result.title()
        c.drawRightString(self.width - 0.3 * cm, 0.3 * cm, result_display)


class ScoreDonut(Flowable):
    """Graphique donut pour scores (dysbiose, diversité)"""
    
    def __init__(
        self,
        score: float,
        max_score: float,
        title: str,
        subtitle: str = "",
        width: float = 5 * cm,
        height: float = 5 * cm,
    ):
        super().__init__()
        self.score = max(0, min(score, max_score))
        self.max_score = max_score
        self.title = title
        self.subtitle = subtitle
        self.width = width
        self.height = height
    
    def draw(self):
        c = self.canv
        
        cx = self.width / 2
        cy = self.height / 2 + 0.5 * cm
        outer_radius = 1.5 * cm
        inner_radius = 1 * cm
        
        # Déterminer la couleur
        ratio = self.score / self.max_score if self.max_score > 0 else 0
        
        if ratio <= 0.4:
            color = BrandColors.NORMAL
        elif ratio <= 0.7:
            color = BrandColors.WARNING
        else:
            color = BrandColors.CRITICAL
        
        # Fond gris
        c.setFillColor(BrandColors.VERY_LIGHT_GREY)
        c.circle(cx, cy, outer_radius, fill=1, stroke=0)
        
        # Arc de score
        angle = 360 * ratio
        if angle > 0:
            c.setFillColor(color)
            path = c.beginPath()
            path.moveTo(cx, cy)
            path.arcTo(
                cx - outer_radius, cy - outer_radius,
                cx + outer_radius, cy + outer_radius,
                90, angle
            )
            path.close()
            c.drawPath(path, fill=1, stroke=0)
        
        # Trou central blanc
        c.setFillColor(colors.white)
        c.circle(cx, cy, inner_radius, fill=1, stroke=0)
        
        # Score au centre
        c.setFont("Helvetica-Bold", 18)
        c.setFillColor(BrandColors.PRIMARY)
        c.drawCentredString(cx, cy + 0.1 * cm, f"{int(self.score)}")
        
        c.setFont("Helvetica", 9)
        c.setFillColor(BrandColors.GREY)
        c.drawCentredString(cx, cy - 0.4 * cm, f"/ {int(self.max_score)}")
        
        # Titre
        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(BrandColors.DARK_GREY)
        c.drawCentredString(cx, 0.8 * cm, self.title)
        
        if self.subtitle:
            c.setFont("Helvetica", 8)
            c.setFillColor(BrandColors.GREY)
            c.drawCentredString(cx, 0.3 * cm, self.subtitle)


# ═══════════════════════════════════════════════════════════════════════════
# MAIN PDF GENERATOR CLASS
# ═══════════════════════════════════════════════════════════════════════════

class PremiumPDFGenerator:
    """Générateur PDF Premium pour ALGO-LIFE/UNILABS"""
    
    def __init__(self, output_path: str = "rapport_algolife_premium.pdf"):
        self.output_path = output_path
        self.doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm,
        )
        self.story = []
        self.styles = self._create_styles()
        
        # Page dimensions
        self.page_width = A4[0]
        self.page_height = A4[1]
    
    def _create_styles(self) -> Dict[str, ParagraphStyle]:
        """Crée les styles de paragraphes personnalisés"""
        styles = getSampleStyleSheet()
        
        custom_styles = {
            "Title": ParagraphStyle(
                "CustomTitle",
                parent=styles["Heading1"],
                fontSize=24,
                textColor=BrandColors.PRIMARY,
                spaceAfter=20,
                alignment=TA_CENTER,
                fontName="Helvetica-Bold",
            ),
            "Subtitle": ParagraphStyle(
                "CustomSubtitle",
                parent=styles["Heading2"],
                fontSize=14,
                textColor=BrandColors.GREY,
                spaceAfter=12,
                alignment=TA_CENTER,
                fontName="Helvetica",
            ),
            "SectionTitle": ParagraphStyle(
                "SectionTitle",
                parent=styles["Heading1"],
                fontSize=16,
                textColor=BrandColors.PRIMARY,
                spaceBefore=12,
                spaceAfter=12,
                fontName="Helvetica-Bold",
                borderWidth=2,
                borderColor=BrandColors.PRIMARY,
                borderPadding=8,
                backColor=BrandColors.BG_LIGHT_BLUE,
                borderRadius=5,
            ),
            "SubsectionTitle": ParagraphStyle(
                "SubsectionTitle",
                parent=styles["Heading2"],
                fontSize=13,
                textColor=BrandColors.PRIMARY_DARK,
                spaceBefore=10,
                spaceAfter=8,
                fontName="Helvetica-Bold",
            ),
            "Body": ParagraphStyle(
                "CustomBody",
                parent=styles["BodyText"],
                fontSize=10,
                textColor=BrandColors.DARK_GREY,
                alignment=TA_JUSTIFY,
                spaceAfter=6,
                leading=14,
            ),
            "BodySmall": ParagraphStyle(
                "BodySmall",
                parent=styles["BodyText"],
                fontSize=9,
                textColor=BrandColors.GREY,
                alignment=TA_LEFT,
                spaceAfter=4,
                leading=12,
            ),
            "InfoBox": ParagraphStyle(
                "InfoBox",
                parent=styles["BodyText"],
                fontSize=9,
                textColor=BrandColors.DARK_GREY,
                alignment=TA_LEFT,
                leftIndent=12,
                rightIndent=12,
                spaceAfter=8,
                backColor=BrandColors.BG_LIGHT_BLUE,
                borderWidth=1,
                borderColor=BrandColors.ACCENT,
                borderPadding=8,
                borderRadius=3,
            ),
            "WarningBox": ParagraphStyle(
                "WarningBox",
                parent=styles["BodyText"],
                fontSize=9,
                textColor=BrandColors.DARK_GREY,
                alignment=TA_LEFT,
                leftIndent=12,
                rightIndent=12,
                spaceAfter=8,
                backColor=colors.HexColor("#FFF3E0"),
                borderWidth=1,
                borderColor=BrandColors.WARNING,
                borderPadding=8,
                borderRadius=3,
            ),
        }
        
        return custom_styles
    
    # ═══════════════════════════════════════════════════════════════════════
    # PAGE DE GARDE
    # ═══════════════════════════════════════════════════════════════════════
    
    def add_cover_page(self, patient_data: Dict[str, Any]):
        """Page de garde élégante"""
        
        # Espaceur initial
        self.story.append(Spacer(1, 1*cm))
        
        # Logo ADN centré
        dna_logo = DNALogo(width=3*cm, height=3*cm)
        self.story.append(dna_logo)
        self.story.append(Spacer(1, 1*cm))
        
        # Titre principal
        title = Paragraph(
            "<b>UNILABS</b><br/>ALGO-LIFE",
            self.styles["Title"]
        )
        self.story.append(title)
        self.story.append(Spacer(1, 0.3*cm))
        
        # Sous-titre
        subtitle = Paragraph(
            "Analyse Multimodale de Biologie Fonctionnelle",
            self.styles["Subtitle"]
        )
        self.story.append(subtitle)
        self.story.append(Spacer(1, 2*cm))
        
        # Informations patient dans un cadre élégant
        # Support des deux formats: "nom"/"name", "sexe"/"sex"
        patient_name = _safe_str(
            patient_data.get("nom") or patient_data.get("name") or "N/A"
        )
        patient_age = _safe_str(
            patient_data.get("age") or patient_data.get("âge") or "N/A"
        )
        patient_sex = _safe_str(
            patient_data.get("sexe") or patient_data.get("sex") or "N/A"
        )
        date_rapport = datetime.now().strftime("%d/%m/%Y")
        
        patient_info = f"""
        <para alignment="center" spaceBefore="12" spaceAfter="12">
        <b>Informations Patient</b><br/>
        <br/>
        <b>Nom:</b> {patient_name}<br/>
        <b>Âge:</b> {patient_age} ans<br/>
        <b>Sexe:</b> {patient_sex}<br/>
        <br/>
        <b>Date du rapport:</b> {date_rapport}
        </para>
        """
        
        patient_para = Paragraph(patient_info, self.styles["Body"])
        
        # Tableau pour encadrer
        patient_table = Table(
            [[patient_para]],
            colWidths=[12*cm]
        )
        patient_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.white),
            ('BOX', (0, 0), (-1, -1), 2, BrandColors.PRIMARY),
            ('ROUNDEDCORNERS', [10, 10, 10, 10]),
            ('LEFTPADDING', (0, 0), (-1, -1), 20),
            ('RIGHTPADDING', (0, 0), (-1, -1), 20),
            ('TOPPADDING', (0, 0), (-1, -1), 15),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
        ]))
        
        self.story.append(patient_table)
        self.story.append(Spacer(1, 3*cm))
        
        # Pied de page de couverture
        footer_text = """
        <para alignment="center">
        <font size="9" color="#757575">
        Dr Thibault SUTTER, PhD<br/>
        Biologiste spécialisé en biologie fonctionnelle<br/>
        UNILABS Group<br/>
        <br/>
        <b>CONFIDENTIEL - Usage médical uniquement</b>
        </font>
        </para>
        """
        self.story.append(Paragraph(footer_text, self.styles["BodySmall"]))
        
        # Page break
        self.story.append(PageBreak())
    
    # ═══════════════════════════════════════════════════════════════════════
    # SECTION BIOLOGIE
    # ═══════════════════════════════════════════════════════════════════════
    
    def add_biology_section(self, biology_data: Dict[str, Any]):
        """Section biologie avec cartes modernes comme la capture d'écran"""
        
        # Titre de section
        self.story.append(Paragraph(
            "🔬 ANALYSE BIOLOGIQUE",
            self.styles["SectionTitle"]
        ))
        self.story.append(Spacer(1, 0.5*cm))
        
        # Introduction
        intro_text = """
        Cette section présente l'analyse détaillée de vos biomarqueurs biologiques.
        Chaque paramètre est visualisé par rapport à ses valeurs de référence optimales.
        """
        self.story.append(Paragraph(intro_text, self.styles["Body"]))
        self.story.append(Spacer(1, 0.5*cm))
        
        # Récupérer les biomarqueurs - SUPPORT DES DEUX FORMATS
        # Format 1: {"biomarkers": {"Nom": {...}}}
        # Format 2: {"Nom": {...}} (format app.py direct)
        if "biomarkers" in biology_data:
            biomarkers = biology_data["biomarkers"]
        else:
            # Format direct de app.py
            biomarkers = {k: v for k, v in biology_data.items() if isinstance(v, dict)}
        
        if not biomarkers:
            self.story.append(Paragraph(
                "<i>Aucun biomarqueur disponible</i>",
                self.styles["BodySmall"]
            ))
            return
        
        # Grouper les biomarqueurs par catégorie
        categorized = self._categorize_biomarkers(biomarkers)
        
        for category, markers in categorized.items():
            # Titre de catégorie
            if category != "Autres":
                self.story.append(Paragraph(
                    f"<b>{category}</b>",
                    self.styles["SubsectionTitle"]
                ))
                self.story.append(Spacer(1, 0.3*cm))
            
            # Afficher les biomarqueurs en cartes 2x2
            self._add_biomarker_cards_grid(markers)
            self.story.append(Spacer(1, 0.5*cm))
        
        self.story.append(PageBreak())
    
    def _add_biomarker_cards_grid(self, markers: Dict[str, Any]):
        """Affiche les biomarqueurs en grille de cartes 2x2 comme la capture d'écran"""
        
        marker_items = list(markers.items())
        cards_data = []
        row = []
        
        for marker_name, marker_data in marker_items:
            # Créer la carte pour ce biomarqueur
            card = self._create_biomarker_card(marker_name, marker_data)
            row.append(card)
            
            # 2 cartes par ligne
            if len(row) == 2:
                cards_data.append(row)
                row = []
        
        # Ajouter la dernière ligne si impaire
        if row:
            cards_data.append(row + [Spacer(1, 1)])
        
        # Créer la table de cartes
        if cards_data:
            cards_table = Table(
                cards_data,
                colWidths=[8.5*cm, 8.5*cm],
                rowHeights=[4*cm] * len(cards_data)
            )
            cards_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            
            self.story.append(cards_table)
    
    def _create_biomarker_card(self, name: str, data: Dict[str, Any]) -> 'BiomarkerCard':
        """Crée une carte biomarqueur moderne comme la capture d'écran"""
        
        value = _safe_float(data.get("value", 0))
        unit = _safe_str(data.get("unit", ""))
        reference = _safe_str(data.get("reference", ""))
        status = _safe_str(data.get("status", "Normal"))
        
        # Parser la référence
        ref_min, ref_max = parse_reference_range(reference)
        
        return BiomarkerCard(
            name=name,
            value=value,
            ref_min=ref_min,
            ref_max=ref_max,
            unit=unit,
            status=status,
            width=8*cm,
            height=3.5*cm,
        )
    
    def _categorize_biomarkers(self, biomarkers: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Catégorise les biomarqueurs par type"""
        
        categories = {
            "Hormones": {},
            "Métabolisme": {},
            "Inflammation": {},
            "Vitamines & Minéraux": {},
            "Autres": {},
        }
        
        # Mots-clés pour catégorisation
        hormone_keywords = [
            "testostérone", "oestradiol", "progestérone", "cortisol",
            "dhea", "tsh", "t3", "t4", "insuline", "igf"
        ]
        
        metabolism_keywords = [
            "glucose", "cholestérol", "hdl", "ldl", "triglycérides",
            "hba1c", "créatinine", "urée", "acide urique"
        ]
        
        inflammation_keywords = [
            "crp", "ferritine", "homocystéine", "fibrinogène"
        ]
        
        vitamin_keywords = [
            "vitamine", "vitamin", "zinc", "magnésium", "fer",
            "calcium", "sélénium", "b12", "folate", "d3"
        ]
        
        for marker_name, marker_data in biomarkers.items():
            name_lower = marker_name.lower()
            
            categorized = False
            
            if any(kw in name_lower for kw in hormone_keywords):
                categories["Hormones"][marker_name] = marker_data
                categorized = True
            elif any(kw in name_lower for kw in metabolism_keywords):
                categories["Métabolisme"][marker_name] = marker_data
                categorized = True
            elif any(kw in name_lower for kw in inflammation_keywords):
                categories["Inflammation"][marker_name] = marker_data
                categorized = True
            elif any(kw in name_lower for kw in vitamin_keywords):
                categories["Vitamines & Minéraux"][marker_name] = marker_data
                categorized = True
            
            if not categorized:
                categories["Autres"][marker_name] = marker_data
        
        # Supprimer les catégories vides
        return {k: v for k, v in categories.items() if v}
    
    def _add_biomarker_gauge(self, name: str, data: Dict[str, Any]):
        """Ajoute une jauge pour un biomarqueur"""
        
        value = _safe_float(data.get("value", 0))
        unit = _safe_str(data.get("unit", ""))
        reference = _safe_str(data.get("reference", ""))
        status = _safe_str(data.get("status", "Normal"))
        
        # Parser la référence
        ref_min, ref_max = parse_reference_range(reference)
        
        # Créer la jauge
        gauge = PremiumGauge(
            name=name,
            value=value,
            ref_min=ref_min,
            ref_max=ref_max,
            unit=unit,
            status=status,
            width=16*cm,
            height=2.5*cm,
        )
        
        self.story.append(gauge)
        
        # Si recommandation spécifique, l'afficher
        recommendation = _safe_str(data.get("recommendation", "")).strip()
        if recommendation:
            rec_para = Paragraph(
                f"<i>💡 {recommendation}</i>",
                self.styles["InfoBox"]
            )
            self.story.append(Spacer(1, 0.2*cm))
            self.story.append(rec_para)
    
    # ═══════════════════════════════════════════════════════════════════════
    # SECTION MICROBIOTE
    # ═══════════════════════════════════════════════════════════════════════
    
    def add_microbiome_section(self, microbiome_data: Dict[str, Any]):
        """Section microbiote avec visualisations modernes"""
        
        # Titre de section
        self.story.append(Paragraph(
            "🦠 ANALYSE DU MICROBIOTE INTESTINAL",
            self.styles["SectionTitle"]
        ))
        self.story.append(Spacer(1, 0.5*cm))
        
        # Introduction
        intro_text = """
        Cette section présente l'analyse de votre microbiote intestinal (GutMAP).
        L'équilibre de votre flore intestinale est un facteur clé de votre santé globale.
        """
        self.story.append(Paragraph(intro_text, self.styles["Body"]))
        self.story.append(Spacer(1, 0.5*cm))
        
        # === SCORES GLOBAUX ===
        dysbiosis_index = microbiome_data.get("dysbiosis_index")
        diversity = microbiome_data.get("diversity")
        
        if dysbiosis_index is not None or diversity is not None:
            self.story.append(Paragraph(
                "<b>Scores Globaux</b>",
                self.styles["SubsectionTitle"]
            ))
            self.story.append(Spacer(1, 0.3*cm))
            
            # Table pour les donuts côte à côte
            donuts = []
            
            if dysbiosis_index is not None:
                donut_dysbiosis = ScoreDonut(
                    score=dysbiosis_index,
                    max_score=5,
                    title="Indice de Dysbiose",
                    subtitle="(1=Normal, 5=Sévère)",
                    width=6*cm,
                    height=5*cm,
                )
                donuts.append(donut_dysbiosis)
            
            if diversity is not None and isinstance(diversity, str):
                # Convertir la diversité textuelle en score
                diversity_lower = diversity.lower()
                if "high" in diversity_lower or "élevée" in diversity_lower:
                    diversity_score = 1
                elif "moderate" in diversity_lower or "modérée" in diversity_lower:
                    diversity_score = 2
                else:
                    diversity_score = 3
                
                donut_diversity = ScoreDonut(
                    score=diversity_score,
                    max_score=3,
                    title="Diversité Bactérienne",
                    subtitle=diversity,
                    width=6*cm,
                    height=5*cm,
                )
                donuts.append(donut_diversity)
            
            if donuts:
                # Afficher les donuts côte à côte
                donut_table = Table(
                    [[donuts]],
                    colWidths=[17*cm],
                    rowHeights=[6*cm]
                )
                donut_table.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ]))
                self.story.append(donut_table)
                self.story.append(Spacer(1, 0.5*cm))
        
        # === GROUPES BACTÉRIENS ===
        bacteria = microbiome_data.get("bacteria", [])
        
        if bacteria:
            self.story.append(Paragraph(
                "<b>Groupes Bactériens Analysés</b>",
                self.styles["SubsectionTitle"]
            ))
            self.story.append(Spacer(1, 0.3*cm))
            
            # Organiser les cartes par groupe de 2
            cards_data = []
            row = []
            
            for bact in bacteria:
                category = _safe_str(bact.get("category", ""))
                group = _safe_str(bact.get("group", ""))
                result = _safe_str(bact.get("result", "Expected"))
                
                card = MicrobiomeCard(
                    category=category,
                    group_name=group,
                    result=result,
                    width=8*cm,
                    height=2*cm,
                )
                
                row.append(card)
                
                if len(row) == 2:
                    cards_data.append(row)
                    row = []
            
            # Ajouter la dernière ligne si impaire
            if row:
                cards_data.append(row + [Spacer(1, 1)])
            
            # Créer la table de cartes
            cards_table = Table(
                cards_data,
                colWidths=[8.5*cm, 8.5*cm],
                rowHeights=[2.3*cm] * len(cards_data)
            )
            cards_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            
            self.story.append(cards_table)
        
        self.story.append(PageBreak())
    
    # ═══════════════════════════════════════════════════════════════════════
    # SECTION ANALYSE CROISÉE
    # ═══════════════════════════════════════════════════════════════════════
    
    def add_cross_analysis_section(self, cross_analysis: Dict[str, Any]):
        """Section analyse croisée multimodale améliorée"""
        
        if not cross_analysis:
            return
        
        # Récupérer les données - support de plusieurs formats
        cross_analysis_list = cross_analysis.get("cross_analysis", [])
        priority_actions = cross_analysis.get("priority_actions", [])
        
        # Si vide, ne pas afficher la section
        if not cross_analysis_list and not priority_actions:
            return
        
        # Titre de section
        self.story.append(Paragraph(
            "🔄 ANALYSE CROISÉE MULTIMODALE",
            self.styles["SectionTitle"]
        ))
        self.story.append(Spacer(1, 0.5*cm))
        
        # Introduction
        intro_text = """
        Cette section présente les corrélations identifiées entre vos données biologiques
        et votre microbiote, permettant une approche intégrée et personnalisée de votre santé.
        """
        self.story.append(Paragraph(intro_text, self.styles["Body"]))
        self.story.append(Spacer(1, 0.5*cm))
        
        # === OBSERVATIONS / CROSS ANALYSIS ===
        if cross_analysis_list:
            self.story.append(Paragraph(
                "<b>🔍 Observations croisées</b>",
                self.styles["SubsectionTitle"]
            ))
            self.story.append(Spacer(1, 0.3*cm))
            
            for item in cross_analysis_list:
                # Extraire le texte selon le format
                if isinstance(item, dict):
                    obs_text = _safe_str(item.get("text", item.get("observation", item.get("description", ""))))
                    category = _safe_str(item.get("category", item.get("type", "info"))).lower()
                else:
                    obs_text = _safe_str(item)
                    category = "info"
                
                if not obs_text:
                    continue
                
                # Couleur selon catégorie
                if "critique" in category or "critical" in category or "urgent" in category:
                    bg_color = colors.HexColor("#FFEBEE")
                    border_color = BrandColors.CRITICAL
                    icon = "🔴"
                elif "attention" in category or "warning" in category:
                    bg_color = colors.HexColor("#FFF3E0")
                    border_color = BrandColors.WARNING
                    icon = "🟡"
                else:
                    bg_color = colors.HexColor("#E3F2FD")
                    border_color = BrandColors.PRIMARY
                    icon = "🔵"
                
                obs_para = Paragraph(f"{icon} {obs_text}", self.styles["Body"])
                
                obs_table = Table([[obs_para]], colWidths=[16*cm])
                obs_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), bg_color),
                    ('BOX', (0, 0), (-1, -1), 1.5, border_color),
                    ('LEFTPADDING', (0, 0), (-1, -1), 12),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 12),
                    ('TOPPADDING', (0, 0), (-1, -1), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                    ('ROUNDEDCORNERS', [5, 5, 5, 5]),
                ]))
                
                self.story.append(obs_table)
                self.story.append(Spacer(1, 0.3*cm))
        
        # === ACTIONS PRIORITAIRES ===
        if priority_actions:
            self.story.append(Spacer(1, 0.3*cm))
            self.story.append(Paragraph(
                "<b>⚡ Actions prioritaires recommandées</b>",
                self.styles["SubsectionTitle"]
            ))
            self.story.append(Spacer(1, 0.3*cm))
            
            for i, action in enumerate(priority_actions, 1):
                # Extraire le texte selon le format
                if isinstance(action, dict):
                    action_text = _safe_str(action.get("text", action.get("action", action.get("description", ""))))
                    priority = _safe_str(action.get("priority", "medium")).lower()
                else:
                    action_text = _safe_str(action)
                    priority = "medium"
                
                if not action_text:
                    continue
                
                # Icône selon priorité
                if priority == "high" or priority == "élevée":
                    icon = "🔴"
                    bg_color = colors.HexColor("#FFEBEE")
                    border_color = BrandColors.CRITICAL
                elif priority == "low" or priority == "basse":
                    icon = "🟢"
                    bg_color = colors.HexColor("#E8F5E9")
                    border_color = BrandColors.NORMAL
                else:
                    icon = "🟡"
                    bg_color = colors.HexColor("#FFF3E0")
                    border_color = BrandColors.WARNING
                
                action_para = Paragraph(f"<b>{i}.</b> {icon} {action_text}", self.styles["Body"])
                
                action_table = Table([[action_para]], colWidths=[16*cm])
                action_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), bg_color),
                    ('BOX', (0, 0), (-1, -1), 2, border_color),
                    ('LEFTPADDING', (0, 0), (-1, -1), 12),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 12),
                    ('TOPPADDING', (0, 0), (-1, -1), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                    ('ROUNDEDCORNERS', [5, 5, 5, 5]),
                ]))
                
                self.story.append(action_table)
                self.story.append(Spacer(1, 0.3*cm))
        
        self.story.append(PageBreak())
    
    # ═══════════════════════════════════════════════════════════════════════
    # SECTION RECOMMANDATIONS
    # ═══════════════════════════════════════════════════════════════════════
    
    def add_recommendations_section(self, recommendations: Dict[str, Any]):
        """Section recommandations regroupées et structurées - Support format app.py"""
        
        # Titre de section
        self.story.append(Paragraph(
            "💊 RECOMMANDATIONS PERSONNALISÉES",
            self.styles["SectionTitle"]
        ))
        self.story.append(Spacer(1, 0.5*cm))
        
        # Introduction
        intro_text = """
        Ces recommandations sont générées automatiquement par ALGO-LIFE sur la base
        de votre profil multimodal (biologie + microbiote). Elles visent à optimiser
        votre santé selon une approche de biologie fonctionnelle.
        """
        self.story.append(Paragraph(intro_text, self.styles["Body"]))
        self.story.append(Spacer(1, 0.3*cm))
        
        # Warning box
        warning = Paragraph(
            "⚠️ <b>Important:</b> Ces suggestions ne remplacent pas un avis médical. "
            "Consultez votre médecin avant toute nouvelle supplémentation.",
            self.styles["WarningBox"]
        )
        self.story.append(warning)
        self.story.append(Spacer(1, 0.5*cm))
        
        # Support de plusieurs formats: {"raw": {...}, "edited": {...}} ou direct {...}
        reco_data = recommendations.get("raw", recommendations) if "raw" in recommendations else recommendations
        edited_data = recommendations.get("edited", {})
        
        # Merger les données edited si présentes
        if edited_data:
            for key in ["nutrition", "micronutrition", "microbiome", "lifestyle", "supplementation"]:
                if key in edited_data and edited_data[key]:
                    reco_data[key] = edited_data[key]
        
        # === RECOMMANDATIONS NUTRITION ===
        nutrition_recs = reco_data.get("nutrition", reco_data.get("Nutrition", []))
        if nutrition_recs:
            self._add_recommendation_subsection(
                "🥗 NUTRITION",
                nutrition_recs,
                BrandColors.NORMAL
            )
        
        # === RECOMMANDATIONS MICRONUTRITION ===
        micronutrition_recs = reco_data.get("micronutrition", reco_data.get("Micronutrition", []))
        if micronutrition_recs:
            self._add_recommendation_subsection(
                "💊 MICRONUTRITION & SUPPLÉMENTATION",
                micronutrition_recs,
                BrandColors.PRIMARY
            )
        
        # === RECOMMANDATIONS MICROBIOTE ===
        microbiome_recs = reco_data.get("microbiome", reco_data.get("Microbiome", []))
        if microbiome_recs:
            self._add_recommendation_subsection(
                "🦠 MICROBIOTE",
                microbiome_recs,
                BrandColors.DNA_PRIMARY
            )
        
        # === RECOMMANDATIONS LIFESTYLE ===
        lifestyle_recs = reco_data.get("lifestyle", reco_data.get("Lifestyle", []))
        if lifestyle_recs:
            self._add_recommendation_subsection(
                "🏃 LIFESTYLE",
                lifestyle_recs,
                BrandColors.ACCENT
            )
        
        # === SUPPLÉMENTATION DÉTAILLÉE ===
        supplementation = reco_data.get("supplementation", reco_data.get("Supplementation", []))
        if supplementation:
            self.story.append(Spacer(1, 0.5*cm))
            self.story.append(Paragraph(
                "<b>Protocole de Supplémentation Détaillé</b>",
                self.styles["SubsectionTitle"]
            ))
            self.story.append(Spacer(1, 0.3*cm))
            
            # Table de supplémentation
            suppl_data = [
                [
                    Paragraph("<b>Supplément</b>", self.styles["BodySmall"]),
                    Paragraph("<b>Dosage</b>", self.styles["BodySmall"]),
                    Paragraph("<b>Fréquence</b>", self.styles["BodySmall"]),
                    Paragraph("<b>Durée</b>", self.styles["BodySmall"]),
                    Paragraph("<b>Objectif</b>", self.styles["BodySmall"]),
                ]
            ]
            
            for suppl in supplementation:
                nom = _safe_str(suppl.get("nom", suppl.get("name", "N/A")))
                dosage = _safe_str(suppl.get("dosage", suppl.get("dose", "N/A")))
                frequence = _safe_str(suppl.get("frequence", suppl.get("frequency", "N/A")))
                duree = _safe_str(suppl.get("duree", suppl.get("duration", "N/A")))
                objectif = _safe_str(suppl.get("objectif", suppl.get("goal", suppl.get("objective", "N/A"))))
                
                suppl_data.append([
                    Paragraph(nom, self.styles["BodySmall"]),
                    Paragraph(dosage, self.styles["BodySmall"]),
                    Paragraph(frequence, self.styles["BodySmall"]),
                    Paragraph(duree, self.styles["BodySmall"]),
                    Paragraph(objectif, self.styles["BodySmall"]),
                ])
            
            suppl_table = Table(
                suppl_data,
                colWidths=[3.5*cm, 2.5*cm, 2.5*cm, 2*cm, 6.5*cm]
            )
            suppl_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), BrandColors.PRIMARY),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, BrandColors.LIGHT_GREY),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, BrandColors.VERY_LIGHT_GREY]),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ]))
            
            self.story.append(suppl_table)
        
        self.story.append(PageBreak())
    
    def _add_recommendation_subsection(
        self,
        title: str,
        recommendations: List[Any],
        color: colors.Color
    ):
        """Ajoute une sous-section de recommandations - Support strings et dicts"""
        
        self.story.append(Paragraph(title, self.styles["SubsectionTitle"]))
        self.story.append(Spacer(1, 0.3*cm))
        
        for i, rec in enumerate(recommendations, 1):
            # Support de plusieurs formats
            if isinstance(rec, dict):
                rec_text = _safe_str(rec.get("text", rec.get("recommendation", rec.get("description", ""))))
                priority = _safe_str(rec.get("priority", "medium")).lower()
            else:
                # String simple
                rec_text = _safe_str(rec)
                priority = "medium"
            
            if not rec_text:
                continue
            
            # Icône de priorité
            if priority == "high" or priority == "élevée" or priority == "haute":
                icon = "🔴"
            elif priority == "medium" or priority == "moyenne":
                icon = "🟡"
            else:
                icon = "🟢"
            
            rec_para = Paragraph(f"{icon} {rec_text}", self.styles["Body"])
            
            # Encadrer dans un tableau pour le style
            rec_table = Table(
                [[rec_para]],
                colWidths=[16*cm]
            )
            rec_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.white),
                ('BOX', (0, 0), (-1, -1), 1, color),
                ('LEFTPADDING', (0, 0), (-1, -1), 10),
                ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ]))
            
            self.story.append(rec_table)
            self.story.append(Spacer(1, 0.3*cm))
    
    # ═══════════════════════════════════════════════════════════════════════
    # SECTION SUIVI
    # ═══════════════════════════════════════════════════════════════════════
    
    def add_follow_up_section(self, follow_up: Dict[str, Any]):
        """Section plan de suivi - Support format app.py"""
        
        # Titre de section
        self.story.append(Paragraph(
            "📅 PLAN DE SUIVI",
            self.styles["SectionTitle"]
        ))
        self.story.append(Spacer(1, 0.5*cm))
        
        # Introduction
        intro_text = """
        Plan de contrôles recommandé pour évaluer l'efficacité des interventions
        et ajuster le protocole si nécessaire.
        """
        self.story.append(Paragraph(intro_text, self.styles["Body"]))
        self.story.append(Spacer(1, 0.5*cm))
        
        # Support de plusieurs formats
        # Format 1: {"controles": [...]} (ancien)
        # Format 2: {"next_date": ..., "next_tests": ..., "plan": ...} (app.py)
        
        # Vérifier s'il y a des contrôles (ancien format)
        controles = follow_up.get("controles", [])
        
        if controles:
            # Ancien format avec contrôles
            controle_data = [
                [
                    Paragraph("<b>Type d'analyse</b>", self.styles["BodySmall"]),
                    Paragraph("<b>Délai</b>", self.styles["BodySmall"]),
                    Paragraph("<b>Biomarqueurs à surveiller</b>", self.styles["BodySmall"]),
                ]
            ]
            
            for controle in controles:
                type_analyse = _safe_str(controle.get("type", "N/A"))
                delai = _safe_str(controle.get("delai", "N/A"))
                biomarqueurs = controle.get("biomarqueurs", [])
                
                if isinstance(biomarqueurs, list):
                    biomarqueurs_str = ", ".join(biomarqueurs)
                else:
                    biomarqueurs_str = _safe_str(biomarqueurs)
                
                controle_data.append([
                    Paragraph(type_analyse, self.styles["BodySmall"]),
                    Paragraph(delai, self.styles["BodySmall"]),
                    Paragraph(biomarqueurs_str, self.styles["BodySmall"]),
                ])
            
            controle_table = Table(
                controle_data,
                colWidths=[4*cm, 3*cm, 10*cm]
            )
            controle_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), BrandColors.ACCENT),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, BrandColors.LIGHT_GREY),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, BrandColors.VERY_LIGHT_GREY]),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ]))
            
            self.story.append(controle_table)
        
        # Format app.py
        next_date = _safe_str(follow_up.get("next_date", "")).strip()
        next_tests = _safe_str(follow_up.get("next_tests", "")).strip()
        plan = _safe_str(follow_up.get("plan", "")).strip()
        clinician_notes = _safe_str(follow_up.get("clinician_notes", "")).strip()
        
        if next_date or next_tests or plan:
            # Date du prochain contrôle
            if next_date:
                self.story.append(Spacer(1, 0.3*cm))
                self.story.append(Paragraph(
                    f"<b>📆 Date du prochain contrôle:</b> {next_date}",
                    self.styles["Body"]
                ))
            
            # Analyses recommandées
            if next_tests:
                self.story.append(Spacer(1, 0.3*cm))
                self.story.append(Paragraph(
                    "<b>🔬 Analyses recommandées:</b>",
                    self.styles["SubsectionTitle"]
                ))
                self.story.append(Spacer(1, 0.2*cm))
                
                # Afficher dans un cadre
                tests_para = Paragraph(next_tests, self.styles["Body"])
                tests_table = Table([[tests_para]], colWidths=[16*cm])
                tests_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), BrandColors.BG_LIGHT_BLUE),
                    ('BOX', (0, 0), (-1, -1), 1, BrandColors.ACCENT),
                    ('LEFTPADDING', (0, 0), (-1, -1), 12),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 12),
                    ('TOPPADDING', (0, 0), (-1, -1), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                    ('ROUNDEDCORNERS', [5, 5, 5, 5]),
                ]))
                self.story.append(tests_table)
            
            # Plan de suivi
            if plan:
                self.story.append(Spacer(1, 0.3*cm))
                self.story.append(Paragraph(
                    "<b>📋 Plan de suivi:</b>",
                    self.styles["SubsectionTitle"]
                ))
                self.story.append(Spacer(1, 0.2*cm))
                
                plan_para = Paragraph(plan, self.styles["Body"])
                plan_table = Table([[plan_para]], colWidths=[16*cm])
                plan_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#FFF9E6")),
                    ('BOX', (0, 0), (-1, -1), 1.5, colors.HexColor("#FFD700")),
                    ('LEFTPADDING', (0, 0), (-1, -1), 12),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 12),
                    ('TOPPADDING', (0, 0), (-1, -1), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                    ('ROUNDEDCORNERS', [5, 5, 5, 5]),
                ]))
                self.story.append(plan_table)
        
        # Notes cliniques (ne pas afficher dans le PDF patient)
        # Ces notes sont pour usage interne uniquement
    
    # ═══════════════════════════════════════════════════════════════════════
    # FOOTER & GENERATION
    # ═══════════════════════════════════════════════════════════════════════
    
    def add_footer(self):
        """Ajoute le pied de page final"""
        
        self.story.append(PageBreak())
        self.story.append(Spacer(1, 3*cm))
        
        # Logo ADN petit
        dna_logo = DNALogo(width=1.5*cm, height=1.5*cm)
        self.story.append(dna_logo)
        self.story.append(Spacer(1, 0.5*cm))
        
        footer_text = """
        <para alignment="center">
        <b>ALGO-LIFE © 2026</b><br/>
        Powered by UNILABS Group<br/>
        <br/>
        <b>Dr Thibault SUTTER, PhD</b><br/>
        Biologiste spécialisé en biologie fonctionnelle<br/>
        15+ années d'expertise en médecine fonctionnelle<br/>
        <br/>
        <i>Ce rapport est généré automatiquement par analyse multimodale IA.<br/>
        Il ne remplace pas un avis médical personnalisé.</i><br/>
        <br/>
        📧 contact@algo-life.com | 🌐 www.algo-life.com<br/>
        📍 Genève, Suisse
        </para>
        """
        
        self.story.append(Paragraph(footer_text, self.styles["BodySmall"]))
    
    def generate(self, data: Dict[str, Any]) -> str:
        """Génère le rapport PDF complet"""
        
        # Page de garde
        self.add_cover_page(data.get("patient", {}))
        
        # Biologie
        if data.get("biologie"):
            self.add_biology_section(data["biologie"])
        
        # Microbiote
        if data.get("microbiote"):
            self.add_microbiome_section(data["microbiote"])
        
        # Analyse croisée
        if data.get("cross_analysis"):
            self.add_cross_analysis_section(data["cross_analysis"])
        
        # Recommandations
        if data.get("recommendations"):
            self.add_recommendations_section(data["recommendations"])
        
        # Suivi
        if data.get("follow_up"):
            self.add_follow_up_section(data["follow_up"])
        
        # Footer
        self.add_footer()
        
        # Build
        self.doc.build(self.story)
        
        return self.output_path


# ═══════════════════════════════════════════════════════════════════════════
# FONCTION PRINCIPALE
# ═══════════════════════════════════════════════════════════════════════════

def generate_premium_report(
    patient_data: Dict[str, Any],
    biology_data: Dict[str, Any] = None,
    microbiome_data: Dict[str, Any] = None,
    cross_analysis: Dict[str, Any] = None,
    recommendations: Dict[str, Any] = None,
    follow_up: Dict[str, Any] = None,
    output_path: str = "rapport_algolife_premium.pdf",
) -> str:
    """
    Génère un rapport premium ALGO-LIFE/UNILABS
    
    Args:
        patient_data: Infos patient (nom, âge, sexe)
        biology_data: Données biologie {biomarkers: {...}}
        microbiome_data: Données microbiote {dysbiosis_index, diversity, bacteria}
        cross_analysis: Analyse croisée (optionnel, intégré dans les recommandations)
        recommendations: Recommandations {nutrition, micronutrition, microbiome, lifestyle, supplementation}
        follow_up: Plan de suivi {controles: [...]}
        output_path: Chemin du PDF de sortie
    
    Returns:
        Chemin du fichier PDF généré
    """
    
    data = {
        "patient": patient_data or {},
        "biologie": biology_data or {},
        "microbiote": microbiome_data or {},
        "cross_analysis": cross_analysis or {},
        "recommendations": recommendations or {},
        "follow_up": follow_up or {},
    }
    
    generator = PremiumPDFGenerator(output_path)
    return generator.generate(data)


def generate_multimodal_report(
    patient_data: Dict[str, Any],
    biology_data: Dict[str, Any] = None,
    microbiome_data: Dict[str, Any] = None,
    cross_analysis: Dict[str, Any] = None,
    recommendations: Dict[str, Any] = None,
    follow_up: Dict[str, Any] = None,
    output_path: str = "rapport_multimodal.pdf",
) -> str:
    """
    Génère un rapport multimodal ALGO-LIFE/UNILABS
    
    ALIAS de generate_premium_report pour compatibilité avec ancien code.
    
    Args:
        patient_data: Infos patient (nom, âge, sexe)
        biology_data: Données biologie {biomarkers: {...}}
        microbiome_data: Données microbiote {dysbiosis_index, diversity, bacteria}
        cross_analysis: Analyse croisée (optionnel)
        recommendations: Recommandations {nutrition, micronutrition, microbiome, lifestyle, supplementation}
        follow_up: Plan de suivi {controles: [...]}
        output_path: Chemin du PDF de sortie
    
    Returns:
        Chemin du fichier PDF généré
    """
    return generate_premium_report(
        patient_data=patient_data,
        biology_data=biology_data,
        microbiome_data=microbiome_data,
        cross_analysis=cross_analysis,
        recommendations=recommendations,
        follow_up=follow_up,
        output_path=output_path,
    )


if __name__ == "__main__":
    print("✅ PDF Generator Premium chargé avec succès!")
    print("📄 ALGO-LIFE / UNILABS - Version 2.0")
    print("🎨 Design haut de gamme avec visualisations modernes")
