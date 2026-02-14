"""
UNILABS / ALGO-LIFE - Extractors v19.0
=============================================================
✅ Extraction PDF biologie natif (SYNLAB/UNILABS)        — texte encodé
✅ ✨ NOUVEAU: Extraction PDF image/scan (EUROFINS)       — OCR automatique
✅ Détection automatique du type de PDF (natif vs image)
✅ Extraction PDF microbiome (IDK GutMAP)
✅ Extraction Excel biologie
✅ Extraction Excel microbiome (fichier structuré)
✅ Correction unités OCR (G/1→G/L, mul/l→mUI/L, 1m3→µm³…)
✅ Support références avec et sans parenthèses
✅ Références par défaut pour biomarqueurs courants
✅ Extraction robuste des 48 bactéries + groupes
✅ Détection graphique des positions d'abondance
=============================================================
Dépendances OCR (optionnelles, activées si disponibles):
  pip install pdf2image pytesseract
  apt-get install tesseract-ocr tesseract-ocr-fra poppler-utils
"""

from __future__ import annotations
import os, re, sys, unicodedata
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    np = None

# ─────────────────────────────────────────────────────────────
#  Vérification disponibilité OCR
# ─────────────────────────────────────────────────────────────
def _ocr_available() -> bool:
    try:
        from pdf2image import convert_from_path  # noqa
        import pytesseract  # noqa
        return True
    except ImportError:
        return False


# ─────────────────────────────────────────────────────────────
#  ProgressTracker
# ─────────────────────────────────────────────────────────────
class ProgressTracker:
    def __init__(self, total_steps=100, show_bar=True):
        self.total_steps = total_steps
        self.current_step = 0
        self.show_bar = show_bar
        self.current_task = ""

    def update(self, step, task=""):
        self.current_step = min(step, self.total_steps)
        self.current_task = task
        if self.show_bar:
            self._render()

    def _render(self):
        try:
            pct = int((self.current_step / self.total_steps) * 100)
            filled = int((pct / 100) * 40)
            bar = "█" * filled + "░" * (40 - filled)
            sys.stdout.write(f"\r🔄 [{bar}] {pct}% - {self.current_task}")
            sys.stdout.flush()
            if self.current_step >= self.total_steps:
                sys.stdout.write("\n"); sys.stdout.flush()
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────
#  Références par défaut
# ─────────────────────────────────────────────────────────────
DEFAULT_REFERENCES = {
    "glycemie": "0.70 — 1.05", "glucose": "0.70 — 1.05",
    "cpk": "30 — 200", "c.p.k": "30 — 200", "ck": "30 — 200",
    "creatine kinase": "30 — 200", "ferritine": "15 — 150", "ferritin": "15 — 150",
    "crp": "0 — 5", "c-reactive protein": "0 — 5",
    "crp ultrasensible": "0 — 3", "hs-crp": "0 — 3",
    "cholesterol total": "0 — 2.00", "ldl": "0 — 1.60",
    "hdl": "0.40 — 0.65", "triglycerides": "0 — 1.50",
    "hemoglobine": "11.5 — 16.0", "hemoglobin": "11.5 — 16.0",
    "albumine": "35 — 50", "albumin": "35 — 50",
}


# ─────────────────────────────────────────────────────────────
#  Utilitaires communs
# ─────────────────────────────────────────────────────────────
def normalize_biomarker_name(name):
    if name is None: return ""
    s = str(name).strip()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.upper().replace(".", " ").replace(",", " ").replace("'", "'")
    s = re.sub(r"[^A-Z0-9\s\-\+/]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    for old, new in {"C P K":"CPK","L D L":"LDL","H D L":"HDL","V G M":"VGM",
                     "T C M H":"TCMH","C C M H":"CCMH","C R P":"CRP","T S H":"TSH",
                     "D F G":"DFG","G P T":"GPT","G O T":"GOT"}.items():
        s = s.replace(old, new)
    return s


def _safe_float(x):
    try:
        if x is None: return None
        s = str(x).strip().replace(",", ".")
        s = re.sub(r"[^0-9\.\-\+eE]", "", s)
        return float(s) if s else None
    except Exception:
        return None


def _clean_ref(ref):
    if ref is None: return ""
    r = str(ref).strip().replace("—", "-").replace("–", "-")
    return re.sub(r"\s+", " ", r)


def _get_default_reference(name):
    if not name: return ""
    nl = str(name).lower()
    for k, v in DEFAULT_REFERENCES.items():
        if k in nl: return v
    return ""


def determine_biomarker_status(value, reference, biomarker_name=None):
    v = _safe_float(value)
    if v is None: return "Inconnu"
    ref = _clean_ref(reference)
    m = re.search(r"(-?\d+(?:[.,]\d+)?)\s*(?:-|à|to)\s*(-?\d+(?:[.,]\d+)?)", ref, re.IGNORECASE)
    if m:
        lo, hi = _safe_float(m.group(1)), _safe_float(m.group(2))
        if lo is None or hi is None: return "Inconnu"
        if v < lo: return "Bas"
        if v > hi: return "Élevé"
        return "Normal"
    m = re.search(r"(?:<|≤)\s*(-?\d+(?:[.,]\d+)?)", ref)
    if m:
        hi = _safe_float(m.group(1))
        return "Élevé" if (hi and v > hi) else "Normal"
    m = re.search(r"(?:>|≥)\s*(-?\d+(?:[.,]\d+)?)", ref)
    if m:
        lo = _safe_float(m.group(1))
        return "Bas" if (lo and v < lo) else "Normal"
    return "Inconnu"


