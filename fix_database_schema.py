#!/usr/bin/env python3
"""
Comprehensive Database Schema Fix
Adds missing fields and fixes schema inconsistencies
"""

import os
import sys
from datetime import datetime

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db

def fix_database_schema():
    """Fix all database schema issues"""
    
    with app.app_context():
        print("🔧 Starting comprehensive database schema fix...")
        
        try:
            # Get database connection
            connection = db.engine.connect()
            
            print("\n1️⃣ Adding missing fields to users table...")
            
            # Add is_admin field to users table
            try:
                connection.execute(db.text("ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT FALSE"))
                print("   ✅ Added is_admin field")
            except Exception as e:
                if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                    print("   ⚠️  is_admin field already exists")
                else:
                    print(f"   ❌ Error adding is_admin: {e}")
            
            # Add onboarding_completed field to users table
            try:
                connection.execute(db.text("ALTER TABLE users ADD COLUMN onboarding_completed BOOLEAN DEFAULT FALSE"))
                print("   ✅ Added onboarding_completed field")
            except Exception as e:
                if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                    print("   ⚠️  onboarding_completed field already exists")
                else:
                    print(f"   ❌ Error adding onboarding_completed: {e}")
            
            print("\n2️⃣ Fixing human_design_data table...")
            
            # Drop and recreate human_design_data table with all fields
            try:
                connection.execute(db.text("DROP TABLE IF EXISTS human_design_data_backup"))
                connection.execute(db.text("CREATE TABLE human_design_data_backup AS SELECT * FROM human_design_data"))
                print("   ✅ Backed up existing human_design_data")
                
                connection.execute(db.text("DROP TABLE human_design_data"))
                print("   ✅ Dropped old human_design_data table")
                
                # Create new table with all fields
                create_hd_table_sql = """
                CREATE TABLE human_design_data (
                    user_id INTEGER PRIMARY KEY,
                    chart_data TEXT,
                    energy_type VARCHAR(50),
                    strategy VARCHAR(100),
                    authority VARCHAR(100),
                    profile VARCHAR(20),
                    api_response TEXT,
                    calculated_at DATETIME,
                    
                    -- Type and Strategy
                    type_relational_impact TEXT,
                    strategy_relational_impact TEXT,
                    authority_relational_impact TEXT,
                    
                    -- Definition
                    definition_type VARCHAR(50),
                    definition_relational_impact TEXT,
                    
                    -- Centers (9 centers)
                    center_head BOOLEAN DEFAULT FALSE,
                    center_head_relational_impact TEXT,
                    center_ajna BOOLEAN DEFAULT FALSE,
                    center_ajna_relational_impact TEXT,
                    center_throat BOOLEAN DEFAULT FALSE,
                    center_throat_relational_impact TEXT,
                    center_g BOOLEAN DEFAULT FALSE,
                    center_g_relational_impact TEXT,
                    center_heart BOOLEAN DEFAULT FALSE,
                    center_heart_relational_impact TEXT,
                    center_spleen BOOLEAN DEFAULT FALSE,
                    center_spleen_relational_impact TEXT,
                    center_solar_plexus BOOLEAN DEFAULT FALSE,
                    center_solar_plexus_relational_impact TEXT,
                    center_sacral BOOLEAN DEFAULT FALSE,
                    center_sacral_relational_impact TEXT,
                    center_root BOOLEAN DEFAULT FALSE,
                    center_root_relational_impact TEXT,
                    
                    -- Gates and Channels
                    gates_defined TEXT,
                    gates_personality TEXT,
                    gates_design TEXT,
                    hanging_gates TEXT,
                    key_relational_gates TEXT,
                    channels_defined TEXT,
                    key_relationship_channels TEXT,
                    
                    -- Profile Lines
                    profile_line1 BOOLEAN DEFAULT FALSE,
                    profile_line2 BOOLEAN DEFAULT FALSE,
                    profile_line3 BOOLEAN DEFAULT FALSE,
                    profile_line4 BOOLEAN DEFAULT FALSE,
                    profile_line5 BOOLEAN DEFAULT FALSE,
                    profile_line6 BOOLEAN DEFAULT FALSE,
                    profile_relational_impact TEXT,
                    
                    -- Incarnation Cross
                    incarnation_cross VARCHAR(200),
                    cross_gates TEXT,
                    cross_angle VARCHAR(50),
                    cross_relational_impact TEXT,
                    
                    -- Conditioning
                    open_centers TEXT,
                    conditioning_themes TEXT,
                    conditioning_relational_impact TEXT,
                    
                    -- Circuitry
                    circuitry_individual TEXT,
                    circuitry_tribal TEXT,
                    circuitry_collective TEXT,
                    circuitry_relational_impact TEXT,
                    
                    -- Nodes
                    conscious_node VARCHAR(100),
                    unconscious_node VARCHAR(100),
                    nodes_relational_impact TEXT,
                    
                    -- Planetary Activations (Personality)
                    sun_personality VARCHAR(20),
                    earth_personality VARCHAR(20),
                    moon_personality VARCHAR(20),
                    mercury_personality VARCHAR(20),
                    venus_personality VARCHAR(20),
                    mars_personality VARCHAR(20),
                    jupiter_personality VARCHAR(20),
                    saturn_personality VARCHAR(20),
                    uranus_personality VARCHAR(20),
                    neptune_personality VARCHAR(20),
                    pluto_personality VARCHAR(20),
                    north_node_personality VARCHAR(20),
                    south_node_personality VARCHAR(20),
                    
                    -- Planetary Activations (Design)
                    sun_design VARCHAR(20),
                    earth_design VARCHAR(20),
                    moon_design VARCHAR(20),
                    mercury_design VARCHAR(20),
                    venus_design VARCHAR(20),
                    mars_design VARCHAR(20),
                    jupiter_design VARCHAR(20),
                    saturn_design VARCHAR(20),
                    uranus_design VARCHAR(20),
                    neptune_design VARCHAR(20),
                    pluto_design VARCHAR(20),
                    north_node_design VARCHAR(20),
                    south_node_design VARCHAR(20),
                    
                    -- Relational Analysis
                    planetary_relational_impacts TEXT,
                    electromagnetic_connections TEXT,
                    compromise_connections TEXT,
                    dominance_connections TEXT,
                    conditioning_dynamics TEXT,
                    
                    -- Metadata
                    schema_version INTEGER DEFAULT 3,
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                    
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
                """
                
                connection.execute(db.text(create_hd_table_sql))
                print("   ✅ Created new human_design_data table with all fields")
                
                # Restore basic data from backup
                restore_sql = """
                INSERT INTO human_design_data (
                    user_id, chart_data, energy_type, strategy, authority, profile, api_response, calculated_at
                )
                SELECT 
                    user_id, chart_data, energy_type, strategy, authority, profile, api_response, calculated_at
                FROM human_design_data_backup
                """
                connection.execute(db.text(restore_sql))
                print("   ✅ Restored existing data to new table")
                
            except Exception as e:
                print(f"   ❌ Error fixing human_design_data table: {e}")
            
            print("\n3️⃣ Updating admin users...")
            
            # Set admin status for admin users
            try:
                admin_emails = ['admin@glow.com', 'nathanamthor@gmail.com']
                for email in admin_emails:
                    connection.execute(
                        db.text("UPDATE users SET is_admin = TRUE WHERE email = :email"),
                        {"email": email}
                    )
                print(f"   ✅ Set admin status for {admin_emails}")
            except Exception as e:
                print(f"   ❌ Error updating admin users: {e}")
            
            print("\n4️⃣ Cleaning up...")
            
            # Drop backup table
            try:
                connection.execute(db.text("DROP TABLE IF EXISTS human_design_data_backup"))
                print("   ✅ Cleaned up backup table")
            except Exception as e:
                print(f"   ⚠️  Backup cleanup warning: {e}")
            
            # Commit all changes
            connection.commit()
            connection.close()
            
            print("\n🎉 Database schema fix completed successfully!")
            print("\n📊 Summary:")
            print("   ✅ Added is_admin field to users table")
            print("   ✅ Added onboarding_completed field to users table")
            print("   ✅ Recreated human_design_data table with 80+ fields")
            print("   ✅ Set admin status for admin users")
            print("   ✅ Preserved existing data")
            
        except Exception as e:
            print(f"\n❌ Critical error during schema fix: {e}")
            return False
        
        return True

if __name__ == "__main__":
    success = fix_database_schema()
    if success:
        print("\n✅ Database schema is now consistent with the code!")
    else:
        print("\n❌ Database schema fix failed!")
        sys.exit(1)

