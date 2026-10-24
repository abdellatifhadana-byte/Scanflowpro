"""
ScanFlow Pro V7 - Text Region Detector (YOLO Alternative - Lightweight)
Uses OpenCV + Contour Detection instead of heavy YOLO models
"""

import cv2
import numpy as np
import logging
from typing import List, Dict, Optional, Tuple
from PIL import Image

logger = logging.getLogger(__name__)

class TextRegionDetector:
    """
    محرك خفيف للكشف عن مناطق النصوص باستخدام OpenCV
    بديل خفيف لـ YOLO - لا يتطلب نماذج ضخمة
    """
    
    def __init__(
        self,
        min_area: int = 1000,
        max_area: int = 100000,
        aspect_ratio_range: Tuple[float, float] = (0.1, 10.0)
    ):
        """
        Initialize Text Region Detector
        
        Args:
            min_area: الحد الأدنى لمساحة المنطقة (بكسل²)
            max_area: الحد الأقصى لمساحة المنطقة (بكسل²)
            aspect_ratio_range: نطاق نسبة العرض إلى الارتفاع المقبول
        """
        self.min_area = min_area
        self.max_area = max_area
        self.aspect_ratio_range = aspect_ratio_range
        
        logger.info(f"✨ Text Region Detector initialized (lightweight mode)")
    
    def detect_text_regions(
        self,
        image: Image.Image,
        focus_on_numbers: bool = True
    ) -> List[Dict]:
        """
        اكتشاف مناطق النصوص في الصورة
        
        Args:
            image: صورة PIL
            focus_on_numbers: التركيز على المناطق التي تحتوي على أرقام
            
        Returns:
            قائمة بالمناطق المكتشفة [{'x', 'y', 'width', 'height', 'confidence'}]
        """
        try:
            logger.info("🔍 Text Region Detection - START")
            
            # تحويل PIL إلى OpenCV
            cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
            
            # معالجة الصورة
            # 1. تطبيق Gaussian Blur لإزالة الضوضاء
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            
            # 2. Adaptive Thresholding (أفضل من العتبة البسيطة)
            thresh = cv2.adaptiveThreshold(
                blurred,
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY_INV,
                11,
                2
            )
            
            # 3. Morphological Operations لتوصيل الأحرف المتقاربة
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 3))
            dilated = cv2.dilate(thresh, kernel, iterations=2)
            
            # 4. اكتشاف الـ Contours
            contours, _ = cv2.findContours(
                dilated,
                cv2.RETR_EXTERNAL,
                cv2.CHAIN_APPROX_SIMPLE
            )
            
            logger.info(f"   🔍 Found {len(contours)} raw contours")
            
            # 5. فلترة الـ Contours
            text_regions = []
            
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                area = w * h
                
                # فلترة حسب المساحة
                if area < self.min_area or area > self.max_area:
                    continue
                
                # فلترة حسب نسبة العرض/الارتفاع
                aspect_ratio = w / h if h > 0 else 0
                if aspect_ratio < self.aspect_ratio_range[0] or aspect_ratio > self.aspect_ratio_range[1]:
                    continue
                
                # حساب الثقة (confidence) بناءً على خصائص المنطقة
                confidence = self._calculate_confidence(area, aspect_ratio, w, h)
                
                text_regions.append({
                    'x': int(x),
                    'y': int(y),
                    'width': int(w),
                    'height': int(h),
                    'confidence': confidence,
                    'area': area,
                    'aspect_ratio': aspect_ratio
                })
            
            # ترتيب حسب الثقة
            text_regions.sort(key=lambda r: r['confidence'], reverse=True)
            
            logger.info(f"   ✓ Detected {len(text_regions)} valid text regions")
            
            return text_regions
            
        except Exception as e:
            logger.error(f"❌ خطأ في Text Region Detection: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _calculate_confidence(
        self,
        area: float,
        aspect_ratio: float,
        width: int,
        height: int
    ) -> float:
        """
        حساب مستوى الثقة للمنطقة المكتشفة
        
        Args:
            area: مساحة المنطقة
            aspect_ratio: نسبة العرض/الارتفاع
            width: العرض
            height: الارتفاع
            
        Returns:
            مستوى الثقة (0-1)
        """
        confidence = 0.5  # قيمة أساسية
        
        # مكافأة للمساحات المتوسطة (ليست صغيرة جداً أو كبيرة جداً)
        ideal_area = (self.min_area + self.max_area) / 2
        area_score = 1.0 - abs(area - ideal_area) / ideal_area
        confidence += area_score * 0.2
        
        # مكافأة لنسب العرض/الارتفاع المناسبة للنصوص (2:1 إلى 8:1)
        if 2.0 <= aspect_ratio <= 8.0:
            confidence += 0.2
        
        # مكافأة للأبعاد المناسبة للأكواد (العرض > 50 بكسل، الارتفاع 20-60 بكسل)
        if width > 50 and 20 <= height <= 60:
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    async def detect_and_extract(
        self,
        image: Image.Image,
        ocr_engine,
        top_k: int = 3
    ) -> List[Dict]:
        """
        اكتشاف المناطق واستخراج النصوص منها مباشرة
        
        Args:
            image: صورة PIL
            ocr_engine: محرك OCR لاستخراج النصوص
            top_k: عدد أفضل المناطق لاستخراج النصوص منها
            
        Returns:
            قائمة بالمناطق مع النصوص المستخرجة
        """
        try:
            # اكتشاف المناطق
            regions = self.detect_text_regions(image)
            
            if not regions:
                logger.warning("⚠️ لم يتم العثور على مناطق نصية")
                return []
            
            # أخذ أفضل top_k مناطق
            top_regions = regions[:top_k]
            
            logger.info(f"🔍 Extracting text from top {len(top_regions)} regions")
            
            results = []
            
            for i, region in enumerate(top_regions, 1):
                try:
                    # قص المنطقة من الصورة
                    x, y, w, h = region['x'], region['y'], region['width'], region['height']
                    
                    # إضافة padding صغير (5 بكسل)
                    x = max(0, x - 5)
                    y = max(0, y - 5)
                    w = min(image.width - x, w + 10)
                    h = min(image.height - y, h + 10)
                    
                    roi = image.crop((x, y, x + w, y + h))
                    
                    # استخراج النص باستخدام OCR
                    roi_tuple = (x, y, w, h)
                    ocr_results = await ocr_engine.extract_with_confidence(image, roi_tuple)
                    
                    if ocr_results:
                        results.append({
                            'region': region,
                            'ocr_results': ocr_results,
                            'region_index': i
                        })
                        logger.info(f"   ✓ Region {i}: Found {len(ocr_results)} text elements")
                    
                except Exception as e:
                    logger.error(f"   ❌ خطأ في استخراج المنطقة {i}: {e}")
                    continue
            
            logger.info(f"✓ Extracted text from {len(results)} regions successfully")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ خطأ في detect_and_extract: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def visualize_regions(
        self,
        image: Image.Image,
        regions: List[Dict],
        output_path: str
    ):
        """
        رسم المناطق المكتشفة على الصورة (للتصحيح)
        
        Args:
            image: صورة PIL
            regions: المناطق المكتشفة
            output_path: مسار حفظ الصورة
        """
        try:
            cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            
            for i, region in enumerate(regions[:10], 1):  # أول 10 فقط
                x, y, w, h = region['x'], region['y'], region['width'], region['height']
                conf = region['confidence']
                
                # رسم المستطيل
                color = (0, 255, 0) if conf > 0.7 else (0, 165, 255)
                cv2.rectangle(cv_image, (x, y), (x + w, y + h), color, 2)
                
                # كتابة رقم المنطقة والثقة
                label = f"#{i} ({conf:.2f})"
                cv2.putText(
                    cv_image,
                    label,
                    (x, y - 5),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    color,
                    2
                )
            
            cv2.imwrite(output_path, cv_image)
            logger.info(f"✓ Visualization saved to {output_path}")
            
        except Exception as e:
            logger.error(f"❌ خطأ في visualize_regions: {e}")


