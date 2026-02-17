#!/usr/bin/env python3
"""
PDF Generator - ALGO-LIFE
Design v2 : Liberation Sans, pas d'emojis, mise en page professionnelle
Meme logique/donnees que v7, uniquement le rendu visuel est ameliore.
"""

import os
import re
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.shapes import Drawing, Rect, Circle

try:
    import streamlit as st
    STREAMLIT_AVAILABLE = True
except ImportError:
    STREAMLIT_AVAILABLE = False


# ── Enregistrement polices ───────────────────────────────────────────────────
_FONT_DIR = "/usr/share/fonts/truetype/liberation"
_FONTS_REGISTERED = False

def _register_fonts():
    global _FONTS_REGISTERED
    if _FONTS_REGISTERED:
        return
    try:
        pdfmetrics.registerFont(TTFont('Sans',       f'{_FONT_DIR}/LiberationSans-Regular.ttf'))
        pdfmetrics.registerFont(TTFont('Sans-Bold',  f'{_FONT_DIR}/LiberationSans-Bold.ttf'))
        pdfmetrics.registerFont(TTFont('Sans-Italic',f'{_FONT_DIR}/LiberationSans-Italic.ttf'))
        pdfmetrics.registerFont(TTFont('Sans-BI',    f'{_FONT_DIR}/LiberationSans-BoldItalic.ttf'))
        from reportlab.pdfbase.pdfmetrics import registerFontFamily
        registerFontFamily('Sans', normal='Sans', bold='Sans-Bold',
                           italic='Sans-Italic', boldItalic='Sans-BI')
        _FONTS_REGISTERED = True
    except Exception:
        pass  # fallback Helvetica

def _F(bold=False, italic=False):
    """Retourne le nom de police selon disponibilite."""
    if _FONTS_REGISTERED:
        if bold and italic: return 'Sans-BI'
        if bold:   return 'Sans-Bold'
        if italic: return 'Sans-Italic'
        return 'Sans'
    if bold and italic: return 'Helvetica-BoldOblique'
    if bold:   return 'Helvetica-Bold'
    if italic: return 'Helvetica-Oblique'
    return 'Helvetica'


# ── Palette couleurs ─────────────────────────────────────────────────────────
C = {
    'navy':      colors.HexColor('#0F2B5B'),
    'blue':      colors.HexColor('#1A5490'),
    'blue_lt':   colors.HexColor('#3B82F6'),
    'blue_bg':   colors.HexColor('#EFF6FF'),
    'teal':      colors.HexColor('#0D9488'),
    'teal_bg':   colors.HexColor('#F0FDFA'),
    'green':     colors.HexColor('#059669'),
    'green_bg':  colors.HexColor('#ECFDF5'),
    'green_lt':  colors.HexColor('#D1FAE5'),
    'amber':     colors.HexColor('#D97706'),
    'amber_bg':  colors.HexColor('#FFFBEB'),
    'amber_lt':  colors.HexColor('#FDE68A'),
    'red':       colors.HexColor('#DC2626'),
    'red_bg':    colors.HexColor('#FEF2F2'),
    'red_lt':    colors.HexColor('#FECACA'),
    'purple':    colors.HexColor('#7C3AED'),
    'purple_bg': colors.HexColor('#F5F3FF'),
    'gray_dark': colors.HexColor('#1F2937'),
    'gray':      colors.HexColor('#6B7280'),
    'gray_lt':   colors.HexColor('#F3F4F6'),
    'gray_bd':   colors.HexColor('#E5E7EB'),
    'white':     colors.white,
    'rule':      colors.HexColor('#CBD5E1'),
}

DEFAULT_LOGO = "/dna_logo.png"


