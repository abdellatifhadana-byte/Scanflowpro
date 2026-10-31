from fastapi import FastAPI, UploadFile, File, Form, WebSocket, WebSocketDisconnect, HTTPException, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from dotenv import load_dotenv
import os
import logging
import json
import aiofiles
from typing import List
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict
import sys
sys.path.append('/app/backend')

from managers.smart_session_manager import get_smart_session_manager
from managers.processing_orchestrator import ProcessingOrchestrator
from managers.session_lock_manager import get_session_lock_manager
from models import (
    SessionCreate, SessionResponse, ProcessingStatus,
    UpdatePageRequest, MergeRequest, PageResult, CodeGroup
)

# إعداد
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# إنشاء FastAPI app
app = FastAPI(title="ScanFlow Pro V7")
api_router = APIRouter(prefix="/api")

# Managers
session_manager = get_smart_session_manager()
orchestrator = ProcessingOrchestrator()
lock_manager = get_session_lock_manager()

# WebSocket connections
active_connections: dict = {}

# تكوين Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Models
class SessionCreate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    batch_name: str
    document_type: str = "printed"  # printed, handwritten, mixed
    turbo_mode: bool = False
    child_pages_mode: str = "auto"  # auto, manual, none
    
class SessionResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    session_id: str
    status: str
    message: str

class ProcessingStatus(BaseModel):
    model_config = ConfigDict(extra="ignore")
    session_id: str
    status: str
    progress: float
    stage: str
    message: str

# API Routes
@api_router.get("/")
async def root():
    return {
        "message": "ScanFlow Pro V7 API",
        "version": "7.0.0",
        "status": "running"
    }

@api_router.post("/session/create", response_model=SessionResponse)
async def create_session(session_data: SessionCreate):
    """إنشاء جلسة جديدة"""
    try:
        settings = session_data.model_dump()
        
        # SmartSessionManager يتعامل مع الفروقات تلقائياً
        session_id = await session_manager.create_session(
            batch_name=session_data.batch_name,
            settings=settings
        )
        
        logger.info(f"✓ Session créée: {session_id}")
        
        return SessionResponse(
            session_id=session_id,
            status="created",
            message="تم إنشاء الجلسة بنجاح"
        )
    except Exception as e:
        logger.error(f"❌ Erreur création session: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/session/{session_id}/upload")
async def upload_files(
    session_id: str,
    files: List[UploadFile] = File(...)
):
    """رفع ملفات PDF"""
    try:
        session = await session_manager.get_session(session_id)
        if not session:
            return {"error": "الجلسة غير موجودة"}
        
        upload_dir = session_manager.get_session_path(session_id, 'uploads')
        uploaded_files = []
        
        for file in files:
            file_path = upload_dir / file.filename
            
            # حفظ الملف
            async with aiofiles.open(file_path, 'wb') as f:
                content = await file.read()
                await f.write(content)
            
            uploaded_files.append({
                'filename': file.filename,
                'path': str(file_path),
                'size': len(content)
            })
        
        # تحديث الجلسة
        await session_manager.update_session(session_id, {
            'files': uploaded_files,
            'status': 'files_uploaded'
        })
        
        logger.info(f"تم رفع {len(uploaded_files)} ملف للجلسة {session_id}")
        
        return {
            'success': True,
            'files_count': len(uploaded_files),
            'files': uploaded_files
        }
        
    except Exception as e:
        logger.error(f"خطأ في رفع الملفات: {e}")
        return {"error": str(e)}

@api_router.put("/session/{session_id}/file-settings")
async def update_file_settings(session_id: str, settings_data: dict):
    """تحديث إعدادات الملفات بعد الرفع"""
    try:
        session = await session_manager.get_session(session_id)
        if not session:
            return {"error": "الجلسة غير موجودة"}
        
        file_settings = settings_data.get('file_settings', [])
        
        # تحديث session بإعدادات الملفات
        current_settings = session.get('settings', {})
        current_settings['file_settings'] = file_settings
        
        await session_manager.update_session(session_id, {
            'settings': current_settings,
            'updated_at': datetime.now(timezone.utc).isoformat()
        })
        
        logger.info(f"✓ تم تحديث إعدادات {len(file_settings)} ملف للجلسة {session_id}")
        
        return {
            'success': True,
            'message': f'تم تحديث إعدادات {len(file_settings)} ملف',
            'file_settings_count': len(file_settings)
        }
        
    except Exception as e:
        logger.error(f"خطأ في تحديث إعدادات الملفات: {e}")
        return {"error": str(e)}

