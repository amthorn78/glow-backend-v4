#!/usr/bin/env python3
"""
Human Design Data Extraction Engine
Parses Human Design API responses and populates comprehensive schema fields
"""
import json
from datetime import datetime
from app import app, db, HumanDesignData

def extract_hd_data_from_api(api_response, user_id):
    """
    Extract comprehensive Human Design data from API response and populate database
    
    Args:
        api_response (dict): Raw Human Design API response
        user_id (int): User ID to associate the data with
    
    Returns:
        HumanDesignData: Populated HD data object
    """
    
    # Get or create HD data record
    hd_data = HumanDesignData.query.get(user_id)
    if not hd_data:
        hd_data = HumanDesignData(user_id=user_id)
    
    # Store raw API response
    hd_data.set_api_response(api_response)
    hd_data.set_chart_data(api_response)
    hd_data.calculated_at = datetime.utcnow()
    hd_data.schema_version = 3
    
    # === CORE TYPE & STRATEGY ===
    hd_data.energy_type = api_response.get('type', '')
    hd_data.sub_type = api_response.get('subtype', '')  # For Manifesting Generators
    hd_data.strategy = api_response.get('strategy', '')
    hd_data.type_relational_impact = generate_type_relational_impact(hd_data.energy_type, hd_data.sub_type)
    
    # === AUTHORITY & DECISION MAKING ===
    hd_data.authority = api_response.get('authority', '')
    hd_data.decision_pacing = generate_decision_pacing(hd_data.authority)
    hd_data.authority_compatibility_impact = generate_authority_compatibility_impact(hd_data.authority)
    
    # === DEFINITION & SPLITS ===
    hd_data.definition_type = api_response.get('definition', '')
    hd_data.split_bridges = json.dumps(extract_split_bridges(api_response))
    hd_data.definition_relational_impact = generate_definition_relational_impact(hd_data.definition_type)
    
    # === CENTERS ===
    centers = api_response.get('centers', {})
    extract_centers_data(hd_data, centers)
    
    # === GATES ===
    gates_data = api_response.get('gates', {})
    extract_gates_data(hd_data, gates_data, api_response)
    
    # === CHANNELS ===
    channels_data = api_response.get('channels', {})
    extract_channels_data(hd_data, channels_data)
    
    # === PROFILE ===
    profile = api_response.get('profile', '')
    extract_profile_data(hd_data, profile)
    
    # === INCARNATION CROSS ===
    cross_data = api_response.get('incarnation_cross', {})
    extract_incarnation_cross_data(hd_data, cross_data)
    
    # === CONDITIONING & OPENNESS ===
    extract_conditioning_data(hd_data, centers)
    
    # === CIRCUITRY ===
    extract_circuitry_data(hd_data, channels_data)
    
    # === NODES ===
    nodes_data = api_response.get('nodes', {})
    extract_nodes_data(hd_data, nodes_data)
    
    # === PLANETARY ACTIVATIONS ===
    planets_data = api_response.get('planets', {})
    extract_planetary_data(hd_data, planets_data)
    
    # === COMPATIBILITY CALCULATIONS ===
    calculate_compatibility_connections(hd_data)
    
    return hd_data

def extract_centers_data(hd_data, centers):
    """Extract and populate center data with relational impacts"""
    center_mapping = {
        'head': ('center_head', 'center_head_relational_impact'),
        'ajna': ('center_ajna', 'center_ajna_relational_impact'),
        'throat': ('center_throat', 'center_throat_relational_impact'),
        'g': ('center_g', 'center_g_relational_impact'),
        'heart': ('center_heart', 'center_heart_relational_impact'),
        'spleen': ('center_spleen', 'center_spleen_relational_impact'),
        'solar_plexus': ('center_solar_plexus', 'center_solar_plexus_relational_impact'),
        'sacral': ('center_sacral', 'center_sacral_relational_impact'),
        'root': ('center_root', 'center_root_relational_impact')
    }
    
    for center_name, (defined_field, impact_field) in center_mapping.items():
        is_defined = centers.get(center_name, {}).get('defined', False)
        setattr(hd_data, defined_field, is_defined)
        setattr(hd_data, impact_field, generate_center_relational_impact(center_name, is_defined))

