"""
ScanFlow Pro V7 - Candidate Ensemble Engine
Multi-Engine Voting + Score Fusion + Intelligent Decision Making
"""

import logging
from typing import List, Dict, Optional, Tuple
from collections import Counter
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class Candidate:
    """Candidat de code avec métadonnées"""
    code: str
    confidence: float
    source: str
    method: str
    context: Dict
    
    def __hash__(self):
        return hash(self.code)
    
    def __eq__(self, other):
        return self.code == other.code

class CandidateEnsemble:
    """
    Système de vote et fusion intelligent pour les codes extraits
    Combine OCR + HTR + YOLO + Context pour choisir le meilleur code
    """
    
def __init__(
    self,
    weights: Optional[Dict[str, float]] = None,
    voting_threshold: float = 0.55  # ✅ REDUCED from 0.60/0.65
):
    """
    Initialiser l'ensemble
    
    Args:
        weights: Poids pour chaque source
        voting_threshold: Seuil minimal pour accepter un vote
    """
    # Poids par défaut pour chaque source
    self.weights = weights or {
        "ocr": 0.40,
        "htr": 0.25,
        "yolo+ocr": 0.45,
        "keyword": 0.20,
        "context": 0.15,
        "dam_pattern": 0.60,  # ✅ NOUVEAU: Très haute priorité
        "dam_window": 0.65,   # ✅ NOUVEAU: Plus haute que YOLO
    }
    
    self.voting_threshold = voting_threshold
    
    logger.info(f"Ensemble DAM initialisé avec poids: {self.weights}")
    
    def vote(
        self,
        candidates: List[Candidate]
    ) -> Optional[Dict]:
        """
        Voter parmi les candidats et choisir le meilleur
        
        Args:
            candidates: Liste des candidats
            
        Returns:
            Meilleur candidat avec métadonnées ou None
        """
        if not candidates:
            logger.warning("Aucun candidat pour le vote")
            return None
        
        logger.info(f"🗳️ Vote parmi {len(candidates)} candidats")
        
        # 1. Compter les occurrences de chaque code
        code_counts = Counter([c.code for c in candidates])
        
        # 2. Calculer le score pour chaque code unique
        scores = {}
        details = {}
        
        for code in code_counts.keys():
            # Récupérer tous les candidats pour ce code
            code_candidates = [c for c in candidates if c.code == code]
            
            # Calculer le score combiné
            score, info = self._calculate_combined_score(code_candidates)
            
            scores[code] = score
            details[code] = {
                "count": code_counts[code],
                "candidates": len(code_candidates),
                "score": score,
                "sources": [c.source for c in code_candidates],
                "methods": [c.method for c in code_candidates],
                "info": info
            }
        
        # 3. Vérifier s'il y a consensus
        if len(scores) == 1:
            # Un seul code → consensus parfait
            code = list(scores.keys())[0]
            logger.info(f"✅ Consensus parfait: {code}")
            details[code]["consensus"] = "perfect"
        elif len(scores) == 2:
            # Deux codes → vérifier s'ils sont très proches
            codes = list(scores.keys())
            if self._are_similar(codes[0], codes[1]):
                logger.info(f"⚠️ Codes similaires: {codes[0]} vs {codes[1]}")
                details[codes[0]]["consensus"] = "similar"
                details[codes[1]]["consensus"] = "similar"
        else:
            logger.warning(f"⚠️ Conflit: {len(scores)} codes différents")
        
        # 4. Choisir le meilleur code
        best_code = max(scores, key=scores.get)
        best_score = scores[best_code]
        
        logger.info(f"🏆 Meilleur code: {best_code} (score={best_score:.3f})")
        
        # 5. Vérifier si le score dépasse le seuil
        if best_score < self.voting_threshold:
            logger.warning(f"❌ Score trop bas ({best_score:.3f} < {self.voting_threshold})")
            return {
                "code": None,
                "status": "rejected",
                "reason": "score_too_low",
                "best_candidate": best_code,
                "score": best_score,
                "all_scores": scores,
                "details": details
            }
        
        # 6. Retourner le résultat
        best_candidates = [c for c in candidates if c.code == best_code]
        
        return {
            "code": best_code,
            "status": "accepted",
            "score": best_score,
            "confidence": best_score,
            "vote_count": code_counts[best_code],
            "total_candidates": len(candidates),
            "sources": [c.source for c in best_candidates],
            "methods": [c.method for c in best_candidates],
            "consensus": details[best_code].get("consensus", "majority"),
            "all_scores": scores,
            "details": details[best_code]
        }
    
    def _calculate_combined_score(
        self,
        candidates: List[Candidate]
    ) -> Tuple[float, Dict]:
        """
        Calculer le score combiné pour un groupe de candidats
        
        Args:
            candidates: Candidats avec le même code
            
        Returns:
            (score_combiné, informations_détaillées)
        """
        # Initialiser les scores
        base_score = 0.0
        bonus_score = 0.0
        info = {
            "base_components": [],
            "bonuses": [],
            "penalties": []
        }
        
        # 1. Score de base (moyenne pondérée des confidences)
        for cand in candidates:
            weight = self.weights.get(cand.source, 0.3)
            contribution = cand.confidence * weight
            base_score += contribution
            info["base_components"].append({
                "source": cand.source,
                "confidence": cand.confidence,
                "weight": weight,
                "contribution": contribution
            })
        
        # Normaliser par le nombre de sources
        if candidates:
            base_score /= len(candidates)
        
        # 2. Bonus pour le consensus (plusieurs sources donnent le même code)
        if len(candidates) >= 2:
            consensus_bonus = min(0.15, len(candidates) * 0.05)
            bonus_score += consensus_bonus
            info["bonuses"].append({
                "type": "consensus",
                "value": consensus_bonus,
                "reason": f"{len(candidates)} sources concordent"
            })
        
        # 3. Bonus si keyword trouvé dans le contexte
        keyword_found = any(
            c.context.get("keyword_found", False) for c in candidates
        )
        if keyword_found:
            keyword_bonus = 0.10
            bonus_score += keyword_bonus
            info["bonuses"].append({
                "type": "keyword",
                "value": keyword_bonus,
                "reason": "Keyword trouvé à proximité"
            })
        
        # 4. Bonus si YOLO a détecté la région
        yolo_detected = any(
            "yolo" in c.source.lower() for c in candidates
        )
        if yolo_detected:
            yolo_bonus = 0.08
            bonus_score += yolo_bonus
            info["bonuses"].append({
                "type": "yolo",
                "value": yolo_bonus,
                "reason": "YOLO a détecté la région du code"
            })
        
        # 5. Vérifier les incohérences (pénalités)
        confidences = [c.confidence for c in candidates]
        if confidences:
            std_dev = self._std_deviation(confidences)
            if std_dev > 0.2:
                penalty = -0.10
                bonus_score += penalty
                info["penalties"].append({
                    "type": "inconsistency",
                    "value": penalty,
                    "reason": f"Confiances incohérentes (std={std_dev:.2f})"
                })
        
        # 6. Score final
        final_score = min(base_score + bonus_score, 1.0)
        
        info["base_score"] = base_score
        info["bonus_score"] = bonus_score
        info["final_score"] = final_score
        
        return final_score, info
    
    def _std_deviation(self, values: List[float]) -> float:
        """Calculer l'écart-type"""
        if not values:
            return 0.0
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance ** 0.5
    
    def _are_similar(self, code1: str, code2: str, threshold: int = 1) -> bool:
        """
        Vérifier si deux codes sont similaires (distance de Levenshtein)
        
        Args:
            code1, code2: Codes à comparer
            threshold: Distance maximale pour être considérés similaires
            
        Returns:
            True si similaires
        """
        # Distance de Levenshtein simple
        if len(code1) != len(code2):
            return False
        
        distance = sum(c1 != c2 for c1, c2 in zip(code1, code2))
        return distance <= threshold
    
    def analyze_conflicts(
        self,
        candidates: List[Candidate]
    ) -> Dict:
        """
        Analyser les conflits entre candidats
        
        Args:
            candidates: Liste des candidats
            
        Returns:
            Analyse des conflits
        """
        codes = [c.code for c in candidates]
        unique_codes = set(codes)
        
        if len(unique_codes) == 1:
            return {
                "conflict": False,
                "type": "consensus",
                "message": "Tous les candidats sont d'accord"
            }
        
        # Compter les occurrences
        counts = Counter(codes)
        most_common = counts.most_common(1)[0]
        
        if most_common[1] >= len(candidates) * 0.7:
            return {
                "conflict": False,
                "type": "majority",
                "message": f"Majorité claire: {most_common[0]} ({most_common[1]}/{len(candidates)})"
            }
        
        return {
            "conflict": True,
            "type": "split",
            "message": f"{len(unique_codes)} codes différents sans majorité claire",
            "codes": dict(counts)
        }
    
    def get_top_k(
        self,
        candidates: List[Candidate],
        k: int = 3
    ) -> List[Dict]:
        """
        Obtenir les k meilleurs candidats
        
        Args:
            candidates: Liste des candidats
            k: Nombre de candidats à retourner
            
        Returns:
            Top-K candidats triés par score
        """
        # Grouper par code
        code_groups = {}
        for cand in candidates:
            if cand.code not in code_groups:
                code_groups[cand.code] = []
            code_groups[cand.code].append(cand)
        
        # Calculer le score pour chaque groupe
        scored = []
        for code, group in code_groups.items():
            score, info = self._calculate_combined_score(group)
            scored.append({
                "code": code,
                "score": score,
                "count": len(group),
                "sources": [c.source for c in group],
                "info": info
            })
        
        # Trier par score
        scored.sort(key=lambda x: x["score"], reverse=True)
        
        return scored[:k]

