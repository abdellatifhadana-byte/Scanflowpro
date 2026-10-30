import cv2
import numpy as np
from PIL import Image
import logging
from typing import Dict

logger = logging.getLogger(__name__)

class ImageEnhancer:
    """محسن الصور - تحسين جودة الصور قبل OCR"""
    
    def __init__(self):
        pass
    
    async def enhance(self, image: Image.Image, enhancement_level: str = 'medium') -> Image.Image:
        """تحسين الصورة للحصول على أفضل نتائج OCR"""
        try:
            # تحويل إلى numpy array
            img_array = np.array(image)
            
            # تحويل إلى grayscale إذا كانت ملونة
            if len(img_array.shape) == 3:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = img_array
            
            # إزالة الضوضاء
            denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
            
            # زيادة الحدة (sharpening) قبل OCR
            kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
            sharpened = cv2.filter2D(denoised, -1, kernel)
            
            # تحسين التباين
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
            enhanced = clahe.apply(sharpened)
            
            # تطبيق threshold
            if enhancement_level == 'high':
                # Adaptive threshold للنصوص المكتوبة يدوياً
                binary = cv2.adaptiveThreshold(
                    enhanced, 255, 
                    cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                    cv2.THRESH_BINARY, 11, 2
                )
            else:
                # Otsu threshold للنصوص المطبوعة
                _, binary = cv2.threshold(
                    enhanced, 0, 255, 
                    cv2.THRESH_BINARY + cv2.THRESH_OTSU
                )
            
            # تحويل مرة أخرى إلى PIL Image
            result = Image.fromarray(binary)
            logger.info("تحسين الصورة بنجاح")
            return result
            
        except Exception as e:
            logger.error(f"خطأ في تحسين الصورة: {e}")
            return image  # إرجاع الصورة الأصلية في حالة الخطأ
    
    async def deskew(self, image: Image.Image) -> Image.Image:
        """تصحيح ميلان الصورة"""
        try:
            img_array = np.array(image)
            
            # تحويل إلى grayscale
            if len(img_array.shape) == 3:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = img_array
            
            # اكتشاف الحواف
            coords = np.column_stack(np.where(gray > 0))
            angle = cv2.minAreaRect(coords)[-1]
            
            # تصحيح الزاوية
            if angle < -45:
                angle = -(90 + angle)
            else:
                angle = -angle
            
            # تطبيق التدوير
            (h, w) = gray.shape[:2]
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            rotated = cv2.warpAffine(
                gray, M, (w, h),
                flags=cv2.INTER_CUBIC,
                borderMode=cv2.BORDER_REPLICATE
            )
            
            return Image.fromarray(rotated)
            
        except Exception as e:
            logger.error(f"خطأ في تصحيح الميلان: {e}")
            return image
    
    async def detect_orientation(self, image: Image.Image) -> int:
        """اكتشاف اتجاه الصفحة (0, 90, 180, 270)"""
        try:
            img_array = np.array(image)
            
            # تحويل إلى grayscale
            if len(img_array.shape) == 3:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = img_array
            
            # حساب كثافة النص في كل اتجاه
            orientations = [0, 90, 180, 270]
            scores = []
            
            for angle in orientations:
                # تدوير الصورة
                if angle == 0:
                    rotated = gray
                else:
                    h, w = gray.shape
                    center = (w // 2, h // 2)
                    M = cv2.getRotationMatrix2D(center, angle, 1.0)
                    rotated = cv2.warpAffine(gray, M, (w, h))
                
                # حساب كثافة النص (استخدام edge detection)
                edges = cv2.Canny(rotated, 50, 150)
                score = np.sum(edges > 0)
                scores.append(score)
            
            # الاتجاه الصحيح هو الذي يعطي أكبر كثافة حواف
            best_orientation = orientations[np.argmax(scores)]
            
            if best_orientation != 0:
                logger.info(f"اكتشفنا أن الصفحة مقلوبة بزاوية {best_orientation} درجة")
            
            return best_orientation
            
        except Exception as e:
            logger.error(f"خطأ في اكتشاف الاتجاه: {e}")
            return 0
    
    async def rotate_if_needed(self, image: Image.Image) -> Image.Image:
        """تدوير الصورة إذا كانت مقلوبة"""
        try:
            angle = await self.detect_orientation(image)
            
            if angle == 0:
                return image
            
            # تدوير الصورة
            rotated = image.rotate(-angle, expand=True)
            logger.info(f"تم تدوير الصورة {angle} درجة")
            return rotated
            
        except Exception as e:
            logger.error(f"خطأ في التدوير: {e}")
            return image
    
    async def check_blur(self, image: Image.Image) -> Dict:
        """التحقق من وضوح الصورة"""
        try:
            img_array = np.array(image)
            
            # تحويل إلى grayscale
            if len(img_array.shape) == 3:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = img_array
            
            # حساب Laplacian variance للكشف عن الضبابية
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            
            # تقليل العتبة لتكون أكثر تسامحاً
            is_blurry = laplacian_var < 30  # العتبة المحسنة
            
            result = {
                'is_blurry': bool(is_blurry),
                'blur_score': float(laplacian_var),
                'quality': 'good' if laplacian_var > 100 else 'medium' if laplacian_var > 30 else 'poor'
            }
            
            if is_blurry:
                logger.warning(f"الصورة مضببة (النتيجة: {laplacian_var:.2f})")
            
            return result
            
        except Exception as e:
            logger.error(f"خطأ في التحقق من الضبابية: {e}")
            return {'is_blurry': False, 'blur_score': 0, 'quality': 'unknown'}
    
    async def expand_roi(self, image: Image.Image, roi: Dict, expansion: int = 20) -> Image.Image:
        """تكبير منطقة ROI من جميع الاتجاهات"""
        try:
            img_array = np.array(image)
            h, w = img_array.shape[:2]
            
            # الحصول على إحداثيات ROI
            x = max(0, roi.get('x', 0) - expansion)
            y = max(0, roi.get('y', 0) - expansion)
            width = min(w - x, roi.get('width', w) + 2 * expansion)
            height = min(h - y, roi.get('height', h) + 2 * expansion)
            
            # قص المنطقة الموسعة
            expanded = img_array[y:y+height, x:x+width]
            
            logger.info(f"تم توسيع ROI بمقدار {expansion} بكسل من كل جانب")
            return Image.fromarray(expanded)
            
        except Exception as e:
            logger.error(f"خطأ في توسيع ROI: {e}")
            return image