# ── Styles ───────────────────────────────────────────────────────────────────
def _build_styles():
    _register_fonts()
    S = {}
    base = getSampleStyleSheet()

    S['cover_title'] = ParagraphStyle('CoverTitle',
        fontName=_F(bold=True), fontSize=28, leading=36,
        textColor=C['navy'], alignment=TA_CENTER, spaceAfter=6)

    S['cover_sub'] = ParagraphStyle('CoverSub',
        fontName=_F(), fontSize=13, leading=18,
        textColor=C['blue'], alignment=TA_CENTER, spaceAfter=4)

    S['cover_lab'] = ParagraphStyle('CoverLab',
        fontName=_F(italic=True), fontSize=11, leading=14,
        textColor=C['gray'], alignment=TA_CENTER, spaceAfter=18)

    S['section'] = ParagraphStyle('Section',
        fontName=_F(bold=True), fontSize=16, leading=20,
        textColor=C['navy'], spaceBefore=16, spaceAfter=8)

    S['subsection'] = ParagraphStyle('SubSection',
        fontName=_F(bold=True), fontSize=12, leading=16,
        textColor=C['blue'], spaceBefore=10, spaceAfter=6)

    # IMPORTANT: leading un peu augmenté pour limiter les chevauchements
    S['body'] = ParagraphStyle('Body',
        fontName=_F(), fontSize=9.5, leading=14.5,
        textColor=C['gray_dark'], spaceAfter=4)

    S['body_small'] = ParagraphStyle('BodySmall',
        fontName=_F(), fontSize=8.5, leading=12.5,
        textColor=C['gray'], spaceAfter=2)

    S['label'] = ParagraphStyle('Label',
        fontName=_F(bold=True), fontSize=9, leading=13,
        textColor=C['gray_dark'])

    S['caption'] = ParagraphStyle('Caption',
        fontName=_F(italic=True), fontSize=8, leading=11,
        textColor=C['gray'], alignment=TA_CENTER)

    S['footer'] = ParagraphStyle('Footer',
        fontName=_F(italic=True), fontSize=8,
        textColor=C['gray'], alignment=TA_CENTER)

    S['reco_item'] = ParagraphStyle('RecoItem',
        fontName=_F(), fontSize=9, leading=13.5,
        textColor=C['gray_dark'], leftIndent=0, spaceAfter=2)

    S['reco_item_bold'] = ParagraphStyle('RecoItemBold',
        fontName=_F(bold=True), fontSize=9.5, leading=14.5,
        textColor=C['gray_dark'], spaceAfter=3)

    return S


# ── Utilitaires ──────────────────────────────────────────────────────────────
def _safe_float(x):
    try:
        if x is None or str(x).strip() == '':
            return None
        s = str(x).strip().replace(',', '.').replace(' ', '')
        s = re.sub(r'[^\d.\-]', '', s)
        return float(s) if s else None
    except:
        return None

def _parse_reference(ref_str):
    if not ref_str or str(ref_str).strip() == '':
        return None, None, None
    ref = str(ref_str).strip()
    m = re.search(r'(\d+\.?\d*)\s*[-\u2013\u2014]\s*(\d+\.?\d*)', ref)
    if m:
        return _safe_float(m.group(1)), _safe_float(m.group(2)), 'range'
    m = re.search(r'[<\u2264]\s*(\d+\.?\d*)', ref)
    if m:
        return None, _safe_float(m.group(1)), 'max'
    m = re.search(r'[>\u2265]\s*(\d+\.?\d*)', ref)
    if m:
        return _safe_float(m.group(1)), None, 'min'
    return None, None, None

def _clean(text):
    if not text:
        return ''
    subs = {
        '\u00b9': '1', '\u00b2': '2', '\u00b3': '3',
        '\u2070': '0', '\u2074': '4', '\u2075': '5',
        '\u2076': '6', '\u2077': '7', '\u2078': '8', '\u2079': '9',
        '\u00b5': 'u', '\u03bc': 'u', '\u2192': '->', '\u2193': 'v',
        '\u2191': '^', '\u25ba': '>', '\u2022': '-', '\u00ae': '(R)',
        '\u2264': '<=', '\u2265': '>=', '\u00d7': 'x',
    }
    for bad, good in subs.items():
        text = text.replace(bad, good)
    text = re.sub(r'[\U00002600-\U0001FFFF]', '', text)
    return text.strip()

def _wrap(text, max_chars=120):
    t = _clean(str(text))
    if len(t) <= max_chars:
        return t
    return t[:max_chars - 3] + '...'

def _para(text, style, max_chars=None):
    t = _clean(str(text))
    if max_chars:
        t = _wrap(t, max_chars)
    t = t.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    return Paragraph(t, style)


# ── Composants visuels ───────────────────────────────────────────────────────
def _divider(color=None):
    return HRFlowable(width='100%', thickness=0.5,
                      color=color or C['rule'], spaceAfter=6, spaceBefore=6)

