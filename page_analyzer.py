import logging
from typing import List, Dict, Optional
import re

logger = logging.getLogger(__name__)

class PageAnalyzer:
    """محلل الصفحات المتقدم - يدعم 5 أنواع من منطق الصفحات التابعة"""
    
    def __init__(self):
        self.page_marker_patterns = [
            r'(\d+)\s*/\s*(\d+)',  # 1/3, 2/3
            r'Page\s+(\d+)\s+of\s+(\d+)',  # Page 1 of 3
            r'Pg\s+(\d+)/(\d+)',  # Pg 1/3
        ]
    
    async def analyze_pages(self, 
                           pages_data: List[Dict],
                           child_pages_mode: str = 'auto',
                           fixed_child_count: int = 0) -> List[Dict]:
        """
        تحليل الصفحات وتحديد التابعة منها
        
        Args:
            pages_data: قائمة الصفحات
            child_pages_mode: 'auto' | 'fixed' | 'marker' | 'none'
            fixed_child_count: عدد الصفحات التابعة الثابتة
        
        Returns:
            قائمة مجموعات الصفحات
        """
        try:
            if child_pages_mode == 'none':
                # النوع 1: لا توجد صفحات تابعة
                return await self._analyze_no_children(pages_data)
            
            elif child_pages_mode == 'fixed':
                # النوع 3: صفحات تابعة ثابتة
                return await self._analyze_fixed_children(pages_data, fixed_child_count)
            
            elif child_pages_mode == 'marker':
                # النوع 4: صفحات مرقمة (1/3, 2/3)
                return await self._analyze_marker_children(pages_data)
            
            elif child_pages_mode == 'dynamic':
                # النوع 5: صفحات تابعة غير ثابتة
                return await self._analyze_dynamic_children(pages_data)
            
            else:  # auto
                # محاولة كشف تلقائي
                return await self._analyze_auto(pages_data)
                
        except Exception as e:
            logger.error(f"خطأ في تحليل الصفحات: {e}")
            return []
    
    async def _analyze_no_children(self, pages_data: List[Dict]) -> List[Dict]:
        """النوع 1: لا توجد صفحات تابعة - كل صفحة main"""
        grouped_pages = []
        
        for page in pages_data:
            code = page.get('code')
            if code:
                page['is_main'] = True
                page['is_child'] = False
                page['parent_code'] = None
                
                grouped_pages.append({
                    'code': code,
                    'pages': [page],
                    'main_page': page,
                    'child_pages': []
                })
        
        logger.info(f"[NO_CHILDREN] تم تحليل {len(grouped_pages)} صفحة رئيسية")
        return grouped_pages
    
    async def _analyze_fixed_children(self, pages_data: List[Dict], count: int) -> List[Dict]:
        """النوع 3: صفحات تابعة ثابتة (مثلاً 1 صفحة تابعة لكل main)"""
        grouped_pages = []
        i = 0
        
        while i < len(pages_data):
            page = pages_data[i]
            code = page.get('code')
            
            if code:
                # صفحة رئيسية
                page['is_main'] = True
                page['is_child'] = False
                page['parent_code'] = None
                
                group = {
                    'code': code,
                    'pages': [page],
                    'main_page': page,
                    'child_pages': []
                }
                
                # أخذ الصفحات التابعة الثابتة
                for j in range(1, count + 1):
                    if i + j < len(pages_data):
                        child_page = pages_data[i + j]
                        child_page['is_main'] = False
                        child_page['is_child'] = True
                        child_page['parent_code'] = code
                        child_page['code'] = code  # نفس الكود
                        
                        group['pages'].append(child_page)
                        group['child_pages'].append(child_page)
                
                grouped_pages.append(group)
                i += count + 1  # تخطي الصفحات التابعة
            else:
                i += 1
        
        logger.info(f"[FIXED_CHILDREN] تم تحليل {len(grouped_pages)} مجموعة بصفحات تابعة ثابتة")
        return grouped_pages
    
    async def _analyze_marker_children(self, pages_data: List[Dict]) -> List[Dict]:
        """النوع 4: صفحات مرقمة (1/3, 2/3, 3/3)"""
        grouped_pages = []
        current_group = None
        
        for page in pages_data:
            # محاولة اكتشاف page marker
            marker = await self.detect_page_markers(page.get('ocr_text', ''))
            
            if marker:
                current_page = marker['current_page']
                total_pages = marker['total_pages']
                
                if current_page == 1:
                    # بداية مجموعة جديدة
                    if current_group:
                        grouped_pages.append(current_group)
                    
                    code = page.get('code')
                    page['is_main'] = True
                    page['is_child'] = False
                    page['parent_code'] = None
                    page['page_marker'] = f"{current_page}/{total_pages}"
                    
                    current_group = {
                        'code': code,
                        'pages': [page],
                        'main_page': page,
                        'child_pages': [],
                        'expected_total': total_pages
                    }
                else:
                    # صفحة تابعة
                    if current_group:
                        page['is_main'] = False
                        page['is_child'] = True
                        page['parent_code'] = current_group['code']
                        page['code'] = current_group['code']  # نفس الكود
                        page['page_marker'] = f"{current_page}/{total_pages}"
                        
                        current_group['pages'].append(page)
                        current_group['child_pages'].append(page)
            else:
                # بدون marker - افتراض صفحة رئيسية
                if current_group:
                    grouped_pages.append(current_group)
                
                code = page.get('code')
                if code:
                    page['is_main'] = True
                    page['is_child'] = False
                    page['parent_code'] = None
                    
                    current_group = {
                        'code': code,
                        'pages': [page],
                        'main_page': page,
                        'child_pages': []
                    }
        
        if current_group:
            grouped_pages.append(current_group)
        
        logger.info(f"[MARKER_CHILDREN] تم تحليل {len(grouped_pages)} مجموعة بصفحات مرقمة")
        return grouped_pages
    
    async def _analyze_dynamic_children(self, pages_data: List[Dict]) -> List[Dict]:
        """النوع 5: صفحات تابعة غير ثابتة (الأصعب)"""
        grouped_pages = []
        current_group = None
        
        for i, page in enumerate(pages_data):
            code = page.get('code')
            
            # إذا وجدنا كود، هذه صفحة رئيسية
            if code and code != 'NO_CODE':
                # حفظ المجموعة السابقة
                if current_group:
                    grouped_pages.append(current_group)
                
                # بدء مجموعة جديدة
                page['is_main'] = True
                page['is_child'] = False
                page['parent_code'] = None
                
                current_group = {
                    'code': code,
                    'pages': [page],
                    'main_page': page,
                    'child_pages': []
                }
            
            # إذا لم نجد كود، نحدد هل هي تابعة أم لا
            else:
                if current_group:
                    # فحص: هل هذه صفحة تابعة؟
                    is_child = await self._is_likely_child_page(page, current_group['main_page'], i, pages_data)
                    
                    if is_child:
                        page['is_main'] = False
                        page['is_child'] = True
                        page['parent_code'] = current_group['code']
                        page['code'] = current_group['code']
                        
                        current_group['pages'].append(page)
                        current_group['child_pages'].append(page)
                    else:
                        # ليست تابعة - صفحة منفصلة
                        page['is_main'] = False
                        page['is_child'] = False
                        page['code'] = 'NO_CODE'
                else:
                    # لا يوجد مجموعة حالية
                    page['is_main'] = False
                    page['is_child'] = False
                    page['code'] = 'NO_CODE'
        
        if current_group:
            grouped_pages.append(current_group)
        
        logger.info(f"[DYNAMIC_CHILDREN] تم تحليل {len(grouped_pages)} مجموعة بصفحات ديناميكية")
        return grouped_pages
    
    async def _is_likely_child_page(self, page: Dict, main_page: Dict, index: int, all_pages: List[Dict]) -> bool:
        """
        تحديد احتمالية كون الصفحة تابعة
        
        معايير:
        1. تأتي مباشرة بعد main أو بعد child آخر
        2. نفس الملف المصدر
        3. نفس نمط الوثيقة
        4. لا يوجد فاصل واضح
        """
        try:
            # معيار 1: الموقع (يجب أن تكون قريبة)
            if index > 0:
                prev_page = all_pages[index - 1]
                if prev_page.get('parent_code') != main_page.get('code') and prev_page != main_page:
                    return False
            
            # معيار 2: نفس الملف المصدر
            if page.get('source_file') != main_page.get('source_file'):
                return False
            
            # معيار 3: لا يوجد كود واضح
            if page.get('code') and page.get('code') != 'NO_CODE':
                return False
            
            # معيار 4: لا يوجد page marker جديد يشير لبداية مجموعة
            marker = await self.detect_page_markers(page.get('ocr_text', ''))
            if marker and marker['current_page'] == 1:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"خطأ في تحديد الصفحة التابعة: {e}")
            return False
    
    async def _analyze_auto(self, pages_data: List[Dict]) -> List[Dict]:
        """محاولة كشف تلقائي لنوع الصفحات التابعة"""
        # محاولة اكتشاف page markers
        has_markers = False
        for page in pages_data:
            marker = await self.detect_page_markers(page.get('ocr_text', ''))
            if marker:
                has_markers = True
                break
        
        if has_markers:
            logger.info("[AUTO] اكتشفنا page markers - استخدام MARKER mode")
            return await self._analyze_marker_children(pages_data)
        
        # افتراضياً: استخدام dynamic
        logger.info("[AUTO] استخدام DYNAMIC mode")
        return await self._analyze_dynamic_children(pages_data)
    
    async def detect_page_markers(self, text: str) -> Optional[Dict]:
        """اكتشاف علامات الصفحات مثل 1/3, 2/3"""
        try:
            if not text:
                return None
            
            for pattern in self.page_marker_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    current, total = matches[0]
                    return {
                        'current_page': int(current),
                        'total_pages': int(total),
                        'is_multi_page': True,
                        'pattern': pattern
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"خطأ في اكتشاف علامات الصفحات: {e}")
            return None
    
    def reorder_pages_in_group(self, pages: List[Dict], new_order: List[int]) -> List[Dict]:
        """إعادة ترتيب الصفحات داخل مجموعة"""
        try:
            if len(new_order) != len(pages):
                logger.error("عدد الترتيب لا يتطابق مع عدد الصفحات")
                return pages
            
            reordered = [pages[i] for i in new_order]
            logger.info(f"تم إعادة ترتيب {len(pages)} صفحة")
            return reordered
            
        except Exception as e:
            logger.error(f"خطأ في إعادة الترتيب: {e}")
            return pages
