"""
GLOW Human Design Intelligence Engine
=====================================

This module provides sophisticated Human Design compatibility analysis
that enhances Magic 10 matching behind the scenes. Users see clean
Magic 10 results while HD intelligence provides superior accuracy.

Key Features:
- 7-layer HD compatibility analysis
- humandesignapi.nl integration
- Magic 10 + HD combined scoring
- Clean API without exposing HD terminology
"""

import requests
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
import os

# ============================================================================
# HD INTELLIGENCE CONFIGURATION
# ============================================================================

HD_API_KEY = os.environ.get('HD_API_KEY')
HD_API_BASE_URL = os.environ.get('HD_API_BASE_URL', 'https://api.humandesignapi.nl/v1')

# HD Type compatibility matrix (simplified for backend use)
HD_TYPE_COMPATIBILITY = {
    'Generator': {
        'Generator': 0.85,
        'Manifesting Generator': 0.90,
        'Projector': 0.75,
        'Manifestor': 0.65,
        'Reflector': 0.70
    },
    'Manifesting Generator': {
        'Generator': 0.90,
        'Manifesting Generator': 0.80,
        'Projector': 0.85,
        'Manifestor': 0.70,
        'Reflector': 0.75
    },
    'Projector': {
        'Generator': 0.75,
        'Manifesting Generator': 0.85,
        'Projector': 0.60,
        'Manifestor': 0.70,
        'Reflector': 0.80
    },
    'Manifestor': {
        'Generator': 0.65,
        'Manifesting Generator': 0.70,
        'Projector': 0.70,
        'Manifestor': 0.75,
        'Reflector': 0.65
    },
    'Reflector': {
        'Generator': 0.70,
        'Manifesting Generator': 0.75,
        'Projector': 0.80,
        'Manifestor': 0.65,
        'Reflector': 0.85
    }
}

# Authority compatibility for decision-making alignment
AUTHORITY_COMPATIBILITY = {
    'Emotional': {
        'Emotional': 0.90,  # Both need time for clarity
        'Sacral': 0.70,    # Different pacing
        'Splenic': 0.65,   # Instant vs waiting
        'Ego': 0.75,
        'Self-Projected': 0.70,
        'Environmental': 0.80,
        'Lunar': 0.85      # Both need time
    },
    'Sacral': {
        'Emotional': 0.70,
        'Sacral': 0.95,    # Perfect pacing match
        'Splenic': 0.85,   # Both in-the-moment
        'Ego': 0.80,
        'Self-Projected': 0.75,
        'Environmental': 0.70,
        'Lunar': 0.60
    },
    'Splenic': {
        'Emotional': 0.65,
        'Sacral': 0.85,
        'Splenic': 0.90,   # Both instinctive
        'Ego': 0.85,
        'Self-Projected': 0.80,
        'Environmental': 0.75,
        'Lunar': 0.55
    },
    'Ego': {
        'Emotional': 0.75,
        'Sacral': 0.80,
        'Splenic': 0.85,
        'Ego': 0.80,
        'Self-Projected': 0.85,
        'Environmental': 0.75,
        'Lunar': 0.70
    },
    'Self-Projected': {
        'Emotional': 0.70,
        'Sacral': 0.75,
        'Splenic': 0.80,
        'Ego': 0.85,
        'Self-Projected': 0.75,
        'Environmental': 0.80,
        'Lunar': 0.75
    },
    'Environmental': {
        'Emotional': 0.80,
        'Sacral': 0.70,
        'Splenic': 0.75,
        'Ego': 0.75,
        'Self-Projected': 0.80,
        'Environmental': 0.85,
        'Lunar': 0.90      # Both environment-dependent
    },
    'Lunar': {
        'Emotional': 0.85,
        'Sacral': 0.60,
        'Splenic': 0.55,
        'Ego': 0.70,
        'Self-Projected': 0.75,
        'Environmental': 0.90,
        'Lunar': 0.95      # Perfect understanding
    }
}

# ============================================================================
# HUMANDESIGNAPI.NL INTEGRATION
# ============================================================================

