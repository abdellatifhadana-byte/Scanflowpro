"""
ScanFlow Pro V7 - Session Lock Manager
Prevents concurrent processing of the same session
"""

import asyncio
import logging
from typing import Dict, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class SessionLockManager:
    """
    Gère les locks de sessions pour éviter les traitements concurrents
    """
    
    def __init__(self):
        self._locks: Dict[str, asyncio.Lock] = {}
        self._tasks: Dict[str, asyncio.Task] = {}
        self._processing_start_times: Dict[str, datetime] = {}
        logger.info("🔒 SessionLockManager initialized")
    
    def get_lock(self, session_id: str) -> asyncio.Lock:
        """
        Obtenir ou créer un lock pour une session
        
        Args:
            session_id: ID de la session
            
        Returns:
            asyncio.Lock pour cette session
        """
        if session_id not in self._locks:
            self._locks[session_id] = asyncio.Lock()
            logger.info(f"🔒 Created lock for session {session_id}")
        
        return self._locks[session_id]
    
    def is_locked(self, session_id: str) -> bool:
        """
        Vérifier si une session est verrouillée (en traitement)
        
        Args:
            session_id: ID de la session
            
        Returns:
            True si la session est verrouillée
        """
        if session_id not in self._locks:
            return False
        
        return self._locks[session_id].locked()
    
    def register_task(self, session_id: str, task: asyncio.Task):
        """
        Enregistrer une tâche de traitement pour une session
        
        Args:
            session_id: ID de la session
            task: Tâche asyncio
        """
        self._tasks[session_id] = task
        self._processing_start_times[session_id] = datetime.now(timezone.utc)
        logger.info(f"📝 Registered task for session {session_id}")
    
    def get_task(self, session_id: str) -> Optional[asyncio.Task]:
        """
        Obtenir la tâche de traitement d'une session
        
        Args:
            session_id: ID de la session
            
        Returns:
            asyncio.Task ou None
        """
        return self._tasks.get(session_id)
    
    async def cancel_task(self, session_id: str) -> bool:
        """
        Annuler la tâche de traitement d'une session
        
        Args:
            session_id: ID de la session
            
        Returns:
            True si l'annulation a réussi
        """
        task = self._tasks.get(session_id)
        
        if not task:
            logger.warning(f"⚠️ No task found for session {session_id}")
            return False
        
        if task.done():
            logger.info(f"✓ Task already completed for session {session_id}")
            return True
        
        try:
            task.cancel()
            logger.info(f"🛑 Cancelled task for session {session_id}")
            
            # Attendre que la tâche se termine
            try:
                await task
            except asyncio.CancelledError:
                logger.info(f"✓ Task cancellation confirmed for session {session_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error cancelling task for session {session_id}: {e}")
            return False
    
    def cleanup_session(self, session_id: str):
        """
        Nettoyer les ressources d'une session
        
        Args:
            session_id: ID de la session
        """
        # Supprimer le lock
        if session_id in self._locks:
            del self._locks[session_id]
        
        # Supprimer la tâche
        if session_id in self._tasks:
            del self._tasks[session_id]
        
        # Supprimer le temps de début
        if session_id in self._processing_start_times:
            del self._processing_start_times[session_id]
        
        logger.info(f"🧹 Cleaned up session {session_id}")
    
    def get_processing_time(self, session_id: str) -> Optional[float]:
        """
        Obtenir le temps de traitement d'une session
        
        Args:
            session_id: ID de la session
            
        Returns:
            Temps en secondes ou None
        """
        if session_id not in self._processing_start_times:
            return None
        
        start_time = self._processing_start_times[session_id]
        return (datetime.now(timezone.utc) - start_time).total_seconds()
    
    def get_status(self) -> Dict:
        """
        Obtenir le statut du gestionnaire de locks
        
        Returns:
            Dictionnaire avec les statistiques
        """
        return {
            'total_locks': len(self._locks),
            'active_locks': sum(1 for lock in self._locks.values() if lock.locked()),
            'total_tasks': len(self._tasks),
            'active_tasks': sum(1 for task in self._tasks.values() if not task.done()),
            'sessions': list(self._locks.keys())
        }


# Instance globale
_session_lock_manager: Optional[SessionLockManager] = None

def get_session_lock_manager() -> SessionLockManager:
    """
    Obtenir l'instance globale du SessionLockManager
    
    Returns:
        SessionLockManager instance
    """
    global _session_lock_manager
    
    if _session_lock_manager is None:
        _session_lock_manager = SessionLockManager()
    
    return _session_lock_manager
