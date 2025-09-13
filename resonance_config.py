"""
Resonance Ten - Canonical Compatibility Model Configuration
Shared configuration for frontend and backend alignment
"""

# Resonance Ten Model Definition
RESONANCE_TEN_CONFIG = {
    "version": 1,
    "brand": "Resonance Ten",
    "keys": [
        "love",
        "intimacy", 
        "communication",
        "friendship",
        "collaboration",
        "lifestyle",
        "decisions",
        "support",
        "growth",
        "space"
    ],
    "labels": {
        "love": "Love",
        "intimacy": "Intimacy",
        "communication": "Communication",
        "friendship": "Friendship",
        "collaboration": "Collaboration",
        "lifestyle": "Lifestyle",
        "decisions": "Decisions",
        "support": "Support",
        "growth": "Growth",
        "space": "Space"
    },
    "public_descriptions": {
        "love": "How you show affection and romance.",
        "intimacy": "Your pace for closeness and vulnerability.",
        "communication": "How you express, listen, and click in conversation.",
        "friendship": "Everyday ease and shared play.",
        "collaboration": "How you work and decide together on practical things.",
        "lifestyle": "Daily rhythm, habits, and preferences.",
        "decisions": "How choices feel smooth (or sticky) together.",
        "support": "Feeling resourced, encouraged, and seen.",
        "growth": "Learning, goals, and direction as a pair.",
        "space": "Boundaries, independence, and healthy distance."
    },
    "sub_facets": {
        "intimacy": ["spark", "emotional_sync"],
        "communication": ["mind_spark"],
        "friendship": ["humor"],
        "growth": ["values_direction", "drive"],
        "lifestyle": ["home_family"]
    }
}

# Mapping from legacy Model A field names to Resonance Ten keys
LEGACY_MODEL_A_MAPPING = {
    "love_priority": "love",
    "intimacy_priority": "intimacy",
    "communication_priority": "communication",
    "friendship_priority": "friendship",
    "collaboration_priority": "collaboration",
    "lifestyle_priority": "lifestyle",
    "decisions_priority": "decisions",
    "support_priority": "support",
    "growth_priority": "growth",
    "space_priority": "space"
}

# Reverse mapping for compatibility
RESONANCE_TO_LEGACY_MAPPING = {v: k for k, v in LEGACY_MODEL_A_MAPPING.items()}

def get_resonance_config():
    """Get the canonical Resonance Ten configuration"""
    return RESONANCE_TEN_CONFIG

def validate_resonance_weights(weights):
    """Validate that weights dict contains valid keys and values"""
    if not isinstance(weights, dict):
        return False, "Weights must be a dictionary"
    
    valid_keys = set(RESONANCE_TEN_CONFIG["keys"])
    provided_keys = set(weights.keys())
    
    # Check for invalid keys
    invalid_keys = provided_keys - valid_keys
    if invalid_keys:
        return False, f"Invalid keys: {list(invalid_keys)}"
    
    # Check value ranges
    for key, value in weights.items():
        if not isinstance(value, (int, float)) or not (0 <= value <= 100):
            return False, f"Value for {key} must be between 0 and 100"
    
    return True, "Valid"

def convert_legacy_to_resonance(legacy_priorities):
    """Convert legacy Model A priorities to Resonance Ten format"""
    resonance_weights = {}
    
    for legacy_key, resonance_key in LEGACY_MODEL_A_MAPPING.items():
        if hasattr(legacy_priorities, legacy_key):
            value = getattr(legacy_priorities, legacy_key)
            # Convert from 1-10 scale to 0-100 scale
            resonance_weights[resonance_key] = (value - 1) * 100 // 9 if value else 50
    
    return resonance_weights

def convert_resonance_to_legacy(resonance_weights):
    """Convert Resonance Ten weights to legacy Model A format for backward compatibility"""
    legacy_values = {}
    
    for resonance_key, legacy_key in RESONANCE_TO_LEGACY_MAPPING.items():
        if resonance_key in resonance_weights:
            value = resonance_weights[resonance_key]
            # Convert from 0-100 scale to 1-10 scale
            legacy_values[legacy_key] = max(1, min(10, (value * 9 // 100) + 1))
        else:
            legacy_values[legacy_key] = 5  # Default value
    
    return legacy_values