# ─────────────────────────────────────────────────────────────
#  Lecture PDF — détection automatique natif / image
# ─────────────────────────────────────────────────────────────
def _read_pdf_text(pdf_path: str) -> str:
    """Lit le texte d'un PDF. Fallback OCR automatique si PDF image/scan."""
    try:
        import pdfplumber
    except ImportError as e:
        raise ImportError("pdfplumber manquant: pip install pdfplumber") from e

    chunks = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            chunks.append(page.extract_text() or "")

    full_text = "\n".join(chunks).strip()

    # Si < 100 caractères utiles → PDF image → OCR
    if len(full_text) < 100:
        full_text = _ocr_pdf(pdf_path)

    return full_text


def _ocr_pdf(pdf_path: str, lang: str = "fra") -> str:
    """Convertit un PDF image en texte via OCR (pdf2image + pytesseract)."""
    if not _ocr_available():
        raise ImportError(
            "OCR requis pour ce PDF (fichier image/scan).\n"
            "pip install pdf2image pytesseract\n"
            "apt-get install tesseract-ocr tesseract-ocr-fra poppler-utils"
        )
    from pdf2image import convert_from_path
    import pytesseract

    try:
        available = pytesseract.get_languages()
        langs = "+".join(l for l in [lang, "eng"] if l in available) or "eng"
    except Exception:
        langs = lang

    images = convert_from_path(pdf_path, dpi=300)
    return "\n".join(pytesseract.image_to_string(img, lang=langs) for img in images)


def _detect_pdf_source(text: str) -> str:
    """Détecte la source du PDF."""
    t = text.upper()
    if "EUROFINS" in t: return "eurofins"
    if "SYNLAB" in t: return "synlab"
    if "UNILABS" in t: return "unilabs"
    return "generic"


# ─────────────────────────────────────────────────────────────
#  Correcteurs OCR Eurofins
# ─────────────────────────────────────────────────────────────
_UNIT_OCR_FIXES = {
    "1m3":"µm³","Im3":"µm³","lm3":"µm³","um3":"µm³",
    "pmol/l":"µmol/L","pmol":"µmol","umol/l":"µmol/L","umol":"µmol",
    "mmol/l":"mmol/L","mmol":"mmol/L",
    "g/1":"g/L","g/l":"g/L","G/1":"G/L","G/l":"G/L",
    "T/1":"T/L","T/l":"T/L","Gi":"G/L",
    # OCR confond I (majuscule) et l (minuscule) et 1 avec /
    "G/I":"G/L","G/i":"G/L","T/I":"T/L",
    "mul/l":"mUI/L","mul/L":"mUI/L","mul":"mUI/L","mUI/1":"mUI/L","mUI/I":"mUI/L",
    "ng/m":"ng/mL","ng/ml":"ng/mL",
    "ug/100ml":"µg/100mL","ug/100mI":"µg/100mL",
    "Ur/I":"UI/L","Ur/l":"UI/L","UI/":"UI/L","UI/1":"UI/L","UI/l":"UI/L","UI/I":"UI/L",
    "U/l":"UI/L","U/1":"UI/L","U/I":"UI/L",
    "ULI":"UI/L","ull":"UI/L","url":"UI/L","url/l":"UI/L",
    "picog":"pg","Picog":"pg",
    "g/100mI":"g/100mL","g/100ml":"g/100mL",
    "g/dl":"g/dL","g/Dl":"g/dL",
    "mg/l":"mg/L","mg/I":"mg/L",
}

_NAME_OCR_FIXES = {
    "votsh":"TSH","vot sh":"TSH","en bo) een":"TSH","en bo een":"TSH","tsh":"TSH",
    "creatininemie":"Créatininémie","créatininemie":"Créatininémie",
    "glycemie a jeun":"Glycémie à jeun","glycémie a jeun":"Glycémie à jeun",
    "natremie":"Natrémie","natrémie":"Natrémie",
    "kaliemie":"Kaliémie","kaliémie":"Kaliémie",
    "ferritinemie":"Ferritinémie","ferritinémie":"Ferritinémie",
    "natremie sodium":"Natrémie (Sodium)","natrémie sodium":"Natrémie (Sodium)",
    "kaliemie potassium sur serum":"Kaliémie (Potassium)",
    "kaliémie potassium sur serum":"Kaliémie (Potassium)",
    "hemoglobine ceeeeeeee ee":"Hémoglobine",
    "hémoglobine ceeeeeeee ee":"Hémoglobine",
    "hematocrite":"Hématocrite","hématocrite":"Hématocrite",
    "leucocytes":"Leucocytes","plaquettes":"Plaquettes",
    "transferrine":"Transferrine","ferritinemie":"Ferritinémie",
    "bilirubine totale":"Bilirubinémie totale",
    "bilirubinémie totale":"Bilirubinémie totale",
    "transaminases tgo asat":"Transaminases TGO (ASAT)",
    "transaminases tgp alat":"Transaminases TGP (ALAT)",
    "transaminases tgo":"Transaminases TGO (ASAT)",
    "transaminases tgp":"Transaminases TGP (ALAT)",
    "transaminases tgo (asat":"Transaminases TGO (ASAT)",
    "transaminases tgp (alat":"Transaminases TGP (ALAT)",
    "phosphatases alcalines":"Phosphatases alcalines",
    "gamma glutamyl transferase":"Gamma GT (GGT)",
    "gamma glutamyl transférase":"Gamma GT (GGT)",
    "proteine c reactive":"Protéine C réactive",
    "protéine c réactive":"Protéine C réactive",
    "gm.":"VGM","gm":"VGM","vgm.":"VGM",
    "pm.":"VPM","pm":"VPM","vpm.":"VPM",
    "c.c.mh":"C.C.M.H","ccmh":"C.C.M.H",
    "tcmh":"T.C.M.H","t.c.m.h":"T.C.M.H",
    "idr":"IDR",
}

