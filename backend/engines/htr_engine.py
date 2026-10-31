from PIL import Image
import numpy as np
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


class HTREngine:
    """محرك قراءة الخط اليدوي (Handwritten Text Recognition)"""

    def __init__(self, lang: str = "en"):
        try:
            # Import lazily so a missing native OCR dependency cannot prevent
            # the FastAPI application from importing and starting.
            from paddleocr import PaddleOCR

            self.ocr = PaddleOCR(use_angle_cls=True, lang=lang)
            logger.info("✓ PaddleOCR initialized successfully")
        except Exception as e:
            logger.error(f"❌ PaddleOCR init error: {e}")
            self.ocr = None

    async def extract_text(self, image: Image.Image, roi: tuple = None) -> str:
        """استخراج النص فقط"""
        if not self.ocr:
            return ""

        try:
            if roi:
                x, y, w, h = roi
                image = image.crop((x, y, x + w, y + h))

            img = np.array(image)

            try:
                result = self.ocr.ocr(img, cls=True)
            except TypeError:
                result = self.ocr.ocr(img)

            if result and result[0]:
                texts = [
                    line[1][0]
                    for line in result[0]
                    if isinstance(line, (list, tuple)) and len(line) >= 2
                ]
                return " ".join(texts).strip()

            return ""

        except Exception as e:
            logger.error(f"[HTR extract_text] {e}")
            return ""

    async def extract_with_confidence(
        self,
        image: Image.Image,
        roi: tuple = None
    ) -> List[Dict]:
        """استخراج النص مع الثقة"""
        if not self.ocr:
            logger.warning("[HTR] PaddleOCR not available")
            return []

        try:
            if roi:
                x, y, w, h = roi
                image = image.crop((x, y, x + w, y + h))

            img = np.array(image)

            try:
                result = self.ocr.ocr(img, cls=True)
            except TypeError:
                result = self.ocr.ocr(img)

            outputs: List[Dict] = []

            if result and result[0]:
                for line in result[0]:
                    if not isinstance(line, (list, tuple)) or len(line) < 2:
                        continue

                    bbox = (
                        line[0]
                        if isinstance(line[0], (list, tuple)) and len(line[0]) >= 4
                        else None
                    )
                    text = line[1][0]
                    confidence = float(line[1][1]) if len(line[1]) > 1 else 0.5

                    if not bbox or not text:
                        continue

                    outputs.append({
                        "text": text,
                        "confidence": confidence,
                        "bbox": bbox
                    })

            logger.info(f"[HTR] Extracted {len(outputs)} texts")
            return outputs

        except Exception as e:
            logger.error(f"[HTR extract_with_confidence] {e}")
            return []
