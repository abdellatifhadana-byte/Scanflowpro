"""
ScanFlow Pro V7 - YOLO Text Region Detector (Enterprise-Grade)
Multi-Engine Text Detection with YOLO, PaddleOCR, and OpenCV fallback
"""

import cv2
import numpy as np
import logging
from typing import List, Dict, Optional, Tuple
from PIL import Image

logger = logging.getLogger(__name__)


class YOLOTextRegionDetector:
    """
    محرك كشف مناطق النصوص باستخدام عدة تقنيات:
    1. YOLO للكشف العام عن العناصر
    2. OpenCV Contour Detection كخطة احتياطية موثوقة
    """

    def __init__(
        self,
        min_area: int = 500,
        max_area: int = 150000,
        aspect_ratio_range: Tuple[float, float] = (0.1, 15.0),
        use_yolo: bool = True,
        confidence_threshold: float = 0.3
    ):
        self.min_area = min_area
        self.max_area = max_area
        self.aspect_ratio_range = aspect_ratio_range
        self.confidence_threshold = confidence_threshold

        self.yolo_model = None

        if use_yolo:
            self._init_yolo()

        logger.info("🎯 YOLOTextRegionDetector initialized")
        logger.info(f"   YOLO: {'✓' if self.yolo_model else '✗'}")
        logger.info("   OpenCV: ✓ (fallback enabled)")

    def _init_yolo(self):
        try:
            from ultralytics import YOLO
            self.yolo_model = YOLO("yolov8n.pt")
            logger.info("✓ YOLO model loaded successfully")
        except Exception as e:
            logger.warning(f"⚠️ Could not load YOLO: {e}")
            self.yolo_model = None

    async def detect_text_regions(
        self,
        image: Image.Image,
        methods: Optional[List[str]] = None
    ) -> List[Dict]:

        if methods is None:
            methods = ["yolo", "opencv"]

        all_regions: List[Dict] = []

        try:
            np_image = np.array(image)

            if "yolo" in methods and self.yolo_model:
                yolo_regions = await self._detect_with_yolo(np_image)
                all_regions.extend(yolo_regions)
                logger.info(f"YOLO detected {len(yolo_regions)} regions")

            if "opencv" in methods:
                opencv_regions = await self._detect_with_opencv(np_image)
                all_regions.extend(opencv_regions)
                logger.info(f"OpenCV detected {len(opencv_regions)} regions")

            merged = self._merge_overlapping_regions(all_regions)
            filtered = self._filter_regions(merged)

            filtered.sort(key=lambda r: r.get("confidence", 0), reverse=True)
            return filtered

        except Exception as e:
            logger.error(f"Error in detect_text_regions: {e}")
            return []

    # ✅ FIXED: THIS METHOD IS NOW INSIDE THE CLASS
    async def _detect_with_yolo(self, np_image: np.ndarray) -> List[Dict]:
        regions: List[Dict] = []

        try:
            if np_image is None:
                return []

            if len(np_image.shape) == 2:
                np_image = cv2.cvtColor(np_image, cv2.COLOR_GRAY2RGB)
            elif len(np_image.shape) == 3 and np_image.shape[2] == 4:
                np_image = cv2.cvtColor(np_image, cv2.COLOR_RGBA2RGB)

            results = self.yolo_model(np_image, verbose=False)

            for result in results:
                if not result.boxes:
                    continue

                for box in result.boxes:
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    conf = float(box.conf[0])

                    if conf < self.confidence_threshold:
                        continue

                    w = int(x2 - x1)
                    h = int(y2 - y1)
                    if w <= 0 or h <= 0:
                        continue

                    regions.append({
                        "x": int(x1),
                        "y": int(y1),
                        "width": w,
                        "height": h,
                        "confidence": conf * 0.7,
                        "method": "yolo",
                        "area": w * h,
                        "aspect_ratio": w / h
                    })

        except Exception as e:
            logger.warning(f"YOLO detection error: {e}")

        return regions

    async def _detect_with_opencv(self, np_image: np.ndarray) -> List[Dict]:
        regions: List[Dict] = []

        try:
            gray = cv2.cvtColor(np_image, cv2.COLOR_RGB2GRAY) if len(np_image.shape) == 3 else np_image
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            thresh = cv2.adaptiveThreshold(
                blurred, 255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY_INV, 11, 2
            )

            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 3))
            dilated = cv2.dilate(thresh, kernel, iterations=2)

            contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for c in contours:
                x, y, w, h = cv2.boundingRect(c)
                area = w * h

                if self.min_area <= area <= self.max_area:
                    ar = w / h if h > 0 else 0
                    conf = self._calculate_opencv_confidence(area, ar, w, h)
                    regions.append({
                        "x": x, "y": y, "width": w, "height": h,
                        "confidence": conf, "method": "opencv",
                        "area": area, "aspect_ratio": ar
                    })

        except Exception as e:
            logger.warning(f"OpenCV detection error: {e}")

        return regions

    def _calculate_opencv_confidence(self, area, ar, w, h):
        conf = 0.5
        if 5000 <= area <= 50000:
            conf += 0.15
        if 2.0 <= ar <= 10.0:
            conf += 0.15
        if w > 50 and 15 <= h <= 80:
            conf += 0.1
        if area < 1000 or area > 100000:
            conf -= 0.1
        return max(0.1, min(0.7, conf))

    def _merge_overlapping_regions(self, regions):
        merged = []
        for r in sorted(regions, key=lambda x: x["area"], reverse=True):
            if not any(self._iou(r, m) > 0.3 for m in merged):
                merged.append(r)
        return merged

    def _iou(self, a, b):
        x1 = max(a["x"], b["x"])
        y1 = max(a["y"], b["y"])
        x2 = min(a["x"] + a["width"], b["x"] + b["width"])
        y2 = min(a["y"] + a["height"], b["y"] + b["height"])
        if x2 <= x1 or y2 <= y1:
            return 0.0
        inter = (x2 - x1) * (y2 - y1)
        union = a["area"] + b["area"] - inter
        return inter / union if union else 0.0

    def _filter_regions(self, regions):
        return [
            r for r in regions
            if self.min_area <= r["area"] <= self.max_area
            and self.aspect_ratio_range[0] <= r["aspect_ratio"] <= self.aspect_ratio_range[1]
        ]


# Global singleton
_yolo_detector: Optional[YOLOTextRegionDetector] = None


def get_yolo_text_detector() -> YOLOTextRegionDetector:
    global _yolo_detector
    if _yolo_detector is None:
        _yolo_detector = YOLOTextRegionDetector()
    return _yolo_detector