@api_router.post("/session/{session_id}/process")
async def start_processing(session_id: str):
    """بدء معالجة الملفات مع Session Lock"""
    try:
        # Vérifier si la session existe
        session = await session_manager.get_session(session_id)
        if not session:
            return {"error": "الجلسة غير موجودة"}
        
        # Vérifier l'état de la session
        current_status = session.get('status')
        if current_status == 'processing':
            return {
                "error": "المعالجة جارية بالفعل",
                "status": "already_processing"
            }
        
        if current_status == 'completed':
            return {
                "error": "تمت معالجة هذه الجلسة بالفعل",
                "status": "already_completed"
            }
        
        # Vérifier si la session est verrouillée
        if lock_manager.is_locked(session_id):
            return {
                "error": "الجلسة مقفلة - المعالجة جارية",
                "status": "locked"
            }
        
        # تحديث حالة الجلسة
        await session_manager.update_session(session_id, {
            'status': 'processing',
            'started_at': datetime.now(timezone.utc).isoformat()
        })
        
        # Créer et enregistrer la tâche de traitement
        import asyncio
        task = asyncio.create_task(
            process_session_files(session_id, session)
        )
        lock_manager.register_task(session_id, task)
        
        logger.info(f"🚀 Processing started for session {session_id}")
        
        return {
            'success': True,
            'message': 'بدأت المعالجة',
            'session_id': session_id
        }
        
    except Exception as e:
        logger.error(f"خطأ في بدء المعالجة: {e}")
        return {"error": str(e)}

@api_router.post("/session/{session_id}/cancel")
async def cancel_processing(session_id: str):
    """إلغاء معالجة الجلسة - Real Cancel with Task Cancellation"""
    try:
        session = await session_manager.get_session(session_id)
        if not session:
            return {"error": "الجلسة غير موجودة"}
        
        # Annuler la tâche de traitement
        cancelled = await lock_manager.cancel_task(session_id)
        
        if not cancelled:
            logger.warning(f"⚠️ Could not cancel task for session {session_id} (may already be done)")
        
        # تحديث حالة الجلسة إلى ملغاة
        await session_manager.update_session(session_id, {
            'status': 'cancelled',
            'cancelled_at': datetime.now(timezone.utc).isoformat()
        })
        
        # Nettoyer les ressources
        lock_manager.cleanup_session(session_id)
        
        logger.info(f"🛑 Session {session_id} cancelled successfully (task_cancelled={cancelled})")
        
        return {
            'success': True,
            'message': 'تم إلغاء المعالجة بنجاح',
            'session_id': session_id,
            'task_cancelled': cancelled
        }
        
    except Exception as e:
        logger.error(f"خطأ في إلغاء المعالجة: {e}")
        return {"error": str(e)}