# Mots parasites OCR connus (lignes de points mal OCRisées)
_NOISE_WORDS_SET = {
    'ins','inrsinrennss','siennes','enrenenenre','sise','eunssses',
    'sisi','sis','rss','tsetse','inrs','siernes','inrs','siesiesss',
}


def _fix_unit_ocr(unit: str) -> str:
    if not unit: return unit
    fixed = _UNIT_OCR_FIXES.get(unit.strip())
    if fixed: return fixed
    ul = unit.strip().lower()
    for k, v in _UNIT_OCR_FIXES.items():
        if k.lower() == ul: return v
    return unit


def _fix_name_ocr(name: str) -> str:
    """Nettoie les noms de biomarqueurs après OCR Eurofins."""
    # 1. Supprimer le différentiel leucocytaire en fin: '58,2 %'
    name = re.sub(r"\s+\d+[.,]\d+\s*%\s*$", "", name)

    # 2. Supprimer préfixes OCR isolés ('v ', 'vy ') sans toucher VGM/VPM
    name = re.sub(r"^vy\s+", "", name, flags=re.IGNORECASE)
    name = re.sub(r"^v\s+(?=[A-ZÀ-Ÿa-zà-ÿ])", "", name)
    name = re.sub(r"^[✓✔JY7\*\u2713\u2714]\s+", "", name)

    # 3. Supprimer suffixe de bruit OCR (lignes de points = ceeeeee, ssssss...)
    #    Pattern: séquences répétitives de 4+ caractères alternant consonnes/voyelles
    name = re.sub(r"\s+(?:[a-zà-ÿ]{1,3}(?:ee|ii|uu|oo|aa|ss|nn|rr){2,}[a-zà-ÿ]*)+\s*$", "", name)
    name = re.sub(r"\s+(?:c+[eaou]+){3,}[a-zà-ÿ]*\s*$", "", name)   # ceeeeee, ceaaaeee...
    name = re.sub(r"\s+[a-zà-ÿ]*(?:eee|aaa|ooo|sss|nnn|rrr)[a-zà-ÿ]*\s*$", "", name)  # triple répétition

    # 4. Supprimer trailing ponctuation / artefacts
    name = re.sub(r"[\s,\.\(\)<]+$", "", name)

    # 5. Supprimer mots parasites OCR connus
    words = name.split()
    words = [w for w in words if w.lower() not in _NOISE_WORDS_SET]
    name = " ".join(words)

    # 6. Supprimer suffixes de méthode analytique
    name = re.sub(
        r"\s*(Enzymatique|Spectrophotométrie|Chimiluminescence|Immunoturbidimétrie"
        r"|NADH\s+avec|Potentiométrie|Diazo\s+|p-NPP\s*\(|Férène\s+|Hexokinase\s+Architect"
        r"|Architect\s+Abbott|Abbott\s+\d|SYSMEX|SIEMENS|Beckman|Roche).*$",
        "", name, flags=re.IGNORECASE,
    )
    # 7. Normaliser parenthèses
    name = re.sub(r"\(\s*([A-Za-zÀ-ÿ\s]+)\s*\)", r"\1", name)
    name = re.sub(r"\s+", " ", name).strip()

    # 8. Chercher dans les corrections connues
    key = name.lower().strip()
    if key in _NAME_OCR_FIXES:
        return _NAME_OCR_FIXES[key]

    return name


