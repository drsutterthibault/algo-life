"""
ALGO-LIFE - Universal Extractor v2.4.0 (ULTRA CLEAN + STRICT RESULT LINES)
✅ Objectif: EXTRAIRE UNIQUEMENT des lignes "résultat biomarqueur" (pas de phrases/paragraphes)
✅ Fix: filtre candidat renforcé + parse strict "valeur en FIN de ligne"
✅ Fix: split des lignes collées multi-colonnes (pdfplumber) si plusieurs refs "(...)"
✅ Option: suppression totale de raw_text dans la sortie (keep_raw_text_field=False)
✅ SYNLAB parser conservé + strictifié
✅ API compatible: extract_from_pdf_file() retourne (known, all_data, text?) selon return_raw_text

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
      2) OPEN CLEAN STRICT: extraction stricte "nom + valeur + unité/ref" (valeur en fin de ligne)
    """

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
    }

    _BAD_TOKENS = {
        "edition", "page", "dossier", "adresse", "telephone", "tél", "fax",
        "laboratoire", "biologie", "biologiste", "validation", "validé",
        "patient", "docteur", "médecin", "prescripteur",
        "commentaire", "interpretation", "interprétation", "conclusion",
        "methode", "méthode", "technique", "instrument", "automate",
        "signature", "service", "site", "centre", "imprimé", "imprime",
        "recommandation", "résumé", "compte rendu", "compte-rendu",
        "analyse", "analyses", "bilan", "examen", "valeur cible",
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

                # label -> valeur (classique)
                pattern_list.append(rf"{name_norm}\s*[:\s]\s*(\d+[.,]?\d*)")

                # label ... valeur unité
                pattern_list.append(rf"{name_norm}\s+(\d+[.,]?\d*)\s*[a-zµμ°/%A-Z]{{0,12}}")

                # valeur -> label (rare)
                pattern_list.append(rf"(\d+[.,]?\d*)\s+{name_norm}")

                # label * + - valeur
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
    # PASS 2: Extraction ouverte CLEAN STRICT
    # ============================================================

    def extract_all_biomarkers(
        self,
        text: str,
        debug: bool = False,
        min_value: float = 0.0001,
        max_value: float = 100000,
        strict: bool = True,
        keep_raw_text_field: bool = False,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Retour:
          Dict[key, {
              name, value, unit,
              ref_low, ref_high, ref_type,
              line_number,
              is_known, canonical_key,
              (optionnel) raw_text si keep_raw_text_field=True
          }]
        """
        data: Dict[str, Dict[str, Any]] = {}

        lines = self._preclean_lines(text)

        # SYNLAB prioritaire
        if self._is_synlab_format(text):
            if debug:
                print("🔍 SYNLAB détecté -> parser Synlab CLEAN STRICT")
            syn = self._extract_synlab_specific(
                lines,
                debug=debug,
                min_value=min_value,
                max_value=max_value,
                strict=strict,
                keep_raw_text_field=keep_raw_text_field,
            )
            data.update(syn)

        # OPEN CLEAN STRICT
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

            # strict: si pas connu, unit/ref déjà exigés au parse, donc ici juste garde-fou
            if strict and not is_known and not (self._looks_like_unit(unit) or ref is not None):
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
                    "pattern_used": "generic_strict_tail",
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
                    print(f"✅ [OPEN STRICT] {name} = {value} {unit} | ref=({rl},{rh})")

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
        keep_raw_text_field: bool = False,
    ) -> Tuple[Dict[str, float], Dict[str, Dict[str, Any]]]:
        known = self.extract_known_biomarkers(text, debug=debug)
        all_data = self.extract_all_biomarkers(
            text,
            debug=debug,
            strict=strict,
            keep_raw_text_field=keep_raw_text_field,
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
    # SYNLAB parser CLEAN STRICT
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
        max_value: float = 100000,
        strict: bool = True,
        keep_raw_text_field: bool = False,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Pattern SYNLAB typique:
          Fer serique   18.0  µmol/l   (12.5−32.2)
          FERRITINE     187.5 ng/ml    (22.0−322.0)
          Folates ...   42.90 nmol/l   (>12.19)
        """
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

            if not self._is_candidate_biomarker_line(line, strict=strict):
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

            # strict: si pas de ref et unité bizarre, on coupe (sauf known)
            is_known = self._canonical_key_from_name(name) is not None
            if strict and not is_known:
                if not self._looks_like_unit(unit) and ref is None:
                    continue

            key = self._normalize_key(name)

            if key not in data:
                entry: Dict[str, Any] = {
                    "name": name,
                    "value": value,
                    "unit": unit,
                    "line_number": i,
                    "pattern_used": "synlab_strict",
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
                    print(f"✅ [SYNLAB STRICT] {name} = {value} {unit} ref=({ref_raw})")

        return data

    # ============================================================
    # Generic STRICT parsing (valeur en fin de ligne)
    # ============================================================

    def _parse_line_generic(self, line: str, strict: bool = True) -> Optional[Dict[str, Any]]:
        """
        Parse STRICT: on garde uniquement les lignes où la FIN ressemble à un résultat labo :
          <NAME> <VALUE> <UNIT?> (<REF?>)
        Et on refuse si du texte traine après la valeur (car valeur forcée en fin de ligne).
        """
        tail_pat = re.compile(
            r"^(?P<name>.+?)\s{1,}"
            r"(?P<value>\d+[.,]?\d*)\s*"
            r"(?P<unit>[a-zA-Zµμ°/%]+(?:/[a-zA-Z0-9]+)?)?\s*"
            r"(?P<ref>\([^)]{1,60}\))?\s*$"
        )

        m = tail_pat.match(line)
        if not m:
            return None

        name = self._clean_biomarker_name(m.group("name"))
        value_str = (m.group("value") or "").replace(",", ".").strip()
        unit = (m.group("unit") or "").strip()
        ref_raw = (m.group("ref") or "").strip()

        if len(name) < 3 or len(name) > 65:
            return None
        if self._is_header_or_footer(name):
            return None

        # phrase-like -> out (sauf connu)
        is_known = self._canonical_key_from_name(name) is not None
        if not self._looks_like_biomarker_name(name) and not is_known:
            return None

        try:
            value = float(value_str)
        except ValueError:
            return None

        if not self._is_value_plausible(value):
            return None

        ref = None
        if ref_raw:
            rr = ref_raw.strip()
            if rr.startswith("(") and rr.endswith(")"):
                rr = rr[1:-1].strip()
            ref = self._parse_reference(rr) if rr else None

        # strict: si pas connu -> exige unité OU ref parsée
        if strict and not is_known:
            if not self._looks_like_unit(unit) and ref is None:
                return None

        return {"name": name, "value": value, "unit": unit, "ref": ref}

    def _parse_reference(self, ref_raw: str) -> Optional[Dict[str, Any]]:
        if not ref_raw:
            return None

        s = ref_raw.strip()
        s = s.replace("−", "-").replace("–", "-")
        s = s.replace("à", "-").replace("A", "-")
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
        for raw in text.split("\n"):
            line = raw.strip()
            if not line:
                continue

            line = line.replace("\u00a0", " ").strip()
            line = re.sub(r"\s{2,}", "  ", line)

            # ✅ split lignes collées multi-colonnes si plusieurs refs
            # ex: "... (0-3)   ... (12-30)"
            if line.count("(") >= 2 and len(line) > 120:
                parts = re.split(r"(?<=\))\s{2,}", line)
                for p in parts:
                    p = p.strip()
                    if p:
                        lines.append(re.sub(r"\s{2,}", "  ", p))
                continue

            lines.append(line)

        return lines

    def _is_candidate_biomarker_line(self, line: str, strict: bool = True) -> bool:
        """
        Filtre ultra fort:
          - longueur contrôlée
          - contient chiffre
          - rejette tokens parasites (même si chiffre)
          - impose une FIN qui ressemble à: <value> <unit?> (<ref?>)
        """
        if not line:
            return False

        if len(line) < 6 or len(line) > (110 if strict else 140):
            return False

        low = line.lower()

        if "http" in low or "www" in low or "@" in low:
            return False

        # rejette stop-tokens (même si valeurs)
        for tok in self._BAD_TOKENS:
            if tok in low:
                return False

        if not re.search(r"\d", line):
            return False

        # phrase-like: trop de mots alpha
        words = re.findall(r"[A-Za-zÀ-ÿ]{2,}", line)
        if len(words) >= (12 if strict else 18):
            return False

        # impose une structure "result tail" à la fin de ligne
        # valeur + (unité?) + (ref?) EN FIN
        if not re.search(
            r"(\d+[.,]?\d*)\s*([a-zA-Zµμ°/%]+(?:/[a-zA-Z0-9]+)?)?\s*(\([^)]{1,60}\))?\s*$",
            line
        ):
            return False

        # rejette headers simples
        if re.search(r"^(page|edition|dossier|adresse|t[eé]l|fax)\b", low):
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
        if not (1 <= len(words) <= 8):
            return False
        if re.search(r"\b(avec|sans|pour|chez|vous|nous|afin|selon|dossier|page)\b", n.lower()):
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
    # Extraction PDF complète
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
        prioritize_known: bool = True,
        strict: bool = True,
        keep_raw_text_field: bool = False,
        return_raw_text: bool = False,
    ) -> Tuple[Dict[str, float], Dict[str, Dict[str, Any]], str]:
        """
        Retourne:
          known (Dict[canonical_key, float]),
          all_data (dict struct),
          text (str) -> vide si return_raw_text=False
        """
        text = self.extract_text_from_pdf(pdf_file)
        known, all_data = self.extract_complete(
            text,
            debug=debug,
            prioritize_known=prioritize_known,
            strict=strict,
            keep_raw_text_field=keep_raw_text_field,
        )

        # optionnel: ne pas renvoyer le texte brut à l'app
        if not return_raw_text:
            return known, all_data, ""

        return known, all_data, text


__all__ = ["UniversalPDFExtractor"]
