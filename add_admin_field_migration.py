#!/usr/bin/env python3
"""
Migration script to add is_admin field to users table
"""

import os
import sys
from sqlalchemy import text

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db

def add_admin_field():
    """Add is_admin field to users table"""
    with app.app_context():
        try:
            # Check if column already exists
            result = db.session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'users' AND column_name = 'is_admin'
            """))
            
            if result.fetchone():
                print("✅ is_admin column already exists")
                return
            
            # Add the column
            db.session.execute(text("""
                ALTER TABLE users 
                ADD COLUMN is_admin BOOLEAN DEFAULT FALSE NOT NULL
            """))
            
            # Set admin@glow.com as admin if it exists
            db.session.execute(text("""
                UPDATE users 
                SET is_admin = TRUE 
                WHERE email = 'admin@glow.com'
            """))
            
            db.session.commit()
            print("✅ Successfully added is_admin field and set admin@glow.com as admin")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Migration failed: {e}")
            
            # Try SQLite syntax if PostgreSQL fails
            try:
                db.session.execute(text("""
                    ALTER TABLE users 
                    ADD COLUMN is_admin BOOLEAN DEFAULT 0 NOT NULL
                """))
                
                db.session.execute(text("""
                    UPDATE users 
                    SET is_admin = 1 
                    WHERE email = 'admin@glow.com'
                """))
                
                db.session.commit()
                print("✅ Successfully added is_admin field (SQLite) and set admin@glow.com as admin")
                
            except Exception as e2:
                db.session.rollback()
                print(f"❌ SQLite migration also failed: {e2}")

if __name__ == '__main__':
    add_admin_field()

