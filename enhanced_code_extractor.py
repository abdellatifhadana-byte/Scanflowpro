"""
ScanFlow Pro V7 - Enhanced Code Extractor - DAM EDITION (FIXED)
Enterprise-Grade Code Extraction for Document Administratif Marocain
"""

import logging
from typing import List, Dict, Optional
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from .code_extractor import CodeExtractor
    from .code_validator import CodeValidator, ValidationLevel
    from .text_region_detector import TextRegionDetector
    from .yolo_text_detector import get_yolo_text_detector
except ImportError:
    from code_extractor import CodeExtractor
    from code_validator import CodeValidator, ValidationLevel
    from text_region_detector import TextRegionDetector
    from yolo_text_detector import get_yolo_text_detector

logger = logging.getLogger(__name__)

# ================================
# 🔥 استخدم نفس CONFIG من processing_orchestrator
# ================================
try:
    from .processing_orchestrator import DAM_CONFIG
except ImportError:
    # القيم الافتراضية إذا لم يتم العثور على CONFIG
    DAM_CONFIG = {
        "MIN_DIGITS": 4,
        "MAX_DIGITS": 8,
        "STRICT_MODE": True,
        "DAM_PATTERNS_ONLY": True
    }

def roi_to_tuple(roi: Optional[Dict]) -> Optional[tuple]:
    if not roi:
        return None
    try:
        x = int(roi.get("x", 0))
        y = int(roi.get("y", 0))
        w = int(roi.get("width", 0))
        h = int(roi.get("height", 0))
        if w <= 0 or h <= 0:
            return None
        return (x, y, x + w, y + h)
    except Exception:
        return None


