"""
Resonance Ten Scoring Service
Sophisticated compatibility scoring with signal modulation
"""

import math
try:
    import numpy as np
except Exception as e:
    np = None
    _import_err = e

def require_numpy():
    if np is None:
        raise RuntimeError(f"NumPy unavailable: {_import_err}")

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from resonance_config import get_resonance_config

@dataclass
class ResonanceSignal:
    """Individual resonance signal with confidence and modulation"""
    dimension: str
    base_score: float  # 0.0 to 1.0
    confidence: float  # 0.0 to 1.0 (birth time accuracy, etc.)
    hd_modulation: float  # -0.3 to +0.3 (Human Design influence)
    final_score: float  # Computed final score
    
@dataclass
class CompatibilityResult:
    """Complete compatibility analysis result"""
    overall_score: float
    dimension_scores: Dict[str, ResonanceSignal]
    confidence_level: str
    hd_insights: List[str]
    recommendations: List[str]

class ResonanceScorer:
    """Advanced scoring engine for Resonance Ten compatibility"""
    
    def __init__(self):
        self.config = get_resonance_config()
        self.dimensions = self.config['keys']
        
        # Scoring weights for different aspects
        self.base_weights = {
            'love': 0.15,
            'intimacy': 0.14,
            'communication': 0.13,
            'friendship': 0.12,
            'collaboration': 0.11,
            'lifestyle': 0.10,
            'decisions': 0.09,
            'support': 0.08,
            'growth': 0.08,
            'space': 0.10
        }
        
        # Human Design type compatibility matrix
        self.hd_type_compatibility = {
            ('Manifestor', 'Generator'): 0.8,
            ('Manifestor', 'Manifesting Generator'): 0.9,
            ('Manifestor', 'Projector'): 0.7,
            ('Manifestor', 'Reflector'): 0.6,
            ('Generator', 'Generator'): 0.9,
            ('Generator', 'Manifesting Generator'): 0.95,
            ('Generator', 'Projector'): 0.8,
            ('Generator', 'Reflector'): 0.7,
            ('Manifesting Generator', 'Manifesting Generator'): 0.9,
            ('Manifesting Generator', 'Projector'): 0.85,
            ('Manifesting Generator', 'Reflector'): 0.75,
            ('Projector', 'Projector'): 0.6,
            ('Projector', 'Reflector'): 0.8,
            ('Reflector', 'Reflector'): 0.5,
        }
    
    def compute_base_compatibility(self, user1_prefs: Dict, user2_prefs: Dict) -> Dict[str, float]:
        """Compute base compatibility scores for each dimension"""
        scores = {}
        
        for dimension in self.dimensions:
            if dimension in user1_prefs and dimension in user2_prefs:
                # Get preference values (1-10 scale)
                pref1 = user1_prefs[dimension]
                pref2 = user2_prefs[dimension]
                
                # Calculate compatibility using preference alignment
                # Higher scores when preferences are complementary or aligned
                diff = abs(pref1 - pref2)
                
                # Different scoring strategies per dimension
                if dimension in ['love', 'intimacy']:
                    # For love/intimacy, closer alignment is better
                    score = max(0, 1.0 - (diff / 9.0))
                elif dimension in ['communication', 'friendship']:
                    # For communication/friendship, some difference can be good
                    score = 1.0 - (diff / 10.0) if diff <= 3 else 0.7 - (diff - 3) * 0.1
                elif dimension in ['collaboration', 'decisions']:
                    # For collaboration/decisions, moderate alignment preferred
                    score = 1.0 - (diff / 8.0) if diff <= 4 else 0.5
                elif dimension in ['lifestyle', 'space']:
                    # For lifestyle/space, some flexibility is good
                    score = max(0.3, 1.0 - (diff / 7.0))
                else:  # support, growth
                    # For support/growth, alignment is important
                    score = max(0.2, 1.0 - (diff / 8.0))
                
                scores[dimension] = max(0.0, min(1.0, score))
            else:
                # Missing data - use neutral score
                scores[dimension] = 0.5
        
        return scores
    
    def apply_hd_modulation(self, base_scores: Dict[str, float], 
                           user1_hd: Dict, user2_hd: Dict) -> Dict[str, float]:
        """Apply Human Design modulation to base scores"""
        modulated_scores = base_scores.copy()
        
        # Get HD types
        type1 = user1_hd.get('type', 'Unknown')
        type2 = user2_hd.get('type', 'Unknown')
        
        # Get type compatibility multiplier
        type_key = tuple(sorted([type1, type2]))
        type_multiplier = self.hd_type_compatibility.get(type_key, 0.7)
        
        # Apply type-specific modulations
        for dimension in self.dimensions:
            base_score = modulated_scores[dimension]
            
            # Type-specific adjustments
            if dimension == 'communication':
                # Projectors excel at communication
                if 'Projector' in [type1, type2]:
                    modulated_scores[dimension] = min(1.0, base_score * 1.15)
            
            elif dimension == 'collaboration':
                # Generators work well together
                if type1 == 'Generator' and type2 == 'Generator':
                    modulated_scores[dimension] = min(1.0, base_score * 1.2)
            
            elif dimension == 'decisions':
                # Manifestors are natural decision makers
                if 'Manifestor' in [type1, type2]:
                    modulated_scores[dimension] = min(1.0, base_score * 1.1)
            
            elif dimension == 'space':
                # Reflectors need more space
                if 'Reflector' in [type1, type2]:
                    modulated_scores[dimension] = min(1.0, base_score * 1.25)
            
            # Apply overall type compatibility
            modulated_scores[dimension] = base_score * (0.7 + 0.3 * type_multiplier)
        
        return modulated_scores
    
    def calculate_confidence(self, user1_data: Dict, user2_data: Dict) -> float:
        """Calculate overal        # Apply overall type compatibility
        confidence_factors = []
        
        # Birth time accuracy
        for user_data in [user1_data, user2_data]:
            birth_data = user_data.get('birth_data', {})
            time_known = birth_data.get('time_known', False)
            if time_known:
                confidence_factors.append(0.9)
            else:
                confidence_factors.append(0.6)
        
        # Preference completeness
        for user_data in [user1_data, user2_data]:
            prefs = user_data.get('resonance_prefs', {})
            completeness = len(prefs) / len(self.dimensions)
            confidence_factors.append(completeness)
        
        # HD data completeness
        for user_data in [user1_data, user2_data]:
            hd_data = user_data.get('hd_data', {})
            hd_completeness = 1.0 if hd_data.get('type') else 0.5
            confidence_factors.append(hd_completeness)
        
        require_numpy()
        return np.mean(confidence_factors)
    
    def generate_insights(self, scores: Dict[str, float], 
                         user1_hd: Dict, user2_hd: Dict) -> List[str]:
        """Generate Human Design insights for the compatibility"""
        insights = []
        
        type1 = user1_hd.get('type', 'Unknown')
        type2 = user2_hd.get('type', 'Unknown')
        
        # Type-specific insights
        if type1 == 'Manifestor' or type2 == 'Manifestor':
            insights.append("Manifestor energy brings natural leadership and initiation to this connection.")
        
        if type1 == 'Generator' and type2 == 'Generator':
            insights.append("Two Generators create a powerful, sustainable energy dynamic together.")
        
        if 'Projector' in [type1, type2]:
            insights.append("Projector wisdom enhances guidance and recognition in this partnership.")
        
        if 'Reflector' in [type1, type2]:
            insights.append("Reflector presence brings unique perspective and environmental awareness.")
        
        # Score-based insights
        high_scores = [dim for dim, score in scores.items() if score > 0.8]
        if high_scores:
            insights.append(f"Exceptional alignment in: {', '.join(high_scores)}")
        
        growth_areas = [dim for dim, score in scores.items() if score < 0.6]
        if growth_areas:
            insights.append(f"Growth opportunities in: {', '.join(growth_areas)}")
        
        return insights
    
    def generate_recommendations(self, scores: Dict[str, float]) -> List[str]:
        """Generate actionable recommendations based on scores"""
        recommendations = []
        
        # Find strongest and weakest dimensions
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        strongest = sorted_scores[:3]
        weakest = sorted_scores[-2:]
        
        # Strength-based recommendations
        for dim, score in strongest:
            if score > 0.8:
                if dim == 'communication':
                    recommendations.append("Leverage your natural communication flow for deeper conversations.")
                elif dim == 'intimacy':
                    recommendations.append("Your intimacy potential is strong - create space for vulnerability.")
                elif dim == 'friendship':
                    recommendations.append("Build on your natural friendship foundation with shared activities.")
        
        # Growth-based recommendations
        for dim, score in weakest:
            if score < 0.6:
                if dim == 'communication':
                    recommendations.append("Practice active listening and express needs clearly.")
                elif dim == 'space':
                    recommendations.append("Discuss boundaries and individual space needs openly.")
                elif dim == 'decisions':
                    recommendations.append("Develop a decision-making process that honors both perspectives.")
        
        return recommendations
    
    def compute_compatibility(self, user1_data: Dict, user2_data: Dict) -> CompatibilityResult:
        """Main method to compute full compatibility analysis"""
        
        # Extract data
        user1_prefs = user1_data.get('resonance_prefs', {})
        user2_prefs = user2_data.get('resonance_prefs', {})
        user1_hd = user1_data.get('hd_data', {})
        user2_hd = user2_data.get('hd_data', {})
        
        # Compute base compatibility
        base_scores = self.compute_base_compatibility(user1_prefs, user2_prefs)
        
        # Apply Human Design modulation
        modulated_scores = self.apply_hd_modulation(base_scores, user1_hd, user2_hd)
        
        # Calculate confidence
        confidence = self.calculate_confidence(user1_data, user2_data)
        
        # Create resonance signals
        dimension_scores = {}
        for dimension in self.dimensions:
            base_score = base_scores.get(dimension, 0.5)
            final_score = modulated_scores.get(dimension, 0.5)
            hd_modulation = final_score - base_score
            
            dimension_scores[dimension] = ResonanceSignal(
                dimension=dimension,
                base_score=base_score,
                confidence=confidence,
                hd_modulation=hd_modulation,
                final_score=final_score
            )
        
        # Calculate overall score (weighted average)
        overall_score = sum(
            self.base_weights[dim] * signal.final_score 
            for dim, signal in dimension_scores.items()
        )
        
        # Determine confidence level
        if confidence > 0.8:
            confidence_level = "High"
        elif confidence > 0.6:
            confidence_level = "Medium"
        else:
            confidence_level = "Low"
        
        # Generate insights and recommendations
        final_scores = {dim: signal.final_score for dim, signal in dimension_scores.items()}
        insights = self.generate_insights(final_scores, user1_hd, user2_hd)
        recommendations = self.generate_recommendations(final_scores)
        
        return CompatibilityResult(
            overall_score=overall_score,
            dimension_scores=dimension_scores,
            confidence_level=confidence_level,
            hd_insights=insights,
            recommendations=recommendations
        )

# Utility functions for API integration
def score_compatibility(user1_id: int, user2_id: int, db_session) -> Dict:
    """Score compatibility between two users (for API endpoint)"""
    scorer = ResonanceScorer()
    
    # This would fetch user data from database
    # For now, return mock structure
    user1_data = {
        'resonance_prefs': {},
        'hd_data': {},
        'birth_data': {}
    }
    user2_data = {
        'resonance_prefs': {},
        'hd_data': {},
        'birth_data': {}
    }
    
    result = scorer.compute_compatibility(user1_data, user2_data)
    
    return {
        'overall_score': result.overall_score,
        'confidence_level': result.confidence_level,
        'dimension_scores': {
            dim: {
                'score': signal.final_score,
                'confidence': signal.confidence,
                'hd_modulation': signal.hd_modulation
            }
            for dim, signal in result.dimension_scores.items()
        },
        'insights': result.hd_insights,
        'recommendations': result.recommendations
    }

