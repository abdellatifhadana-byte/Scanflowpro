import logging
from typing import Dict, List, Optional
from PIL import Image
import copy

logger = logging.getLogger(__name__)


def roi_to_tuple(roi_dict: Dict) -> tuple:
    """
    تحويل ROI من dict إلى tuple للاستخدام مع PIL
    
    Args:
        roi_dict: {'x': int, 'y': int, 'width': int, 'height': int}
    
    Returns:
        (x1, y1, x2, y2)
    """
    if not roi_dict:
        return None
    
    try:
        x = int(roi_dict.get('x', 0))
        y = int(roi_dict.get('y', 0))
        w = int(roi_dict.get('width', 0))
        h = int(roi_dict.get('height', 0))
        
        # التأكد من الأبعاد الإيجابية
        if w <= 0 or h <= 0:
            logger.warning(f"ROI بأبعاد غير صالحة: {roi_dict}")
            return None
        
        return (x, y, x + w, y + h)
    except Exception as e:
        logger.error(f"خطأ في تحويل ROI: {e}")
        return None


def expand_roi_dict(roi_dict: Dict, pixels: int = 20) -> Dict:
    """
    توسيع ROI من جميع الجوانب
    """
    if not roi_dict:
        return None
    
    try:
        return {
            'x': max(0, roi_dict['x'] - pixels),
            'y': max(0, roi_dict['y'] - pixels),
            'width': roi_dict['width'] + (2 * pixels),
            'height': roi_dict['height'] + (2 * pixels)
        }
    except Exception as e:
        logger.error(f"خطأ في توسيع ROI: {e}")
        return roi_dict


