import uuid
from datetime import datetime, timezone
from pathlib import Path
import json
import logging
from typing import Dict, Optional
import os
from motor.motor_asyncio import AsyncIOMotorClient
import numpy as np

logger = logging.getLogger(__name__)


class CustomJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for handling special types"""
    def default(self, obj):
        if isinstance(obj, (np.integer, np.floating)):
            return int(obj) if isinstance(obj, np.integer) else float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, np.bool_):
            return bool(obj)
        elif isinstance(obj, bool):
            return bool(obj)
        elif isinstance(obj, (datetime,)):
            return obj.isoformat()
        return super().default(obj)

class SessionManager:
    """مدير الجلسات - إدارة جلسات المعالجة مع حفظ دائم"""
    
    def __init__(self, base_dir: str = "/app/backend/sessions"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # الاتصال بـ MongoDB
        mongo_url = os.environ.get('MONGO_URL')
        if mongo_url:
            self.mongo_client = AsyncIOMotorClient(mongo_url)
            self.db = self.mongo_client[os.environ.get('DB_NAME', 'scanflow')]
            self.sessions_collection = self.db['sessions']
        else:
            self.mongo_client = None
            self.sessions_collection = None
        
        # ذاكرة مؤقتة
        self.sessions = {}
    
    async def create_session(self, batch_name: str, settings: Dict) -> str:
        """إنشاء جلسة جديدة"""
        try:
            session_id = str(uuid.uuid4())
            
            # إنشاء مجلد الجلسة
            session_dir = self.base_dir / session_id
            session_dir.mkdir(parents=True, exist_ok=True)
            
            # إنشاء مجلدات فرعية
            (session_dir / 'uploads').mkdir(exist_ok=True)
            (session_dir / 'processed').mkdir(exist_ok=True)
            (session_dir / 'results').mkdir(exist_ok=True)
            (session_dir / 'roi_images').mkdir(exist_ok=True)
            
            # بيانات الجلسة
            session_data = {
                '_id': session_id,
                'session_id': session_id,
                'batch_name': batch_name,
                'settings': settings,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'updated_at': datetime.now(timezone.utc).isoformat(),
                'status': 'created',
                'progress': 0,
                'files': [],
                'pages': [],
                'code_groups': [],
                'results': [],
                'report': {}
            }
            
            # حفظ في الذاكرة
            self.sessions[session_id] = session_data
            
            # حفظ في الملف
            session_file = session_dir / 'session.json'
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, ensure_ascii=False, indent=2, cls=CustomJSONEncoder)
            
            # حفظ في MongoDB
            if self.sessions_collection is not None:
                await self.sessions_collection.insert_one(session_data.copy())
            
            logger.info(f"تم إنشاء جلسة: {session_id}")
            return session_id
            
        except Exception as e:
            logger.error(f"خطأ في إنشاء الجلسة: {e}")
            raise
    
    async def get_session(self, session_id: str) -> Optional[Dict]:
        """الحصول على بيانات الجلسة"""
        try:
            # محاولة من الذاكرة
            if session_id in self.sessions:
                return self.sessions[session_id]
            
            # محاولة من MongoDB
            if self.sessions_collection is not None:
                session = await self.sessions_collection.find_one({'_id': session_id})
                if session:
                    self.sessions[session_id] = session
                    return session
            
            # محاولة من الملف
            session_file = self.base_dir / session_id / 'session.json'
            if session_file.exists():
                with open(session_file, 'r', encoding='utf-8') as f:
                    session = json.load(f)
                    self.sessions[session_id] = session
                    return session
            
            logger.warning(f"الجلسة غير موجودة: {session_id}")
            return None
            
        except Exception as e:
            logger.error(f"خطأ في الحصول على الجلسة: {e}")
            return None
    
    async def update_session(self, session_id: str, updates: Dict):
        """تحديث بيانات الجلسة"""
        try:
            # الحصول على الجلسة الحالية
            session = await self.get_session(session_id)
            if not session:
                raise ValueError(f"الجلسة غير موجودة: {session_id}")
            
            # تطبيق التحديثات
            session.update(updates)
            session['updated_at'] = datetime.now(timezone.utc).isoformat()
            
            # حفظ في الذاكرة
            self.sessions[session_id] = session
            
            # حفظ في الملف
            session_file = self.base_dir / session_id / 'session.json'
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(session, f, ensure_ascii=False, indent=2, cls=CustomJSONEncoder)
            
            # حفظ في MongoDB
            if self.sessions_collection is not None:
                await self.sessions_collection.update_one(
                    {'_id': session_id},
                    {'$set': updates}
                )
            
            logger.debug(f"تم تحديث الجلسة: {session_id}")
            
        except Exception as e:
            logger.error(f"خطأ في تحديث الجلسة: {e}")
            raise
    
    async def list_sessions(self, limit: int = 50) -> list:
        """قائمة الجلسات"""
        try:
            if self.sessions_collection is not None:
                cursor = self.sessions_collection.find().sort('created_at', -1).limit(limit)
                sessions = []
                async for session in cursor:
                    sessions.append(session)
                return sessions
            else:
                # من الملفات
                sessions = []
                for session_dir in self.base_dir.iterdir():
                    if session_dir.is_dir():
                        session_file = session_dir / 'session.json'
                        if session_file.exists():
                            with open(session_file, 'r', encoding='utf-8') as f:
                                sessions.append(json.load(f))
                
                sessions.sort(key=lambda x: x.get('created_at', ''), reverse=True)
                return sessions[:limit]
                
        except Exception as e:
            logger.error(f"خطأ في قائمة الجلسات: {e}")
            return []
    
    async def delete_session(self, session_id: str):
        """حذف جلسة"""
        try:
            # حذف من الذاكرة
            if session_id in self.sessions:
                del self.sessions[session_id]
            
            # حذف من MongoDB
            if self.sessions_collection is not None:
                await self.sessions_collection.delete_one({'_id': session_id})
            
            # حذف المجلد
            session_dir = self.base_dir / session_id
            if session_dir.exists():
                import shutil
                shutil.rmtree(session_dir)
            
            logger.info(f"تم حذف الجلسة: {session_id}")
            
        except Exception as e:
            logger.error(f"خطأ في حذف الجلسة: {e}")
            raise
    
    def get_session_path(self, session_id: str, subdir: str = None) -> Path:
        """الحصول على مسار مجلد الجلسة"""
        if subdir:
            return self.base_dir / session_id / subdir
        return self.base_dir / session_id
