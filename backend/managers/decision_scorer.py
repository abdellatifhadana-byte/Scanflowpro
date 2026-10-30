"""
ScanFlow Pro V7 - Decision Scorer
Intelligent code selection based on multiple factors
"""

import logging
from typing import List, Dict, Optional
import re

logger = logging.getLogger(__name__)

class DecisionScorer:
    """
    Système de notation intelligent pour choisir le meilleur code extrait
    """
    
    def __init__(self):
        self.weights = {
            'confidence': 0.35,        # 35% - Niveau de confiance de l'OCR/HTR
            'keyword_proximity': 0.25, # 25% - Proximité avec le mot-clé
            'roi_alignment': 0.20,     # 20% - Alignement avec la ROI définie
            'repetition': 0.10,        # 10% - Répétition du même code
            'validity': 0.10           # 10% - Validité du format
        }
        logger.info("🎯 DecisionScorer initialized with intelligent voting system")
    
    def score_candidate(
        self,
        code: str,
        confidence: float,
        method: str,
        keyword: Optional[str] = None,
        roi_used: bool = False,
        all_candidates: Optional[List[Dict]] = None
    ) -> Dict:
        """
        Calculer le score d'un candidat de code
        
        Args:
            code: Le code extrait
            confidence: Niveau de confiance (0-1)
            method: Méthode d'extraction (ocr/htr/context)
            keyword: Mot-clé recherché (optionnel)
            roi_used: Si une ROI a été utilisée
            all_candidates: Liste de tous les candidats pour comparaison
            
        Returns:
            Dictionnaire avec score et détails
        """
        scores = {}
        
        # 1. Score de confiance (35%)
        scores['confidence'] = confidence * self.weights['confidence']
        
        # 2. Score de proximité avec mot-clé (25%)
        if keyword:
            proximity_score = self._calculate_keyword_proximity(code, keyword, method)
            scores['keyword_proximity'] = proximity_score * self.weights['keyword_proximity']
        else:
            scores['keyword_proximity'] = 0.5 * self.weights['keyword_proximity']  # Neutre
        
        # 3. Score d'alignement ROI (20%)
        if roi_used:
            scores['roi_alignment'] = 1.0 * self.weights['roi_alignment']
        else:
            scores['roi_alignment'] = 0.5 * self.weights['roi_alignment']  # Pénalité légère
        
        # 4. Score de répétition (10%)
        if all_candidates:
            repetition_score = self._calculate_repetition_score(code, all_candidates)
            scores['repetition'] = repetition_score * self.weights['repetition']
        else:
            scores['repetition'] = 0.5 * self.weights['repetition']
        
        # 5. Score de validité (10%)
        validity_score = self._calculate_validity_score(code)
        scores['validity'] = validity_score * self.weights['validity']
        
        # Score total
        total_score = sum(scores.values())
        
        return {
            'code': code,
            'total_score': total_score,
            'confidence': confidence,
            'method': method,
            'scores': scores,
            'breakdown': {
                'confidence': f"{scores['confidence']:.3f} (weight: {self.weights['confidence']})",
                'keyword_proximity': f"{scores['keyword_proximity']:.3f} (weight: {self.weights['keyword_proximity']})",
                'roi_alignment': f"{scores['roi_alignment']:.3f} (weight: {self.weights['roi_alignment']})",
                'repetition': f"{scores['repetition']:.3f} (weight: {self.weights['repetition']})",
                'validity': f"{scores['validity']:.3f} (weight: {self.weights['validity']})"
            }
        }
    
    def _calculate_keyword_proximity(self, code: str, keyword: str, method: str) -> float:
        """
        Calculer la proximité avec le mot-clé
        
        Args:
            code: Code extrait
            keyword: Mot-clé recherché
            method: Méthode d'extraction
            
        Returns:
            Score entre 0 et 1
        """
        # Si le code a été trouvé avec le mot-clé (context method)
        if 'context' in method.lower() or 'keyword' in method.lower():
            return 1.0
        
        # Sinon, score neutre
        return 0.5
    
    def _calculate_repetition_score(self, code: str, all_candidates: List[Dict]) -> float:
        """
        Calculer le score basé sur la répétition du code
        
        Args:
            code: Code à évaluer
            all_candidates: Tous les candidats
            
        Returns:
            Score entre 0 et 1
        """
        if not all_candidates or len(all_candidates) < 2:
            return 0.5  # Neutre si pas assez de candidats
        
        # Compter combien de fois ce code apparaît
        count = sum(1 for c in all_candidates if c.get('code') == code)
        
        # Score basé sur la fréquence (plus fréquent = meilleur)
        max_count = len(all_candidates)
        return min(count / max_count * 2, 1.0)  # Normaliser
    
    def _calculate_validity_score(self, code: str) -> float:
        """
        Calculer le score de validité du format
        
        Args:
            code: Code à évaluer
            
        Returns:
            Score entre 0 et 1
        """
        if not code:
            return 0.0
        
        score = 0.5  # Score de base
        
        # Bonus si c'est uniquement des chiffres
        if code.isdigit():
            score += 0.3
        
        # Bonus si la longueur est raisonnable (6-12 caractères)
        if 6 <= len(code) <= 12:
            score += 0.2
        
        # Pénalité si trop court ou trop long
        if len(code) < 4 or len(code) > 15:
            score -= 0.2
        
        # Pénalité si contient des caractères étranges
        if re.search(r'[^a-zA-Z0-9\-_]', code):
            score -= 0.1
        
        return max(0.0, min(1.0, score))  # Clamper entre 0 et 1
    
    def select_best_candidate(self, candidates: List[Dict]) -> Optional[Dict]:
        """
        Sélectionner le meilleur candidat parmi une liste
        
        Args:
            candidates: Liste de candidats avec leurs scores
            
        Returns:
            Le meilleur candidat ou None
        """
        if not candidates:
            logger.warning("⚠️ No candidates to select from")
            return None
        
        # Trier par score total
        sorted_candidates = sorted(
            candidates,
            key=lambda c: c.get('total_score', 0),
            reverse=True
        )
        
        best = sorted_candidates[0]
        
        logger.info(f"🏆 Best candidate selected: {best['code']} (score: {best['total_score']:.3f})")
        logger.info(f"   Method: {best['method']}, Confidence: {best['confidence']:.3f}")
        
        # Log des alternatives
        if len(sorted_candidates) > 1:
            logger.info(f"   Alternatives:")
            for i, candidate in enumerate(sorted_candidates[1:3], 2):  # Top 3
                logger.info(f"   {i}. {candidate['code']} (score: {candidate['total_score']:.3f})")
        
        return best
    
    def explain_decision(self, selected_candidate: Dict, all_candidates: List[Dict]) -> str:
        """
        Générer une explication de la décision
        
        Args:
            selected_candidate: Candidat sélectionné
            all_candidates: Tous les candidats
            
        Returns:
            Chaîne explicative
        """
        explanation_parts = []
        
        explanation_parts.append(f"Code sélectionné: {selected_candidate['code']}")
        explanation_parts.append(f"Score total: {selected_candidate['total_score']:.3f}/1.0")
        explanation_parts.append(f"Méthode: {selected_candidate['method']}")
        explanation_parts.append(f"Confiance OCR/HTR: {selected_candidate['confidence']:.3f}")
        
        explanation_parts.append("\nDétail des scores:")
        for key, value in selected_candidate['breakdown'].items():
            explanation_parts.append(f"  • {key}: {value}")
        
        if len(all_candidates) > 1:
            explanation_parts.append(f"\nNombre de candidats évalués: {len(all_candidates)}")
        
        return "\n".join(explanation_parts)
