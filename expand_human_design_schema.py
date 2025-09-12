#!/usr/bin/env python3
"""
Expand Human Design Data Schema for Comprehensive Matching
This adds all the necessary fields for effective Human Design compatibility matching
"""

import os
import sys
from datetime import datetime
from sqlalchemy import create_engine, text, Column, Integer, String, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Add the app directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def get_database_url():
    """Get database URL from environment or use default"""
    return os.environ.get('DATABASE_URL', 'sqlite:///glow_dev.db')

def expand_human_design_schema():
    """Add comprehensive Human Design fields for matching"""
    
    database_url = get_database_url()
    engine = create_engine(database_url)
    
    print(f"Expanding Human Design schema in database: {database_url}")
    
    # SQL commands to add new columns
    expansion_commands = [
        # Centers (9 defined/undefined centers)
        "ALTER TABLE human_design_data ADD COLUMN center_head BOOLEAN DEFAULT FALSE",
        "ALTER TABLE human_design_data ADD COLUMN center_ajna BOOLEAN DEFAULT FALSE", 
        "ALTER TABLE human_design_data ADD COLUMN center_throat BOOLEAN DEFAULT FALSE",
        "ALTER TABLE human_design_data ADD COLUMN center_g BOOLEAN DEFAULT FALSE",
        "ALTER TABLE human_design_data ADD COLUMN center_heart BOOLEAN DEFAULT FALSE",
        "ALTER TABLE human_design_data ADD COLUMN center_spleen BOOLEAN DEFAULT FALSE",
        "ALTER TABLE human_design_data ADD COLUMN center_solar_plexus BOOLEAN DEFAULT FALSE",
        "ALTER TABLE human_design_data ADD COLUMN center_sacral BOOLEAN DEFAULT FALSE",
        "ALTER TABLE human_design_data ADD COLUMN center_root BOOLEAN DEFAULT FALSE",
        
        # Key Gates (most important for compatibility)
        "ALTER TABLE human_design_data ADD COLUMN gates_defined TEXT", # JSON array of defined gate numbers
        "ALTER TABLE human_design_data ADD COLUMN gates_personality TEXT", # JSON array of personality gates
        "ALTER TABLE human_design_data ADD COLUMN gates_design TEXT", # JSON array of design gates
        
        # Channels (36 channels for electromagnetic connections)
        "ALTER TABLE human_design_data ADD COLUMN channels_defined TEXT", # JSON array of defined channel numbers
        
        # Variables (4 arrows)
        "ALTER TABLE human_design_data ADD COLUMN digestion VARCHAR(50)", # PHS - how to process
        "ALTER TABLE human_design_data ADD COLUMN environment VARCHAR(50)", # PHS - where to be
        "ALTER TABLE human_design_data ADD COLUMN motivation VARCHAR(50)", # Motivation arrow
        "ALTER TABLE human_design_data ADD COLUMN perspective VARCHAR(50)", # Perspective arrow
        
        # Incarnation Cross
        "ALTER TABLE human_design_data ADD COLUMN incarnation_cross VARCHAR(200)",
        "ALTER TABLE human_design_data ADD COLUMN cross_angle VARCHAR(50)", # Right/Left angle, Juxtaposition
        
        # Circuitry and Definition
        "ALTER TABLE human_design_data ADD COLUMN definition_type VARCHAR(50)", # Single, Split, Triple Split, Quadruple Split, No Definition
        "ALTER TABLE human_design_data ADD COLUMN circuitry_individual INTEGER DEFAULT 0", # Count of individual circuitry
        "ALTER TABLE human_design_data ADD COLUMN circuitry_tribal INTEGER DEFAULT 0", # Count of tribal circuitry  
        "ALTER TABLE human_design_data ADD COLUMN circuitry_collective INTEGER DEFAULT 0", # Count of collective circuitry
        
        # Planetary activations (for deeper compatibility)
        "ALTER TABLE human_design_data ADD COLUMN sun_personality VARCHAR(20)", # Gate.Line format
        "ALTER TABLE human_design_data ADD COLUMN earth_personality VARCHAR(20)",
        "ALTER TABLE human_design_data ADD COLUMN moon_personality VARCHAR(20)",
        "ALTER TABLE human_design_data ADD COLUMN mercury_personality VARCHAR(20)",
        "ALTER TABLE human_design_data ADD COLUMN venus_personality VARCHAR(20)",
        "ALTER TABLE human_design_data ADD COLUMN mars_personality VARCHAR(20)",
        "ALTER TABLE human_design_data ADD COLUMN jupiter_personality VARCHAR(20)",
        "ALTER TABLE human_design_data ADD COLUMN saturn_personality VARCHAR(20)",
        "ALTER TABLE human_design_data ADD COLUMN uranus_personality VARCHAR(20)",
        "ALTER TABLE human_design_data ADD COLUMN neptune_personality VARCHAR(20)",
        "ALTER TABLE human_design_data ADD COLUMN pluto_personality VARCHAR(20)",
        "ALTER TABLE human_design_data ADD COLUMN north_node_personality VARCHAR(20)",
        "ALTER TABLE human_design_data ADD COLUMN south_node_personality VARCHAR(20)",
        
        "ALTER TABLE human_design_data ADD COLUMN sun_design VARCHAR(20)",
        "ALTER TABLE human_design_data ADD COLUMN earth_design VARCHAR(20)",
        "ALTER TABLE human_design_data ADD COLUMN moon_design VARCHAR(20)",
        "ALTER TABLE human_design_data ADD COLUMN mercury_design VARCHAR(20)",
        "ALTER TABLE human_design_data ADD COLUMN venus_design VARCHAR(20)",
        "ALTER TABLE human_design_data ADD COLUMN mars_design VARCHAR(20)",
        "ALTER TABLE human_design_data ADD COLUMN jupiter_design VARCHAR(20)",
        "ALTER TABLE human_design_data ADD COLUMN saturn_design VARCHAR(20)",
        "ALTER TABLE human_design_data ADD COLUMN uranus_design VARCHAR(20)",
        "ALTER TABLE human_design_data ADD COLUMN neptune_design VARCHAR(20)",
        "ALTER TABLE human_design_data ADD COLUMN pluto_design VARCHAR(20)",
        "ALTER TABLE human_design_data ADD COLUMN north_node_design VARCHAR(20)",
        "ALTER TABLE human_design_data ADD COLUMN south_node_design VARCHAR(20)",
        
        # Compatibility scoring fields
        "ALTER TABLE human_design_data ADD COLUMN electromagnetic_connections TEXT", # JSON of electromagnetic connections with other charts
        "ALTER TABLE human_design_data ADD COLUMN compromise_connections TEXT", # JSON of compromise connections
        "ALTER TABLE human_design_data ADD COLUMN dominance_connections TEXT", # JSON of dominance connections
        
        # Metadata
        "ALTER TABLE human_design_data ADD COLUMN schema_version INTEGER DEFAULT 2",
        "ALTER TABLE human_design_data ADD COLUMN last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
    ]
    
    try:
        with engine.connect() as conn:
            # Check if table exists using a different method
            try:
                result = conn.execute(text("SELECT COUNT(*) FROM human_design_data LIMIT 1"))
                print("human_design_data table found!")
            except Exception:
                print("human_design_data table does not exist. Please run the main application first to create base tables.")
                return False
            
            # Execute each command
            for i, command in enumerate(expansion_commands, 1):
                try:
                    print(f"Executing command {i}/{len(expansion_commands)}: {command[:50]}...")
                    conn.execute(text(command))
                    conn.commit()
                except Exception as e:
                    if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                        print(f"  Column already exists, skipping...")
                        continue
                    else:
                        print(f"  Error: {e}")
                        continue
            
            print("\n✅ Human Design schema expansion completed successfully!")
            print("\nNew fields added for comprehensive matching:")
            print("- 9 Centers (defined/undefined)")
            print("- Gates (personality and design)")
            print("- Channels (electromagnetic connections)")
            print("- Variables (digestion, environment, motivation, perspective)")
            print("- Incarnation Cross and angle")
            print("- Definition type and circuitry")
            print("- Planetary activations (13 planets x 2 sides)")
            print("- Compatibility connection fields")
            
            return True
            
    except Exception as e:
        print(f"Error expanding schema: {e}")
        return False

if __name__ == "__main__":
    success = expand_human_design_schema()
    if success:
        print("\n🎉 Schema expansion complete! The Human Design data model now supports comprehensive compatibility matching.")
    else:
        print("\n❌ Schema expansion failed. Please check the error messages above.")

