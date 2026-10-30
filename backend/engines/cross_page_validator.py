"""
ScanFlow Pro V7 - Cross-Page Consistency Validator
Validates codes across multiple pages for consistency
"""

import logging
from typing import List, Dict, Optional, Tuple
from collections import Counter, defaultdict

logger = logging.getLogger(__name__)

class CrossPageValidator:
    """
    Validateur de cohérence entre pages
    Détecte et corrige les incohérences de codes entre pages
    """
    
    def __init__(self, auto_correct: bool = True):
        """
        Initialiser le validateur cross-page
        
        Args:
            auto_correct: Corriger automatiquement les incohérences
        """
        self.auto_correct = auto_correct
        self.page_codes = defaultdict(list)  # file_id -> [codes]
        self.correction_log = []
        
        logger.info(f"Cross-Page Validator initialisé (auto_correct={auto_correct})")
    
    def add_page(self, file_id: str, page_num: int, code: str, confidence: float):
        """
        Ajouter une page pour validation
        
        Args:
            file_id: ID du fichier
            page_num: Numéro de la page
            code: Code extrait
            confidence: Confiance
        """
        self.page_codes[file_id].append({
            "page_num": page_num,
            "code": code,
            "confidence": confidence
        })
    
    def validate_file(self, file_id: str) -> Dict:
        """
        Valider toutes les pages d'un fichier
        
        Args:
            file_id: ID du fichier
            
        Returns:
            Résultat de validation avec corrections
        """
        pages = self.page_codes.get(file_id, [])
        
        if not pages:
            return {"status": "no_pages", "corrections": []}
        
        if len(pages) == 1:
            return {"status": "single_page", "corrections": []}
        
        logger.info(f"📊 Validation cross-page: {file_id} ({len(pages)} pages)")
        
        # Compter les codes
        codes = [p["code"] for p in pages]
        code_counts = Counter(codes)
        
        # Vérifier la cohérence
        if len(code_counts) == 1:
            # Tous les codes identiques
            return {
                "status": "consistent",
                "code": codes[0],
                "pages": len(pages),
                "corrections": []
            }
        
        # Incohérence détectée
        logger.warning(f"⚠️ Incohérence détectée: {len(code_counts)} codes différents")
        
        # Trouver le code majoritaire
        most_common_code, count = code_counts.most_common(1)[0]
        majority_threshold = len(pages) * 0.7
        
        corrections = []
        
        if count >= majority_threshold:
            # Majorité claire → corriger les autres
            logger.info(f"✓ Majorité claire: {most_common_code} ({count}/{len(pages)})")
            
            if self.auto_correct:
                for page in pages:
                    if page["code"] != most_common_code:
                        corrections.append({
                            "page_num": page["page_num"],
                            "old_code": page["code"],
                            "new_code": most_common_code,
                            "reason": "majority_correction",
                            "confidence_before": page["confidence"],
                            "confidence_after": 0.95  # Haute confiance après correction
                        })
                        
                        # Enregistrer
                        self.correction_log.append({
                            "file_id": file_id,
                            "page_num": page["page_num"],
                            "correction": corrections[-1]
                        })
            
            return {
                "status": "majority_corrected" if corrections else "majority",
                "code": most_common_code,
                "pages": len(pages),
                "corrections": corrections,
                "code_distribution": dict(code_counts)
            }
        
        # Pas de majorité claire → conflit
        return {
            "status": "conflict",
            "pages": len(pages),
            "code_distribution": dict(code_counts),
            "corrections": [],
            "requires_review": True
        }
    
    def validate_all_files(self) -> Dict:
        """
        Valider tous les fichiers
        
        Returns:
            Résultats pour tous les fichiers
        """
        results = {}
        total_corrections = 0
        
        for file_id in self.page_codes.keys():
            result = self.validate_file(file_id)
            results[file_id] = result
            total_corrections += len(result.get("corrections", []))
        
        logger.info(f"✓ Validation cross-page terminée: {total_corrections} corrections")
        
        return {
            "total_files": len(results),
            "total_corrections": total_corrections,
            "files": results
        }
    
    def detect_similar_codes(
        self,
        code: str,
        all_codes: List[str],
        threshold: int = 1
    ) -> List[str]:
        """
        Détecter les codes similaires
        
        Args:
            code: Code à comparer
            all_codes: Tous les codes
            threshold: Distance maximale
            
        Returns:
            Codes similaires
        """
        similar = []
        
        for other_code in all_codes:
            if code == other_code:
                continue
            
            distance = self._levenshtein_distance(code, other_code)
            if distance <= threshold:
                similar.append(other_code)
        
        return similar
    
    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """Calculer la distance de Levenshtein"""
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    def get_correction_log(self) -> List[Dict]:
        """Obtenir le journal des corrections"""
        return self.correction_log
    
    def reset(self):
        """Réinitialiser l'état"""
        self.page_codes.clear()
        self.correction_log.clear()
        logger.info("Cross-Page Validator reset")

# Test
def test_cross_page():
    """Test du validateur cross-page"""
    validator = CrossPageValidator(auto_correct=True)
    
    # Ajouter des pages
    validator.add_page("file1", 1, "123456", 0.85)
    validator.add_page("file1", 2, "123456", 0.90)
    validator.add_page("file1", 3, "123458", 0.65)  # Différent!
    validator.add_page("file1", 4, "123456", 0.88)
    
    # Valider
    result = validator.validate_file("file1")
    
    print("=" * 60)
    print("🧪 Test Cross-Page Validator")
    print("=" * 60)
    print(f"Status: {result['status']}")
    print(f"Code: {result.get('code', 'N/A')}")
    print(f"Corrections: {len(result.get('corrections', []))}")
    
    if result.get('corrections'):
        print("\nCorrections:")
        for corr in result['corrections']:
            print(f"  Page {corr['page_num']}: {corr['old_code']} → {corr['new_code']}")

if __name__ == "__main__":
    test_cross_page()
