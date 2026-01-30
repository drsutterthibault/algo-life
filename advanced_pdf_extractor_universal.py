"""
ALGO-LIFE - Universal Extractor v2.3 (CLEAN + REF RANGES + SYNLAB)
✅ Extraction propre biomarqueurs uniquement (anti-parasites)
✅ Parse unités + références: (low–high), >x, <x
✅ SYNLAB patch robuste (lignes tabulées + méthodes entre parenthèses)
✅ Sortie structurée prête pour rules engine Excel

Author: Dr Thibault SUTTER
Date: Jan 2026
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


class UniversalPDFExtractor:
    """
    Extracteur PDF universel avec 2 passes:
      1) TARGETED: biomarqueurs connus (clé canonique) -> value
      2) OPEN CLEAN: extraction générique des lignes "biomarqueur | valeur | unité | ref"
    """

    def __init__(self, known_biomarkers: Optional[Dict] = None):
        self.known_biomarkers = known_biomarkers or {}
        self._targeted_patterns_cache = self._build_targeted_patterns() if self.known_biomarkers else {}

    # ============================================================
    # PASS 1: Extraction ciblée (biomarqueurs connus)
    # ============================================================

    def extract_known_biomarkers(self, text: str, debug: bool = False) -> Dict[str, float]:
        if not self.known_biomarkers:
            return {}

        data: Dict[str, float] = {}
        text_lower = text.lower()

        for biomarker_key, pattern_list in self._targeted_patterns_cache.items():
            for pattern in pattern_list:
                try:
                    for match in re.finditer(pattern, text_lower, re.IGNORECASE | re.MULTILINE):
                        try:
                            value_str = match.group(1).replace(',', '.').strip()
                            value = float(value_str)

                            # sanity
                            if self._is_value_plausible(value):
                                data[biomarker_key] = value
                                if debug:
                                    print(f"✅ [TARGETED] {biomarker_key}: {value}")
                                break
                        except Exception:
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
                name_norm = self._normalize_for_regex(name)

                # label -> valeur (classique)
                pattern_list.append(rf'{name_norm}\s*[:\s]\s*(\d+[.,]?\d*)')

                # label ... valeur unité
                pattern_list.append(rf'{name_norm}\s+(\d+[.,]?\d*)\s*[a-zµμ°/%A-Z]{{0,12}}')

                # valeur -> label (rare)
                pattern_list.append(rf'(\d+[.,]?\d*)\s+{name_norm}')

                # label * + - valeur
                pattern_list.append(rf'{name_norm}\s*[*+\-]?\s*(\d+[.,]?\d*)')

            patterns[biomarker_key] = pattern_list

        return patterns

    def _normalize_for_regex(self, s: str) -> str:
        """
        normalise pour regex accent tolerant
        """
        s = s.lower().strip()
        s = re.escape(s)

        # tolérance accents fréquents
        s = s.replace("e", "[eéèêë]")
        s = s.replace("a", "[aàâä]")
        s = s.replace("i", "[iîï]")
        s = s.replace("o", "[oôö]")
        s = s.replace("u", "[uùûü]")
        s = s.replace("c", "[cç]")

        return s

    # ============================================================
    # PASS 2: Extraction ouverte CLEAN (uniquement lignes biomarqueurs)
    # ============================================================

    def extract_all_biomarkers(
        self,
        text: str,
        debug: bool = False,
        min_value: float = 0.0001,
        max_value: float = 100000
    ) -> Dict[str, Dict[str, Any]]:
        """
        Retour:
          Dict[key, {
              name, value, unit,
              ref_low, ref_high, ref_type,
              raw_text, line_number,
              is_known, canonical_key
          }]
        """
        data: Dict[str, Dict[str, Any]] = {}

        # pré-clean texte
        lines = self._preclean_lines(text)

        # SYNLAB: parser spécifique prioritaire (meilleur SNR)
        if self._is_synlab_format(text):
            if debug:
                print("🔍 SYNLAB détecté -> parser Synlab CLEAN")
            syn = self._extract_synlab_specific(lines, debug=debug, min_value=min_value, max_value=max_value)
            data.update(syn)

        # OPEN CLEAN parser (générique mais strict)
        for i, line in enumerate(lines):
            if not self._is_candidate_biomarker_line(line):
                continue

            parsed = self._parse_line_generic(line)
            if not parsed:
                continue

            name, value, unit, ref = parsed["name"], parsed["value"], parsed["unit"], parsed["ref"]

            if not (min_value <= value <= max_value):
                continue

            # anti-faux positifs: exige un signe biomédical (unité OU ref_range OU nom connu)
            key = self._normalize_key(name)
            is_known = self._is_known_name_or_key(name, key)

            has_unit = bool(unit)
            has_ref = ref is not None

            if not (is_known or has_unit or has_ref):
                # sinon tu récupères des chiffres de paragraphes et tu pleures
                continue

            # blacklist fin: headers/footers
            if self._is_header_or_footer(name):
                continue

            # stock
            if key not in data:
                entry = {
                    "name": name,
                    "value": value,
                    "unit": unit,
                    "raw_text": line,
                    "line_number": i,
                    "pattern_used": "generic_clean",
                    "ref_low": None,
                    "ref_high": None,
                    "ref_type": None,
                    "is_known": False,
                    "canonical_key": None,
                }

                if ref:
                    entry["ref_low"] = ref.get("low")
                    entry["ref_high"] = ref.get("high")
                    entry["ref_type"] = ref.get("type")

                # map vers clé canonique si biomarqueur connu
                canon = self._canonical_key_from_name(name)
                if canon:
                    entry["is_known"] = True
                    entry["canonical_key"] = canon

                data[key] = entry
                if debug:
                    rl = entry["ref_low"]
                    rh = entry["ref_high"]
                    print(f"✅ [OPEN CLEAN] {name} = {value} {unit} | ref=({rl},{rh})")

        return data

    # ============================================================
    # PASS 3: Fusion intelligente (known + all)
    # ============================================================

    def extract_complete(
        self,
        text: str,
        debug: bool = False,
        prioritize_known: bool = True
    ) -> Tuple[Dict[str, float], Dict[str, Dict[str, Any]]]:
        known = self.extract_known_biomarkers(text, debug=debug)
        all_data = self.extract_all_biomarkers(text, debug=debug)

        if prioritize_known and known:
            for canonical_key, value in known.items():
                # inject dans all_data si absent, sinon marque is_known
                canon_name = canonical_key.replace("_", " ").title()
                canon_norm = self._normalize_key(canon_name)

                found_key = None
                # tente match direct canonical_key dans data via canonical_key stocké
                for k, v in all_data.items():
                    if v.get("canonical_key") == canonical_key:
                        found_key = k
                        break

                if found_key:
                    all_data[found_key]["is_known"] = True
                    all_data[found_key]["canonical_key"] = canonical_key
                    all_data[found_key]["value"] = value
                else:
                    all_data[canon_norm] = {
                        "name": canon_name,
                        "value": value,
                        "unit": self.known_biomarkers.get(canonical_key, {}).get("unit", ""),
                        "raw_text": "",
                        "line_number": -1,
                        "pattern_used": "targeted_only",
                        "ref_low": None,
                        "ref_high": None,
                        "ref_type": None,
                        "is_known": True,
                        "canonical_key": canonical_key,
                    }

        return known, all_data

    # ============================================================
    # SYNLAB parser CLEAN
    # ============================================================

    def _is_synlab_format(self, text: str) -> bool:
        markers = [
            "synlab",
            "laboratoire de biologie médicale",
            "dossier validé biologiquement",
            "biologistes médicaux",
        ]
        t = text.lower()
        return any(m in t for m in markers)

    def _extract_synlab_specific(
        self,
        lines: List[str],
        debug: bool = False,
        min_value: float = 0.0001,
        max_value: float = 100000
    ) -> Dict[str, Dict[str, Any]]:
        """
        Pattern SYNLAB typique:
          Fer serique   18.0  µmol/l   (12.5−32.2)
          FERRITINE     187.5 ng/ml    (22.0−322.0)
          Folates ...   42.90 nmol/l   (>12.19)
        """
        data: Dict[str, Dict[str, Any]] = {}

        # nom  + espaces + valeur + unité + ref(OPTION)
        # on accepte unités du style µmol/l, g/l, mg/L, ng/ml, %, etc.
        pat = re.compile(
            r'^([A-Za-zÀ-ÿ0-9\s\-\(\)\+\/]+?)\s{2,}'
            r'(\d+[.,]?\d*)\s+'
            r'([a-zA-Zµμ°/%]+(?:/[a-zA-Z0-9]+)?)'
            r'(?:\s*\(([^)]{1,40})\))?\s*$'
        )

        for i, line in enumerate(lines):
            # ignore méthodes entre parenthèses seule
            if line.startswith("(") and line.endswith(")"):
                continue

            if not self._is_candidate_biomarker_line(line):
                continue

            m = pat.match(line)
            if not m:
                continue

            name = self._clean_biomarker_name(m.group(1))
            value_str = m.group(2).replace(",", ".").strip()
            unit = (m.group(3) or "").strip()
            ref_raw = (m.group(4) or "").strip()

            if self._is_header_or_footer(name):
                continue

            try:
                value = float(value_str)
            except ValueError:
                continue

            if not (min_value <= value <= max_value) or not self._is_value_plausible(value):
                continue

            # parse ref
            ref = self._parse_reference(ref_raw) if ref_raw else None

            key = self._normalize_key(name)

            if key not in data:
                entry = {
                    "name": name,
                    "value": value,
                    "unit": unit,
                    "raw_text": line,
                    "line_number": i,
                    "pattern_used": "synlab_clean",
                    "ref_low": None,
                    "ref_high": None,
                    "ref_type": None,
                    "is_known": False,
                    "canonical_key": None,
                }
                if ref:
                    entry["ref_low"] = ref.get("low")
                    entry["ref_high"] = ref.get("high")
                    entry["ref_type"] = ref.get("type")

                canon = self._canonical_key_from_name(name)
                if canon:
                    entry["is_known"] = True
                    entry["canonical_key"] = canon

                data[key] = entry
                if debug:
                    print(f"✅ [SYNLAB CLEAN] {name} = {value} {unit} ref={ref_raw}")

        return data

    # ============================================================
    # Generic CLEAN parsing
    # ============================================================

    def _parse_line_generic(self, line: str) -> Optional[Dict[str, Any]]:
        """
        Parse une ligne sous formes courantes :
          "CRP ultrasensible .... 1.2 mg/L (0.0-3.0)"
          "Ferritine: 22 ng/mL (22-322)"
          "25-OH Vitamine D 36.3 ng/ml (>30.0)"
        """
        # 1) tabulé: name .... value unit (ref)
        tab = re.compile(
            r'^([A-Za-zÀ-ÿ0-9\s\-\(\)\+\/]+?)\s*[\.:\s]{2,}\s*'
            r'(\d+[.,]?\d*)\s*'
            r'([a-zA-Zµμ°/%]+(?:/[a-zA-Z0-9]+)?)?'
            r'(?:\s*\(([^)]{1,40})\))?\s*$'
        )

        # 2) "name: value unit (ref)"
        colon = re.compile(
            r'^([A-Za-zÀ-ÿ0-9\s\-\(\)\+\/]+?)\s*[:]\s*'
            r'(\d+[.,]?\d*)\s*'
            r'([a-zA-Zµμ°/%]+(?:/[a-zA-Z0-9]+)?)?'
            r'(?:\s*\(([^)]{1,40})\))?\s*$'
        )

        # 3) "name value unit (ref)" (moins strict)
        space = re.compile(
            r'^([A-Za-zÀ-ÿ0-9\s\-\(\)\+\/]+?)\s+'
            r'(\d+[.,]?\d*)\s*'
            r'([a-zA-Zµμ°/%]+(?:/[a-zA-Z0-9]+)?)?'
            r'(?:\s*\(([^)]{1,40})\))?\s*$'
        )

        for pat in (tab, colon, space):
            m = pat.match(line)
            if not m:
                continue

            name = self._clean_biomarker_name(m.group(1))
            value_str = m.group(2).replace(",", ".").strip()
            unit = (m.group(3) or "").strip()
            ref_raw = (m.group(4) or "").strip()

            # name sanity
            if len(name) < 3 or len(name) > 80:
                return None

            # évite "Edition 1 2 3", etc.
            if self._is_header_or_footer(name):
                return None

            try:
                value = float(value_str)
            except ValueError:
                return None

            if not self._is_value_plausible(value):
                return None

            ref = self._parse_reference(ref_raw) if ref_raw else None

            return {"name": name, "value": value, "unit": unit, "ref": ref}

        return None

    def _parse_reference(self, ref_raw: str) -> Optional[Dict[str, Any]]:
        """
        Parse:
          "12.5−32.2" / "12.5-32.2"
          ">30.0" / ">= 75"
          "<5.4"
        """
        if not ref_raw:
            return None

        s = ref_raw.strip()
        s = s.replace("−", "-").replace("–", "-")
        s = s.replace(",", ".")
        s = re.sub(r"\s+", "", s)

        # range low-high
        m = re.match(r"^(\d+\.?\d*)-(\d+\.?\d*)$", s)
        if m:
            return {"type": "range", "low": float(m.group(1)), "high": float(m.group(2))}

        # >x / >=x
        m = re.match(r"^(>=|>)(\d+\.?\d*)$", s)
        if m:
            return {"type": "lower_bound", "low": float(m.group(2)), "high": None}

        # <x / <=x
        m = re.match(r"^(<=|<)(\d+\.?\d*)$", s)
        if m:
            return {"type": "upper_bound", "low": None, "high": float(m.group(2))}

        return None

    # ============================================================
    # Filtering / Cleaning
    # ============================================================

    def _preclean_lines(self, text: str) -> List[str]:
        lines = []
        for raw in text.split("\n"):
            line = raw.strip()
            if not line:
                continue
            line = re.sub(r"\s{2,}", "  ", line)  # compact spaces
            lines.append(line)
        return lines

    def _is_candidate_biomarker_line(self, line: str) -> bool:
        """
        Filtre fort anti-parasites :
          - doit contenir au moins un chiffre
          - évite les paragraphes longs
          - évite adresses, pages, dates, etc.
        """
        if len(line) < 5:
            return False
        if len(line) > 140:
            return False

        # doit contenir un nombre
        if not re.search(r"\d", line):
            return False

        # évite URLs / emails / numéros de page
        low = line.lower()
        if "http" in low or "www" in low or "@" in low:
            return False

        # évite "Page X", "Edition", "Dossier", "Adresse"
        if re.search(r"^(page|edition|dossier|adresse|t[eé]l|fax)\b", low):
            return False

        return True

    def _is_value_plausible(self, value: float) -> bool:
        # évite certains faux positifs (années, codes)
        if value == 0:
            return False
        if 1800 <= value <= 2100:
            return False
        return True

    def _clean_biomarker_name(self, name: str) -> str:
        name = re.sub(r"[\.]{3,}", "", name)
        name = re.sub(r"\s+", " ", name).strip()
        name = name.strip(".:;,|-_")
        return name

    def _normalize_key(self, name: str) -> str:
        key = name.lower()
        key = re.sub(r"[àâä]", "a", key)
        key = re.sub(r"[éèêë]", "e", key)
        key = re.sub(r"[îï]", "i", key)
        key = re.sub(r"[ôö]", "o", key)
        key = re.sub(r"[ùûü]", "u", key)
        key = re.sub(r"[ç]", "c", key)
        key = re.sub(r"[^a-z0-9]+", "_", key)
        key = re.sub(r"_+", "_", key).strip("_")
        return key

    def _is_header_or_footer(self, name: str) -> bool:
        ignore_patterns = [
            r"^page\s+\d+",
            r"^date",
            r"^laboratoire",
            r"^patient",
            r"^docteur",
            r"^pr[ée]lev",
            r"^r[ée]f[ée]rence",
            r"^valeur",
            r"^r[ée]sultat",
            r"^unit[ée]",
            r"^biochimie",
            r"^h[ée]matologie",
            r"^immunologie",
            r"^microbiologie",
            r"^commentaire",
            r"^interpretation",
            r"^conclusion",
            r"^m[ée]thode",
        ]
        low = name.lower()
        return any(re.search(p, low) for p in ignore_patterns)

    def _is_known_name_or_key(self, name: str, key: str) -> bool:
        if not self.known_biomarkers:
            return False
        if key in self.known_biomarkers:
            return True
        # match par alias
        return self._canonical_key_from_name(name) is not None

    def _canonical_key_from_name(self, extracted_name: str) -> Optional[str]:
        """
        Retourne canonical_key si extracted_name match un lab_name connu
        """
        if not self.known_biomarkers:
            return None
        n = extracted_name.lower().strip()

        for canon, meta in self.known_biomarkers.items():
            for alias in meta.get("lab_names", [canon]):
                a = alias.lower().strip()
                if a and a in n:
                    return canon
        return None

    # ============================================================
    # Extraction PDF complète
    # ============================================================

    @staticmethod
    def extract_text_from_pdf(pdf_file) -> str:
        text = ""

        # pdfplumber
        if PDFPLUMBER_AVAILABLE:
            try:
                pdf_file.seek(0)
                with pdfplumber.open(pdf_file) as pdf:
                    for page in pdf.pages:
                        t = page.extract_text()
                        if t:
                            text += t + "\n"
                if text.strip():
                    return text
            except Exception:
                pass

        # PyPDF2
        if PYPDF2_AVAILABLE:
            try:
                pdf_file.seek(0)
                reader = PyPDF2.PdfReader(pdf_file)
                for page in reader.pages:
                    t = page.extract_text()
                    if t:
                        text += t + "\n"
                if text.strip():
                    return text
            except Exception:
                pass

        raise ImportError("PDF libraries not available. Install pdfplumber or PyPDF2.")

    def extract_from_pdf_file(self, pdf_file, debug: bool = False) -> Tuple[Dict[str, float], Dict[str, Dict[str, Any]], str]:
        text = self.extract_text_from_pdf(pdf_file)
        known, all_data = self.extract_complete(text, debug=debug)
        return known, all_data, text