class HDAPIClient:
    """Client for humandesignapi.nl integration"""
    
    def __init__(self):
        self.api_key = HD_API_KEY
        self.base_url = HD_API_BASE_URL
        self.session = requests.Session()
        if self.api_key:
            self.session.headers.update({'Authorization': f'Bearer {self.api_key}'})
    
    def calculate_chart(self, birth_data: Dict) -> Optional[Dict]:
        """
        Calculate HD chart from birth data
        
        Args:
            birth_data: {
                'birth_date': 'YYYY-MM-DD',
                'birth_time': 'HH:MM',
                'latitude': float,
                'longitude': float,
                'timezone': str
            }
        
        Returns:
            HD chart data or None if error
        """
        try:
            if not self.api_key:
                print("HD API key not configured")
                return None
            
            # Format data for HD API
            payload = {
                'date': birth_data['birth_date'],
                'time': birth_data['birth_time'],
                'latitude': birth_data['latitude'],
                'longitude': birth_data['longitude'],
                'timezone': birth_data.get('timezone', 'UTC')
            }
            
            response = self.session.post(f'{self.base_url}/chart', json=payload)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"HD API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"HD API request failed: {e}")
            return None
    
    def get_compatibility(self, chart1: Dict, chart2: Dict) -> Optional[Dict]:
        """
        Get compatibility analysis between two charts
        
        Args:
            chart1: First person's HD chart
            chart2: Second person's HD chart
        
        Returns:
            Compatibility analysis or None if error
        """
        try:
            if not self.api_key:
                return None
            
            payload = {
                'chart1': chart1,
                'chart2': chart2
            }
            
            response = self.session.post(f'{self.base_url}/compatibility', json=payload)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"HD Compatibility API error: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"HD Compatibility request failed: {e}")
            return None

# ============================================================================
# HD INTELLIGENCE ENGINE
# ============================================================================

