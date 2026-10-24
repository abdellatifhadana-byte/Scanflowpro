import fitz
import io
from PIL import Image
import numpy as np
from pathlib import Path
from typing import List, Tuple
import logging

logger = logging.getLogger(__name__)

class PDFProcessor:
    """معالج PDF - تحويل الصفحات إلى صور عالية الجودة"""
    
    def __init__(self, dpi: int = 400):
        self.dpi = dpi
        self.zoom = dpi / 72  # PDF default is 72 DPI
        
    async def extract_pages(self, pdf_path: str) -> List[dict]:
        """استخراج جميع الصفحات من PDF"""
        try:
            doc = fitz.open(pdf_path)
            pages = []
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                # تحويل الصفحة إلى صورة عالية الجودة جداً
                # استخدام DPI عالي مع colorspace=fitz.csRGB للوضوح الأفضل
                mat = fitz.Matrix(self.zoom, self.zoom)
                pix = page.get_pixmap(matrix=mat, alpha=False, colorspace=fitz.csGRAY)
                
                # تحويل إلى PIL Image
                img_data = pix.tobytes("png")
                img = Image.open(io.BytesIO(img_data))
                
                # تحسين الصورة للحصول على نص أوضح
                img = img.convert('L')  # Grayscale
                
                logger.info(f"[PDF_PROCESSOR] صفحة {page_num+1}: {img.width}x{img.height}px @ {self.dpi}DPI")
                
                pages.append({
                    'page_number': page_num + 1,
                    'image': img,
                    'width': img.width,
                    'height': img.height,
                    'original_file': Path(pdf_path).name
                })
            
            doc.close()
            logger.info(f"استخراج {len(pages)} صفحة من {Path(pdf_path).name}")
            return pages
            
        except Exception as e:
            logger.error(f"خطأ في استخراج الصفحات: {e}")
            raise
    
    async def save_page_image(self, page_data: dict, output_path: str):
        """حفظ صورة الصفحة"""
        try:
            page_data['image'].save(output_path, 'PNG', quality=95)
            logger.info(f"حفظ الصفحة {page_data['page_number']} في {output_path}")
        except Exception as e:
            logger.error(f"خطأ في حفظ الصورة: {e}")
            raise
