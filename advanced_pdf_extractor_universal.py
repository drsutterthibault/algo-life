"""
ALGO-LIFE - Universal Extractor v2.3.2 (STRICT VALUES ONLY)
✅ Extraction biomarqueurs uniquement (mode STRICT par défaut)
✅ Anti-parasites renforcé: rejette phrases, commentaires, conclusions, headers, etc.
✅ Parse unités + références: (low–high), >x, <x, "x - y", "x à y"
✅ SYNLAB patch robuste (lignes tabulées + méthodes entre parenthèses)
✅ Sortie structurée prête pour rules engine Excel
✅ Sécurisé: anti-années/codes, anti-lignes texte, anti-faux positifs
✅ IMPORTANT: extract_from_pdf_file() ne renvoie plus le texte brut par défaut

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
      2) OPEN CLEAN STRICT: extraction stricte des lignes "biomarqueur | valeur | unité/ref"
    """

    # unités "biomédicales" courantes
    _UNIT_HINTS = {
        "mg", "g", "kg", "ug", "µg", "ng", "pg",
        "l", "dl", "ml", "ul", "µl",
        "mol", "mmol", "umol", "µmol",
        "iu", "ui", "u", "meq",
        "u/l", "ui/l", "iu/l", "mu/l", "mui/l",
        "g/l", "mg/l", "mg/dl", "g/dl",
        "mmol/l", "µmol/l", "umol/l", "nmol/l", "pmol/l",
        "%", "h", "min", "sec",
        "/l", "/ml", "/dl",
        "kpa", "mmhg",
        "u/g", "u/ghb", "u/ghb", "u/ghb",
        "u/ghb", "u/g hb", "u/ghb",
    }

    # tokens parasites fréquents (footers, intitulés, méthodes, etc.)
    _BAD_TOKENS = {
        "edition", "page", "dossier", "adresse", "telephone", "tél", "fax",
        "laboratoire", "biologie", "biologiste", "validation", "validé", "valide",
        "patient", "docteur", "médecin", "prescripteur",
        "commentaire", "interpretation", "interprétation", "conclusion",
        "methode", "méthode", "technique", "instrument", "automate",
        "signature", "service", "site", "centre", "imprimé", "imprime",
        "renseignements", "identité", "identite", "adresse", "telephone",
        "facture", "cotation", "code", "nomenclature",
    }

    # stopwords qui indiquent une phrase (donc pas une ligne résultat)
    _SENTENCE_STOPWORDS = {
        "avec", "sans", "pour", "chez", "vous", "nous", "afin", "selon",
        "en raison", "ceci", "cela", "peut", "doit", "recommande", "recommandé",
        "interprétation", "interpretation", "commentaire", "conclusion",
        "valeurs", "résultats", "resultats", "référence", "reference",
        "méthode", "methode", "principe", "technique",
    }

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
                            value_str = match.group(1).replace(",", ".").strip()
                            value = float(value_str)
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
                pattern_list.append(rf"{name_norm}\s*[:\s]\s*(\d+[.,]?\d*)")
                pattern_list.append(rf"{name_norm}\s+(\d+[.,]?\d*)\s*[a-zµμ°/%A-Z]{{0,12}}")
                pattern_list.append(rf"(\d+[.,]?\d*)\s+{name_norm}")
                pattern_list.append(rf"{name_norm}\s*[*+\-]?\s*(\d+[.,]?\d*)")
            patterns[biomarker_key] = pattern_list
        return patterns

    def _normalize_for_regex(self, s: str) -> str:
        s = s.lower().strip()
        s = re.escape(s)
        s = s.replace("e", "[eéèêë]")
        s = s.replace("a", "[aàâä]")
        s = s.replace("i", "[iîï]")
        s = s.replace("o", "[oôö]")
        s = s.replace("u", "[uùûü]")
        s = s.replace("c", "[cç]")
        return s

    # ============================================================
    # PASS 2: Extraction ouverte STRICT (uniquement lignes résultat)
    # ============================================================

    def extract_all_biomarkers(
        self,
        text: str,
        debug: bool = False,
        min_value: float = 0.0001,
        max_value: float = 100000,
        strict: bool = True,
        keep_raw_text_field: bool = True,
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
        lines = self._preclean_lines(text)

        # SYNLAB prioritaire
        if self._is_synlab_format(text):
            if debug:
                print("🔍 SYNLAB détecté -> parser Synlab CLEAN")
            syn = self._extract_synlab_specific(
                lines, debug=debug, min_value=min_value, max_value=max_value, keep_raw_text_field=keep_raw_text_field
            )
            data.update(syn)

        # OPEN STRICT
        for i, line in enumerate(lines):
            if not self._is_candidate_biomarker_line(line, strict=strict):
                continue

            parsed = self._parse_line_generic(line, strict=strict)
            if not parsed:
                continue

            name, value, unit, ref = parsed["name"], parsed["value"], parsed["unit"], parsed["ref"]

            if not (min_value <= value <= max_value):
                continue

            key = self._normalize_key(name)
            is_known = self._is_known_name_or_key(name, key)

            has_unit = self._looks_like_unit(unit)
            has_ref = ref is not None

            # si pas connu, exige unit OU ref
            if not (is_known or has_unit or has_ref):
                continue

            if self._is_header_or_footer(name):
                continue

            if not is_known and not self._looks_like_biomarker_name(name):
                continue

            if key not in data:
                entry: Dict[str, Any] = {
                    "name": name,
                    "value": value,
                    "unit": unit,
                    "line_number": i,
                    "pattern_used": "generic_strict",
                    "ref_low": None,
                    "ref_high": None,
                    "ref_type": None,
                    "is_known": False,
                    "canonical_key": None,
                }

                if keep_raw_text_field:
                    entry["raw_text"] = line

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
                    rl = entry["ref_low"]
                    rh = entry["ref_high"]
                    print(f"✅ [STRICT] {name} = {value} {unit} | ref=({rl},{rh})")

        return data

    # ============================================================
    # PASS 3: Fusion intelligente (known + all)
    # ============================================================

    def extract_complete(
        self,
        text: str,
        debug: bool = False,
        prioritize_known: bool = True,
        strict: bool = True,
        keep_raw_text_field: bool = True,
    ) -> Tuple[Dict[str, float], Dict[str, Dict[str, Any]]]:
        known = self.extract_known_biomarkers(text, debug=debug)
        all_data = self.extract_all_biomarkers(
            text, debug=debug, strict=strict, keep_raw_text_field=keep_raw_text_field
        )

        if prioritize_known and known:
            for canonical_key, value in known.items():
                canon_name = canonical_key.replace("_", " ").title()
                canon_norm = self._normalize_key(canon_name)

                found_key = None
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
                        "line_number": -1,
                        "pattern_used": "targeted_only",
                        "ref_low": None,
                        "ref_high": None,
                        "ref_type": None,
                        "is_known": True,
                        "canonical_key": canonical_key,
                    }
                    if keep_raw_text_field:
                        all_data[canon_norm]["raw_text"] = ""

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
        t = (text or "").lower()
        return any(m in t for m in markers)

    def _extract_synlab_specific(
        self,
        lines: List[str],
        debug: bool = False,
        min_value: float = 0.0001,
        max_value: float = 100000,
        keep_raw_text_field: bool = True,
    ) -> Dict[str, Dict[str, Any]]:
        data: Dict[str, Dict[str, Any]] = {}

        pat = re.compile(
            r"^([A-Za-zÀ-ÿ0-9\s\-\(\)\+\/]+?)\s{2,}"
            r"(\d+[.,]?\d*)\s+"
            r"([a-zA-Zµμ°/%]+(?:/[a-zA-Z0-9]+)?)"
            r"(?:\s*\(([^)]{1,60})\))?\s*$"
        )

        for i, line in enumerate(lines):
            if line.startswith("(") and line.endswith(")"):
                continue

            if not self._is_candidate_biomarker_line(line, strict=True):
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

            ref = self._parse_reference(ref_raw) if ref_raw else None
            key = self._normalize_key(name)

            if key not in data:
                entry: Dict[str, Any] = {
                    "name": name,
                    "value": value,
                    "unit": unit,
                    "line_number": i,
                    "pattern_used": "synlab_clean",
                    "ref_low": None,
                    "ref_high": None,
                    "ref_type": None,
                    "is_known": False,
                    "canonical_key": None,
                }
                if keep_raw_text_field:
                    entry["raw_text"] = line

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
                    print(f"✅ [SYNLAB CLEAN] {name} = {value} {unit} ref=({ref_raw})")

        return data

    # ============================================================
    # Generic STRICT parsing
    # ============================================================

    def _parse_line_generic(self, line: str, strict: bool = True) -> Optional[Dict[str, Any]]:
        """
        STRICT:
          - exige une valeur
          - ET (une unité valide OU une référence valide) si pas biomarqueur connu
          - limite la "queue" textuelle
        """
        # On refuse les lignes où il y a du texte après la valeur qui ressemble à une phrase
        if strict and re.search(r"\d+[.,]?\d*\s+[A-Za-zÀ-ÿ]{4,}\s+[A-Za-zÀ-ÿ]{4,}", line):
            return None

        tab = re.compile(
            r"^([A-Za-zÀ-ÿ0-9\s\-\(\)\+\/]+?)\s*[\.:\s]{2,}\s*"
            r"(\d+[.,]?\d*)\s*"
            r"([a-zA-Zµμ°/%]+(?:/[a-zA-Z0-9]+)?)?\s*"
            r"(?:\(([^)]{1,60})\))?\s*$"
        )
        colon = re.compile(
            r"^([A-Za-zÀ-ÿ0-9\s\-\(\)\+\/]+?)\s*:\s*"
            r"(\d+[.,]?\d*)\s*"
            r"([a-zA-Zµμ°/%]+(?:/[a-zA-Z0-9]+)?)?\s*"
            r"(?:\(([^)]{1,60})\))?\s*$"
        )
        space = re.compile(
            r"^([A-Za-zÀ-ÿ0-9\s\-\(\)\+\/]+?)\s+"
            r"(\d+[.,]?\d*)\s*"
            r"([a-zA-Zµμ°/%]+(?:/[a-zA-Z0-9]+)?)?\s*"
            r"(?:\(([^)]{1,60})\))?\s*$"
        )

        for pat in (tab, colon, space):
            m = pat.match(line)
            if not m:
                continue

            name = self._clean_biomarker_name(m.group(1))
            value_str = m.group(2).replace(",", ".").strip()
            unit = (m.group(3) or "").strip()
            ref_raw = (m.group(4) or "").strip()

            if len(name) < 3 or len(name) > 70:
                return None
            if self._is_header_or_footer(name):
                return None

            try:
                value = float(value_str)
            except ValueError:
                return None

            if not self._is_value_plausible(value):
                return None

            ref = self._parse_reference(ref_raw) if ref_raw else None
            is_known = self._canonical_key_from_name(name) is not None

            if strict and not is_known:
                # en strict, si pas connu -> il faut unit OU ref
                if not self._looks_like_unit(unit) and ref is None:
                    return None

            return {"name": name, "value": value, "unit": unit, "ref": ref}

        return None

    def _parse_reference(self, ref_raw: str) -> Optional[Dict[str, Any]]:
        if not ref_raw:
            return None

        s = ref_raw.strip()
        s = s.replace("−", "-").replace("–", "-")
        s = s.replace("à", "-").replace("a", "-")
        s = s.replace(",", ".")
        s = re.sub(r"\s+", "", s)
        s = re.sub(r"[a-zA-Zµμ/%°]+$", "", s)

        m = re.match(r"^(\d+\.?\d*)-(\d+\.?\d*)$", s)
        if m:
            low = float(m.group(1))
            high = float(m.group(2))
            if low <= high:
                return {"type": "range", "low": low, "high": high}
            return {"type": "range", "low": high, "high": low}

        m = re.match(r"^(>=|>)(\d+\.?\d*)$", s)
        if m:
            return {"type": "lower_bound", "low": float(m.group(2)), "high": None}

        m = re.match(r"^(<=|<)(\d+\.?\d*)$", s)
        if m:
            return {"type": "upper_bound", "low": None, "high": float(m.group(2))}

        return None

    # ============================================================
    # Filtering / Cleaning
    # ============================================================

    def _preclean_lines(self, text: str) -> List[str]:
        lines: List[str] = []
        for raw in (text or "").split("\n"):
            line = raw.strip()
            if not line:
                continue
            line = line.replace("\u00a0", " ").strip()
            line = re.sub(r"\s{2,}", "  ", line)
            lines.append(line)
        return lines

    def _is_candidate_biomarker_line(self, line: str, strict: bool = True) -> bool:
        if len(line) < 5 or len(line) > (120 if strict else 160):
            return False
        if not re.search(r"\d", line):
            return False

        low = line.lower()
        if "http" in low or "www" in low or "@" in low:
            return False

        # rejette gros paragraphes (trop de mots)
        words = re.findall(r"[A-Za-zÀ-ÿ]+", line)
        if len(words) >= (14 if strict else 20):
            return False

        # rejette si stopwords de phrase présents
        if strict:
            for sw in self._SENTENCE_STOPWORDS:
                if sw in low:
                    return False

        # blacklist headers
        if re.search(r"^(page|edition|dossier|adresse|t[eé]l|fax|conclusion|commentaire)\b", low):
            return False

        # ratio lettres/chiffres: si beaucoup de lettres => souvent phrase
        if strict:
            letters = len(re.findall(r"[A-Za-zÀ-ÿ]", line))
            digits = len(re.findall(r"\d", line))
            if letters >= 45 and digits <= 3:
                return False

        # tokens parasites
        for tok in self._BAD_TOKENS:
            if tok in low:
                # si tok présent, on rejette (même si chiffre) car ce sont souvent des sections
                return False

        return True

    def _is_value_plausible(self, value: float) -> bool:
        if value == 0:
            return False
        if 1800 <= value <= 2100:
            return False
        if value != value:  # NaN
            return False
        return True

    def _looks_like_unit(self, unit: str) -> bool:
        if not unit:
            return False
        u = unit.strip().lower().replace("μ", "µ")
        u = u.replace(" ", "")
        u = u.replace("ug", "µg").replace("ul", "µl")
        if u in self._UNIT_HINTS:
            return True
        if "/" in u and len(u) <= 12:
            return True
        if u in {"%", "g", "mg", "µg", "ng", "pg", "l", "ml", "dl", "mmol", "µmol", "nmol", "pmol"}:
            return True
        return False

    def _looks_like_biomarker_name(self, name: str) -> bool:
        n = name.strip()
        if not re.search(r"[A-Za-zÀ-ÿ]", n):
            return False
        words = re.findall(r"[A-Za-zÀ-ÿ0-9]+", n)
        if not (1 <= len(words) <= 7):
            return False
        if re.search(r"\b(avec|sans|pour|chez|vous|nous|afin|selon|dossier|page|commentaire|conclusion)\b", n.lower()):
            return False
        # rejette noms trop "phrase"
        if len(n) > 55 and len(words) >= 6:
            return False
        return True

    def _clean_biomarker_name(self, name: str) -> str:
        name = re.sub(r"[\.]{3,}", "", name)
        name = re.sub(r"\s+", " ", name).strip()
        name = name.strip(".:;,|-_")
        name = re.sub(r"\s*\(\s*\)\s*", "", name)
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
            r"^interpr[ée]tation",
            r"^conclusion",
            r"^m[ée]thode",
        ]
        low = name.lower().strip()
        return any(re.search(p, low) for p in ignore_patterns)

    def _is_known_name_or_key(self, name: str, key: str) -> bool:
        if not self.known_biomarkers:
            return False
        if key in self.known_biomarkers:
            return True
        return self._canonical_key_from_name(name) is not None

    def _canonical_key_from_name(self, extracted_name: str) -> Optional[str]:
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
    # Extraction PDF texte
    # ============================================================

    @staticmethod
    def extract_text_from_pdf(pdf_file) -> str:
        text = ""

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

    def extract_from_pdf_file(
        self,
        pdf_file,
        debug: bool = False,
        return_raw_text: bool = False,          # ✅ NEW: default False
        strict: bool = True,                   # ✅ NEW: default True
        keep_raw_text_field: bool = True,      # ✅ NEW
    ):
        """
        Retour:
          known, all_data, (optionnel) raw_text
        """
        text = self.extract_text_from_pdf(pdf_file)
        known, all_data = self.extract_complete(
            text,
            debug=debug,
            prioritize_known=True,
            strict=strict,
            keep_raw_text_field=keep_raw_text_field,
        )
        if return_raw_text:
            return known, all_data, text
        return known, all_data


__all__ = ["UniversalPDFExtractor"]
