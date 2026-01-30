"""
ALGO-LIFE PDF Generator - Universal Extractor v2.1 (SYNLAB PATCH)
✅ Extraction universelle (tous biomarqueurs)
✅ Patch spécifique format SYNLAB

Author: Dr Thibault SUTTER
Date: January 2026
"""

import re
from typing import Dict, List, Tuple, Optional

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
    Extracteur PDF universel avec 2 modes:
    1. TARGETED: biomarqueurs connus avec ranges/interprétation
    2. OPEN: extraction générique de TOUTES les paires nom-valeur
    
    ✅ PATCH SYNLAB: Gère le format spécifique des PDFs Synlab
    """
    
    def __init__(self, known_biomarkers: Optional[Dict] = None):
        """
        Args:
            known_biomarkers: Dict des biomarqueurs connus (optionnel)
                Format: {'crp': {'unit': 'mg/L', 'lab_names': [...], ...}}
        """
        self.known_biomarkers = known_biomarkers or {}
    
    # ============================================================
    # PASS 1: Extraction Ciblée (biomarqueurs connus)
    # ============================================================
    
    def extract_known_biomarkers(self, text: str, debug: bool = False) -> Dict[str, float]:
        """
        Extrait les biomarqueurs CONNUS avec patterns spécifiques
        """
        if not self.known_biomarkers:
            return {}
        
        data = {}
        text_lower = text.lower()
        
        patterns_cache = self._build_targeted_patterns()
        
        for biomarker_key, pattern_list in patterns_cache.items():
            for pattern in pattern_list:
                try:
                    matches = re.finditer(pattern, text_lower, re.IGNORECASE | re.MULTILINE)
                    
                    for match in matches:
                        try:
                            value_str = match.group(1).replace(',', '.').strip()
                            value = float(value_str)
                            
                            # Sanity check
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
        """Construit patterns pour biomarqueurs connus"""
        patterns = {}
        
        for biomarker_key, ref_data in self.known_biomarkers.items():
            lab_names = ref_data.get('lab_names', [biomarker_key])
            pattern_list = []
            
            for name in lab_names:
                name_normalized = name.lower().replace('é', '[eé]').replace('è', '[eè]')
                
                # Pattern 1: Valeur AVANT label (LIMS)
                pattern_list.append(rf'(\d+[.,]?\d*)\s+{name_normalized}')
                
                # Pattern 2: Label AVANT valeur
                pattern_list.append(rf'{name_normalized}[:\s]+(\d+[.,]?\d*)')
                
                # Pattern 3: Avec unités
                pattern_list.append(rf'{name_normalized}\s+(\d+[.,]?\d*)\s*[a-zµμ°/%]*')
                
                # Pattern 4: Symboles (*, +, -)
                pattern_list.append(rf'{name_normalized}\s*[*+\-]*\s*(\d+[.,]?\d*)')
            
            patterns[biomarker_key] = pattern_list
        
        return patterns
    
    # ============================================================
    # PASS 2: Extraction Ouverte (TOUS les paramètres)
    # ============================================================
    
    def extract_all_biomarkers(
        self, 
        text: str, 
        debug: bool = False,
        min_value: float = 0.001,
        max_value: float = 100000
    ) -> Dict[str, Dict]:
        """
        Extrait TOUS les biomarqueurs trouvés dans le PDF
        
        Returns:
            Dict[biomarker_name, {'value': float, 'unit': str, 'raw_text': str}]
        """
        data = {}
        
        # ✅ PATCH SYNLAB: Prétraitement spécifique
        if self._is_synlab_format(text):
            if debug:
                print("🔍 Format SYNLAB détecté - Utilisation du parser spécifique")
            synlab_data = self._extract_synlab_specific(text, debug=debug)
            data.update(synlab_data)
        
        # Patterns génériques pour détecter lignes avec valeurs numériques
        generic_patterns = [
            # Pattern 1: "Nom du test ........ 15.2 mg/L" (format tabulé)
            r'^([A-Za-zÀ-ÿ\s\-\(\)]+?)\s*[\.:\s]{2,}\s*(\d+[.,]?\d*)\s*([a-zµμ°/%A-Z]*)',
            
            # Pattern 2: "Nom du test: 15.2" ou "Nom du test 15.2"
            r'([A-Za-zÀ-ÿ\s\-\(\)]+?)[:\s]+(\d+[.,]?\d*)\s*([a-zµμ°/%A-Z]*)',
            
            # Pattern 3: "15.2 Nom du test" (valeur avant)
            r'(\d+[.,]?\d*)\s+([A-Za-zÀ-ÿ\s\-\(\)]+?)\s*([a-zµμ°/%A-Z]*)',
            
            # Pattern 4: Format tableau "| Nom | 15.2 | mg/L |"
            r'\|\s*([A-Za-zÀ-ÿ\s\-\(\)]+?)\s*\|\s*(\d+[.,]?\d*)\s*\|\s*([a-zµμ°/%A-Z]*)',
        ]
        
        lines = text.split('\n')
        
        for line_num, line in enumerate(lines):
            line_clean = line.strip()
            if not line_clean or len(line_clean) < 5:
                continue
            
            for pattern_idx, pattern in enumerate(generic_patterns):
                matches = re.finditer(pattern, line_clean, re.IGNORECASE)
                
                for match in matches:
                    try:
                        # Identifier nom et valeur selon le pattern
                        if pattern_idx == 2:  # Valeur avant nom
                            value_str = match.group(1).replace(',', '.').strip()
                            name = match.group(2).strip()
                            unit = match.group(3).strip() if len(match.groups()) >= 3 else ''
                        else:
                            name = match.group(1).strip()
                            value_str = match.group(2).replace(',', '.').strip()
                            unit = match.group(3).strip() if len(match.groups()) >= 3 else ''
                        
                        # Nettoyer le nom
                        name = self._clean_biomarker_name(name)
                        
                        # Valider
                        if len(name) < 3 or len(name) > 80:
                            continue
                        
                        # Skip headers/footers communs
                        if self._is_header_or_footer(name):
                            continue
                        
                        # Convertir valeur
                        try:
                            value = float(value_str)
                        except ValueError:
                            continue
                        
                        # Sanity check
                        if not (min_value <= value <= max_value):
                            continue
                        
                        # Normaliser nom pour clé
                        key = self._normalize_key(name)
                        
                        # Éviter doublons (garder première occurrence)
                        if key not in data:
                            data[key] = {
                                'name': name,
                                'value': value,
                                'unit': unit,
                                'raw_text': line_clean,
                                'line_number': line_num,
                                'pattern_used': pattern_idx
                            }
                            
                            if debug:
                                print(f"✅ [OPEN] {name} = {value} {unit} (line {line_num})")
                    
                    except Exception as e:
                        if debug:
                            print(f"⚠️ Error parsing line {line_num}: {e}")
                        continue
        
        return data
    
    # ============================================================
    # ✅ PATCH SYNLAB: Extraction spécifique
    # ============================================================
    
    def _is_synlab_format(self, text: str) -> bool:
        """Détecte si le PDF est au format Synlab"""
        synlab_markers = [
            'synlab',
            'laboratoire de biologie médicale',
            'biologistes médicaux coresponsables',
            'dossier validé biologiquement'
        ]
        text_lower = text.lower()
        return any(marker in text_lower for marker in synlab_markers)
    
    def _extract_synlab_specific(self, text: str, debug: bool = False) -> Dict[str, Dict]:
        """
        Extracteur spécifique pour format Synlab
        
        Format typique:
        Fer serique                    18.0  µmol/l      (12.5−32.2)
        (Colorimétrie TPTZ )           101   µg/100ml    (70−180)
        
        Transferrine                   1.88  g/l         (2.00−3.60)
        (Immunoturbidimétrie Siemens)
        """
        data = {}
        lines = text.split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Skip lignes vides, headers, footers
            if (not line or 
                len(line) < 5 or
                line.startswith('Edition') or
                line.startswith('Page') or
                line.startswith('Dossier') or
                'biologiquement' in line.lower()):
                i += 1
                continue
            
            # Skip lignes méthode (entre parenthèses au début)
            if line.startswith('(') and line.endswith(')'):
                i += 1
                continue
            
            # Pattern Synlab: Nom + espaces + valeur + unité + (range)
            # Ex: "Fer serique                    18.0  µmol/l      (12.5−32.2)"
            synlab_pattern = r'^([A-Za-zÀ-ÿ\s\-]+?)\s{2,}(\d+[.,]?\d*)\s+([a-zµμ°/%A-Z]+(?:/[a-zA-Z0-9]+)?)\s*(?:\(.*?\))?'
            
            match = re.match(synlab_pattern, line, re.IGNORECASE)
            
            if match:
                name = match.group(1).strip()
                value_str = match.group(2).replace(',', '.').strip()
                unit = match.group(3).strip()
                
                # Nettoyer le nom
                name = self._clean_biomarker_name(name)
                
                # Valider nom
                if len(name) < 3 or len(name) > 80:
                    i += 1
                    continue
                
                # Skip headers
                if self._is_header_or_footer(name):
                    i += 1
                    continue
                
                try:
                    value = float(value_str)
                    
                    # Sanity check
                    if 0.001 <= value <= 100000:
                        key = self._normalize_key(name)
                        
                        if key not in data:
                            data[key] = {
                                'name': name,
                                'value': value,
                                'unit': unit,
                                'raw_text': line,
                                'line_number': i,
                                'pattern_used': 'synlab_specific'
                            }
                            
                            if debug:
                                print(f"✅ [SYNLAB] {name} = {value} {unit}")
                except ValueError:
                    pass
            
            i += 1
        
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
        """
        Extraction complète en 2 passes + fusion
        
        Returns:
            (known_biomarkers, all_biomarkers)
        """
        # Pass 1: Biomarqueurs connus
        known = self.extract_known_biomarkers(text, debug=debug)
        
        # Pass 2: Extraction ouverte
        all_data = self.extract_all_biomarkers(text, debug=debug)
        
        # Fusion: enrichir all_data avec info des connus
        if prioritize_known:
            for key, value in known.items():
                # Trouver correspondance dans all_data
                norm_key = self._normalize_key(key)
                if norm_key in all_data:
                    all_data[norm_key]['is_known'] = True
                    all_data[norm_key]['canonical_key'] = key
                else:
                    # Ajouter si manquant
                    all_data[norm_key] = {
                        'name': key.replace('_', ' ').title(),
                        'value': value,
                        'unit': self.known_biomarkers.get(key, {}).get('unit', ''),
                        'is_known': True,
                        'canonical_key': key
                    }
        
        return known, all_data
    
    # ============================================================
    # Helpers
    # ============================================================
    
    def _clean_biomarker_name(self, name: str) -> str:
        """Nettoie un nom de biomarqueur"""
        # Supprimer caractères spéciaux excessifs
        name = re.sub(r'[\.]{3,}', '', name)  # Points multiples
        name = re.sub(r'\s+', ' ', name)      # Espaces multiples
        name = name.strip('.:;,|-_')
        return name
    
    def _normalize_key(self, name: str) -> str:
        """Normalise un nom en clé unique"""
        key = name.lower()
        key = re.sub(r'[àâä]', 'a', key)
        key = re.sub(r'[éèêë]', 'e', key)
        key = re.sub(r'[îï]', 'i', key)
        key = re.sub(r'[ôö]', 'o', key)
        key = re.sub(r'[ùûü]', 'u', key)
        key = re.sub(r'[ç]', 'c', key)
        key = re.sub(r'[^a-z0-9]+', '_', key)
        key = re.sub(r'_+', '_', key)
        key = key.strip('_')
        return key
    
    def _is_header_or_footer(self, name: str) -> bool:
        """Détecte si c'est un header/footer à ignorer"""
        ignore_patterns = [
            r'^page\s+\d+',
            r'^date',
            r'^laboratoire',
            r'^patient',
            r'^docteur',
            r'^pr[ée]lev',
            r'^r[ée]f[ée]rence',
            r'^valeur',
            r'^r[ée]sultat',
            r'^unit[ée]',
            r'^total',
            r'^biochimie',
            r'^proteines',
            r'^marqueurs',
            r'^vitamines',
            r'^sang',
            r'^renseignements',
            r'^commentaire',
            r'^interpretation',
        ]
        
        name_lower = name.lower()
        for pattern in ignore_patterns:
            if re.search(pattern, name_lower):
                return True
        return False
    
    # ============================================================
    # Extraction PDF complète
    # ============================================================
    
    @staticmethod
    def extract_text_from_pdf(pdf_file) -> str:
        """Extrait texte d'un PDF avec fallback"""
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
            raise ImportError("PDF libraries not available. Install pdfplumber or PyPDF2.")
        
        return text
    
    def extract_from_pdf_file(
        self, 
        pdf_file, 
        debug: bool = False
    ) -> Tuple[Dict[str, float], Dict[str, Dict], str]:
        """
        Extraction complète depuis un fichier PDF
        
        Returns:
            (known_biomarkers, all_biomarkers, raw_text)
        """
        text = self.extract_text_from_pdf(pdf_file)
        known, all_data = self.extract_complete(text, debug=debug)
        return known, all_data, text