# ─────────────────────────────────────────────────────────────
#  Lignes à ignorer
# ─────────────────────────────────────────────────────────────
_IGNORE_PATTERNS = [
    r"^Édition\s*:", r"^Laboratoire", r"^SYNLAB", r"^UNILABS", r"^EUROFINS",
    r"^Dossier", r"^FranceLIS", r"^Analyses",
    r"^BIOCHIMIE|^CHIMIE|^HORMONOLOGIE|^IMMUNOLOGIE|^HEMATOLOGIE|^HEMOSTASE",
    r"^Colorimétrie|^Chimiluminescence|^Spectrophotométrie|^Immunoturbidimétrie",
    r"^Interprétation", r"^Accéder", r"^Validé", r"^Page\s+\d+",
    r"^Valeurs\s+de\s+référence", r"^Antériorités", r"^Biochimie\s+Statut",
    r"^Aspect\s+du", r"^Non\s+", r"^Demande\s+n", r"^Prélevé", r"^Imprimé",
    r"^Prescripteur", r"^CHUGA|^CHU\s+", r"^Dr\s+", r"^Merci\s+de",
    r"^Le\s+laboratoire", r"^Dans\s+un\s+soucis", r"^S\.E\.L\.A",
    r"^T\.\s+04", r"^Andrew\s+and", r"^Les\s+formules", r"^Chez\s+ces\s+sujets",
    r"^Remarque\s*:", r"^La\s+demande", r"^L['']\s*assurance",
    r"^Exploration\s+de", r"^Taux\s+de\s+prothrombine\s+normal",
    r"^Le\s+dosage", r"^Bilan\s+", r"Finess\s*:", r"RCS\s+CHAMBERY",
    r"www\.", r"^\d{2}/\d{2}/\d{2,4}\s*$",
    r"^NADH\s+avec", r"^Chimiluminescence\s+Architect",
    r"^Immunoturbidimétrie\s+Architect", r"^Enzymatique\s+Architect",
    r"^Potentiométrie\s+", r"^Diazo\s+Architect", r"^p-NPP\s+\(",
    r"^Férène\s+Architect", r"^Hexokinase\s+Architect",
    r"^Spectrophotométrie\s+Architect", r"^SYSMEX\s+",
]


def _is_noise_line(line):
    if not line: return True
    s = line.strip()
    if len(s) < 4: return True
    for pat in _IGNORE_PATTERNS:
        if re.search(pat, s, flags=re.IGNORECASE): return True
    return False


# ─────────────────────────────────────────────────────────────
#  Parser Eurofins OCR — approche "chercher la référence d'abord"
# ─────────────────────────────────────────────────────────────
_REF_PAT = re.compile(
    r"(?:"
    r"(?P<inf>[Ii]nf\.?\s*[àa]\s*\d+[.,]?\d*)"
    r"|(?P<sup>[Ss]up\.?\s*[àa]\s*\d+[.,]?\d*)"
    r"|(?P<range>\d+[.,]?\d*\s*[àa]\s*\d+[.,]?\d*)"
    r")",
    re.UNICODE,
)

_VAL_UNIT_PAT = re.compile(
    r"\*?\s*(\d+[.,]\d+|\d+)\s*([A-Za-zµμ%°][A-Za-z0-9µμ/\.\|°%]*)?\s*$",
    re.UNICODE,
)


