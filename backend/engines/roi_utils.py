"""
ScanFlow Pro V7 - ROI Utilities
أدوات مساعدة لتوحيد صيغ ROI في جميع أنحاء النظام
"""

import logging
from typing import Optional, Dict, Tuple

logger = logging.getLogger(__name__)


def roi_dict_to_tuple(roi: Optional[Dict]) -> Optional[Tuple]:
    """
    تحويل ROI من dict (x,y,w,h) إلى tuple (x1,y1,x2,y2)
    
    Args:
        roi: {'x': int, 'y': int, 'width': int, 'height': int}
    
    Returns:
        (x, y, x+w, y+h) أو None
    """
    if not roi:
        return None
    
    try:
        x = int(roi.get('x', 0))
        y = int(roi.get('y', 0))
        w = int(roi.get('width', 0))
        h = int(roi.get('height', 0))
        
        # التأكد من عدم الخروج عن حدود الصورة
        x2 = x + w
        y2 = y + h
        
        # أمان إضافي
        if x < 0: x = 0
        if y < 0: y = 0
        if w <= 0 or h <= 0:
            logger.warning(f"ROI بأبعاد غير صالحة: {roi}")
            return None
            
        return (x, y, x2, y2)
        
    except Exception as e:
        logger.error(f"خطأ في تحويل ROI: {e}, roi={roi}")
        return None


def tuple_to_roi_dict(roi_tuple: Optional[Tuple]) -> Optional[Dict]:
    """
    تحويل ROI من tuple إلى dict
    
    Args:
        roi_tuple: (x1, y1, x2, y2)
    
    Returns:
        {'x': x1, 'y': y1, 'width': w, 'height': h}
    """
    if not roi_tuple or len(roi_tuple) != 4:
        return None
    
    try:
        x1, y1, x2, y2 = roi_tuple
        return {
            'x': int(x1),
            'y': int(y1),
            'width': int(x2 - x1),
            'height': int(y2 - y1)
        }
    except Exception as e:
        logger.error(f"خطأ في تحويل tuple إلى dict: {e}")
        return None


def expand_roi(roi: Dict, pixels: int = 20) -> Dict:
    """
    توسيع ROI من جميع الجهات
    
    Args:
        roi: ROI الأصلية
        pixels: عدد البكسل للتوسيع
    
    Returns:
        ROI موسعة
    """
    try:
        return {
            'x': max(0, roi['x'] - pixels),
            'y': max(0, roi['y'] - pixels),
            'width': roi['width'] + (2 * pixels),
            'height': roi['height'] + (2 * pixels)
        }
    except Exception as e:
        logger.error(f"خطأ في توسيع ROI: {e}")
        return roi


def roi_center(roi: Dict) -> Tuple[float, float]:
    """
    حساب مركز ROI
    
    Returns:
        (center_x, center_y)
    """
    try:
        center_x = roi['x'] + (roi['width'] / 2)
        center_y = roi['y'] + (roi['height'] / 2)
        return (center_x, center_y)
    except Exception as e:
        logger.error(f"خطأ في حساب مركز ROI: {e}")
        return (0, 0)


def is_point_in_roi(point_x: int, point_y: int, roi: Dict) -> bool:
    """
    التحقق إذا كانت النقطة داخل ROI
    
    Args:
        point_x: إحداثي x للنقطة
        point_y: إحداثي y للنقطة
        roi: المنطقة
    
    Returns:
        True إذا كانت النقطة داخل ROI
    """
    try:
        x1, y1 = roi['x'], roi['y']
        x2, y2 = roi['x'] + roi['width'], roi['y'] + roi['height']
        return x1 <= point_x <= x2 and y1 <= point_y <= y2
    except Exception as e:
        logger.error(f"خطأ في التحقق من النقطة في ROI: {e}")
        return False


def crop_image_with_roi(image, roi: Dict):
    """
    قص الصورة باستخدام ROI مع التحقق من الحدود
    
    Args:
        image: صورة PIL
        roi: منطقة القص
    
    Returns:
        صورة مقصوصة أو الصورة الأصلية في حالة الخطأ
    """
    try:
        from PIL import Image
        
        img_width, img_height = image.size
        x1 = max(0, roi['x'])
        y1 = max(0, roi['y'])
        x2 = min(img_width, roi['x'] + roi['width'])
        y2 = min(img_height, roi['y'] + roi['height'])
        
        if x1 >= x2 or y1 >= y2:
            logger.warning(f"ROI خارج الحدود: {roi}, حجم الصورة: {img_width}x{img_height}")
            return image
            
        return image.crop((x1, y1, x2, y2))
    except Exception as e:
        logger.error(f"خطأ في قص الصورة: {e}")
        return image