# ================================
# Test
# ================================
def test_ensemble():
    """Test du système de vote"""
    ensemble = CandidateEnsemble()
    
    # Créer des candidats de test
    candidates = [
        Candidate("123456", 0.85, "ocr", "roi", {"keyword_found": True}),
        Candidate("123456", 0.78, "htr", "roi", {}),
        Candidate("123456", 0.92, "yolo+ocr", "box", {"yolo_detected": True}),
        Candidate("123458", 0.65, "ocr", "fullpage", {}),
    ]
    
    print("=" * 60)
    print("🧪 Test Candidate Ensemble")
    print("=" * 60)
    
    # Test vote
    result = ensemble.vote(candidates)
    
    if result:
        print(f"\n📊 Résultat du vote:")
        print(f"  Code: {result['code']}")
        print(f"  Status: {result['status']}")
        print(f"  Score: {result['score']:.3f}")
        print(f"  Consensus: {result.get('consensus', 'N/A')}")
        print(f"  Sources: {result['sources']}")
    
    # Test top-k
    print(f"\n🏆 Top-3 candidats:")
    top_k = ensemble.get_top_k(candidates, k=3)
    for i, cand in enumerate(top_k, 1):
        print(f"  {i}. {cand['code']} (score={cand['score']:.3f}, count={cand['count']})")

if __name__ == "__main__":
    test_ensemble()