async def process_session_files(session_id: str, session: dict):
    """معالجة ملفات الجلسة مع Support للإلغاء"""
    lock = lock_manager.get_lock(session_id)
    
    try:
        # Acquérir le lock
        async with lock:
            logger.info(f"🔒 Lock acquired for session {session_id}")
            
            # Checkpoint: Vérifier si annulé
            import asyncio
            await asyncio.sleep(0)
            
            files_paths = [f['path'] for f in session['files']]
            file_settings_list = session.get('settings', {}).get('file_settings', [])
            
            # تحويل القائمة إلى dict حسب اسم الملف
            file_settings_dict = {}
            for settings in file_settings_list:
                filename = settings.get('filename')
                if filename:
                    file_settings_dict[filename] = settings
            
            async def progress_callback(data):
                # Checkpoint: Vérifier si annulé
                await asyncio.sleep(0)
                
                # تحديث تقدم الجلسة
                await session_manager.update_session(session_id, {
                    'progress': data.get('progress', 0),
                    'current_stage': data.get('stage', 'processing')
                })
                
                # إرسال التحديثات عبر WebSocket
                if session_id in active_connections:
                    try:
                        await active_connections[session_id].send_json(data)
                    except:
                        pass
            
            # معالجة الملفات
            session_path = session_manager.get_session_path(session_id)
            results = await orchestrator.process_files(
                files_paths=files_paths,
                file_settings=file_settings_dict,
                session_path=session_path,
                progress_callback=progress_callback
            )
        
        if results['success']:
            # إنشاء تقرير
            results_dir = session_manager.get_session_path(session_id, 'results')
            report = await orchestrator.pdf_merger.create_report(
                results['code_groups'], results_dir
            )
            
            # تحديث الجلسة
            await session_manager.update_session(session_id, {
                'status': 'completed',
                'pages': results['pages'],
                'code_groups': results['code_groups'],
                'report': report,
                'progress': 100,
                'completed_at': datetime.now(timezone.utc).isoformat()
            })
            
            # إرسال إشعار الانتهاء
            if session_id in active_connections:
                try:
                    await active_connections[session_id].send_json({
                        'stage': 'completed',
                        'progress': 100,
                        'total_codes': results['total_codes'],
                        'total_pages': results['total_pages'],
                        'report': report
                    })
                except:
                    pass
        else:
            await session_manager.update_session(session_id, {
                'status': 'failed',
                'error': results.get('error', 'Unknown error')
            })
            
    except asyncio.CancelledError:
        # L'annulation a été demandée
        logger.info(f"🛑 Processing cancelled for session {session_id}")
        await session_manager.update_session(session_id, {
            'status': 'cancelled',
            'cancelled_at': datetime.now(timezone.utc).isoformat()
        })
        raise  # Re-raise pour propagation
        
    except Exception as e:
        logger.error(f"خطأ في معالجة الجلسة: {e}")
        import traceback
        traceback.print_exc()
        await session_manager.update_session(session_id, {
            'status': 'failed',
            'error': str(e)
        })
    
    finally:
        # Toujours nettoyer le lock
        lock_manager.cleanup_session(session_id)
        logger.info(f"🧹 Cleaned up session {session_id}")

@api_router.get("/session/{session_id}/status")
async def get_session_status(session_id: str):
    """الحصول على حالة الجلسة"""
    try:
        session = await session_manager.get_session(session_id)
        if not session:
            return {"error": "الجلسة غير موجودة"}
        
        return {
            'session_id': session_id,
            'status': session.get('status'),
            'progress': session.get('progress', 0),
            'results': session.get('results', []),
            'report': session.get('report', {})
        }
    except Exception as e:
        logger.error(f"خطأ في الحصول على الحالة: {e}")
        return {"error": str(e)}

@api_router.post("/pdf/first-page")
async def get_pdf_first_page(file: UploadFile = File(...)):
    """استخراج الصفحة الأولى من PDF كصورة"""
    try:
        import fitz
        from fastapi.responses import Response
        
        # قراءة الملف
        pdf_bytes = await file.read()
        
        # فتح PDF
        pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        
        if len(pdf_doc) == 0:
            return {"error": "الملف فارغ"}
        
        # استخراج الصفحة الأولى
        first_page = pdf_doc[0]
        
        # تحويل إلى صورة
        mat = fitz.Matrix(2, 2)  # تكبير 2x
        pix = first_page.get_pixmap(matrix=mat)
        
        # تحويل إلى PNG
        img_data = pix.tobytes("png")
        
        pdf_doc.close()
        
        # إرجاع الصورة كـ blob
        return Response(content=img_data, media_type="image/png")
        
    except Exception as e:
        logger.error(f"خطأ في استخراج الصفحة الأولى: {e}")
        return {"error": str(e)}

@api_router.post("/pdf/info")
async def get_pdf_info(file: UploadFile = File(...)):
    """الحصول على معلومات PDF (عدد الصفحات، الحجم، الخ)"""
    try:
        import fitz
        
        # قراءة الملف
        pdf_bytes = await file.read()
        
        # فتح PDF
        pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        
        page_count = len(pdf_doc)
        
        # معلومات إضافية
        metadata = pdf_doc.metadata
        
        pdf_doc.close()
        
        return {
            'success': True,
            'page_count': page_count,
            'file_size': len(pdf_bytes),
            'metadata': metadata
        }
        
    except Exception as e:
        logger.error(f"خطأ في الحصول على معلومات PDF: {e}")
        return {"error": str(e), "page_count": 0}