class AutoRecoveryEngine:
    """محرك الاسترداد التلقائي - يعمل عند فشل استخراج الكود"""
    
    def __init__(self, image_enhancer, ocr_engine, htr_engine, code_extractor):
        self.image_enhancer = image_enhancer
        self.ocr_engine = ocr_engine
        self.htr_engine = htr_engine
        self.code_extractor = code_extractor
        
        # استراتيجيات الاسترداد
        self.strategies = [
            'enhance_aggressive',
            'expand_roi',
            'switch_engine',
            'try_different_psm',
            'combine_all'
        ]
    
    async def recover_code(self, 
                          page_data: Dict,
                          original_image: Image.Image,
                          settings: Dict) -> Dict:
        """
        محاولة استرداد الكود باستخدام استراتيجيات متعددة
        
        Args:
            page_data: بيانات الصفحة الأصلية
            original_image: الصورة الأصلية
            settings: الإعدادات
        
        Returns:
            أفضل نتيجة مع decision_log
        """
        try:
            logger.info(f"[AUTO_RECOVERY] بدء الاسترداد التلقائي للصفحة {page_data.get('page_number')}")
            
            recovery_results = []
            decision_log = []
            
            # الإعدادات الأساسية
            keyword = settings.get('keyword')
            doc_type = settings.get('document_type', 'printed')
            
            # استخراج code_roi من roi_areas
            roi_areas = settings.get('roi_areas', [])
            code_roi = None
            
            if isinstance(roi_areas, list):
                # roi_areas هو قائمة - نبحث عن code ROI
                for roi in roi_areas:
                    if roi.get('type') == 'code':
                        code_roi = {
                            'x': int(roi['x']),
                            'y': int(roi['y']),
                            'width': int(roi['width']),
                            'height': int(roi['height'])
                        }
                        break
            elif isinstance(roi_areas, dict):
                # roi_areas هو قاموس - نأخذ code_roi مباشرة
                code_roi = roi_areas.get('code_roi')
            
            # استراتيجية 1: تحسين عدواني
            result1 = await self._strategy_aggressive_enhance(original_image, keyword, code_roi, doc_type)
            if result1:
                recovery_results.append(result1)
                decision_log.append({
                    'strategy': 'enhance_aggressive',
                    'result': result1,
                    'timestamp': None
                })
            
            # استراتيجية 2: توسيع ROI
            result2 = await self._strategy_expand_roi(original_image, keyword, code_roi, doc_type)
            if result2:
                recovery_results.append(result2)
                decision_log.append({
                    'strategy': 'expand_roi',
                    'result': result2,
                    'timestamp': None
                })
            
            # استراتيجية 3: تبديل المحرك
            result3 = await self._strategy_switch_engine(original_image, keyword, code_roi, doc_type)
            if result3:
                recovery_results.append(result3)
                decision_log.append({
                    'strategy': 'switch_engine',
                    'result': result3,
                    'timestamp': None
                })
            
            # استراتيجية 4: دمج الكل
            result4 = await self._strategy_combine_all(original_image, keyword, code_roi)
            if result4:
                recovery_results.append(result4)
                decision_log.append({
                    'strategy': 'combine_all',
                    'result': result4,
                    'timestamp': None
                })
            
            # اختيار أفضل نتيجة
            if recovery_results:
                best_result = max(recovery_results, key=lambda x: x.get('confidence', 0))
                
                logger.info(f"[AUTO_RECOVERY] ✓ نجح الاسترداد: {best_result['code']} (confidence: {best_result['confidence']})")
                
                return {
                    'success': True,
                    'code': best_result['code'],
                    'confidence': best_result['confidence'],
                    'method': best_result['method'],
                    'recovery_strategy': best_result.get('strategy', 'unknown'),
                    'decision_log': decision_log,
                    'attempts': len(recovery_results)
                }
            else:
                logger.warning("[AUTO_RECOVERY] فشل الاسترداد بجميع الاستراتيجيات")
                return {
                    'success': False,
                    'code': None,
                    'confidence': 0,
                    'decision_log': decision_log,
                    'attempts': len(recovery_results)
                }
                
        except Exception as e:
            logger.error(f"[AUTO_RECOVERY] خطأ في الاسترداد: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _strategy_aggressive_enhance(self, image: Image.Image, keyword: str, roi: Dict, doc_type: str) -> Optional[Dict]:
        """استراتيجية 1: تحسين عدواني للصورة"""
        try:
            # تحسين بمستوى عالي جداً
            enhanced = await self.image_enhancer.enhance(image, enhancement_level='very_high')
            
            # استخدام ROI المحولة
            roi_tuple = roi_to_tuple(roi)
            
            # OCR/HTR حسب النوع
            if doc_type == 'handwritten':
                results = await self.htr_engine.extract_with_confidence(enhanced, roi_tuple)
            else:
                results = await self.ocr_engine.extract_with_confidence(enhanced, roi_tuple)
            
            # استخراج الكود
            code_result = await self.code_extractor.extract_code_with_keyword(results, keyword, roi)
            
            if code_result.get('code'):
                code_result['strategy'] = 'enhance_aggressive'
                return code_result
            
            return None
            
        except Exception as e:
            logger.error(f"خطأ في استراتيجية التحسين العدواني: {e}")
            return None
    
    async def _strategy_expand_roi(self, image: Image.Image, keyword: str, roi: Dict, doc_type: str) -> Optional[Dict]:
        """استراتيجية 2: توسيع منطقة ROI"""
        try:
            if not roi:
                # إذا لم يكن هناك ROI، نستخدم الصفحة كاملة
                expanded_roi = None
            else:
                # توسيع ROI بنسبة 50%
                expanded_roi = expand_roi_dict(roi, pixels=int(min(roi['width'], roi['height']) * 0.3))
            
            # تحسين + OCR/HTR
            enhanced = await self.image_enhancer.enhance(image, enhancement_level='high')
            
            # استخدام ROI المحولة
            expanded_roi_tuple = roi_to_tuple(expanded_roi) if expanded_roi else None
            
            if doc_type == 'handwritten':
                results = await self.htr_engine.extract_with_confidence(enhanced, expanded_roi_tuple)
            else:
                results = await self.ocr_engine.extract_with_confidence(enhanced, expanded_roi_tuple)
            
            code_result = await self.code_extractor.extract_code_with_keyword(results, keyword, expanded_roi)
            
            if code_result.get('code'):
                code_result['strategy'] = 'expand_roi'
                return code_result
            
            return None
            
        except Exception as e:
            logger.error(f"خطأ في استراتيجية توسيع ROI: {e}")
            return None
    
    async def _strategy_switch_engine(self, image: Image.Image, keyword: str, roi: Dict, doc_type: str) -> Optional[Dict]:
        """استراتيجية 3: تبديل المحرك (OCR ↔ HTR)"""
        try:
            enhanced = await self.image_enhancer.enhance(image, enhancement_level='high')
            
            # استخدام ROI المحولة
            roi_tuple = roi_to_tuple(roi)
            
            # تبديل المحرك
            if doc_type == 'printed':
                # جرب HTR بدلاً من OCR
                results = await self.htr_engine.extract_with_confidence(enhanced, roi_tuple)
            else:
                # جرب OCR بدلاً من HTR
                results = await self.ocr_engine.extract_with_confidence(enhanced, roi_tuple)
            
            code_result = await self.code_extractor.extract_code_with_keyword(results, keyword, roi)
            
            if code_result.get('code'):
                code_result['strategy'] = 'switch_engine'
                return code_result
            
            return None
            
        except Exception as e:
            logger.error(f"خطأ في استراتيجية تبديل المحرك: {e}")
            return None
    
    async def _strategy_combine_all(self, image: Image.Image, keyword: str, roi: Dict) -> Optional[Dict]:
        """استراتيجية 4: دمج OCR + HTR معاً"""
        try:
            enhanced = await self.image_enhancer.enhance(image, enhancement_level='high')
            
            # استخدام ROI المحولة
            roi_tuple = roi_to_tuple(roi)
            
            # OCR + HTR معاً
            ocr_results = await self.ocr_engine.extract_with_confidence(enhanced, roi_tuple)
            htr_results = await self.htr_engine.extract_with_confidence(enhanced, roi_tuple)
            
            # دمج النتائج
            all_results = ocr_results + htr_results
            
            code_result = await self.code_extractor.extract_code_with_keyword(all_results, keyword, roi)
            
            if code_result.get('code'):
                code_result['strategy'] = 'combine_all'
                return code_result
            
            return None
            
        except Exception as e:
            logger.error(f"خطأ في استراتيجية الدمج: {e}")
            return None
    
    def should_trigger_recovery(self, extraction_result: Dict) -> bool:
        """
        تحديد هل يجب تشغيل الاسترداد التلقائي
        
        الشروط:
        - code = None أو NO_CODE
        - confidence < 0.6
        - method = 'failed' أو 'error'
        """
        code = extraction_result.get('code')
        confidence = extraction_result.get('confidence', 0)
        method = extraction_result.get('method', '')
        
        if not code or code == 'NO_CODE':
            return True
        
        if confidence < 0.6:
            return True
        
        if method in ['failed', 'error', 'none']:
            return True
        
        return False