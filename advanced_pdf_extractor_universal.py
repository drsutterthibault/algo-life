"""
ALGO-LIFE - Universal PDF Extractor v3.2 (CLEAN BIOMARKERS ONLY)
✅ Extraction ciblée biomarqueurs connus (TARGETED)
✅ Extraction ouverte STRICTE (OPEN) = biomarqueurs + valeur + unité + ref range
✅ Patch SYNLAB amélioré + récupération des références
✅ Anti-bruit (dates, pages, méthodes, texte non analytique)

Author: Dr Thibault SUTTER
Date: January 2026
"""

import re
from typing import Dict, List, Tuple, Optional, Any

# Imports optionnels
try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False


# ---------------------------------------------------------------------------
# Helpers parsing ranges
# ---------------------------------------------------------------------------

DASHES = r"\-–—−"  # inclut le "−" synlab

def _clean_spaces(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()

def _normalize_decimal(s: str) -> str:
    return (s or "").replace(",", ".").strip()

def _normalize_key(name: str) -> str:
    key = (name or "").lower()
    key = re.sub(r"[àâä]", "a", key)
    key = re.sub(r"[éèêë]", "e", key)
    key = re.sub(r"[îï]", "i", key)
    key = re.sub(r"[ôö]", "o", key)
    key = re.sub(r"[ùûü]", "u", key)
    key = re.sub(r"[ç]", "c", key)
    key = re.sub(r"[^a-z0-9]+", "_", key)
    key = re.sub(r"_+", "_", key).strip("_")
    return key

def _clean_biomarker_name(name: str) -> str:
    name = name or ""
    name = re.sub(r"[\.]{3,}", "", name)
    name = re.sub(r"\s+", " ", name)
    name = name.strip(" .:;,|-_")
    return name

def _looks_like_method_line(line: str) -> bool:
    """
    Lignes parasites fréquentes dans Synlab / PDF :
    - (CLIA - Siemens Atellica)
    - (Colorimétrie ...)
    """
    s = (line or "").strip()
    if not s:
        return True
    if s.startswith("(") and s.endswith(")"):
        return True
    # méthodes sans parenthèses mais typiques
    lower = s.lower()
    method_words = [
        "immuno", "chemilum", "clia", "eclia", "elisa", "siemens", "atellica", "roche",
        "colorim", "tptz", "nephel", "turbid", "hplc", "spectro", "method", "automate"
    ]
    if any(w in lower for w in method_words) and len(s) < 80:
        return True
    return False

def _is_header_or_footer(name: str) -> bool:
    ignore_patterns = [
        r"^page\s+\d+",
        r"^edition",
        r"^date",
        r"^laboratoire",
        r"^patient",
        r"^docteur",
        r"^dr\b",
        r"^prelev",
        r"^dossier",
        r"^adresse",
        r"^telephone",
        r"^email",
        r"^code",
        r"^resultat",
        r"^unite",
        r"^reference",
        r"^valeur",
        r"^commentaire",
        r"^interpretation",
        r"^biochimie",
        r"^hematologie",
        r"^immunologie",
        r"^bacteriologie",
        r"^virologie",
        r"^marqueurs",
        r"^proteines",
        r"^vitamines",
        r"^renseignements",
        r"^conclusion",
        r"^signature",
    ]
    n = (name or "").lower().strip()
    return any(re.search(p, n) for p in ignore_patterns)

def parse_reference_range(raw: str) -> Dict[str, Any]:
    """
    Extrait un range depuis un texte, ex:
      (12.5−32.2) -> {"type":"interval", "low":12.5, "high":32.2}
      (>12.19)    -> {"type":"gt", "threshold":12.19}
      (<0.5)      -> {"type":"lt", "threshold":0.5}
      (<= 1.0)    -> {"type":"lte", "threshold":1.0}
      (>= 30)     -> {"type":"gte", "threshold":30}
    Renvoie {} si rien trouvé.
    """
    if not raw:
        return {}
    s = raw.strip()
    # on accepte "(...)" ou juste "..."
    s = s.strip()
    s = s[1:-1].strip() if (s.startswith("(") and s.endswith(")")) else s

    s = s.replace(" ", "")
    s = s.replace("–", "−").replace("—", "−").replace("-", "−")  # unifie

    # intervalle a−b
    m = re.search(rf"(?P<low>\d+(?:[.,]\d+)?)\s*[{DASHES}]\s*(?P<high>\d+(?:[.,]\d+)?)", s)
    if m:
        try:
            low = float(_normalize_decimal(m.group("low")))
            high = float(_normalize_decimal(m.group("high")))
            return {"type": "interval", "low": low, "high": high, "raw": raw}
        except Exception:
            return {}

    # seuils
    m = re.search(r"(?P<op>>=|<=|>|<)\s*(?P<th>\d+(?:[.,]\d+)?)", s)
    if m:
        try:
            th = float(_normalize_decimal(m.group("th")))
            op = m.group("op")
            return {"type": {"<": "lt", ">": "gt", "<=": "lte", ">=": "gte"}[op], "threshold": th, "raw": raw}
        except Exception:
            return {}

    return {}

def looks_like_unit(unit: str) -> bool:
    """
    On veut éviter que 'ans', 'page', etc. soient pris comme unités.
    On autorise les unités biomédicales courantes.
    """
    u = (unit or "").strip()
    if not u:
        return False
    u_low = u.lower()

    # unités à rejeter
    bad = ["ans", "page", "pages", "mm", "cm", "m", "kg", "kcal", "jours", "jour", "min", "sec", "seconde"]
    if u_low in bad:
        return False

    # unités acceptées (liste volontairement large)
    good_patterns = [
        r"^(mg|g|ug|µg|ng|pg)\/?(l|dl|ml|100ml)?$",
        r"^(mmol|mol|umol|µmol|nmol|pmol)\/?(l|dl|ml)?$",
        r"^(ui|iu)\/?l?$",
        r"^(mui|mu|miu|mui)\/?l$",
        r"^(u\/l|ui\/l|iu\/l)$",
        r"^(kui|mui)\/l$",
        r"^(%)$",
        r"^(g\/l|g\/dl|mmol\/l|µmol\/l|umol\/l|nmol\/l|pmol\/l|mg\/l|mg\/dl|ng\/ml|µg\/l|ug\/l)$",
        r"^(u\/g|u\/g\s*hb|u\/gHb|u\/g\shb)$",
        r"^(ratio)$",
        r"^(u?fc\/g)$",
        r"^(10\^?\d+\/l)$",
    ]
    for p in good_patterns:
        if re.match(p, u_low.replace(" ", ""), re.IGNORECASE):
            return True

    # tolérance pour trucs type "mg/L" avec variantes
    if re.match(r"^[a-zA-Zµμ/%°]+(?:\/[a-zA-Z0-9]+)+$", u):
        return True

    return False


# ---------------------------------------------------------------------------
# Extractor
# ---------------------------------------------------------------------------

class UniversalPDFExtractor:
    """
    Extracteur PDF universel avec 2 modes:
    1. TARGETED: biomarqueurs connus avec ranges/interprétation
    2. OPEN STRICT: extraction de biomarqueurs SEULEMENT si ligne ressemble à un résultat
       => nom + valeur + unité + référence (ou valeur+unité+réf)
    ✅ PATCH SYNLAB: parsing spécifique (et récupération ranges)
    """

    def __init__(self, known_biomarkers: Optional[Dict] = None):
        self.known_biomarkers = known_biomarkers or {}

    # ============================================================
    # PASS 1: Extraction Ciblée (biomarqueurs connus)
    # ============================================================

    def extract_known_biomarkers(self, text: str, debug: bool = False) -> Dict[str, float]:
        if not self.known_biomarkers:
            return {}

        data: Dict[str, float] = {}
        text_lower = (text or "").lower()
        patterns_cache = self._build_targeted_patterns()

        for biomarker_key, pattern_list in patterns_cache.items():
            for pattern in pattern_list:
                try:
                    matches = re.finditer(pattern, text_lower, re.IGNORECASE | re.MULTILINE)
                    for match in matches:
                        try:
                            value_str = _normalize_decimal(match.group(1))
                            value = float(value_str)
                            if 0 < value < 100000:
                                data[biomarker_key] = value
                                if debug:
                                    print(f"✅ [TARGETED] {biomarker_key}: {value}")
                                break
                        except (ValueError, IndexError):
                            continue
                    if biomarker_key in data:
                        break
                except re.error:
                    continue

        return data

    def _build_targeted_patterns(self) -> Dict[str, List[str]]:
        patterns: Dict[str, List[str]] = {}

        for biomarker_key, ref_data in self.known_biomarkers.items():
            lab_names = ref_data.get("lab_names", [biomarker_key])
            pattern_list: List[str] = []

            for name in lab_names:
                name_normalized = (name or "").lower()
                name_normalized = name_normalized.replace("é", "[eé]").replace("è", "[eè]").replace("ê", "[eê]").replace("ë", "[eë]")

                # Label AVANT valeur (le plus fiable)
                pattern_list.append(rf"{name_normalized}\s*[:\s]+\s*(\d+[.,]?\d*)")

                # Label + valeur + unité + ref
                pattern_list.append(rf"{name_normalized}.*?(\d+[.,]?\d*)\s*[a-zµμ°/%A-Z/]*\s*\((.*?)\)")

                # Valeur avant label (rare)
                pattern_list.append(rf"(\d+[.,]?\d*)\s+{name_normalized}")

                # Avec symboles
                pattern_list.append(rf"{name_normalized}\s*[*+\-]*\s*(\d+[.,]?\d*)")

            patterns[biomarker_key] = pattern_list

        return patterns

    # ============================================================
    # PASS 2: Extraction Ouverte STRICTE (biomarqueurs only)
    # ============================================================

    def extract_all_biomarkers(
        self,
        text: str,
        debug: bool = False,
        min_value: float = 0.001,
        max_value: float = 100000
    ) -> Dict[str, Dict]:
        """
        Extrait des biomarqueurs (OPEN STRICT):
        - On ne conserve que des lignes "résultats" crédibles
        - Extrait: name, value, unit, reference_range
        """
        data: Dict[str, Dict] = {}
        raw_text = text or ""

        # 1) Synlab parser strict (prioritaire)
        if self._is_synlab_format(raw_text):
            if debug:
                print("🔍 Format SYNLAB détecté - parser strict")
            synlab_data = self._extract_synlab_specific(raw_text, debug=debug, min_value=min_value, max_value=max_value)
            data.update(synlab_data)

        # 2) Parse ligne par ligne avec règles STRICTES
        lines = raw_text.split("\n")

        # Pattern strict : NOM  <spaces>  VALEUR  UNITE  (REF)
        # Ex: "Fer serique   18.0  µmol/l   (12.5−32.2)"
        strict_line_patterns = [
            rf"""
            ^(?P<name>[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ0-9\s\-\(\)\/\+]+?)      # nom (pas vide)
            \s{{2,}}                                               # séparation
            (?P<value>\d+[.,]?\d*)                                 # valeur
            \s+
            (?P<unit>[A-Za-zµμ°/%]+(?:\/[A-Za-z0-9]+)?)            # unité
            \s*
            (?P<ref>\(.*?\))?                                      # ref optionnelle (mais filtrée ensuite)
            $
            """,
            # Variante "Nom: valeur unité (ref)"
            rf"""
            ^(?P<name>[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ0-9\s\-\(\)\/\+]+?)
            \s*[:]\s*
            (?P<value>\d+[.,]?\d*)
            \s+
            (?P<unit>[A-Za-zµμ°/%]+(?:\/[A-Za-z0-9]+)?)
            \s*
            (?P<ref>\(.*?\))?
            $
            """,
        ]

        # On veut éviter les faux positifs :
        # ✅ On exige: (ref) présent OU (unité biomédicale + ligne ressemble à résultat)
        # et on rejette: méthodes, headers, etc.
        for i, line in enumerate(lines):
            line_clean = _clean_spaces(line)
            if not line_clean or len(line_clean) < 6:
                continue

            # skip gros bruit
            if _looks_like_method_line(line_clean):
                continue

            # stop si c'est une ligne très narrative (beaucoup de ponctuation)
            if line_clean.count(",") >= 3 and "(" not in line_clean:
                continue

            for pidx, pattern in enumerate(strict_line_patterns):
                m = re.match(pattern, line_clean, re.IGNORECASE | re.VERBOSE)
                if not m:
                    continue

                name = _clean_biomarker_name(m.group("name"))
                value_str = _normalize_decimal(m.group("value"))
                unit = (m.group("unit") or "").strip()
                ref_raw = m.group("ref") or ""

                if _is_header_or_footer(name):
                    break
                if len(name) < 3 or len(name) > 80:
                    break

                # unit doit ressembler à une unité biomédicale
                if not looks_like_unit(unit):
                    # si on n'a pas d'unité crédible, on ne garde PAS
                    break

                try:
                    value = float(value_str)
                except Exception:
                    break

                if not (min_value <= value <= max_value):
                    break

                ref = parse_reference_range(ref_raw)

                # ✅ règle anti-faux-positif principale:
                # on garde seulement si on a une référence exploitable
                # OU si on est dans une "section résultat" typique (Synlab) déjà traitée.
                # Ici (parse générique), on exige ref.
                if not ref:
                    break

                key = _normalize_key(name)
                candidate = {
                    "name": name,
                    "value": value,
                    "unit": unit,
                    "reference": ref,
                    "raw_text": line_clean,
                    "line_number": i,
                    "pattern_used": f"strict_{pidx}",
                }

                # Dedup: on garde celui avec ref intervalle plutôt que seuil, et le plus long raw_text
                if key not in data:
                    data[key] = candidate
                else:
                    prev = data[key]
                    prev_ref = prev.get("reference", {}) or {}
                    cand_ref = candidate.get("reference", {}) or {}

                    def ref_score(r: Dict[str, Any]) -> int:
                        if r.get("type") == "interval":
                            return 3
                        if r.get("type") in ["gt", "lt", "gte", "lte"]:
                            return 2
                        return 0

                    if (ref_score(cand_ref) > ref_score(prev_ref)) or (len(candidate["raw_text"]) > len(prev.get("raw_text", ""))):
                        data[key] = candidate

                if debug:
                    rr = candidate["reference"]
                    if rr.get("type") == "interval":
                        rr_s = f"[{rr['low']}-{rr['high']}]"
                    else:
                        rr_s = f"{rr.get('type')} {rr.get('threshold')}"
                    print(f"✅ [OPEN-STRICT] {name} = {value} {unit} | ref {rr_s} (line {i})")

                break  # stop patterns for this line

        return data

    # ============================================================
    # ✅ PATCH SYNLAB: Extraction spécifique + ref ranges
    # ============================================================

    def _is_synlab_format(self, text: str) -> bool:
        synlab_markers = [
            "synlab",
            "laboratoire de biologie médicale",
            "biologistes médicaux",
            "dossier validé biologiquement",
        ]
        tl = (text or "").lower()
        return any(m in tl for m in synlab_markers)

    def _extract_synlab_specific(
        self,
        text: str,
        debug: bool = False,
        min_value: float = 0.001,
        max_value: float = 100000
    ) -> Dict[str, Dict]:
        """
        Synlab strict:
        Nom  <2+ spaces>  valeur  unité   (ref)
        Ex:
          Fer serique                    18.0  µmol/l      (12.5−32.2)
          Transferrine                   1.88  g/l         (2.00−3.60)
          Folates sériques ...           42.90 nmol/l     (>12.19)
        """
        data: Dict[str, Dict] = {}
        lines = (text or "").split("\n")

        synlab_pattern = rf"""
        ^(?P<name>[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ0-9\s\-\(\)\/\+]+?)
        \s{{2,}}
        (?P<value>\d+[.,]?\d*)
        \s+
        (?P<unit>[A-Za-zµμ°/%]+(?:\/[A-Za-z0-9]+)?)
        \s*
        (?P<ref>\(.*?\))?
        $
        """

        for i, line in enumerate(lines):
            line_clean = _clean_spaces(line)

            if not line_clean or len(line_clean) < 6:
                continue
            if line_clean.startswith(("Edition", "Page", "Dossier")):
                continue
            if "biologiquement" in line_clean.lower():
                continue
            if _looks_like_method_line(line_clean):
                continue

            m = re.match(synlab_pattern, line_clean, re.IGNORECASE | re.VERBOSE)
            if not m:
                continue

            name = _clean_biomarker_name(m.group("name"))
            unit = (m.group("unit") or "").strip()
            ref_raw = m.group("ref") or ""

            if _is_header_or_footer(name):
                continue
            if len(name) < 3 or len(name) > 80:
                continue
            if not looks_like_unit(unit):
                continue

            try:
                value = float(_normalize_decimal(m.group("value")))
            except Exception:
                continue
            if not (min_value <= value <= max_value):
                continue

            ref = parse_reference_range(ref_raw)

            # ✅ en Synlab: si pas de ref sur la ligne, on rejette (évite bruit)
            if not ref:
                continue

            key = _normalize_key(name)
            if key not in data:
                data[key] = {
                    "name": name,
                    "value": value,
                    "unit": unit,
                    "reference": ref,
                    "raw_text": line_clean,
                    "line_number": i,
                    "pattern_used": "synlab_strict",
                }
                if debug:
                    rr = data[key]["reference"]
                    rr_s = f"[{rr['low']}-{rr['high']}]" if rr.get("type") == "interval" else f"{rr.get('type')} {rr.get('threshold')}"
                    print(f"✅ [SYNLAB-STRICT] {name} = {value} {unit} | ref {rr_s}")

        return data

    # ============================================================
    # PASS 3: Fusion Intelligente
    # ============================================================

    def extract_complete(
        self,
        text: str,
        debug: bool = False,
        prioritize_known: bool = True
    ) -> Tuple[Dict[str, float], Dict[str, Dict]]:
        known = self.extract_known_biomarkers(text, debug=debug)
        all_data = self.extract_all_biomarkers(text, debug=debug)

        # enrichir all_data via known (canonical_key)
        if prioritize_known:
            for key, value in known.items():
                norm = _normalize_key(key)
                if norm in all_data:
                    all_data[norm]["is_known"] = True
                    all_data[norm]["canonical_key"] = key
                    # si l'unité est vide en OPEN mais connue dans la DB
                    if not all_data[norm].get("unit"):
                        all_data[norm]["unit"] = self.known_biomarkers.get(key, {}).get("unit", "")
                else:
                    # ajouter entrée minimale (sans ref si non détectée)
                    all_data[norm] = {
                        "name": key.replace("_", " ").title(),
                        "value": value,
                        "unit": self.known_biomarkers.get(key, {}).get("unit", ""),
                        "reference": {},  # inconnu
                        "is_known": True,
                        "canonical_key": key,
                        "pattern_used": "targeted_only",
                    }

        return known, all_data

    # ============================================================
    # Extraction PDF complète
    # ============================================================

    @staticmethod
    def extract_text_from_pdf(pdf_file) -> str:
        text = ""

        # Méthode 1: pdfplumber
        if PDFPLUMBER_AVAILABLE:
            try:
                with pdfplumber.open(pdf_file) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
                    if text.strip():
                        return text
            except Exception:
                pass

        # Méthode 2: PyPDF2
        if PYPDF2_AVAILABLE:
            try:
                pdf_file.seek(0)
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                for page in pdf_reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            except Exception:
                pass

        if not text:
            raise ImportError("PDF libraries not available or empty extraction. Install pdfplumber or PyPDF2.")

        return text

    def extract_from_pdf_file(
        self,
        pdf_file,
        debug: bool = False
    ) -> Tuple[Dict[str, float], Dict[str, Dict], str]:
        text = self.extract_text_from_pdf(pdf_file)
        known, all_data = self.extract_complete(text, debug=debug)
        return known, all_data, text


# ============================================================
# Exemple
# ============================================================

if __name__ == "__main__":
    known_db = {
        "crp": {"unit": "mg/L", "lab_names": ["crp", "crp ultrasensible", "hs-crp", "crp-us"]},
        "vit_d": {"unit": "ng/mL", "lab_names": ["vitamine d", "25-oh d", "vitamin d", "25-oh-vitamine d"]},
        "ferritine": {"unit": "ng/ml", "lab_names": ["ferritine"]},
        "folates": {"unit": "nmol/l", "lab_names": ["folates", "folates sériques", "vitamine b9"]},
    }

    extractor = UniversalPDFExtractor(known_biomarkers=known_db)

    sample_text = """
    SYNLAB Pays de Savoie
    Laboratoire de biologie médicale

    BIOCHIMIE − SANG

    Fer serique                    18.0  µmol/l      (12.5−32.2)
    (Colorimétrie TPTZ )           101   µg/100ml    (70−180)

    Transferrine                   1.88  g/l         (2.00−3.60)
    (Immunoturbidimétrie Siemens)

    Calcium                        2.38  mmol/l      (2.18−2.60)
    (Complexometrie −Siemens)      96    mg/l        (88−105)

    PROTEINES − MARQUEURS − VITAMINES − SANG

    FERRITINE                      187.5 ng/ml      (22.0−322.0)
    (CLIA − Siemens Atellica)

    Folates sériques (vitamine B9) 42.90 nmol/l     (>12.19)
    (CLIA − Siemens Atellica)      18.9  ng/ml      (>5.4)

    25−OH−Vitamine D(D2+D3)        90.8  nmol/l     (>75.0)
    (CLIA − Siemens Atellica)      36.3  ng/ml      (>30.0)

    Ceci est un paragraphe narratif avec 2026 et 15% de texte.
    """

    known, all_biomarkers = extractor.extract_complete(sample_text, debug=True)

    print("\n" + "=" * 60)
    print(f"✅ CONNUS extraits: {len(known)}")
    print(known)

    print("\n" + "=" * 60)
    print(f"✅ TOTAL (OPEN STRICT) extraits: {len(all_biomarkers)}")
    for k, d in all_biomarkers.items():
        marker = "⭐" if d.get("is_known") else "🆕"
        ref = d.get("reference", {}) or {}
        if ref.get("type") == "interval":
            rr = f"[{ref['low']}-{ref['high']}]"
        elif ref.get("type"):
            rr = f"{ref['type']} {ref.get('threshold')}"
        else:
            rr = "-"
        print(f"  {marker} {d['name']}: {d['value']} {d.get('unit','')} | ref {rr}")
