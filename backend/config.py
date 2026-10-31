"""
ScanFlow Pro V7 - Configuration DAM Edition
Tous les paramètres et constantes du système avec focus DAM
"""

import os
import shutil
from pathlib import Path

# ================================
# 🔥 DAM PROFILES
# ================================
DAM_PROFILES = {
    "DAM_STRICT": {
        "name": "DAM Strict",
        "description": "Mode DAM strict pour documents administratifs marocains",
        "min_digits": 4,
        "max_digits": 8,          # ✅ DAM: 8 أرقام كحد أقصى
        "strict_mode": True,
        "dam_patterns_only": True,
        "validation_threshold": 0.70,
        "min_confidence": 0.65
    },
    "DAM_FLEXIBLE": {
        "name": "DAM Flexible",
        "description": "Mode DAM flexible avec extraction générique",
        "min_digits": 4,
        "max_digits": 10,
        "strict_mode": False,
        "dam_patterns_only": False,
        "validation_threshold": 0.60,
        "min_confidence": 0.55
    },
    "GENERIC": {
        "name": "Generic",
        "description": "Mode générique pour tous types de documents",
        "min_digits": 4,
        "max_digits": 12,
        "strict_mode": False,
        "dam_patterns_only": False,
        "validation_threshold": 0.50,
        "min_confidence": 0.45
    }
}

# 🔥 PROFILE ACTIF (Single Source of Truth)
ACTIVE_PROFILE = "DAM_STRICT"
DAM_CONFIG = DAM_PROFILES[ACTIVE_PROFILE]

# ================================
# Chemins (Paths)
# ================================
BASE_DIR = Path(__file__).parent
PROJECT_ROOT = BASE_DIR.parent
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
CODES_DIR = PROJECT_ROOT / "codes"
DATA_DIR = PROJECT_ROOT / "data"
ENGINES_DIR = BASE_DIR / "engines"

# Créer les dossiers si nécessaire
OUTPUTS_DIR.mkdir(exist_ok=True)
CODES_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

# ================================
# Base de données (MongoDB)
# ================================
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "scanflow_pro_v7_dam")

# ================================
# Serveur
# ================================
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8001"))
ENV = os.getenv("ENV", "production")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

# ================================
# 🔥 Tesseract OCR (DAM Optimized)
# ================================
_DEFAULT_TESSERACT_CMD = (
    shutil.which("tesseract")
    or (
        r"C:\ProgramData\Tesseract-OCR\tesseract.exe"
        if os.name == "nt"
        else "/usr/bin/tesseract"
    )
)
TESSERACT_CMD = os.getenv("TESSERACT_CMD", _DEFAULT_TESSERACT_CMD)

# Langues OCR (Arabe prioritaire pour DAM)
TESSERACT_LANGUAGES = "ara+fra+eng"

# PSM optimisé pour DAM
TESSERACT_PSM = 11  # Sparse text avec orientation
TESSERACT_OEM = 3   # LSTM Engine

# ================================
# 🔥 OCR/HTR Settings for DAM
# ================================
# Seuils de confiance DAM (plus élevés pour la précision)
MIN_OCR_CONFIDENCE = 0.75  # Confiance minimale pour accepter un code
MIN_HTR_CONFIDENCE = 0.65  # HTR moins précis

# DPI pour conversion PDF → Image (haute qualité pour DAM)
PDF_TO_IMAGE_DPI = 400

# Nombre maximum de tentatives auto-recovery
MAX_RECOVERY_ATTEMPTS = 3

# ================================
# 🔥 DAM Code Patterns
# ================================
# Dam Anchors (Arabic)
DAM_ARABIC_ANCHORS = [
    "القطعة رقم",
    "رقم القطعة", 
    "القطعة المتعلقة بالرقم",
    "رقم المتعلقة",
    "رقم",
    "الرقم",
    "كود",
    "معرف",
    "الرمز",
    "المعرف"
]

# Dam Anchors (French)
DAM_FRENCH_ANCHORS = [
    "N°",
    "Parcelle N°",
    "Parcelle",
    "Code Parcelle", 
    "Numéro",
    "Code",
    "ID",
    "Identifiant"
]

# Combined anchors
DAM_ANCHORS = DAM_ARABIC_ANCHORS + DAM_FRENCH_ANCHORS

# DAM Regex Patterns
DAM_PATTERNS = [
    # Arabe
    r'(?:القطعة\s*رقم|رقم\s*القطعة|القطعة\s*المتعلقة)[\s:.-]*(\d{4,8})',
    r'(?:رقم|كود|معرف|الرمز)[\s:.-]*(\d{4,8})',
    
    # Français
    r'(?:N[°\s]|Parcelle\s*N[°\s]|Code\s*Parcelle)[\s:.-]*(\d{4,8})',
    r'(?:Numéro|Code|ID)[\s:.-]*(\d{4,8})',
    
    # Générique
    r'(?:القطعة\s*رقم|رقم\s*القطعة|N[°\s]|Parcelle)[^0-9]{0,10}(\d{4,8})',
    r'(?:\.{3,}\s*)?(?:N[°\s]|رقم)[\s:.-]*(\d{4,8})',
]