# ============================================================
# Exemple d'utilisation
# ============================================================

if __name__ == "__main__":
    # Biomarqueurs connus (subset pour démo)
    known_db = {
        'crp': {
            'unit': 'mg/L',
            'lab_names': ['crp', 'crp ultrasensible', 'hs-crp', 'crp-us']
        },
        'vit_d': {
            'unit': 'ng/mL',
            'lab_names': ['vitamine d', '25-oh d', 'vitamin d', '25-oh-vitamine d']
        },
        'ferritine': {
            'unit': 'ng/ml',
            'lab_names': ['ferritine']
        },
        'folates': {
            'unit': 'nmol/l',
            'lab_names': ['folates', 'folates sériques', 'vitamine b9']
        }
    }
    
    # Test avec un PDF fictif
    extractor = UniversalPDFExtractor(known_biomarkers=known_db)
    
    # Simuler du texte de PDF Synlab
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
    """
    
    known, all_biomarkers = extractor.extract_complete(sample_text, debug=True)
    
    print("\n" + "="*60)
    print(f"✅ CONNUS extraits: {len(known)}")
    print(known)
    
    print("\n" + "="*60)
    print(f"✅ TOTAL extraits: {len(all_biomarkers)}")
    for key, data in all_biomarkers.items():
        marker = "⭐" if data.get('is_known') else "🆕"
        print(f"  {marker} {data['name']}: {data['value']} {data['unit']}")
