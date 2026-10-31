"""
ScanFlow Pro V7 - Smart Session Manager
Gestion intelligente avec fallback automatique: MongoDB → JSON

✅ Si MongoDB disponible → utilise MongoDB
✅ Si MongoDB indisponible → utilise JSON automatiquement
"""

import logging
import os
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)

class SmartSessionManager:
    """
    Gestionnaire de sessions intelligent avec fallback automatique
    """
    
    def __init__(self):
        """Initialiser le gestionnaire avec détection automatique"""
        self.manager = None
        self.storage_type = None
        self._initialize()
    
    def _initialize(self):
        """
        Initialiser le bon gestionnaire selon l'environnement
        Ordre de priorité: MongoDB → JSON
        """
        # Essayer MongoDB d'abord
        mongo_url = os.getenv("MONGO_URL", "").strip()
        
        if mongo_url and mongo_url != "":
            try:
                logger.info("🔍 Tentative de connexion à MongoDB...")
                from .session_manager import SessionManager
                
                # Tester la connexion
                self.manager = SessionManager()
                self.storage_type = "mongodb"
                logger.info("✅ MongoDB connecté - utilisation de MongoDB")
                return
                
            except Exception as e:
                logger.warning(f"⚠️ MongoDB non disponible: {e}")
                logger.info("🔄 Basculement vers JSON...")
        else:
            logger.info("ℹ️ MONGO_URL non configuré - utilisation de JSON")
        
        # Fallback vers JSON
        try:
            from .json_session_manager import JSONSessionManager
            self.manager = JSONSessionManager()
            self.storage_type = "json"
            logger.info("✅ JSON Session Manager activé")
            
        except Exception as e:
            logger.error(f"❌ Impossible d'initialiser le gestionnaire: {e}")
            raise RuntimeError("Aucun gestionnaire de sessions disponible")
    
    def get_info(self) -> Dict[str, str]:
        """Obtenir des informations sur le gestionnaire actif"""
        return {
            "storage_type": self.storage_type,
            "manager": self.manager.__class__.__name__,
            "status": "active"
        }
    
    # ================================
    # Proxy methods - toutes les méthodes du manager
    # ================================
    
    async def create_session(self, *args, **kwargs) -> str:
        """Create a session and always return its string identifier."""
        if len(args) == 1 and isinstance(args[0], dict):
            session_data = dict(args[0])
            batch_name = session_data.get("batch_name", "")
            settings = session_data.get("settings", {})
        else:
            batch_name = kwargs.get("batch_name", args[0] if args else "")
            settings = kwargs.get("settings", args[1] if len(args) > 1 else {})
            session_data = {
                "batch_name": batch_name,
                "settings": settings,
                "files": [],
                "pages": [],
                "code_groups": [],
                "results": [],
                "report": {},
                "status": "created",
                "progress": 0,
            }

        if self.storage_type == "mongodb":
            session_id = await self.manager.create_session(
                batch_name=batch_name,
                settings=settings,
            )
        else:
            import uuid
            session_data.setdefault("session_id", str(uuid.uuid4()))
            session_data.setdefault("batch_name", batch_name)
            session_data.setdefault("settings", settings)
            session_data.setdefault("files", [])
            session_data.setdefault("pages", [])
            session_data.setdefault("code_groups", [])
            session_data.setdefault("results", [])
            session_data.setdefault("report", {})
            session_data.setdefault("status", "created")
            session_data.setdefault("progress", 0)
            created = await self.manager.create_session(session_data)
            session_id = created.get("session_id") if isinstance(created, dict) else created

        if not isinstance(session_id, str) or not session_id:
            raise RuntimeError("Session manager did not return a valid session_id")
        return session_id

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Récupérer une session"""
        return await self.manager.get_session(session_id)
    
    async def update_session(self, session_id: str, updates: Dict[str, Any]) -> bool:
        """Mettre à jour une session"""
        return await self.manager.update_session(session_id, updates)
    
    async def delete_session(self, session_id: str) -> bool:
        """Supprimer une session"""
        return await self.manager.delete_session(session_id)
    
    async def list_sessions(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Lister les sessions"""
        if hasattr(self.manager, 'list_sessions'):
            return await self.manager.list_sessions(limit)
        else:
            # Pour MongoDB SessionManager qui n'a pas cette méthode
            logger.warning("list_sessions non supporté par ce manager")
            return []
    
    async def cleanup_old_sessions(self, days: int = 7) -> int:
        """Nettoyer les anciennes sessions"""
        if hasattr(self.manager, 'cleanup_old_sessions'):
            return await self.manager.cleanup_old_sessions(days)
        else:
            logger.warning("cleanup_old_sessions non supporté par ce manager")
            return 0
    
    async def get_storage_info(self) -> Dict[str, Any]:
        """Obtenir des infos sur le stockage"""
        if hasattr(self.manager, 'get_storage_info'):
            return await self.manager.get_storage_info()
        else:
            return {
                "type": self.storage_type,
                "manager": self.manager.__class__.__name__,
                "available": True
            }
    
    def get_session_path(self, session_id: str, subdir: str = None):
        """Obtenir le chemin du dossier de session"""
        if hasattr(self.manager, 'get_session_path'):
            return self.manager.get_session_path(session_id, subdir)
        else:
            # Fallback pour les managers qui n'ont pas cette méthode
            from pathlib import Path
            base_path = Path("/app/backend/sessions")
            base_path.mkdir(parents=True, exist_ok=True)
            if subdir:
                return base_path / session_id / subdir
            return base_path / session_id

# ================================
# Instance globale (Singleton)
# ================================
_smart_manager_instance = None

def get_smart_session_manager() -> SmartSessionManager:
    """
    Obtenir l'instance du gestionnaire (Singleton)
    
    Returns:
        Instance unique du SmartSessionManager
    """
    global _smart_manager_instance
    
    if _smart_manager_instance is None:
        _smart_manager_instance = SmartSessionManager()
    
    return _smart_manager_instance

# ================================
# Test
# ================================
async def test_smart_manager():
    """Test du gestionnaire intelligent"""
    manager = get_smart_session_manager()
    
    print("=" * 50)
    print("🧪 Test Smart Session Manager")
    print("=" * 50)
    
    # Afficher le type de stockage
    info = manager.get_info()
    print(f"\n📊 Type de stockage: {info['storage_type'].upper()}")
    print(f"📦 Manager: {info['manager']}")
    
    # Test création
    print("\n1️⃣ Test création...")
    session = await manager.create_session({
        "session_id": "test_smart_001",
        "batch_name": "Test Smart Batch",
        "files": []
    })
    print(f"   ✓ Session créée: {session['session_id']}")
    
    # Test lecture
    print("\n2️⃣ Test lecture...")
    retrieved = await manager.get_session("test_smart_001")
    print(f"   ✓ Batch name: {retrieved['batch_name']}")
    
    # Test update
    print("\n3️⃣ Test update...")
    success = await manager.update_session("test_smart_001", {"status": "completed"})
    print(f"   ✓ Update: {'Succès' if success else 'Échec'}")
    
    # Test storage info
    print("\n4️⃣ Test storage info...")
    storage_info = await manager.get_storage_info()
    print(f"   ✓ Storage: {storage_info}")
    
    # Test suppression
    print("\n5️⃣ Test suppression...")
    deleted = await manager.delete_session("test_smart_001")
    print(f"   ✓ Suppression: {'Succès' if deleted else 'Échec'}")
    
    print("\n" + "=" * 50)
    print("✅ Tests terminés!")
    print("=" * 50)

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_smart_manager())
