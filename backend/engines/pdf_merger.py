import fitz
from pathlib import Path
import logging
from typing import List, Dict
import json

logger = logging.getLogger(__name__)

class PDFMerger:
    """محرك دمج PDF - دمج الصفحات وإنشاء PDF جديد بالهيكل الصحيح"""
    
    def __init__(self):
        pass
    
    async def merge_final(self, code_groups: List[Dict], merged_files: List[str], 
                         output_dir: Path) -> Dict:
        """التجميع النهائي حسب الهيكل: P{code}/ مع P{code}-{nom}.pdf و P{code}-PV-{nom}.pdf"""
        try:
            created_files = []
            
            # استخدام المسار الصحيح: /app/codes
            base_output_dir = Path('/app/codes')
            base_output_dir.mkdir(parents=True, exist_ok=True)
            
            for group in code_groups:
                code = group['code']
                pages = group['pages']
                output_names = group.get('output_names', [])
                
                if not code or code == 'NO_CODE':
                    logger.warning("تخطي كود فارغ")
                    continue
                
                # إنشاء مجلد الكود
                code_dir = base_output_dir / f"P{code}"
                code_dir.mkdir(parents=True, exist_ok=True)
                
                # تجميع الصفحات حسب output_name و source_file
                files_by_name = {}
                pv_files_by_name = {}
                
                for page in pages:
                    output_name = page.get('output_name', 'DEFAULT')
                    source_file = page.get('source_file', '')
                    
                    # تحديد إذا كان ملف PV
                    is_pv = source_file in merged_files
                    
                    if is_pv:
                        if output_name not in pv_files_by_name:
                            pv_files_by_name[output_name] = []
                        pv_files_by_name[output_name].append(page)
                    else:
                        if output_name not in files_by_name:
                            files_by_name[output_name] = []
                        files_by_name[output_name].append(page)
                
                # إنشاء الملفات العادية
                for output_name, output_pages in files_by_name.items():
                    pdf_path = await self._create_pdf(
                        pages=output_pages,
                        output_path=code_dir / f"P{code}-{output_name}.pdf",
                        code=code,
                        name=output_name
                    )
                    if pdf_path:
                        created_files.append({
                            'code': code,
                            'filename': f"P{code}-{output_name}.pdf",
                            'path': str(pdf_path),
                            'type': 'normal',
                            'pages_count': len(output_pages)
                        })
                
                # إنشاء ملفات PV
                for output_name, output_pages in pv_files_by_name.items():
                    pdf_path = await self._create_pdf(
                        pages=output_pages,
                        output_path=code_dir / f"P{code}-PV-{output_name}.pdf",
                        code=code,
                        name=output_name
                    )
                    if pdf_path:
                        created_files.append({
                            'code': code,
                            'filename': f"P{code}-PV-{output_name}.pdf",
                            'path': str(pdf_path),
                            'type': 'pv',
                            'pages_count': len(output_pages)
                        })
            
            # إنشاء تقرير
            report = {
                'total_files': len(created_files),
                'total_codes': len(set(f['code'] for f in created_files)),
                'files': created_files
            }
            
            report_path = base_output_dir / 'merge_report.json'
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            logger.info(f"تم إنشاء {len(created_files)} ملف في {len(set(f['code'] for f in created_files))} مجلد")
            
            return {
                'success': True,
                'files': created_files,
                'report': report
            }
            
        except Exception as e:
            logger.error(f"خطأ في التجميع النهائي: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _create_pdf(self, pages: List[Dict], output_path: Path, 
                         code: str, name: str) -> Path:
        """إنشاء ملف PDF واحد من مجموعة صفحات"""
        try:
            pdf_output = fitz.open()
            
            # ترتيب الصفحات: الرئيسية أولاً ثم التابعة
            sorted_pages = sorted(pages, key=lambda p: (
                0 if p.get('is_main') else 1,
                p.get('page_number', 0)
            ))
            
            for page_data in sorted_pages:
                original_path = page_data.get('original_file_path')
                if not original_path or not Path(original_path).exists():
                    logger.warning(f"الملف غير موجود: {original_path}")
                    continue
                
                try:
                    src_pdf = fitz.open(original_path)
                    page_num = page_data.get('original_page_number', 0)
                    
                    if page_num < len(src_pdf):
                        pdf_output.insert_pdf(src_pdf, from_page=page_num, to_page=page_num)
                    
                    src_pdf.close()
                except Exception as e:
                    logger.error(f"خطأ في إضافة الصفحة: {e}")
                    continue
            
            if len(pdf_output) > 0:
                # إضافة metadata
                pdf_output.set_metadata({
                    'title': f"P{code}-{name}",
                    'author': 'ScanFlow Pro V7',
                    'subject': f'Code: {code}, Name: {name}',
                    'keywords': f'{code}, {name}, ScanFlow'
                })
                
                pdf_output.save(str(output_path), deflate=True)
                pdf_output.close()
                
                logger.info(f"تم إنشاء {output_path} ({len(sorted_pages)} صفحة)")
                return output_path
            else:
                logger.warning(f"لا توجد صفحات لـ {output_path}")
                return None
                
        except Exception as e:
            logger.error(f"خطأ في إنشاء PDF: {e}")
            return None
    
    async def create_report(self, grouped_pages: List[Dict], output_dir: Path) -> Dict:
        """إنشاء تقرير شامل للنتائج"""
        try:
            report = {
                'total_codes': len(grouped_pages),
                'total_pages': sum(len(g['pages']) for g in grouped_pages),
                'codes': []
            }
            
            for group in grouped_pages:
                code_info = {
                    'code': group['code'],
                    'total_pages': len(group['pages']),
                    'main_pages': len([p for p in group['pages'] if p.get('is_main')]),
                    'child_pages': len([p for p in group['pages'] if p.get('is_child')]),
                    'output_names': list(set(p.get('output_name', 'DEFAULT') for p in group['pages'])),
                    'pages_list': [
                        {
                            'page_number': p.get('page_number'),
                            'is_main': p.get('is_main', False),
                            'original_file': p.get('source_file'),
                            'output_name': p.get('output_name')
                        } for p in group['pages']
                    ]
                }
                report['codes'].append(code_info)
            
            report_path = output_dir / 'analysis_report.json'
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            logger.info(f"تم إنشاء التقرير في {report_path}")
            return report
            
        except Exception as e:
            logger.error(f"خطأ في إنشاء التقرير: {e}")
            return {}
