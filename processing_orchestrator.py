import logging
from typing import List, Dict
from pathlib import Path
import asyncio
import sys
import uuid
sys.path.append('/app/backend')

# 🔥 استيراد CONFIG الموحد
from config import DAM_CONFIG, DAM_PATTERNS, DAM_ANCHORS

from engines.pdf_processor import PDFProcessor
from engines.image_enhancer import ImageEnhancer
from engines.ocr_engine import OCREngine
from engines.htr_engine import HTREngine
from engines.code_extractor import CodeExtractor
from engines.enhanced_code_extractor import EnhancedCodeExtractor
from engines.page_analyzer import PageAnalyzer
from engines.pdf_merger import PDFMerger
from engines.auto_recovery import AutoRecoveryEngine

logger = logging.getLogger(__name__)

# ================================
# أدوات مساعدة للـ ROI
# ================================
def roi_to_tuple(roi_dict: Dict) -> tuple:
    """تحويل ROI من dict إلى tuple للاستخدام مع PIL"""
    if not roi_dict:
        return None
    
    try:
        x = int(roi_dict.get('x', 0))
        y = int(roi_dict.get('y', 0))
        w = int(roi_dict.get('width', 0))
        h = int(roi_dict.get('height', 0))
        
        if w <= 0 or h <= 0:
            logger.warning(f"ROI بأبعاد غير صالحة: {roi_dict}")
            return None
        
        return (x, y, x + w, y + h)
    except Exception as e:
        logger.error(f"خطأ في تحويل ROI: {e}")
        return None


def expand_roi_dict(roi_dict: Dict, pixels: int = 20) -> Dict:
    """توسيع ROI من جميع الجوانب"""
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


