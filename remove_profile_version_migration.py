#!/usr/bin/env python3
"""
Remove profile_version Column Migration
======================================

This migration removes the unused profile_version column from the users table.
The field was deprecated and is no longer needed in the API contract.

Migration: S1.1-4_remove_profile_version
Date: September 17, 2025
"""

import os
import sys
from datetime import datetime
from app import app, db

def remove_profile_version_column():
    """Remove profile_version column from users table"""
    print("🗑️  Removing profile_version Column Migration")
    print(f"📅 Migration Date: {datetime.now().isoformat()}")
    
    with app.app_context():
        try:
            # Get database URL to confirm we're using the right database
            database_url = app.config['SQLALCHEMY_DATABASE_URI']
            print(f"🔗 Database: {database_url.split('@')[-1] if '@' in database_url else 'Local SQLite'}")
            
            # Check if profile_version column exists
            if 'postgresql' in database_url.lower():
                # PostgreSQL check
                result = db.session.execute(db.text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'users' AND column_name = 'profile_version'
                """))
                column_exists = result.fetchone() is not None
                
                if column_exists:
                    print("✅ profile_version column found in users table")
                    
                    # Drop the column
                    print("🔄 Dropping profile_version column...")
                    db.session.execute(db.text("ALTER TABLE users DROP COLUMN profile_version"))
                    db.session.commit()
                    print("✅ profile_version column dropped successfully")
                else:
                    print("ℹ️  profile_version column not found (already removed or never existed)")
                    
            elif 'sqlite' in database_url.lower():
                # SQLite check (for local development)
                result = db.session.execute(db.text("PRAGMA table_info(users)"))
                columns = [row[1] for row in result.fetchall()]
                
                if 'profile_version' in columns:
                    print("✅ profile_version column found in users table")
                    print("⚠️  SQLite doesn't support DROP COLUMN directly")
                    print("ℹ️  Column will be ignored in ORM model")
                else:
                    print("ℹ️  profile_version column not found (already removed or never existed)")
            
            # Verify the column is gone (PostgreSQL only)
            if 'postgresql' in database_url.lower():
                result = db.session.execute(db.text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'users' AND column_name = 'profile_version'
                """))
                column_still_exists = result.fetchone() is not None
                
                if not column_still_exists:
                    print("✅ Migration successful: profile_version column removed")
                else:
                    print("❌ Migration failed: profile_version column still exists")
                    return False
            
            return True
            
        except Exception as e:
            print(f"❌ Migration failed with error: {str(e)}")
            db.session.rollback()
            return False

if __name__ == "__main__":
    success = remove_profile_version_column()
    if success:
        print("🎉 Migration completed successfully")
        sys.exit(0)
    else:
        print("💥 Migration failed")
        sys.exit(1)