# ================================
# Test Function
# ================================
def test_text_region_detector():
    """اختبار محرك كشف المناطق النصية"""
    from PIL import Image
    
    detector = TextRegionDetector(
        min_area=500,
        max_area=50000,
        aspect_ratio_range=(0.5, 15.0)
    )
    
    # تحميل صورة اختبارية
    test_image_path = "/tmp/test_document_12345678.pdf"
    
    # تحويل PDF إلى صورة للاختبار
    try:
        import fitz  # PyMuPDF
        pdf = fitz.open(test_image_path)
        page = pdf[0]
        pix = page.get_pixmap(dpi=300)
        img_data = pix.tobytes("png")
        
        from io import BytesIO
        image = Image.open(BytesIO(img_data))
        
        # اكتشاف المناطق
        regions = detector.detect_text_regions(image)
        
        print(f"\n{'='*60}")
        print(f"🧪 Text Region Detector - Test Results")
        print(f"{'='*60}")
        print(f"Total regions detected: {len(regions)}")
        
        for i, region in enumerate(regions[:5], 1):
            print(f"\n  Region {i}:")
            print(f"    Position: ({region['x']}, {region['y']})")
            print(f"    Size: {region['width']}x{region['height']}")
            print(f"    Confidence: {region['confidence']:.3f}")
        
        # حفظ visualisation
        detector.visualize_regions(image, regions, "/tmp/detected_regions.png")
        
        print(f"\n{'='*60}\n")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")


if __name__ == "__main__":
    test_text_region_detector()
