#!/usr/bin/env python3
"""
Database Migration: Enhanced Location Data Support
==================================================

This migration adds enhanced location fields to support OpenStreetMap Nominatim
autocomplete functionality and improved geocoding data storage.

New fields added to BirthData table:
- location_display_name: Full formatted location name from Nominatim
- location_country: Country name for filtering and analytics
- location_state: State/province for regional analysis
- location_city: City name for local matching
- location_importance: Nominatim importance score for ranking
- location_osm_id: OpenStreetMap ID for reference
- location_osm_type: OSM type (node, way, relation)
- timezone: Timezone identifier for accurate birth time calculations
- location_source: Source of location data (nominatim, manual, etc.)
- location_verified: Whether location has been verified/confirmed

Migration Date: September 12, 2025
Author: GLOW Development Team
"""

import os
import sys
from datetime import datetime
from sqlalchemy import create_engine, text, MetaData, Table, Column, String, Boolean, Numeric, Integer

def get_database_url():
    """Get database URL from environment or use default"""
    database_url = os.environ.get('DATABASE_URL')
    if database_url and database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    return database_url or 'sqlite:///glow_dev.db'

def run_migration():
    """Execute the database migration"""
    print("🚀 Starting Enhanced Location Data Migration")
    print(f"📅 Migration Date: {datetime.now().isoformat()}")
    
    # Connect to database
    database_url = get_database_url()
    print(f"🔗 Connecting to database: {database_url.split('@')[-1] if '@' in database_url else database_url}")
    
    engine = create_engine(database_url)
    
    try:
        with engine.connect() as conn:
            # Check if birth_data table exists (handle different database types)
            database_url = get_database_url()
            print(f"🔍 Using database URL: {database_url}")
            
            if 'sqlite' in database_url.lower():
                # First, let's see all tables
                all_tables_result = conn.execute(text("""
                    SELECT name FROM sqlite_master WHERE type='table' ORDER BY name
                """))
                all_tables = [row[0] for row in all_tables_result.fetchall()]
                print(f"📋 Found {len(all_tables)} tables: {all_tables}")
                
                result = conn.execute(text("""
                    SELECT name FROM sqlite_master WHERE type='table' AND name='birth_data'
                """))
            else:
                result = conn.execute(text("""
                    SELECT tablename FROM pg_tables WHERE tablename='birth_data'
                """))
            
            table_found = result.fetchone()
            if not table_found:
                print("❌ Error: birth_data table not found. Please ensure the base schema is created first.")
                return False
            
            print("✅ Found birth_data table")
            
            # Add new columns to birth_data table
            new_columns = [
                ("location_display_name", "TEXT"),
                ("location_country", "VARCHAR(100)"),
                ("location_state", "VARCHAR(100)"),
                ("location_city", "VARCHAR(100)"),
                ("location_importance", "DECIMAL(5,4)"),
                ("location_osm_id", "BIGINT"),
                ("location_osm_type", "VARCHAR(20)"),
                ("timezone", "VARCHAR(50)"),
                ("location_source", "VARCHAR(20) DEFAULT 'manual'"),
                ("location_verified", "BOOLEAN DEFAULT FALSE")
            ]
            
            print("📝 Adding new columns to birth_data table:")
            
            for column_name, column_type in new_columns:
                try:
                    # Check if column already exists
                    if 'sqlite' in database_url.lower():
                        check_query = text(f"PRAGMA table_info(birth_data)")
                        columns = conn.execute(check_query).fetchall()
                        column_exists = any(col[1] == column_name for col in columns)
                    else:
                        check_query = text("""
                            SELECT column_name FROM information_schema.columns 
                            WHERE table_name = 'birth_data' AND column_name = :column_name
                        """)
                        result = conn.execute(check_query, {"column_name": column_name})
                        column_exists = result.fetchone() is not None
                    
                    if column_exists:
                        print(f"   ⚠️  Column {column_name} already exists, skipping")
                        continue
                    
                    # Add the column
                    alter_query = text(f"ALTER TABLE birth_data ADD COLUMN {column_name} {column_type}")
                    conn.execute(alter_query)
                    print(f"   ✅ Added column: {column_name} ({column_type})")
                    
                except Exception as e:
                    print(f"   ❌ Error adding column {column_name}: {str(e)}")
                    # Continue with other columns
            
            # Create index on location fields for better query performance
            try:
                print("📊 Creating indexes for improved query performance:")
                
                indexes = [
                    ("idx_birth_data_country", "location_country"),
                    ("idx_birth_data_city", "location_city"),
                    ("idx_birth_data_source", "location_source"),
                    ("idx_birth_data_verified", "location_verified")
                ]
                
                for index_name, column_name in indexes:
                    try:
                        create_index_query = text(f"""
                            CREATE INDEX IF NOT EXISTS {index_name} 
                            ON birth_data ({column_name})
                        """)
                        conn.execute(create_index_query)
                        print(f"   ✅ Created index: {index_name}")
                    except Exception as e:
                        print(f"   ⚠️  Index {index_name} may already exist: {str(e)}")
                
            except Exception as e:
                print(f"   ❌ Error creating indexes: {str(e)}")
            
            # Commit the transaction
            conn.commit()
            print("💾 Migration committed successfully")
            
            # Verify the migration
            print("🔍 Verifying migration:")
            if 'sqlite' in database_url.lower():
                verify_query = text("PRAGMA table_info(birth_data)")
                columns = conn.execute(verify_query).fetchall()
                column_names = [col[1] for col in columns]
            else:
                verify_query = text("""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = 'birth_data' 
                    ORDER BY ordinal_position
                """)
                columns = conn.execute(verify_query).fetchall()
                column_names = [col[0] for col in columns]
            
            new_column_names = [col[0] for col in new_columns]
            added_columns = [col for col in new_column_names if col in column_names]
            
            print(f"   ✅ Verified {len(added_columns)} new columns added:")
            for col in added_columns:
                print(f"      - {col}")
            
            print("🎉 Enhanced Location Data Migration completed successfully!")
            return True
            
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        return False

def rollback_migration():
    """Rollback the migration (remove added columns)"""
    print("🔄 Starting Migration Rollback")
    
    database_url = get_database_url()
    engine = create_engine(database_url)
    
    columns_to_remove = [
        "location_display_name", "location_country", "location_state", 
        "location_city", "location_importance", "location_osm_id", 
        "location_osm_type", "timezone", "location_source", "location_verified"
    ]
    
    try:
        with engine.connect() as conn:
            print("⚠️  Note: SQLite does not support DROP COLUMN. For PostgreSQL:")
            
            for column_name in columns_to_remove:
                try:
                    drop_query = text(f"ALTER TABLE birth_data DROP COLUMN IF EXISTS {column_name}")
                    conn.execute(drop_query)
                    print(f"   ✅ Removed column: {column_name}")
                except Exception as e:
                    print(f"   ❌ Error removing column {column_name}: {str(e)}")
            
            conn.commit()
            print("🎉 Migration rollback completed!")
            
    except Exception as e:
        print(f"❌ Rollback failed: {str(e)}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        rollback_migration()
    else:
        success = run_migration()
        if not success:
            sys.exit(1)

