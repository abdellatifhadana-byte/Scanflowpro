"""
ScanFlow Pro V7 - JSON Session Manager (Fallback)
Gestion des sessions avec fichiers JSON (sans MongoDB)
Pour Windows Offline ou environnements sans base de données
"""

import json
import logging
from pathlib import Path
from typing import Optional, Dict, List, Any
from datetime import datetime, timezone
import shutil

logger = logging.getLogger(__name__)

class JSONSessionManager:
    """
    Gestionnaire de sessions basé sur JSON
    Alternative à MongoDB pour environnements offline
    """
    
    def __init__(self, storage_dir: Optional[Path] = None):
        """
        Initialiser le gestionnaire JSON
        
        Args:
            storage_dir: Dossier de stockage des sessions (défaut: ./data/sessions)
        """
        if storage_dir is None:
            storage_dir = Path(__file__).parent.parent.parent / "data" / "sessions"
        
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"JSON Session Manager initialisé: {self.storage_dir}")
    
    def _get_session_path(self, session_id: str) -> Path:
        """Obtenir le chemin du fichier de session"""
        return self.storage_dir / f"{session_id}.json"
    
    async def create_session(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Créer une nouvelle session
        
        Args:
            session_data: Données de la session
            
        Returns:
            Session créée avec métadonnées
        """
        try:
            session_id = session_data.get("session_id")
            if not session_id:
                raise ValueError("session_id requis")
            
            # Ajouter métadonnées
            session_data["created_at"] = datetime.now(timezone.utc).isoformat()
            session_data["updated_at"] = datetime.now(timezone.utc).isoformat()
            session_data["status"] = session_data.get("status", "created")
            session_data["version"] = "7.0.0"
            
            # Sauvegarder
            session_path = self._get_session_path(session_id)
            with open(session_path, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✓ Session créée: {session_id}")
            return session_data
            
        except Exception as e:
            logger.error(f"Erreur création session: {e}")
            raise
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Récupérer une session
        
        Args:
            session_id: ID de la session
            
        Returns:
            Données de la session ou None
        """
        try:
            session_path = self._get_session_path(session_id)
            
            if not session_path.exists():
                logger.warning(f"Session non trouvée: {session_id}")
                return None
            
            with open(session_path, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
            
            return session_data
            
        except Exception as e:
            logger.error(f"Erreur lecture session {session_id}: {e}")
            return None
    
    async def update_session(self, session_id: str, updates: Dict[str, Any]) -> bool:
        """
        Mettre à jour une session
        
        Args:
            session_id: ID de la session
            updates: Données à mettre à jour
            
        Returns:
            True si succès, False sinon
        """
        try:
            session = await self.get_session(session_id)
            if not session:
                logger.error(f"Session non trouvée pour update: {session_id}")
                return False
            
            # Mettre à jour
            session.update(updates)
            session["updated_at"] = datetime.now(timezone.utc).isoformat()
            
            # Sauvegarder
            session_path = self._get_session_path(session_id)
            with open(session_path, 'w', encoding='utf-8') as f:
                json.dump(session, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✓ Session mise à jour: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur update session {session_id}: {e}")
            return False
    
    async def delete_session(self, session_id: str) -> bool:
        """
        Supprimer une session
        
        Args:
            session_id: ID de la session
            
        Returns:
            True si succès, False sinon
        """
        try:
            session_path = self._get_session_path(session_id)
            
            if session_path.exists():
                session_path.unlink()
                logger.info(f"✓ Session supprimée: {session_id}")
                return True
            else:
                logger.warning(f"Session non trouvée pour suppression: {session_id}")
                return False
                
        except Exception as e:
            logger.error(f"Erreur suppression session {session_id}: {e}")
            return False
    
    async def list_sessions(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Lister toutes les sessions
        
        Args:
            limit: Nombre maximum de sessions à retourner
            
        Returns:
            Liste des sessions
        """
        try:
            sessions = []
            
            for session_file in self.storage_dir.glob("*.json"):
                try:
                    with open(session_file, 'r', encoding='utf-8') as f:
                        session = json.load(f)
                        sessions.append(session)
                except Exception as e:
                    logger.error(f"Erreur lecture {session_file}: {e}")
            
            # Trier par date de création (plus récent d'abord)
            sessions.sort(
                key=lambda x: x.get("created_at", ""),
                reverse=True
            )
            
            return sessions[:limit]
            
        except Exception as e:
            logger.error(f"Erreur listage sessions: {e}")
            return []
    
    async def cleanup_old_sessions(self, days: int = 7) -> int:
        """
        Nettoyer les sessions anciennes
        
        Args:
            days: Nombre de jours avant suppression
            
        Returns:
            Nombre de sessions supprimées
        """
        try:
            deleted = 0
            cutoff_date = datetime.now(timezone.utc).timestamp() - (days * 86400)
            
            for session_file in self.storage_dir.glob("*.json"):
                try:
                    # Vérifier la date de modification du fichier
                    file_time = session_file.stat().st_mtime
                    
                    if file_time < cutoff_date:
                        session_file.unlink()
                        deleted += 1
                        logger.info(f"✓ Session ancienne supprimée: {session_file.name}")
                        
                except Exception as e:
                    logger.error(f"Erreur suppression {session_file}: {e}")
            
            logger.info(f"✓ Nettoyage: {deleted} sessions supprimées")
            return deleted
            
        except Exception as e:
            logger.error(f"Erreur nettoyage: {e}")
            return 0
    
    async def get_storage_info(self) -> Dict[str, Any]:
        """
        Obtenir des informations sur le stockage
        
        Returns:
            Statistiques de stockage
        """
        try:
            session_files = list(self.storage_dir.glob("*.json"))
            total_size = sum(f.stat().st_size for f in session_files)
            
            return {
                "type": "json",
                "location": str(self.storage_dir),
                "total_sessions": len(session_files),
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "available": True
            }
            
        except Exception as e:
            logger.error(f"Erreur info stockage: {e}")
            return {
                "type": "json",
                "location": str(self.storage_dir),
                "error": str(e),
                "available": False
            }
    
    async def export_all_sessions(self, export_path: Path) -> bool:
        """
        Exporter toutes les sessions vers un dossier
        
        Args:
            export_path: Dossier de destination
            
        Returns:
            True si succès
        """
        try:
            export_path = Path(export_path)
            export_path.mkdir(parents=True, exist_ok=True)
            
            for session_file in self.storage_dir.glob("*.json"):
                shutil.copy2(session_file, export_path / session_file.name)
            
            logger.info(f"✓ Export sessions vers: {export_path}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur export: {e}")
            return False
    
    async def import_session(self, session_file: Path) -> Optional[str]:
        """
        Importer une session depuis un fichier
        
        Args:
            session_file: Chemin du fichier JSON
            
        Returns:
            session_id si succès, None sinon
        """
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
            
            session_id = session_data.get("session_id")
            if not session_id:
                raise ValueError("session_id manquant dans le fichier")
            
            # Copier vers storage
            dest_path = self._get_session_path(session_id)
            shutil.copy2(session_file, dest_path)
            
            logger.info(f"✓ Session importée: {session_id}")
            return session_id
            
        except Exception as e:
            logger.error(f"Erreur import: {e}")
            return None

# ================================
# Fonction helper pour tests
# ================================
async def test_json_manager():
    """Test du gestionnaire JSON"""
    manager = JSONSessionManager()
    
    # Test création
    session = await manager.create_session({
        "session_id": "test_123",
        "batch_name": "Test Batch",
        "files": []
    })
    print(f"✓ Création: {session['session_id']}")
    
    # Test lecture
    retrieved = await manager.get_session("test_123")
    print(f"✓ Lecture: {retrieved['batch_name']}")
    
    # Test update
    await manager.update_session("test_123", {"status": "processing"})
    print("✓ Update")
    
    # Test info
    info = await manager.get_storage_info()
    print(f"✓ Info: {info}")
    
    # Test suppression
    await manager.delete_session("test_123")
    print("✓ Suppression")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_json_manager())