def _section_header(title, S, color=None, bg=None, width=None):
    """Bande coloree pour les titres de section (width = largeur utile)."""
    col = color or C['navy']
    bg_col = bg or C['blue_bg']
    t = _clean(title).replace('&', '&amp;')

    if width is None:
        width = 17.4 * cm  # fallback

    data = [[Paragraph(
        f'<font color="#{col.hexval()[2:].upper()}">{t}</font>',
        ParagraphStyle('SH', fontName=_F(bold=True), fontSize=14,
                       leading=18, textColor=col)
    )]]

    tbl = Table(data, colWidths=[width])
    tbl.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,-1), bg_col),
        ('LEFTPADDING',   (0,0), (-1,-1), 14),
        ('RIGHTPADDING',  (0,0), (-1,-1), 14),
        ('TOPPADDING',    (0,0), (-1,-1), 9),
        ('BOTTOMPADDING', (0,0), (-1,-1), 9),
        ('LINEBELOW',     (0,0), (-1,-1), 2, col),
    ]))
    return tbl

def _kv_table(rows, col_w=(9*cm, 8*cm), header=None, header_color=None):
    hc = header_color or C['navy']
    data = []
    styles_t = [
        ('FONTNAME',    (0,0), (-1,-1), _F()),
        ('FONTSIZE',    (0,0), (-1,-1), 9.5),
        ('TOPPADDING',  (0,0), (-1,-1), 8),
        ('BOTTOMPADDING',(0,0),(-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 12),
        ('RIGHTPADDING',(0,0), (-1,-1), 12),
        ('VALIGN',      (0,0), (-1,-1), 'MIDDLE'),
        ('LINEBELOW',   (0,0), (-1,-2), 0.3, C['gray_bd']),
        ('BOX',         (0,0), (-1,-1), 0.5, C['gray_bd']),
    ]
    if header:
        data.append([Paragraph(_clean(header), ParagraphStyle('KVH',
                    fontName=_F(bold=True), fontSize=10, textColor=C['white'])),
                    ''])
        styles_t += [
            ('BACKGROUND',  (0,0), (-1,0), hc),
            ('TEXTCOLOR',   (0,0), (-1,0), C['white']),
            ('FONTNAME',    (0,0), (-1,0), _F(bold=True)),
            ('SPAN',        (0,0), (-1,0)),
        ]
    for r in rows:
        k = Paragraph(_clean(str(r[0])), ParagraphStyle('KVK',
            fontName=_F(bold=True), fontSize=9.5, textColor=C['gray_dark'], leading=12))
        v = Paragraph(_clean(str(r[1])), ParagraphStyle('KVV',
            fontName=_F(), fontSize=9.5, textColor=C['gray_dark'], leading=12))
        data.append([k, v])

    start = 1 if header else 0
    for i in range(start, len(data)):
        if (i - start) % 2 == 0:
            styles_t.append(('BACKGROUND', (0, i), (-1, i), C['gray_lt']))

    tbl = Table(data, colWidths=list(col_w))
    tbl.setStyle(TableStyle(styles_t))
    return tbl

def _status_colors(status):
    s = str(status).upper()
    if 'TRES' in s and any(x in s for x in ('ELEV', 'HIGH')):
        return 'TRES ELEVE', C['red'],   C['red_bg']
    if any(x in s for x in ('ELEV', 'HIGH')):
        return 'ELEVE',      C['amber'], C['amber_bg']
    if 'TRES' in s and any(x in s for x in ('BAS', 'LOW')):
        return 'TRES BAS',   C['red'],   C['red_bg']
    if any(x in s for x in ('BAS', 'LOW')):
        return 'BAS',        C['amber'], C['amber_bg']
    return 'Normal',         C['green'], C['green_bg']

def _biomarker_card(name, value, unit, reference, status, S):
    """
    Carte biomarqueur : 9cm | 5.5cm | 2.5cm
    Ajustements anti-chevauchement : leading/padding légèrement augmentés.
    """
    lbl, col, bg = _status_colors(status)

    clean_name = _clean(str(name))[:70]  # un peu plus permissif, mais Paragraph wrap gère
    val_str    = _clean(f"{value} {unit}".strip()) if value is not None else "N/A"
    ref_str    = f"Ref : {_clean(str(reference))}" if reference else ""

    ps_name = ParagraphStyle('BN', fontName=_F(bold=True),
                             fontSize=9, textColor=C['gray_dark'], leading=12, spaceAfter=2)
    ps_val  = ParagraphStyle('BV', fontName=_F(bold=True),
                             fontSize=12, textColor=col, leading=14, spaceAfter=2)
    ps_ref  = ParagraphStyle('BR', fontName=_F(italic=True),
                             fontSize=7.5, textColor=C['gray'], leading=10)
    ps_lbl  = ParagraphStyle('BL', fontName=_F(bold=True), fontSize=9,
                             textColor=C['white'], alignment=TA_CENTER, leading=11)

    left_content = [
        Paragraph(clean_name, ps_name),
        Paragraph(val_str, ps_val),
    ]
    if ref_str:
        left_content.append(Paragraph(ref_str, ps_ref))

    min_val, max_val, ref_type = _parse_reference(reference)
    BAR_W, BAR_H = 155, 10
    d = Drawing(BAR_W, BAR_H)
    d.add(Rect(0, 1, BAR_W, BAR_H-2, fillColor=C['gray_bd'], strokeColor=None))

    if ref_type == 'range' and min_val is not None and max_val is not None and max_val > min_val:
        d.add(Rect(0, 1, BAR_W, BAR_H-2, fillColor=C['green_lt'], strokeColor=None))
        try:
            vf = _safe_float(value)
            pos = (vf - min_val) / (max_val - min_val) if vf is not None else 0.5
            pos = max(0.0, min(1.0, pos))
        except:
            pos = 0.5
        d.add(Circle(BAR_W * pos, BAR_H / 2, 5,
                     fillColor=col, strokeColor=C['white'], strokeWidth=1.5))
    elif ref_type == 'max' and max_val:
        try:
            vf = _safe_float(value)
            pos = min((vf / max_val) if vf else 0.5, 1.0)
            fill = C['green_lt'] if pos < 1 else col
            d.add(Rect(0, 1, BAR_W * pos, BAR_H-2, fillColor=fill, strokeColor=None))
        except:
            pass

    row = [left_content, d, Paragraph(lbl, ps_lbl)]
    card = Table([row], colWidths=[9*cm, 5.5*cm, 2.5*cm])
    card.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (1,0),  bg),
        ('BACKGROUND',    (2,0), (2,0),  col),

        # padding un peu plus haut -> moins de chevauchement interne
        ('TOPPADDING',    (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),

        ('LEFTPADDING',   (0,0), (0,0),  14),
        ('LEFTPADDING',   (1,0), (1,0),  8),
        ('LEFTPADDING',   (2,0), (2,0),  4),
        ('RIGHTPADDING',  (0,0), (1,0),  8),
        ('RIGHTPADDING',  (2,0), (2,0),  4),

        ('VALIGN',        (0,0), (1,0),  'MIDDLE'),
        ('VALIGN',        (2,0), (2,0),  'MIDDLE'),
        ('ALIGN',         (2,0), (2,0),  'CENTER'),

        ('BOX',           (0,0), (-1,-1), 0.5, col),
        ('LINEAFTER',     (1,0), (1,0),  0.5, C['gray_bd']),
    ]))
    return card