class EnhancedCodeExtractor:
    """
    OCR + HTR + Keyword + YOLO + Validation + DAM PATTERNS
    Version simplifiée et optimisée pour DAM
    """
    
    def __init__(self, min_digits=None, max_digits=None, strict_mode=None):
        # 🔥 استخدم CONFIG موحد إذا لم يتم توفير قيم
        min_digits = min_digits or DAM_CONFIG["MIN_DIGITS"]
        max_digits = max_digits or DAM_CONFIG["MAX_DIGITS"]
        strict_mode = strict_mode if strict_mode is not None else DAM_CONFIG["STRICT_MODE"]
        
        # 🔥 Utiliser le CodeExtractor DAM READY بنفس القيم
        self.base_extractor = CodeExtractor(
            min_digits=min_digits,
            max_digits=max_digits,
            dam_strict=strict_mode
        )
        
        # 🔧 Validateur pour DAM بنفس القيم
        self.validator = CodeValidator(
            min_digits=min_digits,
            max_digits=max_digits,
            strict_mode=strict_mode
        )

        # Détecteurs régionaux (optionnels)
        self.region_detector = TextRegionDetector(
            min_area=500,
            max_area=100000,
            aspect_ratio_range=(0.3, 20.0),
        )

        # YOLO (optionnel)
        try:
            self.yolo_detector = get_yolo_text_detector()
            logger.info("✓ YOLO detector ready")
        except Exception as e:
            logger.warning(f"YOLO unavailable: {e}")
            self.yolo_detector = None

        self.min_digits = min_digits
        self.max_digits = max_digits
        self.strict_mode = strict_mode
        
        logger.info(f"✅ EnhancedCodeExtractor DAM Edition initialisé (min={min_digits}, max={max_digits}, strict={strict_mode})")

    async def extract_code_with_keyword(
        self,
        ocr_results: List[Dict],
        keyword: Optional[str] = None,
        roi_area: Optional[Dict] = None,
        htr_results: Optional[List[Dict]] = None,
        original_image=None,
    ) -> Dict:
        """
        Extraction DAM simplifiée - Pas de voting complexe
        """
        try:
            logger.info(f"[DAM-SIMPLE] Début extraction avec {len(ocr_results)} résultats OCR")
            
            # 🎯 ÉTAPE 1: EXTRACTION DAM DE BASE
            base_result = await self.base_extractor.extract_code_with_keyword(
                ocr_results=ocr_results,
                keyword=keyword,
                roi_area=roi_area,
                htr_results=htr_results,
            )
            
            logger.info(f"[DAM-SIMPLE] Résultat base extractor: {base_result}")
            
            # Si aucun code trouvé, on s'arrête
            if not base_result or not base_result.get("code"):
                logger.warning("[DAM-SIMPLE] Aucun code trouvé par base extractor")
                return self._create_rejected_result("no_code_found")
            
            code = base_result["code"]
            base_confidence = base_result.get("confidence", 0.0)
            method = base_result.get("method", "unknown")
            
            logger.info(f"[DAM-SIMPLE] Code trouvé: '{code}' (conf: {base_confidence:.2f}, méthode: {method})")
            
            # 🎯 ÉTAPE 2: VALIDATION DAM
            validation_context = {
                "dam_pattern": method.startswith("dam_"),
                "keyword_found": keyword is not None,
                "roi_used": roi_area is not None,
            }
            
            # Déterminer la source pour la validation
            source = self._determine_source(method)
            
            # Validation
            level, validated_confidence, reasons = self.validator.validate(
                code=code,
                confidence=base_confidence,
                source=source,
                context=validation_context
            )
            
            logger.info(f"[DAM-SIMPLE] Validation: {level.value} (conf: {validated_confidence:.2f})")
            
            # 🎯 ÉTAPE 3: DÉCISION FINALE
            if level == ValidationLevel.REJECTED:
                logger.warning(f"[DAM-SIMPLE] Code rejeté: {reasons}")
                return self._create_rejected_result("validation_failed", code=code, reasons=reasons)
            
            # 📝 PRÉPARER LE RÉSULTAT FINAL
            result = {
                "code": code,
                "confidence": validated_confidence,
                "status": "accepted",
                "method": f"dam_enhanced_{method}",
                "validation_level": level.value,
                "validation_reasons": reasons,
                "source": source,
                "base_method": method,
                "base_confidence": base_confidence,
            }
            
            # 🔥 AJOUTER INFO DAM SI PRÉSENT
            if method.startswith("dam_"):
                result["dam_detected"] = True
                result["dam_method"] = method
            
            # 🎯 ÉTAPE 4: YOLO VERIFICATION (optionnel)
            if original_image is not None and self.yolo_detector:
                yolo_boost = await self._verify_with_yolo(
                    original_image, code, roi_area, validated_confidence
                )
                if yolo_boost:
                    result["confidence"] = yolo_boost["confidence"]
                    result["yolo_verified"] = True
                    result["yolo_confidence"] = yolo_boost["yolo_confidence"]
                    logger.info(f"[DAM-SIMPLE] ✓ YOLO verification boost: {yolo_boost['confidence']:.2f}")
            
            logger.info(f"[DAM-SIMPLE] ✓ Code accepté: {code} (conf: {result['confidence']:.2f})")
            
            return result

        except Exception as e:
            logger.error(f"[DAM-SIMPLE] Erreur: {e}")
            import traceback
            traceback.print_exc()
            return self._create_error_result(str(e))
    
    def _determine_source(self, method: str) -> str:
        """Déterminer la source pour la validation"""
        if method.startswith("dam_"):
            return "dam_pattern"
        elif method.startswith("keyword_"):
            return "keyword"
        elif method == "htr":
            return "htr"
        elif method == "generic_safe":
            return "ocr"
        else:
            return "ocr"
    
    async def _verify_with_yolo(
        self, 
        image, 
        code: str, 
        roi_area: Optional[Dict], 
        current_confidence: float
    ) -> Optional[Dict]:
        """Vérification optionnelle avec YOLO"""
        try:
            if not self.yolo_detector:
                return None
            
            # Détecter les régions
            regions = await self.yolo_detector.detect_text_regions(
                image, methods=["yolo", "opencv"]
            )
            
            if not regions:
                return None
            
            # Filtrer les régions dans le ROI
            filtered_regions = []
            for region in regions:
                if roi_area and not self._is_in_region(region, roi_area):
                    continue
                filtered_regions.append(region)
            
            if not filtered_regions:
                return None
            
            # Prendre la région avec la plus haute confiance
            best_region = max(filtered_regions, key=lambda r: r.get("confidence", 0))
            region_confidence = best_region.get("confidence", 0.5)
            
            # Bonus YOLO
            yolo_boost = min(1.0, current_confidence * (1.0 + (region_confidence * 0.3)))
            
            return {
                "confidence": yolo_boost,
                "yolo_confidence": region_confidence,
                "region_count": len(filtered_regions)
            }
            
        except Exception as e:
            logger.warning(f"[YOLO-VERIFY] Erreur: {e}")
            return None
    
    def _is_in_region(self, region: Dict, roi: Dict) -> bool:
        """Vérifier si une région YOLO est dans le ROI"""
        try:
            region_center_x = region["x"] + (region["width"] / 2)
            region_center_y = region["y"] + (region["height"] / 2)
            
            roi_x1 = roi.get("x", 0)
            roi_y1 = roi.get("y", 0)
            roi_x2 = roi_x1 + roi.get("width", 0)
            roi_y2 = roi_y1 + roi.get("height", 0)
            
            margin = 10  # pixels de marge
            return (roi_x1 - margin <= region_center_x <= roi_x2 + margin and 
                    roi_y1 - margin <= region_center_y <= roi_y2 + margin)
            
        except Exception:
            return False
    
    def _create_rejected_result(self, reason: str, **kwargs) -> Dict:
        """Créer un résultat rejeté"""
        result = {
            "code": None,
            "confidence": 0.0,
            "status": "rejected",
            "method": "dam_rejected",
            "rejection_reason": reason,
        }
        result.update(kwargs)
        return result
    
    def _create_error_result(self, error: str) -> Dict:
        """Créer un résultat d'erreur"""
        return {
            "code": None,
            "confidence": 0.0,
            "status": "error",
            "method": "dam_error",
            "error": error,
        }


# Alias
EnhancedExtractor = EnhancedCodeExtractor