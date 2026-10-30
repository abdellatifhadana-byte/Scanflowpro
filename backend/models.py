from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict
from datetime import datetime, timezone

class ROIArea(BaseModel):
    """منطقة ROI"""
    model_config = ConfigDict(extra="ignore")
    x: float
    y: float
    width: float
    height: float
    type: str  # code, keyword, page_number

class FileSettings(BaseModel):
    """إعدادات كل ملف"""
    model_config = ConfigDict(extra="ignore")
    filename: str
    output_name: str  # الاسم النهائي للإخراج
    has_child_pages: bool = True
    document_type: str = "printed"  # printed, handwritten, mixed
    roi_areas: List[ROIArea] = []
    merge_with_files: List[str] = []  # أسماء الملفات للتجميع

class PageResult(BaseModel):
    """نتيجة صفحة واحدة"""
    model_config = ConfigDict(extra="ignore")
    page_id: str
    page_number: int
    code: Optional[str] = None
    confidence: float = 0.0
    is_main: bool = False
    is_child: bool = False
    parent_code: Optional[str] = None
    output_name: str = ""
    source_file: str = ""
    code_image_url: Optional[str] = None
    page_marker: Optional[str] = None
    original_file_path: Optional[str] = None
    original_page_number: int = 0
    
    def get(self, key: str, default=None):
        """للتوافق مع dict"""
        return getattr(self, key, default)

class CodeGroup(BaseModel):
    """مجموعة كود واحد"""
    model_config = ConfigDict(extra="ignore")
    code: str
    pages: List[PageResult]
    output_names: List[str]  # أسماء الإخراج المختلفة
    merged_files: List[str] = []  # ملفات مجمعة

class SessionCreate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    batch_name: str
    turbo_mode: bool = False
    file_settings: List[FileSettings] = []

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

class UpdatePageRequest(BaseModel):
    """طلب تحديث صفحة"""
    model_config = ConfigDict(extra="ignore")
    page_id: str
    code: Optional[str] = None
    output_name: Optional[str] = None
    is_child: Optional[bool] = None

class MergeRequest(BaseModel):
    """طلب تجميع النهائي"""
    model_config = ConfigDict(extra="ignore")
    session_id: str
    code_groups: List[CodeGroup]
