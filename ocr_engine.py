import pytesseract
from config import TESSERACT_CMD, TESSERACT_LANGUAGES
from PIL import Image
import re
import logging
import os
from typing import List, Dict
import numpy as np

logger = logging.getLogger(__name__)

class OCREngine:
    """محرك OCR لقراءة النصوص المطبوعة"""

    def __init__(self, lang: str = TESSERACT_LANGUAGES):
        self.lang = lang
        
        # PSM ديناميكي - سنجرب عدة إعدادات
        self.psm_list = [6, 7, 11, 12]  # line, single-line, sparse, sparse text
        
        # تعيين مسار Tesseract من config فقط (مصدر واحد للحقيقة)
        if TESSERACT_CMD and os.path.exists(TESSERACT_CMD):
            pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
            logger.info(f"[OCR] Tesseract path set: {TESSERACT_CMD}")
        else:
            logger.error(f"[OCR] Tesseract غير موجود في المسار: {TESSERACT_CMD}")

        # التحقق من Tesseract
        try:
            version = pytesseract.get_tesseract_version()
            logger.info(f"[OCR] Tesseract version: {version}")
        except Exception as e:
            logger.error(f"[OCR] خطأ في التحقق من Tesseract: {e}")
    
    def _extract_with_psm(self, image: Image.Image, psm: int) -> List[Dict]:
        """استخراج النص باستخدام PSM محدد"""
        try:
            config = f'--oem 3 --psm {psm}'
            
            # استخراج البيانات التفصيلية
            data = pytesseract.image_to_data(
                image, 
                lang=self.lang, 
                config=config,
                output_type=pytesseract.Output.DICT
            )
            
            results = []
            for i in range(len(data['text'])):
                text = data['text'][i].strip()
                if text:
                    # تحويل الثقة من 0-100 إلى 0-1
                    conf = float(data['conf'][i])
                    confidence = conf / 100.0 if conf > 0 else 0.01
                    
                    results.append({
                        'text': text,
                        'confidence': confidence,
                        'bbox': (
                            int(data['left'][i]),
                            int(data['top'][i]),
                            int(data['width'][i]),
                            int(data['height'][i])
                        ),
                        'psm': psm,
                        'block_num': int(data['block_num'][i]) if i < len(data.get('block_num', [])) else 0,
                        'line_num': int(data['line_num'][i]) if i < len(data.get('line_num', [])) else 0
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"خطأ في OCR مع PSM {psm}: {e}")
            return []
    
    async def extract_with_confidence(self, image: Image.Image, roi: tuple = None) -> List[Dict]:
        """استخراج النص مع مستوى الثقة - مع تجربة PSM ديناميكي"""
        try:
            # قص المنطقة المحددة إذا وجدت
            working_image = image.copy()
            
            if roi:
                # تحويل (x1,y1,x2,y2) إلى crop صحيح
                x1, y1, x2, y2 = map(int, roi)
                
                # التأكد من أن الإحداثيات داخل حدود الصورة
                width, height = working_image.size
                x1 = max(0, min(x1, width - 1))
                y1 = max(0, min(y1, height - 1))
                x2 = max(x1 + 1, min(x2, width))
                y2 = max(y1 + 1, min(y2, height))
                
                if x2 > x1 and y2 > y1:
                    working_image = working_image.crop((x1, y1, x2, y2))
                    logger.debug(f"[OCR] قص ROI: ({x1},{y1})-({x2},{y2})")
                else:
                    logger.warning(f"[OCR] ROI غير صالحة: ({x1},{y1})-({x2},{y2})")
            
            # تجربة كل PSM وجمع النتائج
            all_results = []
            
            for psm in self.psm_list:
                results = self._extract_with_psm(working_image, psm)
                if results:
                    all_results.extend(results)
                    logger.debug(f"[OCR] PSM {psm}: وجد {len(results)} نص")
            
            if not all_results:
                logger.warning("[OCR] لم يتم العثور على أي نص")
                return []
            
            # إزالة التكرارات (نفس النص في نفس المكان)
            unique_results = []
            seen = set()
            
            for r in all_results:
                # مفتاح فريد يجمع النص والموضع تقريبياً
                bbox = r['bbox']
                key = f"{r['text']}_{bbox[0]//10}_{bbox[1]//10}"
                if key not in seen:
                    seen.add(key)
                    unique_results.append(r)
            
            # دمج النصوص المتشابهة (نفس النص في أماكن قريبة)
            text_to_results = {}
            for r in unique_results:
                text = r['text']
                bbox = r['bbox']
                pos_key = f"{bbox[0]//20}_{bbox[1]//20}"
                
                if text not in text_to_results:
                    text_to_results[text] = {'confidences': [], 'positions': [], 'results': []}
                
                text_to_results[text]['confidences'].append(r['confidence'])
                text_to_results[text]['positions'].append(pos_key)
                text_to_results[text]['results'].append(r)
            
            # إنشاء النتائج النهائية
            final_results = []
            for text, data in text_to_results.items():
                # متوسط الثقة
                avg_confidence = sum(data['confidences']) / len(data['confidences'])
                
                # إذا وجدنا النص في أماكن متعددة، نعزز الثقة
                unique_positions = len(set(data['positions']))
                if unique_positions > 1:
                    avg_confidence = min(1.0, avg_confidence * 1.2)
                
                # استخدام أفضل نتيجة (أعلى ثقة)
                best_result = max(data['results'], key=lambda x: x['confidence'])
                
                final_results.append({
                    'text': text,
                    'confidence': avg_confidence,
                    'bbox': best_result['bbox'],
                    'psm': best_result.get('psm', 0),
                    'source_count': len(data['confidences']),
                    'position_count': unique_positions,
                    'block_num': best_result.get('block_num', 0),
                    'line_num': best_result.get('line_num', 0)
                })
            
            # ترتيب حسب الثقة
            final_results.sort(key=lambda x: x['confidence'], reverse=True)
            
            logger.info(f"[OCR] إجمالي النصوص: {len(final_results)} (فريدة: {len(set(r['text'] for r in final_results))})")
            
            # عرض عينة
            if final_results:
                sample_texts = [f"{r['text'][:20]} ({r['confidence']:.2f})" 
                               for r in final_results[:3]]
                logger.info(f"[OCR] عينة: {sample_texts}")
            
            return final_results
            
        except Exception as e:
            logger.error(f"خطأ في استخراج النص مع الثقة: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    async def extract_text(self, image: Image.Image, roi: tuple = None) -> str:
        """استخراج النص من الصورة"""
        try:
            # قص المنطقة المحددة إذا وجدت
            if roi:
                x1, y1, x2, y2 = map(int, roi)
                image = image.crop((x1, y1, x2, y2))
            
            # استخدام أفضل PSM للنص الكامل
            text = pytesseract.image_to_string(
                image, 
                lang=self.lang, 
                config='--oem 3 --psm 6'
            )
            
            logger.info(f"نص مستخرج: {text[:100]}...")
            return text.strip()
            
        except Exception as e:
            logger.error(f"خطأ في استخراج النص: {e}")
            return ""
    
    async def find_numbers(self, text: str, min_digits: int = 4, max_digits: int = 8) -> List[str]:
        """البحث عن الأرقام في النص"""
        pattern = rf'\b\d{{{min_digits},{max_digits}}}\b'
        numbers = re.findall(pattern, text)
        return list(set(numbers))
    
    async def extract_with_context(self, image: Image.Image, keyword: str, roi: tuple = None) -> List[Dict]:
        """استخراج النص مع التركيز على الكلمة المفتاحية"""
        try:
            # استخراج النتائج العادية
            results = await self.extract_with_confidence(image, roi)
            
            if not results or not keyword:
                return results
            
            # البحث عن الكلمة المفتاحية
            keyword_lower = keyword.lower()
            keyword_results = []
            
            for result in results:
                text_lower = result['text'].lower()
                if keyword_lower in text_lower:
                    # تعزيز الثقة للنصوص التي تحتوي على الكلمة المفتاحية
                    result['confidence'] = min(1.0, result['confidence'] * 1.3)
                    result['keyword_found'] = True
                    keyword_results.append(result)
            
            if keyword_results:
                logger.info(f"[OCR] وجد {len(keyword_results)} نص يحتوي على الكلمة المفتاحية '{keyword}'")
                # إضافة النتائج المحسنة في البداية
                results = keyword_results + [r for r in results if r not in keyword_results]
            
            return results
            
        except Exception as e:
            logger.error(f"خطأ في استخراج النص مع السياق: {e}")
            return []