# Patterns suspects (à rejeter)
SUSPICIOUS_PATTERNS = [
    r'^0{4,}$',      # 0000...
    r'^1{4,}$',      # 1111...
    r'^9{4,}$',      # 9999...
    r'^12345',       # 123456
    r'^54321',       # 543210
]

# Patterns de codes acceptés (dynamique selon profile)
CODE_PATTERN = rf'\d{{{DAM_CONFIG["min_digits"]},{DAM_CONFIG["max_digits"]}}}'

# ================================
# Image Enhancement (DAM Optimized)
# ================================
# Seuil de flou
BLUR_THRESHOLD = 150.0  # Valeur Laplacian (haut pour DAM)

# Taille maximale d'image
MAX_IMAGE_WIDTH = 2500
MAX_IMAGE_HEIGHT = 3500

# Enhancement levels
ENHANCEMENT_LEVELS = {
    "handwritten": "very_high",
    "printed": "high",
    "mixed": "medium",
    "dam": "very_high"  # Niveau spécial DAM
}

# ================================
# Processing Timeouts
# ================================
PAGE_PROCESSING_TIMEOUT = 45  # DAM nécessite plus de temps
OCR_TIMEOUT = 15
HTR_TIMEOUT = 20

# ================================
# WebSocket
# ================================
WS_PING_INTERVAL = 5
WS_PING_TIMEOUT = 30

# ================================
# File Upload
# ================================
MAX_UPLOAD_SIZE = 200 * 1024 * 1024  # 200MB pour DAM (documents lourds)
ALLOWED_EXTENSIONS = [".pdf", ".PDF"]

# ================================
# Session Management
# ================================
SESSION_LIFETIME_DAYS = 30  # DAM: sessions plus longues
AUTO_CLEANUP_ENABLED = True
CLEANUP_OLDER_THAN_DAYS = 30

# ================================
# Logging
# ================================
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - [DAM] %(message)s"

# ================================
# PaddleOCR (HTR) Settings
# ================================
PADDLE_USE_GPU = False
PADDLE_LANG = "fr"  # Français pour DAM

# ================================
# Performance
# ================================
MAX_WORKERS = 2  # DAM: moins de workers pour plus de stabilité
ENABLE_CACHING = True
CACHE_TTL = 3600  # 1 heure

# ================================
# YOLO Settings (optionnel)
# ================================
YOLO_ENABLED = True
YOLO_MIN_CONFIDENCE = 0.4
YOLO_MODEL_PATH = None  # Utilise le modèle par défaut

# ================================
# ROI Settings
# ================================
ROI_EXPANSION_PIXELS = 25
ROI_MIN_WIDTH = 50
ROI_MIN_HEIGHT = 20

# ================================
# Frontend URLs
# ================================
FRONTEND_URLS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",  # Vite
    "http://127.0.0.1:5173",
]

# ================================
# Security
# ================================
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dam-enterprise-secret-key-2024")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 48

# ================================
# Debug & Development
# ================================
DEBUG = ENV == "development"
SAVE_DEBUG_IMAGES = DEBUG
LOG_DAM_EXTRACTION = True  # Toujours logger les extractions DAM

# ================================
# Export Configuration
# ================================
PDF_OUTPUT_FORMAT = "PDF/A-2b"  # Format archive avancé
PDF_COMPRESSION = True
PDF_ENCRYPTION = False

PDF_METADATA = {
    "Creator": "ScanFlow Pro V7 - DAM Edition",
    "Producer": "ScanFlow Enterprise DAM",
    "Title": "Document Administratif Marocain",
    "Subject": "Extraction et gestion de codes DAM",
    "Keywords": "DAM, Administratif, Maroc, Parcelle, قطعة, رقم"
}

# ================================
# Validation
# ================================
def validate_config():
    """Valider la configuration DAM au démarrage"""
    errors = []
    
    # Vérifier Tesseract
    if TESSERACT_CMD and not Path(TESSERACT_CMD).exists():
        errors.append(f"❌ Tesseract non trouvé: {TESSERACT_CMD}")
    
    # Vérifier MongoDB URL
    if not MONGO_URL:
        errors.append("❌ MONGO_URL non définie")
    
    # Vérifier dossiers
    required_dirs = [OUTPUTS_DIR, CODES_DIR, DATA_DIR]
    for dir_path in required_dirs:
        if not dir_path.exists():
            try:
                dir_path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                errors.append(f"❌ Impossible de créer {dir_path}: {e}")
    
    # Vérifier profile DAM
    if ACTIVE_PROFILE not in DAM_PROFILES:
        errors.append(f"❌ Profile DAM invalide: {ACTIVE_PROFILE}")
    
    # Afficher le profile actif
    if not errors:
        profile = DAM_PROFILES[ACTIVE_PROFILE]
        print(f"\n{'='*60}")
        print(f"🎯 PROFILE DAM ACTIF: {profile['name']}")
        print(f"{'='*60}")
        print(f"Description: {profile['description']}")
        print(f"Min digits: {profile['min_digits']}")
        print(f"Max digits: {profile['max_digits']}")
        print(f"Strict mode: {profile['strict_mode']}")
        print(f"DAM patterns only: {profile['dam_patterns_only']}")
        print(f"Validation threshold: {profile['validation_threshold']}")
        print(f"Min confidence: {profile['min_confidence']}")
        print(f"{'='*60}\n")
    
    return errors