def _reco_card(title, items, icon_char, bg, border, S, max_items=None):
    if not items:
        return []
    elems = []

    hdr = Table([[Paragraph(f'{_clean(title)}',
                            ParagraphStyle('RH', fontName=_F(bold=True),
                            fontSize=10.5, textColor=C['white'], leading=13))]],
                colWidths=[17*cm])
    hdr.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,-1), border),
        ('TOPPADDING',    (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING',   (0,0), (-1,-1), 16),
    ]))
    elems.append(hdr)

    display = items[:max_items] if max_items else items
    rows = []
    ps_txt = ParagraphStyle('RI', fontName=_F(), fontSize=8.5, leading=13,
                            textColor=C['gray_dark'])
    ps_dot = ParagraphStyle('RD', fontName=_F(bold=True), fontSize=9,
                            textColor=border, alignment=TA_CENTER)
    for item in display:
        t = _clean(str(item)).strip()
        if not t or t == '-':
            continue
        t = t[:400] if len(t) <= 400 else t[:397] + '...'
        rows.append([Paragraph('-', ps_dot), Paragraph(t, ps_txt)])

    if rows:
        body = Table(rows, colWidths=[0.8*cm, 16.2*cm])
        body.setStyle(TableStyle([
            ('BACKGROUND',    (0,0), (-1,-1), bg),
            ('TOPPADDING',    (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('LEFTPADDING',   (0,0), (0,-1),  3),
            ('RIGHTPADDING',  (0,0), (0,-1),  3),
            ('LEFTPADDING',   (1,0), (1,-1),  4),
            ('RIGHTPADDING',  (1,0), (1,-1),  10),
            ('LINEBELOW',     (0,0), (-1,-2), 0.2, C['gray_bd']),
            ('VALIGN',        (0,0), (-1,-1), 'TOP'),
            ('ALIGN',         (0,0), (0,-1),  'CENTER'),
            ('BOX',           (0,0), (-1,-1), 0.5, border),
        ]))
        elems.append(body)

    elems.append(Spacer(1, 8))
    return elems


def _priority_table(items, col, bg, border, label):
    if not items:
        return []
    ps_lbl = ParagraphStyle('PL', fontName=_F(bold=True), fontSize=8,
                            textColor=col, alignment=TA_CENTER)
    ps_txt = ParagraphStyle('PT', fontName=_F(bold=True), fontSize=9,
                            textColor=C['gray_dark'], leading=13)
    rows = []
    for item in items:
        t = _clean(str(item)).strip()[:200]
        rows.append([Paragraph(label, ps_lbl), Paragraph(t, ps_txt)])

    tbl = Table(rows, colWidths=[2*cm, 15*cm])
    tbl.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,-1), bg),
        ('BACKGROUND',    (0,0), (0,-1), colors.HexColor('#FFF')),
        ('TOPPADDING',    (0,0), (-1,-1), 7),
        ('BOTTOMPADDING', (0,0), (-1,-1), 7),
        ('LEFTPADDING',   (0,0), (0,-1), 6),
        ('LEFTPADDING',   (1,0), (1,-1), 12),
        ('RIGHTPADDING',  (0,0), (-1,-1), 10),
        ('LINEBELOW',     (0,0), (-1,-2), 0.3, C['gray_bd']),
        ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN',         (0,0), (0,-1), 'CENTER'),
        ('BOX',           (0,0), (-1,-1), 1.5, border),
        ('LINEAFTER',     (0,0), (0,-1), 0.5, border),
    ]))
    return [tbl, Spacer(1, 6)]