def extract_gates_data(hd_data, gates_data, api_response):
    """Extract gates data including hanging gates and relational impacts"""
    # Get all defined gates
    defined_gates = []
    personality_gates = []
    design_gates = []
    
    # Extract from different sources in API response
    if 'personality' in api_response:
        personality_gates = extract_gates_from_planets(api_response['personality'])
    if 'design' in api_response:
        design_gates = extract_gates_from_planets(api_response['design'])
    
    defined_gates = list(set(personality_gates + design_gates))
    
    # Calculate hanging gates (gates without their channel partner)
    hanging_gates = calculate_hanging_gates(defined_gates)
    
    # Identify key relational gates
    key_relational_gates = identify_key_relational_gates(defined_gates)
    
    hd_data.set_gates_defined(defined_gates)
    hd_data.gates_personality = json.dumps(personality_gates)
    hd_data.gates_design = json.dumps(design_gates)
    hd_data.set_hanging_gates(hanging_gates)
    hd_data.key_relational_gates = json.dumps(key_relational_gates)

def extract_channels_data(hd_data, channels_data):
    """Extract channel data with relational impacts"""
    defined_channels = []
    
    # Extract defined channels from API response
    if isinstance(channels_data, dict):
        defined_channels = [ch for ch, data in channels_data.items() if data.get('defined', False)]
    elif isinstance(channels_data, list):
        defined_channels = channels_data
    
    # Identify key relationship channels
    key_relationship_channels = identify_key_relationship_channels(defined_channels)
    
    hd_data.set_channels_defined(defined_channels)
    hd_data.key_relationship_channels = json.dumps(key_relationship_channels)

def extract_profile_data(hd_data, profile):
    """Extract profile data with line-by-line relational impacts"""
    hd_data.profile = profile
    
    if profile:
        lines = profile.split('/')
        if len(lines) == 2:
            line1, line2 = lines
            hd_data.profile_line1 = generate_profile_line_impact(1, line1)
            hd_data.profile_line2 = generate_profile_line_impact(2, line2)
            # Lines 3-6 are derived from the conscious/unconscious lines
            hd_data.profile_line3 = generate_profile_line_impact(3, line1)
            hd_data.profile_line4 = generate_profile_line_impact(4, line2)
            hd_data.profile_line5 = generate_profile_line_impact(5, line1)
            hd_data.profile_line6 = generate_profile_line_impact(6, line2)
    
    hd_data.profile_relational_impact = generate_profile_relational_impact(profile)

def extract_incarnation_cross_data(hd_data, cross_data):
    """Extract incarnation cross data"""
    if isinstance(cross_data, dict):
        hd_data.incarnation_cross = cross_data.get('name', '')
        hd_data.cross_gates = json.dumps(cross_data.get('gates', []))
        hd_data.cross_angle = cross_data.get('angle', '')
    elif isinstance(cross_data, str):
        hd_data.incarnation_cross = cross_data
        hd_data.cross_gates = json.dumps([])
        hd_data.cross_angle = ''
    
    hd_data.cross_relational_impact = generate_cross_relational_impact(hd_data.incarnation_cross)

def extract_conditioning_data(hd_data, centers):
    """Extract conditioning and openness patterns"""
    open_centers = []
    conditioning_themes = []
    
    for center_name, center_data in centers.items():
        if not center_data.get('defined', False):
            open_centers.append(center_name)
            conditioning_themes.append(generate_conditioning_theme(center_name))
    
    hd_data.set_open_centers(open_centers)
    hd_data.conditioning_themes = '; '.join(conditioning_themes)
    hd_data.conditioning_relational_impact = generate_conditioning_relational_impact(open_centers)

def extract_circuitry_data(hd_data, channels_data):
    """Extract circuitry data with relational impacts"""
    individual_count = 0
    tribal_count = 0
    collective_count = 0
    
    # Count channels by circuitry type
    for channel in hd_data.get_channels_defined():
        circuitry = get_channel_circuitry(channel)
        if circuitry == 'individual':
            individual_count += 1
        elif circuitry == 'tribal':
            tribal_count += 1
        elif circuitry == 'collective':
            collective_count += 1
    
    hd_data.circuitry_individual = individual_count
    hd_data.circuitry_tribal = tribal_count
    hd_data.circuitry_collective = collective_count
    hd_data.circuitry_relational_impact = generate_circuitry_relational_impact(
        individual_count, tribal_count, collective_count
    )

