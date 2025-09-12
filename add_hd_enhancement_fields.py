#!/usr/bin/env python3
"""
Database migration to add HD enhancement fields to CompatibilityMatrix table
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

def add_hd_enhancement_fields():
    """Add HD enhancement fields to compatibility_matrix table"""
    
    # Get database URL from environment
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("ERROR: DATABASE_URL environment variable not set")
        return False
    
    try:
        # Create engine
        engine = create_engine(database_url)
        
        # Check if fields already exist
        with engine.connect() as conn:
            # Check if hd_enhancement_factor column exists
            try:
                result = conn.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'compatibility_matrix' 
                    AND column_name = 'hd_enhancement_factor'
                """))
                
                if result.fetchone():
                    print("HD enhancement fields already exist in compatibility_matrix table")
                    return True
                    
            except Exception as e:
                print(f"Error checking existing columns: {e}")
            
            # Add the new columns
            try:
                print("Adding hd_enhancement_factor column...")
                conn.execute(text("""
                    ALTER TABLE compatibility_matrix 
                    ADD COLUMN hd_enhancement_factor FLOAT
                """))
                conn.commit()
                print("✅ Added hd_enhancement_factor column")
                
            except OperationalError as e:
                if "already exists" in str(e).lower():
                    print("hd_enhancement_factor column already exists")
                else:
                    print(f"Error adding hd_enhancement_factor: {e}")
            
            try:
                print("Adding compatibility_insights column...")
                conn.execute(text("""
                    ALTER TABLE compatibility_matrix 
                    ADD COLUMN compatibility_insights TEXT
                """))
                conn.commit()
                print("✅ Added compatibility_insights column")
                
            except OperationalError as e:
                if "already exists" in str(e).lower():
                    print("compatibility_insights column already exists")
                else:
                    print(f"Error adding compatibility_insights: {e}")
        
        print("✅ HD enhancement fields migration completed successfully")
        return True
        
    except Exception as e:
        print(f"ERROR: Migration failed: {e}")
        return False

if __name__ == "__main__":
    print("🔄 Running HD enhancement fields migration...")
    success = add_hd_enhancement_fields()
    
    if success:
        print("🎉 Migration completed successfully!")
        sys.exit(0)
    else:
        print("❌ Migration failed!")
        sys.exit(1)

