#!/usr/bin/env python3
"""
Database Initialization Script
==============================

This script initializes the GLOW database with all required tables.
It imports the Flask app and creates all tables defined in the models.
"""

import os
import sys
from app import app, db

def init_database():
    """Initialize the database with all tables"""
    print("🚀 Initializing GLOW Database")
    print(f"📍 Database URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
    
    with app.app_context():
        try:
            # Create all tables
            print("📝 Creating database tables...")
            db.create_all()
            
            # Commit the changes
            db.session.commit()
            print("💾 Database changes committed")
            
            # Verify tables were created
            print("🔍 Verifying table creation...")
            
            # Get table names based on database type
            database_url = app.config['SQLALCHEMY_DATABASE_URI']
            
            if 'sqlite' in database_url.lower():
                result = db.session.execute(db.text("""
                    SELECT name FROM sqlite_master WHERE type='table' ORDER BY name
                """))
            else:
                result = db.session.execute(db.text("""
                    SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename
                """))
            
            tables = [row[0] for row in result.fetchall()]
            
            print(f"✅ Created {len(tables)} tables:")
            for table in tables:
                print(f"   - {table}")
            
            # Check specifically for birth_data table
            if 'birth_data' in tables:
                print("✅ birth_data table created successfully")
                
                # Show birth_data table structure
                if 'sqlite' in database_url.lower():
                    schema_result = db.session.execute(db.text("PRAGMA table_info(birth_data)"))
                    columns = schema_result.fetchall()
                    print("📋 birth_data table columns:")
                    for col in columns:
                        print(f"   - {col[1]} ({col[2]})")
                
            else:
                print("❌ birth_data table not found")
                return False
            
            print("🎉 Database initialization completed successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Database initialization failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    success = init_database()
    if not success:
        sys.exit(1)