def extract_nodes_data(hd_data, nodes_data):
    """Extract North/South Node data"""
    hd_data.conscious_node = nodes_data.get('north_node', '')
    hd_data.unconscious_node = nodes_data.get('south_node', '')
    hd_data.nodes_relational_impact = generate_nodes_relational_impact(
        hd_data.conscious_node, hd_data.unconscious_node
    )

def extract_planetary_data(hd_data, planets_data):
    """Extract planetary activation data"""
    personality_planets = planets_data.get('personality', {})
    design_planets = planets_data.get('design', {})
    
    # Personality planets
    hd_data.sun_personality = format_gate_line(personality_planets.get('sun', {}))
    hd_data.earth_personality = format_gate_line(personality_planets.get('earth', {}))
    hd_data.moon_personality = format_gate_line(personality_planets.get('moon', {}))
    hd_data.mercury_personality = format_gate_line(personality_planets.get('mercury', {}))
    hd_data.venus_personality = format_gate_line(personality_planets.get('venus', {}))
    hd_data.mars_personality = format_gate_line(personality_planets.get('mars', {}))
    hd_data.jupiter_personality = format_gate_line(personality_planets.get('jupiter', {}))
    hd_data.saturn_personality = format_gate_line(personality_planets.get('saturn', {}))
    hd_data.uranus_personality = format_gate_line(personality_planets.get('uranus', {}))
    hd_data.neptune_personality = format_gate_line(personality_planets.get('neptune', {}))
    hd_data.pluto_personality = format_gate_line(personality_planets.get('pluto', {}))
    hd_data.north_node_personality = format_gate_line(personality_planets.get('north_node', {}))
    hd_data.south_node_personality = format_gate_line(personality_planets.get('south_node', {}))
    
    # Design planets
    hd_data.sun_design = format_gate_line(design_planets.get('sun', {}))
    hd_data.earth_design = format_gate_line(design_planets.get('earth', {}))
    hd_data.moon_design = format_gate_line(design_planets.get('moon', {}))
    hd_data.mercury_design = format_gate_line(design_planets.get('mercury', {}))
    hd_data.venus_design = format_gate_line(design_planets.get('venus', {}))
    hd_data.mars_design = format_gate_line(design_planets.get('mars', {}))
    hd_data.jupiter_design = format_gate_line(design_planets.get('jupiter', {}))
    hd_data.saturn_design = format_gate_line(design_planets.get('saturn', {}))
    hd_data.uranus_design = format_gate_line(design_planets.get('uranus', {}))
    hd_data.neptune_design = format_gate_line(design_planets.get('neptune', {}))
    hd_data.pluto_design = format_gate_line(design_planets.get('pluto', {}))
    hd_data.north_node_design = format_gate_line(design_planets.get('north_node', {}))
    hd_data.south_node_design = format_gate_line(design_planets.get('south_node', {}))
    
    # Generate planetary relational impacts
    planetary_impacts = generate_planetary_relational_impacts(personality_planets, design_planets)
    hd_data.planetary_relational_impacts = json.dumps(planetary_impacts)

def calculate_compatibility_connections(hd_data):
    """Calculate compatibility connections for Magic 10 algorithm"""
    # This will be populated when comparing with other users
    hd_data.electromagnetic_connections = json.dumps({})
    hd_data.compromise_connections = json.dumps({})
    hd_data.dominance_connections = json.dumps({})
    hd_data.conditioning_dynamics = json.dumps({})

# === HELPER FUNCTIONS FOR RELATIONAL IMPACT GENERATION ===

def generate_type_relational_impact(energy_type, sub_type):
    """Generate relational impact description for energy type"""
    impacts = {
        'Generator': 'Sustainable energy for relationships; responds to life and partners; needs satisfaction in connections',
        'Manifesting Generator': 'Multi-passionate energy; can initiate and respond; needs freedom and variety in relationships',
        'Projector': 'Natural guide and advisor; needs recognition and invitation; brings wisdom to partnerships',
        'Manifestor': 'Independent initiator; needs freedom to act; brings leadership and direction to relationships',
        'Reflector': 'Mirrors relationship dynamics; needs time for clarity; brings unique perspective and wisdom'
    }
    return impacts.get(energy_type, 'Unique energy pattern in relationships')

