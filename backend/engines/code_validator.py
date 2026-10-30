"""
ScanFlow Pro V7 - Code Validation Engine - DAM FIXED
Enterprise-Grade Code Validation with Strict Rules
"""

import re
import logging
from typing import Optional, Dict, List, Tuple
from enum import Enum

logger = logging.getLogger(__name__)

class ValidationLevel(Enum):
    """Niveaux de validation"""
    CONFIRMED = "confirmed"      # Haute confiance - accepté
    LIKELY = "likely"            # Bonne confiance - accepté avec marquage
    SUSPICIOUS = "suspicious"    # Confiance moyenne - révision recommandée
    REJECTED = "rejected"        # Rejeté - ne pas utiliser

class CodeValidator:
    """
    Validateur de codes avec règles strictes
    Empêche les codes invalides d'être acceptés
    """
    
    def __init__(
        self,
        min_digits: int = 4,      # ✅ CORRECTED: Now accepts min_digits
        max_digits: int = 12,     # ✅ CORRECTED: Now accepts max_digits
        strict_mode: bool = True
    ):
        """
        Initialiser le validateur
        
        Args:
            min_digits: Longueur minimale du code
            max_digits: Longueur maximale du code
            strict_mode: Mode strict (rejette davantage)
        """
        self.min_digits = min_digits
        self.max_length = max_digits  # Keep for compatibility
        self.max_digits = max_digits
        self.strict_mode = strict_mode
        
        # Patterns suspects (à éviter)
        self.suspicious_patterns = [
            r'^0{4,}$',      # 0000...
            r'^1{4,}$',      # 1111...
            r'^9{4,}$',      # 9999...
            r'^1234+',       # 1234567...
            r'^9876+',       # 9876543...
        ]
        
        # Historique des codes vus (pour détecter duplications)
        self.seen_codes = set()
        
        logger.info(f"Code Validator initialisé (strict={strict_mode}, min={min_digits}, max={max_digits})")
    
    def validate(
        self,
        code: str,
        confidence: float,
        source: str = "unknown",
        context: Optional[Dict] = None
    ) -> Tuple[ValidationLevel, float, List[str]]:
        """
        Valider un code extrait
        
        Args:
            code: Le code à valider
            confidence: Confiance de l'extraction (0-1)
            source: Source (ocr/htr/yolo)
            context: Contexte additionnel
            
        Returns:
            (niveau_validation, confiance_ajustée, raisons)
        """
        reasons = []
        adjusted_confidence = confidence
        
        # 1. Vérifications de base
        if not code:
            return ValidationLevel.REJECTED, 0.0, ["Code vide"]
        
        if not code.isdigit():
            return ValidationLevel.REJECTED, 0.0, ["Code contient des caractères non-numériques"]
        
        # 2. Vérifier la longueur
        if len(code) < self.min_digits:
            return ValidationLevel.REJECTED, 0.0, [f"Code trop court ({len(code)} < {self.min_digits})"]
        
        if len(code) > self.max_digits:
            return ValidationLevel.REJECTED, 0.0, [f"Code trop long ({len(code)} > {self.max_digits})"]
        
        reasons.append(f"Longueur valide ({len(code)})")
        
        # 3. Vérifier les patterns suspects
        for pattern in self.suspicious_patterns:
            if re.match(pattern, code):
                if self.strict_mode:
                    return ValidationLevel.REJECTED, 0.0, [f"Pattern suspect: {pattern}"]
                else:
                    adjusted_confidence *= 0.5
                    reasons.append(f"⚠️ Pattern suspect: {pattern}")
        
        # 4. Vérifier la confiance minimale
        if self.strict_mode:
            min_conf = 0.70  # ✅ REDUCED from 0.75 for DAM patterns
        else:
            min_conf = 0.55  # ✅ REDUCED from 0.60
        
        if confidence < min_conf:
            if self.strict_mode:
                # DAM pattern bonus
                if context and context.get("dam_pattern", False):
                    logger.info(f"[DAM-VALIDATION] DAM pattern detected, accepting with lower confidence")
                    reasons.append(f"⚠️ Confiance basse mais DAM pattern accepté ({confidence:.2f} < {min_conf})")
                else:
                    return ValidationLevel.SUSPICIOUS, adjusted_confidence, [f"Confiance trop basse ({confidence:.2f} < {min_conf})"]
            else:
                reasons.append(f"⚠️ Confiance faible ({confidence:.2f})")
        
        # 5. Vérifier la source
        if source in ["ocr", "yolo+ocr", "dam_pattern"]:  # ✅ ADDED dam_pattern
            adjusted_confidence *= 1.1  # OCR plus fiable
            reasons.append(f"Source fiable: {source}")
        elif source == "htr":
            adjusted_confidence *= 0.9  # HTR moins fiable
            reasons.append(f"Source HTR (ajustement -10%)")
        
        # 6. Vérifier le contexte (keyword match)
        if context and context.get("keyword_found"):
            adjusted_confidence *= 1.15
            reasons.append("✓ Keyword trouvé (bonus +15%)")
        
        # 7. DAM Pattern bonus (NEW)
        if context and context.get("dam_pattern"):
            adjusted_confidence *= 1.25  # ✅ HIGH bonus for DAM patterns
            reasons.append("✓ Pattern DAM administratif (+25%)")
        
        # 8. Détection de duplication suspecte
        if code in self.seen_codes:
            reasons.append("⚠️ Code déjà vu (possible duplication)")
            if self.strict_mode:
                adjusted_confidence *= 0.8
        else:
            self.seen_codes.add(code)
        
        # 9. Check digit validation (si applicable)
        if context and context.get("check_digit_enabled"):
            if self._validate_check_digit(code):
                adjusted_confidence *= 1.2
                reasons.append("✓ Check digit valide (+20%)")
            else:
                if self.strict_mode:
                    return ValidationLevel.REJECTED, 0.0, ["Check digit invalide"]
                else:
                    adjusted_confidence *= 0.6
                    reasons.append("⚠️ Check digit invalide (-40%)")
        
        # Limiter la confiance à 1.0
        adjusted_confidence = min(adjusted_confidence, 1.0)
        
        # 10. Déterminer le niveau final
        if adjusted_confidence >= 0.80:  # ✅ REDUCED from 0.85
            level = ValidationLevel.CONFIRMED
        elif adjusted_confidence >= 0.65:  # ✅ REDUCED from 0.70
            level = ValidationLevel.LIKELY
        elif adjusted_confidence >= 0.50:
            level = ValidationLevel.SUSPICIOUS
        else:
            level = ValidationLevel.REJECTED
        
        # En mode strict, on rejette SUSPICIOUS mais pas si DAM pattern
        if self.strict_mode and level == ValidationLevel.SUSPICIOUS:
            if context and context.get("dam_pattern"):
                logger.info(f"[DAM-VALIDATION] Accepting suspicious DAM pattern: {code}")
                level = ValidationLevel.LIKELY
                reasons.append("⚠️ DAM pattern accepté malgré suspicion")
            else:
                level = ValidationLevel.REJECTED
                reasons.append("❌ Rejeté (mode strict)")
        
        logger.info(f"Code '{code}': {level.value} (conf={adjusted_confidence:.2f})")
        
        return level, adjusted_confidence, reasons
    
    def _validate_check_digit(self, code: str) -> bool:
        """
        Valider le check digit (algorithme Luhn par exemple)
        
        Args:
            code: Le code à vérifier
            
        Returns:
            True si valide
        """
        try:
            # Algorithme Luhn (comme cartes bancaires)
            digits = [int(d) for d in code]
            checksum = 0
            
            for i, digit in enumerate(reversed(digits)):
                if i % 2 == 1:
                    digit *= 2
                    if digit > 9:
                        digit -= 9
                checksum += digit
            
            return checksum % 10 == 0
        except Exception as e:
            logger.error(f"Erreur check digit: {e}")
            return False
    
    def compare_candidates(
        self,
        candidates: List[Dict]
    ) -> Optional[Dict]:
        """
        Comparer plusieurs candidats et choisir le meilleur
        
        Args:
            candidates: Liste de codes candidats avec metadata
            
        Returns:
            Meilleur candidat ou None
        """
        if not candidates:
            return None
        
        # Valider chaque candidat
        validated = []
        for cand in candidates:
            code = cand.get("code", "")
            conf = cand.get("confidence", 0.0)
            source = cand.get("source", "unknown")
            context = cand.get("context", {})
            
            level, adj_conf, reasons = self.validate(code, conf, source, context)
            
            if level != ValidationLevel.REJECTED:
                validated.append({
                    **cand,
                    "validation_level": level.value,
                    "adjusted_confidence": adj_conf,
                    "validation_reasons": reasons
                })
        
        if not validated:
            logger.warning("Tous les candidats rejetés")
            return None
        
        # Trier par confiance ajustée
        validated.sort(key=lambda x: x["adjusted_confidence"], reverse=True)
        
        best = validated[0]
        logger.info(f"Meilleur candidat: {best['code']} ({best['validation_level']})")
        
        return best
    
    def detect_similar_codes(
        self,
        code: str,
        threshold: int = 2
    ) -> List[str]:
        """
        Détecter les codes similaires (distance de Levenshtein)
        
        Args:
            code: Code à comparer
            threshold: Distance maximale
            
        Returns:
            Liste des codes similaires
        """
        similar = []
        
        for seen_code in self.seen_codes:
            distance = self._levenshtein_distance(code, seen_code)
            if 0 < distance <= threshold:
                similar.append(seen_code)
        
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
    
    def get_statistics(self) -> Dict:
        """Obtenir des statistiques de validation"""
        return {
            "total_codes_seen": len(self.seen_codes),
            "strict_mode": self.strict_mode,
            "min_digits": self.min_digits,
            "max_digits": self.max_digits
        }
    
    def reset(self):
        """Réinitialiser l'état (pour nouvelle session)"""
        self.seen_codes.clear()
        logger.info("Validator reset")

# ================================
# Test
# ================================
def test_validator():
    """Test du validateur"""
    validator = CodeValidator(min_digits=4, max_digits=12, strict_mode=True)
    
    test_cases = [
        ("123456", 0.90, "ocr", {"keyword_found": True}),
        ("54621", 0.68, "dam_pattern", {"dam_pattern": True}),  # DAM example
        ("000000", 0.95, "ocr", {}),
        ("123", 0.90, "ocr", {}),
        ("12345678901234", 0.90, "ocr", {}),
        ("abc123", 0.90, "ocr", {}),
        ("789456", 0.65, "htr", {}),
        ("789456", 0.88, "yolo+ocr", {"keyword_found": True}),
    ]
    
    print("=" * 60)
    print("🧪 Test Code Validator DAM Edition")
    print("=" * 60)
    
    for code, conf, source, ctx in test_cases:
        level, adj_conf, reasons = validator.validate(code, conf, source, ctx)
        print(f"\nCode: '{code}'")
        print(f"  Niveau: {level.value}")
        print(f"  Confiance: {conf:.2f} → {adj_conf:.2f}")
        print(f"  Raisons: {', '.join(reasons)}")

if __name__ == "__main__":
    test_validator()