class ProcessingOrchestrator:
    """منسق المعالجة - تنسيق جميع عمليات المعالجة"""
    
    def __init__(self):
        self.pdf_processor = PDFProcessor()
        self.image_enhancer = ImageEnhancer()
        self.ocr_engine = OCREngine()
        self.htr_engine = HTREngine()
        
        # 🔥 Code Extractor مع CONFIG موحد من config.py
        self.code_extractor = CodeExtractor(
            min_digits=DAM_CONFIG["min_digits"],
            max_digits=DAM_CONFIG["max_digits"],
            dam_strict=DAM_CONFIG["strict_mode"]
        )
        
        # 🔥 Enhanced Code Extractor مع نفس CONFIG
        self.enhanced_code_extractor = EnhancedCodeExtractor(
            min_digits=DAM_CONFIG["min_digits"],
            max_digits=DAM_CONFIG["max_digits"],
            strict_mode=DAM_CONFIG["strict_mode"]
        )
        
        self.page_analyzer = PageAnalyzer()
        self.pdf_merger = PDFMerger()
        
        # Auto-Recovery Engine
        self.auto_recovery = AutoRecoveryEngine(
            self.image_enhancer,
            self.ocr_engine,
            self.htr_engine,
            self.code_extractor
        )
        
        logger.info(f"🚀 Processing Orchestrator DAM Edition initialisé")
        logger.info(f"   Profile: {DAM_CONFIG['name']}")
        logger.info(f"   Min digits: {DAM_CONFIG['min_digits']}")
        logger.info(f"   Max digits: {DAM_CONFIG['max_digits']}")
        logger.info(f"   Strict mode: {DAM_CONFIG['strict_mode']}")
    
    async def process_files(self, 
                           files_paths: List[str],
                           file_settings: Dict[str, Dict],
                           session_path: Path,
                           progress_callback=None) -> Dict:
        """معالجة جميع الملفات حسب إعداداتها"""
        try:
            all_pages = []
            total_files = len(files_paths)
            
            # مرحلة 1: استخراج الصفحات من كل ملف
            for idx, file_path in enumerate(files_paths):
                if progress_callback:
                    await progress_callback({
                        'stage': 'extracting',
                        'file': Path(file_path).name,
                        'progress': (idx / total_files) * 20
                    })
                
                file_name = Path(file_path).name
                settings = file_settings.get(file_name, {})
                
                # استخراج الصفحات
                pages = await self.pdf_processor.extract_pages(file_path)
                
                for page in pages:
                    page['original_file_path'] = file_path
                    page['original_page_number'] = page['page_number'] - 1
                    page['source_file'] = file_name
                    page['file_settings'] = settings
                    page['page_id'] = str(uuid.uuid4())
                    
                all_pages.extend(pages)
            
            # مرحلة 2: معالجة كل صفحة
            processed_pages = []
            total_pages = len(all_pages)
            
            for idx, page in enumerate(all_pages):
                if progress_callback:
                    await progress_callback({
                        'stage': 'processing',
                        'page': page['page_number'],
                        'file': page['source_file'],
                        'progress': 20 + (idx / total_pages) * 60
                    })
                
                processed_page = await self._process_single_page(page, session_path)
                processed_pages.append(processed_page)
            
            # مرحلة 3: تحليل وتجميع
            if progress_callback:
                await progress_callback({
                    'stage': 'analyzing',
                    'progress': 85
                })
            
            # تجميع الصفحات حسب الكود
            code_groups = {}
            for page in processed_pages:
                code = page.get('code', 'NO_CODE')
                if code not in code_groups:
                    code_groups[code] = []
                code_groups[code].append(page)
            
            # تحديد الصفحات التابعة
            final_groups = []
            for code, pages in code_groups.items():
                grouped = await self.page_analyzer.analyze_pages(pages)
                final_groups.extend(grouped)
            
            return {
                'success': True,
                'total_pages': len(processed_pages),
                'pages': processed_pages,
                'code_groups': final_groups,
                'total_codes': len(code_groups)
            }
            
        except Exception as e:
            logger.error(f"خطأ في المعالجة: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _extract_code_with_retry(
        self,
        image,
        code_roi: Dict,
        keyword_roi: Dict,
        keyword: str,
        doc_type: str
    ) -> Dict:
        """استخراج الكود مع إعادة المحاولة بتوسيع ROI - محسّنة DAM"""
        try:
            # التحويل المسبق لـ ROI
            code_roi_tuple = roi_to_tuple(code_roi)
            
            # 🔥 STRATÉGIE 1: ROI الأصلي مع Enhanced Extractor DAM
            ocr_results, htr_results = await self._run_ocr_htr(
                image, code_roi_tuple, keyword_roi, doc_type
            )
            
            logger.info("🔍 Utilisation Enhanced Code Extractor (DAM Edition)")
            
            # البحث مع الكلمة المفتاحية باستخدام المحرك المحسّن DAM
            code_result = await self.enhanced_code_extractor.extract_code_with_keyword(
                ocr_results, 
                keyword, 
                code_roi, 
                htr_results, 
                original_image=image
            )
            
            # 🔍 DEBUG: Afficher les résultats OCR pour vérifier
            if ocr_results:
                logger.info(f"[DEBUG] OCR résultats ({len(ocr_results)}):")
                for i, r in enumerate(ocr_results[:5]):
                    logger.info(f"  [{i}] '{r.get('text', '')[:50]}' (conf: {r.get('confidence', 0):.2f})")
            
            # التحقق من النتيجة
            if code_result and code_result.get('code'):
                status = code_result.get('status')
                
                if status == 'accepted':
                    logger.info(f"✅ Enhanced Extractor DAM a réussi: {code_result['code']} (method: {code_result.get('method')})")
                    return code_result
                elif status == 'validation_rejected':
                    logger.warning(f"⚠️ Code trouvé mais rejeté par validation: {code_result.get('code')}")
                elif status == 'rejected':
                    logger.warning(f"⚠️ Code rejeté par vote: {code_result.get('code')}")
            
            # 🔧 STRATÉGIE 2: توسيع ROI (si ROI spécifiée)
            if code_roi:
                logger.info("⚠️ Tentative avec ROI élargie (+30 pixels)...")
                expanded_roi = expand_roi_dict(code_roi, pixels=30)
                expanded_roi_tuple = roi_to_tuple(expanded_roi)
                
                ocr_results, htr_results = await self._run_ocr_htr(
                    image, expanded_roi_tuple, keyword_roi, doc_type
                )
                
                code_result = await self.enhanced_code_extractor.extract_code_with_keyword(
                    ocr_results, keyword, expanded_roi, htr_results, original_image=image
                )
                
                if code_result and code_result.get('code') and code_result.get('status') == 'accepted':
                    code_result['method'] = code_result.get('method', '') + '_expanded'
                    logger.info(f"✅ Enhanced Extractor avec ROI élargie: {code_result['code']}")
                    return code_result
            
            # 🌐 STRATÉGIE 3: Page complète (dernier recours)
            logger.info("⚠️ Tentative sur page complète...")
            ocr_results, htr_results = await self._run_ocr_htr(
                image, None, None, doc_type
            )
            
            code_result = await self.enhanced_code_extractor.extract_code_with_keyword(
                ocr_results, keyword, None, htr_results, original_image=image
            )
            
            if code_result and code_result.get('code'):
                if code_result.get('status') == 'accepted':
                    code_result['method'] = code_result.get('method', '') + '_fullpage'
                    logger.info(f"✅ Enhanced Extractor sur page complète: {code_result['code']}")
                else:
                    logger.warning(f"⚠️ Code trouvé mais non accepté: {code_result}")
            
            return code_result if code_result else {'code': None, 'confidence': 0, 'method': 'failed'}
            
        except Exception as e:
            logger.error(f"Erreur dans l'extraction de code: {e}")
            import traceback
            traceback.print_exc()
            return {'code': None, 'confidence': 0, 'method': 'error'}
    
    async def _run_ocr_htr(self, image, code_roi_tuple, keyword_roi, doc_type):
        """تشغيل OCR/HTR على المناطق المحددة"""
        try:
            ocr_results = []
            htr_results = []
            
            logger.info(f"[OCR/HTR] Type document: {doc_type}, ROI: {code_roi_tuple}")
            
            # 🔧 OCR/HTR selon le type de document
            if doc_type == 'handwritten':
                logger.info("[OCR/HTR] Exécution HTR seulement")
                htr_results = await self.htr_engine.extract_with_confidence(
                    image, code_roi_tuple
                )
                logger.info(f"[OCR/HTR] HTR a retourné {len(htr_results)} résultats")
                
                # DEBUG: Afficher résultats HTR
                if htr_results:
                    for i, r in enumerate(htr_results[:3]):
                        logger.info(f"  HTR[{i}]: '{r.get('text', '')[:30]}'")
            
            elif doc_type == 'mixed':
                logger.info("[OCR/HTR] Exécution OCR + HTR")
                ocr_results = await self.ocr_engine.extract_with_confidence(
                    image, code_roi_tuple
                )
                htr_results = await self.htr_engine.extract_with_confidence(
                    image, code_roi_tuple
                )
                logger.info(f"[OCR/HTR] OCR: {len(ocr_results)} résultats, HTR: {len(htr_results)} résultats")
            
            else:  # printed
                logger.info("[OCR/HTR] Exécution OCR seulement")
                ocr_results = await self.ocr_engine.extract_with_confidence(
                    image, code_roi_tuple
                )
                logger.info(f"[OCR/HTR] OCR a retourné {len(ocr_results)} résultats")
                
                # DEBUG: Afficher résultats OCR
                if ocr_results:
                    for i, r in enumerate(ocr_results[:3]):
                        logger.info(f"  OCR[{i}]: '{r.get('text', '')[:30]}' (conf: {r.get('confidence', 0):.2f})")
            
            return ocr_results, htr_results
            
        except Exception as e:
            logger.error(f"Erreur dans OCR/HTR: {e}")
            import traceback
            traceback.print_exc()
            return [], []
    
    async def _process_single_page(self, page: Dict, session_path: Path) -> Dict:
        """معالجة صفحة واحدة مع جميع التحسينات - DAM Edition"""
        try:
            image = page['image']
            settings = page.get('file_settings', {})
            doc_type = settings.get('document_type', 'printed')
            roi_areas = settings.get('roi_areas', [])
            keyword = settings.get('keyword', None)
            
            logger.info(f"==== Début traitement page {page.get('page_number')} de {page.get('source_file')} ====")
            logger.info(f"Paramètres: doc_type={doc_type}, keyword={keyword}, roi_areas={len(roi_areas)}")
            
            # Étape 1: Vérification qualité
            blur_check = await self.image_enhancer.check_blur(image)
            logger.info(f"Qualité image: {blur_check['quality']} (score: {blur_check['blur_score']:.1f})")
            
            # Étape 2: Correction orientation
            oriented_image = await self.image_enhancer.rotate_if_needed(image)
            
            # Étape 3: Amélioration image
            enhancement_level = 'high' if doc_type == 'handwritten' else 'medium'
            enhanced_image = await self.image_enhancer.enhance(oriented_image, enhancement_level)
            
            # Étape 4: Extraction ROIs
            code_roi = None
            keyword_roi = None
            child_marker_roi = None
            
            for roi in roi_areas:
                if roi.get('type') == 'code':
                    code_roi = {
                        'x': int(roi['x']),
                        'y': int(roi['y']),
                        'width': int(roi['width']),
                        'height': int(roi['height'])
                    }
                elif roi.get('type') == 'keyword':
                    keyword_roi = {
                        'x': int(roi['x']),
                        'y': int(roi['y']),
                        'width': int(roi['width']),
                        'height': int(roi['height'])
                    }
                elif roi.get('type') == 'child_marker':
                    child_marker_roi = {
                        'x': int(roi['x']),
                        'y': int(roi['y']),
                        'width': int(roi['width']),
                        'height': int(roi['height'])
                    }
            
            logger.info(f"ROI code: {code_roi}, keyword: {keyword}")
            
            # Étape 5: Extraction du code avec retry
            code_result = await self._extract_code_with_retry(
                enhanced_image, 
                code_roi, 
                keyword_roi,
                keyword,
                doc_type
            )
            
            # Extraction sécurisée des résultats
            code = code_result.get('code') if code_result else None
            confidence = float(code_result.get('confidence', 0.0)) if code_result else 0.0
            extraction_method = code_result.get('method', 'unknown') if code_result else 'unknown'
            status = code_result.get('status', 'failed') if code_result else 'failed'
            
            logger.info(f"Résultat extraction - code: {code}, confiance: {confidence:.2f}, méthode: {extraction_method}, status: {status}")
            
            # 🔄 Auto-Recovery si nécessaire
            decision_log = []
            recovery_used = False
            
            if status not in ['accepted', 'validation_rejected'] or confidence < 0.6:
                logger.warning(f"[AUTO-RECOVERY] Déclenchement recovery pour page {page.get('page_number')}")
                
                recovery_result = await self.auto_recovery.recover_code(
                    page, 
                    oriented_image,
                    settings
                )
                
                if recovery_result.get('success'):
                    code = recovery_result['code']
                    confidence = recovery_result['confidence']
                    extraction_method = recovery_result['method']
                    decision_log = recovery_result.get('decision_log', [])
                    recovery_used = True
                    
                    logger.info(f"[AUTO-RECOVERY] ✓ Recovery réussi: {code} (confiance: {confidence})")
                else:
                    logger.warning(f"[AUTO-RECOVERY] Échec recovery")
                    decision_log = recovery_result.get('decision_log', [])
            
            # Sauvegarde image ROI
            code_image_url = None
            if code and code != 'NO_CODE' and code_roi:
                roi_dir = session_path / 'roi_images'
                roi_dir.mkdir(exist_ok=True)
                
                roi_tuple = roi_to_tuple(code_roi)
                if roi_tuple:
                    try:
                        x1, y1, x2, y2 = roi_tuple
                        roi_image = enhanced_image.crop((x1, y1, x2, y2))
                        roi_path = roi_dir / f"{page['page_id']}_code.png"
                        roi_image.save(roi_path)
                        code_image_url = f"/results/{session_path.name}/roi_images/{page['page_id']}_code.png"
                        logger.info(f"ROI image sauvegardée: {roi_path}")
                    except Exception as e:
                        logger.error(f"Erreur sauvegarde ROI: {e}")
            
            # Détection page markers
            page_marker = None
            ocr_text = ""
            
            if child_marker_roi:
                roi_tuple = roi_to_tuple(child_marker_roi)
                if roi_tuple:
                    marker_results = await self.ocr_engine.extract_with_confidence(enhanced_image, roi_tuple)
                    
                    ocr_text = " ".join([r.get('text', '') for r in marker_results])
                    
                    detected_marker = await self.page_analyzer.detect_page_markers(ocr_text)
                    if detected_marker:
                        page_marker = f"{detected_marker['current_page']}/{detected_marker['total_pages']}"
                        logger.info(f"Page marker détecté: {page_marker}")
            
            # 🔧 FALLBACK: Toujours avoir un code (même si DEFAULT)
            if not code or code == 'NO_CODE':
                code = "DEFAULT"
                confidence = confidence or 0.0
                extraction_method = extraction_method or "FALLBACK"
                logger.warning(f"Code fallback utilisé: DEFAULT")
            
            # Sauvegarde résultats
            page['code'] = code
            page['confidence'] = confidence
            page['processed'] = True
            page['output_name'] = settings.get('output_name') or settings.get('outputName') or 'DEFAULT'
            page['keyword'] = settings.get('keyword', '')
            page['code_image_url'] = code_image_url
            page['page_marker'] = page_marker
            page['ocr_text'] = ocr_text
            page['is_main'] = bool(code and code != 'DEFAULT')
            page['is_child'] = not bool(code and code != 'DEFAULT')
            page['parent_code'] = None
            
            logger.info(f"Page {page['page_number']}: code={code}, output={page['output_name']}, confiance={confidence:.2f}, méthode={extraction_method}")
            
            # Informations de traitement
            page['blur_check'] = blur_check
            page['extraction_method'] = extraction_method
            page['extraction_status'] = status
            page['recovery_used'] = recovery_used
            page['decision_log'] = decision_log
            
            # Suppression image pour économiser mémoire
            if 'image' in page:
                del page['image']
            
            return page
            
        except Exception as e:
            logger.error(f"Erreur traitement page: {e}")
            import traceback
            traceback.print_exc()
            
            page['code'] = None
            page['processed'] = False
            page['error'] = str(e)
            page['confidence'] = 0.0
            page['output_name'] = 'ERROR'
            page['is_main'] = False
            page['is_child'] = False
            
            if 'image' in page:
                del page['image']
            
            return page