def generate_decision_pacing(authority):
    """Generate decision pacing description"""
    pacing = {
        'Emotional': 'Requires waiting through emotional wave; no truth in the now',
        'Sacral': 'In-the-moment gut responses; immediate knowing',
        'Splenic': 'Instinctive, in-the-moment awareness; spontaneous knowing',
        'Ego': 'Heart-centered willpower; commitment-based decisions',
        'Self-Projected': 'Needs to talk it out; clarity through expression',
        'Environmental': 'Needs right environment and people for clarity',
        'Lunar': 'Needs full lunar cycle (28 days) for major decisions'
    }
    return pacing.get(authority, 'Unique decision-making process')

def generate_authority_compatibility_impact(authority):
    """Generate authority compatibility impact"""
    return f"Decision-making style affects relationship timing and communication patterns. {authority} authority brings specific needs for clarity and decision-making in partnerships."

def generate_definition_relational_impact(definition_type):
    """Generate definition relational impact"""
    impacts = {
        'Single Definition': 'Self-contained energy; independent; may be attracted to those who bridge their openness',
        'Split Definition': 'Seeks bridging energy; attracted to those who connect their splits; interdependent',
        'Triple Split Definition': 'Complex bridging needs; seeks multiple connections; highly interdependent',
        'Quadruple Split Definition': 'Rare; needs multiple bridging connections; extremely interdependent',
        'No Definition': 'Completely open; highly sensitive to others; mirrors and amplifies energy'
    }
    return impacts.get(definition_type, 'Unique energy flow pattern in relationships')

def generate_center_relational_impact(center_name, is_defined):
    """Generate center-specific relational impact"""
    if is_defined:
        impacts = {
            'head': 'Provides mental pressure and inspiration; conditions others with questions and mental energy',
            'ajna': 'Fixed way of thinking; provides mental certainty; conditions others with concepts and beliefs',
            'throat': 'Consistent expression and manifestation; conditions others with communication style',
            'g': 'Fixed identity and direction; provides consistent love and identity; conditions others with sense of self',
            'heart': 'Willpower and ego strength; conditions others with promises and material focus',
            'spleen': 'Intuitive awareness and survival instincts; conditions others with spontaneous knowing',
            'solar_plexus': 'Emotional wave and depth; conditions others with emotional energy and moods',
            'sacral': 'Life force and sexual energy; conditions others with vitality and response',
            'root': 'Pressure and drive; conditions others with stress and momentum'
        }
    else:
        impacts = {
            'head': 'Absorbs and amplifies mental pressure; seeks inspiration and questions from others',
            'ajna': 'Flexible thinking; absorbs concepts and beliefs; seeks mental certainty from others',
            'throat': 'Inconsistent expression; absorbs communication energy; seeks voice through others',
            'g': 'Flexible identity; absorbs love and direction; seeks sense of self through others',
            'heart': 'Inconsistent willpower; absorbs ego energy; seeks promises and material security from others',
            'spleen': 'Absorbs intuitive energy; seeks spontaneous awareness and health guidance from others',
            'solar_plexus': 'Absorbs emotional energy; amplifies emotions; seeks emotional clarity from others',
            'sacral': 'Absorbs life force; seeks vitality and sexual energy from others',
            'root': 'Absorbs pressure; seeks drive and momentum from others'
        }
    
    return impacts.get(center_name, 'Unique energy pattern in relationships')

# Additional helper functions would continue here...
# (Due to length constraints, I'm showing the core structure)

def extract_gates_from_planets(planets_data):
    """Extract gate numbers from planetary data"""
    gates = []
    for planet, data in planets_data.items():
        if isinstance(data, dict) and 'gate' in data:
            gates.append(data['gate'])
        elif isinstance(data, str) and '.' in data:
            gate = data.split('.')[0]
            try:
                gates.append(int(gate))
            except ValueError:
                pass
    return gates