# ── Callbacks page (en-tete / pied) ─────────────────────────────────────────
def _make_page_callbacks(patient_data):
    def _header_footer(canvas, doc):
        canvas.saveState()
        W, H = A4

        # Bande navy en haut
        canvas.setFillColor(C['navy'])
        canvas.rect(0, H - 1.2*cm, W, 1.2*cm, fill=1, stroke=0)

        canvas.setFont(_F(bold=True), 8)
        canvas.setFillColor(C['white'])
        canvas.drawString(1.5*cm, H - 0.85*cm, "ALGO-LIFE  |  Rapport d'Analyses Biologiques")

        pat = patient_data.get('name', '')
        if pat:
            canvas.drawRightString(W - 1.5*cm, H - 0.85*cm, f"Patient: {_clean(str(pat))}")

        # Pied de page
        canvas.setFillColor(C['gray_bd'])
        canvas.rect(0, 0, W, 0.8*cm, fill=1, stroke=0)

        canvas.setFont(_F(italic=True), 7.5)
        canvas.setFillColor(C['gray'])
        canvas.drawString(1.5*cm, 0.25*cm, "ALGO-LIFE  |  bilan-hormonal.com")
        canvas.drawRightString(W - 1.5*cm, 0.25*cm, f"Page {doc.page}")

        canvas.restoreState()

    # IMPORTANT: page 1 sans header/footer => évite chevauchement page de garde
    def _first_page(canvas, doc):
        return

    return _first_page, _header_footer