@api_router.get("/session/{session_id}/results")
async def get_results(session_id: str):
    """الحصول على نتائج الجلسة"""
    try:
        session = await session_manager.get_session(session_id)
        if not session:
            return {"error": "الجلسة غير موجودة"}
        
        return {
            'session_id': session_id,
            'status': session.get('status'),
            'results': session.get('results', []),
            'report': session.get('report', {}),
            'pages': session.get('pages', []),
            'code_groups': session.get('code_groups', [])
        }
    except Exception as e:
        logger.error(f"خطأ في الحصول على النتائج: {e}")
        return {"error": str(e)}

@api_router.put("/session/{session_id}/page")
async def update_page(session_id: str, update: UpdatePageRequest):
    """تحديث بيانات صفحة"""
    try:
        session = await session_manager.get_session(session_id)
        if not session:
            return {"error": "الجلسة غير موجودة"}
        
        pages = session.get('pages', [])
        updated = False
        
        for page in pages:
            if page.get('page_id') == update.page_id:
                if update.code is not None:
                    page['code'] = update.code
                if update.output_name is not None:
                    page['output_name'] = update.output_name
                if update.is_child is not None:
                    page['is_child'] = update.is_child
                    page['is_main'] = not update.is_child
                updated = True
                break
        
        if updated:
            await session_manager.update_session(session_id, {'pages': pages})
            return {'success': True, 'message': 'تم التحديث بنجاح'}
        else:
            return {'error': 'الصفحة غير موجودة'}
            
    except Exception as e:
        logger.error(f"خطأ في تحديث الصفحة: {e}")
        return {"error": str(e)}

@api_router.delete("/session/{session_id}/page/{page_id}")
async def delete_page(session_id: str, page_id: str):
    """حذف صفحة"""
    try:
        session = await session_manager.get_session(session_id)
        if not session:
            return {"error": "الجلسة غير موجودة"}
        
        pages = session.get('pages', [])
        pages = [p for p in pages if p.get('page_id') != page_id]
        
        await session_manager.update_session(session_id, {'pages': pages})
        return {'success': True, 'message': 'تم الحذف بنجاح'}
        
    except Exception as e:
        logger.error(f"خطأ في حذف الصفحة: {e}")
        return {"error": str(e)}

