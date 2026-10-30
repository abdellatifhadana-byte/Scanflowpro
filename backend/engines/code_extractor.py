"""
ScanFlow Pro V7 - DAM Code Extractor (ONE AND ONLY VERSION)
Enterprise-Grade Code Extraction for Document Administratif Marocain
"""

import re
import logging
from typing import List, Dict, Optional
import sys
import os

logger = logging.getLogger(__name__)

class CodeExtractor:
    """Moteur d'extraction de codes DAM (Document Administratif Marocain) - Enterprise Edition"""
    
    def __init__(self, min_digits: int = 4, max_digits: int = 8, dam_strict: bool = True):
        """
        Initialiser l'extracteur DAM
        
        Args:
            min_digits: Longueur minimale du code
            max_digits: Longueur maximale du code
            dam_strict: Mode strict DAM (rejette l'extraction générique)
        """
        self.min_digits = min_digits
        self.max_digits = max_digits
        self.dam_strict = dam_strict
        self.mode = "DAM"
        
        # 🔥 ANCHORS ADMINISTRATIFS MAROCAINS
        self.dam_anchors_ar = [
            "القطعة رقم",
            "رقم القطعة", 
            "القطعة المتعلقة بالرقم",
            "رقم المتعلقة",
            "رقم",
            "الرقم",
            "كود",
            "معرف",
            "الرمز"
        ]
        
        self.dam_anchors_fr = [
            "N°",
            "Parcelle N°",
            "Parcelle",
            "Code Parcelle", 
            "Numéro",
            "Code",
            "ID"
        ]
        
        self.dam_anchors = self.dam_anchors_ar + self.dam_anchors_fr
        
        # Regex pour numbers de longueur variable
        self.num_pattern = rf"\b\d{{{self.min_digits},{self.max_digits}}}\b"
        
        # 🔥 PATTERNS DAM COMPLETS
        self.dam_patterns = [
            # Arabe
            r'(?:القطعة\s*رقم|رقم\s*القطعة|القطعة\s*المتعلقة)[\s:.-]*(\d{4,8})',
            r'(?:رقم|كود|معرف|الرمز)[\s:.-]*(\d{4,8})',
            
            # Français
            r'(?:N[°\s]|Parcelle\s*N[°\s]|Code\s*Parcelle)[\s:.-]*(\d{4,8})',
            r'(?:Numéro|Code|ID)[\s:.-]*(\d{4,8})',
            
            # Générique
            r'(?:القطعة\s*رقم|رقم\s*القطعة|N[°\s]|Parcelle)[^0-9]{0,10}(\d{4,8})',
            r'(?:\.{3,}\s*)?(?:N[°\s]|رقم)[\s:.-]*(\d{4,8})',
        ]
        
        # Patterns à éviter
        self.suspicious_patterns = [
            r'^0{4,}$',      # 0000...
            r'^1{4,}$',      # 1111...
            r'^9{4,}$',      # 9999...
            r'^12345',       # 123456
            r'^54321',       # 543210
            # ❌ REMOVED: r'^\d{4}$' (تضارب مع min_digits)
            # ❌ REMOVED: r'^\d{8,}$' (تضارب مع max_digits)
        ]
        
        logger.info(f"[DAM-EXTRACTOR] Initialisé (min={min_digits}, max={max_digits}, strict={dam_strict})")
    
    async def extract_code_with_keyword(
        self, 
        ocr_results: List[Dict], 
        keyword: Optional[str] = None,
        roi_area: Optional[Dict] = None,
        htr_results: Optional[List[Dict]] = None
    ) -> Dict:
        """Extraire le code - STRATÉGIE DAM AVANCÉE"""
        try:
            # 1. Fusionner tous les résultats
            all_results = []
            if ocr_results:
                all_results.extend(ocr_results)
            if htr_results:
                all_results.extend(htr_results)
            
            if not all_results:
                logger.warning("[DAM] Aucun résultat OCR/HTR")
                return self._create_result(None, 0, 'no_text')
            
            # 2. FILTRAGE ROI
            filtered_results = self._filter_results_by_roi(all_results, roi_area)
            logger.info(f"[ROI-FILTER] Résultats: {len(all_results)} → {len(filtered_results)}")
            
            if not filtered_results and roi_area:
                logger.warning("[ROI-FILTER] Aucun résultat dans ROI, utilisation totale")
                filtered_results = all_results
            
            # 3. Extraire les métadonnées
            texts_with_meta = [
                {
                    'text': r.get('text', '').strip(), 
                    'confidence': r.get('confidence', 0.5),
                    'bbox': r.get('bbox'),
                    'index': i
                }
                for i, r in enumerate(filtered_results)
            ]
            
            logger.info(f"[DAM] {len(texts_with_meta)} textes pour analyse")
            
            # 4. STRATÉGIE DAM DIRECTE
            dam_result = self._dam_extract_direct(texts_with_meta, keyword)
            if dam_result:
                logger.info(f"[DAM] ✓ Code DAM trouvé: {dam_result['code']}")
                return dam_result
            
            # 5. STRATÉGIE KEYWORD
            if keyword:
                keyword_result = self._extract_with_keyword_enhanced(texts_with_meta, keyword)
                if keyword_result:
                    logger.info(f"[DAM] ✓ Code via keyword: {keyword_result['code']}")
                    return keyword_result
            
            # 6. STRATÉGIE GÉNÉRIQUE (seulement si dam_strict=False)
            if not self.dam_strict:
                generic_result = self._extract_generic_safe(texts_with_meta)
                if generic_result:
                    logger.info(f"[DAM] ✓ Code générique: {generic_result['code']}")
                    return generic_result
            else:
                logger.info("[DAM] Extraction générique désactivée (mode strict)")
            
            logger.warning("[DAM] ❌ Aucun code trouvé")
            return self._create_result(None, 0, 'failed')
            
        except Exception as e:
            logger.error(f"[DAM] Erreur extraction: {e}")
            return self._create_result(None, 0, 'error', error=str(e))
    
    def _create_result(self, code: Optional[str], confidence: float, method: str, **kwargs) -> Dict:
        """Créer un résultat standardisé"""
        result = {
            'code': code,
            'confidence': confidence,
            'method': method,
            'mode': self.mode,
            'strict': self.dam_strict
        }
        
        if method.startswith('dam_'):
            result['context'] = {'dam_pattern': True}
        
        result.update(kwargs)
        return result
    
    def _filter_results_by_roi(self, results: List[Dict], roi: Optional[Dict]) -> List[Dict]:
        """Filtrer les résultats par ROI"""
        if not roi:
            return results
        
        filtered = []
        for r in results:
            bbox = r.get('bbox')
            if not bbox:
                filtered.append(r)
                continue
            
            if self._bbox_in_roi(bbox, roi):
                filtered.append(r)
        
        return filtered
    
    def _bbox_in_roi(self, bbox: tuple, roi: Dict) -> bool:
        """Vérifier si un bbox est dans la ROI"""
        try:
            if len(bbox) < 4:
                return False
            
            bbox_x, bbox_y, bbox_w, bbox_h = bbox
            bbox_center_x = bbox_x + (bbox_w / 2)
            bbox_center_y = bbox_y + (bbox_h / 2)
            
            roi_x1 = roi.get('x', 0)
            roi_y1 = roi.get('y', 0)
            roi_x2 = roi_x1 + roi.get('width', 0)
            roi_y2 = roi_y1 + roi.get('height', 0)
            
            margin = 5
            return (roi_x1 - margin <= bbox_center_x <= roi_x2 + margin and 
                    roi_y1 - margin <= bbox_center_y <= roi_y2 + margin)
        except Exception as e:
            logger.error(f"[ROI] Erreur vérification bbox: {e}")
            return False
    
    def _dam_extract_direct(self, texts_with_meta: List[Dict], keyword: Optional[str]) -> Optional[Dict]:
        """Extraction DAM directe - WINDOW SYSTEM"""
        try:
            WINDOW_SIZE = 3
            texts = [t['text'] for t in texts_with_meta]
            
            # STRATÉGIE A: PATTERNS DAM COMPLETS
            for i in range(len(texts)):
                end_idx = min(i + WINDOW_SIZE, len(texts))
                window_texts = texts[i:end_idx]
                
                if not window_texts:
                    continue
                
                window_combined = " ".join(window_texts)
                
                for pattern in self.dam_patterns:
                    matches = re.findall(pattern, window_combined, re.IGNORECASE)
                    if matches:
                        code = matches[0]
                        cleaned = self._clean_code(code)
                        
                        if cleaned:
                            confidences = [t['confidence'] for t in texts_with_meta[i:end_idx]]
                            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.7
                            dam_confidence = min(0.95, avg_confidence * 1.3)
                            
                            return self._create_result(
                                code=cleaned,
                                confidence=dam_confidence,
                                method='dam_pattern',
                                pattern=pattern,
                                window_text=window_combined[:50]
                            )
            
            # STRATÉGIE B: ANCHOR + NUMBER PROXIMITY
            for i, meta in enumerate(texts_with_meta):
                text = meta['text']
                confidence = meta['confidence']
                
                found_anchor = None
                for anchor in self.dam_anchors:
                    if anchor.lower() in text.lower():
                        found_anchor = anchor
                        break
                
                if not found_anchor:
                    continue
                
                # Chercher dans la même ligne
                same_line_matches = re.findall(self.num_pattern, text)
                if same_line_matches:
                    for match in same_line_matches:
                        cleaned = self._clean_code(match)
                        if cleaned:
                            return self._create_result(
                                code=cleaned,
                                confidence=min(0.95, confidence * 1.4),
                                method='dam_sameline',
                                anchor=found_anchor
                            )
                
                # Chercher dans la fenêtre suivante
                for j in range(i+1, min(i+4, len(texts_with_meta))):
                    next_text = texts_with_meta[j]['text']
                    next_matches = re.findall(self.num_pattern, next_text)
                    
                    if next_matches:
                        for match in next_matches:
                            cleaned = self._clean_code(match)
                            if cleaned:
                                distance = j - i
                                distance_penalty = max(0.7, 1.0 - (distance * 0.1))
                                
                                return self._create_result(
                                    code=cleaned,
                                    confidence=min(0.90, confidence * 1.2 * distance_penalty),
                                    method=f'dam_window_d{distance}',
                                    anchor=found_anchor,
                                    distance=distance
                                )
            
            return None
            
        except Exception as e:
            logger.error(f"[DAM-DIRECT] Erreur: {e}")
            return None
    
    def _extract_with_keyword_enhanced(self, texts_with_meta: List[Dict], keyword: str) -> Optional[Dict]:
        """Extraction avec mot-clé améliorée"""
        try:
            keyword_lower = keyword.lower()
            keyword_indices = []
            
            for i, meta in enumerate(texts_with_meta):
                text = meta['text'].lower()
                if keyword_lower in text:
                    keyword_indices.append(i)
            
            if not keyword_indices:
                return None
            
            all_candidates = []
            for idx in keyword_indices:
                confidence = texts_with_meta[idx]['confidence']
                start = max(0, idx - 2)
                end = min(len(texts_with_meta), idx + 3)
                
                for j in range(start, end):
                    text = texts_with_meta[j]['text']
                    matches = re.findall(self.num_pattern, text)
                    
                    for match in matches:
                        distance = abs(j - idx)
                        distance_factor = max(0.5, 1.0 - (distance * 0.2))
                        
                        cleaned = self._clean_code(match)
                        if cleaned:
                            all_candidates.append({
                                'code': cleaned,
                                'confidence': min(0.95, confidence * distance_factor),
                                'distance': distance
                            })
            
            if not all_candidates:
                return None
            
            all_candidates.sort(key=lambda x: (x['distance'], -x['confidence']))
            best = all_candidates[0]
            
            return self._create_result(
                code=best['code'],
                confidence=best['confidence'],
                method=f'keyword_distance_{best["distance"]}',
                keyword=keyword
            )
            
        except Exception as e:
            logger.error(f"[KEYWORD] Erreur: {e}")
            return None
    
    def _extract_generic_safe(self, texts_with_meta: List[Dict]) -> Optional[Dict]:
        """Extraction générique avec sécurité"""
        try:
            all_numbers = []
            number_metadata = []
            
            for meta in texts_with_meta:
                text = meta['text']
                confidence = meta['confidence']
                
                matches = re.findall(self.num_pattern, text)
                for match in matches:
                    all_numbers.append(match)
                    number_metadata.append({
                        'match': match,
                        'confidence': confidence
                    })
            
            if not all_numbers:
                return None
            
            valid_codes = []
            for i, num in enumerate(all_numbers):
                cleaned = self._clean_code(num)
                if cleaned and self._looks_like_admin_code(cleaned):
                    valid_codes.append({
                        'code': cleaned,
                        'confidence': number_metadata[i]['confidence']
                    })
            
            if not valid_codes:
                return None
            
            code_groups = {}
            for vc in valid_codes:
                code = vc['code']
                if code not in code_groups:
                    code_groups[code] = []
                code_groups[code].append(vc)
            
            scored_codes = {}
            for code, group in code_groups.items():
                avg_conf = sum(g['confidence'] for g in group) / len(group)
                repetition_bonus = min(0.2, len(group) * 0.05)
                admin_bonus = 0.1 if self._looks_like_admin_code(code) else 0
                total_score = min(0.75, avg_conf + repetition_bonus + admin_bonus)
                scored_codes[code] = total_score
            
            if not scored_codes:
                return None
            
            best_code = max(scored_codes.items(), key=lambda x: x[1])[0]
            best_score = scored_codes[best_code]
            
            if best_score < 0.6:
                return None
            
            return self._create_result(
                code=best_code,
                confidence=best_score,
                method='generic_safe'
            )
            
        except Exception as e:
            logger.error(f"[GENERIC] Erreur: {e}")
            return None
    
    def _clean_code(self, code: str) -> Optional[str]:
        """Nettoyer et valider le code"""
        try:
            cleaned = re.sub(r'[^\d]', '', code)
            
            if not (self.min_digits <= len(cleaned) <= self.max_digits):
                return None
            
            if self._is_suspicious_pattern(cleaned):
                return None
            
            return cleaned
            
        except Exception as e:
            logger.error(f"[CLEAN] Erreur: {e}")
            return None
    
    def _looks_like_admin_code(self, code: str) -> bool:
        """Vérifier si le code ressemble à un code administratif"""
        if len(code) < 5 or len(code) > 7:
            return False
        
        if code.startswith('0'):
            return False
        
        if code == code[0] * len(code):
            return False
        
        digits = [int(d) for d in code]
        
        if all(digits[i] == digits[0] + i for i in range(len(digits))):
            return False
        
        if all(digits[i] == digits[0] - i for i in range(len(digits))):
            return False
        
        if len(code) % 2 == 0:
            half = len(code) // 2
            if code[:half] == code[half:]:
                return False
        
        return True
    
    def _is_suspicious_pattern(self, code: str) -> bool:
        """Détecter les patterns suspects"""
        for pattern in self.suspicious_patterns:
            if re.match(pattern, code):
                return True
        
        if len(code) >= 6:
            if code[0:2] * (len(code) // 2) == code[:len(code) - (len(code) % 2)]:
                return True
            
            if len(code) % 3 == 0:
                part_len = len(code) // 3
                if code[0:part_len] * 3 == code:
                    return True
        
        return False
    
    def get_config(self) -> Dict:
        """Obtenir la configuration actuelle"""
        return {
            'mode': self.mode,
            'min_digits': self.min_digits,
            'max_digits': self.max_digits,
            'dam_strict': self.dam_strict
        }