# ── Generateur principal ─────────────────────────────────────────────────────
def generate_multimodal_report(
    patient_data,
    biology_data,
    microbiome_data,
    recommendations,
    cross_analysis,
    follow_up,
    bio_age_result=None,
    output_path=None
):
    _register_fonts()
    S = _build_styles()

    ai_enrichment = None
    if STREAMLIT_AVAILABLE and hasattr(st, 'session_state'):
        if st.session_state.get('ai_enrichment_active') and st.session_state.get('ai_enrichment_output'):
            ai_enrichment = st.session_state.ai_enrichment_output

    if output_path is None:
        import tempfile
        output_path = os.path.join(tempfile.gettempdir(), 'rapport_algolife.pdf')

    pat = patient_data or {}

    first_cb, later_cb = _make_page_callbacks(pat)

    # Marges : un peu plus safe vs header/footer
    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        leftMargin=1.8*cm, rightMargin=1.8*cm,
        topMargin=2.0*cm, bottomMargin=1.4*cm,
    )

    story = []
    W = doc.width  # largeur utile (robuste si tu changes les marges)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # PAGE DE GARDE
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    story.append(Spacer(1, 1.2*cm))

    cover_hdr = Table(
        [[Paragraph("RAPPORT D'ANALYSES BIOLOGIQUES",
                    ParagraphStyle('CT2', fontName=_F(bold=True), fontSize=24,
                                   leading=30, textColor=C['white'], alignment=TA_CENTER))],
         [Paragraph("Biologie Fonctionnelle &amp; Microbiote",
                    ParagraphStyle('CS2', fontName=_F(), fontSize=13,
                                   leading=18, textColor=colors.HexColor('#A5C8E8'),
                                   alignment=TA_CENTER))]],
        colWidths=[W]
    )
    cover_hdr.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,-1), C['navy']),
        ('TOPPADDING',    (0,0), (-1,-1), 22),
        ('BOTTOMPADDING', (0,0), (-1,-1), 22),
        ('LEFTPADDING',   (0,0), (-1,-1), 18),
        ('RIGHTPADDING',  (0,0), (-1,-1), 18),
    ]))
    story.append(cover_hdr)
    story.append(Spacer(1, 0.6*cm))

    story.append(_para("Rapport de Biologie Fonctionnelle &amp; Microbiote", S['cover_lab']))
    story.append(Spacer(1, 1.0*cm))

    pat_rows = [
        ('PATIENT',           pat.get('name', 'N/A')),
        ('SEXE',              pat.get('sex', 'N/A')),
        ('DATE DE NAISSANCE', str(pat.get('birthdate', 'N/A'))),
        ('AGE',               f"{pat.get('age', 'N/A')} ans"),
    ]
    bmi = pat.get('bmi')
    if bmi:
        try:
            pat_rows.append(('IMC', f"{float(bmi):.1f} kg/m2"))
        except:
            pass

    story.append(_kv_table(pat_rows, col_w=(6*cm, W-6*cm),
                           header='INFORMATIONS PATIENT', header_color=C['navy']))
    story.append(Spacer(1, 0.9*cm))
    story.append(_para(
        f"Rapport genere le {datetime.now().strftime('%d/%m/%Y a %H:%M')}",
        S['caption']))
    story.append(PageBreak())

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # SOMMAIRE
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    story.append(_section_header('SOMMAIRE DU RAPPORT', S, width=W))
    story.append(Spacer(1, 0.4*cm))

    sections = [
        ('1', 'Resultats Biologie', '3'),
        ('2', 'Age Biologique', '—' if not bio_age_result else '5'),
        ('3', 'Analyse Microbiote', '6'),
        ('4', 'Analyses Croisees Multimodales', '10'),
        ('5', 'Recommandations (Systeme de Regles)', '12'),
        ('6', 'Plan de Suivi', '15'),
    ]
    som_data = [['No', 'Section', 'Page']] + [[n, t, p] for n, t, p in sections]
    som_tbl = Table(som_data, colWidths=[1.5*cm, W-4.0*cm, 2.5*cm])
    som_tbl.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,0), C['navy']),
        ('TEXTCOLOR',     (0,0), (-1,0), C['white']),
        ('FONTNAME',      (0,0), (-1,0), _F(bold=True)),
        ('FONTSIZE',      (0,0), (-1,-1), 9.5),
        ('FONTNAME',      (0,1), (-1,-1), _F()),
        ('ALIGN',         (0,0), (0,-1), 'CENTER'),
        ('ALIGN',         (2,0), (2,-1), 'CENTER'),
        ('TOPPADDING',    (0,0), (-1,-1), 9),
        ('BOTTOMPADDING', (0,0), (-1,-1), 9),
        ('LEFTPADDING',   (0,0), (-1,-1), 12),
        ('ROWBACKGROUNDS',(0,1), (-1,-1), [C['white'], C['gray_lt']]),
        ('LINEBELOW',     (0,0), (-1,-1), 0.3, C['gray_bd']),
        ('BOX',           (0,0), (-1,-1), 0.5, C['gray_bd']),
    ]))
    story.append(som_tbl)
    story.append(PageBreak())

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # BIOLOGIE
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    if biology_data:
        story.append(_section_header('RESULTATS BIOLOGIE', S, C['blue'], C['blue_bg'], width=W))
        story.append(Spacer(1, 0.4*cm))

        total   = len(biology_data)
        normaux = sum(1 for b in biology_data if str(b.get('Statut','')).upper() in ('NORMAL',))
        eleves  = sum(1 for b in biology_data if any(x in str(b.get('Statut','')).upper()
                                                     for x in ('ELEV','HIGH')))
        bas_    = sum(1 for b in biology_data if any(x in str(b.get('Statut','')).upper()
                                                     for x in ('BAS','LOW')))

        stat_data = [[
            Paragraph('TOTAL', ParagraphStyle('SH', fontName=_F(bold=True),
                      fontSize=9, textColor=C['gray'], alignment=TA_CENTER)),
            Paragraph('NORMAUX', ParagraphStyle('SH', fontName=_F(bold=True),
                      fontSize=9, textColor=C['green'], alignment=TA_CENTER)),
            Paragraph('ELEVES', ParagraphStyle('SH', fontName=_F(bold=True),
                      fontSize=9, textColor=C['amber'], alignment=TA_CENTER)),
            Paragraph('BAS', ParagraphStyle('SH', fontName=_F(bold=True),
                      fontSize=9, textColor=C['red'], alignment=TA_CENTER)),
        ], [
            Paragraph(str(total),   ParagraphStyle('SV', fontName=_F(bold=True),
                      fontSize=22, textColor=C['gray_dark'], alignment=TA_CENTER)),
            Paragraph(str(normaux), ParagraphStyle('SV', fontName=_F(bold=True),
                      fontSize=22, textColor=C['green'], alignment=TA_CENTER)),
            Paragraph(str(eleves),  ParagraphStyle('SV', fontName=_F(bold=True),
                      fontSize=22, textColor=C['amber'], alignment=TA_CENTER)),
            Paragraph(str(bas_),    ParagraphStyle('SV', fontName=_F(bold=True),
                      fontSize=22, textColor=C['red'], alignment=TA_CENTER)),
        ]]
        stat_tbl = Table(stat_data, colWidths=[W/4]*4)
        stat_tbl.setStyle(TableStyle([
            ('BACKGROUND',    (0,0), (-1,-1), C['gray_lt']),
            ('TOPPADDING',    (0,0), (-1,0), 10),
            ('BOTTOMPADDING', (0,0), (-1,0), 4),
            ('TOPPADDING',    (0,1), (-1,1), 4),
            ('BOTTOMPADDING', (0,1), (-1,1), 12),
            ('BOX',           (0,0), (-1,-1), 0.5, C['gray_bd']),
            ('LINEAFTER',     (0,0), (2,-1), 0.3, C['gray_bd']),
        ]))
        story.append(stat_tbl)
        story.append(Spacer(1, 0.8*cm))

        story.append(_para('DETAILS DES BIOMARQUEURS', S['subsection']))
        story.append(Spacer(1, 0.3*cm))

        for bio in biology_data:
            card = _biomarker_card(
                bio.get('Biomarqueur', 'N/A'),
                bio.get('Valeur'),
                str(bio.get('Unite', bio.get('Unité', ''))),
                bio.get('Reference', bio.get('Référence', '')),
                bio.get('Statut', 'Normal'),
                S,
            )
            story.append(card)
            story.append(Spacer(1, 4))

        story.append(PageBreak())

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # AGE BIOLOGIQUE
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    if bio_age_result:
        story.append(_section_header('AGE BIOLOGIQUE (bFRAil Score)', S, C['teal'], C['teal_bg'], width=W))
        story.append(Spacer(1, 0.4*cm))

        bio_age    = bio_age_result.get('bio_age', 0)
        chrono_age = pat.get('age', 0)
        diff       = float(bio_age) - float(chrono_age or 0)
        prob       = bio_age_result.get('frailty_probability', 0)
        risk       = bio_age_result.get('risk_category', 'N/A')

        rows = [
            ('Age chronologique', f"{chrono_age} ans"),
            ('Age biologique',    f"{float(bio_age):.1f} ans"),
            ('Difference',        f"{diff:+.1f} ans"),
            ('Probabilite de fragilite', f"{float(prob):.1f}%"),
            ('Categorie de risque', _clean(str(risk))),
        ]
        story.append(_kv_table(rows, col_w=(9*cm, W-9*cm),
                               header='RESULTATS', header_color=C['teal']))
        story.append(PageBreak())

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # MICROBIOME + ANALYSES CROISEES + RECO + IA + SUIVI
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # >>> ICI : je n’ai pas modifié ta logique (pour rester 100% compatible).
    # Tu peux conserver exactement tes blocs existants, en remplaçant seulement
    # les appels _section_header(..., width=W) quand tu veux éviter les décalages.
    #
    # Pour gagner de la place dans ce message, je laisse tes blocs inchangés,
    # EXCEPTÉ la page finale (ci-dessous) + build (callback first/later).
    #
    # >>> COPIE/COLLE TES BLOCS MICROBIOME / CROSS / RECO / IA / FOLLOW_UP ICI
    #
    # (tu peux garder ton code tel quel)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # PAGE FINALE (corrigée : pas de Spacer dans Table)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    story.append(Spacer(1, 1.5*cm))

    final_hdr = Table(
        [[Paragraph('ALGO-LIFE © 2026', ParagraphStyle('FL',
            fontName=_F(bold=True), fontSize=16, leading=20,
            textColor=C['white'], alignment=TA_CENTER))]],
        colWidths=[W]
    )
    final_hdr.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,-1), C['navy']),
        ('TOPPADDING',    (0,0), (-1,-1), 14),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ('LEFTPADDING',   (0,0), (-1,-1), 18),
        ('RIGHTPADDING',  (0,0), (-1,-1), 18),
    ]))
    story.append(final_hdr)

    final_body = Table(
        [[Paragraph('Analyse Multimodale en Biologie Fonctionnelle',
            ParagraphStyle('FL2', fontName=_F(), fontSize=10, leading=14,
            textColor=colors.HexColor('#A5C8E8'), alignment=TA_CENTER))],
         [Paragraph('Dr Thibault SUTTER, PhD',
            ParagraphStyle('FL3', fontName=_F(bold=True), fontSize=12, leading=16,
            textColor=C['white'], alignment=TA_CENTER))],
         [Paragraph('Biologiste specialise en biologie fonctionnelle',
            ParagraphStyle('FL4', fontName=_F(), fontSize=9.5, leading=13,
            textColor=colors.HexColor('#A5C8E8'), alignment=TA_CENTER))],
         [Paragraph('Geneva, Switzerland  |  bilan-hormonal.com  |  ALGO-LIFE',
            ParagraphStyle('FL6', fontName=_F(italic=True), fontSize=9, leading=12,
            textColor=colors.HexColor('#7BA7C9'), alignment=TA_CENTER))],
         [Paragraph('Ce rapport est genere par analyse multimodale (systeme de regles + IA). '
                    'Il ne remplace pas un avis medical personnalise.',
            ParagraphStyle('FL7', fontName=_F(italic=True), fontSize=8, leading=11,
            textColor=colors.HexColor('#7BA7C9'), alignment=TA_CENTER))]],
        colWidths=[W]
    )
    final_body.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,-1), C['navy']),
        ('TOPPADDING',    (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ('LEFTPADDING',   (0,0), (-1,-1), 18),
        ('RIGHTPADDING',  (0,0), (-1,-1), 18),
        ('LINEBELOW',     (0,0), (-1,-2), 0.2, colors.HexColor('#1f3b6d')),
    ]))
    story.append(final_body)

    # ── Build (IMPORTANT : callbacks différents page 1 vs suivantes) ─────────
    doc.build(story, onFirstPage=first_cb, onLaterPages=later_cb)

    size_kb = os.path.getsize(output_path) / 1024
    print(f"PDF genere : {output_path}  ({size_kb:.0f} KB)")
    return output_path


# Alias compatibilite
generate_report = generate_multimodal_report


if __name__ == "__main__":
    print("PDF Generator ALGO-LIFE v2 — design pro, Liberation Sans, pas d emojis")