@api_router.post("/session/{session_id}/merge-final")
async def merge_final(session_id: str, merge_request: MergeRequest):
    """التجميع النهائي للملفات"""
    try:
        session = await session_manager.get_session(session_id)
        if not session:
            return {"error": "الجلسة غير موجودة"}
        
        results_dir = session_manager.get_session_path(session_id, 'results')
        
        # تحويل MergeRequest إلى dict
        code_groups_dict = []
        for group in merge_request.code_groups:
            pages_dict = []
            for page in group.pages:
                pages_dict.append({
                    'page_id': page.page_id,
                    'page_number': page.page_number,
                    'code': page.code,
                    'output_name': page.output_name,
                    'source_file': page.source_file,
                    'is_main': page.is_main,
                    'is_child': page.is_child,
                    'original_file_path': page.get('original_file_path'),
                    'original_page_number': page.get('original_page_number', 0)
                })
            
            code_groups_dict.append({
                'code': group.code,
                'pages': pages_dict,
                'output_names': group.output_names,
                'merged_files': group.merged_files
            })
        
        # تنفيذ التجميع الفعلي
        merge_result = await orchestrator.pdf_merger.merge_final(
            code_groups=code_groups_dict,
            merged_files=merge_request.code_groups[0].merged_files if merge_request.code_groups else [],
            output_dir=results_dir
        )
        
        if merge_result['success']:
            await session_manager.update_session(session_id, {
                'final_files': merge_result['files'],
                'merge_completed': True,
                'merge_report': merge_result['report']
            })
            
            return {
                'success': True,
                'message': f'تم إنشاء {len(merge_result["files"])} ملف بنجاح',
                'files': merge_result['files'],
                'report': merge_result['report']
            }
        else:
            return {
                'success': False,
                'error': merge_result.get('error', 'Unknown error')
            }
        
    except Exception as e:
        logger.error(f"خطأ في التجميع النهائي: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}

@api_router.get("/session/{session_id}/download-zip")
async def download_zip(session_id: str):
    """تحميل جميع ملفات الجلسة كـ ZIP"""
    try:
        import zipfile
        import tempfile
        from fastapi.responses import FileResponse
        
        # الحصول على مسار النتائج
        codes_dir = Path('/app/codes')
        
        if not codes_dir.exists():
            return {"error": "لا توجد ملفات للتحميل"}
        
        # إنشاء ملف ZIP مؤقت
        temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
        
        with zipfile.ZipFile(temp_zip.name, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # إضافة جميع الملفات من /app/codes
            for code_folder in codes_dir.iterdir():
                if code_folder.is_dir():
                    for file in code_folder.rglob('*'):
                        if file.is_file():
                            arcname = file.relative_to(codes_dir)
                            zipf.write(file, arcname)
        
        return FileResponse(
            temp_zip.name,
            media_type='application/zip',
            filename=f'scanflow_results_{session_id[:8]}.zip'
        )
        
    except Exception as e:
        logger.error(f"خطأ في إنشاء ZIP: {e}")
        return {"error": str(e)}

@api_router.post("/session/{session_id}/move-page")
async def move_page(session_id: str, move_data: dict):
    """نقل صفحة من كود إلى كود آخر"""
    try:
        page_id = move_data.get('page_id')
        new_code = move_data.get('new_code')
        
        session = await session_manager.get_session(session_id)
        if not session:
            return {"error": "الجلسة غير موجودة"}
        
        # البحث عن الصفحة وتحديث الكود
        updated = False
        for code, pages in session.get('results', {}).items():
            for page in pages:
                if page.get('page_id') == page_id:
                    page['code'] = new_code
                    page['parent_code'] = new_code if page.get('is_child') else None
                    updated = True
                    break
        
        if updated:
            await session_manager.update_session(session_id, {'results': session['results']})
            return {"success": True, "message": "تم نقل الصفحة بنجاح"}
        else:
            return {"error": "الصفحة غير موجودة"}
            
    except Exception as e:
        logger.error(f"خطأ في نقل الصفحة: {e}")
        return {"error": str(e)}

@api_router.put("/session/{session_id}/change-parent")
async def change_parent(session_id: str, data: dict):
    """تغيير parent_code لصفحة تابعة"""
    try:
        page_id = data.get('page_id')
        new_parent_code = data.get('parent_code')
        
        session = await session_manager.get_session(session_id)
        if not session:
            return {"error": "الجلسة غير موجودة"}
        
        # البحث عن الصفحة وتحديث parent_code
        updated = False
        for code, pages in session.get('results', {}).items():
            for page in pages:
                if page.get('page_id') == page_id:
                    page['parent_code'] = new_parent_code
                    page['code'] = new_parent_code
                    updated = True
                    break
        
        if updated:
            await session_manager.update_session(session_id, {'results': session['results']})
            return {"success": True, "message": "تم تغيير parent_code بنجاح"}
        else:
            return {"error": "الصفحة غير موجودة"}
            
    except Exception as e:
        logger.error(f"خطأ في تغيير parent_code: {e}")
        return {"error": str(e)}

@api_router.put("/session/{session_id}/reorder-pages")
async def reorder_pages(session_id: str, data: dict):
    """إعادة ترتيب الصفحات داخل مجموعة كود"""
    try:
        code = data.get('code')
        new_order = data.get('new_order')  # قائمة page_ids بالترتيب الجديد
        
        session = await session_manager.get_session(session_id)
        if not session:
            return {"error": "الجلسة غير موجودة"}
        
        results = session.get('results', {})
        if code not in results:
            return {"error": "الكود غير موجود"}
        
        # إعادة ترتيب الصفحات
        pages = results[code]
        page_dict = {p['page_id']: p for p in pages}
        
        reordered_pages = [page_dict[page_id] for page_id in new_order if page_id in page_dict]
        results[code] = reordered_pages
        
        await session_manager.update_session(session_id, {'results': results})
        return {"success": True, "message": "تم إعادة الترتيب بنجاح"}
            
    except Exception as e:
        logger.error(f"خطأ في إعادة الترتيب: {e}")
        return {"error": str(e)}

@api_router.post("/clear-cache")
async def clear_cache():
    """مسح الذاكرة المؤقتة (cache) بدون مسح البيانات"""
    try:
        import shutil
        
        # مسح ملفات مؤقتة
        temp_dirs = [
            '/tmp/*.pdf',
            '/tmp/*.png',
            '/tmp/*.jpg'
        ]
        
        cleared_count = 0
        for pattern in temp_dirs:
            import glob
            for file in glob.glob(pattern):
                try:
                    os.remove(file)
                    cleared_count += 1
                except:
                    pass
        
        # مسح __pycache__
        for root, dirs, files in os.walk('/app'):
            if '__pycache__' in dirs:
                shutil.rmtree(os.path.join(root, '__pycache__'), ignore_errors=True)
        
        return {
            "success": True,
            "message": f"تم مسح {cleared_count} ملف مؤقت",
            "cleared_count": cleared_count
        }
        
    except Exception as e:
        logger.error(f"خطأ في مسح الذاكرة: {e}")
        return {"error": str(e)}

@api_router.post("/clear-old-files")
async def clear_old_files(days: int = 7):
    """مسح الملفات القديمة (أكثر من X أيام)"""
    try:
        import time
        
        outputs_dir = Path('/app/outputs')
        current_time = time.time()
        cutoff_time = current_time - (days * 24 * 60 * 60)
        
        deleted_count = 0
        deleted_size = 0
        
        if outputs_dir.exists():
            for session_dir in outputs_dir.iterdir():
                if session_dir.is_dir():
                    # فحص آخر تعديل
                    if session_dir.stat().st_mtime < cutoff_time:
                        # حساب الحجم
                        for file in session_dir.rglob('*'):
                            if file.is_file():
                                deleted_size += file.stat().st_size
                                deleted_count += 1
                        
                        # حذف المجلد
                        import shutil
                        shutil.rmtree(session_dir, ignore_errors=True)
        
        return {
            "success": True,
            "message": f"تم حذف {deleted_count} ملف قديم",
            "deleted_count": deleted_count,
            "deleted_size_mb": round(deleted_size / (1024 * 1024), 2),
            "days": days
        }
        
    except Exception as e:
        logger.error(f"خطأ في مسح الملفات القديمة: {e}")
        return {"error": str(e)}

@api_router.get("/session/{session_id}/preview/{code}")
async def preview_pdf(session_id: str, code: str):
    """معاينة PDF لكود معين"""
    try:
        # البحث عن الملف
        code_dir = Path(f'/app/codes/P{code}')
        
        if not code_dir.exists():
            return {"error": "المجلد غير موجود"}
        
        # جلب أول ملف PDF
        pdf_files = list(code_dir.glob('*.pdf'))
        if not pdf_files:
            return {"error": "لا توجد ملفات PDF"}
        
        pdf_file = pdf_files[0]
        
        # فتح PDF وجلب معلومات
        import fitz
        doc = fitz.open(pdf_file)
        
        return {
            "success": True,
            "filename": pdf_file.name,
            "page_count": len(doc),
            "file_size": pdf_file.stat().st_size,
            "path": str(pdf_file)
        }
        
    except Exception as e:
        logger.error(f"خطأ في معاينة PDF: {e}")
        return {"error": str(e)}

@api_router.get("/session/{session_id}/preview/{code}/page/{page_num}")
async def preview_pdf_page(session_id: str, code: str, page_num: int):
    """معاينة صفحة محددة من PDF كصورة"""
    try:
        from fastapi.responses import Response
        import fitz
        
        code_dir = Path(f'/app/codes/P{code}')
        if not code_dir.exists():
            return {"error": "المجلد غير موجود"}
        
        pdf_files = list(code_dir.glob('*.pdf'))
        if not pdf_files:
            return {"error": "لا توجد ملفات PDF"}
        
        pdf_file = pdf_files[0]
        doc = fitz.open(pdf_file)
        
        if page_num < 0 or page_num >= len(doc):
            return {"error": "رقم الصفحة غير صحيح"}
        
        # استخراج الصفحة كصورة
        page = doc[page_num]
        mat = fitz.Matrix(2, 2)  # تكبير 2x
        pix = page.get_pixmap(matrix=mat)
        img_data = pix.tobytes("png")
        
        doc.close()
        
        return Response(content=img_data, media_type="image/png")
        
    except Exception as e:
        logger.error(f"خطأ في معاينة صفحة PDF: {e}")
        return {"error": str(e)}

# WebSocket للتحديثات المباشرة
@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    active_connections[session_id] = websocket
    
    try:
        while True:
            # استقبال الرسائل (للحفاظ على الاتصال)
            data = await websocket.receive_text()
            
    except WebSocketDisconnect:
        if session_id in active_connections:
            del active_connections[session_id]
        logger.info(f"تم قطع الاتصال للجلسة: {session_id}")

# Include router
app.include_router(api_router)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (للنتائج)
app.mount("/results", StaticFiles(directory="/app/backend/sessions"), name="results")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