# Valider au démarrage
_validation_errors = validate_config()
if _validation_errors:
    import warnings
    for error in _validation_errors:
        warnings.warn(f"Configuration Warning: {error}")
    print("\n⚠️  Certaines validations ont échoué. Vérifiez la configuration.\n")
else:
    print("✅ Configuration DAM validée avec succès\n")

# ================================
# Fonctions utilitaires
# ================================
def get_dam_profile():
    """Obtenir le profile DAM actif"""
    return DAM_PROFILES.get(ACTIVE_PROFILE, DAM_PROFILES["DAM_STRICT"])

def set_dam_profile(profile_name: str):
    """Changer le profile DAM dynamiquement"""
    global ACTIVE_PROFILE, DAM_CONFIG
    if profile_name in DAM_PROFILES:
        ACTIVE_PROFILE = profile_name
        DAM_CONFIG = DAM_PROFILES[profile_name]
        print(f"✅ Profile DAM changé vers: {DAM_CONFIG['name']}")
        return True
    else:
        print(f"❌ Profile inconnu: {profile_name}")
        return False

def get_dam_anchors(language: str = "all"):
    """Obtenir les anchors DAM par langue"""
    if language == "ar":
        return DAM_ARABIC_ANCHORS
    elif language == "fr":
        return DAM_FRENCH_ANCHORS
    else:
        return DAM_ANCHORS

def is_dam_mode() -> bool:
    """Vérifier si on est en mode DAM"""
    return ACTIVE_PROFILE.startswith("DAM_")

# ================================
# Exporter toutes les constantes
# ================================
__all__ = [
    # Profiles
    "DAM_PROFILES", "ACTIVE_PROFILE", "DAM_CONFIG", 
    "get_dam_profile", "set_dam_profile", "is_dam_mode",
    
    # Paths
    "BASE_DIR", "PROJECT_ROOT", "OUTPUTS_DIR", "CODES_DIR", 
    "DATA_DIR", "ENGINES_DIR",
    
    # Database
    "MONGO_URL", "DB_NAME",
    
    # Server
    "HOST", "PORT", "ENV", "CORS_ORIGINS",
    
    # Tesseract
    "TESSERACT_CMD", "TESSERACT_LANGUAGES", "TESSERACT_PSM", 
    "TESSERACT_OEM",
    
    # OCR/HTR
    "MIN_OCR_CONFIDENCE", "MIN_HTR_CONFIDENCE", "PDF_TO_IMAGE_DPI",
    "MAX_RECOVERY_ATTEMPTS",
    
    # DAM Patterns
    "DAM_ARABIC_ANCHORS", "DAM_FRENCH_ANCHORS", "DAM_ANCHORS",
    "DAM_PATTERNS", "SUSPICIOUS_PATTERNS", "CODE_PATTERN",
    "get_dam_anchors",
    
    # Images
    "BLUR_THRESHOLD", "MAX_IMAGE_WIDTH", "MAX_IMAGE_HEIGHT",
    "ENHANCEMENT_LEVELS",
    
    # Timeouts
    "PAGE_PROCESSING_TIMEOUT", "OCR_TIMEOUT", "HTR_TIMEOUT",
    
    # WebSocket
    "WS_PING_INTERVAL", "WS_PING_TIMEOUT",
    
    # Upload
    "MAX_UPLOAD_SIZE", "ALLOWED_EXTENSIONS",
    
    # Sessions
    "SESSION_LIFETIME_DAYS", "AUTO_CLEANUP_ENABLED", "CLEANUP_OLDER_THAN_DAYS",
    
    # Logging
    "LOG_LEVEL", "LOG_FORMAT",
    
    # PaddleOCR
    "PADDLE_USE_GPU", "PADDLE_LANG",
    
    # Performance
    "MAX_WORKERS", "ENABLE_CACHING", "CACHE_TTL",
    
    # YOLO
    "YOLO_ENABLED", "YOLO_MIN_CONFIDENCE", "YOLO_MODEL_PATH",
    
    # ROI
    "ROI_EXPANSION_PIXELS", "ROI_MIN_WIDTH", "ROI_MIN_HEIGHT",
    
    # Frontend
    "FRONTEND_URLS",
    
    # Security
    "JWT_SECRET_KEY", "JWT_ALGORITHM", "JWT_EXPIRATION_HOURS",
    
    # Debug
    "DEBUG", "SAVE_DEBUG_IMAGES", "LOG_DAM_EXTRACTION",
    
    # Export
    "PDF_OUTPUT_FORMAT", "PDF_COMPRESSION", "PDF_ENCRYPTION", "PDF_METADATA",
    
    # Validation
    "validate_config",
]