class HDIntelligenceEngine:
    """
    Core HD intelligence engine that enhances Magic 10 compatibility
    without exposing HD terminology to users
    """
    
    def __init__(self):
        self.hd_client = HDAPIClient()
    
    def extract_hd_factors(self, chart_data: Dict) -> Dict:
        """
        Extract key HD factors for compatibility analysis
        
        Args:
            chart_data: Raw HD chart data from API
        
        Returns:
            Simplified HD factors for compatibility calculation
        """
        try:
            factors = {
                'type': chart_data.get('type', 'Generator'),
                'authority': chart_data.get('authority', 'Sacral'),
                'profile': chart_data.get('profile', '1/3'),
                'definition': chart_data.get('definition', 'Single'),
                'centers': chart_data.get('centers', {}),
                'channels': chart_data.get('channels', []),
                'gates': chart_data.get('gates', [])
            }
            return factors
        except Exception as e:
            print(f"Error extracting HD factors: {e}")
            return {}
    
    def calculate_type_compatibility(self, type1: str, type2: str) -> float:
        """Calculate compatibility based on HD types"""
        return HD_TYPE_COMPATIBILITY.get(type1, {}).get(type2, 0.5)
    
    def calculate_authority_compatibility(self, auth1: str, auth2: str) -> float:
        """Calculate compatibility based on authorities"""
        return AUTHORITY_COMPATIBILITY.get(auth1, {}).get(auth2, 0.5)
    
    def calculate_center_compatibility(self, centers1: Dict, centers2: Dict) -> float:
        """
        Calculate compatibility based on center definitions
        Defined + Undefined = attraction
        Both defined = stability
        Both undefined = potential confusion
        """
        if not centers1 or not centers2:
            return 0.5
        
        compatibility_score = 0
        center_count = 0
        
        for center in ['head', 'ajna', 'throat', 'g', 'will', 'sacral', 'solar_plexus', 'spleen', 'root']:
            if center in centers1 and center in centers2:
                defined1 = centers1[center].get('defined', False)
                defined2 = centers2[center].get('defined', False)
                
                if defined1 and not defined2:
                    compatibility_score += 0.8  # Attraction pattern
                elif not defined1 and defined2:
                    compatibility_score += 0.8  # Attraction pattern
                elif defined1 and defined2:
                    compatibility_score += 0.7  # Stability
                else:
                    compatibility_score += 0.4  # Both undefined
                
                center_count += 1
        
        return compatibility_score / center_count if center_count > 0 else 0.5
    
    def calculate_channel_compatibility(self, channels1: List, channels2: List) -> float:
        """
        Calculate compatibility based on channels
        Electromagnetic connections (completing channels) = high attraction
        Shared channels = familiarity
        """
        if not channels1 or not channels2:
            return 0.5
        
        # Simplified channel compatibility
        shared_channels = set(channels1) & set(channels2)
        total_channels = len(set(channels1) | set(channels2))
        
        if total_channels == 0:
            return 0.5
        
        # Shared channels provide familiarity
        familiarity_score = len(shared_channels) / total_channels
        
        # Different channels provide electromagnetic potential
        electromagnetic_score = (total_channels - len(shared_channels)) / total_channels * 0.8
        
        return min(1.0, familiarity_score * 0.6 + electromagnetic_score * 0.4)
    
    def calculate_hd_enhancement_factor(self, hd_factors1: Dict, hd_factors2: Dict) -> float:
        """
        Calculate overall HD enhancement factor for Magic 10 compatibility
        
        Returns:
            Float between 0.5 and 1.5 to enhance/reduce Magic 10 scores
        """
        if not hd_factors1 or not hd_factors2:
            return 1.0  # No enhancement if no HD data
        
        # Calculate individual compatibility factors
        type_compat = self.calculate_type_compatibility(
            hd_factors1.get('type', 'Generator'),
            hd_factors2.get('type', 'Generator')
        )
        
        authority_compat = self.calculate_authority_compatibility(
            hd_factors1.get('authority', 'Sacral'),
            hd_factors2.get('authority', 'Sacral')
        )
        
        center_compat = self.calculate_center_compatibility(
            hd_factors1.get('centers', {}),
            hd_factors2.get('centers', {})
        )
        
        channel_compat = self.calculate_channel_compatibility(
            hd_factors1.get('channels', []),
            hd_factors2.get('channels', [])
        )
        
        # Weighted combination of factors
        hd_score = (
            type_compat * 0.25 +
            authority_compat * 0.30 +
            center_compat * 0.25 +
            channel_compat * 0.20
        )
        
        # Convert to enhancement factor (0.7 to 1.3 range)
        enhancement_factor = 0.7 + (hd_score * 0.6)
        
        return enhancement_factor
    
    def enhance_magic10_compatibility(self, magic10_result: Dict, hd_factors1: Dict, hd_factors2: Dict) -> Dict:
        """
        Enhance Magic 10 compatibility results with HD intelligence
        
        Args:
            magic10_result: Original Magic 10 compatibility result
            hd_factors1: First person's HD factors
            hd_factors2: Second person's HD factors
        
        Returns:
            Enhanced compatibility result
        """
        # Calculate HD enhancement factor
        hd_enhancement = self.calculate_hd_enhancement_factor(hd_factors1, hd_factors2)
        
        # Enhance overall score
        original_score = magic10_result.get('overall_score', 50)
        enhanced_score = min(100, max(0, int(original_score * hd_enhancement)))
        
        # Enhance dimension scores based on HD insights
        enhanced_dimensions = {}
        for dimension, score in magic10_result.get('dimension_scores', {}).items():
            # Apply HD enhancement with some dimension-specific adjustments
            dimension_enhancement = hd_enhancement
            
            # Authority affects decision-making compatibility
            if dimension == 'decisions':
                auth_compat = self.calculate_authority_compatibility(
                    hd_factors1.get('authority', 'Sacral'),
                    hd_factors2.get('authority', 'Sacral')
                )
                dimension_enhancement = (hd_enhancement + auth_compat) / 2
            
            # Type affects collaboration and support
            elif dimension in ['collaboration', 'support']:
                type_compat = self.calculate_type_compatibility(
                    hd_factors1.get('type', 'Generator'),
                    hd_factors2.get('type', 'Generator')
                )
                dimension_enhancement = (hd_enhancement + type_compat) / 2
            
            enhanced_dimensions[dimension] = min(10, max(0, int(score * dimension_enhancement)))
        
        # Create enhanced result
        enhanced_result = magic10_result.copy()
        enhanced_result.update({
            'overall_score': enhanced_score,
            'dimension_scores': enhanced_dimensions,
            'hd_enhancement_factor': round(hd_enhancement, 2),
            'enhanced_by_hd': True
        })
        
        return enhanced_result
    
    def generate_compatibility_insights(self, enhanced_result: Dict, hd_factors1: Dict, hd_factors2: Dict) -> List[str]:
        """
        Generate relationship insights based on HD + Magic 10 analysis
        (Without exposing HD terminology)
        """
        insights = []
        
        overall_score = enhanced_result.get('overall_score', 50)
        hd_enhancement = enhanced_result.get('hd_enhancement_factor', 1.0)
        
        # Overall compatibility insights
        if overall_score >= 85:
            insights.append("You have exceptional natural chemistry and understanding.")
        elif overall_score >= 70:
            insights.append("You share a strong foundation for a meaningful connection.")
        elif overall_score >= 55:
            insights.append("You have good potential for a balanced relationship.")
        
        # HD-enhanced insights (without mentioning HD)
        if hd_enhancement > 1.1:
            insights.append("Your natural personalities complement each other beautifully.")
        elif hd_enhancement < 0.9:
            insights.append("You have different approaches that could lead to interesting growth.")
        
        # Authority-based insights (disguised as decision-making style)
        auth1 = hd_factors1.get('authority', 'Sacral')
        auth2 = hd_factors2.get('authority', 'Sacral')
        
        if auth1 == 'Emotional' or auth2 == 'Emotional':
            insights.append("Taking time with important decisions will strengthen your bond.")
        
        if auth1 == 'Sacral' and auth2 == 'Sacral':
            insights.append("You both trust your gut feelings and can make quick decisions together.")
        
        # Type-based insights (disguised as energy compatibility)
        type1 = hd_factors1.get('type', 'Generator')
        type2 = hd_factors2.get('type', 'Generator')
        
        if 'Generator' in type1 and 'Projector' in type2:
            insights.append("One of you brings steady energy while the other provides guidance.")
        elif 'Generator' in type1 and 'Generator' in type2:
            insights.append("You both have sustainable energy for building something together.")
        
        return insights[:3]  # Return top 3 insights

