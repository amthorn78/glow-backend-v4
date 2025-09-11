#!/usr/bin/env python3
"""
Production Database Migration Runner
===================================

This script runs the enhanced location data migration on the production database.
It uses the same Flask app context to ensure consistency with the production environment.
"""

import os
import sys
from app import app, db

def run_production_migration():
    """Run the database migration in production environment"""
    print("🚀 Running Production Database Migration")
    print(f"📅 Migration Date: {datetime.now().isoformat()}")
    
    with app.app_context():
        try:
            # Get database URL to confirm we're using the right database
            database_url = app.config['SQLALCHEMY_DATABASE_URI']
            print(f"🔗 Database: {database_url.split('@')[-1] if '@' in database_url else 'Local SQLite'}")
            
            # Check if birth_data table exists
            if 'sqlite' in database_url.lower():
                result = db.session.execute(db.text("""
                    SELECT name FROM sqlite_master WHERE type='table' AND name='birth_data'
                """))
                table_exists = result.fetchone() is not None
                
                if table_exists:
                    # Check current columns
                    schema_result = db.session.execute(db.text("PRAGMA table_info(birth_data)"))
                    current_columns = [row[1] for row in schema_result.fetchall()]
                else:
                    current_columns = []
            else:
                # PostgreSQL
                result = db.session.execute(db.text("""
                    SELECT tablename FROM pg_tables WHERE tablename='birth_data'
                """))
                table_exists = result.fetchone() is not None
                
                if table_exists:
                    schema_result = db.session.execute(db.text("""
                        SELECT column_name FROM information_schema.columns 
                        WHERE table_name = 'birth_data' 
                        ORDER BY ordinal_position
                    """))
                    current_columns = [row[0] for row in schema_result.fetchall()]
                else:
                    current_columns = []
            
            if not table_exists:
                print("❌ birth_data table not found. Creating all tables first...")
                db.create_all()
                db.session.commit()
                print("✅ All tables created")
                return True
            
            print(f"📋 Current birth_data columns ({len(current_columns)}): {current_columns}")
            
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
            
            columns_to_add = []
            for column_name, column_type in new_columns:
                if column_name not in current_columns:
                    columns_to_add.append((column_name, column_type))
            
            if not columns_to_add:
                print("✅ All enhanced location columns already exist!")
                return True
            
            print(f"📝 Adding {len(columns_to_add)} new columns:")
            
            for column_name, column_type in columns_to_add:
                try:
                    alter_query = db.text(f"ALTER TABLE birth_data ADD COLUMN {column_name} {column_type}")
                    db.session.execute(alter_query)
                    print(f"   ✅ Added: {column_name} ({column_type})")
                except Exception as e:
                    print(f"   ❌ Error adding {column_name}: {str(e)}")
            
            # Create indexes for better performance
            indexes = [
                ("idx_birth_data_country", "location_country"),
                ("idx_birth_data_city", "location_city"),
                ("idx_birth_data_source", "location_source"),
                ("idx_birth_data_verified", "location_verified")
            ]
            
            print("📊 Creating indexes:")
            for index_name, column_name in indexes:
                try:
                    create_index_query = db.text(f"""
                        CREATE INDEX IF NOT EXISTS {index_name} 
                        ON birth_data ({column_name})
                    """)
                    db.session.execute(create_index_query)
                    print(f"   ✅ Index: {index_name}")
                except Exception as e:
                    print(f"   ⚠️  Index {index_name}: {str(e)}")
            
            # Commit all changes
            db.session.commit()
            print("💾 Migration committed successfully")
            
            # Verify final state
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
            
            print(f"🔍 Final verification: {len(final_columns)} columns in birth_data table")
            
            # Check for all expected columns
            expected_new_columns = [col[0] for col in new_columns]
            missing_columns = [col for col in expected_new_columns if col not in final_columns]
            
            if missing_columns:
                print(f"⚠️  Still missing columns: {missing_columns}")
                return False
            else:
                print("🎉 Production database migration completed successfully!")
                print("✅ All enhanced location fields are now available")
                return True
                
        except Exception as e:
            print(f"❌ Migration failed: {str(e)}")
            import traceback
            traceback.print_exc()
            db.session.rollback()
            return False

if __name__ == "__main__":
    from datetime import datetime
    success = run_production_migration()
    if not success:
        sys.exit(1)
    else:
        print("\n🚀 Production database is ready for enhanced location data!")

