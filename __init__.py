"""
ScanFlow Pro V7 - Engines Package
"""

from .ocr_engine import OCREngine
from .htr_engine import HTREngine
from .code_extractor import CodeExtractor
from .enhanced_code_extractor import EnhancedCodeExtractor, EnhancedExtractor
from .image_enhancer import ImageEnhancer
from .pdf_processor import PDFProcessor
from .pdf_merger import PDFMerger
from .page_analyzer import PageAnalyzer
from .auto_recovery import AutoRecoveryEngine
from .code_validator import CodeValidator, ValidationLevel
from .candidate_ensemble import CandidateEnsemble, Candidate
from .text_region_detector import TextRegionDetector
from .yolo_text_detector import YOLOTextRegionDetector, get_yolo_text_detector
from .cross_page_validator import CrossPageValidator

# Export ROI utilities
try:
    from .roi_utils import (
        roi_dict_to_tuple,
        tuple_to_roi_dict,
        expand_roi,
        roi_center,
        is_point_in_roi,
        crop_image_with_roi
    )
except ImportError:
    # Fallback إذا لم يكن الملف موجوداً
    roi_dict_to_tuple = None
    tuple_to_roi_dict = None
    expand_roi = None
    roi_center = None
    is_point_in_roi = None
    crop_image_with_roi = None

__all__ = [
    'OCREngine',
    'HTREngine',
    'CodeExtractor',
    'EnhancedCodeExtractor',
    'EnhancedExtractor',
    'ImageEnhancer',
    'PDFProcessor',
    'PDFMerger',
    'PageAnalyzer',
    'AutoRecoveryEngine',
    'CodeValidator',
    'ValidationLevel',
    'CandidateEnsemble',
    'Candidate',
    'TextRegionDetector',
    'YOLOTextRegionDetector',
    'get_yolo_text_detector',
    'CrossPageValidator',
    'roi_dict_to_tuple',
    'tuple_to_roi_dict',
    'expand_roi',
    'roi_center',
    'is_point_in_roi',
    'crop_image_with_roi'
]