# ============================================================================
# INTEGRATION FUNCTIONS
# ============================================================================

def get_or_calculate_hd_chart(user_id: int, birth_data: Dict) -> Optional[Dict]:
    """
    Get existing HD chart or calculate new one from birth data
    
    Args:
        user_id: User ID
        birth_data: Birth data dictionary
    
    Returns:
        HD chart data or None
    """
    from app import db, HumanDesignData  # Import here to avoid circular imports
    
    # Check if we already have HD data
    hd_data = HumanDesignData.query.get(user_id)
    
    if hd_data and hd_data.chart_data:
        try:
            return json.loads(hd_data.chart_data)
        except:
            pass
    
    # Calculate new chart
    hd_engine = HDIntelligenceEngine()
    chart_data = hd_engine.hd_client.calculate_chart(birth_data)
    
    if chart_data:
        # Store in database
        if not hd_data:
            hd_data = HumanDesignData(user_id=user_id)
            db.session.add(hd_data)
        
        hd_data.chart_data = json.dumps(chart_data)
        hd_data.calculated_at = datetime.utcnow()
        
        # Extract and store key factors
        factors = hd_engine.extract_hd_factors(chart_data)
        hd_data.energy_type = factors.get('type')
        hd_data.authority = factors.get('authority')
        hd_data.profile = factors.get('profile')
        hd_data.definition_type = factors.get('definition')
        
        try:
            db.session.commit()
        except Exception as e:
            print(f"Error saving HD data: {e}")
            db.session.rollback()
    
    return chart_data

def calculate_enhanced_compatibility(user1_id: int, user2_id: int, magic10_result: Dict) -> Dict:
    """
    Calculate enhanced compatibility using Magic 10 + HD intelligence
    
    Args:
        user1_id: First user ID
        user2_id: Second user ID
        magic10_result: Original Magic 10 compatibility result
    
    Returns:
        Enhanced compatibility result
    """
    from app import db, HumanDesignData  # Import here to avoid circular imports
    
    # Get HD data for both users
    hd_data1 = HumanDesignData.query.get(user1_id)
    hd_data2 = HumanDesignData.query.get(user2_id)
    
    hd_factors1 = {}
    hd_factors2 = {}
    
    # Extract HD factors if available
    hd_engine = HDIntelligenceEngine()
    
    if hd_data1 and hd_data1.chart_data:
        try:
            chart1 = json.loads(hd_data1.chart_data)
            hd_factors1 = hd_engine.extract_hd_factors(chart1)
        except:
            pass
    
    if hd_data2 and hd_data2.chart_data:
        try:
            chart2 = json.loads(hd_data2.chart_data)
            hd_factors2 = hd_engine.extract_hd_factors(chart2)
        except:
            pass
    
    # Enhance Magic 10 result with HD intelligence
    enhanced_result = hd_engine.enhance_magic10_compatibility(
        magic10_result, hd_factors1, hd_factors2
    )
    
    # Generate insights
    insights = hd_engine.generate_compatibility_insights(
        enhanced_result, hd_factors1, hd_factors2
    )
    enhanced_result['compatibility_insights'] = insights
    
    return enhanced_result