def calculate_hanging_gates(defined_gates):
    """Calculate hanging gates (gates without their channel partner)"""
    # Channel pairs mapping (simplified - would need complete mapping)
    channel_pairs = {
        1: 8, 2: 14, 3: 60, 4: 63, 5: 15, 6: 59, 7: 31, 9: 52, 10: 20,
        11: 56, 12: 22, 13: 33, 16: 48, 17: 62, 18: 58, 19: 49, 21: 45,
        23: 43, 24: 61, 25: 51, 26: 44, 27: 50, 28: 38, 29: 46, 30: 41,
        32: 54, 34: 57, 35: 36, 37: 40, 39: 55, 42: 53, 47: 64
    }
    
    hanging_gates = []
    for gate in defined_gates:
        partner = channel_pairs.get(gate)
        if partner and partner not in defined_gates:
            hanging_gates.append(gate)
    
    return hanging_gates

def identify_key_relational_gates(defined_gates):
    """Identify key relational gates and their impacts"""
    key_gates = {
        59: 'Sexuality and intimacy',
        6: 'Conflict and friction',
        49: 'Revolution and needs',
        19: 'Wanting and needs',
        44: 'Coming to meet and patterns',
        26: 'The trickster and ego',
        37: 'The family and friendship',
        40: 'Aloneness and community'
    }
    
    return {gate: impact for gate, impact in key_gates.items() if gate in defined_gates}

def identify_key_relationship_channels(defined_channels):
    """Identify key relationship channels and their impacts"""
    key_channels = {
        '59-6': 'Intimacy and sexuality',
        '49-19': 'Synthesis and needs',
        '40-37': 'Community and family',
        '44-26': 'Surrender and ego'
    }
    
    return {channel: impact for channel, impact in key_channels.items() if channel in defined_channels}

def format_gate_line(planet_data):
    """Format planetary data as gate.line"""
    if isinstance(planet_data, dict):
        gate = planet_data.get('gate', '')
        line = planet_data.get('line', '')
        return f"{gate}.{line}" if gate and line else ''
    return str(planet_data) if planet_data else ''

def get_channel_circuitry(channel):
    """Get circuitry type for a channel"""
    # Simplified mapping - would need complete channel circuitry data
    individual_channels = ['1-8', '2-14', '3-60', '4-63', '5-15']
    tribal_channels = ['6-59', '7-31', '9-52', '10-20', '11-56']
    collective_channels = ['12-22', '13-33', '16-48', '17-62', '18-58']
    
    if channel in individual_channels:
        return 'individual'
    elif channel in tribal_channels:
        return 'tribal'
    elif channel in collective_channels:
        return 'collective'
    return 'unknown'

# Additional helper functions for generating relational impacts...
def generate_profile_line_impact(line_num, line_value):
    """Generate profile line impact"""
    return f"Line {line_num} characteristics"

def generate_profile_relational_impact(profile):
    """Generate overall profile relational impact"""
    return f"Profile {profile} relational dynamics"

def generate_cross_relational_impact(cross_name):
    """Generate incarnation cross relational impact"""
    return f"Life purpose alignment for {cross_name}"

def generate_conditioning_theme(center_name):
    """Generate conditioning theme for open center"""
    return f"{center_name.title()} conditioning patterns"

def generate_conditioning_relational_impact(open_centers):
    """Generate overall conditioning relational impact"""
    return f"Conditioning patterns in {', '.join(open_centers)} centers"

def generate_circuitry_relational_impact(individual, tribal, collective):
    """Generate circuitry relational impact"""
    return f"Energy flow: {individual} individual, {tribal} tribal, {collective} collective channels"

def generate_nodes_relational_impact(conscious, unconscious):
    """Generate nodes relational impact"""
    return f"Environmental orientation: {conscious} (conscious), {unconscious} (unconscious)"

def generate_planetary_relational_impacts(personality, design):
    """Generate planetary relational impacts"""
    return {
        'sun': 'Core identity and life force',
        'earth': 'Grounding and foundation',
        'moon': 'Emotional and driving force'
    }

def extract_split_bridges(api_response):
    """Extract gates/channels that bridge splits"""
    return []  # Would need complex analysis of definition patterns

if __name__ == "__main__":
    print("Human Design Data Extraction Engine")
    print("Use extract_hd_data_from_api(api_response, user_id) to process HD data")

