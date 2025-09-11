#!/usr/bin/env python3
"""
Automatic Database Migration on Startup
=======================================

This script automatically runs database migrations when the Flask app starts.
It's designed to run safely in production and only applies missing migrations.
"""

import os
import sys
from datetime import datetime

def run_startup_migration():
    """Run database migration on app startup"""
    try:
        # Import here to avoid circular imports
        from app import app, db
        
        print("🔄 Checking database schema on startup...")
        
        with app.app_context():
            database_url = app.config['SQLALCHEMY_DATABASE_URI']
            is_postgres = 'postgres' in database_url.lower()
            
            print(f"📊 Database type: {'PostgreSQL' if is_postgres else 'SQLite'}")
            
            # Ensure all tables exist first
            db.create_all()
            
            # Check if birth_data table has enhanced location fields
            if is_postgres:
                result = db.session.execute(db.text("""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = 'birth_data' AND column_name = 'location_display_name'
                """))
                has_enhanced_fields = result.fetchone() is not None
            else:
                result = db.session.execute(db.text("""
                    PRAGMA table_info(birth_data)
                """))
                columns = [row[1] for row in result.fetchall()]
                has_enhanced_fields = 'location_display_name' in columns
            
            if has_enhanced_fields:
                print("✅ Enhanced location fields already exist")
                return True
            
            print("🔧 Adding enhanced location fields...")
            
            # Add new columns
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
            
            for column_name, column_type in new_columns:
                try:
                    alter_query = db.text(f"ALTER TABLE birth_data ADD COLUMN {column_name} {column_type}")
                    db.session.execute(alter_query)
                    print(f"   ✅ Added: {column_name}")
                except Exception as e:
                    if "already exists" in str(e).lower() or "duplicate column" in str(e).lower():
                        print(f"   ⚠️  {column_name} already exists")
                    else:
                        print(f"   ❌ Error adding {column_name}: {str(e)}")
            
            # Create indexes
            indexes = [
                ("idx_birth_data_country", "location_country"),
                ("idx_birth_data_city", "location_city"),
                ("idx_birth_data_source", "location_source"),
                ("idx_birth_data_verified", "location_verified")
            ]
            
            for index_name, column_name in indexes:
                try:
                    create_index_query = db.text(f"""
                        CREATE INDEX IF NOT EXISTS {index_name} 
                        ON birth_data ({column_name})
                    """)
                    db.session.execute(create_index_query)
                except Exception as e:
                    # Indexes are optional, don't fail startup for them
                    pass
            
            db.session.commit()
            print("✅ Database migration completed successfully")
            return True
            
    except Exception as e:
        print(f"❌ Startup migration failed: {str(e)}")
        # Don't fail app startup for migration issues
        return False

if __name__ == "__main__":
    run_startup_migration()

