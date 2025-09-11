#!/usr/bin/env python3
"""
Database Migration: Enhanced Location Data Support (v2)
=======================================================

This migration adds enhanced location fields to support OpenStreetMap Nominatim
autocomplete functionality and improved geocoding data storage.

Uses Flask app context to ensure consistent database connection.
"""

import os
import sys
from datetime import datetime
from app import app, db

def run_migration():
    """Execute the database migration using Flask app context"""
    print("🚀 Starting Enhanced Location Data Migration (v2)")
    print(f"📅 Migration Date: {datetime.now().isoformat()}")
    
    with app.app_context():
        try:
            # Check if birth_data table exists
            database_url = app.config['SQLALCHEMY_DATABASE_URI']
            print(f"🔗 Using database: {database_url}")
            
            if 'sqlite' in database_url.lower():
                result = db.session.execute(db.text("""
                    SELECT name FROM sqlite_master WHERE type='table' ORDER BY name
                """))
                all_tables = [row[0] for row in result.fetchall()]
                print(f"📋 Found {len(all_tables)} tables: {all_tables}")
                
                birth_data_exists = 'birth_data' in all_tables
            else:
                result = db.session.execute(db.text("""
                    SELECT tablename FROM pg_tables WHERE tablename='birth_data'
                """))
                birth_data_exists = result.fetchone() is not None
            
            if not birth_data_exists:
                print("❌ Error: birth_data table not found. Please run init_database.py first.")
                return False
            
            print("✅ Found birth_data table")
            
            # Check current birth_data table structure
            if 'sqlite' in database_url.lower():
                schema_result = db.session.execute(db.text("PRAGMA table_info(birth_data)"))
                current_columns = [row[1] for row in schema_result.fetchall()]
            else:
                schema_result = db.session.execute(db.text("""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = 'birth_data' 
                    ORDER BY ordinal_position
                """))
                current_columns = [row[0] for row in schema_result.fetchall()]
            
            print(f"📋 Current birth_data columns: {current_columns}")
            
            # Define new columns to add
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
                if column_name in current_columns:
                    print(f"   ⚠️  Column {column_name} already exists, skipping")
                    continue
                
                try:
                    # Add the column
                    alter_query = db.text(f"ALTER TABLE birth_data ADD COLUMN {column_name} {column_type}")
                    db.session.execute(alter_query)
                    print(f"   ✅ Added column: {column_name} ({column_type})")
                    
                except Exception as e:
                    print(f"   ❌ Error adding column {column_name}: {str(e)}")
                    # Continue with other columns
            
            # Create indexes for better query performance
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
                        if 'sqlite' in database_url.lower():
                            create_index_query = db.text(f"""
                                CREATE INDEX IF NOT EXISTS {index_name} 
                                ON birth_data ({column_name})
                            """)
                        else:
                            create_index_query = db.text(f"""
                                CREATE INDEX IF NOT EXISTS {index_name} 
                                ON birth_data ({column_name})
                            """)
                        
                        db.session.execute(create_index_query)
                        print(f"   ✅ Created index: {index_name}")
                    except Exception as e:
                        print(f"   ⚠️  Index {index_name} may already exist: {str(e)}")
                
            except Exception as e:
                print(f"   ❌ Error creating indexes: {str(e)}")
            
            # Commit all changes
            db.session.commit()
            print("💾 Migration committed successfully")
            
            # Verify the migration
            print("🔍 Verifying migration:")
            if 'sqlite' in database_url.lower():
                verify_result = db.session.execute(db.text("PRAGMA table_info(birth_data)"))
                final_columns = [row[1] for row in verify_result.fetchall()]
            else:
                verify_result = db.session.execute(db.text("""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = 'birth_data' 
                    ORDER BY ordinal_position
                """))
                final_columns = [row[0] for row in verify_result.fetchall()]
            
            new_column_names = [col[0] for col in new_columns]
            added_columns = [col for col in new_column_names if col in final_columns]
            
            print(f"   ✅ Verified {len(added_columns)} new columns added:")
            for col in added_columns:
                print(f"      - {col}")
            
            print(f"📋 Final birth_data table has {len(final_columns)} columns:")
            for col in final_columns:
                print(f"   - {col}")
            
            print("🎉 Enhanced Location Data Migration completed successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Migration failed: {str(e)}")
            import traceback
            traceback.print_exc()
            db.session.rollback()
            return False

if __name__ == "__main__":
    success = run_migration()
    if not success:
        sys.exit(1)