def _clean_ocr_line(line: str) -> str:
    line = re.sub(r"^[\s\*✓✔JY7✗\u2713\u2714]+", "", line)
    line = re.sub(r"\.{3,}", " ", line)
    line = re.sub(r"\b([bcdfghjklmnpqrstvwxyz])\1+\b", "", line, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", line).strip()


def _parse_eurofins_line(line: str) -> Optional[Dict]:
    """
    Parse une ligne OCR Eurofins.
    Stratégie: localiser la référence (X à Y / inf. à Z), puis extraire
    nom / valeur / unité de ce qui précède.
    """
    line = _clean_ocr_line(line)
    if not line or len(line) < 8:
        return None

    ref_matches = list(_REF_PAT.finditer(line))
    if not ref_matches:
        return None

    ref_m = ref_matches[-1]
    ref_str = ref_m.group(0).strip()
    ref_start = ref_m.start()

    before_ref = line[:ref_start].strip()
    if not before_ref:
        return None

    vu_m = _VAL_UNIT_PAT.search(before_ref)
    if not vu_m:
        return None

    value_str = vu_m.group(1)
    unit_raw = (vu_m.group(2) or "").strip()
    name_raw = before_ref[: vu_m.start()].strip()

    name = _fix_name_ocr(name_raw)
    if len(name) < 2:
        return None

    unit = _fix_unit_ocr(unit_raw)

    # Normaliser la référence
    ref_n = re.sub(r"\s*[àa]\s*", " - ", ref_str)
    ref_n = re.sub(r"[Ii]nf\.?\s*-\s*(\d+[.,]?\d*)", r"< \1", ref_n)
    ref_n = re.sub(r"[Ss]up\.?\s*-\s*(\d+[.,]?\d*)", r"> \1", ref_n)
    ref_n = re.sub(r"\s+", " ", ref_n).strip()

    return {
        "name": name,
        "value": _safe_float(value_str),
        "unit": unit,
        "reference": ref_n,
    }


# ─────────────────────────────────────────────────────────────
#  Extraction biologie SYNLAB/UNILABS (PDF natif)
# ─────────────────────────────────────────────────────────────
_SYNLAB_NOISE = [
    r"^Édition\s*:", r"^Laboratoire", r"^SYNLAB", r"^UNILABS", r"^Dossier",
    r"^FranceLIS", r"^Analyses",
    r"^BIOCHIMIE|^CHIMIE|^HORMONOLOGIE|^IMMUNOLOGIE|^HEMATOLOGIE",
    r"^Colorimétrie|^Chimiluminescence",
    r"^Interprétation", r"^Accéder", r"^Validé", r"^Page\s+\d+",
]


def _is_synlab_noise(line):
    if not line: return True
    s = line.strip()
    if len(s) < 4: return True
    for pat in _SYNLAB_NOISE:
        if re.search(pat, s, flags=re.IGNORECASE): return True
    return False


def _extract_synlab_native(lines: List[str]) -> Dict:
    """Parse PDF SYNLAB/UNILABS natif."""
    out = {}

    pat_fr_parens = re.compile(
        r"^(?P<n>[A-ZÀ-Ÿ0-9\.\-\/\s]{3,60})\s+"
        r"(?P<value>[<>]?\s*[\+\-]?\s*\d+(?:[.,]\d+)?)\s*"
        r"(?P<unit>[a-zA-ZµμÎ¼/%]+(?:\s*[a-zA-ZµμÎ¼/%]+)?)?\s*"
        r"\((?P<ref>[^)]+)\)",
        flags=re.UNICODE,
    )
    pat_fr_no_parens = re.compile(
        r"^(?P<n>[A-ZÀ-Ÿ0-9\.\-\/\s]{3,60})\s+"
        r"(?P<value>[<>]?\s*[\+\-]?\s*\d+(?:[.,]\d+)?)\s+"
        r"(?P<unit>[a-zA-ZµμÎ¼/%]+(?:\s*[a-zA-ZµμÎ¼/%]+)?)?\s+"
        r"(?P<ref>\d+(?:[.,]\d+)?\s*[-—–]\s*\d+(?:[.,]\d+)?)",
        flags=re.UNICODE,
    )
    pat_be = re.compile(
        r"^(?:>\s*)?(?P<n>[A-Za-zÀ-ÿ0-9\.\-\/\s]{3,60}?)\s+"
        r"(?P<valsign>[\+\-])?\s*(?P<value>\d+(?:[.,]\d+)?)\s+"
        r"(?P<ref>\d+(?:[.,]\d+)?\s*-\s*\d+(?:[.,]\d+)?)\s+"
        r"(?P<unit>[A-Za-zµμÎ¼/%]+(?:\s*[a-zA-ZµμÎ¼/%]+)?)\s*$",
        flags=re.UNICODE,
    )

    for ln in lines:
        if _is_synlab_noise(ln): continue
        for pat in [pat_be, pat_fr_parens, pat_fr_no_parens]:
            m = pat.match(ln)
            if m:
                name = m.group("n").strip()
                if re.search(r"\bSIEMENS\b", name, re.IGNORECASE): break
                ref = _clean_ref(m.group("ref"))
                val = _safe_float(m.group("value"))
                out[name] = {
                    "value": val,
                    "unit": m.group("unit").strip(),
                    "reference": ref,
                    "status": determine_biomarker_status(val, ref, name),
                }
                break

    return out


# ─────────────────────────────────────────────────────────────
#  Extraction biologie EUROFINS (OCR)
# ─────────────────────────────────────────────────────────────
def _extract_eurofins_ocr(lines: List[str]) -> Dict:
    """Parse lignes issues d'un PDF Eurofins via OCR."""
    out = {}
    for ln in lines:
        if _is_noise_line(ln): continue
        parsed = _parse_eurofins_line(ln)
        if not parsed or len(parsed["name"]) < 3: continue
        name = parsed["name"]
        if name not in out:
            val = parsed["value"]
            ref = parsed["reference"]
            out[name] = {
                "value": val,
                "unit": parsed["unit"],
                "reference": ref,
                "status": determine_biomarker_status(val, ref, name),
            }
    return out


# ─────────────────────────────────────────────────────────────
#  Fonction principale: extraction biologie PDF
# ─────────────────────────────────────────────────────────────
def extract_synlab_biology(pdf_path: str, progress=None) -> Dict:
    """
    Extrait les biomarqueurs d'un PDF de biologie médicale.

    Détection automatique de la source et du type de PDF:
    - SYNLAB / UNILABS : PDF natif texte encodé
    - EUROFINS          : PDF image/scan → OCR automatique
    - Autres            : tentative générique

    Returns:
        dict {nom: {value, unit, reference, status}}
    """
    if progress: progress.update(5, "Lecture PDF biologie...")

    text = _read_pdf_text(pdf_path)
    if not text or len(text) < 50:
        if progress: progress.update(30, "Biologie: 0 biomarqueurs (PDF illisible)")
        return {}

    source = _detect_pdf_source(text)
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

    if progress: progress.update(15, f"Source: {source} — parsing...")

    out = _extract_eurofins_ocr(lines) if source == "eurofins" else _extract_synlab_native(lines)

    # Fallback références par défaut
    for name, data in out.items():
        if not data.get("reference"):
            dr = _get_default_reference(name)
            if dr:
                data["reference"] = dr
                data["status"] = determine_biomarker_status(data.get("value"), dr, name)

    if progress: progress.update(30, f"Biologie: {len(out)} biomarqueurs ({source})")
    return out


# ─────────────────────────────────────────────────────────────
#  Microbiome IDK GutMAP (PDF)
# ─────────────────────────────────────────────────────────────
def _extract_bacterial_groups_v2(text: str) -> List[Dict]:
    STANDARD_GROUPS = [
        ("A1","Prominent gut microbes"),("A2","Diverse gut bacterial communities"),
        ("B1","Enriched on animal-based diet"),("C1","Complex carbohydrate degraders"),
        ("C2","Lactic acid bacteria and probiotics"),("D1","Gut epithelial integrity marker"),
        ("D2","Major SCFA producers"),("E1","Inflammation indicator"),
        ("E2","Potentially virulent"),("E3","Facultative anaerobes"),
        ("E4","Predominantly oral bacteria"),("E5","Genital, respiratory, and skin bacteria"),
    ]
    def _pr(t):
        tl = t.lower()
        if "slightly" in tl and "deviating" in tl: return "Slightly Deviating"
        if "deviating" in tl and "slightly" not in tl: return "Deviating"
        return "Expected"

    groups = []
    rms = list(re.finditer(r"Result:\s*(expected|slightly\s+deviating|deviating)\s+abundance", text, re.IGNORECASE))

    if len(rms) == len(STANDARD_GROUPS):
        for i,(code,name) in enumerate(STANDARD_GROUPS):
            groups.append({"category":code,"name":name,"abundance":_pr(rms[i].group(1))})
    else:
        for code,name in STANDARD_GROUPS:
            status = "Expected"
            m = re.search(rf"{code}[\.\s]+.{{0,600}}?Result:\s*(expected|slightly\s+deviating|deviating)", text, re.IGNORECASE|re.DOTALL)
            if m: status = _pr(m.group(1))
            groups.append({"category":code,"name":name,"abundance":status})
    return groups


def _extract_dots_from_pdf_page(page) -> List[Dict]:
    try:
        dots = []
        if hasattr(page, "curves"):
            for c in page.curves:
                if "pts" in c and len(c["pts"]) >= 4:
                    pts = c["pts"]
                    dots.append({"x":sum(p[0] for p in pts)/len(pts),"y":sum(p[1] for p in pts)/len(pts),"type":"circle"})
        if hasattr(page, "rects") and not dots:
            for r in page.rects:
                w,h = abs(r.get("x1",0)-r.get("x0",0)), abs(r.get("y1",0)-r.get("y0",0))
                if 2<w<10 and 2<h<10:
                    dots.append({"x":(r["x0"]+r["x1"])/2,"y":(r["y0"]+r["y1"])/2,"type":"rect"})
        dots.sort(key=lambda d: d["y"])
        if dots:
            xs = [d["x"] for d in dots]; xm,xx = min(xs),max(xs)
            cw = (xx-xm)/6 if xx>xm else 1
            for d in dots:
                d["abundance_level"] = max(-3,min(3,int((d["x"]-xm)/cw)-3))
        return dots
    except Exception:
        return []


def _map_abundance_to_status(level) -> str:
    if level is None: return "Not Detected"
    if level <= -2: return "Strongly Reduced"
    if level == -1: return "Reduced"
    if level == 0: return "Normal"
    if level == 1: return "Slightly Elevated"
    if level == 2: return "Elevated"
    return "Strongly Elevated"


def extract_idk_microbiome(pdf_path:str, excel_path=None, enable_graphical_detection=True,
                           resolution=200, progress=None) -> Dict:
    """Extrait les données microbiome depuis rapport IDK® GutMAP (PDF)."""
    try: import pdfplumber
    except ImportError as e: raise ImportError("pdfplumber requis") from e

    if progress: progress.update(35, "Lecture microbiome...")

    text = _read_pdf_text(pdf_path)
    lines = text.splitlines()

    di, di_text = None, "Unknown"
    for pat in [
        r"Result:\s*The\s+microbiota\s+is\s+(normobiotic|mildly\s+dysbiotic|severely\s+dysbiotic)",
        r"Dysbiosis\s+Index[:\s]+(\d+)", r"DI[:\s]+(\d+)",
    ]:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            val = m.group(1).strip().lower()
            if "normobiotic" in val: di,di_text = 1,"Normobiotic (DI 1-2)"
            elif "mildly" in val: di,di_text = 3,"Mildly dysbiotic (DI 3)"
            elif "severely" in val: di,di_text = 5,"Severely dysbiotic (DI 4-5)"
            else:
                di = _safe_float(val)
                if di: di_text = "Normobiotic (DI 1-2)" if di<=2 else "Mildly dysbiotic (DI 3)" if di==3 else "Severely dysbiotic (DI 4-5)"
            break

    diversity = None
    for pat in [
        r"Result:\s*The\s+bacterial\s+diversity\s+is\s+(as\s+expected|slightly\s+lower\s+than\s+expected|lower\s+than\s+expected)",
        r"Diversity[:\s]+(as\s+expected|slightly\s+lower|lower)",
    ]:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            v = m.group(1).strip().lower()
            diversity = "As expected" if "as expected" in v else "Slightly lower than expected" if "slightly lower" in v else "Lower than expected"
            break

    bacteria_groups = _extract_bacterial_groups_v2(text)
    bacteria_order = []; seen_ids: set = set()
    current_group_code = current_group_name = None
    bpat = re.compile(r"^\s*(\d{3})\s+([A-Za-z\[\]\s\.\-\&]+?)(?:\s+Group|\s*$)", re.MULTILINE)

    for line in lines:
        s = line.strip()
        gm = re.match(r"([A-E]\d+)\.\s+([A-Za-z\s]{3,40})", s, re.IGNORECASE)
        if gm:
            current_group_code = gm.group(1).upper()
            current_group_name = gm.group(2).strip()
            for grp in bacteria_groups:
                if grp["category"] == current_group_code:
                    current_group_name = grp["name"]; break
            continue
        bm = bpat.match(s)
        if bm:
            bid,bname = bm.group(1), bm.group(2).strip()
            if len(bname)<5 or bid in seen_ids: continue
            seen_ids.add(bid)
            ga = next((g["abundance"] for g in bacteria_groups if g["category"]==current_group_code), None)
            bacteria_order.append({"id":bid,"name":bname,"category":current_group_code or "Unknown","group":current_group_name or "","group_abundance":ga})

    all_dots = []
    if enable_graphical_detection:
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    pt = page.extract_text() or ""
                    if "Category" in pt and re.search(r"^\d{3}\s+[A-Za-z]",pt,re.MULTILINE) \
                       and "REPORT FORM EXPLANATION" not in pt and "COMMON HUMAN GUT BACTERIA" not in pt:
                        all_dots.extend(_extract_dots_from_pdf_page(page))
        except Exception: pass

    bacteria_individual = []
    for i,bact in enumerate(bacteria_order):
        level = all_dots[i].get("abundance_level",0) if i<len(all_dots) else (
            1 if "Slightly" in (bact.get("group_abundance") or "") else
            2 if "Deviating" in (bact.get("group_abundance") or "") else 0)
        bacteria_individual.append({"id":bact["id"],"name":bact["name"],"category":bact["category"],
                                     "group":bact["group"],"abundance_level":level,"status":_map_abundance_to_status(level)})

    metabolites = {}
    for mn,mp in [("butyrate",r"Butyrate[:\s]+(\d+(?:\.\d+)?)"),
                   ("acetate",r"Acetate[:\s]+(\d+(?:\.\d+)?)"),
                   ("propionate",r"Propionate[:\s]+(\d+(?:\.\d+)?)")]:
        mm = re.search(mp, text, re.IGNORECASE)
        if mm: metabolites[mn] = _safe_float(mm.group(1))

    if progress: progress.update(100, "Extraction terminée")
    return {"dysbiosis_index":di,"dysbiosis_text":di_text,"diversity":diversity,
            "diversity_metrics":None,"bacteria_individual":bacteria_individual,
            "bacteria_groups":bacteria_groups,"metabolites":metabolites or None}


# ─────────────────────────────────────────────────────────────
#  Excel biologie
# ─────────────────────────────────────────────────────────────
def extract_biology_from_excel(excel_path: str, progress=None) -> Dict:
    try:
        if progress: progress.update(10, "Lecture Excel biologie...")
        df = pd.read_excel(excel_path)
        col_name=col_value=col_unit=col_ref=None
        for col in df.columns:
            cl = str(col).lower()
            if any(k in cl for k in ("biomarqueur","marqueur","paramètre")): col_name=col
            elif any(k in cl for k in ("valeur","résultat","result")): col_value=col
            elif any(k in cl for k in ("unité","unit")): col_unit=col
            elif any(k in cl for k in ("référence","norme","range")): col_ref=col
        if not col_name or not col_value: return {}
        out = {}
        for idx,(_,row) in enumerate(df.iterrows()):
            if progress and idx%5==0: progress.update(10+int((idx/len(df))*20), f"Excel: {idx}/{len(df)}...")
            name = str(row.get(col_name,"")).strip()
            if not name or name.lower()=="nan": continue
            val = _safe_float(row.get(col_value))
            unit = str(row.get(col_unit,"")).strip() if col_unit else ""
            ref = str(row.get(col_ref,"")).strip() if col_ref else ""
            out[name] = {"value":val,"unit":unit,"reference":ref,"status":determine_biomarker_status(val,ref,name)}
        if progress: progress.update(30, f"Excel: {len(out)} entrées")
        return out
    except Exception: return {}


# ─────────────────────────────────────────────────────────────
#  Excel microbiome
# ─────────────────────────────────────────────────────────────
def extract_microbiome_from_excel(excel_path: str) -> Dict:
    """Extrait microbiome depuis Excel structuré (Analyse_Microbiome_*.xlsx)."""
    try:
        excel_file = pd.ExcelFile(excel_path)
        sheets = excel_file.sheet_names
        result: Dict[str,Any] = {
            "dysbiosis_index":None,"dysbiosis_text":"Unknown","diversity":None,
            "diversity_metrics":None,"bacteria_groups":[],"bacteria_individual":[],
            "metabolites":None,"stool_biomarkers":{}
        }

        if "Informations Patient" in sheets:
            df_info = pd.read_excel(excel_file,"Informations Patient",skiprows=1,header=None)
            for _,row in df_info.iterrows():
                champ = str(row[0]) if 0 in row.index else ""
                valeur = str(row[1]) if 1 in row.index else ""
                if pd.isna(champ) or not champ.strip() or champ.lower() in ("nan","champ"): continue
                cl = champ.lower()
                if "dysbiosis" in cl or "dysbiose" in cl:
                    mm = re.search(r"(\d+)", valeur)
                    if mm:
                        di = int(mm.group(1))
                        result["dysbiosis_index"] = di
                        result["dysbiosis_text"] = "Normobiotic (DI 1-2)" if di<=2 else "Mildly dysbiotic (DI 3)" if di==3 else "Severely dysbiotic (DI 4-5)"
                if "diversit" in cl: result["diversity"] = valeur

        if "Biomarqueurs Base" in sheets:
            df_bio = pd.read_excel(excel_file,"Biomarqueurs Base",skiprows=1,header=None)
            for _,row in df_bio.iterrows():
                bio = str(row[0]) if 0 in row.index else ""
                if not bio or bio=="nan" or pd.isna(bio) or bio.lower()=="biomarqueur": continue
                result["stool_biomarkers"][bio] = {
                    "value":row[1] if 1 in row.index else None,
                    "unit":str(row[2]) if 2 in row.index else "",
                    "reference":str(row[3]) if 3 in row.index else "",
                    "status":str(row[4]) if 4 in row.index else "Normal",
                }

        if "Microbiome Détaillé" in sheets:
            df_micro = pd.read_excel(excel_file,"Microbiome Détaillé",skiprows=1,header=None)
            categories_map: Dict[str,Any] = {}
            for _,row in df_micro.iterrows():
                category = str(row[0]) if 0 in row.index else ""
                groupe = str(row[1]) if 1 in row.index else ""
                no = str(row[2]) if 2 in row.index else ""
                bacterie = str(row[3]) if 3 in row.index else ""
                position = row[4] if 4 in row.index else 0
                if not category or category=="nan" or pd.isna(category) or category.lower()=="catégorie": continue
                gc,gn = groupe, category
                if gc not in categories_map:
                    categories_map[gc] = {"category":gc,"group":gn,"bacteria_count":0,"normal_count":0,"abnormal_count":0}
                cat = categories_map[gc]
                cat["bacteria_count"] += 1
                try: position = int(position)
                except: position = 0
                if position==0: cat["normal_count"]+=1
                else: cat["abnormal_count"]+=1
                result["bacteria_individual"].append({"id":no,"name":bacterie,"category":gc,"group":gn,
                                                      "abundance_level":position,"status":_map_abundance_to_status(position)})
            for code,info in categories_map.items():
                ab,tot = info["abnormal_count"],info["bacteria_count"]
                gr = "Deviating" if ab>tot*0.3 else "Slightly Deviating" if ab>0 else "Expected"
                result["bacteria_groups"].append({"category":code,"name":info["group"],"abundance":gr,"result":gr})

        return result
    except Exception as e:
        print(f"❌ Erreur extraction Excel microbiome: {e}")
        import traceback; traceback.print_exc()
        return {"dysbiosis_index":None,"dysbiosis_text":"Unknown","diversity":None,
                "bacteria_groups":[],"bacteria_individual":[],"metabolites":None}


# ─────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────
def biology_dict_to_list(biology: Dict, default_category="Autres") -> List[Dict]:
    out = []
    for name,d in (biology or {}).items():
        if not isinstance(d,dict): continue
        out.append({"name":str(d.get("name",name)).strip(),"value":d.get("value"),
                    "unit":str(d.get("unit","")).strip(),"reference":str(d.get("reference","")).strip(),
                    "status":str(d.get("status","Inconnu")).strip(),
                    "category":str(d.get("category",default_category)).strip() or default_category})
    return out


# ─────────────────────────────────────────────────────────────
#  Fonction principale
# ─────────────────────────────────────────────────────────────
def extract_all_data(bio_pdf_path=None, bio_excel_path=None, micro_pdf_path=None,
                     micro_excel_path=None, enable_graphical_detection=True,
                     show_progress=True) -> Tuple[Dict,Dict]:
    """
    Extraction complète toutes sources.
    Détection automatique PDF natif / image (OCR).
    """
    progress = ProgressTracker(100, show_progress) if show_progress else None
    biology: Dict = {}; microbiome: Dict = {}

    if progress: progress.update(0, "Démarrage...")
    if bio_pdf_path: biology.update(extract_synlab_biology(bio_pdf_path, progress))
    if bio_excel_path: biology.update(extract_biology_from_excel(bio_excel_path, progress))
    if micro_pdf_path:
        microbiome = extract_idk_microbiome(micro_pdf_path, micro_excel_path,
                                            enable_graphical_detection=enable_graphical_detection,
                                            resolution=200, progress=progress)
    elif micro_excel_path:
        microbiome = extract_microbiome_from_excel(micro_excel_path)
    if progress: progress.update(100, "Terminé!")
    return biology, microbiome


# ─────────────────────────────────────────────────────────────
#  CLI de test
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python extractors_v19.py <pdf_biologie> [pdf_microbiome]")
        sys.exit(1)

    bio_pdf = sys.argv[1]
    micro_pdf = sys.argv[2] if len(sys.argv) > 2 else None

    print(f"\n📄 Extraction: {bio_pdf}")
    bio, micro = extract_all_data(bio_pdf_path=bio_pdf, micro_pdf_path=micro_pdf, show_progress=True)

    print(f"\n✅ {len(bio)} biomarqueurs extraits:\n")
    icons = {"Normal":"✅","Bas":"⬇️ ","Élevé":"⬆️ "}
    for name,data in bio.items():
        ic = icons.get(data["status"], "❓")
        print(f"  {ic} {name:<45} {str(data['value']):<10} {data['unit']:<14} [{data['reference']}]  → {data['status']}")

    if micro:
        print(f"\n🦠 Microbiome: DI={micro.get('dysbiosis_index')} — {micro.get('dysbiosis_text')}")
        print(f"   Diversité : {micro.get('diversity')}")
        print(f"   Bactéries : {len(micro.get('bacteria_individual', []))}")
